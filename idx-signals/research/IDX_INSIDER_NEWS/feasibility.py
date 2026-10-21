"""IDX_INSIDER_NEWS step 6, counts only: of the audited INSIDER_BUY events, how many can be mapped to the pinned panel and bought under
the harness (hold 20), and how are they spread over years. Prints status counts and event counts; no return, control or price is printed
or saved (the harness computes returns internally; they are not looked at). Fixed GO rule: at least 100 events scored (entered and
exited with a control mean) in the 20-session hold. Writes feasibility/FEASIBILITY.json (refuses to overwrite).
Usage (from idx-signals/): python3 research/IDX_INSIDER_NEWS/feasibility.py
"""
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import idx_events  # noqa: E402

_spec = importlib.util.spec_from_file_location("idxnews_run_v2", HERE / "run_v2.py")
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)
GO_MIN_SCORED = 100


def main() -> int:
    out = HERE / "feasibility" / "FEASIBILITY.json"
    if out.exists():
        sys.exit("error: feasibility/FEASIBILITY.json exists")
    events = pd.read_csv(HERE / "events.csv")
    df, reg, meta = run.load_inputs()
    prep = idx_events.prepare(df, reg, run.START, run.END)
    res = idx_events.run_events(prep, events, run.config(run.PRIMARY), draws=5, seed=run.SEED)
    f = idx_events.filled(res)
    year = lambda s: s.str[:4]  # noqa: E731
    counts = {
        "events_in_table": int(len(events)), "tickers_in_table": int(events.ticker.nunique()),
        "events_by_year": {k: int(v) for k, v in events.groupby(year(events.posted_wib)).size().items()},
        "mapped_to_panel": int(len(res)), "not_in_panel": int(len(events) - len(res)),
        "status_counts": idx_events.status_counts(res), "scored_with_control": int(len(f)),
        "scored_by_year": {k: int(v) for k, v in f.groupby(year(f.posted_wib)).size().items()},
        "distinct_posting_days_scored": int(f.posted_wib.str[:10].nunique()),
        "go_rule": f"scored events >= {GO_MIN_SCORED} (fixed before this run)",
    }
    counts["go"] = bool(counts["scored_with_control"] >= GO_MIN_SCORED)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(counts, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
