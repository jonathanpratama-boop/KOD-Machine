"""Dated price observations: entered manually or imported from a strict local CSV. No feed, scraper or broker is involved.

Every price states its listing, currency, source, session, timezone, adjustment convention (raw, split-adjusted or total-return) and the coverage of the
feed it came from. A daily close is treated as available from the end of its trading day in the stated timezone; it is not an intraday fill. A CSV is
accepted whole or not at all: one malformed row rejects the file, with a report of every problem. Missing volume stays missing.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import io
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .domain import identity, timestamp

ADJUSTMENTS = ("raw", "split_adjusted", "total_return")
SESSIONS = ("regular_close", "official_close", "last_trade", "manual_quote")
MAX_ROWS = 20000
MAX_BYTES = 4 * 1024 * 1024
COLUMNS = ("date", "open", "high", "low", "close", "volume")
CURRENCY = re.compile(r"^[A-Z]{3}$")


class PriceError(ValueError):
    def __init__(self, problems):
        super().__init__(
            "; ".join(problems[:10])
            + (f" (and {len(problems) - 10} more)" if len(problems) > 10 else "")
        )
        self.problems = list(problems)


def _zone(name):
    try:
        return ZoneInfo(str(name))
    except (ZoneInfoNotFoundError, ValueError):
        return None


def available_at(day: str, zone: str) -> str:
    """A daily close is first usable at midnight after its trading day in the listing's timezone (a conservative bound; the close time is not recorded)."""
    moment = datetime.combine(
        date.fromisoformat(day) + timedelta(days=1), time(0, 0), tzinfo=ZoneInfo(zone)
    ).astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _metadata(meta: dict) -> tuple[dict, list]:
    problems = []
    currency = str(meta.get("currency") or "").upper()
    if not CURRENCY.match(currency):
        problems.append("currency must be a three-letter code")
    zone = str(meta.get("timezone") or "")
    if _zone(zone) is None:
        problems.append("timezone must be an IANA name such as America/New_York")
    if meta.get("adjustment") not in ADJUSTMENTS:
        problems.append("adjustment must be one of " + ", ".join(ADJUSTMENTS))
    if meta.get("session") not in SESSIONS:
        problems.append("session must be one of " + ", ".join(SESSIONS))
    for key in ("source", "feed_coverage"):
        if not str(meta.get(key) or "").strip() or len(str(meta.get(key))) > 300:
            problems.append(f"{key} is required (at most 300 characters)")
    return {
        "currency": currency,
        "timezone": zone,
        "adjustment": meta.get("adjustment"),
        "session": meta.get("session"),
        "source": str(meta.get("source") or "").strip(),
        "feed_coverage": str(meta.get("feed_coverage") or "").strip(),
    }, problems


def _price(text, name, row, problems, required=True):
    text = (text or "").strip().replace(",", "")
    if not text:
        if required:
            problems.append(f"row {row}: {name} is missing")
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        problems.append(f"row {row}: {name} is not a number ({text!r})")
        return None
    if not value.is_finite() or value <= 0:
        problems.append(f"row {row}: {name} must be a finite positive number")
        return None
    return value


def parse_csv(raw: bytes, meta: dict) -> dict:
    """{'rows': [...], 'coverage': {...}} from a CSV with a header row: date, close and optionally open, high, low, volume. Raises PriceError listing every
    problem; nothing is partially accepted."""
    meta, problems = _metadata(meta)
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
        problems.append(f"the file must contain 1 byte to {MAX_BYTES // (1024 * 1024)} MiB")
        raise PriceError(problems)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise PriceError(problems + ["the file is not UTF-8 text"])
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip().lower() for h in (reader.fieldnames or [])]
    unknown = [h for h in header if h not in COLUMNS]
    if "date" not in header or "close" not in header:
        problems.append("the header must name at least the columns date and close")
    if unknown:
        problems.append(
            "unknown columns: " + ", ".join(unknown) + " (allowed: " + ", ".join(COLUMNS) + ")"
        )
    if len(set(header)) != len(header):
        problems.append("a column is named twice")
    if problems:
        raise PriceError(problems)
    rows, seen = [], set()
    for n, record in enumerate(reader, start=2):
        if n - 1 > MAX_ROWS:
            problems.append(f"more than {MAX_ROWS} rows")
            break
        if None in record:
            problems.append(f"row {n}: more fields than the header")
            continue
        record = {str(k).strip().lower(): (v or "") for k, v in record.items()}
        day = record.get("date", "").strip()
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
                raise ValueError
            date.fromisoformat(day)
        except ValueError:
            problems.append(f"row {n}: date must be YYYY-MM-DD ({day!r})")
            continue
        if day in seen:
            problems.append(f"row {n}: duplicate date {day}")
            continue
        seen.add(day)
        close = _price(record.get("close"), "close", n, problems)
        o, h, l = (
            _price(record.get(k), k, n, problems, required=False) for k in ("open", "high", "low")
        )
        if any(v is not None for v in (o, h, l)) and None in (o, h, l):
            problems.append(f"row {n}: open, high and low must be given together")
        elif None not in (o, h, l, close) and not (
            l <= min(o, close) and max(o, close) <= h and l <= h
        ):
            problems.append(
                f"row {n}: open/high/low/close are not coherent (low <= open, close <= high)"
            )
        volume = (record.get("volume") or "").strip().replace(",", "")
        if volume:
            try:
                v = Decimal(volume)
                if not v.is_finite() or v < 0 or v != v.to_integral_value():
                    raise InvalidOperation
            except InvalidOperation:
                problems.append(f"row {n}: volume must be a whole non-negative number ({volume!r})")
        if close is not None:
            rows.append(
                {
                    "date": day,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": close,
                    "volume": volume or None,
                }
            )
    if not rows and not problems:
        problems.append("the file has no price rows")
    if problems:
        raise PriceError(problems)
    rows.sort(key=lambda r: r["date"])
    return {"meta": meta, "rows": rows, "coverage": coverage(rows)}


