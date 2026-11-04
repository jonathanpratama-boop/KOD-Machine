"""tools/check_no_lookahead.py: one JSON verdict and exit status per run (0 PASS, 1 LEAK, 2 ERROR).

The tool runs in-process on synthetic toy studies and data written to a temporary
directory; no historical study is run and no repository file is written.
"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from tests.test_lookahead_check import CLEAN, CUTOFFS, LEAKS, labelled, prices

TOOL = Path(__file__).resolve().parents[2] / "tools" / "check_no_lookahead.py"
SPEC = importlib.util.spec_from_file_location("check_no_lookahead", TOOL)
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)

STUDY = """import pandas as pd


def decide(data):
    d = data.sort_values(["asset", "time"], kind="stable")
    d = d[d.fwd3.notna()] if {drop_missing_label} else d
    d = d.assign(score=d.groupby("asset").close.transform(lambda s: s.rolling(5, center={centre}).mean()))
    d = d.dropna(subset=["score"])
    return d.assign(long=d.close > d.score)[["time", "asset", "score", "long"]]
"""
DECISIONS = ["--time-column", "time", "--key-columns", "time", "asset"]


class CheckNoLookaheadCli(unittest.TestCase):
    def setUp(self):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def write(self, name: str, content) -> str:
        path = self.dir / name
        if isinstance(content, pd.DataFrame):
            content.to_csv(path, index=False)
        else:
            path.write_text(content)
        return str(path)

    def study(self, *, centre: bool = False, drop_missing_label: bool = False) -> str:
        source = STUDY.format(centre=centre, drop_missing_label=drop_missing_label)
        return self.write(f"study_{centre}_{drop_missing_label}.py", source)

    def run_tool(self, *argv: str) -> tuple[int, dict, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = CLI.main(list(argv))
        return status, json.loads(out.getvalue()), err.getvalue()

    def module(self, study: str, data: pd.DataFrame, *extra: str) -> tuple[int, dict, str]:
        return self.run_tool(
            "module",
            study,
            self.write("data.csv", data),
            "--data-time-column",
            "time",
            "--cutoff",
            *CUTOFFS,
            *DECISIONS,
            *extra,
        )

    def compare(self, decide, cutoff: str = CUTOFFS[1]) -> tuple[int, dict, str]:
        data = prices()
        reference = self.write("full.csv", decide(data))
        candidate = self.write("cut.csv", decide(data[data.time <= pd.Timestamp(cutoff)]))
        return self.run_tool("compare", reference, candidate, "--cutoff", cutoff, *DECISIONS)

    def test_compare_passes_decision_files_that_agree_up_to_the_cutoff(self):
        status, verdict, _ = self.compare(CLEAN)
        self.assertEqual((status, verdict["verdict"], verdict["mode"]), (0, "PASS", "compare"))
        (check,) = verdict["checks"]
        self.assertEqual(
            (check["check"], check["cutoffs"][0]["decisions_compared"]), ("COMPARE", 63)
        )

    def test_compare_fails_a_leaky_study_with_exit_status_one(self):
        status, verdict, _ = self.compare(LEAKS["centred rolling mean"])
        self.assertEqual((status, verdict["verdict"]), (1, "LEAK"))
        leak = verdict["checks"][0]["first_leak"]
        self.assertEqual(
            (leak["cutoff"], leak["kind"]), ("2026-01-25T00:00:00Z", "ONLY_IN_REFERENCE")
        )
        self.assertEqual(leak["key"], ["2026-01-24T00:00:00Z", "A"])

    def test_compare_reads_cells_as_the_text_written(self):
        rows = {"time": ["2026-01-20T00:00:00Z"], "asset": ["A"]}
        reference = self.write("a.csv", pd.DataFrame({**rows, "score": ["1.0"], "note": ["NA"]}))
        candidate = self.write("b.csv", pd.DataFrame({**rows, "score": ["1"], "note": ["NA"]}))
        status, verdict, _ = self.run_tool(
            "compare", reference, candidate, "--cutoff", CUTOFFS[1], *DECISIONS
        )
        leak = verdict["checks"][0]["first_leak"]
        self.assertEqual((status, leak["column"]), (1, "score"))
        self.assertEqual((leak["reference"], leak["candidate"]), ("1.0", "1"))
        keyless = self.write("c.csv", "time,asset,score\n2026-01-20T00:00:00Z,,1\n")
        status, verdict, _ = self.run_tool(
            "compare", keyless, keyless, "--cutoff", CUTOFFS[1], *DECISIONS
        )
        self.assertEqual((status, verdict["error_type"]), (2, "LookaheadCheckError"))
        self.assertIn("key column 'asset' is missing at row 0", verdict["error"])

    def test_module_runs_both_checks_on_a_leaky_study_and_its_clean_twin(self):
        for centre, status, expected in ((True, 1, "LEAK"), (False, 0, "PASS")):
            with self.subTest(centre=centre):
                code, verdict, _ = self.module(self.study(centre=centre), prices())
                self.assertEqual(
                    (code, verdict["verdict"], verdict["mode"]), (status, expected, "module")
                )
                checks = [(c["check"], c["verdict"]) for c in verdict["checks"]]
                self.assertEqual(checks, [("TRUNCATION", expected), ("SCRAMBLE", expected)])

    def test_module_passes_lags_utc_and_scramble_options_to_the_library(self):
        naive = prices().assign(time=prices().time.dt.tz_localize(None))
        status, verdict, _ = self.module(self.study(), naive, "--assume-utc")
        self.assertEqual((status, verdict["verdict"]), (0, "PASS"))
        self.assertTrue(all(check["assume_utc"] for check in verdict["checks"]))
        study = self.study(drop_missing_label=True)
        status, verdict, _ = self.module(study, labelled())
        self.assertEqual((status, verdict["verdict"]), (0, "PASS"))  # undeclared label lag
        status, verdict, _ = self.module(
            study,
            labelled(),
            "--lag",
            "fwd3=3D",
            "--seed",
            "4",
            "--scramble-columns",
            "close",
            "fwd3",
        )
        self.assertEqual((status, verdict["verdict"]), (1, "LEAK"))
        truncation, scramble = verdict["checks"]
        self.assertEqual(truncation["value_lags"], {"fwd3": "P3DT0H0M0S"})
        self.assertEqual((scramble["seed"], scramble["scrambled_columns"]), (4, ["close", "fwd3"]))
        status, verdict, _ = self.module(
            study, labelled(), "--check", "truncation", "--lag", "fwd3=72h"
        )
        self.assertEqual([c["check"] for c in verdict["checks"]], ["TRUNCATION"])

    def test_problems_are_explicit_error_verdicts_with_exit_status_two(self):
        clean = self.study()
        no_decide = self.write("empty.py", "VALUE = 1\n")
        for extra, study, message in (
            (("--lag", "fwd3=3"), clean, "with a unit"),
            (("--lag", "fwd3=3D", "--lag", "fwd3=4D"), clean, "given once"),
            (("--check", "truncation", "--seed", "1"), clean, "apply only to scramble"),
            ((), no_decide, "defines no callable decide"),
            ((), str(self.dir / "missing.py"), "not an existing .py file"),
        ):
            with self.subTest(message=message):
                status, verdict, _ = self.module(study, labelled(), *extra)
                self.assertEqual((status, verdict["verdict"]), (2, "ERROR"))
                self.assertEqual(verdict["error_type"], "UsageError")
                self.assertIn(message, verdict["error"])

    def test_library_refusals_and_study_crashes_are_error_verdicts(self):
        status, verdict, _ = self.run_tool(
            "compare",
            self.write("x.json", "{}"),
            self.write("y.csv", "a\n"),
            "--cutoff",
            CUTOFFS[0],
            *DECISIONS,
        )
        self.assertEqual((status, verdict["error_type"]), (2, "UsageError"))
        naive = prices().assign(time=prices().time.dt.tz_localize(None))
        status, verdict, _ = self.module(self.study(), naive)
        self.assertEqual((status, verdict["error_type"]), (2, "LookaheadCheckError"))
        self.assertIn("without a UTC offset", verdict["error"])
        crash = self.write("crash.py", "def decide(data):\n    raise RuntimeError('study bug')\n")
        status, verdict, stderr = self.module(crash, prices())
        self.assertEqual(
            (status, verdict["error_type"], verdict["error"]), (2, "RuntimeError", "study bug")
        )
        self.assertIn("Traceback", stderr)


if __name__ == "__main__":
    unittest.main()
