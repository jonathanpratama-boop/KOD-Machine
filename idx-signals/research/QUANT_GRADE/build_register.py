"""One-off: write the historical trial register (trials/<id>.json), dated 2026-10-20, from the project's own records.

A trial is one pre-registered primary question put to data. For each: the one-sided p-value of the *claimed positive
effect* (the strategy beats its comparison), where it came from, and how many variants were searched. Where an
experiment reports only a 95% interval, p is derived by normal approximation (flagged). Experiments whose numbers are
not on this branch (E4-E8, EXIT-ATR, US breakout) are entered from the 2026-10-17 research status report.
Future trials are added as NEW files in trials/ (research/ is append-only); this script is never rerun.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import multiple_testing as mt  # noqa: E402

OUT = Path(__file__).resolve().parent / "trials"
T = []


def add(id_, experiment, date, hypothesis, p, p_source, variants=1, outcome="FAIL", note="", counted=True):
    T.append({"id": id_, "experiment": experiment, "date": date, "hypothesis": hypothesis, "one_sided_p": p,
              "p_source": p_source, "variants_searched": variants, "outcome": outcome, "note": note,
              "counted": counted, "registered": "2026-10-20"})


def ci(effect, lo, hi):
    return mt.p_one_sided(effect, mt.se_from_ci95(lo, hi))


add("E1_idx_validation", "E1", "2026-10-09", "F1_ARA detector plan beats matched random entries (IDX, 2023)", 1.0,
    "results/RUNS.jsonl 20261009T050040Z_MOONSHOT_E1_D1_v1.1 p_value_avg_return_vs_matched")
add("E2_us_validation", "E2", "2026-10-08", "G2_RET30 plan beats matched random entries (US, 2023), final repaired run", 0.6218905,
    "results/RUNS.jsonl 20261008T115656Z p_value_avg_return_vs_matched", variants=10,
    note="the 2023 US test was run 10 times as data repairs were completed; the strategy did not change")
add("E2_crypto_validation", "E2", "2026-10-08", "G2_RET30 plan beats matched random entries (crypto, 2023)", 1.0,
    "results/RUNS.jsonl 20261008T005732Z p_value_avg_return_vs_matched")
add("E3_idx_plans", "E3", "2026-10-13", "any of 108 detector-plan pairs is admitted (IDX limit-up)", None,
    "research/E3/discovery/summary.json: admissible = 0", variants=108, note="p-values per plan not recorded; counts as 108 looks")
add("E4_crypto_short", "E4", "2026-10-13", "short side after a +30% crypto day is profitable (144 detector-plan pairs; v2 redesigned on v1 results)",
    None, "status report 2026-10-17: v1 0 of 144 admitted; v2 failed 2023 validation", variants=144)
add("E5_idx_ranking", "E5", "2026-10-14", "daily price data ranking separates up-moves from down-moves (IDX)", 0.074,
    "status report: IDX p = 0.074 against a required 0.025")
add("E5_crypto_ranking", "E5", "2026-10-14", "same ranking test (crypto)", 0.42, "status report: crypto p = 0.42")
add("E5_us_ranking", "E5", "2026-10-14", "same ranking test (US)", None, "status report: below its controls")
add("E6_crypto_pressure", "E6", "2026-10-15", "absorption of buying or selling pressure predicts five-day returns (crypto)", 0.32,
    "status report: primary specification p = 0.32")
add("E7_crypto_funding", "E7", "2026-10-16", "negative funding with rising open interest predicts spot moves (crypto, local result)",
    round(ci(-0.35, -0.95, 0.33), 4), "derived from the reported 24h excess -0.35 pts (-0.95 to +0.33), normal approximation")
add("E8_crypto_spillover", "E8", "2026-10-16", "related coins follow a sharp rise within 72 hours (crypto)", round(ci(0.44, -0.28, 1.16), 4),
    "derived from the reported +0.44 pts (-0.28 to +1.16), normal approximation")
add("EXIT_ATR_v1", "EXIT-ATR", "2026-10-16", "an ATR trailing stop improves the +30% entry (crypto)", round(ci(-0.82, -2.92, 1.19), 4),
    "derived from the reported change -0.82 pts (-2.92 to +1.19), normal approximation")
add("US_breakout_v1", "US breakout", "2026-10-09", "buying a 60-session high with a 5% stop beats matched entries (US, 2023)",
    round(ci(-0.042, -0.115, 0.035), 4), "derived from the reported -0.042 pts (-0.115 to +0.035), normal approximation")
add("E9_catalyst_split", "E9", "2026-10-16", "movers with a supporting SEC filing beat movers without one (US)", round(ci(0.01993, -0.018334, 0.059987), 4),
    "derived from research/E9/results/RESULT.json separation_doc_minus_undoc.primary_5d, normal approximation")
add("E10_guidance_raise", "E10", "2026-10-17", "guidance raises beat matched controls after an obtainable entry (US 2020-2022)", 0.2471,
    "research/E10/results/RESULT.json classes.RAISE.excess.p_one_sided")
for h, t in (("H1_lowvol", -0.69551662), ("H2_momentum", -0.35808652), ("H3_avoid_wildest", -0.86740217)):
    add(f"LOWVOL_2005_2019_{h}", "US_LOWVOL_MOM_2005_2019", "2026-10-19", f"{h}: pre-registered monthly spread > 0 (US 2005-2019)",
        round(mt.p_from_t(t), 4), "research/US_LOWVOL_MOM_2005_2019/results/RESULT.json t-statistic")
add("IDX_capacity", "IDX capacity", "2026-10-09", "the E1 fill rule concealed a profitable strategy", None,
    "re-run of E1 with a causal fill rule; not an independent hypothesis", counted=False)
add("Zealand_pilot", "Zealand pilot", "2026-10-08", "a single event identifiable and tradable in advance", None,
    "descriptive case study, no test", counted=False)
OUT.mkdir(exist_ok=True)
for t in T:
    (OUT / f"{t['id']}.json").write_text(json.dumps(t, indent=1) + "\n")
print(len(T), "trials written;", sum(t["counted"] for t in T), "counted;", sum(t["one_sided_p"] is not None for t in T), "with a p-value")
