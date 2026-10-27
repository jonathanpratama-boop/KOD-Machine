"""US_INSIDER_OFFICER_v1: the single recorded run of PROTOCOL.md. Usage (from idx-signals/): python3 research/US_INSIDER_OFFICER_v1/run.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = HERE.parent / "US_INSIDER_BUY"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BASE))
from idxsig import event_study as es, global_panel  # noqa: E402
import ib_stats as st  # noqa: E402

PANEL = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
START, END, HOLDS, PRIMARY, DRAWS, SEED = "2020-06-01", "2023-12-29", (20, 60, 120), 60, 200, 20261007


def stats(f: pd.DataFrame) -> dict:
    w = st.week_id(f.entry_date)
    b = st.Boot(w, 10_000, 20261203).mean(f.excess, w)
    return {**b, "median": float(f.excess.median()), "winsorised_mean": st.winsor_mean(f.excess), "hit_rate": float((f.net_return > 0).mean()),
            "mean_net": float(f.net_return.mean()), "mean_control": float(f.control_mean.mean())}


def main() -> int:
    out = HERE / "RESULT.json"
    if out.exists():
        sys.exit("error: RESULT.json exists; this runs once")
    ev = pd.read_csv(BASE / "events.csv", dtype={"accession": str})
    ev = ev[ev.stage == 2].reset_index(drop=True)
    df, meta = global_panel.load(PANEL)
    prep = es.prepare_us(df, START, END)
    res = {"experiment": "US_INSIDER_OFFICER_v1", "panel_sha256": meta["sha256"], "label": "historical research only; survivor-only prices", "holds": {}}
    for hold in HOLDS:
        r = es.run_events(prep, ev, es.us_config(hold), draws=DRAWS, seed=SEED)
        r.to_csv(HERE / f"events_hold{hold}.csv", index=False)
        f = st.scored(r)
        m = f.officer.astype(bool) & ~f.director.astype(bool)
        res["holds"][str(hold)] = {"officer_not_director": stats(f[m]), "all_other": stats(f[~m]), "status": es.status_counts(r[r.officer.astype(bool) & ~r.director.astype(bool)])}
    p = res["holds"][str(PRIMARY)]["officer_not_director"]
    res["gates"] = {"G1_mean_gt_0_t_ge_1.65": bool(p["mean"] > 0 and p["t"] >= 1.65), "G2_mean_ge_2pct": bool(p["mean"] >= 0.02)}
    res["verdict"] = "PASS" if all(res["gates"].values()) else "FAIL"
    out.write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
