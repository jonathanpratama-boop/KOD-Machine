"""The shared-data rule warns on raw reads in new study scripts only, and never fails by default."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(TOOLS), str(TOOLS / "ci_tests")]

import check_shared_data as shared  # noqa: E402
import ci_push  # noqa: E402
from git_fixture import ZERO_SHA, Repo  # noqa: E402

RAW_STUDY = textwrap.dedent(
    """\
    import pandas as pd
    import zipfile, urllib.request, requests
    from pathlib import Path
    import numpy as np

    RAW = Path("idx-signals/data/raw")
    prices = pd.read_csv(RAW / "BTCUSDT.csv")
    book = pd.read_parquet("book.parquet")
    state = pd.read_pickle(HERE / "cache.pkl")
    archive = zipfile.ZipFile(RAW / "klines.zip")
    lines = open(RAW / "trades.jsonl").read()
    page = urllib.request.urlopen("https://example.invalid/klines")
    reply = requests.get("https://example.invalid/book")
    text = (RAW / "notes.txt").read_text()
    grid = np.load(HERE / "grid.npy")
    """
)
CLEAN_STUDY = textwrap.dedent(
    """\
    import hashlib, json
    from pathlib import Path
    from idxsig import panel
    from idxsig.runtime.storage import read_json
    import idxsig.global_panel as gp

    HERE = Path(__file__).parent
    PROTO = json.loads((HERE / "protocol.json").read_text())
    prices = panel.load_yahoo(HERE / PROTO["manifest"])
    state = read_json(HERE / "state.json")
    crypto = gp.load_crypto(PROTO["crypto_manifest"])
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with open(HERE / "out" / "rows.csv", "w") as handle:
        handle.write("a,b\\n")
    archive_out = __import__("zipfile").ZipFile(HERE / "bundle.zip", "w")
    """
)


class ScanTests(unittest.TestCase):
    def test_every_direct_raw_read_is_reported_with_its_line(self):
        findings = shared.scan(RAW_STUDY.encode(), "run.py")
        self.assertEqual(
            [(f.line, f.call) for f in findings],
            [
                (7, "pd.read_csv"),
                (8, "pd.read_parquet"),
                (9, "pd.read_pickle"),
                (10, "zipfile.ZipFile"),
                (11, "open"),
                (12, "urllib.request.urlopen"),
                (13, "requests.get"),
                (14, "(RAW / 'notes.txt').read_text"),
                (15, "np.load"),
            ],
        )

    def test_shared_loaders_protocols_hashes_and_writes_are_not_reported(self):
        self.assertEqual(shared.scan(CLEAN_STUDY.encode(), "run.py"), [])

    def test_unparsable_script_raises_for_the_caller_to_report(self):
        with self.assertRaises(SyntaxError):
            shared.scan(b"def broken(:\n", "run.py")


class AnnotationTests(unittest.TestCase):
    def test_workflow_command_escapes_property_and_message_syntax(self):
        self.assertEqual(
            ci_push.workflow_command("warning", "50% done\nnext", file="a,b:c.py", line=3),
            "::warning file=a%2Cb%3Ac.py,line=3::50%25 done%0Anext",
        )


class AddedStudyScriptTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Repo(Path(temp.name))
        self.base = self.repo.commit(
            "an existing study that reads raw files",
            {"idx-signals/research/OLD_v1/run.py": RAW_STUDY},
        )

    def warnings(self, proc):
        return [line for line in proc.stdout.splitlines() if line.startswith("::warning ")]

    def test_only_python_files_added_under_research_are_reported(self):
        self.repo.append("idx-signals/research/OLD_v1/run.py", "more = pd.read_csv('x.csv')\n")
        head = self.repo.commit(
            "new study, a new library loader and an edit to an existing study",
            {
                "idx-signals/research/NEW_v1/run.py": "import pandas as pd\n\nx = pd.read_csv('a.csv')\n",
                "idx-signals/research/NEW_v1/clean.py": CLEAN_STUDY,
                "idx-signals/research/NEW_v1/PROTOCOL.md": "pd.read_csv('in prose')\n",
                "idx-signals/idxsig/new_loader.py": "import pandas as pd\nx = pd.read_csv('a.csv')\n",
            },
        )
        proc = self.repo.run("check_shared_data.py", "--push", self.base, head)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.warnings(proc),
            [
                "::warning file=idx-signals/research/NEW_v1/run.py,line=3,title=Shared data rule::"
                "pd.read_csv(...) reads raw data directly in a new study script; load it through "
                "a shared idxsig loader (handoff/KOD_FIX_PLAN.md, Fix 3)"
            ],
        )
        self.assertIn("1 warning(s) in 1 of 2 new study script(s)", proc.stdout)

    def test_strict_turns_warnings_into_a_failure(self):
        head = self.repo.commit("new study", {"idx-signals/research/NEW_v1/run.py": RAW_STUDY})
        self.assertEqual(
            self.repo.run("check_shared_data.py", "--push", self.base, head).returncode, 0
        )
        strict = self.repo.run("check_shared_data.py", "--strict", "--push", self.base, head)
        self.assertEqual(strict.returncode, 1)
        self.assertEqual(len(self.warnings(strict)), 9)

    def test_clean_range_passes_even_when_strict(self):
        head = self.repo.commit("clean study", {"idx-signals/research/NEW_v1/run.py": CLEAN_STUDY})
        proc = self.repo.run("check_shared_data.py", "--strict", "--range", f"{self.base}..{head}")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(self.warnings(proc), [])

    def test_new_branch_push_reads_only_the_head_commit(self):
        self.repo.commit("raw study", {"idx-signals/research/A_v1/run.py": RAW_STUDY})
        head = self.repo.commit("clean study", {"idx-signals/research/B_v1/run.py": CLEAN_STUDY})
        proc = self.repo.run("check_shared_data.py", "--push", ZERO_SHA, head)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("::notice::shared data: new branch", proc.stdout)
        self.assertEqual(self.warnings(proc), [])

    def test_force_push_reads_only_the_head_commit(self):
        self.repo.git("checkout", "-q", "-b", "rewritten", self.base)
        dropped = self.repo.commit("dropped by the force-push")
        self.repo.git("checkout", "-q", "main")
        head = self.repo.commit("raw study", {"idx-signals/research/A_v1/run.py": RAW_STUDY})
        proc = self.repo.run("check_shared_data.py", "--push", dropped, head)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("is not an ancestor of", proc.stdout)
        self.assertEqual(len(self.warnings(proc)), 9)

    def test_unparsable_new_study_is_reported_not_skipped(self):
        head = self.repo.commit("broken", {"idx-signals/research/NEW_v1/run.py": "def broken(:\n"})
        proc = self.repo.run("check_shared_data.py", "--push", self.base, head)
        self.assertEqual(proc.returncode, 0)
        [warning] = self.warnings(proc)
        self.assertIn("run.py could not be scanned (invalid syntax", warning)

    def test_study_too_deeply_nested_to_scan_is_reported_and_the_check_still_exits_0(self):
        # 5,000 terms parse but are too deep to unparse; 30,000 are too deep to parse at all.
        for terms in (5_000, 30_000):
            with self.subTest(terms=terms):
                source = "open(" + " + ".join(["'a'"] * terms) + ")\n"
                path = f"idx-signals/research/DEEP_{terms}_v1/run.py"
                before = self.repo.head()
                head = self.repo.commit(f"deep study {terms}", {path: source})
                proc = self.repo.run("check_shared_data.py", "--push", before, head)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                [warning] = self.warnings(proc)
                self.assertIn(f"{path} could not be scanned (maximum recursion depth", warning)

    def test_unreadable_range_warns_and_fails_only_when_strict(self):
        for args, code in ((["--range", "main..missing"], 0), (["--strict", "--range", "x..y"], 1)):
            with self.subTest(args=args):
                proc = self.repo.run("check_shared_data.py", *args)
                self.assertEqual(proc.returncode, code)
                self.assertIn("could not run", proc.stdout)
                self.assertIn("is not a commit in this repository", proc.stdout)


if __name__ == "__main__":
    unittest.main()
