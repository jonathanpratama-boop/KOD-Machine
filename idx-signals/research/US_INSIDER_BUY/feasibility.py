"""US_INSIDER_BUY step 3, counts only: how many Stage 1 events there are, how many can be bought under the harness (hold 60, the run's own 200 control draws, so the scored count here is the
run's) and how they spread over years. Prints status counts and event counts; no return, control value or price is printed or saved (the harness computes returns internally; they are not
looked at). GO rule (PROTOCOL.md): at least 1,500 scored Stage 1 events and at least 300 in each of 2021 and 2022. Writes feasibility/FEASIBILITY.json (refuses to overwrite).
Usage (from idx-signals/): python3 research/US_INSIDER_BUY/feasibility.py"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from idxsig import event_study as es, global_panel  # noqa: E402
import ib_stats as st  # noqa: E402

PANEL_MANIFEST = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
START, END = "2020-06-01", "2023-12-29"
DRAWS, SEED = 200, 20261007


def main() -> int:
    out = HERE / "feasibility" / "FEASIBILITY.json"
    if out.exists():
        sys.exit("error: feasibility/FEASIBILITY.json exists")
    ev = pd.read_csv(HERE / "events.csv", dtype={"accession": str})
    df, meta = global_panel.load(PANEL_MANIFEST)
    prep = es.prepare_us(df, START, END)
    s1 = ev[ev.stage == 1]
    t0 = time.time()
    res = es.run_events(prep, s1, es.us_config(60), draws=DRAWS, seed=SEED)
    seconds = round(time.time() - t0)
    ex = res[res.status == "EXITED"]
    f = st.scored(res)
    ok, info = st.go_check(f)
    counts = {
        "events_stage1": int(len(s1)), "events_stage2": int((ev.stage == 2).sum()), "mapped_to_panel": int(len(res)), "not_in_panel": int(len(s1) - len(res)),
        "status_counts": es.status_counts(res), "exited": int(len(ex)), "exited_without_any_scored_control_draw": int((ex.control_n == 0).sum()),
        "scored": int(len(f)), "scored_by_entry_year": {y: int(n) for y, n in f.groupby(f.entry_date.str[:4]).size().items()},
        "scored_by_top_exec": {str(k): int(n) for k, n in f.groupby("top_exec").size().items()},
        "scored_by_size": {k: int(n) for k, n in f.groupby(pd.cut(f.total_value, [50_000, 100_000, 500_000, float("inf")], right=False, labels=["50-100k", "100-500k", "500k+"]), observed=True).size().items()},
        "go_rule": "scored (EXITED with a scored control draw) >= 1500 at hold 60 and >= 300 in each of 2021 and 2022 (fixed in PROTOCOL.md before this run)",
        "go": ok, "go_detail": info, "seconds": seconds,
    }
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(counts, indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
