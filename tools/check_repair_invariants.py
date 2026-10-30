#!/usr/bin/env python3
"""Run the bounded engineering regression suite and optionally save a JSON receipt.

This checks software invariants, not trading profitability or live data coverage.
Run from any directory: python tools/check_repair_invariants.py --json /tmp/kod-check.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    ("execution", "idx-signals", "tests.test_execution_repair"),
    ("storage", "idx-signals", "tests.test_storage_repair"),
    ("provider_resume", "idx-signals", "tests.test_source_resume_repair"),
    ("outcomes_and_evaluation", "idx-signals", "tests.test_outcome_repair"),
    ("historical_context_and_prices", "kod-machine", "workstation_tests.test_repair_context"),
)


def git_info():
    def read(*args):
        proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return proc.stdout.strip() if proc.returncode == 0 else None
    return {"commit": read("rev-parse", "HEAD"), "working_tree_status": read("status", "--porcelain")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="optional machine-readable result path")
    parser.add_argument("--list", action="store_true", help="list checks without running")
    args = parser.parse_args(argv)
    if args.list:
        for name, directory, module in CHECKS:
            print(f"{name}: {directory} / {module}")
        return 0
    receipt = {"schema": "KOD-ENGINEERING-CHECK-v1", "started_at": datetime.now(timezone.utc).isoformat(),
               "python": platform.python_version(), "platform": platform.platform(), "source": git_info(),
               "scope": "targeted offline engineering regressions; not full CI or strategy validation", "checks": []}
    for name, directory, module in CHECKS:
        started = time.monotonic()
        command = [sys.executable, "-m", "unittest", module, "-v"]
        try:
            proc = subprocess.run(command, cwd=ROOT / directory, capture_output=True, text=True, timeout=300)
            status, output, code = ("PASS" if proc.returncode == 0 else "FAIL"), proc.stdout + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            status, output, code = "FAIL", "check exceeded 300 seconds", None
        except OSError as exc:
            status, output, code = "UNAVAILABLE", str(exc), None
        result = {"name": name, "status": status, "elapsed_seconds": round(time.monotonic() - started, 3),
                  "command": command, "directory": directory, "exit_code": code, "output": output}
        receipt["checks"].append(result)
        print(f"{status}: {name} ({result['elapsed_seconds']}s)", flush=True)
        if status != "PASS":
            print(output, file=sys.stderr)
    receipt["passed"] = all(c["status"] == "PASS" for c in receipt["checks"])
    receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
