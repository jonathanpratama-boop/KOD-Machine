"""CRYPTO_REPLAY_v1: write REPORT.md from run/RESULT.json. The verdict sentences follow fixed rules from the numbers.

python3 research/CRYPTO_REPLAY_v1/report.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ("summary", "sequence", "shuffled", "cash")


def pct(x, d=2):
    return "-" if x is None else f"{x * 100:+.{d}f}%"


def usd(x):
    return "-" if x is None else f"{x:,.2f}"


def num(x, d=2):
    return "-" if x is None else f"{x:.{d}f}"


def verdict(res: dict) -> list[str]:
    s = res["scenarios"]
    names = list(s)
    out = []
    base = s["BASE"]["arms"]
    winners = [
        a
        for a in ("summary", "sequence", "shuffled")
        if base[a]["end_equity"] > base["cash"]["end_equity"]
    ]
    out.append(
        "In the primary scenario no model arm ended above cash."
        if not winners
        else f"In the primary scenario {', '.join(winners)} ended above cash."
    )
    above_cash_everywhere = [
        a
        for a in ("summary", "sequence", "shuffled")
        if all(s[n]["arms"][a]["end_equity"] > s[n]["arms"]["cash"]["end_equity"] for n in names)
    ]
    out.append(
        f"Above cash in all four scenarios: {', '.join(above_cash_everywhere)}."
        if above_cash_everywhere
        else "No model arm stayed above cash in all four scenarios (delay and doubled costs included)."
    )
    seq_beats = [
        n
        for n in names
        if s[n]["comparisons"]["sequence_minus_summary"]["end_equity_difference"] > 0
    ]
    out.append(
        f"Sequence ended above summary in {len(seq_beats)} of {len(names)} scenarios"
        + (f" ({', '.join(seq_beats)})." if seq_beats else ".")
    )
    clear = [
        n
        for n in names
        if s[n]["comparisons"]["sequence_minus_summary"]["lower95"] > 0
        or s[n]["comparisons"]["sequence_minus_summary"]["upper95"] < 0
    ]
    out.append(
        "The sequence-minus-summary interval excludes zero in: " + ", ".join(clear) + "."
        if clear
        else "The sequence-minus-summary interval includes zero in every scenario: no clear executable difference."
    )
    trades = min(s["BASE"]["arms"][a]["closed_trades"] for a in ("summary", "sequence", "shuffled"))
    out.append(
        f"The fewest closed trades in any model arm (primary scenario) is {trades}: too few for certainty."
    )
    return out


def render(res: dict) -> str:
    q = res["predictive_ranking_quality"]
    lines = [
        "# CRYPTO_REPLAY_v1: 2023 historical crypto paper-account replay",
        "",
        f"Ran {res['ran_at']} at commit `{res['code']['commit_at_run']}`. {res['status']}",
        "",
        "## Verdict (fixed rules, from the numbers)",
        "",
        *[f"- {v}" for v in verdict(res)],
        "",
        "## What was traded",
        "",
        (
            "Every day's frozen top-five early-population shortlist (ret1 < 10%, ret5 < 20%) was offered to the "
            "account in rank order; the account limits decided which names entered. Arms: summary and sequence "
            "(frozen PREMOVE_SEQUENCE_v1 models, rankings rebuilt and verified against its summary.json), shuffled "
            "(the frozen shuffled-sequence control from PREMOVE_SHADOW_v1/control_model.json, fitted on 2020-2022, "
            "not part of the PR #19 run) and cash. A hypothetical test of the rankings: not the live PASS-only "
            "policy and no permission to buy."
        ),
        "",
        "## Ranking quality (prediction) versus account result (execution)",
        "",
        f"Each arm put {q['alerts_per_arm']} names on its 2023 early-population shortlist (5 a day). "
        f"Up hits (barrier reached first on a daily close within 5 days): "
        + ", ".join(
            f"{a} {q['rebuilt_early_shortlist_up_hits'][a]}"
            for a in q["rebuilt_early_shortlist_up_hits"]
        )
        + f" (published: summary {q['published_early_shortlist_up_hits']['summary']}, sequence "
        f"{q['published_early_shortlist_up_hits']['sequence']}). {q['note']}.",
        "",
    ]
    for name, sc in res["scenarios"].items():
        p = sc["policy"]
        lines += [
            (
                f"## Scenario {name}: entry delay {p['entry_delay']} bar(s), fee {p['fee']:.1%} + slippage "
                f"{p['slip']:.1%} per side"
            ),
            "",
            (
                "| Arm | End equity | Net return | Realized | Unrealized | Max drawdown | Closed trades | "
                "Win rate | Avg win | Avg loss | Expectancy | Profit factor | Fees | Slippage | Mean exposure | "
                "Turnover |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for a in ARMS:
            m = sc["arms"][a]
            lines.append(
                f"| {a} | {usd(m['end_equity'])} | {pct(m['net_return'])} | {usd(m['realized_pnl'])} | "
                f"{usd(m['unrealized_pnl'])} | {pct(m['max_drawdown'])} ({m['max_drawdown_day']}) | "
                f"{m['closed_trades']} | {pct(m['win_rate'], 1)} | {usd(m['average_win'])} | "
                f"{usd(m['average_loss'])} | {usd(m['expectancy_per_trade'])} | {num(m['profit_factor'])} | "
                f"{usd(m['fees_usd'])} | {usd(m['slippage_usd'])} | {pct(m['mean_exposure'], 1)} | "
                f"{num(m['turnover'])} |"
            )
        lines += ["", "Exit reasons, skips, rejections and data gaps:", ""]
        for a in ("summary", "sequence", "shuffled"):
            m = sc["arms"][a]
            unresolved = (
                "; ".join(
                    f"{u['ticker']} valued {usd(u['value'])} at the close of {u['valued_at_close_of']} "
                    f"(unrealized {usd(u['unrealized'])}, deadline {u['deadline']})"
                    for u in m["unresolved"]
                )
                or "none"
            )
            unfilled = (
                ", ".join(f"{u['ticker']} (entry {u['entry_day']})" for u in m["unfilled"])
                or "none"
            )
            lines.append(
                f"- **{a}**: orders {m['orders']}, fills {m['fills']}; exits {m['exit_reasons']}; "
                f"counters {m['skips_and_rejections']}; unresolved at the data end: {unresolved}; "
                f"unfilled at the data end: {unfilled}."
            )
        lines += [
            "",
            "Paired comparisons (moving-block bootstrap of daily return differences, descriptive):",
            "",
        ]
        for key, c in sc["comparisons"].items():
            lines.append(
                f"- {key}: end equity {c['end_equity_difference']:+,.2f} USDT; summed daily return difference "
                f"{pct(c['sum_of_daily_return_differences'])} (95% interval {pct(c['lower95'])} to {pct(c['upper95'])})"
            )
        lines.append("")
    lines += [
        "## Checks on every arm and scenario",
        "",
        (
            "Invariants (no fill on or before its decision, exits after fills, no overspending, equity = start + "
            "realized + unrealized every day), the cross-check of cash, reservations and realized P&L against the "
            "US paper account's tested accounting, and a repeat run with an identical fingerprint: all passed, or "
            "the run would have stopped."
        ),
        "",
        "## Limits",
        "",
        "- 2023 was studied before: development evidence, not validation. The 2024+ holdout was not read.",
        (
            "- Daily bars: a touched price is not a guaranteed fill; intraday order is unknown (stop-first when "
            "both levels are touched); no depth or queue position."
        ),
        "- Costs are assumptions. The universe is today's archive catalogue, so delisted coins are missing.",
        "- One year and a few hundred decisions at most: no statistical certainty.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    res = json.loads((HERE / "run" / "RESULT.json").read_text())
    (HERE / "REPORT.md").write_text(render(res), encoding="utf-8")
    print((HERE / "REPORT.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
