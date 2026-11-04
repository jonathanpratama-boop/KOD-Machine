"""RECENT_REPLAY_v1: write protocol.json (the freeze) and the PENDING trial registration, once, before run.py.

    python3 freeze.py --start 2026-04-01 --end 2026-10-28

Pins the events file (features only, built before this), the pull's manifest, v2.4's protocol and every module the
replay calls, so run.py refuses to run on anything else.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import learner3  # noqa: E402
from idxsig.provenance import MANIFESTS, sha256_file, utc_stamp  # noqa: E402

HERE = Path(__file__).resolve().parent
PINS = ("idxsig/learner3.py", "idxsig/learner2.py", "idxsig/speculation.py", "idxsig/paper.py",
        "idxsig/rules/moonshot_g.py", "idxsig/global_panel.py", "idxsig/execution.py", "idxsig/call_cert.py",
        "idxsig/risk_control.py", "research/RECENT_REPLAY_v1/build.py", "research/RECENT_REPLAY_v1/run.py",
        "research/TA_HISTORY_v1/run.py")
TRIAL = ROOT / "research" / "QUANT_GRADE" / "trials" / "RECENT_REPLAY_v1_registered.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()
    out = HERE / "protocol.json"
    if out.exists() or TRIAL.exists():
        sys.exit("error: protocol.json or the trial registration exists; the freeze happens once")
    build = json.loads((HERE / "data" / "events_BUILD.json").read_text(encoding="utf-8"))
    if (HERE / "results").exists():
        sys.exit("error: results exist before the freeze")
    proto24, sha24 = learner3.protocol()
    events = "research/RECENT_REPLAY_v1/data/events.csv.gz"
    n_in_range = sum(v["built"] for s, v in build["per_session"].items() if args.start <= s <= args.end)
    proto = {
        "study_id": "RECENT_REPLAY_v1", "frozen_at": utc_stamp(), "protocol_md": "research/RECENT_REPLAY_v1/PROTOCOL.md",
        "owner_instruction": "2026-10-30: backtrack and test how accurate it is on the recent data already collected",
        "question": "do LEARNER v2.4's raw forecasts, replayed session by session over this year's US +30% spikes, rank "
                    "the stocks that close at least 10% lower at the next session (on their own) above the others?",
        "range": [args.start, args.end], "events_in_range_before_outcomes": n_in_range,
        "events": events, "manifest": build["manifest"],
        "learner": {"version": learner3.VERSION, "protocol": "research/LEARNER_v2/protocol_v2_4.json",
                    "protocol_sha256": sha24, "warm_start_sha256": learner3.HISTORY_SHA256,
                    "claim": proto24["claim"]},
        "statistic": "protocol_v2_4.json 'claim', verbatim: AUC of raw NEXT_DUMP10_1 forecasts over resolved pairs, "
                     "bootstrap over signal sessions (1000, seed 20261029), z = (AUC - 0.5) / se, looks 250/500/1000 "
                     "with min sessions 30/60/120, SKILL when z >= 3.75 / 3.0 / 3.0; descriptive beside it: benchmark AUC, "
                     "Brier gains (daily blocks), DUMP10_5, by month, certified calls' realised losing rate",
        "timing": "at each session the learner knows every replay outcome resolved by the previous session's close; "
                  "running DOWN10_1 base rate (0.5 below 20 resolved); FADE10_5 prior 0.403; centres from earlier "
                  "replay forecasts; gates not replayed (claim is on raw)",
        "sealed_data": "US 2024 onward is sealed; this run reads the outcomes of the range once on the owner's "
                       "instruction; nothing is tuned on them (code_pins); a later version is tested on live data or a "
                       "period sealed from now on",
        "limits": ["survivorship: today's universe, names delisted since are absent",
                   "one pull vintage: twins, breadth and market features from this frame",
                   "BASE5 simulated without unit conversion", "gates and published probabilities not replayed"],
        "one_run": "run.py writes results/ once and refuses to run again",
        "data_pins": {events: sha256_file(ROOT / events),
                      f"data/manifests/{build['manifest']}": sha256_file(MANIFESTS / build["manifest"]),
                      "research/RECENT_REPLAY_v1/data/events_BUILD.json": sha256_file(HERE / "data" / "events_BUILD.json"),
                      "research/LEARNER_v2/warmstart_v4/events_us.csv.gz": learner3.HISTORY_SHA256},
        "code_pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    out.write_text(json.dumps(proto, indent=1) + "\n")
    TRIAL.write_text(json.dumps({
        "id": "RECENT_REPLAY_v1_registered", "experiment": "RECENT_REPLAY_v1", "date": utc_stamp()[:10],
        "hypothesis": f"replay of LEARNER v2.4 over US +30% spikes {args.start}..{args.end} ({n_in_range} events built "
                      "before outcomes): raw NEXT_DUMP10_1 forecasts rank the next-session dumpers above the others, "
                      "AUC > 0.5 with z >= 3.75 at the 250 look, 3.0 at 500 and 1000 (protocol_v2_4.json 'claim')",
        "one_sided_p": None, "p_source": "research/RECENT_REPLAY_v1/protocol.json", "variants_searched": 0,
        "outcome": "PENDING (frozen before any outcome was read)", "counted": False, "registered": utc_stamp()[:10],
        "sealed_data_read": f"US {args.start}..{args.end} outcomes, once, on the owner's instruction of 2026-10-30",
    }, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "range", "events_in_range_before_outcomes", "manifest")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
