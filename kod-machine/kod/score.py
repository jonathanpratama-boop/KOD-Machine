"""Calibration. Prospective closed cases only. Retrospective never validates a detector."""

from __future__ import annotations

import json
from collections import defaultdict

from .ledger import Ledger

PROMOTION_MIN = 30


def build_report(ledger: Ledger) -> dict:
    cases = [dict(r) for r in ledger.rows("SELECT * FROM cases ORDER BY opened_at, case_id")]
    outcomes = {
        r["case_id"]: dict(r)
        for r in ledger.rows("SELECT * FROM outcomes")
    }
    evals = [dict(r) for r in ledger.rows("SELECT * FROM detector_evaluations")]
    by_case = defaultdict(list)
    for ev in evals:
        by_case[ev["case_id"]].append(ev)

    buckets = {"PROSPECTIVE": [], "RETROSPECTIVE": [], "SIMULATED": []}
    for case in cases:
        case["outcome"] = outcomes.get(case["case_id"])
        case["evaluations"] = by_case.get(case["case_id"], [])
        buckets[case["call_type"]].append(case)

    prospective_closed = [
        c for c in buckets["PROSPECTIVE"]
        if c["outcome"] and c["outcome"]["outcome_label"] not in {"UNKNOWN", "CENSORED"}
    ]
    detector_table = _detector_table(prospective_closed)
    return {
        "doctrine_sha": ledger.doctrine_sha,
        "calibration_status": "NOT_STARTED" if len(prospective_closed) < PROMOTION_MIN else "SAMPLE_ONLY",
        "promotion_min_closed_prospective": PROMOTION_MIN,
        "counts": {
            "cases": len(cases),
            "prospective_open": sum(1 for c in buckets["PROSPECTIVE"] if not c["outcome"]),
            "prospective_closed": len(prospective_closed),
            "retrospective": len(buckets["RETROSPECTIVE"]),
            "simulated_excluded": len(buckets["SIMULATED"]),
        },
        "detector_table": detector_table,
        "cases": buckets,
        "entry_permission": False,
    }


def _detector_table(closed: list[dict]) -> list[dict]:
    stats = defaultdict(lambda: {"evaluated": 0, "signal": 0, "signal_and_up": 0, "insufficient": 0})
    for case in closed:
        up = case["outcome"]["outcome_label"] == "REPRICED_UP"
        for ev in case["evaluations"]:
            slot = stats[ev["detector"]]
            if ev["status"] == "INSUFFICIENT_DATA":
                slot["insufficient"] += 1
                continue
            if ev["status"] not in {"SIGNAL", "NO_SIGNAL"}:
                continue
            slot["evaluated"] += 1
            if ev["status"] == "SIGNAL":
                slot["signal"] += 1
                if up:
                    slot["signal_and_up"] += 1
    rows = []
    for name, slot in sorted(stats.items()):
        rows.append({
            "detector": name,
            "evaluated": slot["evaluated"],
            "signals": slot["signal"],
            "signal_then_repriced_up": slot["signal_and_up"],
            "insufficient_data": slot["insufficient"],
            "status": "UNVALIDATED",
            "promotable": False,
        })
    return rows


def render_markdown(report: dict) -> str:
    c = report["counts"]
    lines = [
        "# KOD lab status",
        "",
        f"Doctrine SHA-256: `{report['doctrine_sha']}`",
        f"Calibration: **{report['calibration_status']}**",
        "Entry permission: false",
        "",
        "Prospective closed cases are the only rows that can validate a detector.",
        f"Promotion floor: {report['promotion_min_closed_prospective']} closed prospective cases with complete coverage.",
        "",
        "## Counts",
        "",
        f"- Cases: {c['cases']}",
        f"- Prospective open: {c['prospective_open']}",
        f"- Prospective closed (scored): {c['prospective_closed']}",
        f"- Retrospective (hypothesis only): {c['retrospective']}",
        f"- Simulated (excluded): {c['simulated_excluded']}",
        "",
        "## Detector table (prospective closed only)",
        "",
        "| Detector | Evaluated | Signals | Signal then repriced up | Insufficient | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    if not report["detector_table"]:
        lines.append("| — | 0 | 0 | 0 | 0 | UNVALIDATED |")
    for row in report["detector_table"]:
        lines.append(
            f"| {row['detector']} | {row['evaluated']} | {row['signals']} | "
            f"{row['signal_then_repriced_up']} | {row['insufficient_data']} | {row['status']} |"
        )
    lines.extend(["", "## Case cards", ""])
    for kind in ("PROSPECTIVE", "RETROSPECTIVE", "SIMULATED"):
        lines.append(f"### {kind}")
        lines.append("")
        group = report["cases"][kind]
        if not group:
            lines.append("None.")
            lines.append("")
            continue
        for case in group:
            outcome = case["outcome"]["outcome_label"] if case["outcome"] else "OPEN"
            ret = ""
            if case["outcome"] and case["outcome"]["window_return_pct"] is not None:
                ret = f", window {case['outcome']['window_return_pct']:+.1f}%"
            lines.append(
                f"- `{case['case_id']}` {case['symbol']} {case['disposition']} → {outcome}{ret} "
                f"[{case['reconstruction_status']}]"
            )
            lines.append(f"  - Hypothesis: {case['story_hypothesis']}")
            fired = [e["detector"] for e in case["evaluations"] if e["status"] == "SIGNAL"]
            if fired:
                lines.append(f"  - Signals: {', '.join(fired)}")
        lines.append("")
    lines.extend([
        "## What this report is not",
        "",
        "A retrospective winner is not evidence that a detector works. Coverage on the seed",
        "cases is PARTIAL_PUBLIC, not a complete archive. No name here is a recommendation.",
        "",
    ])
    return "\n".join(lines)


def render_json(report: dict) -> str:
    slim = {
        "doctrine_sha": report["doctrine_sha"],
        "calibration_status": report["calibration_status"],
        "entry_permission": False,
        "counts": report["counts"],
        "detector_table": report["detector_table"],
    }
    return json.dumps(slim, indent=2)
