"""US_8K_ITEMS: write PINS.json (inputs and code). Usage (from idx-signals/): python3 research/US_8K_ITEMS/freeze.py"""
import hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CODE = ["idxsig/event_study.py", "idxsig/idx_events.py", "idxsig/execution.py", "idxsig/controls.py", "idxsig/market.py", "idxsig/profiles.py", "idxsig/backtest.py", "idxsig/global_panel.py",
        "research/US_INSIDER_BUY/ib_stats.py", "research/US_8K_ITEMS/k_lib.py", "research/US_8K_ITEMS/build_events.py", "research/US_8K_ITEMS/run.py"]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
out = HERE / "PINS.json"
if out.exists():
    sys.exit("error: PINS.json exists")
meta = json.loads((ROOT / "data/manifests/panel_us_repair-20261008T114805Z.json").read_text())
pins = {"events_csv": sha(HERE / "events.csv"), "filings8k": sha(HERE / "filings8k.csv.gz"), "panel": meta["sha256"], "code": {p: sha(ROOT / p) for p in CODE}}
out.write_text(json.dumps(pins, indent=1) + "\n")
print(json.dumps(pins, indent=1))
