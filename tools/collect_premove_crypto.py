#!/usr/bin/env python3
"""Collect a new Binance daily-data vintage for the pre-move discovery benchmark.

Free archive catalog defines the universe before any labels are computed. The
runtime API supplies daily bars, including delisted pairs it still recognizes.
Failures are recorded explicitly, never mistaken for ordinary zero-return days.
Only 2020-2023 is supported here; existing sealed holdouts remain unread.
"""

from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idx-signals"))
from idxsig.global_panel import STABLE, LEVERAGED
from idxsig.provenance import publish_bytes

START_MS = 1577836800000
END_MS = 1704067199999
DAY_MS = 86400000
API = "https://data-api.binance.vision/api/v3/klines"
CATALOG = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"


def stamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(body):
    return hashlib.sha256(body).hexdigest()


def dump(path, value):
    publish_bytes(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def catalog_page(body):
    root = ET.fromstring(body)
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    pairs = [n.text.rstrip("/").rsplit("/", 1)[-1] for n in root.findall("CommonPrefixes/Prefix")]
    truncated = root.findtext("IsTruncated") == "true"
    return pairs, root.findtext("NextMarker"), truncated


def eligible_pair(pair):
    if not pair.endswith("USDT"):
        return False
    base = pair[:-4]
    return bool(base) and base not in STABLE and not LEVERAGED.search(base)


def rows_frame(rows, pair):
    """Strict UTC bounds and raw numerical prices; no future-informed deletion."""
    records = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 9:
            raise ValueError("malformed Binance kline")
        t = int(row[0])
        if t < START_MS or t + DAY_MS - 1 > END_MS:
            raise ValueError("response contains a row outside 2020-2023")
        close_time = int(row[6])
        if t % DAY_MS or not t <= close_time <= t + DAY_MS - 1:
            raise ValueError("unexpected daily bar boundary")
        values = [float(row[i]) for i in (1, 2, 3, 4, 5, 7)]
        import math

        if not all(math.isfinite(v) for v in values):
            raise ValueError("nonfinite Binance kline")
        o, h, low, c, v, q = values
        if min(o, h, low, c) <= 0 or min(v, q) < 0 or not low <= min(o, c) <= max(o, c) <= h:
            raise ValueError("invalid OHLCV")
        item = {
            "date": datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d"),
            "ticker": pair,
            "open": o,
            "high": h,
            "low": low,
            "close": c,
            "volume": v,
            "value": q,
            "complete_bar": close_time == t + DAY_MS - 1,
            "source": "binance",
        }
        if t in records and records[t] != item:
            raise ValueError("conflicting duplicate timestamp")
        records[t] = item
    return pd.DataFrame(
        [records[t] for t in sorted(records)],
        columns=[
            "date",
            "ticker",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "value",
            "complete_bar",
            "source",
        ],
    )


class Collector:
    def __init__(self, out, reuse=None):
        self.out = Path(out).resolve()
        self.lock = threading.Lock()
        self.last = 0.0
        self.stopped = threading.Event()
        self.reuse = Path(reuse).resolve() if reuse else None
        self.cache = {}
        if self.reuse:
            for path in sorted((self.reuse / "records").glob("*.json")):
                for rec in json.loads(path.read_text()).get("requests", []):
                    self.cache[rec["url"]] = rec

    def cached(self, rec, relative):
        path = (self.reuse / rec["path"]).resolve()
        if not path.is_relative_to(self.reuse):
            raise ValueError("cached path escapes reuse directory")
        body = path.read_bytes()
        if len(body) != rec["bytes"] or digest(body) != rec["sha256"]:
            raise ValueError("cached raw response hash mismatch")
        publish_bytes(self.out / relative, body)
        return body, {**rec, "path": relative}

    def get(self, url, relative):
        if url in self.cache:
            return self.cached(self.cache[url], relative)
        started = stamp()
        for attempt in range(3):
            if self.stopped.is_set():
                raise RuntimeError("collection stopped after provider rate limit")
            with self.lock:
                time.sleep(max(0, 0.2 - (time.monotonic() - self.last)))
                self.last = time.monotonic()
            try:
                with urllib.request.urlopen(url, timeout=25) as response:
                    body = response.read()
                path = self.out / relative
                publish_bytes(path, body)
                return body, {
                    "url": url,
                    "path": relative,
                    "sha256": digest(body),
                    "bytes": len(body),
                    "requested_at": started,
                    "observed_at": stamp(),
                    "status": 200,
                }
            except urllib.error.HTTPError as exc:
                if exc.code in (418, 429):
                    self.stopped.set()
                if exc.code < 500:
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                pass
            time.sleep(attempt + 1)
        raise RuntimeError("bounded request attempts exhausted")

    def universe(self):
        if self.reuse:
            body = (self.reuse / "UNIVERSE.json").read_bytes()
            result = json.loads(body)
            catalog_pairs = []
            for rec in result["catalog_pages"]:
                raw, _ = self.cached(rec, rec["path"])
                catalog_pairs.extend(catalog_page(raw)[0])
            expected = sorted(p for p in set(catalog_pairs) if eligible_pair(p))
            if not expected or result["pairs"] != expected:
                raise ValueError("invalid reused universe")
            publish_bytes(self.out / "UNIVERSE.json", body)
            return result["pairs"]
        pairs, pages, marker = [], [], None
        for i in range(30):
            params = {"delimiter": "/", "prefix": "data/spot/monthly/klines/", "max-keys": 1000}
            if marker:
                params["marker"] = marker
            body, rec = self.get(
                CATALOG + "?" + urllib.parse.urlencode(params), f"catalog/page-{i}.xml"
            )
            found, next_marker, truncated = catalog_page(body)
            pages.append(rec)
            pairs.extend(found)
            if not truncated:
                break
            if not next_marker or next_marker == marker:
                raise RuntimeError("archive catalog pagination did not advance")
            marker = next_marker
        else:
            raise RuntimeError("archive catalog exceeded page bound")
        selected = sorted(p for p in set(pairs) if eligible_pair(p))
        if not selected:
            raise RuntimeError("empty archive universe")
        result = {
            "created_at": stamp(),
            "source": CATALOG,
            "catalog_pages": pages,
            "pairs": selected,
            "exclusion": "non-USDT; global_panel.STABLE and LEVERAGED regex",
            "excluded_usdt": sorted(
                p for p in set(pairs) if p.endswith("USDT") and not eligible_pair(p)
            ),
            "limitation": "2026 archive-covered universe, not proof of every historically listed pair; existing leveraged suffix filter can also exclude names ending UP",
        }
        dump(self.out / "UNIVERSE.json", result)
        return selected

    def pair(self, pair):
        cursor, rows, requests = START_MS, [], []
        try:
            for page in range(3):
                params = {
                    "symbol": pair,
                    "interval": "1d",
                    "startTime": cursor,
                    "endTime": END_MS,
                    "limit": 1000,
                }
                body, rec = self.get(
                    API + "?" + urllib.parse.urlencode(params), f"raw/{pair}-{page}.json"
                )
                requests.append(rec)
                chunk = json.loads(body)
                if not isinstance(chunk, list):
                    raise ValueError("provider did not return kline array")
                rows.extend(chunk)
                if not chunk or len(chunk) < 1000 or int(chunk[-1][0]) + DAY_MS > END_MS:
                    break
                following = int(chunk[-1][0]) + DAY_MS
                if following <= cursor:
                    raise ValueError("pagination did not advance")
                cursor = following
            else:
                raise ValueError("pagination exceeded 2020-2023 bound")
            frame = rows_frame(rows, pair)
            result = {
                "pair": pair,
                "status": "ok" if len(frame) else "empty_in_window",
                "rows": len(frame),
                "requests": requests,
            }
            if len(frame):
                result.update(first=frame.date.min(), last=frame.date.max())
            return result, frame
        except Exception as exc:
            return {
                "pair": pair,
                "status": "failed",
                "error_type": type(exc).__name__,
                "http_status": getattr(exc, "code", None),
                "message": str(exc)[:200],
                "requests": requests,
            }, None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="new output directory; existing directories are refused",
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--reuse",
        type=Path,
        help="reuse frozen universe and SHA-256 verified recorded raw responses from an earlier collection",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 24:
        parser.error("workers must be between 1 and 24")
    args.out.mkdir(parents=True, exist_ok=False)
    collector = Collector(args.out, args.reuse)
    universe = collector.universe()
    print(f"Frozen universe: {len(universe)} USDT pairs; bounds2020-2023", flush=True)
    frames, results = [], []
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        for i, (rec, frame) in enumerate(pool.map(collector.pair, universe), 1):
            results.append(rec)
            dump(args.out / "records" / f"{rec['pair']}.json", rec)
            if frame is not None and len(frame):
                frames.append(frame)
            if i % 50 == 0 or i == len(universe):
                print(
                    f"Processed {i}/{len(universe)}; usable={len(frames)} failed={sum(r['status'] == 'failed' for r in results)}",
                    flush=True,
                )
    if not frames:
        raise RuntimeError("no usable historical data")
    panel = pd.concat(frames, ignore_index=True).sort_values(["date", "ticker"])
    path = args.out / "panel.csv.gz"
    panel.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
    summary = {
        "schema": "KOD-PREMOVE-COLLECTION-v1",
        "collected_at": stamp(),
        "bounds": ["2020-01-01", "2023-12-31"],
        "universe_sha256": digest((args.out / "UNIVERSE.json").read_bytes()),
        "universe_pairs": len(universe),
        "usable_pairs": int(panel.ticker.nunique()),
        "rows": len(panel),
        "panel": path.name,
        "panel_sha256": digest(path.read_bytes()),
        "first": panel.date.min(),
        "last": panel.date.max(),
        "failed_pairs": [r["pair"] for r in results if r["status"] == "failed"],
        "empty_pairs": [r["pair"] for r in results if r["status"] == "empty_in_window"],
        "pair_records": results,
        "value_units": "USDT quote volume",
        "limitations": [
            "New retrieval vintage, not original KOD panel reconstruction",
            "Runtime API may omit archive-only delisted history; failures listed explicitly",
            "Short delisting-day bars are preserved and marked complete_bar=False; not eligible completed daily bars",
            "Rows absent before listing/after delisting are not zero-return observations",
            "Daily bars cannot resolve intraday threshold order when both barriers are touched",
            "No future-reversion spike deletion; stable/leveraged filter matches existing KOD conventions",
            "2020-2023 have been used in earlier KOD research; this is exploratory retrospective evidence",
        ],
    }
    dump(args.out / "COLLECTION.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "pair_records"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
