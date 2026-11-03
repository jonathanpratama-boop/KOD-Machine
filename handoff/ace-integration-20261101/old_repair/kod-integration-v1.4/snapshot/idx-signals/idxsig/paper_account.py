"""PAPER_ACCOUNT_v1: one capital-constrained paper account that takes KOD's US paper-book candidates through the
shared execution model (research/PAPER_ACCOUNT_v1/protocol.json). Paper only: no orders, no money.

Owner and Ace (2026-10-31): connect the existing execution model to a separately versioned, capital-constrained
paper account; $10,000, 0.5% planned risk per position, 1.5% aggregate planned risk including pending orders, at
most three new positions per session, no leverage; the signal-low stop as the baseline and a fixed 5% stop below
the fill as one shadow comparison; the frozen paper book left untouched.

Candidates come from paper/paper_book.jsonl: every BUY_OK plan the owner did not SKIP, and every spike the owner
confirmed BUY. Each arm keeps its own account:

  BASE    exec_us.make_plan / execute unchanged (EXEC-US-v1): stop at the signal session's low, permitted entry
          the highest open whose stop is at most 5% away (and never above the signal close x 1.10), buy at the
          opening print or not at all, resting stop, gap fills at the open, market-on-close exit five sessions on.
  FIXED5  the same, except the stop is set when the entry fills, 5% below the fill (rounded up to the tick), and
          the permitted entry is only the chase limit; the order is sized as if filled at that limit.

Lifecycle, one record each, in paper/paper_account.jsonl (hash chain, RFC 3161 stamped):
  ACCT_ORDER    sealed before the entry session's 09:30 New York open (calendar_us): plan, sizing, the account
                state it was sized from, the cash it reserves and the planned risk it adds.
  ACCT_DECLINE  a candidate the account did not order, with the reason (no plan, a limit, no bars).
  ACCT_CANCEL   the owner's SKIP on an ordered spike before the open.
  ACCT_ENTRY    the opening print decided it: FILLED (price, shares, stop) or REJECTED_* with the reason.
  ACCT_EXIT     the position closed: stop, gap through the stop, or the time exit; realized P&L after costs.
  ACCT_MARK     the account at the latest close: cash, reserved, open value, equity, realized, unrealized.
A plan never counts as a purchase; realized gains need a completed exit; open losses stay in equity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from . import calendar_us, exec_us, paper, paper_book
from .provenance import utc_stamp

LEDGER = paper.PAPER / "paper_account.jsonl"
REPORT = paper.PAPER / "PAPER_ACCOUNT.md"
ACCOUNT_ID = "PAPER_ACCOUNT_v1"
ORDER, DECLINE, CANCEL, ENTRY, EXIT, MARK = (
    "ACCT_ORDER",
    "ACCT_DECLINE",
    "ACCT_CANCEL",
    "ACCT_ENTRY",
    "ACCT_EXIT",
    "ACCT_MARK",
)
ARMS = ("BASE", "FIXED5")
START_CASH = 10_000.0
RISK_FRACTION = 0.005  # planned loss at the stop per position, of equity
MAX_PLANNED_RISK = 0.015  # all open positions and pending orders together, of equity
MAX_NEW_PER_SESSION = 3
FIXED_STOP = 0.05


@dataclass(frozen=True)
class Bars:
    """One name's adjusted daily bars with unit factors (as traded = adjusted x uf); s is the signal session."""

    o: np.ndarray
    h: np.ndarray
    lo: np.ndarray
    c: np.ndarray
    v: np.ndarray
    present: np.ndarray
    uf: np.ndarray
    s: int
    dates: np.ndarray

    def last(self) -> int:
        return int(max(k for k in range(len(self.c)) if self.present[k] and np.isfinite(self.c[k])))


def spec_for(equity: float) -> exec_us.ExecSpec:
    return exec_us.ExecSpec(equity_usd=round(float(equity), 2), risk_fraction=RISK_FRACTION)


def ceil_tick(price: float) -> float:
    t = exec_us.tick(price)
    return round(math.ceil(price / t - 1e-9) * t, 6)


def lines() -> list[dict]:
    return paper.ledger_lines(LEDGER) if LEDGER.exists() else []


