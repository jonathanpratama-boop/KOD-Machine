import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import pandas as pd

from tests.support import random_walk_panel, synthetic_registry

spec = importlib.util.spec_from_file_location(
    "idxnews_run",
    Path(__file__).resolve().parents[1] / "research" / "IDX_INSIDER_NEWS" / "run_v2.py",
)
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


class GateTests(unittest.TestCase):
    def frame(self, n, excess, net, years=("2021", "2022", "2023")):
        rows = [
            {
                "posted_wib": f"{years[i % len(years)]}-0{1 + i % 9}-1{i % 9}T10:00:00+07:00",
                "excess": excess,
                "net_return": net,
                "control_mean": net - excess,
            }
            for i in range(n)
        ]
        return pd.DataFrame(rows)

    def test_gates_need_a_year_with_enough_events_and_every_such_year_positive(self):
        f = self.frame(90, 0.03, 0.03)
        stats = {
            "mean_excess": 0.03,
            "t_excess": 4.0,
            "mean_net": 0.03,
            "winsorised_net": 0.02,
            "mean_net_extra_cost": 0.02,
        }
        g, years = run.gates(f, stats)
        self.assertTrue(all(g.values()))
        self.assertEqual(sorted(years), ["2021", "2022", "2023"])
        thin = self.frame(30, 0.03, 0.03)  # 10 per year: no year qualifies
        self.assertFalse(run.gates(thin, stats)[0]["G3_excess_gt_0_in_each_year_with_20_events"])
        mixed = f.copy()
        mixed.loc[mixed.posted_wib.str[:4] == "2022", "excess"] = -0.05
        self.assertFalse(run.gates(mixed, stats)[0]["G3_excess_gt_0_in_each_year_with_20_events"])

    def test_threshold_and_cost_gates(self):
        f = self.frame(90, 0.03, 0.03)
        base = {
            "mean_excess": 0.03,
            "t_excess": 2.9,
            "mean_net": 0.03,
            "winsorised_net": 0.02,
            "mean_net_extra_cost": 0.02,
        }
        self.assertFalse(run.gates(f, base)[0]["G1_excess_t_ge_3"])
        self.assertFalse(
            run.gates(f, {**base, "t_excess": 3.5, "mean_net_extra_cost": -0.001})[0][
                "G4_net_gt_0_with_extra_0.5pct_per_side"
            ]
        )
        self.assertFalse(
            run.gates(f, {**base, "t_excess": 3.5, "winsorised_net": -0.001})[0][
                "G2_net_and_winsorised_net_gt_0"
            ]
        )


class EndToEnd(unittest.TestCase):
    def stage(self, drift_names):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        df, meta = random_walk_panel(
            n_tickers=60, n_sessions=220, seed=5, drift={i: 0.004 for i in range(drift_names)}
        )
        reg, _ = synthetic_registry(df, meta)
        dates = sorted(df["date"].unique())
        rows = []
        for j in range(30):
            ticker = f"S{j:03d}" if j < drift_names else f"S{30 + j:03d}"
            rows.append(
                {
                    "ticker": ticker,
                    "posted_wib": f"{dates[45 + 4 * j].date()}T17:00:00+07:00",
                    "title": f"t{j}",
                }
            )
        pd.DataFrame(rows).to_csv(tmp / "events.csv", index=False)
        patches = [
            mock.patch.object(run, "HERE", tmp),
            mock.patch.object(run, "OUT", tmp / "results"),
            mock.patch.object(run, "START", str(dates[0].date())),
            mock.patch.object(run, "END", str(dates[-1].date())),
            mock.patch.object(run, "BOOT", 800),
            mock.patch.object(run, "DRAWS", 40),
            mock.patch.object(
                run,
                "load_inputs",
                lambda: (df, reg, {"panel_sha256": "synthetic", "registry_sha256": "synthetic"}),
            ),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return tmp / "results"

    def go(self, drift_names):
        out = self.stage(drift_names)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(), 0)
        return out, json.loads((out / "RESULT.json").read_text())

    def test_a_planted_effect_passes_and_is_written_out(self):
        out, res = self.go(30)
        self.assertEqual(res["verdict"], "PASS", res["gates"])
        self.assertGreater(res["primary_hold_20"]["mean_excess"], 0.03)
        self.assertEqual(res["variants_reported"], 3)
        for name in ("RESULT.json", "events.csv", "grid.csv"):
            self.assertTrue((out / name).exists(), name)
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            run.main()

    def test_no_effect_fails(self):
        _, res = self.go(0)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertFalse(res["gates"]["G1_excess_t_ge_3"])


if __name__ == "__main__":
    unittest.main()
