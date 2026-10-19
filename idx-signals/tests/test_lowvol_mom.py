import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location(
    "lowvol_run", Path(__file__).resolve().parents[1] / "research" / "US_LOWVOL_MOM_2005_2019" / "run.py")
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)


def panel(planted: bool, seed=4, names=400, sessions=1400):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2004-01-02", periods=sessions)
    sd = rng.uniform(0.005, 0.04, names)
    drift = (-sd * 0.15) if planted else np.zeros(names)          # calmer stocks drift higher when planted
    r = rng.normal(drift, sd, (sessions, names))
    adj = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=dates, columns=[f"S{i}" for i in range(names)])
    vol = pd.DataFrame(np.full(adj.shape, 1e9), index=dates, columns=adj.columns)     # always liquid
    return adj, adj.copy(), vol


class EngineTests(unittest.TestCase):
    def test_planted_low_vol_effect_is_found_and_null_is_not(self):
        m, skipped = run.monthly(*panel(True))
        self.assertGreater(len(m), 20)
        planted = run.verdicts(m)["H1_lowvol_Q5_minus_Q1"]
        self.assertGreater(planted["mean_monthly"], 0)
        self.assertGreater(planted["t"], 2.4)
        m0, _ = run.monthly(*panel(False))
        self.assertLess(abs(run.verdicts(m0)["H1_lowvol_Q5_minus_Q1"]["t"]), 2.4)

    def test_entry_is_the_close_after_formation(self):
        rng = np.random.default_rng(9)
        dates = pd.bdate_range("2004-01-02", periods=900)
        base = 100 * np.exp(np.cumsum(rng.normal(0, 1e-6, (900, 400)), axis=0))
        t = [i for i in range(400, 800) if dates[i].month != dates[i + 1].month][0]
        vol = pd.DataFrame(np.full(base.shape, 1e9), index=dates)
        for jump_at, expect_in_return in ((t + 1, False), (t + 2, True)):
            a = base.copy()
            a[jump_at:, 0] *= 2.0                       # stock 0 doubles on that session
            m, _ = run.monthly(pd.DataFrame(a, index=dates), pd.DataFrame(a, index=dates), vol)
            u = float(m.loc[m.formed == dates[t].strftime("%Y-%m-%d"), "universe"].iloc[0])
            if expect_in_return:
                self.assertGreater(u, 1e-3)             # about +1/400
            else:
                self.assertLess(abs(u), 1e-4)           # the jump happened before entry: not earned


if __name__ == "__main__":
    unittest.main()