# ------------------------------------------------------------------------------------- candidates
def candidates(book_recs: list[dict] | None = None) -> tuple[list[dict], set[str]]:
    """(spikes the account should consider, set_ids the owner skipped) from the paper book."""
    book_recs = paper_book.lines() if book_recs is None else book_recs
    plans = {r["set_id"]: r for r in book_recs if r["type"] == paper_book.PLAN}
    out, skipped = [], set()
    for row in paper_book.trades(book_recs):
        p = plans[row["set_id"]]
        if row["owner"] == "SKIP":
            skipped.add(row["set_id"])
            continue
        if row["verdict"] != "BUY_OK" and row["owner"] != "BUY":
            continue
        source = (
            "OWNER"
            if row["verdict"] != "BUY_OK"
            else "KOD+OWNER"
            if row["owner"] == "BUY"
            else "KOD"
        )
        out.append(
            {
                "set_id": row["set_id"],
                "ticker": row["ticker"],
                "signal_session": row["session"],
                "dump_tomorrow": row["dump_tomorrow"],
                "source": source,
                "book_plan_record_hash": p["record_hash"],
            }
        )
    return sorted(out, key=lambda c: (c["dump_tomorrow"], c["ticker"])), skipped


def entry_cutoff(signal_session: str) -> datetime:
    return calendar_us.open_utc(calendar_us.next_session(signal_session))


# ------------------------------------------------------------------------------------------ state
def orders_of(recs: list[dict], arm: str) -> dict[str, dict]:
    """order record hash -> {order, entry, exit, cancel} for one arm."""
    book: dict[str, dict] = {}
    for r in recs:
        if r.get("arm") != arm:
            continue
        if r["type"] == ORDER:
            book[r["record_hash"]] = {"order": r, "entry": None, "exit": None, "cancel": None}
        elif r["type"] in (ENTRY, EXIT, CANCEL):
            book[r["order_record_hash"]][r["type"].split("_")[1].lower()] = r
    return book


def cost_basis(entry: dict) -> float:
    return entry["shares"] * entry["price"] * (1 + entry["cost_in"])


def account_state(recs: list[dict], arm: str, marks: dict[str, float] | None = None) -> dict:
    """Cash, reservations, open positions, equity and planned risk. marks: order hash -> return since the
    entry at the latest close (adjusted bars, so splits cancel); a position without a mark is held at cost."""
    marks = marks or {}
    cash, reserved, risk, realized, value, unrealized = START_CASH, 0.0, 0.0, 0.0, 0.0, 0.0
    open_positions = []
    for h, x in orders_of(recs, arm).items():
        o, en, ex = x["order"], x["entry"], x["exit"]
        if en is None:
            if x["cancel"] is None:
                reserved += o["reserved_usd"]
                risk += o["planned_risk_usd"]
            continue
        if en["status"] != "FILLED":
            continue
        cash -= cost_basis(en)
        if ex is not None:
            cash += cost_basis(en) + ex["net_pnl_usd"]
            realized += ex["net_pnl_usd"]
            continue
        r = marks.get(h)
        worth = en["shares"] * en["price"] * (1 + (r if r is not None else 0.0))
        at_stop = en["shares"] * en["stop"]
        value += worth
        unrealized += worth * (1 - exec_us.cost_rate(en["price"], "sell")) - cost_basis(en)
        risk += max(worth - at_stop, 0.0) + at_stop * exec_us.cost_rate(en["stop"], "sell")
        open_positions.append(
            {"order_record_hash": h, "ticker": o["ticker"], "mark_return": r, "value": worth}
        )
    return {
        "cash": cash,
        "reserved": reserved,
        "free_cash": cash - reserved,
        "open_value": value,
        "equity": cash + value,
        "planned_risk": risk,
        "realized": realized,
        "unrealized": unrealized,
        "open": open_positions,
    }


