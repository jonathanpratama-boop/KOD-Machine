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
ENV = dict(os.environ, PYTHONPATH=os.pathsep.join((str(REPO / 'idx-signals'), str(REPO / 'kod-machine'))))
FOCUSED = (
    'tests.test_runtime_account', 'tests.test_runtime_data_context',
    'tests.test_runtime_backup', 'tests.test_runtime_coordinator',
    'tests.test_runtime_integrity', 'tests.test_runtime_candidates', 'tests.test_timing_research',
    'tests.test_research_evaluation', 'tests.test_experiment_catalog',
    'tests.test_crypto_account', 'tests.test_crypto_account_concurrency',
    'tests.test_crypto_replay', 'tests.test_paper_account', 'tests.test_paper_account_report',
)


def run(args, cwd=REPO, capture=False):
    result = subprocess.run([PYTHON, *args], cwd=cwd, env=ENV, check=True,
                            text=True, capture_output=capture)
    if capture:
        return json.loads(result.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('focused', 'full'), default='focused')
    args = parser.parse_args(argv)
    run(['-m', 'unittest', *FOCUSED], REPO / 'idx-signals')
    run(['-m', 'unittest', 'discover', '-s', 'workstation_tests', '-p', 'test_operations.py'], REPO / 'kod-machine')
    with tempfile.TemporaryDirectory(prefix='kod-release-') as base:
        root = Path(base) / 'runtime'
        command = ['-m', 'idxsig.runtime', '--root', str(root)]
        run([*command, 'demo'], capture=True)
        before = (root / 'snapshot.json').read_bytes()
        run([*command, 'verify'], capture=True)
        run([*command, 'status'], capture=True)
        run([*command, 'demo'], capture=True)
        if (root / 'snapshot.json').read_bytes() != before:
            raise AssertionError('repeated demo changed the final snapshot')
        archive = Path(base) / 'runtime.zip'
        run([*command, 'backup', '--output', str(archive)], capture=True)
        restored = Path(base) / 'restored'
        run(['-m', 'idxsig.runtime', '--root', str(restored), 'restore', '--archive', str(archive)], capture=True)
        run(['-m', 'idxsig.runtime', '--root', str(restored), 'verify'], capture=True)
        if (restored / 'snapshot.json').read_bytes() != before:
            raise AssertionError('restored snapshot differs')
        # Use the real web presentation contract, not a second mock schema.
        sys.path.insert(0, str(REPO / 'kod-machine'))
        from kod.workstation.operations import OperationsArchive
        OperationsArchive(restored).snapshot()
    if args.mode == 'full':
        run(['-m', 'unittest'], REPO / 'idx-signals')
        run(['-m', 'unittest'], REPO / 'kod-machine')
        run(['-m', 'unittest', 'discover', '-s', 'workstation_tests'], REPO / 'kod-machine')
    print(json.dumps({'ok': True, 'mode': args.mode, 'network': False,
                      'scope': 'engineering invariants; synthetic paper run; backup/restore',
                      'profitability_validated': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
