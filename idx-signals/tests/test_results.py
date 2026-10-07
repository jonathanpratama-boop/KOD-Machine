import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from idxsig.backtest import RunConfig
from idxsig.results import verify_runs, write_run
from tests.support import random_walk_panel
from tests.support import run_synthetic as run

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "tools" / "check_append_only.py"


class RunStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "results"
        df, meta = random_walk_panel(n_tickers=10, n_sessions=60)
        self.output = run(RunConfig("PLACEBO_COINFLIP", random_draws=10), df, meta)

    def tearDown(self):
        for p in Path(self.tmp.name).rglob("*"):
            if p.is_file():
                p.chmod(stat.S_IWUSR | stat.S_IRUSR)
        self.tmp.cleanup()

    def write(self):
        return write_run(self.output, allow_dirty=True, commit=False, root=self.root)

    def test_run_is_written_once_hashed_and_read_only(self):
        run_dir = self.write()
        self.assertEqual(sorted(p.name for p in run_dir.iterdir()),
                         ["REPORT.md", "random_draws.csv", "summary.json", "trades.csv.gz"])
        for p in run_dir.iterdir():
            self.assertEqual(stat.S_IMODE(p.stat().st_mode) & 0o222, 0)
        line = json.loads((self.root / "RUNS.jsonl").read_text().splitlines()[0])
        self.assertEqual(line["run_id"], run_dir.name)
        self.assertEqual(verify_runs(self.root, use_git=False), [])
        report = (run_dir / "REPORT.md").read_text()
        self.assertIn("Hit rate", report)
        self.assertIn("Average net return", report)

    def test_existing_run_directory_is_never_reused(self):
        run_dir = self.write()
        with self.assertRaises(FileExistsError):
            (run_dir / "summary.json").open("x")

    def test_edited_or_deleted_run_files_fail_verify(self):
        run_dir = self.write()
        target = run_dir / "summary.json"
        target.chmod(0o644)
        target.write_text(target.read_text().replace('"hit_rate"', '"hit_rate_edited"', 1))
        problems = verify_runs(self.root, use_git=False)
        self.assertTrue(any("edited" in p for p in problems))
        (run_dir / "random_draws.csv").chmod(0o644)
        (run_dir / "random_draws.csv").unlink()
        self.assertTrue(any("missing" in p for p in verify_runs(self.root, use_git=False)))

    def test_unindexed_run_directory_fails_verify(self):
        self.write()
        (self.root / "runs" / "stray").mkdir()
        self.assertTrue(any("not in RUNS.jsonl" in p for p in verify_runs(self.root, use_git=False)))


class AppendOnlyGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@example.invalid")
        run = self.repo / "idx-signals" / "results" / "runs" / "r1"
        run.mkdir(parents=True)
        (run / "summary.json").write_text("{}\n")
        (self.repo / "idx-signals" / "results" / "RUNS.jsonl").write_text('{"run_id":"r1"}\n')
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "first run")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True)

    def guard(self, *args):
        return subprocess.run(["python3", str(GUARD), *args], cwd=self.repo, capture_output=True, text=True)

    def test_appending_passes(self):
        with (self.repo / "idx-signals" / "results" / "RUNS.jsonl").open("a") as fh:
            fh.write('{"run_id":"r2"}\n')
        self.git("add", "-A")
        self.assertEqual(self.guard("--staged").returncode, 0)

    def test_editing_a_past_run_fails(self):
        (self.repo / "idx-signals" / "results" / "runs" / "r1" / "summary.json").write_text('{"better": true}\n')
        self.git("add", "-A")
        result = self.guard("--staged")
        self.assertEqual(result.returncode, 1)
        self.assertIn("frozen record", result.stderr)

    def test_rewriting_the_index_fails_in_history_check(self):
        (self.repo / "idx-signals" / "results" / "RUNS.jsonl").write_text('{"run_id":"r1","hit_rate":0.9}\n')
        self.git("commit", "-q", "-am", "rewrite")
        result = self.guard("--all")
        self.assertEqual(result.returncode, 1)
        self.assertIn("rewrites earlier lines", result.stderr)

    def test_deleting_a_run_fails(self):
        self.git("rm", "-q", "-r", "idx-signals/results/runs/r1")
        self.assertEqual(self.guard("--staged").returncode, 1)

    def test_corporate_action_registry_is_frozen_and_manual_file_append_only(self):
        """Guards against: re-classifying past corporate actions in place (which would silently change
        every run that used the registry), or rewriting a primary-source entry instead of adding one."""
        ca = self.repo / "idx-signals" / "data" / "corporate_actions"
        ca.mkdir(parents=True)
        (ca / "ca_registry-1.csv").write_text("ticker,action_type\nAAAA,UNKNOWN\n")
        (ca / "manual.csv").write_text("ticker,effective_date\nAAAA,2024-01-02\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "registry")
        (ca / "ca_registry-1.csv").write_text("ticker,action_type\nAAAA,STOCK_SPLIT\n")
        self.git("add", "-A")
        self.assertIn("frozen record", self.guard("--staged").stderr)
        self.git("checkout", "--", ".")
        self.git("reset", "-q")
        (ca / "ca_registry-1.csv").write_text("ticker,action_type\nAAAA,UNKNOWN\n")
        (ca / "manual.csv").write_text("ticker,effective_date\nAAAA,2024-01-03\n")
        self.git("add", "-A")
        self.assertIn("rewrites earlier lines", self.guard("--staged").stderr)
        with (ca / "manual.csv").open("w") as fh:
            fh.write("ticker,effective_date\nAAAA,2024-01-02\nAAAA,2024-01-03\n")
        self.git("add", "-A")
        self.assertEqual(self.guard("--staged").returncode, 0)


if __name__ == "__main__":
    unittest.main()
