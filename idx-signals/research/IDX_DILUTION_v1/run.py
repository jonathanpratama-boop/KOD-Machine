"""IDX_DILUTION_v1 single recorded run (see PROTOCOL.md). Usage (from idx-signals/): python3 research/IDX_DILUTION_v1/run.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "US_INSIDER_BUY"))
import common  # noqa: E402
import dl_lib  # noqa: E402
import ib_stats as st  # noqa: E402
from idxsig import idx_events  # noqa: E402


def main() -> int:
    out = HERE / "RESULT.json"
    if out.exists():
        sys.exit("error: RESULT.json exists; this runs once")
    df, reg, meta = common.load_inputs()
    ev = dl_lib.events(df, 0.05)
    ev = ev[ev.date.between("2023-01-03", "2023-09-29")].reset_index(drop=True)
    ev.to_csv(HERE / "events_2023.csv", index=False)
    prep = idx_events.prepare(df, reg, "2019-07-29", "2023-12-29")
    res = {"experiment": "IDX_DILUTION_v1", "inputs": meta, "events": len(ev), "holds": {}}
    for h in (20, 60):
        r = idx_events.run_events(prep, ev, common.config(h), draws=200, seed=20261027)
        r.to_csv(HERE / f"results_hold{h}.csv", index=False)
        f = r[r.excess.notna()]
        w = st.week_id(f.entry_date)
        b = st.Boot(w, 10_000, 20261203).mean(f.excess, w)
        res["holds"][str(h)] = {**b, "median": float(f.excess.median()), "status": idx_events.status_counts(r)}
    p = res["holds"]["60"]
    res["gates"] = {"G1_mean_le_-2pct": bool(p["mean"] <= -0.02), "G2_t_le_-1.65": bool(p["t"] <= -1.65)}
    res["verdict"] = "PASS" if all(res["gates"].values()) else "FAIL"
    out.write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
