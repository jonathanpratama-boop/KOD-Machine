"""Render research/MSCI_DELETION_v1/run/RESULT.json as REPORT.md (presentation only; written before the run).

python3 research/MSCI_DELETION_v1/report.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def pc(x, d=2):
    return "n/a" if x is None else f"{x * 100:+.{d}f}%"


def idr(x):
    return "n/a" if x is None else f"IDR {x / 1e6:,.1f}m"


VARIANTS = (
    ("primary", "Primary: buy the implementation close, hold 20"),
    ("S1_entry_next_session", "S1: buy one session later"),
    ("S2_tick_cost", "S2: one tick per side added"),
    ("descriptive_hold_5", "Descriptive: hold 5"),
    ("descriptive_hold_60", "Descriptive: hold 60"),
)


def table(p: dict) -> list[str]:
    out = [
        (
            "| Variant | Scored | Mean net | Median net | Win rate | Worst / best | Mean matched control | Mean excess |"
            " Excess 95% (review clusters) |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for k, label in VARIANTS:
        v = p.get(k, {})
        if not v.get("scored_with_controls"):
            out.append(f"| {label} | 0 | | | | | | | |")
            continue
        be = v.get("boot_excess", {})
        out.append(
            f"| {label} | {v['scored_with_controls']} | {pc(v['mean_net'])} | {pc(v['median_net'])} | "
            f"{v['win_rate']:.0%} | {pc(v['worst_net'])} / {pc(v['best_net'])} | {pc(v['mean_control'])} | "
            f"{pc(v['mean_excess'])} | {pc(be.get('lower95'))} to {pc(be.get('upper95'))} |"
        )
    return out


def period(name: str, p: dict) -> list[str]:
    a, pr = p["account"], p["primary"]
    bn = pr.get("boot_net", {})
    return [
        f"## {name}",
        "",
        *table(p),
        "",
        (
            f"- Mean net (primary) review-cluster bootstrap: 95% {pc(bn.get('lower95'))} to {pc(bn.get('upper95'))}, "
            f"one-sided lower bound {pc(bn.get('lower_one_sided_95'))}, {bn.get('clusters')} reviews."
        ),
        (
            f"- Account (slots fixed before the auction, each at most 25% of equity and IDR 40m, cash otherwise): {idr(a['start'])} -> "
            f"{idr(a['end_equity'])} ({pc(a['net_return'])}), cash stays {idr(a['start'])}; drawdown at review "
            f"exits {pc(a['max_drawdown_at_review_exits'])}; {a['trades']} trades over {a['reviews_traded']} reviews; mean "
            f"capital deployed per review {a['mean_capital_per_review']:.0%}; P&L without the 3 largest winners "
            f"{idr(a['pnl_without_top3'])}."
        ),
        (
            f"- Account without its best review ({p['account_without_best_review']['review']}): "
            f"{idr(p['account_without_best_review']['end_equity'])} "
            f"({pc(p['account_without_best_review']['net_return'])})."
        ),
        f"- Match levels of scored events (0 = every bucket): {pr.get('match_levels')}.",
        f"- Status counts (primary): {pr['status']}.",
        f"- By deletion kind: {json.dumps(pr.get('by_kind', {}))}",
        f"- By review: {json.dumps(pr.get('by_review', {}))}",
        "",
    ]


def main() -> int:
    r = json.loads((HERE / "run/RESULT.json").read_text())
    L = [
        "# MSCI_DELETION_v1: buying MSCI Indonesia deletions in the trackers' closing auction",
        "",
        (
            f"Ran {r['ran_at']} at commit `{r['commit']}` on the frozen protocol. One run. Simulation only; IDX data to "
            "2023-12-29 (the sealed holdout 2024-01-02..2025-02-21 was not read)."
        ),
        "",
        f"## Verdict: {r['verdict']}",
        "",
        "| Gate | Result |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in r["gates"].items()],
        "",
        *period("Discovery (reviews Nov 2019 .. Nov 2022)", r["discovery"]),
        *period("2023 provisional screen (an already-used year)", r["screen_2023"]),
        "## What this does and does not show",
        "",
        (
            "- Development data with 8 discovery reviews; May 2020 (after the COVID low) holds 20 of 46 events. Matched "
            "controls bought at the same close absorb market moves."
        ),
        "- Closing-auction fills are the harness's model (decision-time capacity, 10% participation), not observed fills.",
        (
            "- Between-review MSCI changes are not included. Forward relevance depends on MSCI's treatment of Indonesia "
            "(additions frozen since Jan 2026; reclassification proposed, decision by 30 Jun 2027) and on the IDX "
            "short-selling restart."
        ),
        "",
    ]
    (HERE / "REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
