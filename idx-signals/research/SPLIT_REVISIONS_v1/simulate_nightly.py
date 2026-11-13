"""SPLIT_REVISIONS_v1: four simulated nights through the real nightly hook, on a temporary ledger.

Usage (from idx-signals/):  python3 research/SPLIT_REVISIONS_v1/simulate_nightly.py EVIDENCE_DIR

The scheduled job cannot be run from this branch, so the function the job calls (`cli._split_assess_hook`) is run here
against manifests built from the provider responses recorded on 2026-11-12 (see `dry_run_and_effect.py`).

- Night 1 stands for the run of 2026-11-11 23:00 UTC, the night the 19 sets of 2026-11-11 were sealed. For GOVX and
  SLXN the response is put back into the state the scan saw: the split event removed and the closes before the signal
  session divided by 24. That state is a RECONSTRUCTION from the later response; no pull of that night was available
  to this branch. The script checks it against the sealed record: the reconstructed previous close must equal the
  previous close the scan recorded.
- Night 2 holds the responses as recorded on 2026-11-12, split events and re-based closes included.
- Night 3 is night 2 with GOVX's response replaced by a response without bars (the shape the provider returned for
  four other names on 2026-11-12).
- Night 4 is night 2 again: the provider answers for GOVX again.

Nothing outside a temporary directory is written, except `results/simulation.json` and `results/SIMULATION.md`.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dry_run_and_effect import build_payloads  # noqa: E402

from idxsig import cli, paper, provenance, speculation, split_flags, split_units  # noqa: E402
from idxsig import split_assessments as SA  # noqa: E402

LATE = ("GOVX", "SLXN")
NAMED = LATE + ("SMX",)
OUT = Path(__file__).resolve().parent / "results"
NIGHTS = (
    ("night_1", "2026-11-11T23:00:40Z", "the scan's own pull: the provider does not list the split of GOVX and SLXN yet"),
    ("night_2", "2026-11-12T23:00:40Z", "the provider now lists the split and shows re-based closes"),
    ("night_3", "2026-11-13T23:00:40Z", "the provider returns no bars for GOVX"),
    ("night_4", "2026-11-14T23:00:40Z", "the provider answers for GOVX again"),
)


def as_at_sealing(payload: dict) -> dict:
    """The response without its split events and with every close before the last bar divided by the split factor."""
    p = copy.deepcopy(payload)
    result = p["chart"]["result"][0]
    event = split_flags.provider_splits(payload)[-1]
    k = event["denominator"] / event["numerator"]
    result["events"] = {}
    closes = result["indicators"]["quote"][0]["close"]
    result["indicators"]["quote"][0]["close"] = [None if c is None else c / k for c in closes[:-1]] + closes[-1:]
    return p


def without_bars(template: dict, ticker: str) -> dict:
    p = copy.deepcopy(template)
    p["chart"]["result"][0]["meta"]["symbol"] = ticker
    return p


def manifest(folder: Path, name: str, payloads: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    rows = [{"manifest": name}]
    for ticker, payload in sorted(payloads.items()):
        if payload is None:
            rows.append({"ticker": ticker, "http_status": 0, "path": ""})
            continue
        path = folder / f"{ticker}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        rows.append({"ticker": ticker, "http_status": 200, "path": str(path)})
    out = folder / f"{name}.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return out


def main() -> int:
    evidence = Path(sys.argv[1])
    specs = speculation.spec_lines()
    sets = [s for s in specs if SA._is_set(s)]
    by_id = {s["set_id"]: s for s in sets}
    name = lambda sid: f"{by_id[sid]['ticker']} {by_id[sid]['signal_session']}"  # noqa: E731
    recorded, _ = build_payloads(evidence, sets)
    empty = next(p for t, p in sorted(recorded.items()) if p is not None and not split_units.payload_bars(p))

    night1 = dict(recorded)
    reconstruction = {}
    for t in LATE:
        night1[t] = as_at_sealing(recorded[t])
        s = max((x for x in sets if x["ticker"] == t), key=lambda x: x["signal_session"])
        before = [px for day, px in split_units.payload_bars(night1[t]) if day < s["signal_session"] and px]
        reconstruction[t] = {
            "previous_close_sealed_by_the_scan": s["signal"]["previous"],
            "previous_close_reconstructed": round(before[-1], 4),
            "equal_within_1_percent": abs(before[-1] / s["signal"]["previous"] - 1) <= 0.01,
        }
    night3 = dict(recorded)
    night3["GOVX"] = without_bars(empty, "GOVX")
    pulls = {"night_1": night1, "night_2": recorded, "night_3": night3, "night_4": recorded}

    v11 = paper.ledger_lines(split_flags.FLAGS_LEDGER)
    cutoffs = SA.entry_cutoffs(specs)
    report = {"reconstruction_check": reconstruction, "nights": {}}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ledger = tmp / "split_assessments.jsonl"
        with mock.patch.object(SA, "LEDGER", ledger):
            for label, stamp, what in NIGHTS:
                m = manifest(tmp / label, f"yahoo_us_recent-{label}", pulls[label])
                with (
                    mock.patch.object(provenance, "latest_manifest", lambda prefix, suffix=".jsonl", m=m: m),
                    mock.patch.object(SA, "utc_stamp", lambda stamp=stamp: stamp),
                ):
                    before = len(paper.ledger_lines(ledger))
                    files = cli._split_assess_hook(None)
                    records = paper.ledger_lines(ledger)
                    new = [r for r in records[before:] if r.get("type") == SA.RECORD_TYPE]
                    again = len(paper.ledger_lines(ledger))
                    cli._split_assess_hook(None)
                    repeated = len(paper.ledger_lines(ledger)) - again
                standing = SA.standing(records)
                tally = {}
                for r in new:
                    tally[r["assessment"]] = tally.get(r["assessment"], 0) + 1
                report["nights"][label] = {
                    "run_at": stamp,
                    "pull": what,
                    "records_appended": len(new),
                    "appended_by_assessment": dict(sorted(tally.items())),
                    "marked_as_the_scans_own_pull": sum(1 for r in new if r["pull_role"] == "seal"),
                    "reassessments": [
                        {
                            "set": name(r["set_id"]),
                            "assessment": r["assessment"],
                            "split": r["split"],
                            "split_adjusted_ret1": r["split_adjusted_ret1"],
                            "names_the_record_it_supersedes": bool(r["supersedes"]),
                        }
                        for r in new
                        if r["supersedes"]
                    ],
                    "named_sets_standing": {
                        name(sid): {
                            "assessment": r["assessment"],
                            "previous_session": r["previous_session"],
                            "units": r["units"],
                            "assessed_at": r["assessed_at"],
                        }
                        for sid, r in sorted(standing.items())
                        if r["ticker"] in NAMED and r["signal_session"] >= "2026-11-10"
                    },
                    "validator_problems": SA.verify(records, specs),
                    "removed_corrected": sorted(name(s) for s in SA.removed_set_ids("corrected", records, v11, cutoffs)),
                    "removed_at_the_time": sorted(name(s) for s in SA.removed_set_ids("at_the_time", records, v11, cutoffs)),
                    "unresolved": sorted(name(s) for s in SA.unresolved_set_ids(records)),
                    "records_added_by_running_the_same_night_twice": repeated,
                    "hook_returned_the_ledger_for_commit": bool(files),
                }
    OUT.mkdir(exist_ok=True)
    (OUT / "simulation.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    md = [
        "# SPLIT_REVISIONS_v1: four simulated nights through the nightly hook",
        "",
        "The scheduled job cannot run from a working branch. Here the function the job calls is run four times on a "
        "temporary ledger, against pulls built from the provider responses recorded on 2026-11-12. Night 1 is a "
        "reconstruction, not a recorded pull: for GOVX and SLXN the split event is removed and the earlier closes are "
        "divided by 24, which is the state the scan saw on 2026-11-11.",
        "",
        "Check of the reconstruction against the sealed records:",
        "",
        "| Ticker | Previous close sealed by the scan | Previous close in the reconstructed pull | Equal within 1% |",
        "|---|---:|---:|---|",
    ]
    md += [
        f"| {t} | {v['previous_close_sealed_by_the_scan']} | {v['previous_close_reconstructed']} | "
        f"{'yes' if v['equal_within_1_percent'] else 'NO'} |"
        for t, v in reconstruction.items()
    ]
    md += [
        "",
        "| Night | Pull | Records appended | Reassessments | Same night run twice adds | Validator problems | "
        "Left out, corrected | Left out, known at the time | Unresolved |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for label, _, _ in NIGHTS:
        n = report["nights"][label]
        re = "; ".join(f"{r['set']} to {r['assessment']}" for r in n["reassessments"]) or "none"
        md.append(
            f"| {n['run_at'][:10]} | {n['pull']} | {n['records_appended']} | {re} | "
            f"{n['records_added_by_running_the_same_night_twice']} | {len(n['validator_problems'])} | "
            f"{len(n['removed_corrected'])} | {len(n['removed_at_the_time'])} | {len(n['unresolved'])} |"
        )
    md += ["", "Standing assessment of the named sets after each night:", "", "| Night | Set | Assessment | Previous bar | Units |", "|---|---|---|---|---|"]
    for label, _, _ in NIGHTS:
        n = report["nights"][label]
        for s, r in n["named_sets_standing"].items():
            md.append(f"| {n['run_at'][:10]} | {s} | {r['assessment']} | {r['previous_session'] or '-'} | {r['units']} |")
    last = report["nights"]["night_4"]
    md += [
        "",
        f"Left out of the corrected view after night 4: {', '.join(last['removed_corrected'])}.",
        "",
        f"Left out of the view as known at the time after night 4: {', '.join(last['removed_at_the_time']) or 'none'}.",
        "",
        f"Unresolved after night 4: {', '.join(last['unresolved'])}.",
        "",
    ]
    (OUT / "SIMULATION.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