def coverage(rows: list) -> dict:
    """First and last date, row count and weekdays without a price (exchange holidays are not known here, so a gap is a gap, not an error)."""
    if not rows:
        return {"rows": 0}
    first, last = date.fromisoformat(rows[0]["date"]), date.fromisoformat(rows[-1]["date"])
    have = {r["date"] for r in rows}
    gaps = [
        d
        for d in (first + timedelta(days=i) for i in range((last - first).days + 1))
        if d.weekday() < 5 and d.isoformat() not in have
    ]
    return {
        "rows": len(rows),
        "first": first.isoformat(),
        "last": last.isoformat(),
        "weekdays_without_price": len(gaps),
        "first_gaps": [d.isoformat() for d in gaps[:10]],
        "volume_missing": sum(1 for r in rows if r["volume"] is None),
        "note": "weekday gaps may be exchange holidays or missing data; this importer does not know the exchange calendar",
    }


def manual(meta: dict, day: str, close, at: str | None = None) -> dict:
    """One manually entered price: a close for a day, or a quote at a stated time (session manual_quote)."""
    meta, problems = _metadata(meta)
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(day)):
            raise ValueError
        date.fromisoformat(day)
    except ValueError:
        problems.append("date must be YYYY-MM-DD")
    value = _price(str(close), "price", 1, problems)
    if meta.get("session") == "manual_quote":
        try:
            at = timestamp(at) if at else None
        except ValueError:
            at = None
        if not at:
            problems.append("a manual quote needs the timezone-aware time it was observed")
    elif at:
        problems.append("only a manual quote carries a time; a close is dated by its trading day")
    if problems:
        raise PriceError(problems)
    return {
        "meta": meta,
        "rows": [
            {
                "date": day,
                "open": None,
                "high": None,
                "low": None,
                "close": value,
                "volume": None,
                "at": at,
            }
        ],
        "coverage": coverage([{"date": day, "volume": None}]),
    }


def rows_for_store(
    parsed: dict,
    security_id: str,
    source_kind: str,
    observed_at: str,
    now: str,
    import_id: str | None = None,
) -> list:
    """Immutable price-observation rows (pure). A row's identity depends on what it says, not on when it was imported."""
    meta = parsed["meta"]
    out = []
    for r in parsed["rows"]:
        published = r.get("at") or available_at(r["date"], meta["timezone"])
        values = {
            k: (None if r.get(k) is None else str(r[k]))
            for k in ("open", "high", "low", "close", "volume")
        }
        pid = identity(
            "price",
            security_id,
            r["date"],
            meta["session"],
            meta["adjustment"],
            meta["source"],
            meta["currency"],
            values,
        )
        out.append(
            {
                "id": pid,
                "security_id": security_id,
                "observed_on": r["date"],
                "session": meta["session"],
                "timezone": meta["timezone"],
                "currency": meta["currency"],
                **values,
                "adjustment": meta["adjustment"],
                "source": meta["source"],
                "source_kind": source_kind,
                "feed_coverage": meta["feed_coverage"],
                "published_at": published,
                "publication_basis": (
                    "time of the manual quote"
                    if r.get("at")
                    else f"end of the trading day {r['date']} in {meta['timezone']}"
                ),
                "observed_at": observed_at,
                "recorded_at": now,
                "import_id": import_id,
            }
        )
    return out
