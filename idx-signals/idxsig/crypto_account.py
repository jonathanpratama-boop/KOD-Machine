"""CRYPTO_ACCOUNT_v1: a crypto spot paper account (research/CRYPTO_ACCOUNT_v1/protocol.json). Paper only: no orders.

A separate adapter beside the frozen US stock account. It reuses that account's tested cash accounting
(paper_account.orders_of / account_state: cash, reservations, fills, cancels, realized P&L) by writing records
of the same shapes, and replaces everything market-specific:

  * time: 24/7 UTC timestamps; no sessions, no opens. An order lives ORDER_VALID after it is placed.
  * prices: only recorded Binance spot best bid/ask observations (CRYPTO_QUOTE records, taken from the public
    bookTicker endpoint and timestamped when observed). Nothing fills, stops or exits on a price that was not
    recorded in this ledger.
  * fees: an explicit taker fee per side (FEE); the bid/ask spread is paid by buying at the ask, selling at the bid.
  * fills: a limit buy fills at the ask of the first recorded quote, from the decision quote on and before the
    order expires, whose ask is at or below the limit; otherwise it expires unfilled (ACCT_ENTRY EXPIRED_UNFILLED).
  * exits: the stop is set at the fill, MAX_STOP below it. A position exits at the bid of the first recorded quote
    after the fill whose bid is at or below the stop (that bid can be well below the stop: quotes are sparse),
    or at the bid of the first recorded quote at or after the HOLD deadline.

Decisions come from the crypto paper scan (paper/ledger.jsonl, the frozen paper policy). The account only buys a
decision the policy itself made a buy; every PASS is recorded as a decline with the policy's reason. Quantities
are fractional (exchange lot-size and minimum-notional rules are not modelled). Records live in
paper/crypto_account.jsonl (hash chain, RFC 3161 stamped); nothing is edited, a correction is a new line.
"""

from __future__ import annotations

import json
import math
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote as quote_url

from . import paper
from . import paper_account as stock
from .provenance import utc_stamp

LEDGER = paper.PAPER / "crypto_account.jsonl"
REPORT = paper.PAPER / "CRYPTO_ACCOUNT.md"
ACCOUNT_ID = "CRYPTO_ACCOUNT_v1"
ARM = "CRYPTO_SPOT"
QUOTE = "CRYPTO_QUOTE"
ORDER, DECLINE, CANCEL, ENTRY, EXIT, MARK = (
    stock.ORDER,
    stock.DECLINE,
    stock.CANCEL,
    stock.ENTRY,
    stock.EXIT,
    stock.MARK,
)
START_CASH = stock.START_CASH  # 10,000 USDT
RISK_FRACTION = stock.RISK_FRACTION  # 0.5% planned loss per position
MAX_PLANNED_RISK = stock.MAX_PLANNED_RISK  # 1.5% for pending and open together
MAX_NEW_PER_DAY = 3  # new orders per UTC day
MAX_POSITION = 0.20  # of equity in one coin
FEE = 0.001  # taker fee per side (Binance spot base rate)
CHASE = 0.01  # limit = the policy's decision-time quote x (1 + CHASE)
MAX_STOP = 0.05  # stop set at the fill, 5% below it
ORDER_VALID = timedelta(hours=1)
HOLD = timedelta(days=5)
FIRST_SIGNAL = "2026-10-30"
BOOK_TICKER = "https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol={}"


def lines() -> list[dict]:
    return paper.ledger_lines(LEDGER) if LEDGER.exists() else []


