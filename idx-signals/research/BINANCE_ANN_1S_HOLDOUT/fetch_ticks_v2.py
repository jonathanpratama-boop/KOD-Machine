"""BINANCE_ANN_1S_HOLDOUT step 2 (corrected selection, ADDENDUM_1.md): for each eligible event of feasibility/events.csv and for its placebo (the same pair 24 h earlier), read Binance's
daily aggregate-trade archive and keep the trades in [T-120 s, T+3900 s], with BINANCE_ANN_1S/fetch_ticks.py's own download and slicing code.
Stores them in ticks/ticks.npz with ticks/MANIFEST.json (every archive's URL, size and sha256). Nothing is computed from them here. Needs AUTHORIZATION.md.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1S_HOLDOUT/fetch_ticks.py --cache <scratch dir>
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from hold_common import GO_MIN_ELIGIBLE, HERE, ROOT, S1, load, require_authorization, require_pinned_code, sha_file


def main() -> int:
    require_authorization()
    require_pinned_code()
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    out = HERE / "ticks"
    if (out / "MANIFEST.json").exists():
        sys.exit("error: ticks/MANIFEST.json exists")
    feas = HERE / "feasibility_v2" / "events.csv"
    ev = pd.read_csv(feas)
    ev = ev[ev.eligible].sort_values(["t_ms", "token"]).reset_index(drop=True)
    if len(ev) < GO_MIN_ELIGIBLE:
        sys.exit(f"error: GO rule 1 fails: {len(ev)} eligible events < {GO_MIN_ELIGIBLE}")
    f1 = load(S1 / "fetch_ticks.py", "ann1s_fetch")
    cache = args.cache
    from pathlib import Path
    Path(cache).mkdir(parents=True, exist_ok=True)
    tasks = [{"i": i, "event_key": r.event_key, "token": r.token, "pair": r.pair, "kind": kind,
              "T": int(r.t_ms) - (f1.DAY_MS if kind == "placebo" else 0), "t_event_ms": int(r.t_ms)}
             for i, r in ev.iterrows() for kind in ("event", "placebo")]
    print(f"{len(ev)} events, {len(tasks)} series")
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda t: f1.one(t, Path(cache)), tasks))
    print(f"fetched in {time.time() - t0:.0f}s")
    sizes = np.array([len(r[1]) for r in results])
    index = np.concatenate([[0], np.cumsum(sizes)])
    out.mkdir(exist_ok=True)
    npz = out / "ticks.npz"
    np.savez_compressed(npz, ts=np.concatenate([r[1] for r in results]), price=np.concatenate([r[2] for r in results]),
                        qty=np.concatenate([r[3] for r in results]), m=np.concatenate([r[4] for r in results]), index=index)
    man = {"fetched_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "source": f1.BASE,
           "events_source": "research/BINANCE_ANN_1S_HOLDOUT/feasibility_v2/events.csv (eligible rows)", "events_csv_sha256": sha_file(feas),
           "window_ms": [-f1.PRE_MS, f1.POST_MS],
           "series": [{"row": n, "event_key": r[0]["event_key"], "token": r[0]["token"], "pair": r[0]["pair"], "kind": r[0]["kind"],
                       "T": r[0]["T"], "t_event_ms": r[0]["t_event_ms"], "trades": int(sizes[n]), "zips": r[5]} for n, r in enumerate(results)],
           "npz": {"path": "research/BINANCE_ANN_1S_HOLDOUT/ticks/ticks.npz", "sha256": sha_file(npz), "bytes": npz.stat().st_size}}
    (out / "MANIFEST.json").write_text(json.dumps(man, indent=0) + "\n")
    missing = sum(1 for r in results if any(z["sha256"] is None for z in r[5]))
    print(json.dumps({"series": len(results), "series_with_a_missing_archive": missing, "empty_series": int((sizes == 0).sum()),
                      "npz_bytes": man["npz"]["bytes"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
