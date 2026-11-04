"""REPLAY_UNITS_v2: write protocol_A.json and protocol_B.json (the replays' freeze) and the PENDING trial, once, after
build.py (features only, as-traded) and before replay.py reads any outcome.

    python3 freeze.py
    python3 replay.py protocol_A.json results_A     # one run each
    python3 replay.py protocol_B.json results_B
    python3 short.py                                # once, on results_B, FRESH_SHORT_v1's rules unchanged

Supersedes RECENT_REPLAY_v1 (period A) and FRESH_SHORT_v1 (period B), whose features used split-adjusted prices for
log_price and log_turnover (their CORRECTION_1.md). Statistic and bars unchanged: v2.4's registered claim for the
replays, short_rules.json for the short.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import learner3  # noqa: E402
from idxsig.provenance import MANIFESTS, sha256_file, utc_stamp  # noqa: E402

HERE = Path(__file__).resolve().parent
STUDY = "REPLAY_UNITS_v2"
PINS = ("idxsig/learner3.py", "idxsig/learner2.py", "idxsig/speculation.py", "idxsig/paper.py",
        "idxsig/rules/moonshot_g.py", "idxsig/global_panel.py", "idxsig/execution.py", "idxsig/call_cert.py",
        "idxsig/risk_control.py", "research/TA_HISTORY_v1/run.py",
        f"research/{STUDY}/build.py", f"research/{STUDY}/replay.py", f"research/{STUDY}/short.py")
TRIAL = ROOT / "research" / "QUANT_GRADE" / "trials" / f"{STUDY}_registered.json"
PERIODS = {"A": ["2026-04-01", "2026-10-28"], "B": ["2025-11-03", "2026-03-31"]}


def main() -> int:
    if any((HERE / f"protocol_{k}.json").exists() for k in PERIODS) or TRIAL.exists():
        sys.exit("error: the freeze happens once")
    proto24, sha24 = learner3.protocol()
    written = {}
    for k, (start, end) in PERIODS.items():
        if (HERE / f"results_{k}").exists():
            sys.exit(f"error: results_{k} exists before the freeze")
        build = json.loads((HERE / "data" / f"events_{k}_BUILD.json").read_text(encoding="utf-8"))
        if build["range"] != [start, end] or not str(build.get("units", "")).startswith("as_traded"):
            sys.exit(f"error: events_{k} is not the as-traded build of {start}..{end}")
        events = f"research/{STUDY}/data/events_{k}.csv.gz"
        n = sum(v["built"] for s, v in build["per_session"].items() if start <= s <= end)
        proto = {
            "study_id": f"{STUDY}_{k}", "frozen_at": utc_stamp(), "supersedes":
                {"A": "research/RECENT_REPLAY_v1 (CORRECTION_1.md)", "B": "research/FRESH_SHORT_v1 (CORRECTION_1.md)"}[k],
            "range": [start, end], "events_in_range_before_outcomes": n, "events": events, "manifest": build["manifest"],
            "units": build["units"], "events_with_later_split": build.get("events_with_later_split"),
            "learner": {"version": learner3.VERSION, "protocol": "research/LEARNER_v2/protocol_v2_4.json",
                        "protocol_sha256": sha24, "warm_start_sha256": learner3.HISTORY_SHA256, "claim": proto24["claim"]},
            "statistic": "protocol_v2_4.json 'claim' verbatim; for B also the paper short of short_rules.json (unchanged)",
            "sealed_data": "US 2024 onward is sealed; A was read once (RECENT_REPLAY_v1) and B once (FRESH_SHORT_v1's "
                           "replay, no short) with the defective features; this is the corrected read, run once",
            "known_mismatch": "VALIDATION.json: CAPS and OBAI remain unresolved against the daily pulls",
            "data_pins": {events: sha256_file(ROOT / events),
                          f"research/{STUDY}/data/events_{k}_BUILD.json": sha256_file(HERE / "data" / f"events_{k}_BUILD.json"),
                          f"data/manifests/{build['manifest']}": sha256_file(MANIFESTS / build["manifest"]),
                          f"research/{STUDY}/short_rules.json": sha256_file(HERE / "short_rules.json"),
                          "research/LEARNER_v2/warmstart_v4/events_us.csv.gz": learner3.HISTORY_SHA256},
            "code_pins": {p: sha256_file(ROOT / p) for p in PINS},
        }
        (HERE / f"protocol_{k}.json").write_text(json.dumps(proto, indent=1) + "\n")
        written[k] = n
    TRIAL.write_text(json.dumps({
        "id": f"{STUDY}_registered", "experiment": STUDY, "date": utc_stamp()[:10],
        "hypothesis": "corrected (as-traded) replays of LEARNER v2.4: its registered AUC claim on A (2026-04..10, "
                      f"{written['A']} events) and B (2025-11..2026-03, {written['B']} events); on B, the redesigned paper "
                      "short of the certified calls (short_rules.json) is profitable after TYPICAL costs",
        "one_sided_p": None, "p_source": f"research/{STUDY}/protocol_A.json, protocol_B.json", "variants_searched": 0,
        "outcome": "PENDING (frozen before the corrected replays read any outcome)", "counted": False,
        "registered": utc_stamp()[:10], "supersedes": ["RECENT_REPLAY_v1_result", "FRESH_SHORT_v1_registered"],
    }, indent=1) + "\n")
    print(json.dumps(written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