def _t(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _stamp(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def floor8(x: float) -> float:
    return math.floor(x * 1e8 + 1e-6) / 1e8


# ---------------------------------------------------------------------------------------- quotes
def fetch_quotes(symbols: list[str]) -> list[dict]:
    """One CRYPTO_QUOTE per symbol that answered; a symbol without an answer gets no record."""
    out = []
    for sym in sorted(set(symbols)):
        url = BOOK_TICKER.format(quote_url(sym))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read())
            bid, ask = float(body["bidPrice"]), float(body["askPrice"])
        except Exception:  # noqa: BLE001, S112 - no answer is no observation
            continue
        if bid > 0 and ask >= bid:
            out.append(
                {
                    "type": QUOTE,
                    "account": ACCOUNT_ID,
                    "symbol": sym,
                    "bid": bid,
                    "ask": ask,
                    "observed_at": utc_stamp(),
                    "source": url,
                }
            )
    return out


def quotes_of(recs: list[dict], symbol: str) -> list[dict]:
    return sorted(
        (r for r in recs if r["type"] == QUOTE and r["symbol"] == symbol),
        key=lambda r: r["observed_at"],
    )


# ------------------------------------------------------------------------------------- decisions
def candidates(ledger_recs: list[dict]) -> list[dict]:
    """The crypto paper scan's decisions from FIRST_SIGNAL on, oldest first."""
    return sorted(
        (
            r
            for r in ledger_recs
            if r.get("market") == "CRYPTO"
            and r.get("type") == "DECISION"
            and r["signal_session"] >= FIRST_SIGNAL
        ),
        key=lambda r: (r["decided_at"], r["decision_id"]),
    )


def symbol_of(decision: dict) -> str:
    return f"{decision['instrument']['ticker']}USDT"


def account(recs: list[dict]) -> dict:
    """Cash, reservations and realized P&L from the stock account's tested accounting; the open positions valued
    here at the latest recorded bid, with this adapter's fee, and their risk to the stop."""
    st = stock.account_state(recs, ARM)
    value = unrealized = open_risk = 0.0
    positions = []
    for h, x in stock.orders_of(recs, ARM).items():
        en = x["entry"]
        if en is None or en["status"] != "FILLED" or x["exit"] is not None:
            continue
        qs = quotes_of(recs, x["order"]["symbol"])
        last = qs[-1] if qs else None
        bid = last["bid"] if last else en["price"]
        worth = en["shares"] * bid
        value += worth
        unrealized += worth * (1 - FEE) - stock.cost_basis(en)
        open_risk += max(worth - en["shares"] * en["stop"], 0.0) + en["shares"] * en["stop"] * FEE
        positions.append(
            {
                "order_record_hash": h,
                "symbol": x["order"]["symbol"],
                "quantity": en["shares"],
                "bid": bid,
                "valued_at": last["observed_at"] if last else None,
                "value": worth,
            }
        )
    pending_risk = sum(
        x["order"]["planned_risk_usd"]
        for x in stock.orders_of(recs, ARM).values()
        if x["entry"] is None and x["cancel"] is None
    )
    return {
        "cash": st["cash"],
        "reserved": st["reserved"],
        "free_cash": st["free_cash"],
        "open_value": value,
        "equity": st["cash"] + value,
        "realized": st["realized"],
        "unrealized": unrealized,
        "planned_risk": pending_risk + open_risk,
        "open": positions,
    }


def decide(recs: list[dict], cands: list[dict], now: datetime) -> list[dict]:
    """ORDER or DECLINE for each scan decision this account has not decided yet."""
    decided = {r["decision_id"] for r in recs if r["type"] in (ORDER, DECLINE)}
    state = account(recs)
    today = _stamp(now)[:10]
    placed_today = sum(1 for r in recs if r["type"] == ORDER and r["made_at"][:10] == today)
    out = []
    for d in cands:
        if d["decision_id"] in decided:
            continue
        sym = symbol_of(d)
        qs = quotes_of(recs, sym)
        q = qs[-1] if qs else None
        base = {
            "account": ACCOUNT_ID,
            "arm": ARM,
            "decision_id": d["decision_id"],
            "set_id": d["decision_id"],
            "ticker": d["instrument"]["ticker"],
            "symbol": sym,
            "signal_session": d["signal_session"],
            "policy_decision": d["decision"],
            "decision_record_hash": d["record_hash"],
            "made_at": _stamp(now),
        }
        if not d["decision"].upper().startswith("BUY"):
            out.append(
                {
                    "type": DECLINE,
                    **base,
                    "reason": f"POLICY_{d['decision']}: {d.get('reason', '')}",
                }
            )
            continue
        if q is None:
            out.append(
                {"type": DECLINE, **base, "reason": "NO_QUOTE: no recorded spot quote for the coin"}
            )
            continue
        ref = float((d.get("verified_price") or {}).get("quote") or 0)
        if not ref > 0:
            out.append(
                {
                    "type": DECLINE,
                    **base,
                    "reason": "NO_DECISION_PRICE: the policy recorded no quote",
                }
            )
            continue
        limit = ref * (1 + CHASE)
        stop_at_limit = limit * (1 - MAX_STOP)
        per_unit = (limit - stop_at_limit) + limit * 2 * FEE
        qty = floor8(
            min(RISK_FRACTION * state["equity"] / per_unit, MAX_POSITION * state["equity"] / limit)
        )
        reserve = round(qty * limit * (1 + FEE), 8)
        risk = round(qty * per_unit, 8)
        reason = (
            "NO_SIZE: no quantity fits the limits"
            if qty <= 0
            else f"LIMIT_NEW_PER_DAY: {MAX_NEW_PER_DAY} orders already placed on {today}"
            if placed_today >= MAX_NEW_PER_DAY
            else f"LIMIT_PLANNED_RISK: {state['planned_risk']:.2f} + {risk:.2f} would exceed "
            f"{MAX_PLANNED_RISK:.1%} of equity {state['equity']:.2f}"
            if state["planned_risk"] + risk > MAX_PLANNED_RISK * state["equity"] + 1e-9
            else f"INSUFFICIENT_CASH: reserving {reserve:.2f} needs more than the free cash {state['free_cash']:.2f}"
            if reserve > state["free_cash"] + 1e-9
            else None
        )
        if reason:
            out.append({"type": DECLINE, **base, "reason": reason})
            continue
        out.append(
            {
                "type": ORDER,
                **base,
                "limit": limit,
                "quantity": qty,
                "reserved_usd": reserve,
                "planned_risk_usd": risk,
                "fee_per_side": FEE,
                "decision_quote_record_hash": q["record_hash"],
                "decision_quote_at": q["observed_at"],
                "valid_until": _stamp(now + ORDER_VALID),
                "account_state": {
                    k: round(state[k], 2) for k in ("equity", "cash", "free_cash", "planned_risk")
                },
                "plan": {"shares": qty, "max_entry": limit},
                "order": f"buy {qty:g} {sym} at or below {limit:g}, valid until {_stamp(now + ORDER_VALID)}",
            }
        )
        placed_today += 1
        state["reserved"] += reserve
        state["free_cash"] -= reserve
        state["planned_risk"] += risk
    return out


def cancel(recs: list[dict], order_hash: str, reason: str, now: datetime) -> dict:
    x = stock.orders_of(recs, ARM).get(order_hash)
    if (
        x is None
        or x["entry"] is not None
        or x["cancel"] is not None
        or now >= _t(x["order"]["valid_until"])
    ):
        raise ValueError("only a pending, unexpired order can be cancelled")
    o = x["order"]
    return {
        "type": CANCEL,
        "account": ACCOUNT_ID,
        "arm": ARM,
        "set_id": o["set_id"],
        "ticker": o["ticker"],
        "order_record_hash": order_hash,
        "reason": reason,
        "made_at": _stamp(now),
    }


# ----------------------------------------------------------------------------------- fills, exits
def settle(recs: list[dict], now: datetime) -> list[dict]:
    """ENTRY for pending orders (fill or expiry), EXIT for open positions, from recorded quotes only."""
    out = []
    for h, x in stock.orders_of(recs, ARM).items():
        o = x["order"]
        if x["cancel"] is not None or x["exit"] is not None:
            continue
        base = {
            "account": ACCOUNT_ID,
            "arm": ARM,
            "set_id": o["set_id"],
            "ticker": o["ticker"],
            "order_record_hash": h,
            "recorded_at": _stamp(now),
        }
        qs = quotes_of(recs, o["symbol"])
        en = x["entry"]
        if en is None:
            fill = next(
                (
                    q
                    for q in qs
                    if o["decision_quote_at"] <= q["observed_at"] <= o["valid_until"]
                    and q["ask"] <= o["limit"]
                ),
                None,
            )
            if fill is not None:
                en = {
                    "type": ENTRY,
                    **base,
                    "status": "FILLED",
                    "price": fill["ask"],
                    "shares": o["quantity"],
                    "cost_in": FEE,
                    "stop": fill["ask"] * (1 - MAX_STOP),
                    "filled_at": fill["observed_at"],
                    "quote_record_hash": fill["record_hash"],
                    "deadline": _stamp(_t(fill["observed_at"]) + HOLD),
                }
                out.append(en)
            elif now > _t(o["valid_until"]):
                out.append(
                    {
                        "type": ENTRY,
                        **base,
                        "status": "EXPIRED_UNFILLED",
                        "reason": f"no recorded ask at or below {o['limit']:g} before {o['valid_until']}",
                    }
                )
                continue
            else:
                continue
        if en["status"] != "FILLED":
            continue
        for q in qs:
            if q["observed_at"] <= en["filled_at"]:
                continue
            why = (
                "STOP"
                if q["bid"] <= en["stop"]
                else "TIME_EXIT"
                if q["observed_at"] >= en["deadline"]
                else None
            )
            if why:
                proceeds = en["shares"] * q["bid"] * (1 - FEE)
                out.append(
                    {
                        "type": EXIT,
                        **base,
                        "exit_reason": why,
                        "price": q["bid"],
                        "cost_out": FEE,
                        "exited_at": q["observed_at"],
                        "exit_session": q["observed_at"],
                        "quote_record_hash": q["record_hash"],
                        "net_pnl_usd": round(proceeds - stock.cost_basis(en), 8),
                        "net_return": proceeds / stock.cost_basis(en) - 1,
                    }
                )
                break
    return out


def mark(recs: list[dict], now: datetime) -> dict:
    st = account(recs)
    return {
        "type": MARK,
        "account": ACCOUNT_ID,
        "arm": ARM,
        "session": _stamp(now),
        **{
            k: round(st[k], 2)
            for k in ("cash", "reserved", "open_value", "equity", "realized", "unrealized")
        },
        "open_positions": [{**p, "value": round(p["value"], 2)} for p in st["open"]],
        "made_at": _stamp(now),
    }


def symbols_needed(recs: list[dict], cands: list[dict]) -> list[str]:
    """Coins with a pending order, an open position, or an undecided buy decision."""
    out = {
        symbol_of(d)
        for d in cands
        if d["decision"].upper().startswith("BUY")
        and d["decision_id"]
        not in {r["decision_id"] for r in recs if r["type"] in (ORDER, DECLINE)}
    }
    for x in stock.orders_of(recs, ARM).values():
        if (
            x["cancel"] is None
            and x["exit"] is None
            and (x["entry"] is None or x["entry"]["status"] == "FILLED")
        ):
            out.add(x["order"]["symbol"])
    return sorted(out)


def step(recs: list[dict], cands: list[dict], now: datetime) -> list[dict]:
    """After the quotes are recorded: fills and exits, then the decisions. The mark is taken from the ledger
    after these are written (mark()), so it always includes tonight's reservations."""
    new = settle(recs, now)
    return new + decide(recs + new, cands, now)


# ---------------------------------------------------------------------------------------- report
def render(recs: list[dict]) -> str:
    st = account(recs)
    book = stock.orders_of(recs, ARM)
    as_of = max(
        (r.get("made_at") or r.get("recorded_at") or r.get("observed_at") or "" for r in recs),
        default="no records yet",
    )
    out = [
        "# KOD crypto spot paper account (CRYPTO_ACCOUNT_v1)",
        "",
        (
            f"As of the latest record ({as_of}). Paper only: no orders, no money. "
            "Protocol: `research/CRYPTO_ACCOUNT_v1/protocol.json`."
        ),
        "",
        (
            f"- **Rules:** {START_CASH:,.0f} USDT; {RISK_FRACTION:.1%} planned loss per position, "
            f"{MAX_PLANNED_RISK:.1%} in total, {MAX_NEW_PER_DAY} new orders per UTC day, no leverage; buys only what "
            f"the frozen crypto policy decides to buy; limit {CHASE:.0%} above the policy's quote, valid "
            f"{ORDER_VALID}; fills at a recorded ask, exits at a recorded bid; stop {MAX_STOP:.0%} below the fill; "
            f"time exit after {HOLD.days} days; fee {FEE:.2%} per side."
        ),
        "",
        "| Cash | Reserved | Available | Open value | Equity | Realized | Unrealized |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        "| "
        + " | ".join(
            f"{st[k]:,.2f}"
            for k in (
                "cash",
                "reserved",
                "free_cash",
                "open_value",
                "equity",
                "realized",
                "unrealized",
            )
        )
        + " |",
        "",
        "## Open positions",
        "",
    ]
    out += [
        f"- {p['symbol']}: {p['quantity']:g} valued {p['value']:,.2f} USDT at the bid recorded "
        f"{p['valued_at'] or '(none: carried at entry price)'}"
        for p in st["open"]
    ] or ["- None."]
    out += [
        "",
        "## Every decision",
        "",
        "| Decided | Coin | Policy | Account | Fill | Exit | Net P&L |",
        "|---|---|---|---|---|---|---:|",
    ]
    for r in recs:
        if r["type"] == DECLINE:
            out.append(
                f"| {r['made_at']} | {r['symbol']} | {r['policy_decision']} | declined: "
                f"{r['reason'][:140]} | - | - | - |"
            )
        elif r["type"] == ORDER:
            x = book[r["record_hash"]]
            en, ex = x["entry"], x["exit"]
            fill = (
                "cancelled"
                if x["cancel"]
                else "pending"
                if en is None
                else f"{en['status']} @ {en['price']:g}"
                if en["status"] == "FILLED"
                else en["status"]
            )
            out.append(
                f"| {r['made_at']} | {r['symbol']} | {r['policy_decision']} | {r['order']} | {fill} | "
                + (
                    f"{ex['exit_reason']} @ {ex['price']:g} | {ex['net_pnl_usd']:+,.2f} |"
                    if ex
                    else "- | - |"
                )
            )
    return "\n".join(out) + "\n"


def write_report():
    REPORT.write_text(render(lines()), encoding="utf-8")
    return REPORT


def verify() -> list[str]:
    if not LEDGER.exists():
        return []
    problems = [f"crypto_account.jsonl: {p}" for p in paper.verify_chain(LEDGER)]
    recs = lines()
    by_hash = {r["record_hash"]: r for r in recs}
    decided, followed = set(), set()
    for r in recs:
        if r["type"] in (ORDER, DECLINE):
            if r["decision_id"] in decided:
                problems.append(f"{r['decision_id']}: decided twice")
            decided.add(r["decision_id"])
        if r["type"] == ORDER:
            q = by_hash.get(r["decision_quote_record_hash"])
            if q is None or q["type"] != QUOTE or q["symbol"] != r["symbol"]:
                problems.append(f"{r['decision_id']}: order does not point at its quote")
        if r["type"] in (ENTRY, EXIT, CANCEL):
            o = by_hash.get(r["order_record_hash"])
            if o is None or o["type"] != ORDER:
                problems.append(f"{r['set_id']}: {r['type']} does not point at its order")
                continue
            if (r["order_record_hash"], r["type"]) in followed:
                problems.append(f"{r['set_id']}: {r['type']} recorded twice")
            followed.add((r["order_record_hash"], r["type"]))
            if r["type"] == CANCEL and r["made_at"] >= o["valid_until"]:
                problems.append(f"{r['set_id']}: cancelled after the order expired")
            if r.get("status") == "FILLED" or r["type"] == EXIT:
                q = by_hash.get(r["quote_record_hash"])
                if q is None or q["type"] != QUOTE or q["symbol"] != o["symbol"]:
                    problems.append(
                        f"{r['set_id']}: {r['type']} does not point at a recorded quote"
                    )
                elif r["type"] == ENTRY and not (
                    q["ask"] == r["price"]
                    and q["ask"] <= o["limit"]
                    and o["decision_quote_at"] <= q["observed_at"] <= o["valid_until"]
                ):
                    problems.append(f"{r['set_id']}: fill not at a qualifying recorded ask")
                elif r["type"] == EXIT and q["bid"] != r["price"]:
                    problems.append(f"{r['set_id']}: exit not at the recorded bid")
    return problems
