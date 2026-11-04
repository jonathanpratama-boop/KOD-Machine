"""RECENT_REPLAY_v1: render REPORT.md from results/RESULT.json in plain words (read-only; run.py is the one run)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def pct(x, d=0):
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def num(x, d=3):
    return "n/a" if x is None else f"{x:.{d}f}"


def gain(g):
    return "n/a" if not g else f"{g['mean']:+.4f} (se {g['se']:.4f}, {g['blocks']} blocks)"


def main() -> int:
    r = json.loads((HERE / "results" / "RESULT.json").read_text(encoding="utf-8"))
    p = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    c, st, cc = r["claim"], r["statements"], r["certified_calls"]
    h, k = st["NEXT_DUMP10_1"], st["DUMP10_5"]
    lo, hi = r["range"]
    verdict = c["verdict"]
    lines = [f"# RECENT_REPLAY_v1: result (one run, {r['ran_at'][:10]})", "",
             f"Protocol `protocol.json` (frozen {p['frozen_at']}), `PROTOCOL.md`. LEARNER v2.4 replayed session by session "
             f"over the US +30% spikes of {lo}..{hi}: {r['events']} events on {r['sessions']} sessions, {r['pairs']} graded "
             f"pairs. Every number is in `results/RESULT.json`; every forecast and outcome in `results/forecasts.csv.gz`.", "",
             "## The three plain answers", "",
             "**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower "
             "at the next session, when most of its twins do not?", "",
             f"**What counts as success?** The registered bar of the live test: the forecasts rank the dumpers above the others "
             f"with z >= {p['learner']['claim']['z_min'][0]} at the first look of {p['learner']['claim']['looks'][0]} pairs "
             f"({p['learner']['claim']['min_sessions'][0]} sessions), {p['learner']['claim']['z_min'][1]} at the later looks.", "",
             f"**What is the evidence?** {h['n']} next-session outcomes over {r['sessions']} sessions: AUC {num(c['auc'])} "
             f"(benchmark {num(c['auc_bench'])}), se {num(c['se'])}, z {num(c['z'], 2)}, look {c['look']}. "
             f"**Verdict: {verdict}.**", "",
             "## Headline: the next-session dump", "",
             "| | v2.4 raw | benchmark |", "|---|---|---|",
             f"| AUC | {num(h['auc'])} | {num(h['auc_bench'])} |",
             f"| Brier gain over the base rate | {gain(h['brier_gain_vs_base'])} | {gain(h['bench_gain_vs_base'])} |",
             f"| Brier gain of v2.4 over the benchmark | {gain(h['brier_gain_vs_bench'])} | |", "",
             f"Base rate of the statement (own dump at the next session): {pct(h['rate'], 1)} of {h['n']}; raw next-session "
             f"dump (any, twins aside): {pct(r['raw_dump_rate_next_session'], 1)}.", "",
             "### By month", "", "| month | pairs | own-dump rate | AUC |", "|---|---:|---:|---:|"]
    for mth, v in r["by_month"].items():
        lines.append(f"| {mth} | {v['n']} | {pct(v['rate'], 1)} | {num(v['auc'])} |")
    lines += ["", "## Companion: the 5-session plan ends 10% down", "",
              f"{k['n']} graded (ungraded {r['ungraded']['DUMP10_5']}: window still open or no entry); own-dump rate "
              f"{pct(k['rate'], 1)}; AUC {num(k['auc'])} (benchmark {num(k['auc_bench'])}); Brier gain over the base rate "
              f"{gain(k['brier_gain_vs_base'])}, over the benchmark {gain(k['brier_gain_vs_bench'])}.", "",
              "## Certified next-day dump calls (idxsig.call_cert)", "",
              f"{cc['calls']} calls on {r['events']} events ({pct(cc['share_of_events'], 1)}), {cc['graded']} graded: "
              f"{cc['wrong']} wrong, losing rate {pct(cc['losing_rate'], 1)} against the certified {pct(cc['certified_bound'])} "
              f"(exact binomial p that a true losing rate of {pct(cc['certified_bound'])} or worse gives this few or fewer: "
              f"{num(cc['p_losing_rate_at_or_above_bound'])}).", ""]
    if cc["calls_list"]:
        lines += ["| ticker | session | score | bar | dumped |", "|---|---|---:|---:|---|"]
        lines += [f"| {x['ticker']} | {x['session']} | {x['score']:.3f} | {x['threshold']:.3f} | "
                  f"{'yes' if x['dumped'] == 1 else 'no' if x['dumped'] == 0 else 'ungraded'} |" for x in cc["calls_list"]]
        lines.append("")
    lines += ["## What it does not show", "",
              "- A live record: the forecasts were replayed, not sealed that evening; the live ledger (paper/learner_v3.jsonl) "
              "stays the only prospective record and its registered looks stand.",
              "- Names delisted between the range and 2026-10-30 are absent (survivorship); the twins and the breadth and "
              "market features come from this pull's frame (see PROTOCOL.md).",
              "- Nothing here changes v2.4; a later version is tested on live data or on a period sealed from now on.", ""]
    (HERE / "REPORT.md").write_text("\n".join(lines))
    print((HERE / "REPORT.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
