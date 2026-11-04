"""FRESH_SHORT_v1: write protocol.json (the replay's freeze) and the PENDING trial registration, once, after build.py
(features only) and before replay.py reads any outcome.

    python3 freeze.py

The period 2025-11-03..2026-03-31 lies inside the 400-day pull and before RECENT_REPLAY_v1's range; no KOD study has
read its outcomes. The replay's statistic is v2.4's registered claim verbatim (an independent read of
RECENT_REPLAY_v1's result); the study's primary bar is the paper short's (short_rules.json, frozen first).
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
STUDY = "FRESH_SHORT_v1"
PINS = ("idxsig/learner3.py", "idxsig/learner2.py", "idxsig/speculation.py", "idxsig/paper.py",
        "idxsig/rules/moonshot_g.py", "idxsig/global_panel.py", "idxsig/execution.py", "idxsig/call_cert.py",
        "idxsig/risk_control.py", "research/TA_HISTORY_v1/run.py",
        f"research/{STUDY}/build.py", f"research/{STUDY}/replay.py", f"research/{STUDY}/short.py")
TRIAL = ROOT / "research" / "QUANT_GRADE" / "trials" / f"{STUDY}_registered.json"


def main() -> int:
    out = HERE / "protocol.json"
    if out.exists() or TRIAL.exists():
        sys.exit("error: protocol.json or the trial registration exists; the freeze happens once")
    if (HERE / "results").exists():
        sys.exit("error: results exist before the freeze")
    build = json.loads((HERE / "data" / "events_BUILD.json").read_text(encoding="utf-8"))
    rules = json.loads((HERE / "short_rules.json").read_text(encoding="utf-8"))
    start, end = rules["period"]
    if build["range"] != [start, end]:
        sys.exit(f"error: the build's range {build['range']} is not the frozen period {rules['period']}")
    proto24, sha24 = learner3.protocol()
    events = f"research/{STUDY}/data/events.csv.gz"
    n = sum(v["built"] for s, v in build["per_session"].items() if start <= s <= end)
    proto = {
        "study_id": STUDY, "frozen_at": utc_stamp(), "short_rules": f"research/{STUDY}/short_rules.json",
        "owner_instruction": "2026-10-30: 'i need immediate result' / 'just do whatever is necessary'",
        "question": "on a period no KOD study has read: (1) do LEARNER v2.4's replayed raw forecasts rank the "
                    "next-session own dumpers above the others (v2.4's registered claim, an independent read of "
                    "RECENT_REPLAY_v1); (2) does the redesigned paper short of the certified calls make money after "
                    "typical costs (short_rules.json, the primary bar)?",
        "range": [start, end], "events_in_range_before_outcomes": n, "events": events, "manifest": build["manifest"],
        "learner": {"version": learner3.VERSION, "protocol": "research/LEARNER_v2/protocol_v2_4.json",
                    "protocol_sha256": sha24, "warm_start_sha256": learner3.HISTORY_SHA256, "claim": proto24["claim"]},
        "statistic": "replay: protocol_v2_4.json 'claim' verbatim (AUC, session bootstrap, z, looks 250/500/1000); "
                     "short: short_rules.json bar (TYPICAL net mean > 0 and one-sided 95% lower bound > 0)",
        "timing": "as RECENT_REPLAY_v1: at each session the learner knows every replay outcome resolved by the previous "
                  "session's close; running DOWN10_1 base rate; FADE10_5 prior 0.403; centres from earlier replay "
                  "forecasts; gates not replayed; the certified bar from the 2022-2023 calibration plus this replay's "
                  "own earlier outcomes",
        "sealed_data": "US 2024 onward is sealed; this period's outcomes are read once, on the owner's instruction; "
                       "nothing is tuned on them (code_pins); the same pull vintage as RECENT_REPLAY_v1",
        "limits": ["survivorship: today's universe", "one pull vintage for twins, breadth and market features",
                   "BASE5 simulated without unit conversion", "gates and published probabilities not replayed",
                   "no historical borrow availability; the stop is assumed filled at its price on daily bars"],
        "one_run": "replay.py writes results/ once; short.py writes results/SHORT_RESULT.json once",
        "data_pins": {events: sha256_file(ROOT / events),
                      f"data/manifests/{build['manifest']}": sha256_file(MANIFESTS / build["manifest"]),
                      f"research/{STUDY}/data/events_BUILD.json": sha256_file(HERE / "data" / "events_BUILD.json"),
                      f"research/{STUDY}/short_rules.json": sha256_file(HERE / "short_rules.json"),
                      "research/LEARNER_v2/warmstart_v4/events_us.csv.gz": learner3.HISTORY_SHA256},
        "code_pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    out.write_text(json.dumps(proto, indent=1) + "\n")
    TRIAL.write_text(json.dumps({
        "id": f"{STUDY}_registered", "experiment": STUDY, "date": utc_stamp()[:10],
        "hypothesis": f"on US +30% spikes {start}..{end} ({n} events built before outcomes), a period no KOD study has "
                      "read: the redesigned paper short of LEARNER v2.4's certified next-day dump calls (short at the "
                      "next open, stop 1.30x, else cover at the 5th close) has a positive mean net return per trade under "
                      "TYPICAL costs with a one-sided 95% session-bootstrap lower bound above zero; beside it, v2.4's "
                      "registered AUC claim on the same period",
        "one_sided_p": None, "p_source": f"research/{STUDY}/protocol.json", "variants_searched": 0,
        "outcome": "PENDING (frozen before any outcome was read)", "counted": False, "registered": utc_stamp()[:10],
        "sealed_data_read": f"US {start}..{end} outcomes, once, on the owner's instruction of 2026-10-30",
    }, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "range", "events_in_range_before_outcomes")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
