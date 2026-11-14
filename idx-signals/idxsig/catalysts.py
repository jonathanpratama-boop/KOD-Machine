"""Catalyst Register v1 (research/CATALYST_REGISTER_v1/PROTOCOL.md). Paper only, no orders.

The Speculation Register run over dated event lists instead of scan candidates: for every event of a catalyst
family whose direction is set by its mechanism, seal, before the entry, a cone of dated statements, a frozen
yardstick plan, five matched twins and a coverage class (FIRE or ABSTAIN under a pre-registered rule); grade
them when the future arrives.

  BATCH          one per read of a family's source: every event seen, with its status (SEALED or a SKIP reason)
                 and the inputs' sha256, so a missing event is a recorded gap and never a quiet omission.
  CATALYST_SET   one per event, sealed before its entry cutoff: the event, the signal features, the coverage
                 class with every rule's input, the cone with its priors, the plan's windows and the twins.
  TAG            DILUTION_RECENT for a Speculation Register set, sealed before that set's cutoff and bound to
                 its record hash (metadata only; the Speculation Register's protocol is unchanged).
  RESOLUTION     one per (set, window) once the bars cover the window, as the Speculation Register's.

Families: SEC13D (counted; original Schedule 13D filings on EDGAR) and IDX_INDEX (descriptive; scheduled IDX30,
LQ45 and IDX80 constituent changes from an events file). The records live in paper/catalysts.jsonl, a hash chain
of the ledger's kind (paper.append), stamped by the same RFC 3161 authorities and pushed. Nothing is edited; the
register never changes a paper decision, the policy or the Speculation Register.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import catalyst as e9
from . import paper
from . import speculation as spec
from .provenance import PKG_ROOT, sha256_file, utc_stamp

PROTOCOL_DIR = PKG_ROOT / "research" / "CATALYST_REGISTER_v1"
PROTOCOL_JSON = PROTOCOL_DIR / "protocol.json"
PREREG_JSON = (
    PROTOCOL_DIR / "prereg_2.json"
)  # SEC13D: win-rate primary and extended looks, frozen before any SEC13D set
CLASS_JSON = (
    PROTOCOL_DIR / "prereg_3_document_class.json"
)  # the pooled DOCUMENT_CLASS test, frozen before any resolution
FAMILY_DIR = (
    PKG_ROOT / "research" / "CATALYST_FAMILIES"
)  # later families, one frozen protocol.json each
FAMILY_MODULES = {
    "DILUTION_8K": "fam_dilution8k",
    "FORM4": "fam_form4",
    "SEC13D_V2": "fam_sec13d_v2",
    "FORM4_SHARP": "fam_form4_sharp",
}
PARENT_FAMILY = {
    "SEC13D_V2": "SEC13D",
    "FORM4_SHARP": "FORM4",
}  # child families seal from their parent's sets of the same run
EVENTS_DIR = PROTOCOL_DIR / "events"
CAT_LEDGER = paper.PAPER / "catalysts.jsonl"
REPORT = paper.PAPER / "CATALYSTS.md"
REGISTER_VERSION = "catalyst-register-v1"
RESOLVER_ID = "catalyst-resolve-v1"
NY = ZoneInfo("America/New_York")
FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=SCHEDULE%2013D&company=&dateb="
    "&owner=include&start={start}&count=100&output=atom"
)
TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
PRIMARY_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/primary_doc.xml"
EN_SITEMAP_URL = "https://www.emitennews.com/sitemap-{year}.xml"
FEED_PAGES = 5
TWINS = spec.TWINS
TWIN_CHECKS = 15
TWINS_20, TWIN_CHECKS_20 = (
    20,
    40,
)  # the 2026-10-29 families (research/CATALYST_FAMILIES/SEC13D_V2, FORM4_SHARP)
REPEAT_DAYS = 90
DILUTION_SESSIONS = 20
MOVED_ALREADY = 1.15
MICROCAP_USD = 50e6
EN_DILUTION_DAYS = 28
# IDX codes that are also ordinary words in EmitenNews headline slugs (ADDENDUM_4, frozen 2026-11-09).
# A slug "names" such a code only when it names no other IDX code: "laba-buva-..." is about BUVA, not
# LABA ("profit"). Chosen from the 2026 sitemap's most frequent code-shaped words.
COMMON_WORD_CODES = frozenset(
    """agar aksi area auto ayam baik baja bali bank beef beli best bina bird blue bola buah buka bull
    bumi cash chip city coal coin crab cuan data daya deal dewa dewi east edge emas euro fast film fire
    food gema gold golf good gula guna hope idea ikan indo jati jawa jaya kayu keju king kopi kota laba
    labs laju land life link live main mari mark maya mega meja mutu naik nasi nice nine obat pada palm
    part pipa pola raja real reli roda roti runs safe same satu ship sofa star tamu taxi trim true truk
    uang visi viva wifi wine zinc""".split()
)
# Fixed phrases whose first word is an IDX code but which never name the company ("aksi korporasi":
# corporate action, a section label).
NOT_A_NAME = (("aksi", "korporasi"),)
TAGS_FROM = (
    "2026-10-28T00:00:00Z"  # Speculation Register sets sealed from the day this protocol was frozen
)
OPERATING_FORMS = frozenset(
    {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A"}
)
FUND_FORMS = frozenset(
    {"N-CSR", "N-CSRS", "N-CSR/A", "N-CSRS/A", "NPORT-P", "NPORT-P/A", "N-CEN", "N-CEN/A"}
)
OPERATING_DAYS = 550
ORIGINAL_13D = frozenset({"SCHEDULE 13D", "SC 13D"})
INTENT_WORDS = (
    "board",
    "merger",
    "acquisition",
    "strategic alternatives",
    "sale of the",
    "proxy",
    "nominate",
    "director",
    "change of control",
    "going private",
    "take private",
    "letter",
)
RELATIVE = frozenset({"BEATS_TWINS_20", "LOSES_TO_TWINS_20", "WITH_FLOW_RUNUP", "REVERSAL_POST20"})
_HORIZON_ID = re.compile(r"^(RUN30|GAIN0|FADE10|BEATS_TWINS|LOSES_TO_TWINS)_(\d+)$")


def is_relative(statement_id: str) -> bool:
    """A statement graded against the twins (no twins-rate of its own)."""
    m = _HORIZON_ID.match(statement_id)
    return statement_id in RELATIVE or bool(m and m[1] in ("BEATS_TWINS", "LOSES_TO_TWINS"))


def protocol() -> tuple[dict, str]:
    return json.loads(PROTOCOL_JSON.read_text(encoding="utf-8")), sha256_file(PROTOCOL_JSON)


def family_protocol(name: str) -> tuple[dict, str]:
    path = FAMILY_DIR / name / "protocol.json"
    return json.loads(path.read_text(encoding="utf-8")), sha256_file(path)


def extra_families() -> dict[str, tuple[dict, str]]:
    """The families frozen after protocol.json, each in research/CATALYST_FAMILIES/<name>/protocol.json."""
    if not FAMILY_DIR.exists():
        return {}
    return {
        d.name: family_protocol(d.name)
        for d in sorted(FAMILY_DIR.iterdir())
        if (d / "protocol.json").exists()
    }


def family_module(name: str):
    import importlib

    return importlib.import_module(f".{FAMILY_MODULES[name]}", __package__)


def prereg() -> tuple[dict, str]:
    return json.loads(PREREG_JSON.read_text(encoding="utf-8")), sha256_file(PREREG_JSON)


def cat_lines(path: Path | None = None) -> list[dict]:
    return paper.ledger_lines(CAT_LEDGER if path is None else path)


def set_seed(set_id: str) -> int:
    return int(hashlib.sha256(f"KOD-CATALYST-REGISTER-v1:{set_id}".encode()).hexdigest()[:8], 16)


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _true(values: pd.Series) -> pd.Series:
    return values.astype(str).str.lower().isin(("true", "1"))


# ------------------------------------------------------------------------------- US sessions (New York)
def _ny(day: str, hh: int, mm: int) -> datetime:
    return datetime.combine(date.fromisoformat(day), time(hh, mm), tzinfo=NY)


def prev_weekday(day: str) -> str:
    return str(np.busday_offset(np.datetime64(day, "D"), -1, roll="backward"))


# NYSE weekday holidays 2026-2027, as exchange_calendars 4.5.6 (XNYS) lists them (checked 2026-10-28). Hard-coded because
# exchange_calendars needs pandas < 3, which the cloud container's system Python does not have.
NYSE_HOLIDAYS = (
    "2026-01-01",
    "2026-01-19",
    "2026-02-16",
    "2026-04-03",
    "2026-05-25",
    "2026-06-19",
    "2026-07-03",
    "2026-09-07",
    "2026-11-26",
    "2026-12-25",
    "2027-01-01",
    "2027-01-18",
    "2027-02-15",
    "2027-03-26",
    "2027-05-31",
    "2027-06-18",
    "2027-07-05",
    "2027-09-06",
    "2027-11-25",
    "2027-12-24",
)
CALENDAR_YEARS = ("2026", "2027")


def _check_year(day: str) -> None:
    if day[:4] not in CALENDAR_YEARS:
        raise ValueError(
            f"{day}: outside the NYSE holiday list of this protocol ({', '.join(CALENDAR_YEARS)})"
        )


def us_is_session(day: str) -> bool:
    _check_year(day)
    return bool(np.is_busday(np.datetime64(day, "D"), holidays=list(NYSE_HOLIDAYS)))


def us_prev_session(day: str) -> str:
    _check_year(day)
    return str(
        np.busday_offset(np.datetime64(day, "D"), -1, roll="forward", holidays=list(NYSE_HOLIDAYS))
    )


def us_entry_session(now: datetime) -> str:
    """The first NYSE session whose 09:15 New York time is after `now`."""
    day = now.astimezone(NY).date()
    while not us_is_session(day.isoformat()) or _ny(day.isoformat(), 9, 15) <= now:
        day += timedelta(days=1)
    return day.isoformat()


def us_cutoff(entry_session: str) -> datetime:
    return _ny(entry_session, 9, 15).astimezone(timezone.utc)


def acceptance_position(accepted: datetime, signal_session: str) -> str:
    """LATE (at or before the close of the session before the signal session), DURING (up to the signal
    session's close: the reference close is the previous one), AFTER (after it: the reference is the signal close)."""
    if accepted <= _ny(us_prev_session(signal_session), 16, 0):
        return "LATE"
    return "DURING" if accepted <= _ny(signal_session, 16, 0) else "AFTER"


# ------------------------------------------------------------------------------- EDGAR parsing (pure)
_ENTRY = re.compile(r"<entry>(.*?)</entry>", re.S)
_TITLE = re.compile(
    r"^(?P<form>.+?) - (?P<name>.*) \((?P<cik>\d{10})\) \((?P<role>[^()]+)\)\s*$", re.S
)
_ACC = re.compile(r"/(\d{10}-\d{2}-\d{6})-index\.html?")


def _tag(text: str, name: str) -> str | None:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", text, re.S)
    return html.unescape(m.group(1)).strip() if m else None


def parse_feed(body: bytes) -> list[dict]:
    """Entries of the EDGAR current-filings Atom feed: one per (filing, company role)."""
    out = []
    for e in _ENTRY.findall(body.decode("utf-8", "replace")):
        title, updated = _tag(e, "title"), _tag(e, "updated")
        link = re.search(r'<link[^>]*href="([^"]+)"', e)
        cat = re.search(r'<category[^>]*term="([^"]+)"', e)
        m = _TITLE.match(title or "")
        acc = _ACC.search(link.group(1)) if link else None
        if not (m and updated and cat and acc):
            continue
        out.append(
            {
                "form": html.unescape(cat.group(1)).strip(),
                "name": m["name"].strip(),
                "cik": int(m["cik"]),
                "role": m["role"].strip(),
                "accepted": updated,
                "accession": acc.group(1),
                "url": link.group(1),
            }
        )
    return out


def originals(entries: list[dict]) -> list[dict]:
    """Original Schedule 13D filings with their subject company, in acceptance order."""
    by_acc: dict[str, dict] = {}
    for e in entries:
        if e["form"] != "SCHEDULE 13D":
            continue
        rec = by_acc.setdefault(
            e["accession"],
            {
                "accession": e["accession"],
                "accepted": e["accepted"],
                "url": e["url"],
                "subject": None,
                "filed_by": [],
            },
        )
        if e["role"] == "Subject":
            rec["subject"] = {"cik": e["cik"], "name": e["name"]}
        else:
            rec["filed_by"].append(e["name"])
    out = [r for r in by_acc.values() if r["subject"]]
    return sorted(out, key=lambda r: (datetime.fromisoformat(r["accepted"]), r["accession"]))


def ticker_maps(body: bytes) -> tuple[dict[int, list[str]], dict[str, int]]:
    blob = json.loads(body)
    col = {f: i for i, f in enumerate(blob["fields"])}
    by_cik: dict[int, list[str]] = {}
    by_ticker: dict[str, int] = {}
    for row in blob["data"]:
        cik, t = int(row[col["cik"]]), str(row[col["ticker"]]).upper().replace(".", "-")
        by_cik.setdefault(cik, []).append(t)
        by_ticker.setdefault(t, cik)
    return by_cik, by_ticker


def dilution_filings(filings: pd.DataFrame, signal_session: str, until: str) -> list[str]:
    """Dilution filings (idxsig.catalyst.is_dilution) dated from the 19th weekday before the signal session
    through `until` (the sealing date)."""
    if filings is None or not len(filings):
        return []
    start = str(
        np.busday_offset(
            np.datetime64(signal_session, "D"), -(DILUTION_SESSIONS - 1), roll="backward"
        )
    )
    f = filings[(filings["filingDate"] >= start) & (filings["filingDate"] <= until)]
    return [
        f"{r.form}|{r.accessionNumber}|{r.filingDate}|{r.items}"
        for r in f.itertuples()
        if e9.is_dilution(r.form, r.items)
    ]


def earlier_13d(
    filings: pd.DataFrame, accession: str, day: str, days: int = REPEAT_DAYS
) -> list[str]:
    """Other original Schedule 13D filings on the company dated in the `days` days before `day` (same-day
    filings are left to the register's own order: the first one sealed wins)."""
    if filings is None or not len(filings):
        return []
    start = (date.fromisoformat(day) - timedelta(days=days)).isoformat()
    f = filings[
        filings["form"].str.upper().isin(ORIGINAL_13D)
        & (filings["accessionNumber"] != accession)
        & (filings["filingDate"] >= start)
        & (filings["filingDate"] < day)
    ]
    return [f"{r.form}|{r.accessionNumber}|{r.filingDate}" for r in f.itertuples()]


def is_operating(filings: pd.DataFrame, day: str) -> bool:
    """An operating issuer: a 10-K, 10-Q, 20-F or 40-F (or /A) filed in the OPERATING_DAYS days up to `day`, and no
    investment-company report (N-CSR, N-CSRS, NPORT-P, N-CEN) in the same days."""
    if filings is None or not len(filings):
        return False
    start = (date.fromisoformat(day) - timedelta(days=OPERATING_DAYS)).isoformat()
    forms = filings[(filings["filingDate"] >= start) & (filings["filingDate"] <= day)][
        "form"
    ].str.upper()
    return bool(forms.isin(OPERATING_FORMS).any()) and not bool(forms.isin(FUND_FORMS).any())


def market_value(points: list[dict], close: float, until: str) -> tuple[float | None, dict | None]:
    pts = [p for p in points if (p.get("filed") or "") <= until and p.get("val")]
    if not pts or not (close > 0):
        return None, None
    p = max(pts, key=lambda p: (p["end"], p.get("filed") or ""))
    return float(p["val"]) * float(close), p


def item4(body: bytes | None) -> dict:
    """Descriptive tag from the structured filing's Item 4 (transactionPurpose); never a rule."""
    m = re.search(rb"<transactionPurpose>(.*?)</transactionPurpose>", body or b"", re.S)
    if not m:
        return {"found": False}
    text = html.unescape(m.group(1).decode("utf-8", "replace")).strip()
    low = text.lower()
    return {
        "found": True,
        "chars": len(text),
        "sha256": _sha(text.encode()),
        "intent_words": [w for w in INTENT_WORDS if w in low],
    }


def coverage(dilution: list[str], move_ratio: float, mv: float | None) -> dict:
    rules = {
        "DILUTION_RECENT": bool(dilution),
        "MOVED_ALREADY": bool(move_ratio >= MOVED_ALREADY),
        "MICROCAP": mv is None or mv < MICROCAP_USD,
    }
    return {
        "class": "ABSTAIN" if any(rules.values()) else "FIRE",
        "rules": rules,
        "reasons": [
            k if not (k == "MICROCAP" and mv is None) else "MV_UNKNOWN"
            for k, v in rules.items()
            if v
        ],
    }


# ------------------------------------------------------------------------------- EDGAR access
def submissions(client, cik: int) -> pd.DataFrame | None:
    status, body = client.get(SUBMISSIONS_URL.format(cik=int(cik)))
    if status != 200 or not body:
        return None
    try:
        return e9.parse_submissions(body, [])
    except (ValueError, KeyError):
        return None


def share_points(client, cik: int) -> list[dict]:
    from . import us_actions

    return us_actions.share_points(client, int(cik))


def sec_client(out_dir: Path | None = None):
    """EDGAR client with the declared contact (KOD_SEC_CONTACT, or a full IDXSIG_SEC_USER_AGENT); refuses without
    one, and never writes the contact to a file."""
    import os

    from . import us_actions
    from .provenance import RAW

    ua = os.environ.get("IDXSIG_SEC_USER_AGENT") or (
        f"KOD-Machine research {os.environ['KOD_SEC_CONTACT']}"
        if os.environ.get("KOD_SEC_CONTACT")
        else None
    )
    if not ua or ua == us_actions.DEFAULT_USER_AGENT:
        raise RuntimeError(
            "EDGAR needs a declared contact: set KOD_SEC_CONTACT (or IDXSIG_SEC_USER_AGENT)"
        )
    return us_actions.SecClient(
        ua, out_dir or RAW / "sec" / ("catalysts-" + utc_stamp().replace("-", "").replace(":", ""))
    )


# ------------------------------------------------------------------------------- shared set pieces
def _scan_for(ledger: list[dict], market: str, session: str) -> dict | None:
    hits = [
        r
        for r in ledger
        if r["type"] == "SCAN" and r.get("market", "IDX") == market and r["session"] == session
    ]
    return hits[-1] if hits else None


def _signal(row: pd.Series) -> dict:
    return {
        k: spec._num(row[k])
        for k in (
            "close",
            "previous",
            "high",
            "low",
            "open",
            "volume",
            "adv20_value",
            "ret1",
            "ret5",
            "ret20",
            "volr",
            "cpos",
            "dd60",
        )
        if k in row.index
    }


def _cone(proto_family: dict, records: list[dict], market: str, family: str) -> list[dict]:
    out = []
    for st in proto_family["cone"]:
        if st["prior"] == "running":
            prior, n = running_prior(family, st["id"], records)
            source = f"register running base rate (n {n}; 0.5 below {spec.RUNNING_MIN_N})"
        else:
            prior, source = float(st["prior"]), st["prior_source"]
        out.append(
            {
                "id": st["id"],
                "statement": st["statement"],
                "prior": prior,
                "prior_source": source,
                "resolves_with": st["resolves_with"],
            }
        )
    return out


def running_prior(family: str, statement_id: str, records: list[dict]) -> tuple[float, int]:
    counted = (r for r in paper.latest_resolutions(records).values() if r.get("family") == family)
    outcomes = [
        c["outcome"]
        for r in counted
        for c in r.get("cone", [])
        if c["id"] == statement_id and c.get("outcome") is not None
    ]
    if len(outcomes) < spec.RUNNING_MIN_N:
        return 0.5, len(outcomes)
    return float(np.mean(outcomes)), len(outcomes)


def _universe(feats: pd.DataFrame) -> pd.DataFrame:
    return feats[_true(feats["fresh"]) & _true(feats["eligible"])]


# ------------------------------------------------------------------------------- SEC13D
def _reject_13d(filings: pd.DataFrame, day: str) -> str | None:
    if earlier_13d(filings, "", (date.fromisoformat(day) + timedelta(days=1)).isoformat()):
        return f"an original Schedule 13D in the {REPEAT_DAYS} days before sealing"
    return None


def reject_dilution(filings: pd.DataFrame, day: str) -> str | None:
    start = (date.fromisoformat(day) - timedelta(days=REPEAT_DAYS)).isoformat()
    f = filings[(filings["filingDate"] >= start) & (filings["filingDate"] <= day)]
    if any(e9.is_dilution(r.form, r.items) for r in f.itertuples()):
        return f"a dilution filing (is_dilution) in the {REPEAT_DAYS} days before sealing"
    return None


def sec13d_twins(
    feats,
    ticker,
    excluded,
    selected,
    seed,
    client,
    by_ticker,
    day: str,
    reject=_reject_13d,
    n: int = TWINS,
    checks: int = TWIN_CHECKS,
) -> tuple[list[dict], str, list[dict]]:
    """Matched, event-free twins: draw_twins' seeded order, then the first `n` (TWINS) operating issuers, of at most
    `checks` examined, that `reject` (filings, day) -> reason does not exclude (default: an original Schedule 13D in
    the last 90 days)."""
    pool, level = spec.draw_twins(feats, ticker, excluded, selected, "US", seed, k=10**9)
    twins, log = [], []
    for tw in pool[:checks]:
        cik = by_ticker.get(tw["ticker"])
        filings = submissions(client, cik) if cik is not None else None
        if cik is None:
            reason = "no CIK in company_tickers_exchange"
        elif filings is None:
            reason = "submissions unavailable"
        elif not is_operating(filings, day):
            reason = f"no 10-K, 10-Q, 20-F or 40-F in {OPERATING_DAYS} days, or a fund report: not an operating issuer"
        else:
            reason = reject(filings, day)
        log.append(
            {
                "ticker": tw["ticker"],
                "accepted": reason is None,
                **({"reason": reason} if reason else {}),
            }
        )
        if reason is None:
            twins.append({**tw, "cik": int(cik)})
            if len(twins) == n:
                break
    return twins, level, log


def sec13d_batch(
    now: datetime,
    client,
    ledger: list[dict] | None = None,
    records: list[dict] | None = None,
    clock=None,
) -> tuple[dict, list[dict]]:
    """Read the feed and build (BATCH, sets) for every new original accepted since the window start."""
    proto, proto_sha = protocol()
    pre, pre_sha = prereg()
    fam = proto["families"]["SEC13D"]
    ledger = paper.ledger_lines() if ledger is None else ledger
    records = cat_lines() if records is None else records
    window_start = datetime.fromisoformat(fam["window_start"])
    entry = us_entry_session(now)
    signal = us_prev_session(entry)
    cutoff = us_cutoff(entry)
    scan = _scan_for(ledger, "US", signal)
    if scan is None:
        raise RuntimeError(
            f"no US paper scan for the signal session {signal}; run paper-scan --market US first"
        )
    earlier_batches = [r for r in records if r["type"] == "BATCH" and r["family"] == "SEC13D"]
    prev_newest = next(
        (
            datetime.fromisoformat(b["feed"]["newest_entry"])
            for b in reversed(earlier_batches)
            if b["feed"]["newest_entry"]
        ),
        None,
    )
    pages, entries = [], []
    for k in range(FEED_PAGES):
        status, body = client.get(FEED_URL.format(start=100 * k))
        if status != 200:
            raise RuntimeError(f"EDGAR current feed page {k}: HTTP {status}")
        got = parse_feed(body)
        pages.append({"start": 100 * k, "sha256": _sha(body), "entries": len(got)})
        entries += got
        oldest = min((datetime.fromisoformat(e["accepted"]) for e in got), default=None)
        if (
            oldest is None
            or oldest < window_start
            or (prev_newest is not None and oldest < prev_newest)
        ):
            break
    times = [datetime.fromisoformat(e["accepted"]) for e in entries]
    listed = {e["accession"] for r in earlier_batches for e in r["events"]}
    events = [
        o
        for o in originals(entries)
        if datetime.fromisoformat(o["accepted"]) >= window_start and o["accession"] not in listed
    ]
    # A gap: the read never reached back to the previous batch's newest entry (the window start for the first
    # batch), or it read nothing at all. Missed filings are recorded as a gap, never backfilled.
    gap = (not times) or min(times) > (prev_newest if prev_newest is not None else window_start)
    status, tm_body = client.get(TICKERS_URL)
    if status != 200:
        raise RuntimeError(f"SEC ticker map: HTTP {status}")
    by_cik, by_ticker = ticker_maps(tm_body)
    feats = spec.scan_features(scan)
    universe = set(_universe(feats)["ticker"])
    chosen = {}
    for ev in events:
        tickers = by_cik.get(ev["subject"]["cik"], [])
        ok = [t for t in tickers if t in universe]
        chosen[ev["accession"]] = (tickers, ok[0] if ok else None)
    # every ticker of an event subject (all its share classes), so a twin is never the event company itself
    excluded = sorted({*scan["candidates_ranked"], *(t for tks, _ in chosen.values() for t in tks)})
    sealed_subjects = {
        r["event"]["subject_cik"]: r["event"]["accepted"]
        for r in records
        if r["type"] == "CATALYST_SET" and r["family"] == "SEC13D"
    }
    statuses, sets = [], []
    today = now.astimezone(NY).date().isoformat()
    for ev in events:
        acc, subj = ev["accession"], ev["subject"]
        accepted = datetime.fromisoformat(ev["accepted"])
        tickers, ticker = chosen[acc]
        row = {
            "accession": acc,
            "subject_cik": subj["cik"],
            "subject_name": subj["name"],
            "accepted": ev["accepted"],
            "tickers": tickers,
            "ticker": ticker,
        }

        def skip(code, reason):
            statuses.append({**row, "status": code, "reason": reason})

        if not tickers:
            skip("SKIP_NO_TICKER", "the subject CIK has no ticker in company_tickers_exchange")
            continue
        if ticker is None:
            skip(
                "SKIP_NOT_IN_UNIVERSE",
                f"none of {tickers} is fresh and eligible in {scan['scan_id']}",
            )
            continue
        pos = acceptance_position(accepted, signal)
        if pos == "LATE":
            skip(
                "SKIP_LATE",
                f"accepted at or before the close of {us_prev_session(signal)}; the register missed its window",
            )
            continue
        prior = sealed_subjects.get(subj["cik"])
        if prior and accepted - datetime.fromisoformat(prior) < timedelta(days=REPEAT_DAYS):
            skip(
                "SKIP_REPEAT_90D",
                f"a set on the same subject was sealed for a filing accepted {prior}",
            )
            continue
        filings = submissions(client, subj["cik"])
        if not is_operating(filings, today):
            skip(
                "SKIP_NOT_OPERATING",
                f"no 10-K, 10-Q, 20-F or 40-F in {OPERATING_DAYS} days, a fund report, or no submissions",
            )
            continue
        repeat = earlier_13d(filings, acc, accepted.astimezone(NY).date().isoformat())
        if repeat:
            skip("SKIP_REPEAT_90D", "; ".join(repeat[:3]))
            continue
        frow = feats[feats["ticker"] == ticker].iloc[0]
        close, previous = float(frow["close"]), spec._num(frow["previous"])
        if pos == "DURING":
            ratio, ref = (
                (close / previous if previous else float("nan")),
                {"session": us_prev_session(signal), "close": previous},
            )
        else:
            ratio, ref = 1.0, {"session": signal, "close": close}
        dil = dilution_filings(filings, signal, today)
        mv, point = market_value(share_points(client, subj["cik"]), close, today)
        cov = coverage(dil, ratio if math.isfinite(ratio) else 0.0, mv)
        cov["inputs"] = {
            "dilution_filings": dil,
            "pre_entry_move": ratio - 1 if math.isfinite(ratio) else None,
            "reference_close": ref,
            "market_value_usd": mv,
            "shares_fact": point,
        }
        st, pdoc = client.get(PRIMARY_DOC_URL.format(cik=subj["cik"], acc=acc.replace("-", "")))
        set_id = f"CAT-SEC13D-{acc}"
        twins, level, log = sec13d_twins(
            feats,
            ticker,
            excluded,
            scan["detector"]["selected"],
            set_seed(set_id),
            client,
            by_ticker,
            today,
        )
        sets.append(
            {
                "type": "CATALYST_SET",
                "register": REGISTER_VERSION,
                "family": "SEC13D",
                "market": "US",
                "set_id": set_id,
                "event_id": acc,
                "ticker": ticker,
                "signal_session": signal,
                "event": {
                    "accession": acc,
                    "form": "SCHEDULE 13D",
                    "accepted": ev["accepted"],
                    "accepted_utc": utc_stamp(accepted.astimezone(timezone.utc)),
                    "position": pos,
                    "subject_cik": subj["cik"],
                    "subject_name": subj["name"],
                    "filed_by": ev["filed_by"],
                    "url": ev["url"],
                    "item4": item4(pdoc if st == 200 else None),
                },
                "entry": {
                    "basis": "open",
                    "session": entry,
                    "text": "the entry session's opening print",
                },
                "entry_cutoff": utc_stamp(cutoff),
                "direction": 1,
                "scan_id": scan["scan_id"],
                "scan_record_hash": scan["record_hash"],
                "features_file": scan["features_file"],
                "features_sha256": scan["features_sha256"],
                "signal": _signal(frow),
                "coverage": cov,
                "twins": twins,
                "twins_match_level": level,
                "twins_seed": set_seed(set_id),
                "twins_checked": log,
                "cone": _cone(fam, records, "US", "SEC13D"),
                "windows": {
                    "H20": {k: fam["plan"][k] for k in ("kind", "entry_window", "holding_sessions")}
                },
                "plan": "H20",
                "protocol": {"id": proto["protocol_id"], "sha256": proto_sha},
                "preregistration": {"id": pre["id"], "sha256": pre_sha},
            }
        )
        statuses.append({**row, "status": "SEALED", "set_id": set_id, "coverage": cov["class"]})
        sealed_subjects[subj["cik"]] = ev["accepted"]
    sealed_at = (clock or (lambda: datetime.now(timezone.utc)))()
    if sets and sealed_at >= cutoff:
        raise RuntimeError(
            f"the entry cutoff {utc_stamp(cutoff)} passed while the batch was built; nothing sealed"
        )
    for s in sets:
        s["sealed_at"] = utc_stamp(sealed_at)
    batch = {
        "type": "BATCH",
        "register": REGISTER_VERSION,
        "family": "SEC13D",
        "market": "US",
        "sealed_at": utc_stamp(sealed_at),
        "window_start": fam["window_start"],
        "signal_session": signal,
        "entry_session": entry,
        "entry_cutoff": utc_stamp(cutoff),
        "scan_id": scan["scan_id"],
        "feed": {
            "pages": pages,
            "entries": len(entries),
            "oldest_entry": min(times).isoformat() if times else None,
            "newest_entry": max(times).isoformat() if times else None,
            "coverage_gap": gap,
        },
        "ticker_map_sha256": _sha(tm_body),
        "events": statuses,
        "protocol": {"id": proto["protocol_id"], "sha256": proto_sha},
    }
    return batch, sets


# ------------------------------------------------------------------------------- IDX_INDEX
def load_events(path: Path) -> tuple[dict, str]:
    return json.loads(path.read_text(encoding="utf-8")), sha256_file(path)


def idx_index_batch(
    events_path: Path,
    now: datetime,
    ledger: list[dict] | None = None,
    records: list[dict] | None = None,
) -> tuple[dict, list[dict]]:
    proto, proto_sha = protocol()
    fam = proto["families"]["IDX_INDEX"]
    ledger = paper.ledger_lines() if ledger is None else ledger
    records = cat_lines() if records is None else records
    ev, ev_sha = load_events(events_path)
    scans = [r for r in ledger if r["type"] == "SCAN" and r.get("market", "IDX") == "IDX"]
    if not scans:
        raise RuntimeError("no IDX paper scan in the ledger")
    scan = max(scans, key=lambda r: r["session"])
    signal = scan["session"]
    cutoff = spec.entry_cutoff("IDX", signal)
    if now >= cutoff:
        raise RuntimeError(
            f"the entry cutoff {utc_stamp(cutoff)} for signal session {signal} has passed"
        )
    last_before = prev_weekday(ev["effective"])
    entry = paper._next_session(signal, "IDX")
    hold_runup = int(np.busday_count(np.datetime64(entry, "D"), np.datetime64(last_before, "D")))
    post_ew = int(np.busday_count(np.datetime64(signal, "D"), np.datetime64(last_before, "D")))
    if post_ew < 1:
        raise RuntimeError(
            f"the signal session {signal} is not before the last session before {ev['effective']}"
        )
    windows = {}
    if hold_runup >= 1:
        windows["RUNUP"] = {"kind": "plan", "entry_window": 1, "holding_sessions": hold_runup}
    windows["POST20"] = {"kind": "plan", "entry_window": post_ew, "holding_sessions": 20}
    feats = spec.scan_features(scan)
    fresh = set(_universe(feats)["ticker"])
    by_ticker: dict[str, list[dict]] = {}
    for ch in ev["changes"]:
        by_ticker.setdefault(ch["ticker"], []).append(ch)
    excluded = sorted({*scan["candidates_ranked"], *by_ticker})
    done = {
        r["event_id"] for r in records if r["type"] == "CATALYST_SET" and r["family"] == "IDX_INDEX"
    }
    statuses, sets = [], []
    for ticker, changes in sorted(by_ticker.items()):
        kinds = {c["change"] for c in changes}
        event_id = f"{ev['review_id']}:{ticker}"
        row = {
            "event_id": event_id,
            "ticker": ticker,
            "changes": [f"{c['change']} {c['index']}" for c in changes],
        }
        if event_id in done:
            continue
        if kinds not in ({"ADD"}, {"DELETE"}):
            statuses.append(
                {
                    **row,
                    "status": "SKIP_MIXED",
                    "reason": "added to one index and removed from another",
                }
            )
            continue
        if ticker not in fresh:
            statuses.append(
                {
                    **row,
                    "status": "SKIP_NOT_IN_UNIVERSE",
                    "reason": f"not fresh and eligible in {scan['scan_id']}",
                }
            )
            continue
        frow = feats[feats["ticker"] == ticker].iloc[0]
        set_id = f"CAT-IDX_INDEX-{ev['review_id']}-{ticker}"
        twins, level = spec.draw_twins(
            feats, ticker, excluded, scan["detector"]["selected"], "IDX", set_seed(set_id)
        )
        windows_here = dict(windows)
        cone = [
            c for c in _cone(fam, records, "IDX", "IDX_INDEX") if c["resolves_with"] in windows_here
        ]
        confidence = (
            "CONFIRMED" if all(c["confidence"] == "CONFIRMED" for c in changes) else "SINGLE_SOURCE"
        )
        sets.append(
            {
                "type": "CATALYST_SET",
                "register": REGISTER_VERSION,
                "family": "IDX_INDEX",
                "market": "IDX",
                "set_id": set_id,
                "event_id": event_id,
                "ticker": ticker,
                "signal_session": signal,
                "event": {
                    "review_id": ev["review_id"],
                    "changes": changes,
                    "announced": ev["announced"],
                    "effective": ev["effective"],
                    "last_session_before_effective": last_before,
                    "confidence": confidence,
                    "events_file": str(events_path.relative_to(PKG_ROOT)),
                    "events_sha256": ev_sha,
                },
                "entry": {
                    "basis": "close",
                    "session": entry,
                    "text": "the closing auction of the session after the signal session",
                },
                "entry_cutoff": utc_stamp(cutoff),
                "direction": 1 if kinds == {"ADD"} else -1,
                "scan_id": scan["scan_id"],
                "scan_record_hash": scan["record_hash"],
                "features_file": scan["features_file"],
                "features_sha256": scan["features_sha256"],
                "signal": _signal(frow),
                "coverage": {"class": "DESCRIPTIVE", "rules": {}, "reasons": []},
                "twins": twins,
                "twins_match_level": level,
                "twins_seed": set_seed(set_id),
                "cone": cone,
                "windows": windows_here,
                "plan": next(iter(windows_here)),
                "protocol": {"id": proto["protocol_id"], "sha256": proto_sha},
            }
        )
        statuses.append({**row, "status": "SEALED", "set_id": set_id, "confidence": confidence})
    sealed_at = utc_stamp(now)
    for s in sets:
        s["sealed_at"] = sealed_at
    batch = {
        "type": "BATCH",
        "register": REGISTER_VERSION,
        "family": "IDX_INDEX",
        "market": "IDX",
        "sealed_at": sealed_at,
        "signal_session": signal,
        "entry_session": entry,
        "entry_cutoff": utc_stamp(cutoff),
        "scan_id": scan["scan_id"],
        "events_file": str(events_path.relative_to(PKG_ROOT)),
        "events_sha256": ev_sha,
        "events": statuses,
        "protocol": {"id": proto["protocol_id"], "sha256": proto_sha},
    }
    return batch, sets


# ------------------------------------------------------------------------------- DILUTION_RECENT tags
def names_code(slug: str, ticker: str, universe: frozenset | None = None) -> bool:
    """Does an EmitenNews slug name this IDX code (CATALYST_REGISTER_v1 ADDENDUM_4)?

    The code must be a whole word of the slug, not the start of a phrase in NOT_A_NAME. A code that
    is also an ordinary word (COMMON_WORD_CODES) names the company only when the slug names no other
    IDX code of `universe`; without a universe that cannot be decided, and ValueError says so."""
    words = slug.lower().split("-")
    code = ticker.lower()
    at = [
        i
        for i, w in enumerate(words)
        if w == code and not any(tuple(words[i : i + len(p)]) == p for p in NOT_A_NAME)
    ]
    if not at:
        return False
    if code not in COMMON_WORD_CODES:
        return True
    if universe is None:
        raise ValueError(f"{ticker} is also an ordinary word; the IDX code list is needed")
    return not any(w in universe and w != code for w in words)


def idx_universe() -> frozenset | None:
    """IDX codes (lower case) of the latest Yahoo pull manifest, or None if none can be read."""
    from .provenance import latest_manifest

    try:
        lines = latest_manifest("yahoo_recent").read_text(encoding="utf-8").splitlines()[1:]
        codes = {json.loads(x)["ticker"].split(".")[0].lower() for x in lines if '"ticker"' in x}
    except (FileNotFoundError, ValueError, KeyError):
        return None
    return frozenset(codes) or None


def idx_dilution_slugs(
    raw: bytes,
    ticker: str,
    until: str,
    days: int = EN_DILUTION_DAYS,
    universe: frozenset | None = None,
) -> list[str]:
    from .sensors import EN_SLUG, dilution_kinds

    start = (date.fromisoformat(until) - timedelta(days=days)).isoformat()
    out = []
    for slug, lastmod in EN_SLUG.findall(raw.decode("utf-8", "replace")):
        if not (start <= lastmod[:10] <= until):
            continue
        kinds = dilution_kinds(slug)
        if kinds and names_code(slug, ticker, universe):
            out.append(f"{slug}|{lastmod[:10]}|{','.join(kinds)}")
    return out


def pending_tags(
    now: datetime, specs: list[dict] | None = None, records: list[dict] | None = None
) -> list[dict]:
    specs = spec.spec_lines() if specs is None else specs
    records = cat_lines() if records is None else records
    done = {r["set_id"] for r in records if r["type"] == "TAG" and r["tag"] == "DILUTION_RECENT"}
    return [
        s
        for s in specs
        if s["type"] == "SPECULATION_SET"
        and s["market"] in ("US", "IDX")
        and s["sealed_at"] >= TAGS_FROM
        and s["set_id"] not in done
        and utc_stamp(now) < s["entry_cutoff"]
    ]


def dilution_tags(
    now: datetime, sets: list[dict], client=None, en_fetch=None, clock=None
) -> list[dict]:
    proto, proto_sha = protocol()
    today = now.astimezone(NY).date().isoformat()
    by_ticker, map_status, raws, out, universe = None, None, {}, [], None
    for s in sets:
        evidence, value, source = [], None, None
        if s["market"] == "US":
            if by_ticker is None:
                map_status, body = client.get(TICKERS_URL)
                by_ticker = ticker_maps(body)[1] if map_status == 200 else {}
            cik = by_ticker.get(s["ticker"])
            filings = submissions(client, cik) if cik is not None else None
            if map_status != 200:  # unknown, and said so: the map was not read, not "no CIK"
                source = f"company_tickers_exchange unavailable (HTTP {map_status})"
            elif cik is None:
                source = "no CIK in company_tickers_exchange"
            elif filings is None:
                source = f"EDGAR submissions CIK {cik} unavailable"
            else:
                source = f"EDGAR submissions CIK {cik}"
                evidence = dilution_filings(filings, s["signal_session"], today)
                value = bool(evidence)
        else:
            day = now.astimezone(timezone.utc).date().isoformat()
            years = sorted(
                {
                    int(day[:4]),
                    int(
                        (date.fromisoformat(day) - timedelta(days=EN_DILUTION_DAYS)).isoformat()[:4]
                    ),
                }
            )
            try:
                for y in years:
                    if y not in raws:
                        raws[y] = en_fetch(EN_SITEMAP_URL.format(year=y))
                if universe is None:
                    universe = idx_universe()
                if universe is None and s["ticker"].lower() in COMMON_WORD_CODES:
                    raise ValueError("no IDX code list for a code that is also a word")
                evidence = [
                    x
                    for y in years
                    for x in idx_dilution_slugs(raws[y], s["ticker"], day, universe=universe)
                ]
                value, source = (
                    bool(evidence),
                    "EmitenNews sitemap " + ", ".join(str(y) for y in years),
                )
            except ValueError:  # a code that is also a word, and no IDX code list to decide it
                evidence, value, source = [], None, "IDX code list unavailable (ADDENDUM_4)"
            except Exception as exc:  # recorded as unknown, never guessed
                source = f"EmitenNews sitemap unavailable: {type(exc).__name__}"
        out.append(
            {
                "type": "TAG",
                "register": REGISTER_VERSION,
                "tag": "DILUTION_RECENT",
                "market": s["market"],
                "set_id": s["set_id"],
                "set_record_hash": s["record_hash"],
                "ticker": s["ticker"],
                "signal_session": s["signal_session"],
                "set_entry_cutoff": s["entry_cutoff"],
                "value": value,
                "evidence": evidence,
                "source": source,
                "protocol": {"id": proto["protocol_id"], "sha256": proto_sha},
            }
        )
    sealed_at = utc_stamp((clock or (lambda: datetime.now(timezone.utc)))())
    for t in out:
        if sealed_at >= t["set_entry_cutoff"]:
            raise RuntimeError(
                f"{t['set_id']}: its cutoff {t['set_entry_cutoff']} passed; no tag sealed"
            )
        t["sealed_at"] = sealed_at
    return out


# ------------------------------------------------------------------------------- append
def append(records: list[dict], timestamper=None) -> tuple[list[Path], list[dict]]:
    stored = paper.append(records, path=CAT_LEDGER, timestamper=timestamper)
    tokens = [
        paper.TOKENS / f"{r['record_hash']}.{a}.tsr" for r in stored for a in ("freetsa", "sectigo")
    ]
    return [CAT_LEDGER, *[t for t in tokens if t.exists()]], stored


# ------------------------------------------------------------------------------- resolution
def window_length(w: dict) -> int:
    if (
        w.get("kind") == "mechanism"
    ):  # sessions after the signal session, plus one for the next morning's index
        return int(w["sessions"]) + 1 if "sessions" in w else 0
    return int(w["entry_window"]) + int(w["holding_sessions"])


def _mechanism_due(s: dict, w: dict, today_d) -> bool:
    if "calendar_days" in w:
        day = np.datetime64(
            datetime.fromisoformat(s["event"]["accepted"]).astimezone(NY).date().isoformat(), "D"
        )
        return int((today_d - day).astype(int)) > int(w["calendar_days"])
    return int(np.busday_count(np.datetime64(s["signal_session"], "D"), today_d)) >= window_length(
        w
    )


def due(
    market: str,
    today: str | None = None,
    records: list[dict] | None = None,
    mechanism: bool = False,
) -> list[tuple[str, str]]:
    """(set, window) pairs whose window has ended: the price windows, or with `mechanism` the mechanism windows."""
    records = cat_lines() if records is None else records
    today_d = np.datetime64(today or datetime.now(timezone.utc).date().isoformat(), "D")
    done = {(r["set_id"], r["window"]) for r in records if r["type"] == "RESOLUTION"}
    out = []
    for s in records:
        if s["type"] != "CATALYST_SET" or s["market"] != market:
            continue
        elapsed = int(np.busday_count(np.datetime64(s["signal_session"], "D"), today_d))
        for wid, w in s["windows"].items():
            if (s["set_id"], wid) in done or (w.get("kind") == "mechanism") != mechanism:
                continue
            if _mechanism_due(s, w, today_d) if mechanism else elapsed >= window_length(w):
                out.append((s["set_id"], wid))
    return out


def statement_outcome(
    sid: str, m, n: int, d: int, result: dict | None, twin_nets: list[float], direction: int
) -> bool | None:
    """A price statement's outcome. RUN30_<k>, GAIN0_<k>, FADE10_<k>, BEATS_TWINS_<k>, LOSES_TO_TWINS_<k> are graded
    on the window that resolves them (k sessions; RUN30 on the path of k sessions after the signal session)."""
    trade = (result or {}).get("trade") if result else None
    net = trade.get("net_return") if trade else None
    hz = _HORIZON_ID.match(sid)
    kind = hz[1] if hz else None
    if kind == "RUN30":
        return spec.path_statement(m, n, d, int(hz[2]), 1.30)
    if net is None:
        return None
    if kind == "GAIN0":
        return bool(net > 0)
    if kind == "FADE10":
        return bool(net <= -0.10)
    if not twin_nets:
        return None
    if kind == "BEATS_TWINS":
        return bool(net > float(np.median(twin_nets)))
    if kind == "LOSES_TO_TWINS":
        return bool(net < float(np.median(twin_nets)))
    if sid == "WITH_FLOW_RUNUP":
        return bool((net - float(np.mean(twin_nets))) * direction > 0)
    if sid == "REVERSAL_POST20":
        return bool((net - float(np.mean(twin_nets))) * direction < 0)
    return None


def cone_outcomes(s: dict, window_id: str, m, d: int, candidate, twins) -> list[dict]:
    n, cres = candidate
    nets = [r["trade"]["net_return"] for _, r in twins if r and r.get("trade")]
    out = []
    for st in s["cone"]:
        if st["resolves_with"] != window_id:
            continue
        o = statement_outcome(st["id"], m, n, d, cres, nets, int(s.get("direction", 1)))
        rec = {
            "id": st["id"],
            "prior": st["prior"],
            "outcome": o,
            "brier": None if o is None else float((st["prior"] - float(o)) ** 2),
        }
        if o is None:
            rec["note"] = "not graded: no position (or no twin traded)"
        if not is_relative(st["id"]):
            tw = [statement_outcome(st["id"], m, tn, d, tres, [], 1) for tn, tres in twins]
            known = [x for x in tw if x is not None]
            rec["twins_rate"], rec["twins_graded"] = (
                (float(np.mean(known)) if known else None),
                len(known),
            )
        out.append(rec)
    return out


def resolve_set(s: dict, window_id: str, m, events: pd.DataFrame, verify=None) -> dict | None:
    w = s["windows"][window_id]
    market = s["market"]
    dates = m.dates.astype(str)
    if s["signal_session"] not in dates:
        return None
    d0 = int(np.flatnonzero(dates == s["signal_session"])[0])
    if d0 + window_length(w) > m.shape[1] - 1:
        return None
    base = {
        "type": "RESOLUTION",
        "register": REGISTER_VERSION,
        "resolver": RESOLVER_ID,
        "family": s["family"],
        "market": market,
        "set_id": s["set_id"],
        "window": window_id,
        "ticker": s["ticker"],
        "signal_session": s["signal_session"],
        "coverage": s["coverage"]["class"],
        "direction": s.get("direction", 1),
        "resolved_at": utc_stamp(),
        "preprocessing": paper.SCORING_PREPROCESSING[market],
        "protocol": s["protocol"],
    }
    located, units, reason = spec._units_for(
        s["ticker"], s["signal_session"], float(s["signal"]["close"]), m, events, verify, market
    )
    if located is None:
        return {**base, "status": "UNRESOLVABLE", "reason": reason}
    n, d, uf = located
    cand = spec.simulate(m, n, d, w, market, unit_factor=uf)
    if cand is None:
        return None
    twins, graded = [], []
    for tw in s["twins"]:
        loc, tunits, treason = spec._units_for(
            tw["ticker"], s["signal_session"], float(tw["close"]), m, events, verify, market
        )
        if loc is None:
            twins.append(
                {"ticker": tw["ticker"], "status": "DROPPED", "reason": treason, "trade": None}
            )
            continue
        tn, td, tuf = loc
        res = spec.simulate(m, tn, td, w, market, unit_factor=tuf)
        if res is None:
            return None
        twins.append(
            {
                "ticker": tw["ticker"],
                **res,
                **({"units": tunits} if tunits and tunits["actions"] else {}),
            }
        )
        graded.append((tn, res))
    paired = None
    if cand.get("trade"):
        nets = [r["trade"]["net_return"] for _, r in graded if r and r.get("trade")]
        if nets:
            paired = {
                "candidate_net": cand["trade"]["net_return"],
                "twins_traded": len(nets),
                "twins_mean_net": float(np.mean(nets)),
                "twins_median_net": float(np.median(nets)),
                "diff": float(cand["trade"]["net_return"] - np.mean(nets)),
            }
    return {
        **base,
        "status": "RESOLVED",
        "candidate": {**cand, "units": units},
        "twins": twins,
        "paired": paired,
        "cone": cone_outcomes(s, window_id, m, d, (n, cand), graded),
    }


def resolve_pending(
    manifest: Path, market: str, timestamper=None, verify=None
) -> tuple[list[Path], list[dict]]:
    records = cat_lines()
    todo = due(market, records=records)
    if not todo:
        return [], []
    sets = {r["set_id"]: r for r in records if r["type"] == "CATALYST_SET"}
    df, data = paper.load_recent(manifest, market, purpose="scoring")
    m = paper._market(df, market)
    from . import us_actions

    events = us_actions.yahoo_events(manifest, market=market)
    out = []
    for set_id, wid in todo:
        rec = resolve_set(sets[set_id], wid, m, events, verify)
        if rec is not None:
            rec["data"] = {"manifest": data["manifest"], "manifest_sha256": data["manifest_sha256"]}
            out.append(rec)
    if not out:
        return [], []
    return append(out, timestamper)


def resolve_mechanisms(
    market: str,
    client=None,
    timestamper=None,
    today: str | None = None,
    records: list[dict] | None = None,
) -> tuple[list[Path], list[dict], list[str]]:
    """Resolve the mechanism windows that have ended (statements graded from EDGAR or from this register's own
    batches, not from prices) through each family module's resolve_mechanism(set, window, records, client). A window a
    module cannot grade yet (its source not covered, or no EDGAR client) stays due and is listed in the third value."""
    records = cat_lines() if records is None else records
    todo = due(market, today=today, records=records, mechanism=True)
    sets = {r["set_id"]: r for r in records if r["type"] == "CATALYST_SET"}
    out, waiting = [], []
    for set_id, wid in todo:
        s = sets[set_id]
        mod = family_module(s["family"]) if s["family"] in FAMILY_MODULES else None
        rec = (
            mod.resolve_mechanism(s, wid, records, client)
            if mod and hasattr(mod, "resolve_mechanism")
            else None
        )
        if rec is None:
            waiting.append(f"{set_id}/{wid}")
            continue
        out.append(rec)
    if not out:
        return [], [], waiting
    written, stored = append(out, timestamper)
    return written, stored, waiting


def mechanism_record(
    s: dict, window_id: str, outcomes: dict[str, bool | None], evidence: dict
) -> dict:
    """A RESOLUTION of a mechanism window: the cone statements it resolves, graded, with the evidence read."""
    cone = []
    for st in s["cone"]:
        if st["resolves_with"] != window_id:
            continue
        o = outcomes.get(st["id"])
        rec = {
            "id": st["id"],
            "prior": st["prior"],
            "outcome": o,
            "brier": None if o is None else float((st["prior"] - float(o)) ** 2),
        }
        if o is None:
            rec["note"] = "not graded: its source was not readable or not covered"
        cone.append(rec)
    return {
        "type": "RESOLUTION",
        "register": REGISTER_VERSION,
        "resolver": RESOLVER_ID,
        "family": s["family"],
        "market": s["market"],
        "set_id": s["set_id"],
        "window": window_id,
        "ticker": s["ticker"],
        "signal_session": s["signal_session"],
        "coverage": s["coverage"]["class"],
        "direction": s.get("direction", 1),
        "resolved_at": utc_stamp(),
        "status": "RESOLVED",
        "kind": "mechanism",
        "paired": None,
        "evidence": evidence,
        "cone": cone,
        "protocol": s["protocol"],
    }


# ------------------------------------------------------------------------------- statistics
def look_verdict(st: dict, rule: dict) -> dict:
    looks, t_min = rule["looks"], rule["boundaries"]["t_min"]
    reached = [
        i
        for i, n in enumerate(looks)
        if st["n_paired"] >= n and st["n_sessions"] >= rule["min_sessions"]
    ]
    k = reached[-1] if reached else None
    out = {
        "looks": looks,
        "t_min": t_min,
        "reached": looks[k] if k is not None else None,
        "next": looks[k + 1]
        if k is not None and k + 1 < len(looks)
        else (looks[0] if k is None else None),
    }
    if k is None:
        out["verdict"] = "accumulating (no look reached)"
        return out
    eligible = (
        st["t"] is not None
        and st["t"] >= t_min[k]
        and st["p_one_sided"] is not None
        and st["p_one_sided"] < 0.05
        and st["mean_net"] is not None
        and st["mean_net"] > 0
    )
    out["eligible"] = eligible
    out["verdict"] = (
        f"ELIGIBLE FOR OWNER REVIEW at the n>={looks[k]} look"
        if eligible
        else (
            "FAIL at the final look"
            if k == len(looks) - 1
            else f"not eligible at the n>={looks[k]} look; continues"
        )
    )
    return out


def _binomial_upper(k: int, n: int) -> float:
    """Exact one-sided P(X >= k) for X ~ Binomial(n, 0.5)."""
    return float(sum(math.comb(n, i) for i in range(k, n + 1)) / 2**n) if n else float("nan")


def winrate_statistics(resolutions: list[dict], statement: str = "BEATS_TWINS_20") -> dict:
    """WIN_RATE primary (prereg_2.json; the families' protocols): per-session share of sets for which `statement`
    holds (default: the plan's net beats the twins' median net)."""
    by_session: dict[str, list[float]] = {}
    for r in resolutions:
        if r.get("status") != "RESOLVED" or not r.get("paired"):
            continue
        o = next((c["outcome"] for c in r.get("cone", []) if c["id"] == statement), None)
        if o is not None:
            by_session.setdefault(r["signal_session"], []).append(float(o))
    shares = np.array([np.mean(v) for _, v in sorted(by_session.items())])
    n = int(sum(len(v) for v in by_session.values()))
    k = int(sum(sum(v) for v in by_session.values()))
    out = {
        "n_paired": n,
        "n_sessions": len(shares),
        "wins": k,
        "win_rate": k / n if n else None,
        "estimate": float(shares.mean() - 0.5) if len(shares) else None,
        "sd_session": float(np.std(shares, ddof=1)) if len(shares) > 1 else None,
        "t": None,
        "p_one_sided": None,
        "binomial_p_descriptive": _binomial_upper(k, n) if n else None,
    }
    if len(shares) >= 2 and out["sd_session"] and out["sd_session"] > 0:
        t = float((shares.mean() - 0.5) / (out["sd_session"] / math.sqrt(len(shares))))
        out["t"], out["p_one_sided"] = t, float(spec.t_sf(t, len(shares) - 1))
    return out


def prereg_verdict(
    st: dict, estimate: float | None, mean_net: float | None, design: dict | None = None
) -> dict:
    """One primary under prereg_2.json: the look reached, eligibility, futility from the 240 look, FAIL at 1920."""
    design = design or prereg()[0]
    looks, t_min, min_s = (
        design["looks"]["n"],
        design["looks"]["t_min"],
        design["looks"]["min_sessions"],
    )
    reached = [
        i for i, n in enumerate(looks) if st["n_paired"] >= n and st["n_sessions"] >= min_s[i]
    ]
    k = reached[-1] if reached else None
    out = {
        "looks": looks,
        "t_min": t_min,
        "reached": looks[k] if k is not None else None,
        "next": looks[0] if k is None else (looks[k + 1] if k + 1 < len(looks) else None),
    }
    if k is None:
        out["verdict"] = "accumulating (no look reached)"
        return out
    eligible = (
        st.get("t") is not None
        and st["t"] >= t_min[k]
        and st.get("p_one_sided") is not None
        and st["p_one_sided"] < 0.05
        and estimate is not None
        and estimate > 0
        and mean_net is not None
        and mean_net > 0
    )
    out["eligible"] = eligible
    if eligible:
        out["verdict"] = f"ELIGIBLE FOR OWNER REVIEW at the n>={looks[k]} look"
    elif looks[k] >= 240 and (estimate is None or estimate <= 0):
        out["verdict"] = f"FAIL (futility) at the n>={looks[k]} look"
    elif k == len(looks) - 1:
        out["verdict"] = "FAIL at the final look"
    else:
        out["verdict"] = f"not eligible at the n>={looks[k]} look; continues"
    return out


def _calibration(cone_ids: list[str], res: list[dict]) -> dict:
    cal = {}
    for cid in cone_ids:
        graded = [
            x
            for r in res
            for x in r.get("cone", [])
            if x["id"] == cid and x.get("outcome") is not None
        ]
        if not graded:
            cal[cid] = {"n": 0}
            continue
        o = np.array([float(x["outcome"]) for x in graded])
        p = np.array([float(x["prior"]) for x in graded])
        tw = [x["twins_rate"] for x in graded if x.get("twins_rate") is not None]
        cal[cid] = {
            "n": len(graded),
            "realised_rate": float(o.mean()),
            "mean_prior": float(p.mean()),
            "twins_rate": float(np.mean(tw)) if tw else None,
            "brier": float(((p - o) ** 2).mean()),
            "brier_uninformed": float(((0.5 - o) ** 2).mean()),
        }
    return cal


def statistics(records: list[dict] | None = None) -> dict:
    proto, proto_sha = protocol()
    records = cat_lines() if records is None else records
    sets = [r for r in records if r["type"] == "CATALYST_SET"]
    res = [r for r in paper.latest_resolutions(records).values() if r.get("status")]
    fams = {}
    for fam, pf in proto["families"].items():
        fsets = [s for s in sets if s["family"] == fam]
        fres = [r for r in res if r["family"] == fam]
        classes = {}
        for s in fsets:
            classes[s["coverage"]["class"]] = classes.get(s["coverage"]["class"], 0) + 1
        out = {
            "n_sets": len(fsets),
            "classes": classes,
            "sessions": len({s["signal_session"] for s in fsets}),
            "n_resolutions": len(fres),
            "calibration": _calibration([c["id"] for c in pf["cone"]], fres),
        }
        if fam == "SEC13D":
            for cls in ("FIRE", "ABSTAIN"):
                rs = [r for r in fres if r["window"] == "H20" and r["coverage"] == cls]
                st = spec.plan_statistics(rs)
                wr = winrate_statistics(rs)
                if cls == "FIRE":  # the two primaries of prereg_2.json
                    st["look"] = prereg_verdict(st, st["mean_diff"], st["mean_net"])
                    wr["look"] = prereg_verdict(wr, wr["estimate"], st["mean_net"])
                out[cls] = st
                out[f"{cls}_WIN_RATE"] = wr
            batches = [r for r in records if r["type"] == "BATCH" and r["family"] == fam]
            counts = {}
            for b in batches:
                for e in b["events"]:
                    counts[e["status"]] = counts.get(e["status"], 0) + 1
            out["events_seen"] = counts
            out["coverage_gaps"] = sum(bool(b["feed"]["coverage_gap"]) for b in batches)
        else:
            for wid in ("RUNUP", "POST20"):
                rs = [r for r in fres if r["window"] == wid and r.get("paired")]
                signed = [r["paired"]["diff"] * r["direction"] for r in rs]
                out[wid] = {
                    "n_paired": len(rs),
                    "mean_signed_diff": float(np.mean(signed)) if signed else None,
                    "share_with_flow": float(np.mean([x > 0 for x in signed])) if signed else None,
                }
        fams[fam] = out
    for fam, (fs, fsha) in extra_families().items():
        fams[fam] = family_statistics(fam, fs, fsha, sets, res, records)
    return {
        "protocol": {"id": proto["protocol_id"], "sha256": proto_sha},
        "register": REGISTER_VERSION,
        "outcome_view": {"semantics": paper.RESOLUTION_VIEW, "cutoff": "complete supplied ledger"},
        "generated_at": utc_stamp(),
        "families": fams,
        "document_class": document_class(records),
        "tags": {
            "DILUTION_RECENT": {
                "n": sum(r["type"] == "TAG" for r in records),
                "true": sum(r["type"] == "TAG" and r["value"] is True for r in records),
                "unknown": sum(r["type"] == "TAG" and r["value"] is None for r in records),
            }
        },
    }


def document_class_design() -> tuple[dict, str]:
    return json.loads(CLASS_JSON.read_text(encoding="utf-8")), sha256_file(CLASS_JSON)


def document_class(records: list[dict] | None = None) -> dict:
    """The pooled DOCUMENT_CLASS statistic (prereg_3_document_class.json): the latest H20 FIRE resolution of each set
    of the listed parent families, its paired excess signed by the set's direction, the per-session mean and the
    pre-registered look verdict; the win rate, the split by family and the split by price band are descriptive."""
    design, sha = document_class_design()
    records = cat_lines() if records is None else records
    fams = list(design["families"])
    sets = {r["set_id"]: r for r in records if r["type"] == "CATALYST_SET"}
    rs = [
        r
        for r in paper.latest_resolutions(
            records
        ).values()  # the revision that counts, before any filter
        if r.get("status") == "RESOLVED"
        and r.get("paired")
        and r["family"] in fams
        and r["window"] == "H20"
        and r.get("coverage") == "FIRE"
    ]
    signed = [
        {**r, "paired": {**r["paired"], "diff": r["paired"]["diff"] * int(r.get("direction", 1))}}
        for r in rs
    ]
    st = spec.plan_statistics(signed)
    st["look"] = prereg_verdict(
        st, st["mean_diff"], 1.0, design=design
    )  # no mean-net condition for a class with an avoid family
    wins = [
        (r["paired"]["candidate_net"] - r["paired"]["twins_median_net"])
        * int(r.get("direction", 1))
        > 0
        for r in rs
        if r["paired"].get("twins_median_net") is not None
    ]
    band = {"close_ge_20": [], "close_lt_20": [], "close_unknown": []}
    for x in signed:
        close = (sets.get(x["set_id"], {}).get("signal") or {}).get("close")
        band[
            "close_unknown"
            if close is None
            else ("close_ge_20" if float(close) >= 20 else "close_lt_20")
        ].append(x)
    return {
        "design": {"id": design["id"], "sha256": sha},
        "families": fams,
        "MEAN": st,
        "win_rate_descriptive": {
            "n": len(wins),
            "wins": int(sum(wins)),
            "rate": (sum(wins) / len(wins)) if wins else None,
        },
        "by_family": {
            f: spec.plan_statistics([x for x in signed if x["family"] == f]) for f in fams
        },
        "by_price_band": {k: spec.plan_statistics(v) for k, v in band.items()},
    }


def _batch_counts(batches: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for b in batches:
        for e in b.get("events", []):
            counts[e["status"]] = counts.get(e["status"], 0) + 1
        for k, v in (b.get("counts") or {}).items():
            counts[k] = counts.get(k, 0) + int(v)
    return counts


def family_statistics(
    fam: str, fs: dict, fsha: str, sets: list[dict], res: list[dict], records: list[dict]
) -> dict:
    """A later family's two primaries (its protocol's 'decision'), signed by its direction."""
    fsets = [s for s in sets if s["family"] == fam]
    dec = fs["decision"]
    window, cls = dec.get("window", "H20"), dec.get("coverage_class")
    d = int(fs["direction"])

    def signed_of(rs):
        return [
            {**r, "paired": {**r["paired"], "diff": r["paired"]["diff"] * d}}
            if r.get("paired")
            else r
            for r in rs
        ]

    rs = [
        r
        for r in res
        if r["family"] == fam
        and r["window"] == window
        and (cls is None or r.get("coverage") == cls)
    ]
    st = spec.plan_statistics(signed_of(rs))
    wr = winrate_statistics(rs, statement=dec["primaries"]["WIN_RATE"]["statement"])
    net_ok = (
        st["mean_net"] if dec["require_positive_mean_net"] else 1.0
    )  # an avoid family claims no positive net
    st["look"] = prereg_verdict(st, st["mean_diff"], net_ok, design=dec)
    wr["look"] = prereg_verdict(wr, wr["estimate"], net_ok, design=dec)
    batches = [r for r in records if r["type"] == "BATCH" and r["family"] == fam]
    descriptive = {}
    if (
        cls is not None
    ):  # the 2026-10-29 families: the other plan windows and the other class, never counted
        classes = {}
        for s in fsets:
            classes[s["coverage"]["class"]] = classes.get(s["coverage"]["class"], 0) + 1
        descriptive["classes"] = classes
        for wid, w in fs.get("windows", {}).items():
            if w.get("kind") != "plan":
                continue
            for c in ("FIRE", "ABSTAIN"):
                if (wid, c) == (window, cls):
                    continue
                sub = [
                    r
                    for r in res
                    if r["family"] == fam and r["window"] == wid and r.get("coverage") == c
                ]
                descriptive[f"{wid}_{c}"] = spec.plan_statistics(signed_of(sub))
        descriptive["entry_weeks"] = len(
            {date.fromisoformat(r["signal_session"]).isocalendar()[:2] for r in rs}
        )
        mod = family_module(fam) if fam in FAMILY_MODULES else None
        labels = mod.split_labels(fsets) if mod is not None and hasattr(mod, "split_labels") else {}
        groups: dict[str, list[dict]] = {}
        for r in res:
            if r["family"] == fam and r["window"] == window:
                for name, label in labels.get(r["set_id"], {}).items():
                    groups.setdefault(f"split {name}={label}", []).append(r)
        for key in sorted(groups):
            descriptive[key] = spec.plan_statistics(signed_of(groups[key]))
    return {
        "protocol": {"id": fs["protocol_id"], "sha256": fsha},
        "direction": d,
        "n_sets": len(fsets),
        "window": window,
        "coverage_class": cls,
        "descriptive": descriptive,
        "sessions": len({s["signal_session"] for s in fsets}),
        "n_resolutions": len([r for r in res if r["family"] == fam]),
        "MEAN": st,
        "WIN_RATE": wr,
        "events_seen": _batch_counts(batches),
        "coverage_gaps": sum(bool((b.get("feed") or b).get("coverage_gap")) for b in batches),
        "calibration": _calibration(
            [c["id"] for c in fs["cone"]], [r for r in res if r["family"] == fam]
        ),
    }


# ------------------------------------------------------------------------------- report
def _pct(x, digits=2):
    return "n/a" if x is None else f"{x:+.{digits}%}"


def card(s: dict) -> str:
    ev, cov = s["event"], s["coverage"]
    if s["family"] in FAMILY_MODULES and hasattr(family_module(s["family"]), "card_lines"):
        head, what, cls = family_module(s["family"]).card_lines(s)
    elif s["family"] == "SEC13D":
        head = (
            f"### SEC13D {s['ticker']} ({ev['subject_name']}) - accepted {ev['accepted']}, sealed {s['sealed_at']}, "
            f"cutoff {s['entry_cutoff']}"
        )
        what = (
            f"Filing `{ev['accession']}` by {', '.join(ev['filed_by']) or 'n/a'}; Item 4 intent words: "
            f"{', '.join(ev['item4'].get('intent_words', [])) or 'none'}."
        )
        inp = cov.get("inputs", {})
        cls = (
            f"Coverage **{cov['class']}**"
            + (f" ({', '.join(cov['reasons'])})" if cov["reasons"] else "")
            + f"; pre-entry move {_pct(inp.get('pre_entry_move'))}, market value "
            + (
                "n/a"
                if inp.get("market_value_usd") is None
                else f"USD {inp['market_value_usd'] / 1e6:,.1f}M"
            )
            + f", dilution filings {len(inp.get('dilution_filings', []))}."
        )
    elif s["family"] == "IDX_INDEX":
        head = (
            f"### IDX_INDEX {s['ticker']} ({', '.join(c['change'] + ' ' + c['index'] for c in ev['changes'])}) - "
            f"effective {ev['effective']}, sealed {s['sealed_at']}, cutoff {s['entry_cutoff']}"
        )
        what = f"Confidence {ev['confidence']}; events file sha256 `{ev['events_sha256'][:12]}`."
        cls = "Coverage DESCRIPTIVE (not counted)."
    else:  # a later family without its own card_lines
        head = (
            f"### {s['family']} {s['ticker']} - event `{s['event_id']}`, accepted {ev.get('accepted', 'n/a')}, "
            f"sealed {s['sealed_at']}, cutoff {s['entry_cutoff']}"
        )
        what = f"Direction {int(s.get('direction', 1)):+d}; protocol `{s['protocol']['id']}`."
        cls = f"Coverage **{cov['class']}**; pre-entry move {_pct(cov.get('inputs', {}).get('pre_entry_move'))}."

    def _win(
        w: dict,
    ) -> str:  # plan windows have entry/hold; event windows (SEC13D_V2's) count sessions or days
        if "entry_window" in w and "holding_sessions" in w:
            return f"entry +{w['entry_window']}, hold {w['holding_sessions']}"
        if "sessions" in w:
            return f"{w['sessions']} sessions"
        if "calendar_days" in w:
            return f"{w['calendar_days']} calendar days"
        return w.get("kind", "window")

    wins = "; ".join(f"{k}: {_win(w)}" for k, w in s["windows"].items())
    return "\n".join(
        [
            head,
            f"Set `{s['set_id']}`, scan `{s['scan_id']}`; signal close {s['signal']['close']:g} on "
            f"{s['signal_session']}; entry: {s['entry']['text']} ({s['entry']['session']}). Windows: {wins}.",
            what,
            cls,
            f"Twins ({s['twins_match_level']}): "
            + (", ".join(f"{x['ticker']} {x['close']:g}" for x in s["twins"]) or "none")
            + ".",
            "Cone: " + "; ".join(f"{c['id']} p={c['prior']:.2f}" for c in s["cone"]) + ".",
            "",
        ]
    )


def render(stats: dict, records: list[dict]) -> str:
    sets = [r for r in records if r["type"] == "CATALYST_SET"]
    out = [
        "# Catalyst Register",
        "",
        f"Protocol `{stats['protocol']['id']}` (sha256 `{stats['protocol']['sha256'][:12]}`), "
        "`research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` "
        f"(generated {stats['generated_at']}). Nothing here is a result until a look is reached.",
        "",
    ]
    s13 = stats["families"].get("SEC13D", {})
    fire = s13.get("FIRE", {})
    look = fire.get("look", {})
    out += [
        "## SEC13D (counted at each look)",
        "",
        f"Sets {s13.get('n_sets', 0)} ({', '.join(f'{k} {v}' for k, v in s13.get('classes', {}).items()) or 'none'}) over "
        f"{s13.get('sessions', 0)} signal sessions; events seen: "
        f"{', '.join(f'{k} {v}' for k, v in s13.get('events_seen', {}).items()) or 'none'}; coverage gaps {s13.get('coverage_gaps', 0)}.",
        "",
        "| Class | Paired | Sessions | Mean net | Mean diff vs twins | t | p (one-sided) |",
        "|---|---|---|---|---|---|---|",
    ]
    for cls in ("FIRE", "ABSTAIN"):
        st = s13.get(cls, {})
        t_txt = "n/a" if st.get("t") is None else f"{st['t']:.2f}"
        p_txt = "n/a" if st.get("p_one_sided") is None else f"{st['p_one_sided']:.4f}"
        out.append(
            f"| {cls} | {st.get('n_paired', 0)} | {st.get('n_sessions', 0)} | {_pct(st.get('mean_net'))} | "
            f"{_pct(st.get('mean_diff'))} | {t_txt} | {p_txt} |"
        )
    wr = s13.get("FIRE_WIN_RATE", {})
    wlook = wr.get("look", {})
    rate = "n/a" if wr.get("win_rate") is None else f"{wr['win_rate']:.1%}"
    wt = "n/a" if wr.get("t") is None else f"{wr['t']:.2f}"
    out += [
        "",
        "Primaries (`research/CATALYST_REGISTER_v1/prereg_2.json`), looks at "
        f"{look.get('looks')} FIRE pairs, t at least {look.get('t_min')}:",
        f"- MEAN (plan net minus twins' mean): **{look.get('verdict', 'n/a')}**",
        f"- WIN_RATE (plan beats twins' median): {wr.get('wins', 0)} of {wr.get('n_paired', 0)} ({rate}), "
        f"t {wt}: **{wlook.get('verdict', 'n/a')}**",
        "",
    ]
    ix = stats["families"].get("IDX_INDEX", {})
    out += [
        "## IDX_INDEX (descriptive)",
        "",
        f"Sets {ix.get('n_sets', 0)} over {ix.get('sessions', 0)} sessions.",
        "",
    ]
    for wid in ("RUNUP", "POST20"):
        w = ix.get(wid, {})
        share = "n/a" if w.get("share_with_flow") is None else f"{w['share_with_flow']:.0%}"
        out.append(
            f"- {wid}: paired {w.get('n_paired', 0)}, mean signed diff {_pct(w.get('mean_signed_diff'))}, "
            f"share with the flow {share}"
        )
    for fam, fsx in stats["families"].items():
        if "MEAN" not in fsx:
            continue
        mean, wr = fsx["MEAN"], fsx["WIN_RATE"]
        rate = "n/a" if wr.get("win_rate") is None else f"{wr['win_rate']:.1%}"
        out += [
            "",
            f"## {fam} (counted at each look; direction {fsx['direction']:+d}; `{fsx['protocol']['id']}`)",
            "",
            f"Sets {fsx['n_sets']} over {fsx['sessions']} signal sessions; events seen: "
            f"{', '.join(f'{k} {v}' for k, v in fsx['events_seen'].items()) or 'none'}; coverage gaps {fsx['coverage_gaps']}.",
            f"- MEAN (signed edge over the twins) {_pct(mean.get('mean_diff'))} over {mean.get('n_paired', 0)} pairs: "
            f"**{mean['look']['verdict']}**",
            f"- WIN_RATE {wr.get('wins', 0)} of {wr.get('n_paired', 0)} ({rate}): **{wr['look']['verdict']}**",
        ]
        if fsx.get(
            "coverage_class"
        ):  # the 2026-10-29 families: name the decision sample, then the descriptive ones
            out.insert(
                len(out) - 2,
                f"Decision sample: {fsx['coverage_class']} sets, window {fsx['window']}, "
                f"{fsx['descriptive'].get('entry_weeks', 0)} distinct entry week(s).",
            )
            classes = fsx["descriptive"].get("classes", {})
            out.append(
                "- Classes: " + (", ".join(f"{k} {v}" for k, v in classes.items()) or "none")
            )
            for key, d in fsx["descriptive"].items():
                if isinstance(d, dict) and "n_paired" in d:
                    out.append(
                        f"- Descriptive {key}: {_pct(d.get('mean_diff'))} over {d.get('n_paired', 0)} pairs"
                    )
    dc = stats.get("document_class")
    if dc:
        m, wr = dc["MEAN"], dc["win_rate_descriptive"]
        out += [
            "",
            f"## DOCUMENT_CLASS (pooled, pre-registered; `{dc['design']['id']}`)",
            "",
            f"Families {', '.join(dc['families'])}, parents only, one record per set; the paired excess signed by "
            f"direction; window H20, FIRE sets.",
            f"- MEAN (signed edge over the twins) {_pct(m.get('mean_diff'))} over {m.get('n_paired', 0)} pairs in "
            f"{m.get('n_sessions', 0)} sessions: **{m['look']['verdict']}**",
            "- Win rate (descriptive, never a primary): "
            + (
                f"{wr['wins']} of {wr['n']} ({wr['rate']:.1%})"
                if wr["rate"] is not None
                else "none yet"
            ),
            "- By family: "
            + ", ".join(
                f"{f} {v.get('n_paired', 0)} ({_pct(v.get('mean_diff'))})"
                for f, v in dc["by_family"].items()
            ),
            "- By price band: "
            + ", ".join(
                f"{k} {v.get('n_paired', 0)} ({_pct(v.get('mean_diff'))})"
                for k, v in dc["by_price_band"].items()
            ),
        ]
    tg = stats["tags"]["DILUTION_RECENT"]
    out += [
        "",
        "## Calibration",
        "",
        "| Family | Statement | n | Realised | Mean prior | Twins | Brier | Brier at 0.5 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for fam, fs in stats["families"].items():
        for cid, c in fs["calibration"].items():
            if c["n"]:
                twr = "n/a" if c["twins_rate"] is None else f"{c['twins_rate']:.2f}"
                out.append(
                    f"| {fam} | {cid} | {c['n']} | {c['realised_rate']:.2f} | {c['mean_prior']:.2f} | "
                    f"{twr} | {c['brier']:.3f} | {c['brier_uninformed']:.3f} |"
                )
            else:
                out.append(f"| {fam} | {cid} | 0 | | | | | |")
    out += [
        "",
        "## DILUTION_RECENT tags on Speculation Register sets",
        "",
        f"{tg['n']} tags: {tg['true']} true, {tg['unknown']} unknown.",
        "",
        "## Latest sets",
        "",
    ]
    out += [card(s) for s in sets[-15:]] or ["(none yet)"]
    return "\n".join(out) + "\n"


def write_report() -> Path:
    records = cat_lines()
    REPORT.write_text(render(statistics(records), records), encoding="utf-8")
    return REPORT


# ------------------------------------------------------------------------------- verify
def verify() -> list[str]:
    problems = []
    try:
        paper.latest_resolutions(cat_lines())
    except ValueError as exc:
        problems.append(str(exc))
    if not CAT_LEDGER.exists():
        return problems
    problems += [f"catalysts.jsonl: {p}" for p in paper.verify_chain(CAT_LEDGER)]
    _, proto_sha = protocol()
    fam_sha = {k: v[1] for k, v in extra_families().items()}
    scans = {r["scan_id"]: r for r in paper.ledger_lines() if r["type"] == "SCAN"}
    specs = {r["set_id"]: r for r in spec.spec_lines() if r["type"] == "SPECULATION_SET"}
    sets, listed, tags, seen = {}, set(), set(), set()
    for r in cat_lines():
        t = r["type"]
        if t == "BATCH":
            listed |= {e.get("set_id") for e in r["events"] if e["status"] == "SEALED"}
            ff = r.get("filings_file")
            if ff:
                path = PKG_ROOT / ff["path"]
                if not path.exists() or sha256_file(path) != ff["sha256"]:
                    problems.append(
                        f"batch {r['sealed_at']} ({r['family']}): filings file {ff['path']} missing or changed"
                    )
            if r["protocol"]["sha256"] != fam_sha.get(r["family"], proto_sha):
                problems.append(
                    f"batch {r['sealed_at']}: protocol sha256 differs from protocol.json"
                )
        elif t == "CATALYST_SET":
            sid = r["set_id"]
            if sid in sets:
                problems.append(f"{sid}: sealed twice")
            sets[sid] = r
            if r["sealed_at"] >= r["entry_cutoff"]:
                problems.append(
                    f"{sid}: sealed at {r['sealed_at']}, after its cutoff {r['entry_cutoff']}"
                )
            if r["protocol"]["sha256"] != fam_sha.get(r["family"], proto_sha):
                problems.append(
                    f"{sid}: protocol sha256 differs from its family's frozen protocol file"
                )
            if r.get("preregistration") and r["preregistration"]["sha256"] != prereg()[1]:
                problems.append(
                    f"{sid}: preregistration sha256 differs from research/CATALYST_REGISTER_v1/prereg_2.json"
                )
            sc = scans.get(r["scan_id"])
            if (
                sc is None
                or sc["record_hash"] != r["scan_record_hash"]
                or sc["features_sha256"] != r["features_sha256"]
            ):
                problems.append(f"{sid}: scan record or features hash does not match the ledger")
            if sid not in listed:
                problems.append(f"{sid}: not listed as SEALED by a batch before it")
            par = r.get("parent")
            if r["family"] in PARENT_FAMILY:
                ps = sets.get(par["set_id"]) if par else None
                if (
                    ps is None
                    or ps["family"] != PARENT_FAMILY[r["family"]]
                    or ps.get("record_hash") != par["record_hash"]
                    or ps["signal_session"] != r["signal_session"]
                    or ps["entry"]["session"] != r["entry"]["session"]
                ):
                    problems.append(
                        f"{sid}: binds no earlier {PARENT_FAMILY[r['family']]} set with that hash and sessions"
                    )
            if r["family"] == "IDX_INDEX":
                path = PKG_ROOT / r["event"]["events_file"]
                if not path.exists() or sha256_file(path) != r["event"]["events_sha256"]:
                    problems.append(f"{sid}: events file missing or changed")
        elif t == "TAG":
            key = (r["set_id"], r["tag"])
            if key in tags:
                problems.append(f"{r['set_id']}: tagged {r['tag']} twice")
            tags.add(key)
            s = specs.get(r["set_id"])
            if s is None or s.get("record_hash") != r["set_record_hash"]:
                problems.append(
                    f"{r['set_id']}: tag binds no Speculation Register set with that hash"
                )
            if r["sealed_at"] >= r["set_entry_cutoff"]:
                problems.append(
                    f"{r['set_id']}: tag sealed at {r['sealed_at']}, after the set's cutoff"
                )
        elif t == "RESOLUTION":
            key = (r["set_id"], r["window"])
            s = sets.get(r["set_id"])
            if s is None:
                problems.append(f"{r['set_id']}/{r['window']}: resolution without a set")
            elif r["window"] not in s["windows"]:
                problems.append(f"{r['set_id']}/{r['window']}: unknown window")
            if key in seen and not r.get("revises"):
                problems.append(f"{r['set_id']}/{r['window']}: resolved twice without `revises`")
            seen.add(key)
        else:
            problems.append(f"unknown record type {t!r}")
    return problems
