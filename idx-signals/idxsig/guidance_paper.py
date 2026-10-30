"""Forward paper test of E10's event: full-year revenue guidance raises, decided before the entry, never traded.

GUIDANCE-PAPER-v1 (draft until E10 passes). It writes to its own hash-chained ledger, paper/guidance/ledger.jsonl,
through paper.append, and refuses to write anything unless research/E10/results/RESULT.json records verdict PASS;
before that it only dry-runs. No order is ever placed.

Universe: eToro-listed US stocks (the broker the owner can use) that map to an SEC CIK. Each scanned day:
  1. the EDGAR daily form index -> 8-K / 8-K/A rows of universe CIKs;
  2. each full submission -> header items; Item 2.02 releases keep their EX-99 texts and acceptance time;
  3. guidance_watch.revisions against each issuer's state (latest guidance per fiscal year and kind);
  4. a RAISE -> DECISION: buy at the open of the first session it could be traded on (accepted by 09:15 New York
     time on a session day: that session; otherwise the next), sell at the close of the 20th session; 10% of a
     USD 10,000 paper account, at most 10 open positions, E10 cost tiers plus USD 2 per order. The price and
     liquidity floor of E10 (as-traded entry >= USD 2, 20-session median traded value >= USD 500k) is checked when
     the decision is scored, from the bars, and a decision that fails it is scored NOT EXECUTABLE.
The state is bootstrapped from the releases of the 200 days before the first scanned day (MAX_GAP_DAYS).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from idxsig import guidance, guidance_watch
from idxsig.paper import PKG_ROOT, append

DIR = PKG_ROOT / "paper" / "guidance"
LEDGER = DIR / "ledger.jsonl"
STATE = DIR / "state.json"
E10_RESULT = PKG_ROOT / "research" / "E10" / "results" / "RESULT.json"
ETORO = PKG_ROOT / "data" / "raw" / "etoro" / "20261016T190421Z" / "instruments.json"
ARCHIVES = "https://www.sec.gov/Archives/"


@dataclass(frozen=True)
class Policy:
    policy_id: str = "GUIDANCE-PAPER-v1"
    event: str = "full-year revenue guidance RAISE (idxsig.guidance_v2, research/E10/FEASIBILITY_AMENDMENT_1.md)"
    entry: str = (
        "open of the first session tradable after acceptance (by 09:15 New York time: that session)"
    )
    exit: str = "close of the 20th session (entry session = 1)"
    equity_usd: float = 10_000.0
    weight: float = 0.10
    slots: int = 10
    commission_usd: float = 2.0
    cost_tiers_per_side: tuple = ((1, 0.015), (5, 0.005), (20, 0.0015), (float("inf"), 0.0005))
    sec_fee_on_sales: float = 0.0000278
    floor: str = "as-traded entry open >= USD 2 and 20-session median traded value >= USD 500k, checked at scoring"
    orders: str = "none: paper only"


POLICY = Policy()


def policy_sha() -> str:
    return hashlib.sha256(
        json.dumps(asdict(POLICY), sort_keys=True, default=str).encode()
    ).hexdigest()


def e10_passed(path: Path = E10_RESULT) -> bool:
    """True only if E10's single recorded run exists and its verdict is PASS."""
    try:
        return json.loads(path.read_text()).get("verdict") == "PASS"
    except (OSError, ValueError):
        return False


def etoro_us(path: Path = ETORO) -> set[str]:
    data = json.loads(path.read_bytes())["InstrumentDisplayDatas"]
    return {
        str(x["SymbolFull"]).upper().replace(".", "-")
        for x in data
        if x["InstrumentTypeID"] == 5
        and x["ExchangeID"] in (4, 5)
        and not x.get("IsInternalInstrument")
    }


def index_url(day: date) -> str:
    return f"{ARCHIVES}edgar/daily-index/{day.year}/QTR{(day.month - 1) // 3 + 1}/form.{day:%Y%m%d}.idx"


def acceptance_ny(raw: bytes) -> str | None:
    a = guidance.acceptance(raw)
    return datetime.strptime(a, "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%S") if a else None


