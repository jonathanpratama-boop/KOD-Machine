"""Write the two readable reports from results/dry_run.json and results/effect.json. No outcome is read here beyond what
those files already hold; the count-only table reads identifiers only."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
ROOT = HERE.parents[1]


def pct(x, d=0):
    return "-" if x is None else f"{x * 100:+,.{d}f}%"


def num(x, d=3):
    return "-" if x is None else f"{x:.{d}f}"


def main() -> None:
    dry = json.loads((OUT / "dry_run.json").read_text())
    eff = json.loads((OUT / "effect.json").read_text())
    first = json.loads((OUT / "first-run" / "dry_run.json").read_text())
    second = json.loads((OUT / "second-run" / "dry_run.json").read_text())

    d = ["# SPLIT_REVISIONS_v1: dry run of the assessments", ""]
    d.append(
        f"Generated {dry['generated_at']} on repository commit `{dry['repository_commit'][:7]}`, from the provider responses "
        f"recorded on 2026-11-12. No live ledger was written: the {dry['records_proposed']} proposed records were sealed into a "
        "temporary ledger, validated there, and are listed in `dry_run_records.jsonl`. This is the run under contract "
        "addenda 1 and 2; the two earlier runs are kept in `first-run/` and `second-run/`."
    )
    d += ["", "## What the command would append", "", "| Assessment | Sets |", "|---|---:|"]
    d += [f"| {k} | {v} |" for k, v in dry["by_assessment"].items()]
    d += [
        "",
        f"- Sealed US sets: {dry['sets']}. Responses read: {dry['responses_parsed']['tickers']} tickers, "
        f"{dry['responses_parsed']['with_bars']} with bars.",
        f"- Validator problems on the temporary ledger: {len(dry['validator_problems'])}.",
        f"- Records a second pass over the same pull would add: {dry['second_pass_changes']}.",
        f"- Left out of the corrected view ({len(dry['removed_corrected'])}): {', '.join(dry['removed_corrected'])}.",
        f"- Left out of the view as known at the time ({len(dry['removed_at_the_time'])}): {', '.join(dry['removed_at_the_time']) or 'none'}.",
        f"- Unresolved, kept in every view ({len(dry['unresolved'])}): {', '.join(dry['unresolved'])}.",
    ]
    c = dry["cross_check_with_kodcheck_run"]
    if c:
        d.append(
            f"- Against the KODCHECK run of 2026-11-12 on the same sets: {c['same_class']} of {c['compared']} classes are the "
            f"same. The {len(c['different'])} that differ are the sets of addenda 1 and 2: the KODCHECK run reported "
            "them as \"no corporate action found\"."
        )
    d += [
        f"- First run, before addendum 1: {first['by_assessment'].get('NO_ACTION_FOUND')} `NO_ACTION_FOUND` and no "
        "`NOT_ASSESSABLE`; four of those sets (GNTA, HUBC, RCT, SGRX) had a provider response with no bars.",
        f"- Second run, under addendum 1 only: {second['by_assessment'].get('NO_ACTION_FOUND')} `NO_ACTION_FOUND` and "
        f"{second['by_assessment'].get('NOT_ASSESSABLE')} `NOT_ASSESSABLE`; one more set (ADIL 2026-10-28) had a "
        "response that holds only the signal session's bar.",
        f"- In this run every one of the {dry['by_assessment'].get('NO_ACTION_FOUND')} `NO_ACTION_FOUND` sets has its "
        "previous session identified in the provider's bars.",
    ]
    d += [
        "",
        "## The named cases and every set that is not a plain pass",
        "",
        "| Set | Recorded move | Tag at the time | Tag recorded | Entry cutoff | Assessment | Split used | Adjusted move | Previous bar | Units |",
        "|---|---:|---|---|---|---|---|---:|---|---|",
    ]
    for r in dry["affected_sets"]:
        prev = "-" if not r["previous_session"] else f"{r['previous_session']} ({r['previous_session_source']})"
        d.append(
            f"| {r['set']} | {pct(r['recorded_ret1'])} | {r['tag_at_the_time']} | {r['tag_recorded']} | {r['entry_cutoff']} | "
            f"{r['assessment']} | {r['split'] or '-'} | {pct(r['split_adjusted_ret1'])} | {prev} | {r['units']} |"
        )
    src = [r for r in dry["affected_sets"] if r["sources"]]
    d += ["", "Sources recorded on a record:"] + [f"- {r['set']}: {', '.join(r['sources'])}" for r in src]
    d += [
        "",
        "## Reading the three named cases",
        "",
        "- **SMX 2026-11-10.** The recorded previous close is found unchanged in the pull at 2026-11-09, the split's own "
        "effective session, so the previous bar does not precede the split and both closes are in the same units. The "
        "V11 tag was recorded 52 minutes before the entry cutoff: it is the one artifact tag that was available before a "
        "trade, and current evidence does not support it.",
        "- **GOVX and SLXN 2026-11-11.** The pull lists a 1-for-24 split on the signal session and shows the previous "
        "session's close multiplied by 24, so the sealed previous close was in pre-split units. Both tags at the time "
        "were `INDETERMINATE`.",
        "",
        "## What this does not show",
        "",
        "The assessments above are first assessments from a later pull. A reassessment that supersedes an assessment made "
        "at sealing will first occur on a scheduled run after the merge. No recorded pull of a sealing night was "
        "available to this branch. `SIMULATION.md` runs the nightly function on a reconstruction of that night and on "
        "the nights after it; the scheduled job itself has not run this code.",
        "",
    ]
    (OUT / "DRY_RUN.md").write_text("\n".join(d), encoding="utf-8")

    e = ["# SPLIT_REVISIONS_v1: effect on published results (descriptive)", ""]
    e.append(
        f"Generated {eff['generated_at']} from the ledgers at repository commit `{dry['repository_commit'][:7]}`, with each "
        "consumer's own code, under `PROTOCOL.md`. Left column: every record. Right column: without the "
        f"{len(eff['sets_left_out'])} sets that current evidence classes as split artifacts. The "
        f"{len(eff['unresolved_kept_in_both'])} unresolved sets are in both columns. No verdict changes: every frozen "
        "verdict stays as frozen, and no scheduled look is taken here."
    )
    e += ["", f"Sets left out: {', '.join(eff['sets_left_out'])}.", "", f"Unresolved, kept: {', '.join(eff['unresolved_kept_in_both'])}.", ""]
    e += ["## Paper book", ""]
    sec = (OUT / "PAPER_BOOK_secondary_view.md").read_text().splitlines()
    start = next(i for i, l in enumerate(sec) if l.startswith("| Book | View"))
    e += sec[start:]
    e += ["", "## Speculation register, US", "", "All sets:", ""] + [l for l in eff["speculation_register_US"]["as_published"] if l.startswith("|")][:3]
    e += ["", "Without the artifact sets:", ""] + [l for l in eff["speculation_register_US"]["corrected"] if l.startswith("|")][:3]
    a, b = eff["speculation_register_US"]["as_published"], eff["speculation_register_US"]["corrected"]
    sa = {l.split("|")[1].strip(): l for l in a if l.startswith("| ") and l.split("|")[1].strip().isupper() and "_" in l.split("|")[1]}
    sb = {l.split("|")[1].strip(): l for l in b if l.startswith("| ") and l.split("|")[1].strip().isupper() and "_" in l.split("|")[1]}
    e += ["", "| Statement | Graded | Realised rate | Twins' rate | Brier (register) | Graded, corrected | Realised rate, corrected | Twins' rate, corrected | Brier (register), corrected |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k in sa:
        x, y = [c.strip() for c in sa[k].split("|")], [c.strip() for c in sb.get(k, "").split("|")]
        if len(x) > 6 and len(y) > 6 and x[2] != "0":
            e.append(f"| {k} | {x[2]} | {x[3]} | {x[4]} | {x[6]} | {y[2]} | {y[3]} | {y[4]} | {y[6]} |")
    l3 = eff["learner_v2_4"]
    e += ["", "## LEARNER v2.4 (descriptive metrics; no planned evaluation is frozen)", "", "| Statement | Pairs | Rate | AUC | Benchmark AUC | Pairs, corrected | Rate, corrected | AUC, corrected | Benchmark AUC, corrected |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s, x in l3["as_published"]["statements"].items():
        y = l3["corrected"]["statements"][s]
        e.append(f"| {s} | {x['n']} | {num(x['rate'])} | {num(x['auc'])} | {num(x['auc_bench'])} | {y['n']} | {num(y['rate'])} | {num(y['auc'])} | {num(y['auc_bench'])} |")
    e += ["", f"Pairs on the sets left out: {l3['pairs_on_left_out_sets']}. The report printed on 2026-11-11 shows 74 headline pairs and an AUC of 0.693; it predates the outcomes resolved since."]
    l2 = eff["learner_v2_2_SPEC_US"]
    e += ["", "## LEARNER v2.2, US speculation statements", "", "| Statement | n | Rate | Brier anchor | Brier raw | n, corrected | Rate, corrected | Brier anchor, corrected | Brier raw, corrected |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s, x in l2["as_published"].items():
        y = l2["corrected"].get(s) or {}
        e.append(f"| {s} | {x['n']:g} | {num(x['rate'], 2)} | {num(x['brier_anchor'], 4)} | {num(x['brier_raw'], 4)} | {y.get('n', 0):g} | {num(y.get('rate'), 2)} | {num(y.get('brier_anchor'), 4)} | {num(y.get('brier_raw'), 4)} |")
    e += ["", f"Pairs on the sets left out: {l2['pairs_on_left_out_sets']}."]

    # count only: identifiers, no outcome field read
    ids = {}
    for line in (ROOT / "paper" / "speculations.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r.get("market") == "US" and "decision" in r:
            ids[f"{r['ticker']} {r['signal_session']}"] = r["set_id"][len("SPEC-"):]
    wanted = {ids[n] for n in eff["sets_left_out"]}
    files = [("LLM_ARM_v1 US calls (first look not taken)", sorted((ROOT / "research" / "LLM_ARM_v1").glob("calls_US_*.jsonl"))),
             ("Catalyst tags and sets", [ROOT / "paper" / "catalysts.jsonl"]),
             ("Decision ledger", [ROOT / "paper" / "ledger.jsonl"]),
             ("Paper account", [ROOT / "paper" / "paper_account.jsonl"])]
    e += ["", "## Consumers reported by count only", "", "| Consumer | Records citing a set left out | Sets left out that are cited |", "|---|---:|---:|"]
    for name, paths in files:
        hits, cited = 0, set()
        for p in paths:
            for line in p.read_text().splitlines():
                got = {w for w in wanted if w in line}
                if got:
                    hits += 1
                    cited |= got
        e.append(f"| {name} | {hits} | {len(cited)} |")
    e += ["", "The paper account's records on these sets are declined candidates; the KODCHECK trace of 2026-11-12 found no order, entry or exit on any of them.", ""]
    (OUT / "EFFECT.md").write_text("\n".join(e), encoding="utf-8")
    print("written", OUT / "DRY_RUN.md", "and", OUT / "EFFECT.md")


if __name__ == "__main__":
    main()
