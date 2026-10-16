"""E9: write protocol.json, the machine-readable twin of PROTOCOL.md, with the sha256 of every input and of the code
that runs and checks the test. Refuses if protocol.json exists, if the amended feasibility check is not GO, or if
a hashed file has uncommitted changes.

Usage (from idx-signals/): python3 research/E9/freeze.py
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import rules as rule_registry  # noqa: E402
from idxsig.profiles import PROFILES  # noqa: E402

E9 = ROOT / "research" / "E9"
HASHED = [
    "idxsig/backtest.py", "idxsig/execution.py", "idxsig/controls.py", "idxsig/market.py", "idxsig/profiles.py",
    "idxsig/quality.py", "idxsig/global_panel.py", "idxsig/catalyst.py", "idxsig/rules/__init__.py",
    "idxsig/rules/moonshot_g.py", "idxsig/rules/audit.py", "idxsig/rules/sandbox.py",
    "research/E9/PROTOCOL.md", "research/E9/run_test.py", "research/E9/verify_result.py",
    "research/E9/make_entries.py", "research/E9/feasibility_a3.py",
    "research/E9/entries/signals.csv", "research/E9/entries/controls.csv.gz", "research/E9/entries/entries_meta.json",
    "research/E9/feasibility_a3/classes.csv.gz", "research/E9/feasibility_a3/FEASIBILITY.json",
    "data/manifests/panel_us_repair-20261008T114805Z.json",
    "tests/test_catalyst.py", "tests/test_e9_runner.py",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    out = E9 / "protocol.json"
    if out.exists():
        sys.exit("error: protocol.json exists; the protocol is frozen once")
    feas = json.loads((E9 / "feasibility_a3" / "FEASIBILITY.json").read_text())
    if feas["decision"] != "GO":
        sys.exit("error: the amended feasibility check is not GO; E9 stops at feasibility")
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *HASHED], cwd=ROOT, capture_output=True, text=True).stdout
    if dirty.strip():
        sys.exit(f"error: commit these first:\n{dirty}")
    meta = json.loads((E9 / "entries" / "entries_meta.json").read_text())
    rule = rule_registry.get(meta["config"]["rule_id"])
    first = json.loads((E9 / "feasibility" / "FEASIBILITY.json").read_text())
    proto = {
        "protocol_id": "E9_CATALYST_SPLIT_v1",
        "frozen_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "text": "research/E9/PROTOCOL.md",
        "stage": "discovery, run once; historical research, never prospective performance",
        "hypothesis": "Among US G2_RET30 movers, those with an SEC information filing accepted after 16:00 New York "
                      "time on the prior session and by 09:15 on the entry session beat those without one over the E2 "
                      "plan; those with a dilution filing do worst.",
        "rule": {"rule_id": rule.rule_id, "version": rule.version, "sha256": rule.sha256},
        "trade": {**meta["config"], "plan": "buy at the next open; sell at the close of the 5th session after entry",
                  "cost_tiers_per_side": [list(t) for t in PROFILES["US"].cost_tiers], "sec_fee_on_sales": PROFILES["US"].fee_sell},
        "sample": {"statuses": ["EXITED", "EXIT_DATA_END"], "classes": ["DOCUMENTED", "UNDOCUMENTED", "DILUTION"],
                   "requires_window_covered": True,
                   "excluded_and_counted": ["NO_CIK", "NO_SEC_DATA", "NO_ENTRY_SESSION", "NO_HEADER", "window not covered"]},
        "statistics": {"metric": "mean net return per trade", "cluster": "ISO week of the entry session",
                       "resamples": 2000, "seed": 20261018, "interval": "percentile, 2.5 and 97.5",
                       "win": "net > 0, Wilson 95% interval",
                       "excess": "net minus the mean net of the trade's scored matched controls (v2, 200 draws, seed 20261008)"},
        "costs": {"stress_extra_per_side": 0.005, "unit_uncertain_tier_per_side": 0.015},
        "secondary": {"holding_days": 20, "note": "same entries; overlap still decided by the original 5-session exit"},
        "exposure": {"capital_usd": 100000.0, "notional_usd": meta["config"]["notional"]},
        "acceptance": {
            "years": ["2020", "2021", "2022"],
            "criteria": {
                "C1": "at least 150 scored DOCUMENTED and 150 scored UNDOCUMENTED",
                "C2": "DOCUMENTED mean net > 0 in each of 2020, 2021, 2022 (signal year)",
                "C3": "lower 95% bound of the DOCUMENTED mean net > 0",
                "C4": "lower 95% bound of DOCUMENTED minus UNDOCUMENTED > 0",
                "C5": "DOCUMENTED mean excess over matched controls > 0",
                "C6": "DOCUMENTED mean net > 0 with an extra 0.5% per side"}},
        "verdicts": {
            "Q1": "SEPARATES if the lower 95% bound of DOCUMENTED minus UNDOCUMENTED > 0; DOES_NOT_SEPARATE if the "
                  "difference <= 0; else INCONCLUSIVE",
            "Q2": "PROFITABLE_IN_THIS_HISTORICAL_TEST if C1-C6 all hold; UNPROFITABLE if the DOCUMENTED mean net <= 0; "
                  "else INCONCLUSIVE",
            "overall": "RESEARCH-POSITIVE if C1-C6; else NEGATIVE if Q2 is UNPROFITABLE or Q1 is DOES_NOT_SEPARATE; "
                       "else INCONCLUSIVE"},
        "feasibility": {"first": {"path": "research/E9/feasibility/FEASIBILITY.json", "decision": first["decision"],
                                  "failed": [k for k, v in first["go_conditions"].items() if not v]},
                        "second": {"path": "research/E9/feasibility_a3/FEASIBILITY.json", "decision": feas["decision"],
                                   "entered_by_class": feas["counts"]["entered_by_class"]}},
        "hashes": {rel: sha(ROOT / rel) for rel in HASHED},
    }
    out.write_text(json.dumps(proto, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("protocol_id", "frozen_at", "rule", "feasibility")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