# ----------------------------------------------------------------------------------------- orders
def make_order_plan(arm: str, b: Bars, equity: float) -> dict:
    s = b.s
    close = float(b.c[s] * b.uf[s])
    cap = exec_us.capacity_shares(b.v, b.present, b.uf, s)
    spec = spec_for(equity)
    if arm == "BASE":
        plan = exec_us.make_plan(close, float(b.lo[s] * b.uf[s]), cap, spec)
        return {**plan, "stop_rule": "signal-session low (EXEC-US-v1)"}
    chase = exec_us.floor_tick(close * (1 + spec.chase_limit))
    plan = exec_us.make_plan(close, exec_us.floor_tick(chase * (1 - FIXED_STOP)), cap, spec)
    return {
        **plan,
        "stop_rule": "5% below the fill, set when the entry fills; the invalidation here only sizes the order",
    }


def plan_orders(recs, arm, cands, bars_of, marks, now: datetime) -> list[dict]:
    """ORDER or DECLINE for every candidate this arm has not decided yet and whose open is still ahead."""
    state = account_state(recs, arm, marks)
    decided = {r["set_id"] for r in recs if r.get("arm") == arm and r["type"] in (ORDER, DECLINE)}
    per_session: dict[str, int] = {}
    for r in recs:
        if r.get("arm") == arm and r["type"] == ORDER:
            per_session[r["signal_session"]] = per_session.get(r["signal_session"], 0) + 1
    out = []
    for c in cands:
        cutoff = entry_cutoff(c["signal_session"])
        if c["set_id"] in decided or now >= cutoff:
            continue
        base = {
            "account": ACCOUNT_ID,
            "arm": arm,
            **{k: c[k] for k in ("set_id", "ticker", "signal_session", "source", "dump_tomorrow")},
            "book_plan_record_hash": c["book_plan_record_hash"],
            "entry_cutoff": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "made_at": utc_stamp(),
        }
        b = bars_of(c)
        if isinstance(b, str):
            out.append({"type": DECLINE, **base, "reason": f"NO_BARS: {b}"})
            continue
        if b.s != b.last():
            out.append(
                {"type": DECLINE, **base, "reason": "NO_BARS: the bars run past the signal session"}
            )
            continue
        plan = make_order_plan(arm, b, state["equity"])
        snapshot = {k: round(state[k], 2) for k in ("equity", "cash", "free_cash", "planned_risk")}
        if plan["status"] != "PLANNED":
            out.append(
                {"type": DECLINE, **base, "reason": f"NO_PLAN: {plan['reason']}", "plan": plan}
            )
            continue
        reserve = round(plan["shares"] * plan["max_entry"] * (1 + plan["cost_in_at_max_entry"]), 2)
        risk = plan["max_planned_loss_usd"]
        reason = (
            f"LIMIT_NEW_PER_SESSION: {MAX_NEW_PER_SESSION} orders already placed for this session"
            if per_session.get(c["signal_session"], 0) >= MAX_NEW_PER_SESSION
            else f"LIMIT_PLANNED_RISK: {state['planned_risk']:.2f} + {risk:.2f} would exceed "
            f"{MAX_PLANNED_RISK:.1%} of equity {state['equity']:.2f}"
            if state["planned_risk"] + risk > MAX_PLANNED_RISK * state["equity"] + 1e-9
            else f"INSUFFICIENT_CASH: reserving {reserve:.2f} needs more than the free cash {state['free_cash']:.2f}"
            if reserve > state["free_cash"] + 1e-9
            else None
        )
        if reason:
            out.append(
                {"type": DECLINE, **base, "reason": reason, "plan": plan, "account_state": snapshot}
            )
            continue
        out.append(
            {
                "type": ORDER,
                **base,
                "plan": plan,
                "account_state": snapshot,
                "reserved_usd": reserve,
                "planned_risk_usd": risk,
                "order": f"buy {plan['shares']} at the opening print of the next session, limit "
                f"{plan['max_entry']:g}; not filled later",
            }
        )
        per_session[c["signal_session"]] = per_session.get(c["signal_session"], 0) + 1
        state["reserved"] += reserve
        state["free_cash"] -= reserve
        state["planned_risk"] += risk
    return out


