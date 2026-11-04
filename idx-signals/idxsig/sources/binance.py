"""Binance spot daily klines for every USDT pair, including delisted ones (status BREAK).

Source: data-api.binance.vision, Binance's public market-data mirror (the main API is
geo-blocked from here). exchangeInfo still lists delisted pairs, and their klines remain
served, so the universe is not survivor-only for pairs Binance ever listed against USDT
and still describes. Times are UTC; a "session" is a UTC day. The candle of the current UTC
day is still forming. New bound requests end before that UTC day begins, so a
resumed download cannot later promote a cached partial candle into a complete one.
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
from urllib.parse import quote as quote_url
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ..provenance import (
    publish_bytes,
    RAW,
    PKG_ROOT,
    exclusive_lock,
    rel,
    sha256_bytes,
    utc_stamp,
    write_manifest,
)
from .resume import bind_request, canonical, publish, save_raw, verify_cached

BASE = "https://data-api.binance.vision/api/v3"
HEADERS = {"User-Agent": "Mozilla/5.0 (research harness)"}
TERMS = "Binance public market data (data-api.binance.vision); research use"


def _get(url: str, retries: int = 6) -> tuple[int, bytes]:
    """Retry transient server failures only; access/rate blocks end this pull."""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=HEADERS), timeout=60
            ) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (500, 502, 503, 504) or attempt == retries - 1:
                return exc.code, exc.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                return 0, b""
        time.sleep(2 * 2**attempt)
    return 0, b""


def _symbol(
    sym: str, st: str, base: str, t0: int, out_dir: Path, sleep: float, end_ms: int | None = None
) -> dict:
    path = out_dir / f"{sym}.json"
    rows, cursor, last_status = [], t0, 200
    end_query = f"&endTime={end_ms}" if end_ms is not None else ""
    while True:
        last_status, chunk = _get(
            f"{BASE}/klines?symbol={quote_url(sym)}&interval=1d&startTime={cursor}&limit=1000{end_query}"
        )
        if last_status != 200:
            break
        part = json.loads(chunk)
        rows += [r for r in part if end_ms is None or (r[0] <= end_ms and r[6] <= end_ms)]
        if len(part) < 1000:
            break
        cursor = part[-1][0] + 86_400_000
        if end_ms is not None and cursor > end_ms:
            break
        time.sleep(sleep)
    raw = json.dumps(rows, separators=(",", ":")).encode()
    path = save_raw(path, raw)
    day = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()  # noqa: E731
    return {
        "symbol": sym,
        "base_asset": base,
        "status": st,
        "path": rel(path),
        "source_url": f"{BASE}/klines?symbol={quote_url(sym)}&interval=1d&startTime={t0}{end_query}",
        "http_status": last_status,
        "downloaded_at": utc_stamp(),
        "rows": len(rows),
        "sha256": sha256_bytes(raw),
        "first_date": day(rows[0][0]) if rows else None,
        "last_date": day(rows[-1][0]) if rows else None,
        "terms": TERMS,
    }


def fetch(
    start: str = "2020-01-01",
    quote: str = "USDT",
    sleep: float = 0.1,
    log=print,
    workers: int = 6,
    out_dir: Path | None = None,
    only_trading: bool = False,
    prefix: str = "binance",
) -> Path:
    """Resumable: symbols already recorded in out_dir/_progress.jsonl are not fetched again.

    only_trading: skip pairs not currently TRADING (live scans, which cannot buy a halted pair);
    written under a different manifest prefix so a panel build never takes a short pull."""
    started = datetime.now(timezone.utc)
    out_dir = out_dir or RAW / prefix / started.strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(out_dir / "_download"):
        t0 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp() * 1000)
        request = {
            "provider": "binance_spot_klines_1d",
            "endpoint": BASE,
            "interval": "1d",
            "start": start,
            "quote": quote,
            "only_trading": only_trading,
            "prefix": prefix,
            "closed_utc_days_only": True,
            "adapter": "binance-request-v1",
        }
        end_ms = (
            int(started.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000) - 1
        )
        bound = bind_request(
            out_dir, request, {"start_ms": t0, "end_ms": end_ms}, utc_stamp(started)
        )
        t0, end_ms = bound["window"]["start_ms"], bound["window"]["end_ms"]
        snapshot = out_dir / "_exchangeInfo.json"
        if snapshot.exists():
            info_record = json.loads(snapshot.read_text(encoding="utf-8"))
            verify_cached(info_record, out_dir)
            if info_record.get("request_sha256") != bound["sha256"]:
                raise ValueError("exchangeInfo snapshot belongs to a different pinned request")
            info_path = PKG_ROOT / info_record["path"]
            body = info_path.read_bytes()
        else:
            status, body = _get(f"{BASE}/exchangeInfo?permissions=SPOT")
            if status != 200:
                raise RuntimeError(
                    f"exchangeInfo download failed: HTTP {status}; no universe was pinned"
                )
            if not isinstance(json.loads(body).get("symbols"), list):
                raise ValueError("exchangeInfo response has no symbols list")
            info_path = save_raw(out_dir / "exchangeInfo.json", body)
            info_record = {
                "symbol": "_exchangeInfo",
                "path": rel(info_path),
                "http_status": status,
                "sha256": sha256_bytes(body),
                "downloaded_at": utc_stamp(),
                "source_url": f"{BASE}/exchangeInfo?permissions=SPOT",
                "request_sha256": bound["sha256"],
            }
            publish(snapshot, canonical(info_record) + b"\n")
        info = json.loads(body)
        pairs = sorted(
            (s["symbol"], s["status"], s["baseAsset"])
            for s in info["symbols"]
            if s["quoteAsset"] == quote and (not only_trading or s["status"] == "TRADING")
        )
        progress = out_dir / "_progress.jsonl"
        done = {}
        if progress.exists():
            for line in progress.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if rec["http_status"] == 200:
                    verify_cached(rec, out_dir)
                    done[rec["symbol"]] = rec
        lock = threading.Lock()

        def one(pair):
            rec = _symbol(*pair, t0, out_dir, sleep, end_ms=end_ms)
            with lock:
                before = progress.read_bytes() if progress.exists() else b""
                publish_bytes(
                    progress,
                    before + (json.dumps(rec, sort_keys=True) + "\n").encode(),
                    replace=True,
                )
                done[rec["symbol"]] = rec
                if len(done) % 50 == 0:
                    log(
                        f"binance {len(done)}/{len(pairs)} {rec['symbol']} {rec['status']} rows={rec['rows']}"
                    )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(one, [p for p in pairs if p[0] not in done]))
        records = [{**info_record, "pairs": len(pairs)}]
        records += [done[p[0]] for p in pairs if p[0] in done]
        header = {
            "source": "binance_spot_klines_1d",
            "quote": quote,
            "start": start,
            "started_at": bound["started_at"],
            "request": bound,
            "coverage_window": bound["window"],
            "universe_sha256": info_record["sha256"],
            "finished_at": utc_stamp(),
            "pairs": len(pairs),
            "fetched": len(records) - 1,
            "trading": sum(1 for p in pairs if p[1] == "TRADING"),
            "only_trading": only_trading,
            "delisted_or_halted": sum(1 for p in pairs if p[1] != "TRADING"),
            "raw_dir": rel(out_dir),
        }
        return write_manifest(
            f"{prefix}-{started.strftime('%Y%m%dT%H%M%SZ')}.jsonl", header, records
        )
