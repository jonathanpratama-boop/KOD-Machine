"""Score sealed, source-only historical guidance decisions using modeled daily fills."""

import argparse
import hashlib
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import certifi

from idxsig.guidance_margin_trial import POLICY
from idxsig.guidance_revision import session_schedule
from idxsig.provenance import publish_bytes

NY = ZoneInfo("America/New_York")
HORIZONS = [*POLICY["descriptive_sessions"], POLICY["hold_sessions"]]
SLOT = Decimal(POLICY["slot_usd"])
FEE = Decimal(POLICY["cost_per_side_fraction"])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(record):
    return (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def write_once(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"{path.name} already contains a different record")
        return
    publish_bytes(path, data)


def load_decisions(decisions, seal):
    raw = decisions.read_bytes()
    seal_record = json.loads(seal.read_text())
    expected = seal_record["decisions_sha256"]
    if expected != sha(raw):
        raise ValueError("Decisions differ from frozen receipt")
    data = json.loads(raw)
    rows = data["decisions"] if isinstance(data, dict) else data
    if "cohort_sha256" in seal_record:
        cohort_raw = decisions.with_name("cohort.json").read_bytes()
        if sha(cohort_raw) != seal_record["cohort_sha256"]:
            raise ValueError("Historical cohort differs from frozen receipt")
        membership = {r["id"]: r for r in json.loads(cohort_raw)}
        if set(membership) != {r["event_id"] for r in rows}:
            raise ValueError("Decision set does not cover the entire historical cohort")
        for row in rows:
            member = membership[row["event_id"]]
            if (row["ticker"], row["release_published_at"], row["source_sha256"]) != (
                    member["ticker"], member["at"], member["hash"]):
                raise ValueError("Decision differs from source identity in the frozen cohort")
            row["issuer_cik"] = member["cik"]
    seen = set()
    for row in rows:
        if row["event_id"] in seen:
            raise ValueError("Duplicate event ID")
        seen.add(row["event_id"])
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", row["ticker"]):
            raise ValueError("Unknown ticker format")
        if not all(type(row[key]) is bool for key in ["eligible", "revenue_buy", "margin_buy"]):
            raise ValueError("Missing explicit arm decisions")
        if row["margin_buy"] and not row["revenue_buy"]:
            raise ValueError("Margin arm can't buy outside revenue arm")
        if row["revenue_buy"] and not row["eligible"]:
            raise ValueError("Invalid buy on ineligible event")
    return rows, expected


def periods(row):
    import exchange_calendars as xc

    schedule = session_schedule(row.get("decision_at") or row["release_published_at"],
                                row["release_published_at"], POLICY)
    if not schedule["source_fresh"]:
        raise ValueError("Decision outside source freshness window")
    first = schedule["entry_session"]
    last = schedule["time_exit_session"]
    days = xc.get_calendar("XNYS", start=first, end=last).sessions
    dates = {n: days[n - 1].date().isoformat() for n in HORIZONS}
    assert dates[1] == first and dates[20] == last
    return schedule, dates


def get_chart(folder, ticker, first, last):
    def epoch(day, plus):
        stamp = datetime.fromisoformat(day).replace(tzinfo=NY) + timedelta(days=plus)
        return int(stamp.timestamp())
    query = urllib.parse.urlencode({"period1": epoch(first, -1), "period2": epoch(last, 2),
                                    "interval": "1d", "events": "div,splits"})
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(ticker) + "?" + query
    folder.mkdir(exist_ok=True, parents=True)
    receipt = folder / f"{ticker}_{first}_{last}.receipt.json"
    if receipt.exists():
        info = json.loads(receipt.read_text())
        raw = (folder / (info["sha256"] + ".json")).read_bytes()
        if info["sha256"] != sha(raw) or info["url"] != url:
            raise ValueError("Price cache does not match receipt")
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 KOD paper research"})
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=25, context=context) as response:
            raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError("Price response too large")
        result = json.loads(raw)["chart"]
        if result.get("error") or not result.get("result"):
            raise ValueError("Price provider did not cover ticker")
        info = {"url": url, "sha256": sha(raw), "fetched_at": datetime.now(timezone.utc).isoformat()}
        write_once(folder / (info["sha256"] + ".json"), raw)
        write_once(receipt, encode(info))
    return json.loads(raw)["chart"]["result"][0], info


def session_date(stamp):
    return datetime.fromtimestamp(stamp, NY).date().isoformat()