def cancel_records(recs, arm, skipped: set[str], now: datetime) -> list[dict]:
    out = []
    for h, x in orders_of(recs, arm).items():
        o = x["order"]
        if (
            o["set_id"] in skipped
            and x["entry"] is None
            and x["cancel"] is None
            and now.strftime("%Y-%m-%dT%H:%M:%SZ") < o["entry_cutoff"]
        ):
            out.append(
                {
                    "type": CANCEL,
                    "account": ACCOUNT_ID,
                    "arm": arm,
                    "set_id": o["set_id"],
                    "ticker": o["ticker"],
                    "order_record_hash": h,
                    "reason": "the owner skipped this spike before the open",
                    "made_at": utc_stamp(),
                }
            )
    return out


# ----------------------------------------------------------------------------------------- fills
def execution_plan(arm: str, plan: dict, b: Bars) -> dict:
    """The plan execute() runs: BASE unchanged; FIXED5 with its stop set 5% below the opening fill."""
    e = b.s + 1
    if arm == "BASE" or e >= len(b.c) or not (np.isfinite(b.o[e]) and b.o[e] > 0):
        return plan
    open_in_signal_units = float(b.o[e] * b.uf[b.s])
    return {**plan, "invalidation": ceil_tick(open_in_signal_units * (1 - FIXED_STOP))}


def settle(order: dict, entry: dict | None, b: Bars) -> tuple[list[dict], float | None]:
    """New ENTRY/EXIT records for one order from the bars, and the open position's return since entry."""
    arm = order["arm"]
    spec = spec_for(order["account_state"]["equity"])
    plan = execution_plan(arm, order["plan"], b)
    res = exec_us.execute(b.o, b.h, b.lo, b.c, b.v, b.present, b.uf, b.s, plan, spec)
    if res["status"] == "PENDING" and "entry_session_index" not in res:
        return [], None
    e = b.s + 1
    base = {
        "account": ACCOUNT_ID,
        "arm": arm,
        "set_id": order["set_id"],
        "ticker": order["ticker"],
        "order_record_hash": order["record_hash"],
        "recorded_at": utc_stamp(),
    }
    out = []
    if entry is None:
        status = res["status"]
        if status.startswith("REJECTED"):
            if arm == "FIXED5" and status == "REJECTED_STOP_TOO_WIDE":
                status = "REJECTED_ABOVE_CHASE_LIMIT"
            return [
                {
                    "type": ENTRY,
                    **base,
                    "status": status,
                    "entry_session": str(b.dates[e]) if e < len(b.dates) else None,
                    "reason": res.get("reason"),
                    "open_as_traded": res.get("open_as_traded"),
                }
            ], None
        price = float(b.o[e] * b.uf[e])
        out.append(
            {
                "type": ENTRY,
                **base,
                "status": "FILLED",
                "entry_session": str(b.dates[e]),
                "price": price,
                "shares": math.floor(plan["shares"] * b.uf[b.s] / b.uf[e] + 1e-9),
                "stop": float(plan["invalidation"] / b.uf[b.s] * b.uf[e]),
                "cost_in": exec_us.cost_rate(price, "buy"),
                "time_exit_session": str(b.dates[e + spec.exit_after_sessions])
                if e + spec.exit_after_sessions < len(b.dates)
                else f"close of the {spec.exit_after_sessions}th session after entry",
            }
        )
    if res["status"] == "FILLED":
        out.append(
            {
                "type": EXIT,
                **base,
                "exit_session": str(b.dates[res["exit_session_index"]]),
                "exit_reason": res["exit_reason"],
                "price": res["exit_price_as_traded"],
                "cost_out": res["exit_cost_rate"],
                "net_return": res["net_return"],
                "net_pnl_usd": res["net_pnl_usd"],
            }
        )
        return out, None
    return out, float(b.c[b.last()] / b.o[e] - 1)


