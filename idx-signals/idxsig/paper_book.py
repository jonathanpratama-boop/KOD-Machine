"""PAPER_BOOK_v1: KOD trading US +30% spikes on its own, on paper (research/PAPER_BOOK_v1/protocol.json).

Owner (2026-10-31): "set it up ... I just want to see how effective it is to trade on its own. Perhaps it needs my
help to confirm sometimes. But I want this to be a money making machine."

Every night, after LEARNER v2.4 has sealed its forecast for each US spike (learner3-forecast), the book seals a
PLAN for that spike before the next session opens: DONT_BUY when v2.4's raw next-day dump probability is at or
above the frozen cutoff, BUY_OK otherwise. The owner may add a CONFIRM (BUY or SKIP) before the same cutoff.
When the Speculation Register resolves the spike's BASE5 window (buy at the next open, sell at the close five
sessions later, the profile's costs), the book records that trade's net return as a RESULT. No price is fetched
here and nothing is ever bought: the trade is the register's.

Four books, $1,000 per position:
  KOD      every BUY_OK spike (the machine on its own)
  ALL      every spike (what buying without KOD does)
  AVOIDED  every DONT_BUY spike (what KOD's filter kept you out of)
  OWNER    every spike the owner confirmed BUY

Records live in paper/paper_book.jsonl (hash chain, RFC 3161 stamped). Nothing is edited; a correction is a new line.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from . import learner3, paper, speculation
from .provenance import utc_stamp

LEDGER = paper.PAPER / "paper_book.jsonl"
REPORT = paper.PAPER / "PAPER_BOOK.md"
PLAN, CONFIRM, RESULT = "BOOK_PLAN", "BOOK_CONFIRM", "BOOK_RESULT"
BOOK_ID = "PAPER_BOOK_v1"

CUTOFF = (
    0.4626  # mean of the two replay periods' top-third cutoffs (FILTER_BUY_v1: 0.4486 and 0.4768)
)
FIRST_SIGNAL = (
    "2026-10-30"  # the first night still before its entry cutoff when the book was frozen
)
POSITION = 1000.0
LOOK_TRADES, LOOK_MIN_GROUP = (
    300,
    50,
)  # the one planned look: the first 300 traded spikes, each side >= 50
SEED, DRAWS = 20261031, 2000
BOOKS = ("KOD", "ALL", "AVOIDED", "OWNER")


def lines() -> list[dict]:
    return paper.ledger_lines(LEDGER) if LEDGER.exists() else []


def _plans(recs: list[dict]) -> dict[str, dict]:
    return {r["set_id"]: r for r in recs if r["type"] == PLAN}


def plan_records(now: datetime) -> list[dict]:
    """A PLAN for every v2.4 forecast on or after FIRST_SIGNAL that has none yet and is still before its cutoff."""
    have = _plans(lines())
    out = []
    for f in paper.ledger_lines(learner3.LEDGER):
        if (
            f["type"] != "LEARNER3_FORECAST"
            or f["signal_session"] < FIRST_SIGNAL
            or f["set_id"] in have
        ):
            continue
        if now >= datetime.fromisoformat(f["entry_cutoff"].replace("Z", "+00:00")):
            continue
        raw = float(f["forecasts"]["NEXT_DUMP10_1"]["raw"])
        out.append(
            {
                "type": PLAN,
                "book": BOOK_ID,
                "set_id": f["set_id"],
                "ticker": f["ticker"],
                "signal_session": f["signal_session"],
                "entry_cutoff": f["entry_cutoff"],
                "dump_tomorrow": raw,
                "cutoff": CUTOFF,
                "verdict": "DONT_BUY" if raw >= CUTOFF else "BUY_OK",
                "forecast_record_hash": f["record_hash"],
                "made_at": utc_stamp(),
            }
        )
    return out


def confirm_record(ticker: str, decision: str, now: datetime) -> dict:
    """The owner's BUY or SKIP for tonight's planned spike in `ticker`, refused once that spike's cutoff passed."""
    if decision not in ("BUY", "SKIP"):
        raise ValueError("decision is BUY or SKIP")
    recs = lines()
    open_plans = [
        p
        for p in _plans(recs).values()
        if p["ticker"] == ticker.upper()
        and now < datetime.fromisoformat(p["entry_cutoff"].replace("Z", "+00:00"))
    ]
    if not open_plans:
        raise ValueError(f"no planned {ticker.upper()} spike is still before its entry cutoff")
    p = max(open_plans, key=lambda r: r["signal_session"])
    return {
        "type": CONFIRM,
        "book": BOOK_ID,
        "set_id": p["set_id"],
        "ticker": p["ticker"],
        "decision": decision,
        "plan_record_hash": p["record_hash"],
        "made_at": utc_stamp(),
    }


