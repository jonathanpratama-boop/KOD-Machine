"""SLOW_10K step 5: write PINS.json (sha256 of events.csv, similarity.csv.gz, filings.csv.gz, the US repair panel and the code that runs), the inputs run.py refuses to run
without. Usage (from idx-signals/): python3 research/SLOW_10K/freeze.py"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PANEL_MANIFEST = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
CODE = ["idxsig/event_study.py", "idxsig/idx_events.py", "idxsig/execution.py", "idxsig/controls.py", "idxsig/market.py", "idxsig/profiles.py", "idxsig/backtest.py",
        "idxsig/global_panel.py", "research/SLOW_10K/tenk_lib.py", "research/SLOW_10K/tenk_buckets.py", "research/SLOW_10K/tenk_stats.py", "research/SLOW_10K/build_events.py"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    out = HERE / "PINS.json"
    if out.exists():
        sys.exit("error: PINS.json exists")
    meta = json.loads(PANEL_MANIFEST.read_text())
    pins = {"events_csv": sha(HERE / "events.csv"), "similarity_csv": sha(HERE / "similarity.csv.gz"), "filings_csv": sha(HERE / "filings.csv.gz"),
            "panel": meta["sha256"], "code": {p: sha(ROOT / p) for p in CODE}}
    out.write_text(json.dumps(pins, indent=1) + "\n")
    print(json.dumps(pins, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
