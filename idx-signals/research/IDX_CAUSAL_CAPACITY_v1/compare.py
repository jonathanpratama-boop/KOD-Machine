"""Step 3 of PROTOCOL.md: compare the evidence run (fill model A) with the FILL-C-v1 rerun.
Reads both recorded runs; writes comparison.json.

    python3 research/IDX_CAUSAL_CAPACITY_v1/compare.py   (from idx-signals/)"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "results" / "runs"
A, C = "20261008T000401Z_MOONSHOT_E1_D1_v1.1", "20261009T050040Z_MOONSHOT_E1_D1_v1.1"
SCORED = {"EXITED", "EXIT_DATA_END"}


def side(run: str) -> dict:
    s = json.loads((RUNS / run / "summary.json").read_text())
    r, m = s["rule_trades"], s["random_matched"]["avg_net_return"]
    return {"run": run, "fill_model": s.get("repair", {}).get("fill_model", {}).get("model", "A"),
            "attempts": r["attempts"], "filled": r["filled"], "scored": r["scored"], "hit_rate": r["hit_rate"],
            "avg_net": r["avg_net_return"], "median_net": r["median_net_return"],
            "matched_random_avg_net": m["random_mean"], "difference_vs_matched": m["difference"],
            "p_one_sided": m["p_value_one_sided"], "status_counts": r["status_counts"]}


def mean(x: pd.Series):
    return None if x.empty else float(x.mean())


def main() -> int:
    a, c = side(A), side(C)
    ta, tc = (pd.read_csv(RUNS / r / "trades.csv.gz") for r in (A, C))
    both = ta.merge(tc, on=["ticker", "signal_date"], suffixes=("_a", "_c"), how="outer")
    changed = both[both.status_a != both.status_c]
    transitions = changed.groupby(["status_a", "status_c"], dropna=False).size().sort_values(ascending=False)
    only_a = both[both.status_a.isin(SCORED) & ~both.status_c.isin(SCORED)]
    only_c = both[both.status_c.isin(SCORED) & ~both.status_a.isin(SCORED)]
    common = both[both.status_a.isin(SCORED) & both.status_c.isin(SCORED)]
    approval = {"p_below_0.05": c["p_one_sided"] < 0.05, "avg_net_positive": c["avg_net"] > 0,
                "above_matched_random": c["difference_vs_matched"] > 0}
    material = abs(c["avg_net"] - a["avg_net"]) > 0.01 or (a["p_one_sided"] < 0.05) != (c["p_one_sided"] < 0.05)
    out = {
        "A": a, "C": c,
        "rule_avg_net_change_pp": round(100 * (c["avg_net"] - a["avg_net"]), 3),
        "status_transitions": [{"A": sa, "C": sc, "n": int(n)} for (sa, sc), n in transitions.items()],
        "scored_only_under_A": {"n": len(only_a), "avg_net": mean(only_a.net_return_a)},
        "scored_only_under_C": {"n": len(only_c), "avg_net": mean(only_c.net_return_c)},
        "scored_under_both": {"n": len(common), "avg_net": mean(common.net_return_a),
                              "identical_returns": bool((common.net_return_a - common.net_return_c).abs().max() < 1e-12)
                              if len(common) else None},
        "skip_capacity_unknown": c["status_counts"].get("SKIP_CAPACITY_UNKNOWN", 0),
        "approval_v2_test_under_C": {**approval, "passes": all(approval.values())},
        "material_difference": material,
    }
    (Path(__file__).parent / "comparison.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
