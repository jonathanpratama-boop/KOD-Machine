"""Reconcile two E2-US runs attempt by attempt: why the denominators differ.

    python3 research/E2/repair/reconcile.py ORIGINAL_RUN_DIR REPAIRED_RUN_DIR REPAIR_PANEL_MANIFEST [--out FILE]

For every signal (ticker, signal_date) in either run it reports whether it is in both, and if
not, why: the name is quarantined in the repaired run, or the legacy preprocessing had deleted
the signal-day bar or the bar before it (so the legacy panel saw a different previous close),
or neither (listed as unexplained, never hidden). For signals in both it tabulates status
transitions (e.g. SKIP_LOT -> EXITED). It reads only the two runs' trade files, the original
panel (which rows legacy preprocessing kept) and the repair panel's manifest and flags.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from idxsig import global_panel  # noqa: E402

ORIGINAL_PANEL = ROOT / "data" / "manifests" / "panel_us-20261008T004105Z.json"


def trades(run_dir: Path) -> pd.DataFrame:
    t = pd.read_csv(run_dir / "trades.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    return t.set_index(["ticker", "signal_date"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("original", type=Path)
    ap.add_argument("repaired", type=Path)
    ap.add_argument("repair_panel", type=Path)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    a, b = trades(args.original), trades(args.repaired)
    rmeta = json.loads(args.repair_panel.read_text())
    quarantined = set(rmeta.get("unit_quarantine", {}).get("tickers", {}))
    only_a = a.index.difference(b.index)
    only_b = b.index.difference(a.index)
    both = a.index.intersection(b.index)
    names = sorted({t for t, _ in only_a.union(only_b)})

    legacy, _ = global_panel.load(ORIGINAL_PANEL)
    legacy = legacy[legacy["ticker"].isin(names) & (legacy["date"] <= "2023-12-29")]
    repair, _ = global_panel.load(args.repair_panel)
    repair = repair[repair["ticker"].isin(names)]
    legacy_rows = set(zip(legacy["ticker"], legacy["date"].dt.strftime("%Y-%m-%d")))
    rep = repair.sort_values(["ticker", "date"])
    rep["prev_date"] = rep.groupby("ticker")["date"].shift(1).dt.strftime("%Y-%m-%d")
    rep["d"] = rep["date"].dt.strftime("%Y-%m-%d")
    rep_idx = rep.set_index(["ticker", "d"])

    def why(ticker, day, side):
        if side == "original_only" and ticker in quarantined:
            return "name quarantined in the repaired run (split records not corroborated)"
        if (ticker, day) not in legacy_rows:
            return "legacy preprocessing had deleted this bar (later reversal); the causal panel keeps it"
        if (ticker, day) in rep_idx.index:
            prev = rep_idx.loc[(ticker, day), "prev_date"]
            if isinstance(prev, str) and (ticker, prev) not in legacy_rows:
                return "legacy preprocessing had deleted the bar before, so its previous close differed"
            if bool(rep_idx.loc[(ticker, day), "qa_reverting_spike"]):
                return "bar flagged as a reverting spike (kept, flag known one session later)"
        return "unexplained"

    reasons = {}
    for side, idx in (("original_only", only_a), ("repaired_only", only_b)):
        counts = {}
        examples = {}
        for t, d in idx:
            r = why(t, d, side)
            counts[r] = counts.get(r, 0) + 1
            examples.setdefault(r, []).append(f"{t} {d}")
        reasons[side] = {"count": int(len(idx)), "by_reason": counts,
                         "examples": {k: v[:8] for k, v in examples.items()}}
    trans = (pd.DataFrame({"original": a.loc[both, "status"], "repaired": b.loc[both, "status"]})
             .value_counts().rename("n").reset_index())
    trans = trans[trans["original"] != trans["repaired"]]
    sa = json.loads((args.original / "summary.json").read_text())
    sb = json.loads((args.repaired / "summary.json").read_text())

    def side(s):
        rt, mr = s["rule_trades"], s["random_matched"]
        return {"signals": s["signals"]["total"], "attempted": s["signals"]["attempted"],
                "skipped_overlap": s["signals"]["skipped_overlap"], "scored": rt["scored"],
                "status_counts": rt["status_counts"], "avg_net_return": rt["avg_net_return"],
                "median_net_return": rt["median_net_return"], "hit_rate": rt["hit_rate"],
                "matched_random_avg_net_return": (mr.get("avg_net_return") or {}).get("random_mean"),
                "matched_random_p2_5": (mr.get("avg_net_return") or {}).get("random_p2_5"),
                "matched_random_p97_5": (mr.get("avg_net_return") or {}).get("random_p97_5"),
                "p_one_sided_vs_matched": (mr.get("avg_net_return") or {}).get("p_value_one_sided"),
                "matched_pooled_status_counts": mr["pooled"]["status_counts"],
                "evaluable_ticker_sessions": s["universe"]["evaluable_ticker_sessions"],
                "tickers_ever_evaluable": s["universe"]["tickers_ever_evaluable"]}

    out = {"original_run": args.original.name, "repaired_run": args.repaired.name,
           "repair_panel": args.repair_panel.name, "original": side(sa), "repaired": side(sb),
           "signals_in_both": int(len(both)), **reasons,
           "status_transitions_for_signals_in_both": trans.to_dict(orient="records")}
    text = json.dumps(out, indent=2, sort_keys=True, default=str) + "\n"
    if args.out:
        with open(args.out, "x", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
