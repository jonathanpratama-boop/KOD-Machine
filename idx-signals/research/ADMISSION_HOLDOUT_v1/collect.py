"""ADMISSION_HOLDOUT_v1: collect Binance daily bars for the owner-authorised window, with the pre-move collector's own
code (tools/collect_premove_crypto.py, unchanged; its 2020-2023 guard stays in place for every other use).

Owner, 2026-10-31: "I give you permission" to read 2024-01-01..2026-10-29 daily crypto bars for one frozen test of
the fresh 10-15% admission rule. Bars from 2023-07-01 are read only as feature warm-up (the frozen models need 60
valid days); 2026-10-30 onward is not read (the PREMOVE_SHADOW_v1 prospective trial starts that day).

    python3 research/ADMISSION_HOLDOUT_v1/collect.py --out data/raw/premove/holdout-2024-2026
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("cpc", ROOT / "tools/collect_premove_crypto.py")
cpc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpc)

FIRST, LAST = "2023-07-01", "2026-10-29"


def ms(day: str, end: bool = False) -> int:
    t = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)
    return t + cpc.DAY_MS - 1 if end else t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    cpc.START_MS, cpc.END_MS = ms(FIRST), ms(LAST, end=True)  # this module's copy only
    args.out.mkdir(parents=True, exist_ok=False)
    collector = cpc.Collector(args.out)
    universe = collector.universe()
    print(f"universe: {len(universe)} USDT pairs; bounds {FIRST}..{LAST}", flush=True)
    frames, results = [], []
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        for rec, frame in pool.map(collector.pair, universe):
            results.append(rec)
            cpc.dump(args.out / "records" / f"{rec['pair']}.json", rec)
            if frame is not None and len(frame):
                frames.append(frame)
    panel = pd.concat(frames, ignore_index=True).sort_values(["date", "ticker"])
    if panel.date.max() > LAST or panel.date.min() < FIRST:
        raise RuntimeError("a bar outside the authorised window")
    path = args.out / "panel.csv.gz"
    panel.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
    summary = {
        "schema": "KOD-PREMOVE-COLLECTION-v1",
        "study": "ADMISSION_HOLDOUT_v1",
        "collected_at": cpc.stamp(),
        "bounds": [FIRST, LAST],
        "authorisation": "owner, 2026-10-31, one frozen test; 2023-07..12 is feature warm-up only",
        "universe_sha256": cpc.digest((args.out / "UNIVERSE.json").read_bytes()),
        "universe_pairs": len(universe),
        "usable_pairs": int(panel.ticker.nunique()),
        "rows": len(panel),
        "panel": path.name,
        "panel_sha256": cpc.digest(path.read_bytes()),
        "first": panel.date.min(),
        "last": panel.date.max(),
        "failed_pairs": [r["pair"] for r in results if r["status"] == "failed"],
        "empty_pairs": [r["pair"] for r in results if r["status"] == "empty_in_window"],
        "pair_records": results,
        "limitations": [
            "universe = the 2026 archive catalogue (delisted pairs may be missing: survivorship flatters buying)",
            "failures are listed, never treated as zero-return days",
            "short delisting-day bars are kept with complete_bar=False and are not tradable",
        ],
    }
    cpc.dump(args.out / "COLLECTION.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "pair_records"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
