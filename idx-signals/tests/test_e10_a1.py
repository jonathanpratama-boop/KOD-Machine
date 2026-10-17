import importlib.util
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd

E10 = Path(__file__).resolve().parents[1] / "research" / "E10"
TESTS = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


a1 = load("e10_a1", E10 / "run_a1.py")
verify = load("e10_verify_a1", E10 / "verify_result.py")
fixture = load("e10_verify_fixture", TESTS / "test_e10_verify.py").VerifyAgainstRunnerTest


class AmendedRunnerTest(unittest.TestCase):
    """run_a1.py reads feasibility_a1/, never feasibility/, and its output passes the verifier."""

    def test_reads_the_amended_events(self):
        full, core = a1.full, a1.full.core
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel_path, e10 = fixture.build(None, root)
            shutil.move(str(e10 / "feasibility"), str(e10 / "feasibility_a1"))
            (e10 / "feasibility").mkdir()
            pd.DataFrame({"broken": [1]}).to_csv(e10 / "feasibility" / "events.csv.gz", index=False)
            pd.DataFrame({"broken": [1]}).to_csv(e10 / "feasibility" / "releases.csv.gz", index=False)
            saved = (full.ROOT, full.E10, full.OUT, core.PANEL, verify.PANEL, verify.E10, full.pd)
            full.ROOT, full.E10, full.OUT, core.PANEL = root, e10, e10 / "results", panel_path
            verify.PANEL, verify.E10 = panel_path, e10
            try:
                with redirect_stdout(StringIO()):
                    self.assertEqual(a1.main(), 0)
                    self.assertEqual(verify.main(), 0)
                res = json.loads((e10 / "results" / "RESULT.json").read_text())
                self.assertEqual(res["events_in"], 60)
            finally:
                full.ROOT, full.E10, full.OUT, core.PANEL, verify.PANEL, verify.E10, full.pd = saved


if __name__ == "__main__":
    unittest.main()
