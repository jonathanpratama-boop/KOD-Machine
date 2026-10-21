"""BINANCE_ANN_1M step 2: fetch the 1-minute bars the protocol names, for each eligible event and its candidate controls, and
store closes and trade counts in minutes/minutes.npz with minutes/MANIFEST.json (hashes, which series, how many bars).
Only the bars are stored; nothing is computed from them here. Refuses to overwrite.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1M/fetch_minutes.py --cache <scratch dir>
"""
import argparse
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import microstructure as ms  # noqa: E402

PANEL = ROOT / "data" / "raw" / "binance" / "20261008T001212Z"
PANEL_MANIFEST = ROOT / "data" / "manifests" / "binance-20261008T003333Z.jsonl"
EVENTS = HERE / "feasibility" / "events.csv"
OUT = HERE / "minutes"
MIN, DAY = 60_000, 86_400_000
M_LO, M_HI = -65, 1455                      # minute offsets from b0 that are stored
L = M_HI - M_LO + 1
SEED_PREFIX = "20261022"
K_FETCH, K_KEEP = 16, 10
MIN_AGE_DAYS, ADV_DAYS, MIN_ADV = 30, 30, 1_000_000.0
STABLE_FIAT = {"USDC", "TUSD", "BUSD", "USDP", "PAX", "DAI", "USDS", "FDUSD", "SUSD", "VAI", "UST", "EUR", "GBP", "AUD", "TRY",
               "BRL", "RUB", "UAH", "NGN", "IDRT", "BIDR", "ZAR", "PLN", "RON", "ARS", "JPY", "MXN", "CZK", "COP", "AEUR", "USD1"}
LEVERAGED = re.compile(r"(UP|DOWN|BULL|BEAR)$")


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_daily() -> dict[str, dict]:
    """symbol -> {base, days (UTC day index), qv} for every USDT pair of the daily panel, delisted ones included."""
    info = json.loads((PANEL / "exchangeInfo.json").read_text())
    out = {}
    for s in info["symbols"]:
        p = PANEL / f"{s['symbol']}.json"
        if s["quoteAsset"] != "USDT" or not p.exists():
            continue
        rows = json.loads(p.read_text())
        if rows:
            out[s["symbol"]] = {"base": s["baseAsset"], "days": np.array([r[0] // DAY for r in rows]),
                                "qv": np.array([float(r[7]) for r in rows])}
    return out


def excluded_base(base: str) -> bool:
    return base in STABLE_FIAT or bool(LEVERAGED.search(base))


def pool_for(day: int, own_pair: str, near_event_pairs: set[str], daily: dict) -> list[str]:
    """Pairs eligible as controls for an announcement on UTC day index `day`, alphabetical."""
    out = []
    for sym, d in sorted(daily.items()):
        if sym == own_pair or sym in near_event_pairs or excluded_base(d["base"]):
            continue
        if d["days"][0] > day - MIN_AGE_DAYS or d["days"][-1] < day + 1:
            continue
        before = d["qv"][d["days"] < day]
        if len(before) < ADV_DAYS or np.median(before[-ADV_DAYS:]) < MIN_ADV:
            continue
        out.append(sym)
    return out


def permuted(pool: list[str], article_id, token: str) -> list[str]:
    seed = int(hashlib.sha256(f"{SEED_PREFIX}|{article_id}|{token}".encode()).hexdigest()[:16], 16)
    order = np.random.default_rng(seed).permutation(len(pool))
    return [pool[i] for i in order]


def plan(events: pd.DataFrame, daily: dict) -> list[dict]:
    """One entry per eligible event: its pair and the first K_FETCH controls of its permuted pool."""
    ev = events[events.eligible].sort_values(["t_ms", "token"]).reset_index(drop=True)
    days = (ev.t_ms // DAY).to_numpy()
    out = []
    for i, r in ev.iterrows():
        near = {ev.pair[j] for j in range(len(ev)) if abs(days[j] - days[i]) <= 1}
        pool = pool_for(int(days[i]), r.pair, near, daily)
        out.append({"event_key": f"{r.article_id}|{r.token}", "article_id": int(r.article_id), "token": r.token, "pair": r.pair,
                    "t_ms": int(r.t_ms), "b0": int(r.t_ms // MIN * MIN), "pool_size": len(pool),
                    "controls": permuted(pool, r.article_id, r.token)[:K_FETCH]})
    return out


def fetch_series(symbol: str, b0: int, retries: int = 3) -> tuple[np.ndarray, np.ndarray, int]:
    start, end = b0 + M_LO * MIN, b0 + (M_HI + 1) * MIN
    for attempt in range(retries):
        try:
            df = ms.fetch_minutes(symbol, start, end)
            break
        except RuntimeError:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    closes, trades = np.full(L, np.nan, np.float32), np.zeros(L, np.uint16)
    if not df.empty:
        idx = ((df["t"].to_numpy() - start) // MIN).astype(int)
        keep = (idx >= 0) & (idx < L)
        closes[idx[keep]] = df["c"].to_numpy()[keep]
        trades[idx[keep]] = np.minimum(df["n"].to_numpy()[keep], 65535)
    return closes, trades, int(len(df))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, help="scratch directory for per-series files (resumable)")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    if (OUT / "MANIFEST.json").exists():
        sys.exit("error: minutes/MANIFEST.json exists")
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(EVENTS)
    daily = load_daily()
    p = plan(events, daily)
    jobs = [(i, role, rank, sym, e["b0"], e["event_key"]) for i, e in enumerate(p)
            for role, rank, sym in [("event", -1, e["pair"])] + [("control", k, s) for k, s in enumerate(e["controls"])]]
    print(f"{len(p)} events, {len(jobs)} series")

    def one(job):
        i, role, rank, sym, b0, key = job
        f = cache / f"{i:03d}_{role}_{rank}_{sym}.npz"
        if f.exists():
            z = np.load(f)
            return job, z["c"], z["n"], int(z["bars"])
        c, n, bars = fetch_series(sym, b0)
        np.savez(f, c=c, n=n, bars=bars)
        return job, c, n, bars

    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(one, jobs))
    print(f"fetched in {time.time() - t0:.0f}s")
    closes = np.stack([r[1] for r in results]).astype(np.float32)
    trades = np.stack([r[2] for r in results]).astype(np.uint16)
    OUT.mkdir(exist_ok=True)
    npz = OUT / "minutes.npz"
    np.savez_compressed(npz, closes=closes, trades=trades)
    man = {"fetched_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "source": f"{ms.BASE}/klines?interval=1m",
           "events_csv_sha256": sha_file(EVENTS), "panel_manifest": PANEL_MANIFEST.name, "panel_manifest_sha256": sha_file(PANEL_MANIFEST),
           "m_lo": M_LO, "m_hi": M_HI, "length": L, "seed_prefix": SEED_PREFIX, "k_fetch": K_FETCH, "k_keep": K_KEEP,
           "events": [{k: v for k, v in e.items()} for e in p],
           "series": [{"row": n, "event_key": r[0][5], "role": r[0][1], "rank": r[0][2], "symbol": r[0][3], "bars": r[3]}
                      for n, r in enumerate(results)],
           "npz": {"path": "research/BINANCE_ANN_1M/minutes/minutes.npz", "sha256": sha_file(npz), "bytes": npz.stat().st_size}}
    (OUT / "MANIFEST.json").write_text(json.dumps(man, indent=0) + "\n")
    empty = sum(1 for r in results if r[3] == 0)
    print(json.dumps({"series": len(results), "series_with_no_bars": empty, "npz_bytes": man["npz"]["bytes"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
