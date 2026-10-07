"""Calibration. Prospective closed cases only. Retrospective never validates a detector.

Every detector is scored on both sides: the hit rate when it fired, the hit rate when it
was evaluated and did not fire, and the base rate over both. Lift is the signal hit rate
divided by the base rate. A detector with no no-signal cases has no base rate and no lift.
"""

from __future__ import annotations

import json
from collections import defaultdict

from .detectors import HIT_LABEL
from .hashing import parse_ts
from .ledger import CARD_HASH_VERSION, HORIZONS, Ledger

PROMOTION_MIN = 30
UNSCORED = {"UNKNOWN", "CENSORED"}


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

    grades = {r["evidence_id"]: r["grade"] for r in ledger.rows("SELECT evidence_id, grade FROM evidence")}
    sets = defaultdict(dict)
    for row in ledger.rows("SELECT case_id, horizon, payload_json FROM information_sets"):
        sets[row["case_id"]][row["horizon"]] = json.loads(row["payload_json"])

    buckets = {"PROSPECTIVE": [], "RETROSPECTIVE": [], "SIMULATED": []}
    for case in cases:
        case["outcome"] = outcomes.get(case["case_id"])
        case["evaluations"] = by_case.get(case["case_id"], [])
        case["evidence"] = _evidence_coverage(sets[case["case_id"]], grades)
        buckets[case["call_type"]].append(case)

    closed = [
        c for c in buckets["PROSPECTIVE"]
        if c["outcome"] and c["outcome"]["outcome_label"] not in UNSCORED
    ]
    # Only cards whose detector evaluations were frozen into the hash at open can be scored.
    prospective_closed = [c for c in closed if c.get("card_hash_version") == CARD_HASH_VERSION]
    observations = [
        (ev["detector"], ev["status"], case["outcome"]["outcome_label"], HIT_LABEL.get(ev["detector"], "REPRICED_UP"))
        for case in prospective_closed
        for ev in case["evaluations"]
    ]
    detector_table = [
        {**row, "status": "UNVALIDATED", "promotable": False}
        for row in lift_table(observations)
    ]
    scan_log = _scan_log(ledger, cases)
    return {
        "doctrine_sha": ledger.doctrine_sha,
        "calibration_status": "NOT_STARTED" if len(prospective_closed) < PROMOTION_MIN else "SAMPLE_ONLY",
        "promotion_min_closed_prospective": PROMOTION_MIN,
        "counts": {
            "cases": len(cases),
            "prospective_open": sum(1 for c in buckets["PROSPECTIVE"] if not c["outcome"]),
            "prospective_closed": len(prospective_closed),
            "prospective_closed_unfrozen_excluded": len(closed) - len(prospective_closed),
            "retrospective": len(buckets["RETROSPECTIVE"]),
            "simulated_excluded": len(buckets["SIMULATED"]),
            **scan_log["counts"],
        },
        "detector_table": detector_table,
        "scan_log": scan_log,
        "cases": buckets,
        "entry_permission": False,
    }


def _evidence_coverage(sets: dict, grades: dict) -> dict:
    known = cited = 0
    cited_grades = []
    for horizon in HORIZONS:
        payload = sets.get(horizon) or {}
        evidence = payload.get("evidence") or {}
        for fact, value in (payload.get("facts") or {}).items():
            if value is None:
                continue
            known += 1
            ids = evidence.get(fact) or []
            if ids:
                cited += 1
                cited_grades += [grades.get(i, "?") for i in ids]
    return {"known_facts": known, "cited_facts": cited, "weakest_grade": max(cited_grades) if cited_grades else None}


def lift_table(observations) -> list[dict]:
    """observations: (name, status, outcome_label, hit_label). Returns one row per name."""
    stats = defaultdict(lambda: {"signal": [0, 0], "no_signal": [0, 0], "insufficient": 0, "unscored": 0, "hit_label": None})
    for name, status, outcome_label, hit_label in observations:
        slot = stats[name]
        slot["hit_label"] = hit_label
        if status in {"INSUFFICIENT_DATA", "UNAVAILABLE"}:
            slot["insufficient"] += 1
            continue
        if outcome_label in UNSCORED:
            slot["unscored"] += 1
            continue
        side = slot["signal"] if status == "SIGNAL" else slot["no_signal"]
        side[0] += 1
        side[1] += int(outcome_label == hit_label)
    rows = []
    for name, slot in sorted(stats.items()):
        sig_n, sig_hits = slot["signal"]
        no_n, no_hits = slot["no_signal"]
        base_n = sig_n + no_n
        base_rate = (sig_hits + no_hits) / base_n if base_n else None
        sig_rate = sig_hits / sig_n if sig_n else None
        no_rate = no_hits / no_n if no_n else None
        lift = None
        if sig_rate is not None and no_n and base_rate:
            lift = sig_rate / base_rate
        rows.append({
            "detector": name,
            "hit_label": slot["hit_label"],
            "evaluated": base_n,
            "signals": sig_n,
            "signal_hits": sig_hits,
            "signal_hit_rate": sig_rate,
            "no_signal": no_n,
            "no_signal_hits": no_hits,
            "no_signal_hit_rate": no_rate,
            "base_rate": base_rate,
            "lift": lift,
            "insufficient_data": slot["insufficient"],
            "unscored_outcomes": slot["unscored"],
        })
    return rows


