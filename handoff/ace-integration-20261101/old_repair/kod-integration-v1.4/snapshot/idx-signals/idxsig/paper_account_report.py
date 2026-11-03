"""The PAPER_ACCOUNT_v1 report, rendered from the ledger as it stands (paper/PAPER_ACCOUNT.md).

Kept apart from idxsig/paper_account.py, whose bytes the frozen protocol pins: a display repair here cannot
change the account's rules. The first report took balances from the night's ACCT_MARK, written before that
night's orders, so pending orders could appear beside "$0 reserved". This renderer instead:

  * computes cash, reservations, free cash, open positions and realized P&L with paper_account.account_state
    over every current record (orders, cancels, entries and exits included);
  * values open positions at the latest recorded mark (ACCT_MARK), naming that mark's session, and flags any
    position without one as carried at its entry price;
  * reports drawdown from the recorded marks only, with the session of the trough.

It reads the ledger and writes the report; it never appends a record. Identical records give identical output.
"""

from __future__ import annotations

from . import paper_account as acct

REPORT = acct.REPORT


def latest_marks(recs: list[dict], arm: str) -> tuple[dict[str, float], str | None]:
    """order hash -> return since entry from the latest ACCT_MARK of the arm, and that mark's session."""
    marks = [r for r in recs if r["type"] == acct.MARK and r["arm"] == arm]
    if not marks:
        return {}, None
    last = marks[-1]
    got = {
        p["order_record_hash"]: p["mark_return"]
        for p in last["open_positions"]
        if p.get("mark_return") is not None
    }
    return got, last["session"]


def drawdown(recs: list[dict], arm: str) -> tuple[float, str | None]:
    """Worst equity fall from a running peak across the recorded marks, and the session of that trough."""
    peak, worst, when = acct.START_CASH, 0.0, None
    for r in recs:
        if r["type"] == acct.MARK and r["arm"] == arm:
            peak = max(peak, r["equity"])
            fall = r["equity"] / peak - 1
            if fall < worst:
                worst, when = fall, r["session"]
    return worst, when


def summary(recs: list[dict], arm: str) -> dict:
    marks, marked_on = latest_marks(recs, arm)
    st = acct.account_state(recs, arm, marks)
    book = acct.orders_of(recs, arm)
    entries = [x["entry"] for x in book.values() if x["entry"]]
    worst, trough = drawdown(recs, arm)
    return {
        **{
            k: st[k]
            for k in (
                "cash",
                "reserved",
                "free_cash",
                "open_value",
                "equity",
                "realized",
                "unrealized",
            )
        },
        "valued_at": marked_on,
        "open": st["open"],
        "pending": sum(1 for x in book.values() if x["entry"] is None and x["cancel"] is None),
        "cancelled": sum(1 for x in book.values() if x["cancel"] is not None),
        "filled": sum(e["status"] == "FILLED" for e in entries),
        "rejected": sum(e["status"] != "FILLED" for e in entries),
        "declined": sum(1 for r in recs if r["type"] == acct.DECLINE and r["arm"] == arm),
        "closed": sum(1 for x in book.values() if x["exit"] is not None),
        "drawdown": worst,
        "drawdown_session": trough,
        "marks": sum(1 for r in recs if r["type"] == acct.MARK and r["arm"] == arm),
    }


def _money(x: float) -> str:
    return f"-${-x:,.2f}" if x < -0.005 else f"${abs(x):,.2f}"


def _decision_rows(recs: list[dict], arm: str) -> list[str]:
    book = acct.orders_of(recs, arm)
    rows = []
    for r in recs:
        if r.get("arm") != arm or r["type"] not in (acct.ORDER, acct.DECLINE):
            continue
        head = f"| {r['signal_session']} | {r['ticker']} | {arm} | {r['source']} |"
        if r["type"] == acct.DECLINE:
            rows.append(f"{head} declined: {r['reason']} | - | - | - |")
            continue
        x, p = book[r["record_hash"]], r["plan"]
        decision = (
            f"order {p['shares']} @ <= {p['max_entry']:g}, reserved {_money(r['reserved_usd'])}"
        )
        if x["cancel"]:
            entry = "cancelled by you before the open"
        elif x["entry"] is None:
            entry = f"pending: next open (before {r['entry_cutoff']})"
        elif x["entry"]["status"] != "FILLED":
            entry = f"{x['entry']['status']}: {x['entry']['reason']}"
        else:
            en = x["entry"]
            entry = f"filled {en['shares']} @ {en['price']:.4g} on {en['entry_session']}, stop {en['stop']:.4g}"
        ex = x["exit"]
        exit_ = f"{ex['exit_reason']} {ex['exit_session']} @ {ex['price']:.4g}" if ex else "-"
        pnl = _money(ex["net_pnl_usd"]) if ex else "-"
        rows.append(f"{head} {decision} | {entry} | {exit_} | {pnl} |")
    return rows


