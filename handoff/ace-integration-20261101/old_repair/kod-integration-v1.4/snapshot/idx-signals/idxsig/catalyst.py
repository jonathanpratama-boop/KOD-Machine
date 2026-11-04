"""E9 catalyst split (research/E9): SEC filings known before an entry, and the class of a signal.

Pure functions over EDGAR submissions JSON (data.sec.gov/submissions/CIK##########.json and its chunk
files). No network access here; research/E9/collect_sec.py fetches and caches the responses.

Information known at entry: a filing counts for a signal at the close of session s (entry at the open of
session e) if its acceptance time is after 16:00 New York time on session s-1 and at or before 09:15 New
York time on session e. Classes, first match wins: DILUTION, DOCUMENTED, UNDOCUMENTED.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

NY = ZoneInfo("America/New_York")
WINDOW_OPEN = time(16, 0)  # after the close of session s-1
WINDOW_CLOSE = time(9, 15)  # 15 minutes before the 09:30 open of the entry session
DILUTION_FORMS = frozenset(
    {
        "424B1",
        "424B2",
        "424B3",
        "424B4",
        "424B5",
        "424B7",
        "424B8",
        "S-1",
        "S-1/A",
        "S-1MEF",
        "S-3",
        "S-3/A",
        "S-3ASR",
        "S-3MEF",
        "F-1",
        "F-1/A",
        "F-1MEF",
        "F-3",
        "F-3/A",
        "F-3ASR",
        "F-3MEF",
        "EFFECT",
    }
)
DILUTION_8K_ITEMS = frozenset({"3.02"})
INFO_FORMS = frozenset(
    {
        "8-K",
        "8-K/A",
        "6-K",
        "6-K/A",
        "10-Q",
        "10-Q/A",
        "10-K",
        "10-K/A",
        "20-F",
        "20-F/A",
        "40-F",
        "SC 13D",
        "SC 13D/A",
        "SC TO-T",
        "SC TO-T/A",
        "SC TO-C",
        "SC 14D9",
        "DEFM14A",
        "PREM14A",
        "425",
    }
)
CLASSES = ("DILUTION", "DOCUMENTED", "UNDOCUMENTED")
COLUMNS = (
    "accessionNumber",
    "filingDate",
    "acceptanceDateTime",
    "form",
    "items",
    "primaryDocument",
)


def filings_frame(blob: dict) -> pd.DataFrame:
    """Columnar filings block (submissions 'filings.recent', or a chunk file) to a DataFrame."""
    cols = {c: blob.get(c, []) for c in COLUMNS}
    n = len(cols["accessionNumber"])
    for c, v in cols.items():
        if len(v) != n:  # some chunks omit optional columns
            cols[c] = list(v) + [""] * (n - len(v))
    return pd.DataFrame(cols)


def parse_submissions(main_body: bytes, chunk_bodies: list[bytes]) -> pd.DataFrame:
    """Every filing in a submissions response plus its chunk files, de-duplicated by accession."""
    main = json.loads(main_body)
    parts = [filings_frame(main.get("filings", {}).get("recent", {}))]
    parts += [filings_frame(json.loads(b)) for b in chunk_bodies]
    df = pd.concat(parts, ignore_index=True).drop_duplicates("accessionNumber")
    for c in ("items", "form", "acceptanceDateTime"):
        df[c] = df[c].fillna("").astype(str)
    return df.reset_index(drop=True)


def chunk_names(main_body: bytes, start: str, end: str) -> list[str]:
    """Chunk files whose filing-date range overlaps [start, end]."""
    files = json.loads(main_body).get("filings", {}).get("files", [])
    return [
        f["name"]
        for f in files
        if f.get("filingFrom", "0000") <= end and f.get("filingTo", "9999") >= start
    ]


def header_acceptance(body: bytes) -> str | None:
    """<ACCEPTANCE-DATETIME> (YYYYMMDDHHMMSS, New York time) from a filing's -index-headers.html page."""
    m = re.search(rb"<ACCEPTANCE-DATETIME>\s*(\d{14})", body or b"")
    return m.group(1).decode() if m else None


