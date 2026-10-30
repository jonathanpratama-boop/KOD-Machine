"""PREMOVE_SHADOW_v1: write protocol.json and the PENDING trial registration, once, after fit_control.py and before
the first daily forecast. Owner decision of 2026-10-30 (handoff/decisions/2026-10-30_premove_sequence_shadow_trial.md).

    python3 freeze.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import sha256_file, utc_stamp  # noqa: E402

HERE = Path(__file__).resolve().parent
TRIAL = ROOT / "research" / "QUANT_GRADE" / "trials" / "PREMOVE_SHADOW_v1_registered.json"
PINS = ("idxsig/premove_shadow.py", "idxsig/premove_core.py", "idxsig/premove.py",
        "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/models.json",
        "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/summary.json",
        "research/PREMOVE_SEQUENCE_v1/protocol.json",
        "research/PREMOVE_SHADOW_v1/control_model.json", "research/PREMOVE_SHADOW_v1/fit_control.py")
FIRST, LAST = "2026-10-30", "2027-10-29"   # 365 decision days; each needs five more daily closes
FINAL_DUE = "2027-11-05"                   # the last decision's fifth outcome bar closes 2027-11-04 at 24:00 UTC


def main() -> int:
    out = HERE / "protocol.json"
    if out.exists() or TRIAL.exists():
        sys.exit("error: the trial is frozen once")
    control = json.loads((HERE / "control_model.json").read_text())
    proto = {
        "trial_id": "PREMOVE_SHADOW_v1", "frozen_at": utc_stamp(),
        "decision": "Owner, 2026-10-30: retain sequence as a frozen research challenger, keep summary as the default "
                    "research baseline, and run one preregistered prospective shadow trial with a shuffled control.",
        "arms": {
            "summary": "PR #19 frozen summary model (models.json), temperature from summary.json",
            "sequence": "PR #19 frozen sequence model (models.json), temperature from summary.json",
            "shuffled": "control_model.json: the sequence recipe fitted on 2020-2021 with each row's 20-day window "
                        "shuffled separately (one permutation per row, the day's return, range and volume kept "
                        "together; premove_shadow.shuffle_windows); temperature chosen on 2022 by log loss",
        },
        "same_for_every_arm": {
            "universe": "the crypto routine's Binance USDT pull (trading pairs), non-stable, non-leveraged "
                        "(global_panel.STABLE / LEVERAGED, the benchmark's own exclusion)",
            "eligibility": "premove_core.build_examples unchanged: 60 consecutive valid days, median prior 20-day "
                           "quote volume >= 100,000 USDT, finite features; only completed bars",
            "target": "PR #19 unchanged: entry = next UTC day's open (label reference only), barrier "
                      "b = max(log 1.10, 3 x 20-day sd x sqrt 5), first daily close beyond +/-b within 5 days",
            "budget": "five names per arm per day, highest upside probability, ties by ticker",
            "populations": {"early": "ret1 < 10% and ret5 < 20% (primary)", "all": "every eligible candidate"},
        },
        "timing": "each day's forecast is sealed after that UTC day closes (crypto routine, about 00:25 UTC) and "
                  "before its outcome bars exist; the label's entry reference is that 00:00 UTC open, which no "
                  "feature reads. The ledger is hash-chained and externally timestamped.",
        "trial": {"first_decision": FIRST, "last_decision": LAST, "final_outcomes_due": FINAL_DUE,
                  "stopping": "fixed: no early stop, no extension, no performance-based change"},
        "analysis": {
            "primary": "early-population daily hit rate, sequence minus summary (censored alerts count as non-hits)",
            "bootstrap": {"block": 10, "draws": 2000, "seed": 20261031},
            "uncertainty": "paired moving calendar-block bootstrap of daily hit-rate differences, 95% interval",
            "reported_beside": ["distinct episodes caught", "duplicate alerts", "matched-episode lead",
                                "censoring counts", "probability quality (Brier, log loss) of every candidate",
                                "the all-candidates population"],
        },
        "promotion_hurdle": {
            "min_difference": 0.01,
            "rule": "sequence becomes the default research baseline only if, at the end, its early hit rate beats "
                    "summary's by at least 1 percentage point, the paired 95% interval is above zero, and it "
                    "catches more distinct episodes; otherwise summary stays the default",
            "temporal_order": "attributing the gain to the ORDER of days additionally needs sequence to beat the "
                              "shuffled control with a paired 95% interval above zero",
            "note": "a research hurdle, not economic breakeven; neither arm has shown trading profit",
        },
        "honesty": [
            "12 months may be inconclusive: the retrospective +0.88 point difference had a 95% interval of -0.22 to "
            "+1.81; detecting a stable advantage of that size could take about 2.5 to 3 years. An inconclusive end "
            "leaves summary as the default; the trial is not extended until it becomes significant.",
            "the live universe is today's trading pairs, not the archive catalogue the models were fitted on",
            f"the control was fitted on a re-collected vintage ({control['panel']['collected_at']}) whose panel is "
            f"byte-identical to PR #19's input: {control['panel']['same_bytes_as_pr19_input']}; its refit of the "
            "frozen arms on that vintage is recorded in control_model.json",
            "the live USDT universe now includes tokenized US-stock pairs (for example AAPLB, SPYB) that did not "
            "exist in the 2020-2023 training catalogue; the benchmark's universe rule includes them and is kept "
            "unchanged for every arm (seen in the pre-freeze dry run of 2026-10-29, before any outcome)",
            "paper only: no orders, no execution or profit claim",
        ],
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    out.write_text(json.dumps(proto, indent=1) + "\n")
    TRIAL.write_text(json.dumps({
        "id": "PREMOVE_SHADOW_v1_registered", "experiment": "PREMOVE_SHADOW_v1", "date": utc_stamp()[:10],
        "hypothesis": "prospective, 2026-10-30..2027-10-29: the frozen sequence arm's early-population five-name "
                      "daily hit rate exceeds the frozen summary arm's by >= 1 point with a paired 95% calendar-block "
                      "interval above zero and more distinct episodes; order attributed only if it also beats the "
                      "shuffled control",
        "one_sided_p": None, "p_source": "research/PREMOVE_SHADOW_v1/protocol.json", "variants_searched": 0,
        "outcome": "PENDING (registered before the first forecast)", "counted": False, "registered": utc_stamp()[:10],
    }, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("trial_id", "frozen_at", "trial")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