def result_records() -> list[dict]:
    """A RESULT for every planned spike whose BASE5 window the Speculation Register has resolved."""
    recs = lines()
    done = {r["set_id"] for r in recs if r["type"] == RESULT}
    base5 = {
        r["set_id"]: r
        for r in paper.latest_resolutions(speculation.spec_lines()).values()
        if r.get("window") == "BASE5"
    }
    out = []
    for sid, p in _plans(recs).items():
        r = base5.get(sid)
        if sid in done or r is None:
            continue
        trade = (r.get("candidate") or {}).get("trade") if r.get("status") == "RESOLVED" else None
        out.append(
            {
                "type": RESULT,
                "book": BOOK_ID,
                "set_id": sid,
                "ticker": p["ticker"],
                "status": "TRADED"
                if trade
                else (r.get("candidate") or {}).get("status") or r.get("status"),
                "reason": None
                if trade
                else (r.get("candidate") or {}).get("reason") or r.get("reason"),
                "net_return": trade["net_return"] if trade else None,
                "entry_session": trade["entry_session"] if trade else None,
                "exit_session": trade["exit_session"] if trade else None,
                "plan_record_hash": p["record_hash"],
                "resolution_record_hash": r.get("record_hash"),
                "resolved_at": utc_stamp(),
            }
        )
    return out


def trades(recs: list[dict] | None = None) -> list[dict]:
    """One row per planned spike: verdict, owner decision (latest valid CONFIRM), net return once traded."""
    recs = lines() if recs is None else recs
    plans = _plans(recs)
    owner, results = {}, {}
    for r in recs:
        if r["type"] == CONFIRM and r["made_at"] < plans[r["set_id"]]["entry_cutoff"]:
            owner[r["set_id"]] = r["decision"]
        elif r["type"] == RESULT:
            results[r["set_id"]] = r
    rows = []
    for sid, p in sorted(plans.items(), key=lambda kv: (kv[1]["signal_session"], kv[0])):
        res = results.get(sid)
        rows.append(
            {
                "set_id": sid,
                "ticker": p["ticker"],
                "session": p["signal_session"],
                "dump_tomorrow": p["dump_tomorrow"],
                "verdict": p["verdict"],
                "owner": owner.get(sid),
                "status": res["status"] if res else "OPEN",
                "net": res["net_return"] if res and res["status"] == "TRADED" else None,
            }
        )
    return rows


def in_book(row: dict, book: str) -> bool:
    return {
        "KOD": row["verdict"] == "BUY_OK",
        "ALL": True,
        "AVOIDED": row["verdict"] == "DONT_BUY",
        "OWNER": row["owner"] == "BUY",
    }[book]


def book_summary(rows: list[dict], book: str) -> dict:
    mine = [r for r in rows if in_book(r, book)]
    closed = [r["net"] for r in mine if r["net"] is not None]
    return {
        "positions": len(mine),
        "open": sum(r["status"] == "OPEN" for r in mine),
        "closed": len(closed),
        "wins": sum(n > 0 for n in closed),
        "pnl": POSITION * sum(closed),
        "average": float(np.mean(closed)) if closed else None,
    }


def _bootstrap(rows: list[dict], stat) -> tuple[float, float, float]:
    """stat(rows) and its one-sided 5% and 95% bounds, resampling signal sessions."""
    by_session: dict[str, list[dict]] = {}
    for r in rows:
        by_session.setdefault(r["session"], []).append(r)
    groups = list(by_session.values())
    rng = np.random.default_rng(SEED)
    draws = []
    for _ in range(DRAWS):
        pick = [x for i in rng.integers(0, len(groups), len(groups)) for x in groups[i]]
        v = stat(pick)
        if v is not None:
            draws.append(v)
    return stat(rows), float(np.quantile(draws, 0.05)), float(np.quantile(draws, 0.95))


def _mean(rows, verdict):
    v = [r["net"] for r in rows if r["verdict"] == verdict]
    return float(np.mean(v)) if v else None


def planned_look(rows: list[dict]) -> dict | None:
    """The one planned look on the first LOOK_TRADES traded spikes in signal order; None until it is reached."""
    traded = [r for r in rows if r["net"] is not None][:LOOK_TRADES]
    n_dont = sum(r["verdict"] == "DONT_BUY" for r in traded)
    if len(traded) < LOOK_TRADES or min(n_dont, len(traded) - n_dont) < LOOK_MIN_GROUP:
        return None

    def gap(rs):
        a, b = _mean(rs, "DONT_BUY"), _mean(rs, "BUY_OK")
        return None if a is None or b is None else a - b

    d, _, d_hi = _bootstrap(traded, gap)
    k, k_lo, _ = _bootstrap(traded, lambda rs: _mean(rs, "BUY_OK"))
    return {
        "trades": len(traded),
        "dont_buy": n_dont,
        "dont_buy_minus_buy_ok": d,
        "upper_95": d_hi,
        "dont_buy_works": d < 0 and d_hi < 0,
        "kod_book_mean": k,
        "lower_95": k_lo,
        "kod_makes_money": k > 0 and k_lo > 0,
    }


