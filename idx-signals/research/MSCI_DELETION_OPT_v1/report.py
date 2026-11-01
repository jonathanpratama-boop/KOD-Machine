"""Render research/MSCI_DELETION_OPT_v1/run/RESULT.json and TRIALS.csv as REPORT.md (presentation only; written before
the run).

    python3 research/MSCI_DELETION_OPT_v1/report.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def pct(x, nd=2):
    return (
        "-"
        if x is None or (isinstance(x, float) and math.isnan(x))
        else f"{100 * x:+.{nd}f}%"
    )


def num(x, nd=2):
    return (
        "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"
    )


def idr(x):
    return "-" if x is None else f"{x / 1e6:,.1f}m"


def row(name: str, s: dict) -> str:
    a, e = s.get("account", {}), s.get("economics", {})
    return (
        f"| {name} | {s.get('scored_with_controls', '-')} | {pct(s.get('mean_net'))} | {pct(s.get('median_net'))} | "
        f"{pct(s.get('win_rate'), 0)} | {pct(e.get('avg_win'))} | {pct(e.get('avg_loss'))} | "
        f"{num(e.get('payoff_ratio'))} | {pct(s.get('mean_excess'))} | {pct(s.get('mean_mkt_adj'))} | "
        f"{idr(a.get('end_equity'))} ({pct(a.get('net_return'), 1)}) | {pct(a.get('max_drawdown_at_review_exits'), 1)} | "
        f"{pct(e.get('exposure_nominal_hold'), 1)} | {num(e.get('turnover_per_year'))} | "
        f"{pct(e.get('fees_per_year_pct_equity'))} |"
    )


HEAD = (
    "| Rule | Trades | Mean net | Median | Win | Avg win | Avg loss | Payoff | Excess vs controls | Over liquid market | "
    "Account (IDR 160m start) | Max DD (review exits) | Exposure | Turnover/yr | Fees/yr |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
)


COLS = (
    "scope",
    "hold",
    "scored",
    "mean_net",
    "median_net",
    "win_rate",
    "mean_excess_vs_controls",
    "mean_mkt_adj",
    "account_return",
    "max_dd_at_review_exits",
)


def fixed_table(t: pd.DataFrame) -> list[str]:
    d = t[(t.trial.str.startswith("fixed")) & (t.plan == "base")].copy()
    d["hold"] = d.trial.str.replace("fixed_hold_", "").astype(int)
    d = d.sort_values(["scope", "hold"])
    out = ["| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    for r in d.itertuples():
        cells = [r.scope, str(r.hold), str(r.scored)] + [
            pct(getattr(r, c)) for c in COLS[3:]
        ]
        out.append("| " + " | ".join(cells) + " |")
    return out


def main() -> int:
    r = json.loads((HERE / "run/RESULT.json").read_text())
    t = pd.read_csv(HERE / "run/TRIALS.csv")
    wf = r["walk_forward"]
    sel = r["selection"]
    bm = r["benchmarks"]["liquid_market_buy_and_hold"]
    lines = [
        "# MSCI_DELETION_OPT_v1: holding-period study of the MSCI Indonesia deletion trade (EXPLORATORY)",
        "",
        (
            f"Ran {r['ran_at']} at commit `{r['commit']}` on the frozen protocol (`protocol.json`, sha256 "
            f"`{r['protocol_sha256'][:16]}...`). One run. Simulation only. **Exploratory:** every review here was "
            "inspected before; the sealed 2024 reviews were not computed. The two frozen studies' trade files "
            f"reproduce: {all(r['reproduces_frozen_studies'].values())}."
        ),
        "",
        f"## Verdict: {r['verdict']}",
        "",
        "| Gate | Result |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in r["gates"].items()],
        "",
        "## Walk-forward choices (hold chosen on earlier reviews only; None = cash)",
        "",
        "| Outer review | Training reviews | Chosen hold |",
        "|---|---|---|",
        *[
            f"| {p['review']} | {p['train_reviews']} | {p['chosen']} |"
            for p in sel["picks"]
        ],
        "",
        (
            f"Most selected (reviews with a deletion; a tie with cash counts as cash): {sel['most_selected']}; counts "
            f"{sel['counts_reviews_with_deletions']}. Outer sample (W0, scored at every hold): "
            f"{r['outer_sample']['trades']} trades in {r['outer_sample']['reviews']} reviews. The hold the same procedure "
            f"picks on all 23 reviews (in-sample; for a prospective protocol only): {sel['final_choice_all_reviews']}."
        ),
        "",
        "## Walk-forward against the baseline, cash and the market (19 outer reviews; Nov23 excluded)",
        "",
        HEAD,
        row("Walk-forward (base plan)", wf["base"]),
        row("Baseline: hold 20 (v1 rule)", r["baseline_outer"]),
        *[
            row(f"Walk-forward, {pl}", wf[pl])
            for pl in ("S1_entry_next_session", "S2_tick_cost", "S3_double_fees")
        ],
        *[row(f"Walk-forward, block {b}", s) for b, s in wf["base_blocks"].items()],
        "",
        (
            f"W3 accounts (outer reviews): walk-forward {idr(r['w3_accounts']['walk_forward']['end_equity'])}"
            f", baseline {idr(r['w3_accounts']['baseline']['end_equity'])}. Walk-forward without its best review "
            f"({wf['account_without_best_review']['review']}): {idr(wf['account_without_best_review']['end_equity'])}. "
            f"P&L without the 3 largest winners: {idr(wf['base']['account']['pnl_without_top3'])}. W2's review-cluster "
            f"bootstrap one-sided 95% lower bound of the mean net trade return: "
            f"{pct((wf['base'].get('boot_net') or {}).get('lower_one_sided_95'))} "
            f"({(wf['base'].get('boot_net') or {}).get('clusters', 0)} clusters)."
        ),
        "",
        (
            "Benchmarks: cash 0%. Equal-weight liquid IDX market held through each block (rebalanced every 20 "
            f"sessions, costs once in and out): development outer {pct(bm['dev_outer']['net_return'], 1)} "
            f"({bm['dev_outer']['from_entry']} .. {bm['dev_outer']['to']}), out of time {pct(bm['oot']['net_return'], 1)} "
            f"({bm['oot']['from_entry']} .. {bm['oot']['to']}), fully invested throughout."
        ),
        "",
        "## Every fixed hold as a rule (base plan), on all 23 reviews, the 19 outer reviews and per block",
        "",
        *fixed_table(t),
        "",
        "The full trial log (every plan x hold x scope, and the walk-forward under every plan) is `run/TRIALS.csv`.",
        "",
        "## What this does and does not show",
        "",
        (
            "- Exploratory: the holding-period lever was suggested by data already seen; the walk-forward only disciplines "
            "the choice, it does not validate it."
        ),
        "- Closing-auction fills are modelled; prices after 2025-02-21 are Yahoo-sourced; drawdown is at review exits.",
        (
            "- Trade statistics use trades with matched controls; exposure (nominal hold), turnover and fees use every "
            "trade the account held; fees exclude the S2 tick; capital per review averages over reviews that traded; "
            "'over liquid market' is the return relative to an equal-weight liquid basket that cannot be shorted, not a "
            "hedged return."
        ),
        "- No stop; no result here is a guaranteed maximum loss or a forecast. No live promotion follows from it.",
        "",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
