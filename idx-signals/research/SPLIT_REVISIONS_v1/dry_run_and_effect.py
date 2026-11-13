"""SPLIT_REVISIONS_v1: the dry run of the assessments, and the effect table of PROTOCOL.md. Run once.

Usage (from idx-signals/):
  python3 research/SPLIT_REVISIONS_v1/dry_run_and_effect.py EVIDENCE_DIR [KODCHECK_RESULT_JSON]

EVIDENCE_DIR holds the provider responses recorded on 2026-11-12 by the KODCHECK audit, outside the repository:
`set_<set_id>.json` (the raw chart response for each sealed US set, bars up to its signal session) and
`events_<TICKER>.json` (the split events the provider listed for the ticker that day). Nothing in EVIDENCE_DIR is
copied into the repository; the results keep each response's SHA-256.

The script writes no live ledger. It seals the proposed records into a temporary ledger so that hashes, validation and
the report can be exercised exactly as they will run after the merge.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from idxsig import learner2 as L2  # noqa: E402
from idxsig import learner3 as L3  # noqa: E402
from idxsig import paper, paper_book as book, paper_book_report, speculation  # noqa: E402
from idxsig import split_assessments as SA  # noqa: E402
from idxsig import split_flags, split_units  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
PULL_DAY = "2026-11-12"
SMX_FILING = "https://www.sec.gov/Archives/edgar/data/0001940674/000149315226049929/ex99-1.htm"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_payloads(evidence: Path, sets: list[dict]) -> tuple[dict, dict]:
    """One payload per ticker: the recorded response of its latest set, with the ticker's later split events merged in
    (a nightly pull lists them too). Returns (payloads, provenance)."""
    latest = {}
    for s in sets:
        if s["ticker"] not in latest or s["signal_session"] > latest[s["ticker"]]["signal_session"]:
            latest[s["ticker"]] = s
    payloads, prov = {}, {}
    for ticker, s in sorted(latest.items()):
        raw = evidence / f"set_{s['set_id']}.json"
        if not raw.exists():
            payloads[ticker] = None
            prov[ticker] = {"response": None}
            continue
        payload = json.loads(raw.read_text(encoding="utf-8"))
        prov[ticker] = {"response_of_set": s["set_id"], "response_sha256": sha(raw), "later_events_merged": 0}
        ev_file = evidence / f"events_{ticker}.json"
        try:
            result = payload["chart"]["result"][0]
        except (KeyError, IndexError, TypeError):
            payloads[ticker] = payload
            continue
        if ev_file.exists():
            listed = json.loads(ev_file.read_text(encoding="utf-8")).get("splits") or []
            prov[ticker]["events_sha256"] = sha(ev_file)
            have = {(e["effective_session"], e["numerator"], e["denominator"]) for e in split_flags.provider_splits(payload)}
            splits = (result.setdefault("events", {}) or {}).setdefault("splits", {})
            for e in listed:
                key = (e["effective_session"], e["numerator"], e["denominator"])
                if key in have:
                    continue
                unix = int(datetime.fromisoformat(e["effective_session"] + "T14:30:00+00:00").timestamp())
                splits[str(unix)] = {
                    "date": unix,
                    "numerator": e["numerator"],
                    "denominator": e["denominator"],
                    "splitRatio": e.get("provider_ratio") or f"{e['numerator']:g}:{e['denominator']:g}",
                }
                prov[ticker]["later_events_merged"] += 1
        payloads[ticker] = payload
    return payloads, prov


def us_block(text: str) -> list[str]:
    lines, keep, out = text.splitlines(), False, []
    for line in lines:
        if line.startswith("## US"):
            keep = True
        elif line.startswith("## ") and keep:
            break
        if keep and (line.startswith("|") or line.startswith("## US") or line.startswith("PATH20")):
            out.append(line)
    return out


def learner3_table(pairs: list[dict]) -> dict:
    proto, _ = L3.protocol()
    c = L3.claim(pairs, proto["claim"])
    import numpy as np

    per = {}
    for stmt in L3.STATEMENTS:
        sp = [p for p in pairs if p["statement"] == stmt]
        y = np.array([p["y"] for p in sp])
        per[stmt] = {
            "n": len(sp),
            "rate": float(y.mean()) if len(sp) else None,
            "auc": L3._auc(np.array([p["raw"] for p in sp]), y) if len(sp) else None,
            "auc_bench": L3._auc(np.array([p["bench"] for p in sp]), y) if len(sp) else None,
        }
    return {"headline": {"statement": L3.HEADLINE, "n_pairs": c["n_pairs"], "auc": c["auc"], "auc_bench": c["auc_bench"]}, "statements": per}


def learner2_table(pairs: list[dict]) -> dict:
    per = {}
    for stmt in sorted({(p["family"], p["statement"]) for p in pairs if p["family"] == "SPEC_US"}):
        ps = [p for p in pairs if (p["family"], p["statement"]) == stmt]
        w = sum(p["w"] for p in ps)
        per[":".join(stmt)] = {
            "n": round(w, 3),
            "rate": sum(p["w"] * p["y"] for p in ps) / w,
            **{f"brier_{k}": sum(p["w"] * (p[k] - p["y"]) ** 2 for p in ps) / w for k in ("anchor", "raw", "published")},
        }
    return per


def main() -> int:
    evidence = Path(sys.argv[1])
    kodcheck = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    OUT.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    specs = speculation.spec_lines()
    sets = [s for s in specs if SA._is_set(s)]
    v11 = paper.ledger_lines(split_flags.FLAGS_LEDGER)
    tags = {r["set_id"]: r for r in v11 if r.get("type") == split_flags.RECORD_TYPE}
    cutoffs = SA.entry_cutoffs(specs)
    payloads, prov = build_payloads(evidence, sets)
    parsed = {t: len(split_units.payload_bars(p)) for t, p in payloads.items() if p is not None}

    smx = next((s["set_id"] for s in sets if s["ticker"] == "SMX" and s["signal_session"] == "2026-11-10"), None)
    basis = f"provider responses recorded {PULL_DAY} (KODCHECK audit); dry run of SPLIT_REVISIONS_v1"
    proposed = SA.propose_assessments(specs, [], payloads, basis, stamp, retrieved_on=PULL_DAY)
    for r in proposed:
        r["sources"] = [SMX_FILING] if r["set_id"] == smx else []

    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "split_assessments.jsonl"
        sealed = paper.append(proposed, path=ledger)
        records = paper.ledger_lines(ledger)
        problems = SA.verify(records, specs)
        # a second pass over the same pull must change nothing
        again = SA.propose_reassessments(specs, records, payloads, basis, stamp, retrieved_on=PULL_DAY)
        removed_now = SA.removed_set_ids("corrected", records, v11, cutoffs)
        removed_then = SA.removed_set_ids("at_the_time", records, v11, cutoffs)
        unresolved = SA.unresolved_set_ids(records)
        with mock.patch.object(SA, "LEDGER", ledger):
            section = paper_book_report.secondary_view(book.trades())

    by_id = {s["set_id"]: s for s in sets}
    name = lambda sid: f"{by_id[sid]['ticker']} {by_id[sid]['signal_session']}"  # noqa: E731
    tally = {}
    for r in sealed:
        tally[r["assessment"]] = tally.get(r["assessment"], 0) + 1
    cross = None
    if kodcheck and kodcheck.exists():
        derived = {d["id"]: d.get("ca_class") for d in json.loads(kodcheck.read_text())["derived"]}
        diff = [(name(r["set_id"]), derived.get(r["set_id"]), r["assessment"]) for r in sealed if derived.get(r["set_id"]) != r["assessment"]]
        cross = {"compared": len(sealed), "same_class": len(sealed) - len(diff), "different": diff}

    rows = []
    for r in sealed:
        tag = tags.get(r["set_id"], {})
        if r["group"] != "REAL" or tag.get("flag") in ("ARTIFACT_V11", "INDETERMINATE"):
            rows.append(
                {
                    "set": name(r["set_id"]),
                    "recorded_ret1": r["recorded_ret1"],
                    "tag_at_the_time": tag.get("flag"),
                    "tag_recorded": tag.get("assessed_at"),
                    "entry_cutoff": cutoffs.get(r["set_id"]),
                    "assessment": r["assessment"],
                    "group": r["group"],
                    "split": r["split"],
                    "split_adjusted_ret1": r["split_adjusted_ret1"],
                    "previous_session": r["previous_session"],
                    "previous_session_source": r["previous_session_source"],
                    "units": r["units"],
                    "sources": r["sources"],
                }
            )
    dry = {
        "generated_at": stamp,
        "repository_commit": "134f58f9a0b335400c5fd24843767d6b862cfdb0",
        "sets": len(sets),
        "responses_parsed": {"tickers": len(parsed), "with_bars": sum(1 for n in parsed.values() if n > 0)},
        "records_proposed": len(sealed),
        "by_assessment": dict(sorted(tally.items())),
        "validator_problems": problems,
        "second_pass_changes": len(again),
        "removed_corrected": sorted(name(s) for s in removed_now),
        "removed_at_the_time": sorted(name(s) for s in removed_then),
        "unresolved": sorted(name(s) for s in unresolved),
        "cross_check_with_kodcheck_run": cross,
        "affected_sets": rows,
        "provenance": prov,
    }
    (OUT / "dry_run.json").write_text(json.dumps(dry, indent=1), encoding="utf-8")
    (OUT / "dry_run_records.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sealed), encoding="utf-8")
    (OUT / "PAPER_BOOK_secondary_view.md").write_text(section.lstrip("\n"), encoding="utf-8")

    # ---------------------------------------------------------------- effect table
    asof = stamp
    removed = removed_now
    ledger_lines = paper.ledger_lines()
    kept_specs = [r for r in specs if r.get("set_id") not in removed]
    reg_all = us_block(speculation.render(speculation.statistics(specs, ledger_lines), specs))
    reg_cor = us_block(speculation.render(speculation.statistics(kept_specs, ledger_lines), kept_specs))

    recs, l3, l2 = L2.all_records(), L3.lines(), L2.lines()
    p3 = L3.forward_pairs(recs, l3, asof)
    p2 = L2.forward_pairs(recs, l2, asof)
    effect = {
        "generated_at": stamp,
        "sets_left_out": sorted(name(s) for s in removed),
        "unresolved_kept_in_both": sorted(name(s) for s in unresolved),
        "speculation_register_US": {"as_published": reg_all, "corrected": reg_cor},
        "learner_v2_4": {
            "as_published": learner3_table(p3),
            "corrected": learner3_table([p for p in p3 if p["set_id"] not in removed]),
            "pairs_on_left_out_sets": sum(1 for p in p3 if p["set_id"] in removed),
        },
        "learner_v2_2_SPEC_US": {
            "as_published": learner2_table(p2),
            "corrected": learner2_table([p for p in p2 if p["set_id"] not in removed]),
            "pairs_on_left_out_sets": sum(1 for p in p2 if p["family"] == "SPEC_US" and p["set_id"] in removed),
        },
    }
    (OUT / "effect.json").write_text(json.dumps(effect, indent=1), encoding="utf-8")
    print(json.dumps({k: dry[k] for k in ("sets", "responses_parsed", "records_proposed", "by_assessment", "validator_problems", "second_pass_changes", "removed_corrected", "removed_at_the_time", "unresolved")}, indent=1))
    print("cross-check:", None if cross is None else {k: cross[k] for k in ("compared", "same_class")}, (cross or {}).get("different"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
