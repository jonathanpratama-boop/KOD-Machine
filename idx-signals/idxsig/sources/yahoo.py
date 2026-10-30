"""Yahoo Finance chart API, one raw JSON file per IDX ticker (`<TICKER>.JK`).

Coverage: names Yahoo still lists. Yahoo drops delisted IDX tickers (they return
"No data found, symbol may be delisted"), so this source alone is survivor-only. Every
request is logged, including the not-found ones, so the gap is visible in the manifest.

Prices in the response are split-adjusted (not dividend-adjusted). The panel builder
undoes the split adjustment so lots, ticks and auto-rejection limits apply to the prices
that actually traded.
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ..provenance import publish_bytes, RAW, exclusive_lock, rel, sha256_bytes, utc_stamp, write_manifest
from .resume import bind_request, save_raw, verify_cached

CHART = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
)
SOURCE = "yahoo_chart_v8"
TERMS = "Yahoo Finance data; personal and research use under Yahoo's terms of service"
HEADERS = {"User-Agent": "Mozilla/5.0 (idx-signals research harness)", "Accept": "application/json"}


def _summary(payload: dict) -> dict:
    chart = payload.get("chart") or {}
    if chart.get("error"):
        return {"error": chart["error"].get("description") or str(chart["error"])}
    result = (chart.get("result") or [None])[0] or {}
    stamps = result.get("timestamp") or []
    events = result.get("events") or {}
    day = lambda s: datetime.fromtimestamp(s, timezone.utc).date().isoformat()  # noqa: E731
    return {
        "rows": len(stamps),
        "first_date": day(stamps[0]) if stamps else None,
        "last_date": day(stamps[-1]) if stamps else None,
        "splits": len(events.get("splits") or {}),
        "dividends": len(events.get("dividends") or {}),
        "currency": (result.get("meta") or {}).get("currency"),
        "exchange": (result.get("meta") or {}).get("exchangeName"),
    }


def fetch_one(ticker: str, p2: int, retries: int = 6, pause: float = 2.0, p1: int = 0,
              suffix: str = ".JK") -> tuple[int, bytes, str]:
    url = CHART.format(symbol=f"{ticker}{suffix}", p1=p1, p2=p2)
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read(), url
        except urllib.error.HTTPError as exc:
            body = exc.read()
            if exc.code == 404:
                return 404, body, url
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                return exc.code, body, url
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == retries - 1:
                return 0, str(exc).encode(), url
        time.sleep(pause * 2 ** attempt)
    return 0, b"", url


def fetch(tickers: list[str], out_dir: Path | None = None, sleep: float = 0.35, log=print,
          finalize: bool = True, days: int | None = None, prefix: str = "yahoo", suffix: str = ".JK",
          start: str | None = None, workers: int = 1) -> Path | None:
    """Fetch every ticker, resumable. Writes the manifest when `finalize`; returns its path.

    days: only the last `days` calendar days (live scans), written under a different
    manifest prefix so the panel builder never takes a short pull for full history."""
    started = datetime.now(timezone.utc)
    if days is not None and (isinstance(days, bool) or not isinstance(days, int) or days < 1):
        raise ValueError("days must be a positive integer")
    if days is not None and start is not None:
        raise ValueError("choose start or days, not both")
    if (days is not None or start is not None or suffix != ".JK") and prefix == "yahoo":
        raise ValueError("a partial or non-IDX pull needs its own manifest prefix")
    p1 = 0 if days is None else int(started.timestamp()) - days * 86400
    if start is not None:
        p1 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
    out_dir = out_dir or RAW / prefix / started.strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(out_dir / "_download"):
        request = {"provider": SOURCE, "endpoint": CHART, "interval": "1d", "start": start,
                   "days": days, "suffix": suffix, "prefix": prefix, "tickers": sorted(set(tickers)),
                   "adapter": "yahoo-request-v1"}
        bound = bind_request(out_dir, request, {"p1": p1, "p2": int(started.timestamp())}, utc_stamp(started))
        p1, p2 = bound["window"]["p1"], bound["window"]["p2"]
        progress = out_dir / "_progress.jsonl"
        done = {}
        if progress.exists():
            for line in progress.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if rec["http_status"] in (200, 404):
                    verify_cached(rec, out_dir)
                    done[rec["ticker"]] = rec
        lock = threading.Lock()

        def one(ticker):
            status, body, url = fetch_one(ticker, p2, p1=p1, suffix=suffix)
            stamp = utc_stamp()
            ext = f"{suffix}.json" if status == 200 else f"{suffix}.error.json"
            path = out_dir / f"{ticker}{ext}"
            path = save_raw(path, body)
            try:
                summary = _summary(json.loads(body))
            except (json.JSONDecodeError, UnicodeDecodeError):
                summary = {"error": "response was not JSON"}
            rec = {"ticker": ticker, "path": rel(path), "source": SOURCE, "source_url": url, "downloaded_at": stamp,
                   "http_status": status, "bytes": len(body), "sha256": sha256_bytes(body), "terms": TERMS, **summary}
            with lock:
                before = progress.read_bytes() if progress.exists() else b""
                publish_bytes(progress, before + (json.dumps(rec, sort_keys=True) + "\n").encode(), replace=True)
                done[ticker] = rec
                if len(done) % 100 == 0:
                    log(f"yahoo {len(done)}/{len(set(tickers))} {ticker} {status}")
            time.sleep(sleep)

        todo = [t for t in sorted(set(tickers)) if t not in done]
        if workers <= 1:
            for t in todo:
                one(t)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(one, todo))
        if not finalize:
            return None
        records = [done[t] for t in sorted(done) if t in set(tickers)]
        header = {
            "source": SOURCE,
            "request": bound,
            "coverage_window": bound["window"],
            "description": "Yahoo Finance v8 chart, daily bars, " + (
                f"from {start}" if start else "full history" if days is None else f"{days}-day window pinned at {bound['started_at']}")
                           + ", split events and dividends" + (f", symbols suffixed {suffix!r}" if suffix else ", US symbols"),
            "started_at": bound["started_at"],
            "finished_at": utc_stamp(),
            "raw_dir": rel(out_dir),
            "requested": len(set(tickers)),
            "ok": sum(1 for r in records if r["http_status"] == 200 and r.get("rows")),
            "not_found": sum(1 for r in records if r["http_status"] == 404),
            "failed": sum(1 for r in records if r["http_status"] not in (200, 404)),
        }
        return write_manifest(f"{prefix}-{started.strftime('%Y%m%dT%H%M%SZ')}.jsonl", header, records)

