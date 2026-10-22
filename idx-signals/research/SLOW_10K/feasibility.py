"""SLOW_10K step 4, counts only: how many Stage 1 events there are per bucket, how many can be bought under the harness (hold 60), and how they spread over years. Prints status counts
and event counts; no return, control value or price is printed or saved (the harness computes returns internally; they are not looked at). GO rule (PROTOCOL.md): at least 1,000 scored
(EXITED) events in each of Q1 and Q5. Writes feasibility/FEASIBILITY.json (refuses to overwrite).
Usage (from idx-signals/): python3 research/SLOW_10K/feasibility.py"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from idxsig import event_study as es, global_panel  # noqa: E402
from tenk_stats import GO_MIN_PER_BUCKET  # noqa: E402

PANEL_MANIFEST = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
START, END = "2020-06-01", "2023-12-29"


def main() -> int:
    out = HERE / "feasibility" / "FEASIBILITY.json"
    if out.exists():
        sys.exit("error: feasibility/FEASIBILITY.json exists")
    ev = pd.read_csv(HERE / "events.csv", dtype={"accession": str})
    df, meta = global_panel.load(PANEL_MANIFEST)
    prep = es.prepare_us(df, START, END)
    s1 = ev[ev.stage == 1]
    res = es.run_events(prep, s1, es.us_config(60), draws=5)
    ex = res[res.status == "EXITED"]
    counts = {
        "events_stage1": int(len(s1)), "events_stage2": int((ev.stage == 2).sum()), "stage1_by_bucket": {k: int(v) for k, v in s1.groupby("bucket").size().items()},
        "mapped_to_panel": int(len(res)), "not_in_panel": int(len(s1) - len(res)), "status_counts_by_bucket": {b: es.status_counts(g) for b, g in res.groupby("bucket")},
        "exited_by_bucket": {b: int(len(g)) for b, g in ex.groupby("bucket")},
        "exited_by_bucket_and_entry_year": {f"{b}|{y}": int(len(g)) for (b, y), g in ex.assign(y=ex.entry_date.str[:4]).groupby(["bucket", "y"])},
        "exited_without_any_scored_control_draw": int((ex.control_n == 0).sum()),
        "go_rule": f"EXITED events >= {GO_MIN_PER_BUCKET} in each of Q1 and Q5 at hold 60 (fixed in PROTOCOL.md before this run)",
    }
    counts["go"] = bool(counts["exited_by_bucket"].get("Q1", 0) >= GO_MIN_PER_BUCKET and counts["exited_by_bucket"].get("Q5", 0) >= GO_MIN_PER_BUCKET)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(counts, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
