"""Diagnostic (2026-10-08, after the fact): how much do later reverse splits distort the E2 US
trading run?

Yahoo rescales a name's whole price history at every split. A stock that traded at $0.30 in
2023 and reverse-split 1-for-1000 in 2025 appears in the 2023 panel at $300. Returns are ratios
and are unaffected; anything that uses the price LEVEL is not point-in-time: the cost tier, the
price band used for matching, and the share count (a price above the $5,000 notional gives
SKIP_LOT). This script takes every attempt of the run, finds the splits Yahoo reports after its
signal date, and re-costs the scored trades at the price actually traded then.

It reads the committed run (results/runs/...) and the raw Yahoo files named by the yahoo_us
manifest (raw files are not in git; each is checked against the manifest hash). It looks at the
2023 validation window, so it is a diagnostic of the measurement, not evidence for any filter.

    python3 research/E2/diagnostics/us_reverse_splits.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import read_manifest, sha256_file  # noqa: E402

RUN = ROOT / "results" / "runs" / "20261008T060443Z_MOONSHOT_E2_US_D1_v1"
MANIFEST = ROOT / "data" / "manifests" / "yahoo_us-20261008T001812Z.jsonl"
OUT = Path(__file__).with_name("us_reverse_splits.json")
TIERS = ((1, 0.015), (5, 0.005), (20, 0.0015), (float("inf"), 0.0005))  # profiles.US
SEC_FEE = 0.0000278


def tier(price):
    return np.select([price < b for b, _ in TIERS[:-1]], [c for _, c in TIERS[:-1]], TIERS[-1][1])


def main():
    trades = pd.read_csv(RUN / "trades.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    _, records = read_manifest(MANIFEST)
    splits, mismatched = {}, 0
    for rec in records:
        if rec.get("http_status") != 200 or rec["ticker"] not in set(trades["ticker"]):
            continue
        path = ROOT / rec["path"]
        if sha256_file(path) != rec["sha256"]:
            mismatched += 1
            continue
        events = (json.loads(path.read_text())["chart"]["result"][0].get("events") or {}).get("splits") or {}
        splits[rec["ticker"]] = [(int(v["date"]), float(v["numerator"]), float(v["denominator"]))
                                 for v in events.values()]

    def factor_after(ticker, day):
        """actual price on `day` = panel (adjusted) price x factor; < 1 after a later reverse split."""
        cutoff = pd.Timestamp(day).timestamp() + 86_400
        return float(np.prod([num / den for t, num, den in splits.get(ticker, []) if t > cutoff] or [1.0]))

    trades["factor"] = [factor_after(t, d) for t, d in zip(trades["ticker"], trades["signal_date"])]
    trades["reverse_split_later"] = trades["factor"] < 1
    scored = trades[trades["status"].isin(["EXITED", "EXIT_DATA_END"])].copy()
    actual = scored["entry_price"] * scored["factor"]
    cost = tier(actual)
    scored["net_point_in_time"] = (1 + scored["gross_return"]) * (1 - cost - SEC_FEE) / (1 + cost) - 1
    out = {
        "run": RUN.name, "manifest": MANIFEST.name, "raw_files_not_matching_manifest": mismatched,
        "attempts": int(len(trades)),
        "attempts_with_later_reverse_split": int(trades["reverse_split_later"].sum()),
        "status_by_later_reverse_split": {
            str(k): {str(c): int(v) for c, v in row.items()}
            for k, row in pd.crosstab(trades["status"], trades["reverse_split_later"]).iterrows()},
        "scored": int(len(scored)),
        "scored_cost_tier_changes_at_actual_price": int((tier(scored["entry_price"]) != cost).sum()),
        "avg_net_as_run": float(scored["net_return"].mean()),
        "avg_net_point_in_time_costs": float(scored["net_point_in_time"].mean()),
        "avg_net_as_run_later_reverse_split": float(scored.loc[scored["reverse_split_later"], "net_return"].mean()),
        "avg_net_as_run_no_later_reverse_split": float(scored.loc[~scored["reverse_split_later"], "net_return"].mean()),
        "note": ("2023 validation data, looked at after the fact. A later reverse split is not known at the "
                 "signal date, so it cannot be used as a filter; the matched random baseline was not re-costed."),
    }
    with OUT.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
