"""Binance spot daily klines for every USDT pair, including delisted ones (status BREAK).

Source: data-api.binance.vision, Binance's public market-data mirror (the main API is
geo-blocked from here). exchangeInfo still lists delisted pairs, and their klines remain
served, so the universe is not survivor-only for pairs Binance ever listed against USDT
and still describes. Times are UTC; a "session" is a UTC day. The candle of the current UTC
day is still forming and is dropped by the loader, never by the fetch.
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

from ..provenance import RAW, rel, sha256_bytes, utc_stamp, write_manifest

BASE = "https://data-api.binance.vision/api/v3"
HEADERS = {"User-Agent": "Mozilla/5.0 (research harness)"}
TERMS = "Binance public market data (data-api.binance.vision); research use"


def _get(url: str, retries: int = 6) -> tuple[int, bytes]:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (418, 429, 500, 502, 503, 504) or attempt == retries - 1:
                return exc.code, exc.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                return 0, b""
        time.sleep(2 * 2 ** attempt)
    return 0, b""


def _symbol(sym: str, st: str, base: str, t0: int, out_dir: Path, sleep: float) -> dict:
    path = out_dir / f"{sym}.json"
    rows, cursor, last_status = [], t0, 200
    while True:
        last_status, chunk = _get(f"{BASE}/klines?symbol={quote_url(sym)}&interval=1d&startTime={cursor}&limit=1000")
        if last_status != 200:
            break
        part = json.loads(chunk)
        rows += part
        if len(part) < 1000:
            break
        cursor = part[-1][0] + 86_400_000
        time.sleep(sleep)
    raw = json.dumps(rows, separators=(",", ":")).encode()
    path.write_bytes(raw)
    day = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()  # noqa: E731
    return {"symbol": sym, "base_asset": base, "status": st, "path": rel(path),
            "source_url": f"{BASE}/klines?symbol={sym}&interval=1d&startTime={t0}", "http_status": last_status,
            "downloaded_at": utc_stamp(), "rows": len(rows), "sha256": sha256_bytes(raw),
            "first_date": day(rows[0][0]) if rows else None, "last_date": day(rows[-1][0]) if rows else None,
            "terms": TERMS}


def fetch(start: str = "2020-01-01", quote: str = "USDT", sleep: float = 0.1, log=print, workers: int = 6,
          out_dir: Path | None = None) -> Path:
    """Resumable: symbols already recorded in out_dir/_progress.jsonl are not fetched again."""
    started = datetime.now(timezone.utc)
    out_dir = out_dir or RAW / "binance" / started.strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    info_path = out_dir / "exchangeInfo.json"
    if not info_path.exists():
        _, body = _get(f"{BASE}/exchangeInfo?permissions=SPOT")
        info_path.write_bytes(body)
    body = info_path.read_bytes()
    info = json.loads(body)
    pairs = sorted((s["symbol"], s["status"], s["baseAsset"]) for s in info["symbols"] if s["quoteAsset"] == quote)
    t0 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp() * 1000)
    progress = out_dir / "_progress.jsonl"
    done = {}
    if progress.exists():
        for line in progress.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec["http_status"] == 200:
                done[rec["symbol"]] = rec
    lock = threading.Lock()

    def one(pair):
        rec = _symbol(*pair, t0, out_dir, sleep)
        with lock:
            prog.write(json.dumps(rec, sort_keys=True) + "\n")
            prog.flush()
            done[rec["symbol"]] = rec
            if len(done) % 50 == 0:
                log(f"binance {len(done)}/{len(pairs)} {rec['symbol']} {rec['status']} rows={rec['rows']}")

    with progress.open("a", encoding="utf-8") as prog:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(one, [p for p in pairs if p[0] not in done]))
    records = [{"symbol": "_exchangeInfo", "path": rel(info_path), "http_status": 200, "sha256": sha256_bytes(body),
                "downloaded_at": utc_stamp(), "pairs": len(pairs)}]
    records += [done[p[0]] for p in pairs if p[0] in done]
    header = {"source": "binance_spot_klines_1d", "quote": quote, "start": start, "started_at": utc_stamp(started),
              "finished_at": utc_stamp(), "pairs": len(pairs), "fetched": len(records) - 1,
              "trading": sum(1 for p in pairs if p[1] == "TRADING"),
              "delisted_or_halted": sum(1 for p in pairs if p[1] != "TRADING"), "raw_dir": rel(out_dir)}
    return write_manifest(f"binance-{started.strftime('%Y%m%dT%H%M%SZ')}.jsonl", header, records)
