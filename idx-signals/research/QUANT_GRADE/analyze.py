"""Multiple-testing analysis of every file in trials/. Writes analysis-<UTC date>.json (a new file each run) and prints it.
Usage (from idx-signals/): python3 research/QUANT_GRADE/analyze.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from idxsig import multiple_testing as mt  # noqa: E402


def main() -> int:
    trials = [json.loads(p.read_text()) for p in sorted((HERE / "trials").glob("*.json"))]
    counted = [t for t in trials if t["counted"]]
    with_p = [t for t in counted if t["one_sided_p"] is not None]
    raw = [t["one_sided_p"] for t in with_p]
    holm, bh = mt.holm(raw), mt.benjamini_hochberg(raw)
    n_hyp = len(counted)
    n_looks = sum(t["variants_searched"] for t in counted)
    out = {
        "trials_counted": n_hyp, "trials_with_p_value": len(with_p), "total_variants_looked_at": n_looks,
        "table": sorted([{"id": t["id"], "raw_p": t["one_sided_p"], "holm_p": round(h, 4), "bh_q": round(b, 4)}
                         for t, h, b in zip(with_p, holm, bh)], key=lambda r: r["raw_p"]),
        "smallest_raw_p": min(raw), "smallest_holm_p": min(holm), "any_significant_after_holm_5pct": bool(min(holm) < 0.05),
        "expected_best_z_from_pure_noise": {"over_hypotheses": round(mt.expected_max_z(n_hyp), 2),
                                            "over_all_variants": round(mt.expected_max_z(n_looks), 2)},
        "hurdle_z_bonferroni_5pct": {"next_test_given_hypotheses": round(mt.hurdle_z(n_hyp + 1), 2),
                                     "next_test_given_all_variants": round(mt.hurdle_z(n_looks + 1), 2)},
        "project_hurdle_t_for_next_primary_test": round(mt.project_hurdle(n_hyp), 2),
        "rule": "a future primary result must reach this t (and be pre-registered, run once, and added to trials/ first); "
                "where the search space is large (many plans or models), use the all-variants hurdle instead",
        "caveats": ["p-values for E7-E9, EXIT-ATR and US breakout are derived from published 95% intervals by normal approximation",
                    "experiments are correlated (shared data, reruns), so the effective number of tests is below the count",
                    "E3 and E4 searched 108 and 144 variants but recorded no p-values: they raise the search-level bar only",
                    "p-values are for the claimed positive effect, one-sided"],
        "computed": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (HERE / f"analysis-{datetime.now(timezone.utc):%Y-%m-%d}.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("caveats", "rule")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
