"""BINANCE_ANN_1S step 1: for each of the 112 events of BINANCE_ANN_1M's registered run, and for a placebo (the same pair 24 h
earlier), read Binance's daily aggregate-trade archive and keep the trades in [T-120 s, T+3900 s]. Stores them in
ticks/ticks.npz with ticks/MANIFEST.json (every archive's URL, size and sha256). Nothing is computed from them here.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1S/fetch_ticks.py --cache <scratch dir>
"""
import argparse
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
M1 = ROOT / "research" / "BINANCE_ANN_1M"
BASE = "https://data.binance.vision/data/spot/daily/aggTrades"
PRE_MS, POST_MS, DAY_MS = 120_000, 3_900_000, 86_400_000
OUT = HERE / "ticks"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def events() -> pd.DataFrame:
    used = pd.read_csv(M1 / "results" / "events.csv")
    feas = pd.read_csv(M1 / "feasibility" / "events.csv")
    feas["event_key"] = feas.article_id.astype(str) + "|" + feas.token
    out = used[["event_key", "token", "t_ms"]].merge(feas[["event_key", "pair"]], on="event_key", how="left")
    if out.pair.isna().any():
        sys.exit("error: an event has no pair")
    return out.sort_values(["t_ms", "token"]).reset_index(drop=True)


def day_url(pair: str, ms: int) -> str:
    d = datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")
    return f"{BASE}/{pair}/{pair}-aggTrades-{d}.zip"


def download(url: str, retries: int = 4) -> bytes | None:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            time.sleep(3 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"download failed: {url}")


def read_slice(blob: bytes, lo: int, hi: int) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(blob), compression="zip", header=None, usecols=[1, 2, 5, 6], names=["price", "qty", "ts", "m"])
    if df.ts.max() > 2e13:
        raise RuntimeError("timestamps are not milliseconds")
    return df[(df.ts >= lo) & (df.ts <= hi)]


def one(task: dict, cache: Path):
    key, kind, pair, T = task["event_key"], task["kind"], task["pair"], task["T"]
    f = cache / f"{task['i']:03d}_{kind}.npz"
    if f.exists():
        z = np.load(f, allow_pickle=True)
        return task, z["ts"], z["price"], z["qty"], z["m"], json.loads(str(z["zips"]))
    lo, hi = T - PRE_MS, T + POST_MS
    zips, parts = [], []
    for url in dict.fromkeys([day_url(pair, lo), day_url(pair, hi)]):
        blob = download(url)
        if blob is None:
            zips.append({"url": url, "bytes": 0, "sha256": None})
            continue
        zips.append({"url": url, "bytes": len(blob), "sha256": sha(blob)})
        parts.append(read_slice(blob, lo, hi))
    df = pd.concat(parts).sort_values("ts", kind="stable") if parts else pd.DataFrame(columns=["price", "qty", "ts", "m"])
    arrs = (df.ts.to_numpy("int64"), df.price.to_numpy(float), df.qty.to_numpy(float), df.m.to_numpy(bool))
    np.savez(f, ts=arrs[0], price=arrs[1], qty=arrs[2], m=arrs[3], zips=json.dumps(zips))
    return (task, *arrs, zips)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    if (OUT / "MANIFEST.json").exists():
        sys.exit("error: ticks/MANIFEST.json exists")
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    ev = events()
    tasks = [{"i": i, "event_key": r.event_key, "token": r.token, "pair": r.pair, "kind": kind,
              "T": int(r.t_ms) - (DAY_MS if kind == "placebo" else 0), "t_event_ms": int(r.t_ms)}
             for i, r in ev.iterrows() for kind in ("event", "placebo")]
    print(f"{len(ev)} events, {len(tasks)} series")
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda t: one(t, cache), tasks))
    print(f"fetched in {time.time() - t0:.0f}s")
    sizes = np.array([len(r[1]) for r in results])
    index = np.concatenate([[0], np.cumsum(sizes)])
    OUT.mkdir(exist_ok=True)
    npz = OUT / "ticks.npz"
    np.savez_compressed(npz, ts=np.concatenate([r[1] for r in results]), price=np.concatenate([r[2] for r in results]),
                        qty=np.concatenate([r[3] for r in results]), m=np.concatenate([r[4] for r in results]), index=index)
    man = {"fetched_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "source": BASE,
           "events_source": "research/BINANCE_ANN_1M/results/events.csv + feasibility/events.csv",
           "events_csv_sha256": sha((M1 / "results" / "events.csv").read_bytes()),
           "feasibility_events_sha256": sha((M1 / "feasibility" / "events.csv").read_bytes()),
           "window_ms": [-PRE_MS, POST_MS],
           "series": [{"row": n, "event_key": r[0]["event_key"], "token": r[0]["token"], "pair": r[0]["pair"], "kind": r[0]["kind"],
                       "T": r[0]["T"], "t_event_ms": r[0]["t_event_ms"], "trades": int(sizes[n]), "zips": r[5]}
                      for n, r in enumerate(results)],
           "npz": {"path": "research/BINANCE_ANN_1S/ticks/ticks.npz", "sha256": sha(npz.read_bytes()), "bytes": npz.stat().st_size}}
    (OUT / "MANIFEST.json").write_text(json.dumps(man, indent=0) + "\n")
    missing = sum(1 for r in results if any(z["sha256"] is None for z in r[5]))
    print(json.dumps({"series": len(results), "series_with_a_missing_archive": missing, "empty_series": int((sizes == 0).sum()),
                      "npz_bytes": man["npz"]["bytes"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