def price_marks(chart, ticker, horizons, margin_buy):
    meta = chart["meta"]
    if not (meta.get("symbol", "").upper().replace("-", ".") == ticker.replace("-", ".")
            and meta.get("currency") == "USD" and meta.get("instrumentType") == "EQUITY"
            and meta.get("exchangeTimezoneName") == "America/New_York"):
        raise ValueError("Ticker, currency or US equity session mismatch")
    dates = [session_date(stamp) for stamp in chart["timestamp"]]
    if len(dates) != len(set(dates)):
        raise ValueError("Ambiguous daily bar")
    quote = chart["indicators"]["quote"][0]
    actions = [session_date(a["date"]) for group in chart.get("events", {}).values()
               for a in group.values()]
    def valid_bar(day):
        if day not in dates:
            raise ValueError("Daily bar missing")
        idx = dates.index(day)
        try:
            op, hi, lo, close, vol = [Decimal(str(quote[k][idx]))
                                      for k in ["open", "high", "low", "close", "volume"]]
        except (ValueError, ArithmeticError, TypeError, IndexError, KeyError) as exc:
            raise ValueError("Incomplete OHLCV") from exc
        if not all(v.is_finite() and v > 0 for v in (op, hi, lo, close, vol)) or not (
                lo <= min(op, close) <= max(op, close) <= hi):
            raise ValueError("Invalid daily bar")
        return op, close
    first = horizons[1]
    entry, _ = valid_bar(first)
    if entry < Decimal(POLICY["minimum_entry_price"]):
        raise ValueError("Entry below price floor")
    marks = {}
    for horizon, date in horizons.items():
        try:
            if any(first <= action <= date for action in actions):
                raise ValueError("Reported split or dividend before mark")
            _, close = valid_bar(date)
            net = SLOT / (entry * (1 + FEE)) * close * (1 - FEE) - SLOT
            margin = net if margin_buy else Decimal(0)
            marks[str(horizon)] = {"session": date, "entry_open": str(entry), "close": str(close),
                                   "revenue_usd": str(net), "margin_usd": str(margin),
                                   "difference_usd": str(margin - net)}
        except ValueError as exc:
            marks[str(horizon)] = {"session": date, "unavailable": str(exc)}
    return marks


def summarize(results):
    summary = {}
    for horizon in HORIZONS:
        marks = [r["marks"][str(horizon)] for r in results if "marks" in r]
        pairs = [m for m in marks if "revenue_usd" in m]
        totals = {key: str(sum(Decimal(m[key]) for m in pairs)) if pairs else None
                  for key in ["revenue_usd", "margin_usd", "difference_usd"]}
        summary[str(horizon)] = {"scored_pairs": len(pairs), "informative_pairs": sum(
            not r["margin_buy"] for r in results if "revenue_usd" in r.get("marks", {}).get(str(horizon), {})),
            "unavailable": sum(r.get("entered", False) for r in results) - len(pairs), **totals}
    return summary


def run(decisions, seal, out):
    started = time.monotonic()
    rows, digest = load_decisions(decisions, seal)
    results = []
    occupied = {}
    peak_slots = 0
    for row in sorted(rows, key=lambda r: (r.get("decision_at") or r["release_published_at"], r["event_id"])):
        result = {k: row[k] for k in ["event_id", "ticker", "eligible", "revenue_buy", "margin_buy"]}
        results.append(result)
        if not row["eligible"] or not row["revenue_buy"]:
            result["excluded"] = row["reason"]
            continue
        schedule, dates = periods(row)
        previous = occupied.get(row["ticker"])
        if previous and previous >= dates[1]:
            result["excluded"] = "Overlapping position in the same issuer"
            continue
        occupied[row["ticker"]] = dates[20]
        peak_slots = max(peak_slots, sum(end >= dates[1] for end in occupied.values()))
        result.update(entered=True, schedule=schedule)
        try:
            symbol = row["ticker"]
            # Everpure confirmed its NYSE shares retained the same CUSIP.
            if (symbol == "PSTG" and str(row.get("issuer_cik")) == "1474432"
                    and dates[20] < "2026-04-17"):
                symbol = "P"
                result["ticker_change_source"] = (
                    "https://www.everpuredata.com/company/newsroom/press-releases/"
                    "everpure-to-change-ticker-symbol.html"
                )
            result["historical_price_lookup_symbol"] = symbol
            chart, source = get_chart(out / "prices", symbol, dates[1], dates[20])
            result["price_source"] = source
            result["marks"] = price_marks(chart, symbol, dates, row["margin_buy"])
        except (ValueError, OSError, KeyError, IndexError, TypeError) as exc:
            result["unavailable"] = str(exc)
    report = {"study": "Historical guidance replay", "decisions_sha256": digest,
              "design": "Descriptive fixed-slot event P&L (USD), not a portfolio backtest or live fills.",
              "source": "US daily chart. Provider-reported corporate actions through each horizon exclude the mark. Prices and event metadata can be revised.",
              "release_count": len(rows), "max_simultaneous_scheduled_slots": peak_slots,
              "overlapping_issuer_exclusions": sum(r.get("excluded") == "Overlapping position in the same issuer" for r in results),
              "capital_policy": "Independent event comparison; aggregate P&L does not model cash, portfolio returns or drawdowns.",
              "revenue_signals": sum(r["revenue_buy"] for r in rows),
              "margin_signals": sum(r["margin_buy"] for r in rows), "horizons": summarize(results),
              "events": results}
    raw = encode(report)
    out.mkdir(exist_ok=True, parents=True)
    write_once(out / ("result-" + sha(raw) + ".json"), raw)
    publish_bytes(out / "result.json", raw, replace=True)
    print(json.dumps({"seconds": round(time.monotonic()-started, 1), "horizons": report["horizons"]}))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["decisions", "seal", "out"]:
        p.add_argument("--" + name, required=True, type=Path)
    args = p.parse_args()
    run(args.decisions, args.seal, args.out)
