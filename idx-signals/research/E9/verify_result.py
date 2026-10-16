"""E9 step 5: recompute the decisive numbers of results/RESULT.json from results/trades.csv.gz, independently of
run_test.py's code (its own tier lookup, sample filter, week bootstrap and criteria), and compare.

Usage (from idx-signals/): python3 research/E9/verify_result.py
Prints each check; exits non-zero if any decisive number differs by more than 1e-9.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
E9 = ROOT / "research" / "E9"
TIERS = [(1.0, 0.015), (5.0, 0.005), (20.0, 0.0015), (float("inf"), 0.0005)]  # idxsig/profiles.py US, restated
SEC_FEE = 0.0000278


def tier(price: float) -> float:
    for upper, cost in TIERS:
        if price < upper:
            return cost
    return TIERS[-1][1]


def boot_ci(df: pd.DataFrame, col: str, weeks: np.ndarray, pick: np.ndarray) -> list:
    """Percentile interval of the pooled mean over resampled weeks (each pick row lists week positions)."""
    pos = {w: i for i, w in enumerate(weeks)}
    s, c = np.zeros(len(weeks)), np.zeros(len(weeks))
    for w, v in zip(df.week, df[col]):
        s[pos[w]] += v
        c[pos[w]] += 1
    stats = [s[row].sum() / c[row].sum() for row in pick if c[row].sum() > 0]
    return [float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))], s, c


def main() -> int:
    proto = json.loads((E9 / "protocol.json").read_text())
    res = json.loads((E9 / "results" / "RESULT.json").read_text())
    D = pd.read_csv(E9 / "results" / "trades.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    bad = []

    def check(name, mine, theirs, tol=1e-9):
        ok = (mine == theirs) if isinstance(mine, (bool, str, int)) and not isinstance(mine, float) else \
            (theirs is not None and abs(float(mine) - float(theirs)) <= tol)
        print(f"{'ok ' if ok else 'BAD'} {name}: {mine} vs {theirs}")
        if not ok:
            bad.append(name)

    # nets from the gross return and the as-traded prices, by a separate tier lookup
    sc_all = D[D.status.isin(["EXITED", "EXIT_DATA_END"])]
    re_net = [(1 + g) * (1 - SEC_FEE - tier(x)) / (1 + tier(e)) - 1 for g, e, x in zip(sc_all.gross, sc_all.entry_at, sc_all.exit_at)]
    check("max |net recomputed - net|", float(np.max(np.abs(np.array(re_net) - sc_all.net))), 0.0)
    extra = proto["costs"]["stress_extra_per_side"]
    re_st = [(1 + g) * (1 - SEC_FEE - tier(x) - extra) / (1 + tier(e) + extra) - 1
             for g, e, x in zip(sc_all.gross, sc_all.entry_at, sc_all.exit_at)]
    check("max |stress recomputed - stress|", float(np.max(np.abs(np.array(re_st) - sc_all.net_stress))), 0.0)
    check("max |excess - (net - ctrl_net)|", float(np.nanmax(np.abs(sc_all.excess - (sc_all.net - sc_all.ctrl_net)))), 0.0)

    # the sample, by its written rule
    cov = D.covered.astype(str).eq("True")
    S = D[D.status.isin(["EXITED", "EXIT_DATA_END"]) & D["class"].isin(["DOCUMENTED", "UNDOCUMENTED", "DILUTION"]) & cov].copy()
    S["week"] = S.week.astype(int)
    for c in ("DOCUMENTED", "UNDOCUMENTED", "DILUTION"):
        check(f"n {c}", int((S["class"] == c).sum()), int(res["scored_by_class"].get(c, 0)))
    doc, und = S[S["class"] == "DOCUMENTED"], S[S["class"] == "UNDOCUMENTED"]
    check("DOCUMENTED mean net", doc.net.mean(), res["classes"]["DOCUMENTED"]["plan_5d"]["mean"])
    check("UNDOCUMENTED mean net", und.net.mean(), res["classes"]["UNDOCUMENTED"]["plan_5d"]["mean"])
    check("DOCUMENTED win rate", float((doc.net > 0).mean()), res["classes"]["DOCUMENTED"]["plan_5d"]["win_rate"])
    check("UNDOCUMENTED win rate", float((und.net > 0).mean()), res["classes"]["UNDOCUMENTED"]["plan_5d"]["win_rate"])
    check("DOC - UNDOC", doc.net.mean() - und.net.mean(), res["separation_doc_minus_undoc"]["primary_5d"]["diff"])
    check("DOCUMENTED mean excess", doc.excess.mean(), res["classes"]["DOCUMENTED"]["excess_vs_matched"]["mean"])
    check("DOCUMENTED mean stress", doc.net_stress.mean(), res["classes"]["DOCUMENTED"]["stress"]["mean"])

    # the week bootstrap, rebuilt from the protocol's seed and resample count
    weeks = np.array(sorted(S.week.unique()))
    st = proto["statistics"]
    pick = np.random.default_rng(st["seed"]).integers(0, len(weeks), size=(st["resamples"], len(weeks)))
    ci_doc, sd, cd = boot_ci(doc, "net", weeks, pick)
    _, su, cu = boot_ci(und, "net", weeks, pick)
    diffs = [sd[r].sum() / cd[r].sum() - su[r].sum() / cu[r].sum() for r in pick if cd[r].sum() > 0 and cu[r].sum() > 0]
    ci_diff = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]
    r_doc = res["classes"]["DOCUMENTED"]["mean_net_ci"]["ci95"]
    r_diff = res["separation_doc_minus_undoc"]["primary_5d"]["ci95"]
    check("DOCUMENTED lower 95", ci_doc[0], r_doc[0])
    check("DOCUMENTED upper 95", ci_doc[1], r_doc[1])
    check("DOC - UNDOC lower 95", ci_diff[0], r_diff[0])
    check("DOC - UNDOC upper 95", ci_diff[1], r_diff[1])

    # criteria and verdicts
    years = proto["acceptance"]["years"]
    by_year = {y: doc[doc.signal_date.str[:4] == y].net for y in years}
    crit = [len(doc) >= 150 and len(und) >= 150, all(len(v) and v.mean() > 0 for v in by_year.values()),
            ci_doc[0] > 0, ci_diff[0] > 0, doc.excess.mean() > 0, doc.net_stress.mean() > 0]
    for (name, theirs), mine in zip(res["acceptance"].items(), crit):
        check(name, bool(mine), bool(theirs))
    rp = all(crit)
    diff = doc.net.mean() - und.net.mean()
    q1 = "SEPARATES" if ci_diff[0] > 0 else ("DOES_NOT_SEPARATE" if diff <= 0 else "INCONCLUSIVE")
    q2 = "PROFITABLE_IN_THIS_HISTORICAL_TEST" if rp else ("UNPROFITABLE" if doc.net.mean() <= 0 else "INCONCLUSIVE")
    v = res["verdict"]
    check("Q1", q1, v["Q1_filing_known_at_entry_separates_continuation"])
    check("Q2", q2, v["Q2_buying_documented_movers_on_the_E2_plan"])
    overall = "RESEARCH-POSITIVE" if rp else ("NEGATIVE" if q2 == "UNPROFITABLE" or q1 == "DOES_NOT_SEPARATE" else "INCONCLUSIVE")
    check("overall", overall, v["overall"])
    print("VERIFIED" if not bad else f"MISMATCH: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