def sync(recs, book_recs, bars_of, now: datetime, session: str | None) -> list[dict]:
    """Everything new for both arms, in order: cancels, fills and exits, marks, then tonight's orders."""
    cands, skipped = candidates(book_recs)
    new: list[dict] = []
    for arm in ARMS:
        new += cancel_records(recs + new, arm, skipped, now)
        marks = {}
        for h, x in orders_of(recs + new, arm).items():
            if x["cancel"] is not None or x["exit"] is not None:
                continue
            if x["entry"] is not None and x["entry"]["status"] != "FILLED":
                continue
            b = bars_of(x["order"])
            if isinstance(b, str):
                continue
            got, mark = settle(x["order"], x["entry"], b)
            new += got
            if mark is not None:
                marks[h] = mark
        state = account_state(recs + new, arm, marks)
        if session and not any(
            r["type"] == MARK and r["arm"] == arm and r["session"] == session for r in recs + new
        ):
            new.append(
                {
                    "type": MARK,
                    "account": ACCOUNT_ID,
                    "arm": arm,
                    "session": session,
                    **{
                        k: round(state[k], 2)
                        for k in (
                            "cash",
                            "reserved",
                            "open_value",
                            "equity",
                            "realized",
                            "unrealized",
                        )
                    },
                    "open_positions": [{**p, "value": round(p["value"], 2)} for p in state["open"]],
                    "made_at": utc_stamp(),
                }
            )
        new += plan_orders(recs + new, arm, cands, bars_of, marks, now)
    return new


# ---------------------------------------------------------------------------------- bars (live glue)
def bars_from_manifest(manifest, verify=None):
    """A bars_of(candidate or order) over a recent US pull, units reconciled as the register does."""
    import pandas as pd

    from . import speculation, us_actions

    df, data = paper.load_recent(manifest, "US", purpose="scoring")
    m = paper._market(df, "US")
    events = us_actions.yahoo_events(manifest, market="US")
    sets = {r["set_id"]: r for r in speculation.spec_lines() if r["type"] == "SPECULATION_SET"}
    dates = m.dates.astype(str)

    def bars_of(c) -> Bars | str:
        s = sets.get(c["set_id"])
        if s is None:
            return "no speculation set for this spike"
        located, _, reason = speculation._units_for(
            c["ticker"],
            c["signal_session"],
            float(s["signal"]["close"]),
            m,
            events if len(events) else pd.DataFrame(),
            verify,
            "US",
        )
        if located is None:
            return reason
        n, d, uf = located
        return Bars(
            m.open[n],
            m.high[n],
            m.low[n],
            m.close[n],
            m.volume[n],
            m.present[n],
            np.array([uf(k) for k in range(len(dates))]),
            d,
            dates,
        )

    return bars_of, str(dates[-1]), data


# ---------------------------------------------------------------------------------------- report
def drawdown(recs: list[dict], arm: str) -> float:
    peak, worst = START_CASH, 0.0
    for r in recs:
        if r["type"] == MARK and r["arm"] == arm:
            peak = max(peak, r["equity"])
            worst = min(worst, r["equity"] / peak - 1)
    return worst


