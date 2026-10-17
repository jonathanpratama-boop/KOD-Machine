import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

E10 = Path(__file__).resolve().parents[1] / "research" / "E10"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, E10 / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


recorded = load("e10_recorded", "run_e10.py")
verify = load("e10_verify", "verify_result.py")
full, core = recorded.full, recorded.full.core


class VerifyAgainstRunnerTest(unittest.TestCase):
    """The recorded runner (run_e10.py) and verify_result.py on one synthetic panel file: the two codes must agree, and a
    tampered result must be caught."""

    def build(self, root: Path):
        rng = np.random.default_rng(21)
        dates = pd.bdate_range("2021-01-04", periods=420).strftime("%Y-%m-%d")
        names = [f"T{i:02d}" for i in range(40)]
        close = 15 * np.exp(np.cumsum(rng.normal(0, 0.03, (len(dates), len(names))), axis=0))
        opn = close * np.exp(rng.normal(0, 0.02, close.shape))
        low = np.minimum(opn, close) * (1 - rng.uniform(0, 0.04, close.shape))
        uf = np.ones(close.shape)
        uf[:, 3] = 0.25                                   # as-traded price a quarter of the adjusted one
        rows = []
        for i, d in enumerate(dates):
            for j, t in enumerate(names):
                rows.append((d, t, opn[i, j], max(opn[i, j], close[i, j]) * 1.01, low[i, j], close[i, j],
                             rng.uniform(6e5, 5e6), uf[i, j]))
        panel = pd.DataFrame(rows, columns=["date", "ticker", "open", "high", "low", "close", "value", "unit_factor"])
        (root / "data" / "panel").mkdir(parents=True)
        panel_path = root / "data" / "panel" / "panel.csv.gz"
        panel.to_csv(panel_path, index=False)
        e10 = root / "research" / "E10"
        (e10 / "feasibility").mkdir(parents=True)
        ev, rel = [], []
        for k in range(60):
            e = 30 + 5 * k
            when = (f"{dates[e - 1]}T16:30:00", f"{dates[e]}T08:00:00", f"{dates[e - 1]}T11:00:00")[k % 3]
            ev.append({"accession": f"a{k}", "ticker": names[k % 40], "class": ("RAISE", "MAINTAIN", "CUT")[k % 3],
                       "kind": "dollar", "level_change": 0.02, "acceptance_ny": when})
            rel.append({"accession": f"a{k}", "ticker": names[k % 40], "status": "OK", "acceptance_ny": when})
        pd.DataFrame(ev).to_csv(e10 / "feasibility" / "events.csv.gz", index=False)
        pd.DataFrame(rel).to_csv(e10 / "feasibility" / "releases.csv.gz", index=False)
        (e10 / "protocol.json").write_text(json.dumps({"hashes": {}}))
        etoro = root / "data" / "raw" / "etoro" / "20261016T190421Z"
        etoro.mkdir(parents=True)
        (etoro / "instruments.json").write_text(json.dumps({"InstrumentDisplayDatas": []}))
        return panel_path, e10

    def test_verifier_agrees_and_catches_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel_path, e10 = self.build(root)
            saved = (full.ROOT, full.E10, full.OUT, core.PANEL, verify.PANEL, verify.E10)
            full.ROOT, full.E10, full.OUT, core.PANEL = root, e10, e10 / "results", panel_path
            verify.PANEL, verify.E10 = panel_path, e10
            try:
                with redirect_stdout(StringIO()):
                    self.assertEqual(recorded.main(), 0)
                    self.assertEqual(verify.main(), 0)
                path = e10 / "results" / "RESULT.json"
                res = json.loads(path.read_text())
                res["classes"]["RAISE"]["mean_net"] += 1e-6
                path.write_text(json.dumps(res))
                with redirect_stdout(StringIO()):
                    self.assertEqual(verify.main(), 1)
            finally:
                full.ROOT, full.E10, full.OUT, core.PANEL, verify.PANEL, verify.E10 = saved


if __name__ == "__main__":
    unittest.main()