def _scan_log(ledger: Ledger, cases: list[dict]) -> dict:
    now = ledger.now()
    opened = {c["scan_entry_id"] for c in cases if c.get("scan_entry_id")}
    runs = [dict(r) for r in ledger.rows("SELECT * FROM scan_runs ORDER BY scanned_at, scan_id")]
    entries = [dict(r) for r in ledger.rows("SELECT * FROM scan_entries")]
    outcomes = {r["entry_id"]: dict(r) for r in ledger.rows("SELECT * FROM scan_outcomes")}
    evals = defaultdict(list)
    for ev in ledger.rows("SELECT * FROM scan_evaluations"):
        evals[ev["entry_id"]].append(dict(ev))
    by_scan = defaultdict(list)
    for entry in entries:
        by_scan[entry["scan_id"]].append(entry)

    summaries, observations = [], []
    totals = defaultdict(int)
    for run in runs:
        rows = by_scan[run["scan_id"]]
        window_over = now >= parse_ts(run["outcome_window_end"])
        flagged = [e for e in rows if e["flagged"]]
        closed = [e for e in rows if e["entry_id"] in outcomes]
        summary = {
            "scan_id": run["scan_id"],
            "scanner": run["scanner"],
            "scanned_at": run["scanned_at"],
            "outcome_window_end": run["outcome_window_end"],
            "hit_label": run["hit_label"],
            "entries": len(rows),
            "flagged": len(flagged),
            "flagged_opened": sum(1 for e in flagged if e["entry_id"] in opened),
            "flagged_not_opened": sum(1 for e in flagged if e["entry_id"] not in opened),
            "closed": len(closed),
            "overdue_unclosed": (len(rows) - len(closed)) if window_over else 0,
        }
        summaries.append(summary)
        for key in ("entries", "flagged", "flagged_opened", "flagged_not_opened", "closed", "overdue_unclosed"):
            totals[key] += summary[key]
        for entry in closed:
            label = outcomes[entry["entry_id"]]["outcome_label"]
            observations.append((
                f"FLAG:{run['scanner']}",
                "SIGNAL" if entry["flagged"] else "NO_SIGNAL",
                label,
                run["hit_label"],
            ))
            for ev in evals[entry["entry_id"]]:
                observations.append((ev["detector"], ev["status"], label, HIT_LABEL.get(ev["detector"], "REPRICED_UP")))
    return {
        "counts": {f"scan_{k}": totals[k] for k in (
            "entries", "flagged", "flagged_opened", "flagged_not_opened", "closed", "overdue_unclosed"
        )},
        "scans": summaries,
        "lift": lift_table(observations),
    }


def _pct(x) -> str:
    return "—" if x is None else f"{100 * x:.1f}%"


def _lift(x) -> str:
    return "—" if x is None else f"{x:.2f}×"


def _lift_lines(rows: list[dict], with_status: bool) -> list[str]:
    header = "| Detector | Hit = | Signal n | Signal hit rate | No-signal n | No-signal hit rate | Base rate | Lift | Insufficient |"
    rule = "|---|---|---:|---:|---:|---:|---:|---:|---:|"
    if with_status:
        header += " Status |"
        rule += "---|"
    lines = [header, rule]
    if not rows:
        lines.append("| — | — | 0 | — | 0 | — | — | — | 0 |" + (" UNVALIDATED |" if with_status else ""))
    for row in rows:
        line = (
            f"| {row['detector']} | {row['hit_label']} | {row['signals']} | {_pct(row['signal_hit_rate'])} | "
            f"{row['no_signal']} | {_pct(row['no_signal_hit_rate'])} | {_pct(row['base_rate'])} | "
            f"{_lift(row['lift'])} | {row['insufficient_data']} |"
        )
        if with_status:
            line += f" {row['status']} |"
        lines.append(line)
    return lines


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
        f"- Prospective closed but unscored (evaluations not frozen at open): {c['prospective_closed_unfrozen_excluded']}",
        f"- Retrospective (hypothesis only): {c['retrospective']}",
        f"- Simulated (excluded): {c['simulated_excluded']}",
        f"- Scanned names logged: {c['scan_entries']} "
        f"(flagged {c['scan_flagged']}: opened {c['scan_flagged_opened']}, not opened {c['scan_flagged_not_opened']})",
        f"- Scanned names closed: {c['scan_closed']}; past window and still unclosed: {c['scan_overdue_unclosed']}",
        "",
        "## Detector table (prospective closed only)",
        "",
        "Hit rate when the detector fired, when it was evaluated and did not fire, and the base",
        "rate over both. Lift = signal hit rate / base rate. No no-signal cases means no lift.",
        "",
        *_lift_lines(report["detector_table"], with_status=True),
        "",
        "## Scan log (every scanned name, flagged or not, opened or not)",
        "",
    ]
    scans = report["scan_log"]["scans"]
    if not scans:
        lines.append("No scans logged.")
    else:
        lines.extend([
            "| Scan | Scanner | Entries | Flagged | Flagged opened | Flagged not opened | Closed | Overdue unclosed |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ])
        for s in scans:
            lines.append(
                f"| `{s['scan_id']}` | {s['scanner']} | {s['entries']} | {s['flagged']} | {s['flagged_opened']} | "
                f"{s['flagged_not_opened']} | {s['closed']} | {s['overdue_unclosed']} |"
            )
        lines.extend(["", "Lift over the scan base rate (closed scan entries):", ""])
        lines.extend(_lift_lines(report["scan_log"]["lift"], with_status=False))
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
            ev = case["evidence"]
            lines.append(
                f"  - Evidence: {ev['cited_facts']} of {ev['known_facts']} known facts cite archived evidence"
                + (f"; weakest grade {ev['weakest_grade']}" if ev["weakest_grade"] else "")
            )
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
        "scan_log": report["scan_log"],
    }
    return json.dumps(slim, indent=2)
