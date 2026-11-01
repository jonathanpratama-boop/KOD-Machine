"""Render research/VIX_BASIS_v1/run/RESULT.json as REPORT.md. Presentation only; written AFTER the one run (it is not
pinned by protocol.json and changes no number).

    python3 research/VIX_BASIS_v1/report.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = (
    "primary",
    "S1_double_costs",
    "S2_lag_2",
    "N1_threshold_0.05",
    "N2_threshold_0.15",
    "D1_both_sides",
    "B1_always_short",
    "R1_whole_vxm_contracts",
)


def pct(x, nd=1):
    return (
        "-"
        if x is None or (isinstance(x, float) and math.isnan(x))
        else f"{100 * x:+.{nd}f}%"
    )


def table(per: dict) -> list[str]:
    out = [
        (
            "| Arm | Positions (segments) | Mean net / position | Median | Win | Account (USD 10,000) | CAGR | Max DD (daily) "
            "| Worst day | Years up | Exposure | Costs/yr | P&L without top 5 | Bootstrap LB (95%, 1-sided) |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for k in ARMS:
        v = per[k]
        lb = (v.get("boot_net") or {}).get("lower_one_sided_95")
        out.append(
            f"| {k} | {v['trades']} ({v['segments']}) | {pct(v.get('mean_net'), 2)} | {pct(v.get('median_net'), 2)} | "
            f"{pct(v.get('win_rate'), 0)} | {v['end_equity']:,.0f} ({pct(v['net_return'])}) | {pct(v.get('cagr'))} | "
            f"{pct(v['max_drawdown_daily'])} | {pct(v.get('worst_day'))} | {v['years_positive']}/{len(v['by_year'])} | "
            f"{pct(v['exposure_days'], 0)} | {pct(v.get('cost_per_year_frac_equity'))} | "
            f"{v.get('pnl_without_top5', 0):,.0f} | {pct(lb, 2)} |"
        )
    s = per["spx_buy_and_hold"]
    out.append(
        f"| SPX price index, held (context) | - | - | - | - | {pct(s['price_return'])} | - | {pct(s['max_drawdown'])} | "
        "- | - | 100% | - | - | - |"
    )
    out.append(
        "| Cash | - | - | - | - | 10,000 (+0.0%) | - | - | - | - | 0% | - | - | - |"
    )
    return out


def years(per: dict) -> list[str]:
    ys = list(per["primary"]["by_year"])
    out = ["| Arm | " + " | ".join(ys) + " |", "|---|" + "---|" * len(ys)]
    for k in ("primary", "S1_double_costs", "B1_always_short"):
        out.append(
            f"| {k} | " + " | ".join(pct(per[k]["by_year"][y]) for y in ys) + " |"
        )
    return out


def main() -> int:
    r = json.loads((HERE / "run/RESULT.json").read_text())
    d, v = r["discovery"], r.get("validation")
    lines = [
        "# VIX_BASIS_v1: selling VIX futures in contango (futures study, simulation only)",
        "",
        (
            f"Ran {r['ran_at']} at commit `{r['commit']}` on the frozen protocol (`protocol.json`, sha256 "
            f"`{r['protocol_sha256'][:16]}...`, RFC 3161 timestamps in `timestamps/`). One run. Rule: the Simon-Campasano "
            "entry (front = nearest VX with >= 10 trading days; short when (F - VIX)/days > 0.10; 5-session segments), "
            "short leg only, unhedged, notional 20% of equity, 0.065 points per side, fills at settlement."
        ),
        "",
        f"## Verdict: {r['verdict']}",
        "",
        "| Gate | Result |",
        "|---|---|",
        *[f"| {k} | {val} |" for k, val in r["gates"].items()],
        "",
        "## Discovery 2006-01-03 .. 2015-12-31 (2006-2011 is the paper's own sample)",
        "",
        *table(d),
        "",
        *years(d),
        "",
    ]
    if v:
        lines += [
            "## Validation 2016-01-04 .. 2023-12-29 (after publication)",
            "",
            *table(v),
            "",
            *years(v),
            "",
        ]
    lines += [
        "## What this does and does not show",
        "",
        (
            "- Discovery passed every gate, but 2006-2011 is the sample the rule was published on, so it is not independent "
            "evidence."
        ),
        (
            "- After publication the same frozen rule earned far less: it ended above its start and stayed within the drawdown "
            "gate, but failed with doubled costs, its P&L without the 5 best positions is negative, its bootstrap lower bound "
            "is below zero, and it rose in only half the years. It trailed simply holding the S&P 500 by a wide margin."
        ),
        (
            "- Other arms (thresholds 0.05/0.15, both sides, always short, whole contracts) are reported as frozen and are "
            "not candidates: picking the best of them after seeing validation would be a new, contaminated hypothesis."
        ),
        (
            "- No stop is used and no result is a maximum loss: always-short's worst day in validation was -27% of equity at "
            "20% notional (February 2018)."
        ),
        (
            "- The account curve assumes fractional contracts (R1 shows whole Mini VIX contracts), settlement-price fills, "
            "assumed VXM costs, and no interest on collateral. Venue eligibility is not verified; eToro's VIX is a CFD, not "
            "this product."
        ),
        "- Simulation only. The sealed 2024-2026 holdout was not used and is not requested: the rule did not confirm.",
        "",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
