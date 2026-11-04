"""Measures Hermes's finding on the recorded FILL-C-v1 rerun (20261009T050040Z): FILL-C-v1 sizes
from decision-time capacity but never checks the entry session itself, so a trade can be scored
for more shares than the whole entry session traded. Reads the recorded trades and the pinned
panel; writes fill_c_feasibility.json. Nothing recorded is changed.

    python3 research/EXEC_US_v2/fill_c_feasibility.py   (from idx-signals/)"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.panel import load  # noqa: E402

RUNS = ROOT / "results" / "runs"
RUN_C, RUN_A = "20261009T050040Z_MOONSHOT_E1_D1_v1.1", "20261008T000401Z_MOONSHOT_E1_D1_v1.1"
SCORED = ("EXITED", "EXIT_DATA_END")


def entered(run: str, vol: pd.Series) -> pd.DataFrame:
    t = pd.read_csv(RUNS / run / "trades.csv.gz")
    t = t[t.status.isin(SCORED + ("INCOMPLETE",))].copy()
    t["entry_session_volume"] = [vol.get((r.ticker, r.entry_date), 0.0) for r in t.itertuples()]
    t["share_of_entry_session"] = t.shares / t.entry_session_volume.replace(0, np.nan)
    return t


def main() -> int:
    df, meta, _ = load(ROOT / "data" / "manifests" / "panel-20261007T225823Z.json")
    vol = df.assign(d=df.date.dt.strftime("%Y-%m-%d")).set_index(["ticker", "d"])["volume"].astype(float)
    out = {"panel_sha256": meta["sha256"], "runs": {}}
    for label, run in (("C", RUN_C), ("A", RUN_A)):
        t = entered(run, vol)
        s = t[t.status.isin(SCORED)]
        over_all = s[s.shares > s.entry_session_volume]
        over_cap = s[s.share_of_entry_session > 0.10]
        out["runs"][label] = {
            "run": run, "entered": int(len(t)), "scored": int(len(s)),
            "scored_shares_above_entire_entry_session_volume": int(len(over_all)),
            "scored_shares_above_10pct_of_entry_session_volume": int(len(over_cap)),
            "median_share_of_entry_session": float(s.share_of_entry_session.median()),
            "max_share_of_entry_session": float(s.share_of_entry_session.max()),
            "avg_net_if_infeasible_above_10pct_removed": float(s.loc[~s.index.isin(over_cap.index), "net_return"].mean()),
            "avg_net_recorded": float(s.net_return.mean()),
            "examples_above_10pct": over_cap.sort_values("share_of_entry_session", ascending=False)
            [["ticker", "signal_date", "entry_date", "shares", "entry_session_volume", "share_of_entry_session",
              "net_return"]].head(5).to_dict("records"),
        }
    out["note"] = ("Under A the cap is 10% of the entry session's final volume, so no scored A trade can exceed it "
                   "(a check of the measurement). Under C the entry session is never checked. Removing trades is a "
                   "descriptive bound, not a rerun: a feasible model would also change the overlap rule and the "
                   "baselines.")
    (Path(__file__).with_name("fill_c_feasibility.json")).write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
