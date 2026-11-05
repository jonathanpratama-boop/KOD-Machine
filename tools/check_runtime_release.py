#!/usr/bin/env python3
"""Offline release gate: unit invariants plus a restartable end-to-end paper run."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
ENV = dict(
    os.environ, PYTHONPATH=os.pathsep.join((str(REPO / "idx-signals"), str(REPO / "kod-machine")))
)
FOCUSED = (
    "tests.test_llm_arm",
    "tests.test_llm_arm_audit",
    "tests.test_llm_arm_independent",
    "tests.test_component_entrypoints",
    "tests.test_components_strategy",
    "tests.test_components_plan",
    "tests.test_components_execution",
    "tests.test_runtime_validation",
    "tests.test_strategy_checks",
    "tests.test_clock_integrity",
    "tests.test_clock_real_sample",
    "tests.test_research_workflow",
    "tests.test_runtime_account",
    "tests.test_runtime_data_context",
    "tests.test_runtime_backup",
    "tests.test_runtime_coordinator",
    "tests.test_runtime_integrity",
    "tests.test_runtime_candidates",
    "tests.test_timing_research",
    "tests.test_timing_capture",
    "tests.test_timing_context",
    "tests.test_timing_integration",
    "tests.test_timing_evidence",
    "tests.test_time_anchor",
    "tests.test_runtime_timing_paper",
    "tests.test_timing_processing_boundary",
    "tests.test_intraday_capture",
    "tests.test_market_time",
    "tests.test_binance_blocks",
    "tests.test_source_clock_and_blocks",
    "tests.test_research_controls",
    "tests.test_research_evaluation",
    "tests.test_experiment_catalog",
    "tests.test_crypto_account",
    "tests.test_crypto_account_concurrency",
    "tests.test_crypto_replay",
    "tests.test_paper_account",
    "tests.test_paper_account_report",
)


def run(args, cwd=REPO, capture=False):
    result = subprocess.run(
        [PYTHON, *args], cwd=cwd, env=ENV, check=True, text=True, capture_output=capture
    )
    if capture:
        return json.loads(result.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("focused", "full"), default="focused")
    args = parser.parse_args(argv)
    run(["-m", "unittest", *FOCUSED], REPO / "idx-signals")
    run(
        ["-m", "unittest", "discover", "-s", "workstation_tests", "-p", "test_operations.py"],
        REPO / "kod-machine",
    )
    run(
        [
            "-m",
            "unittest",
            "discover",
            "-s",
            "workstation_tests",
            "-p",
            "test_timing_operations.py",
        ],
        REPO / "kod-machine",
    )
    run(
        [
            "-m",
            "unittest",
            "discover",
            "-s",
            "workstation_tests",
            "-p",
            "test_decision_inspector.py",
        ],
        REPO / "kod-machine",
    )
    with tempfile.TemporaryDirectory(prefix="kod-release-") as base:
        root = Path(base) / "runtime"
        command = ["-m", "idxsig.runtime", "--root", str(root)]
        run([*command, "demo"], capture=True)
        before = (root / "snapshot.json").read_bytes()
        run([*command, "verify"], capture=True)
        run([*command, "status"], capture=True)
        run([*command, "demo"], capture=True)
        if (root / "snapshot.json").read_bytes() != before:
            raise AssertionError("repeated demo changed the final snapshot")
        archive = Path(base) / "runtime.zip"
        run([*command, "backup", "--output", str(archive)], capture=True)
        restored = Path(base) / "restored"
        run(
            ["-m", "idxsig.runtime", "--root", str(restored), "restore", "--archive", str(archive)],
            capture=True,
        )
        run(["-m", "idxsig.runtime", "--root", str(restored), "verify"], capture=True)
        if (restored / "snapshot.json").read_bytes() != before:
            raise AssertionError("restored snapshot differs")
        # Use the real web presentation contract, not a second mock schema.
        sys.path.insert(0, str(REPO / "kod-machine"))
        from kod.workstation.operations import OperationsArchive

        OperationsArchive(restored).snapshot()
        # Independently exercise the new timing-only route and its joined records.
        timing_root = Path(base) / "timing-runtime"
        timing_command = ["-m", "idxsig.runtime", "--root", str(timing_root)]
        first = run([*timing_command, "timing-demo"], capture=True)
        second = run([*timing_command, "timing-demo"], capture=True)
        if first != second:
            raise AssertionError("timing demo retry changed its sealed fixture result")
        run([*timing_command, "timing-status"], capture=True)
        from kod.workstation.operations import TimingArchive

        TimingArchive(timing_root).snapshot()
        validation = run([*command, "validate"], capture=True)
        if validation["status"] != "PASS":
            raise AssertionError("retained synthetic account failed isolated replay")
        research_root = Path(base) / "research"
        research = ["tools/kod.py", "research", "--root", str(research_root)]
        researched = run([*research, "demo"], capture=True)
        repeated = run([*research, "demo"], capture=True)
        if researched["attempts_used"] != 1 or repeated["attempts_used"] != 1:
            raise AssertionError("research retry consumed a duplicate hypothesis")
        run([*research, "status"], capture=True)
        llm = ["tools/kod.py", "llm", "--root", str(Path(base) / "llm")]
        first_llm = run([*llm, "demo"], capture=True)
        second_llm = run([*llm, "demo"], capture=True)
        if first_llm != second_llm or first_llm["cases"][0]["net_return"] != -0.12:
            raise AssertionError("LLM demo lost its synthetic loss or duplicated a retry")
        if first_llm["model_service_running"] or first_llm["entry_permission"]:
            raise AssertionError("LLM workbench acquired unintended execution authority")
    if args.mode == "full":
        run(["-m", "unittest"], REPO / "idx-signals")
        run(["-m", "unittest"], REPO / "kod-machine")
        run(["-m", "unittest", "discover", "-s", "workstation_tests"], REPO / "kod-machine")
    print(
        json.dumps(
            {
                "ok": True,
                "mode": args.mode,
                "network": False,
                "scope": "engineering invariants; synthetic paper run; backup/restore",
                "profitability_validated": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