def render(recs: list[dict]) -> str:
    out = [
        "# KOD paper account (PAPER_ACCOUNT_v1)",
        "",
        f"Generated {utc_stamp()}. Paper only: no orders, no money. Protocol: `research/PAPER_ACCOUNT_v1/protocol.json`.",
        "",
        "## The three plain answers",
        "",
        (
            "- **What does it do?** It takes KOD's BUY_OK spikes (and the ones you confirm) through the real "
            f"execution rules with one shared ${START_CASH:,.0f} account: {RISK_FRACTION:.1%} planned loss per "
            f"position, {MAX_PLANNED_RISK:.1%} for everything at once, at most {MAX_NEW_PER_SESSION} new orders per "
            "session, no leverage. An order fills only at the next opening print inside its limit; stops and the "
            "five-session time exit are applied as the bars come in."
        ),
        (
            "- **What counts as working?** First, plumbing: every decision has a sealed plan and a reason, cash and "
            "positions reconcile, realized gains only after an exit, open losses in equity. Profit is judged later, "
            "on many closed trades, never on a few."
        ),
        (
            "- **Two stops side by side:** BASE uses the spike day's low (the existing contract); FIXED5 puts the "
            "stop 5% below the fill. Same candidates, costs and exits."
        ),
        "",
        "## Accounts",
        "",
        "| Arm | Equity | Cash | Reserved | Open value | Realized | Unrealized | Max drawdown | Orders | Filled | Rejected | Declined |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        marks = [r for r in recs if r["type"] == MARK and r["arm"] == arm]
        last = marks[-1] if marks else None
        book = orders_of(recs, arm)
        filled = sum(1 for x in book.values() if x["entry"] and x["entry"]["status"] == "FILLED")
        rejected = sum(1 for x in book.values() if x["entry"] and x["entry"]["status"] != "FILLED")
        declined = sum(1 for r in recs if r["type"] == DECLINE and r["arm"] == arm)
        if last:
            vals = [
                last[k]
                for k in ("equity", "cash", "reserved", "open_value", "realized", "unrealized")
            ]
        else:
            st = account_state(recs, arm)
            vals = [
                st[k]
                for k in ("equity", "cash", "reserved", "open_value", "realized", "unrealized")
            ]
        out.append(
            f"| {arm} | "
            + " | ".join(f"${v:,.2f}" for v in vals)
            + f" | {drawdown(recs, arm):.2%} | {len(book)} | {filled} | {rejected} | {declined} |"
        )
    out += [
        "",
        "## Every decision",
        "",
        "| Signal | Ticker | Arm | Source | Decision | Entry | Exit | Net P&L |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    for arm in ARMS:
        book = orders_of(recs, arm)
        for r in recs:
            if r.get("arm") != arm or r["type"] not in (ORDER, DECLINE):
                continue
            if r["type"] == DECLINE:
                out.append(
                    f"| {r['signal_session']} | {r['ticker']} | {arm} | {r['source']} | declined: {r['reason']} | - | - | - |"
                )
                continue
            x = book[r["record_hash"]]
            p = r["plan"]
            decision = f"order {p['shares']} @ <= {p['max_entry']:g}"
            if x["cancel"]:
                entry = "cancelled by you"
            elif x["entry"] is None:
                entry = "pending (next open)"
            elif x["entry"]["status"] != "FILLED":
                entry = f"{x['entry']['status']}: {x['entry']['reason']}"
            else:
                en = x["entry"]
                entry = f"filled {en['shares']} @ {en['price']:.4g}, stop {en['stop']:.4g}"
            ex = x["exit"]
            exit_ = f"{ex['exit_reason']} {ex['exit_session']} @ {ex['price']:.4g}" if ex else "-"
            pnl = f"${ex['net_pnl_usd']:+,.2f}" if ex else "-"
            out.append(
                f"| {r['signal_session']} | {r['ticker']} | {arm} | {r['source']} | {decision} | {entry} | {exit_} | {pnl} |"
            )
    return "\n".join(out) + "\n"


def write_report():
    REPORT.write_text(render(lines()), encoding="utf-8")
    return REPORT


def verify() -> list[str]:
    if not LEDGER.exists():
        return []
    problems = [f"paper_account.jsonl: {p}" for p in paper.verify_chain(LEDGER)]
    recs = lines()
    orders = {r["record_hash"]: r for r in recs if r["type"] == ORDER}
    decided, followed = set(), set()
    for r in recs:
        if r["type"] in (ORDER, DECLINE):
            key = (r["arm"], r["set_id"])
            if key in decided:
                problems.append(f"{r['arm']} {r['set_id']}: decided twice")
            decided.add(key)
            if r["made_at"] >= r["entry_cutoff"]:
                problems.append(f"{r['arm']} {r['set_id']}: decided after the open")
        elif r["type"] in (ENTRY, EXIT, CANCEL):
            o = orders.get(r["order_record_hash"])
            if o is None or o["arm"] != r["arm"] or o["set_id"] != r["set_id"]:
                problems.append(
                    f"{r['arm']} {r['set_id']}: {r['type']} does not point at its order"
                )
                continue
            if (r["order_record_hash"], r["type"]) in followed:
                problems.append(f"{r['arm']} {r['set_id']}: {r['type']} recorded twice")
            followed.add((r["order_record_hash"], r["type"]))
            if r["type"] == CANCEL and r["made_at"] >= o["entry_cutoff"]:
                problems.append(f"{r['arm']} {r['set_id']}: cancelled after the open")
            if r["type"] == ENTRY and r["recorded_at"] < o["entry_cutoff"]:
                problems.append(f"{r['arm']} {r['set_id']}: entry recorded before the open")
            if r["type"] == EXIT and (r["order_record_hash"], ENTRY) not in followed:
                problems.append(f"{r['arm']} {r['set_id']}: exit without a filled entry")
    return problems
