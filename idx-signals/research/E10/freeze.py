"""E10: write protocol.json, the machine-readable twin of PROTOCOL.md, with the sha256 of every input and of the code
that runs and checks the test. Refuses if protocol.json exists, if the named feasibility and audit are not GO
(FEASIBILITY_SPEC.md: RAISE >= 300, CUT >= 100, acceptance found >= 98%, audit precision RAISE >= 85% and CUT >=
80%), or if a hashed file has uncommitted changes.

Usage (from idx-signals/): python3 research/E10/freeze.py --feasibility <dir> --audit <dir> --runner <file>
(directories and file relative to research/E10/)
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E10 = ROOT / "research" / "E10"
PANEL = "data/panel/panel_us_repair-20261008T114805Z.csv.gz"
ETORO = "data/raw/etoro/20261016T190421Z/instruments.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feasibility", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--runner", required=True)
    args = ap.parse_args()
    out = E10 / "protocol.json"
    if out.exists():
        sys.exit("error: protocol.json exists; the protocol is frozen once")
    feas = json.loads((E10 / args.feasibility / "FEASIBILITY.json").read_text())["counts"]
    audit = json.loads((E10 / args.audit / "AUDIT.json").read_text())
    go = {
        "raise_events_at_least_300": feas["events_by_class"].get("RAISE", 0) >= 300,
        "cut_events_at_least_100": feas["events_by_class"].get("CUT", 0) >= 100,
        "acceptance_found_at_least_98pct": feas["acceptance_found_share"] >= 0.98,
        "audit_raise_precision_at_least_85pct": audit["go_precision"]["RAISE"] >= 0.85,
        "audit_cut_precision_at_least_80pct": audit["go_precision"]["CUT"] >= 0.80,
    }
    if not all(go.values()):
        sys.exit(f"error: NO-GO, E10 stops at feasibility: {json.dumps(go)}")
    rel = lambda p: f"research/E10/{p}"  # noqa: E731
    hashed = [
        "idxsig/guidance.py", "idxsig/guidance_v2.py", "idxsig/profiles.py",
        rel("FEASIBILITY_SPEC.md"), rel("AUDIT_PROCEDURE.md"), rel("PROTOCOL.md"), rel("filings.csv"),
        rel("collect.py"), rel("collect_resume.py"), rel("feasibility.py"), rel("feasibility_a1.py"),
        rel("audit_blind.py"), rel("audit_score.py"), rel("run_test.py"), rel("run_full.py"), rel("run_e10.py"),
        rel(args.runner), rel("verify_result.py"), rel("freeze.py"),
        rel(f"{args.feasibility}/FEASIBILITY.json"), rel(f"{args.feasibility}/events.csv.gz"),
        rel(f"{args.feasibility}/releases.csv.gz"), rel(f"{args.feasibility}/audit_sample.csv"),
        rel(f"{args.audit}/AUDIT.json"),
        "data/manifests/panel_us_repair-20261008T114805Z.json",
        "tests/test_guidance.py", "tests/test_guidance_v2.py", "tests/test_e10_runner.py", "tests/test_e10_full.py",
        "tests/test_e10_verify.py", "tests/test_e10_a1.py",
    ]
    hashed = list(dict.fromkeys(hashed))
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *hashed], cwd=ROOT, capture_output=True,
                           text=True).stdout
    if dirty.strip():
        sys.exit(f"error: commit these first:\n{dirty}")
    proto = {
        "protocol_id": "E10_GUIDANCE_REVISION_v1",
        "frozen_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "text": "research/E10/PROTOCOL.md",
        "stage": "discovery, run once; historical research, never prospective performance",
        "runner": rel(args.runner),
        "feasibility": {"dir": rel(args.feasibility), "counts": feas, "audit": rel(f"{args.audit}/AUDIT.json"),
                        "audit_go_precision": audit["go_precision"], "go": go},
        "gates": {
            "G1": "RAISE mean excess over matched controls: 95% lower bound > 0",
            "G2": "RAISE mean net > 0 and 1%/99%-clipped mean net > 0",
            "G3": "RAISE mean excess > MAINTAIN mean excess",
            "G4": "RAISE mean net with an extra 0.5% per side > 0",
            "G5": "RAISE mean excess > 0 in each entry year",
            "G6": "account A (USD 10,000, 10% per trade, 10 slots, USD 2 per order) ends above USD 10,000 and above "
                  "its shadow account",
            "verdict": "PASS if G1-G6 all hold, else FAIL"},
        # data files that git does not track are bound here too: the runner checks every hash before it starts
        "hashes": {**{p: sha(ROOT / p) for p in hashed}, PANEL: sha(ROOT / PANEL), ETORO: sha(ROOT / ETORO)},
    }
    out.write_text(json.dumps(proto, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("protocol_id", "frozen_at", "runner", "feasibility")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