def render(rows: list[dict]) -> str:
    sums = {b: book_summary(rows, b) for b in BOOKS}
    look = planned_look(rows)
    traded = sum(r["net"] is not None for r in rows)

    def money(x):
        return f"${x:+,.0f}"

    out = [
        "# KOD paper book (PAPER_BOOK_v1)",
        "",
        f"Generated {utc_stamp()}. Paper only: no orders, no money. Protocol: `research/PAPER_BOOK_v1/protocol.json`.",
        "",
        "## The three plain answers",
        "",
        f"- **What does it do?** For every US stock that just closed +30%, KOD says DONT_BUY when its dump-tomorrow "
        f"probability is {CUTOFF:.2f} or more, otherwise BUY_OK. The KOD book buys every BUY_OK at the next open and "
        "sells five sessions later; $1,000 a position, real costs.",
        f"- **Evidence so far?** {len(rows)} spikes planned, {traded} trades closed. "
        + (
            "The planned look is reached: see below."
            if look
            else f"The verdict waits for the planned look at {LOOK_TRADES} closed trades; until then the numbers are a running tally."
        ),
        "- **What counts as success?** Two separate questions, each at the planned look: DONT_BUY works if the "
        "skipped spikes do worse than the bought ones (95% bound below zero); the KOD book makes money if its "
        "average trade is above zero (95% bound above zero).",
        "",
        "## The books",
        "",
        "| Book | What it holds | Positions | Open | Closed | Wins | P&L | Average trade |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    what = {
        "KOD": "every BUY_OK",
        "ALL": "every spike",
        "AVOIDED": "every DONT_BUY (kept out)",
        "OWNER": "spikes you confirmed BUY",
    }
    for b in BOOKS:
        s = sums[b]
        avg = f"{s['average']:+.2%}" if s["average"] is not None else "-"
        out.append(
            f"| {b} | {what[b]} | {s['positions']} | {s['open']} | {s['closed']} | {s['wins']} | "
            f"{money(s['pnl'])} | {avg} |"
        )
    if look:
        out += [
            "",
            "## Planned look",
            "",
            f"- DONT_BUY minus BUY_OK: {look['dont_buy_minus_buy_ok']:+.2%} (upper 95% {look['upper_95']:+.2%}): "
            + ("**DONT_BUY WORKS**" if look["dont_buy_works"] else "**DONT_BUY NOT SHOWN**"),
            f"- KOD book average: {look['kod_book_mean']:+.2%} (lower 95% {look['lower_95']:+.2%}): "
            + ("**MAKES MONEY**" if look["kod_makes_money"] else "**DOES NOT MAKE MONEY**"),
        ]
    out += [
        "",
        "## Every spike",
        "",
        "| Signal | Ticker | Dump tomorrow | KOD | You | Status | Net |",
        "|---|---|---:|---|---|---|---:|",
    ]
    for r in reversed(rows):
        net = f"{r['net']:+.2%}" if r["net"] is not None else "-"
        out.append(
            f"| {r['session']} | {r['ticker']} | {r['dump_tomorrow']:.2f} | {r['verdict']} | "
            f"{r['owner'] or '-'} | {r['status']} | {net} |"
        )
    return "\n".join(out) + "\n"


def write_report():
    REPORT.write_text(render(trades()), encoding="utf-8")
    return REPORT


def verify() -> list[str]:
    if not LEDGER.exists():
        return []
    problems = [f"paper_book.jsonl: {p}" for p in paper.verify_chain(LEDGER)]
    recs = lines()
    by_hash = {r["record_hash"]: r for r in recs}
    forecasts = (
        {f["record_hash"]: f for f in paper.ledger_lines(learner3.LEDGER)}
        if learner3.LEDGER.exists()
        else {}
    )
    plans: dict[str, dict] = {}
    results = set()
    for r in recs:
        sid = r["set_id"]
        if r["type"] == PLAN:
            if sid in plans:
                problems.append(f"{sid}: planned twice")
            plans[sid] = r
            if r["made_at"] >= r["entry_cutoff"]:
                problems.append(f"{sid}: planned after its entry cutoff")
            f = forecasts.get(r["forecast_record_hash"])
            if f is None or f["set_id"] != sid:
                problems.append(f"{sid}: plan does not point at its v2.4 forecast")
        elif r["type"] in (CONFIRM, RESULT):
            p = by_hash.get(r["plan_record_hash"])
            if p is None or p["set_id"] != sid:
                problems.append(f"{sid}: {r['type']} does not point at its plan")
            if r["type"] == RESULT:
                if sid in results:
                    problems.append(f"{sid}: resulted twice")
                results.add(sid)
    return problems