def render(recs: list[dict]) -> str:
    as_of = max(
        (r.get("made_at") or r.get("recorded_at") or "" for r in recs), default="no records yet"
    )
    sums = {arm: summary(recs, arm) for arm in acct.ARMS}
    out = [
        "# KOD paper account (PAPER_ACCOUNT_v1)",
        "",
        (
            f"As of the latest record ({as_of}). Paper only: no orders, no money. "
            "Protocol: `research/PAPER_ACCOUNT_v1/protocol.json`."
        ),
        "",
        "## The three plain answers",
        "",
        (
            "- **What does it do?** It takes KOD's BUY_OK spikes (and the ones you confirm) through the real "
            f"execution rules with one shared ${acct.START_CASH:,.0f} account per arm: "
            f"{acct.RISK_FRACTION:.1%} planned loss per position, {acct.MAX_PLANNED_RISK:.1%} for everything at "
            f"once, at most {acct.MAX_NEW_PER_SESSION} new orders per session, no leverage. An order fills only at "
            "the next opening print inside its limit; stops and the five-session time exit come from the bars."
        ),
        (
            "- **How to read the money:** cash is what the account holds; reserved is cash set aside for orders "
            "waiting for the next open (not spent, not lost, just unavailable to another order); available = cash "
            "minus reserved. Equity = cash plus open positions at their latest recorded price. Realized P&L counts "
            "only closed trades."
        ),
        (
            "- **Two stops side by side:** BASE uses the spike day's low (the existing contract); FIXED5 puts the "
            "stop 5% below the fill. Same candidates, costs and exits. Each arm is a separate simulated account."
        ),
        "",
        "## Accounts",
        "",
        "| Arm | Cash | Reserved | Available | Open value | Equity | Realized | Unrealized | Pending | Filled | Rejected | Cancelled | Declined | Closed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, s in sums.items():
        out.append(
            f"| {arm} | {_money(s['cash'])} | {_money(s['reserved'])} | {_money(s['free_cash'])} | "
            f"{_money(s['open_value'])} | {_money(s['equity'])} | {_money(s['realized'])} | "
            f"{_money(s['unrealized'])} | {s['pending']} | {s['filled']} | {s['rejected']} | {s['cancelled']} | "
            f"{s['declined']} | {s['closed']} |"
        )
    out += ["", "## Open positions and valuation", ""]
    any_open = False
    for arm, s in sums.items():
        for p in s["open"]:
            any_open = True
            if p["mark_return"] is None:
                how = "**no recorded valuation: carried at its entry price**"
            else:
                how = (
                    f"valued at the close of {s['valued_at']} ({p['mark_return']:+.2%} since entry)"
                )
            out.append(f"- {arm} {p['ticker']}: {_money(p['value'])}, {how}")
    if not any_open:
        out.append("- No open positions.")
    out += ["", "## Drawdown (from recorded nightly marks only)", ""]
    for arm, s in sums.items():
        where = f", trough at the close of {s['drawdown_session']}" if s["drawdown_session"] else ""
        out.append(f"- {arm}: {s['drawdown']:.2%} across {s['marks']} mark(s){where}")
    out += [
        "",
        "## Every decision",
        "",
        "| Signal | Ticker | Arm | Source | Decision | Entry | Exit | Net P&L |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    for arm in acct.ARMS:
        out += _decision_rows(recs, arm)
    return "\n".join(out) + "\n"


def write_report():
    REPORT.write_text(render(acct.lines()), encoding="utf-8")
    return REPORT