def releases_on(
    day: date, get: Callable[[str], tuple[int, bytes]], ciks: dict[int, str]
) -> list[dict]:
    """Item 2.02 releases of universe CIKs in the day's form index, in acceptance order. `get(url)` returns
    (status, body); a day without an index (weekend, holiday) returns []."""
    status, body = get(index_url(day))
    if status != 200:
        return []
    out = []
    for row in guidance_watch.form_index_8k(body.decode("latin-1")):
        if row["cik"] not in ciks:
            continue
        s, raw = get(ARCHIVES + row["path"])
        if s != 200 or "2.02" not in guidance_watch.header_items(raw):
            continue
        acc = acceptance_ny(raw)
        if acc is None:
            continue
        out.append(
            {
                "cik": row["cik"],
                "ticker": ciks[row["cik"]],
                "form": row["form"],
                "accession": row["path"].rsplit("/", 1)[-1].removesuffix(".txt"),
                "acceptance_ny": acc,
                "url": ARCHIVES + row["path"],
                "sha256": hashlib.sha256(raw).hexdigest(),
                "texts": guidance.exhibit_texts(raw),
            }
        )
    return sorted(out, key=lambda r: r["acceptance_ny"])


def decision(event: dict, release: dict, now: datetime) -> dict:
    return {
        "type": "DECISION",
        "policy": {"id": POLICY.policy_id, "sha256": policy_sha()},
        "decided_at": now.isoformat(timespec="seconds"),
        "market": "US",
        "ticker": event["ticker"],
        "cik": event["cik"],
        "accession": event["accession"],
        "filing_url": release["url"],
        "filing_sha256": release["sha256"],
        "acceptance_ny": event["acceptance_ny"],
        "event": {
            k: event[k]
            for k in (
                "fiscal_year",
                "kind",
                "old_mid",
                "new_mid",
                "level_change",
                "class",
                "prior_accession",
                "old_sentence",
                "new_sentence",
            )
        },
        "terminal_decision": "BUY ON TRIGGER",
        "entry": POLICY.entry,
        "exit": POLICY.exit,
        "sizing": f"{POLICY.weight:.0%} of marked paper equity, at most {POLICY.slots} open positions",
        "floor": POLICY.floor,
        "orders": POLICY.orders,
        "thesis": "a raised full-year revenue forecast leaves return after an obtainable entry (E10)",
        "prediction": "net return over the 20 sessions beats the mean of matched controls on the same dates",
    }


def scan_day(
    day: date, state: dict, get, ciks: dict[int, str], now: datetime | None = None
) -> tuple[list, list, dict]:
    """(decisions, every event, new state) for one day. Pure apart from `get`."""
    now = now or datetime.now(timezone.utc)
    decisions, events = [], []
    for rel in releases_on(day, get, ciks):
        ev, state = guidance_watch.revisions(
            state, rel["cik"], rel["ticker"], rel["accession"], rel["acceptance_ny"], rel["texts"]
        )
        events.extend(ev)
        decisions.extend(decision(e, rel, now) for e in ev if e["class"] == "RAISE")
    return decisions, events, state


def bootstrap(first_day: date, get, ciks: dict[int, str], log=print) -> dict:
    """State from the releases of the MAX_GAP_DAYS days before `first_day` (no decisions)."""
    state: dict = {}
    for k in range(guidance.MAX_GAP_DAYS, 0, -1):
        day = first_day - timedelta(days=k)
        if day.weekday() < 5:
            _, _, state = scan_day(day, state, get, ciks)
            if k % 20 == 0:
                log(f"bootstrap {day}: {len(state)} guidance keys")
    return state


def record(
    decisions: list[dict],
    events: list[dict],
    day: date,
    now: datetime,
    dry_run: bool,
    path: Path = LEDGER,
    timestamper=None,
) -> list[dict]:
    """A SCAN record (every event of the day, or NO SIGNAL) and the day's DECISIONs. Written only if E10 passed."""
    scan = {
        "type": "SCAN",
        "policy": {"id": POLICY.policy_id, "sha256": policy_sha()},
        "market": "US",
        "session_scanned": day.isoformat(),
        "scanned_at": now.isoformat(timespec="seconds"),
        "events": [
            {
                k: e[k]
                for k in ("ticker", "accession", "class", "level_change", "fiscal_year", "kind")
            }
            for e in events
        ]
        or "NO SIGNAL",
    }
    records = [scan] + decisions
    if dry_run:
        return records
    if not e10_passed():
        raise SystemExit("refused: E10 has no PASS verdict; GUIDANCE-PAPER-v1 can only dry-run")
    path.parent.mkdir(parents=True, exist_ok=True)
    return append(records, path=path, timestamper=timestamper)


def save_state(state: dict, path: Path = STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, sort_keys=True, indent=0) + "\n")


def load_state(path: Path = STATE) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}
