"""Regression tests for the stabilization review of 2026-10-30 (handoff: Ace's findings 1, 3 and 5).

1. A trade can never be entered before its signal: the configuration refuses it, the CLI refuses it, and a stored run
   that claims it fails verification.
3. A corrected outcome is counted once, and the correction wins, for every reader of resolutions.
5. Concurrent ledger appenders cannot fork the hash chain, and a panel is never overwritten by a later build.
"""
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from idxsig import catalysts, learner2, paper, results, speculation
from idxsig.execution import ExecConfig
from idxsig.provenance import sha256_file, write_csv_gz_exclusive


class Chronology(unittest.TestCase):
    def test_configuration_refuses_an_entry_before_the_signal(self):
        ExecConfig(holding_days=5, entry_lag=1)
        for lag in (0, -1, -3):
            with self.assertRaises(ValueError):
                ExecConfig(holding_days=5, entry_lag=lag)
        with self.assertRaises(ValueError):
            ExecConfig(holding_days=-1)

    def test_cli_refuses_a_negative_entry_lag_before_doing_anything(self):
        proc = subprocess.run([sys.executable, "-m", "idxsig", "run", "--rule", "X", "--entry-lag", "-3"],
                              cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("at least one session after its signal", proc.stderr)

    def _run_dir(self, root: Path, entry_lag: int, signal: str, entry: str, exit_: str) -> None:
        run = root / "runs" / "20240131T000000Z_RULE_v1"
        run.mkdir(parents=True)
        (run / "summary.json").write_text(json.dumps({"config": {"entry_lag": entry_lag}}))
        with gzip.open(run / "trades.csv.gz", "wt", newline="") as fh:
            fh.write("ticker,signal_date,status,entry_date,exit_date,net_return\n")
            fh.write(f"ABCD,{signal},EXITED,{entry},{exit_},1.0\n")
            fh.write("EFGH,2024-02-01,SKIP_NO_TRIGGER,,,\n")
        files = {p.name: sha256_file(p) for p in run.iterdir()}
        (root / "RUNS.jsonl").write_text(json.dumps({"run_id": run.name, "files": files}) + "\n")

    def test_a_stored_run_with_a_trade_before_its_signal_fails_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run_dir(root, -3, "2024-01-31", "2024-01-28", "2024-01-31")
            problems = results.verify_runs(root, use_git=False)
            self.assertTrue(any("entry_lag -3" in p for p in problems), problems)
            self.assertTrue(any("entered 2024-01-28 at or before its signal 2024-01-31" in p for p in problems), problems)

    def test_a_chronological_stored_run_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run_dir(root, 1, "2024-01-31", "2024-02-01", "2024-02-06")
            self.assertEqual(results.verify_runs(root, use_git=False), [])

    def test_write_run_refuses_an_impossible_run(self):
        trades = pd.DataFrame({"ticker": ["ABCD"], "signal_date": ["2024-01-31"], "entry_date": ["2024-01-28"],
                               "exit_date": ["2024-01-31"]})
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                results.write_run({"summary": {"config": {"entry_lag": -3}}, "trades": trades, "draws": pd.DataFrame()},
                                  allow_dirty=True, commit=False, root=Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])


def _resolutions(n: int, market: str = "US", family: str = "SEC13D") -> list[dict]:
    out = []
    for i in range(n):
        out.append({"type": "RESOLUTION", "market": market, "family": family, "set_id": f"S{i}", "window": "BASE5",
                    "resolved_at": f"2026-10-{1 + i % 28:02d}T21:00:00Z", "status": "RESOLVED",
                    "cone": [{"id": "X", "outcome": 1 if i % 2 == 0 else 0}]})
    return out


class CorrectionsCountOnce(unittest.TestCase):
    def setUp(self):
        self.n = max(20, speculation.RUNNING_MIN_N)
        self.records = _resolutions(self.n)
        # one correction of set S0 (outcome 1 -> 0), appended later, naming what it revises
        self.records.append({**self.records[0], "cone": [{"id": "X", "outcome": 0}], "revises": "h0",
                             "resolved_at": "2026-10-29T21:00:00Z"})
        self.expected = (sum(1 for i in range(self.n) if i % 2 == 0) - 1) / self.n

    def test_speculation_running_prior(self):
        prior, n = speculation.running_prior("US", "X", self.records)
        self.assertEqual(n, self.n)
        self.assertAlmostEqual(prior, self.expected)

    def test_catalyst_running_prior(self):
        prior, n = catalysts.running_prior("SEC13D", "X", self.records)
        self.assertEqual(n, self.n)
        self.assertAlmostEqual(prior, self.expected)

    def test_learner_outcomes_take_the_correction(self):
        out = learner2.outcomes(self.records, "2026-12-01T00:00:00Z")
        self.assertEqual(len([k for k in out if k[1] == "X"]), self.n)
        self.assertEqual(out[("S0", "X")][0], False)

    def test_an_ungraded_revision_clears_the_earlier_outcome(self):
        records = self.records + [{**self.records[1], "cone": [{"id": "X", "outcome": None}], "status": "UNRESOLVABLE",
                                   "revises": "h1", "resolved_at": "2026-10-30T21:00:00Z"}]
        self.assertEqual(speculation.running_prior("US", "X", records)[1], self.n - 1)
        self.assertNotIn(("S1", "X"), learner2.outcomes(records, "2026-12-01T00:00:00Z"))

    def test_one_rule(self):
        latest = paper.latest_resolutions(self.records)
        self.assertEqual(len(latest), self.n)
        self.assertEqual(latest[("S0", "BASE5")]["cone"][0]["outcome"], 0)


class SafeWrites(unittest.TestCase):
    def test_concurrent_appenders_keep_one_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            errors = []

            def writer(tag):
                try:
                    for i in range(40):
                        paper.append([{"type": "T", "writer": tag, "i": i}], path=path)
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)
            threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            self.assertEqual(paper.verify_chain(path), [])
            self.assertEqual(len(paper.ledger_lines(path)), 160)

    def test_panel_publication_is_exclusive_and_content_identical(self):
        frame = pd.DataFrame({"date": ["2024-01-02", "2024-01-03"], "ticker": ["AAAA", "AAAA"], "close": [1.23456789012, 2.0],
                              "volume": pd.array([100, None], dtype="Int64")})
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a" / "panel-x.csv.gz", Path(tmp) / "b" / "panel-x.csv.gz"
            a.parent.mkdir(); b.parent.mkdir()
            frame.to_csv(a, index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.10g")
            write_csv_gz_exclusive(b, frame, index=False, float_format="%.10g")
            self.assertEqual(gzip.decompress(a.read_bytes()), gzip.decompress(b.read_bytes()))
            before = b.read_bytes()
            with self.assertRaises(FileExistsError):
                write_csv_gz_exclusive(b, frame.iloc[:1], index=False, float_format="%.10g")
            self.assertEqual(b.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