def acceptance_ny(value: str, convention: str) -> datetime | None:
    """An acceptance time as an aware New York datetime. 'header': the filing's own SGML header value
    (YYYYMMDDHHMMSS, New York time; research/E9/FEASIBILITY_AMENDMENT_3.md). For the submissions JSON
    acceptanceDateTime: 'ny', the clock reading is New York time despite the 'Z'; 'utc', it is UTC; 'double',
    New York time converted to UTC twice. The JSON field mixes 'utc' and 'double' (amendment 3)."""
    if not isinstance(value, str) or not value.strip():
        return None
    if convention == "header":
        return datetime.strptime(value.strip()[:14], "%Y%m%d%H%M%S").replace(tzinfo=NY)
    naive = datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    utc = ZoneInfo("UTC")
    if convention == "ny":
        return naive.replace(tzinfo=NY)
    if convention == "utc":
        return naive.replace(tzinfo=utc).astimezone(NY)
    if (
        convention == "double"
    ):  # New York time converted to UTC twice (research/E9/FEASIBILITY_AMENDMENT_1.md)
        once = naive.replace(tzinfo=utc).astimezone(NY).replace(tzinfo=None)
        return once.replace(tzinfo=utc).astimezone(NY)
    raise ValueError(convention)


def accepted(filings: pd.DataFrame, convention: str) -> pd.Series:
    """Acceptance times as UTC timestamps; a filing without one is NaT, so it is in no window (it cannot be
    shown to be public before an open; research/E9/FEASIBILITY_AMENDMENT_2.md). 'header' reads the column
    acceptanceHeader (the caller's fetched SGML values), every other convention acceptanceDateTime."""
    col = "acceptanceHeader" if convention == "header" else "acceptanceDateTime"
    vals = [acceptance_ny(v, convention) for v in filings[col]] if len(filings) else []
    return pd.Series(
        pd.to_datetime(vals, utc=True), index=filings.index, dtype="datetime64[ns, UTC]"
    )


def window(prev_session: str, entry_session: str) -> tuple[datetime, datetime]:
    """(exclusive start, inclusive end) of the information window, New York time."""
    a = datetime.combine(datetime.fromisoformat(prev_session).date(), WINDOW_OPEN, tzinfo=NY)
    b = datetime.combine(datetime.fromisoformat(entry_session).date(), WINDOW_CLOSE, tzinfo=NY)
    return a, b


def items_of(s: str) -> set[str]:
    return {x.strip() for x in str(s).split(",") if x.strip()}


def is_dilution(form: str, items: str) -> bool:
    f = form.upper()
    return f in DILUTION_FORMS or (
        f in ("8-K", "8-K/A") and bool(items_of(items) & DILUTION_8K_ITEMS)
    )


def is_information(form: str) -> bool:
    return form.upper() in INFO_FORMS


def classify(filings: pd.DataFrame, start: datetime, end: datetime, convention: str) -> dict:
    """Class of one signal from its issuer's filings (columns as parse_submissions) in (start, end]."""
    acc = accepted(filings, convention)
    sel = (acc > pd.Timestamp(start)) & (acc <= pd.Timestamp(end))
    inside = filings[sel]
    when = [t.tz_convert(NY).strftime("%Y-%m-%dT%H:%M:%S") for t in acc[sel]]
    rows = list(zip(inside["form"], inside["accessionNumber"], inside["items"], when))
    dil = [r for r in rows if is_dilution(r[0], r[2])]
    info = [r for r in rows if is_information(r[0])]
    cls = "DILUTION" if dil else ("DOCUMENTED" if info else "UNDOCUMENTED")
    used = dil if dil else info
    return {
        "class": cls,
        "n_filings_in_window": int(len(inside)),
        "forms": ";".join(sorted({r[0] for r in rows})),
        "evidence": ";".join(f"{f}|{a}|{t} NY|{i}" for f, a, i, t in used[:6]),
        "items_8k": ";".join(
            sorted({i for r in info if r[0].upper().startswith("8-K") for i in items_of(r[2])})
        ),
    }


def later_documentation(
    filings: pd.DataFrame, entry_end: datetime, days: int, convention: str
) -> bool:
    """Diagnostic only (never a decision input): an information filing within `days` calendar days AFTER the
    entry cutoff, e.g. an 8-K that arrives after the press release."""
    acc = accepted(filings, convention)
    late = filings[
        (acc > pd.Timestamp(entry_end)) & (acc <= pd.Timestamp(entry_end + timedelta(days=days)))
    ]
    return any(is_information(f) for f in late["form"])
