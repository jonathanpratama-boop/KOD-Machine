import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location(
    "engine_run",
    Path(__file__).resolve().parents[1] / "research" / "QUANT_ENGINE_2005_2019" / "run.py",
)
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)


def panel(seed=3, names=450, sessions=1700, effect=0.0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2004-01-02", periods=sessions)
    sd = rng.uniform(0.01, 0.04, names)
    r = rng.normal(0, sd, (sessions, names)) + effect * (
        0.025 - sd
    )  # calmer stocks drift up when effect > 0
    adj = pd.DataFrame(
        100 * np.exp(np.cumsum(r, axis=0)), index=dates, columns=[f"S{i}" for i in range(names)]
    )
    return adj, adj.copy(), pd.DataFrame(np.full(adj.shape, 1e9), index=dates, columns=adj.columns)


class EnginePanelTests(unittest.TestCase):
    def test_shapes_and_timing(self):
        adj, cl, vol = panel()
        P = run.build_panels(adj, cl, vol)
        T = len(P["meta"])
        self.assertGreater(T, 40)
        for k in run.FEATURES + ["fwd"]:
            self.assertEqual(P[k].shape, (T, adj.shape[1]))
        m = P["meta"][10]
        self.assertEqual(m["entry"], adj.index.get_loc(m["formed"]) + 1)
        self.assertTrue(adj.index[m["exit"]].month != adj.index[m["exit"] + 1].month)

    def test_features_ignore_the_future(self):
        adj, cl, vol = panel()
        P = run.build_panels(adj, cl, vol)
        t = 30
        cut = adj.index.get_loc(P["meta"][t]["formed"])
        adj2 = adj.copy()
        adj2.iloc[cut + 1 :] *= np.random.default_rng(1).uniform(
            0.5, 2.0, adj2.iloc[cut + 1 :].shape
        )
        P2 = run.build_panels(adj2, adj2.copy(), vol)
        for k in run.FEATURES:
            np.testing.assert_allclose(P[k][t], P2[k][t], equal_nan=True, err_msg=k)
        self.assertFalse(np.allclose(P["fwd"][t], P2["fwd"][t], equal_nan=True))

    def test_end_to_end_runs_and_finds_planted_low_vol_effect(self):
        adj, cl, vol = panel(effect=2.0, sessions=3200)
        P = run.build_panels(adj, cl, vol)
        saved = run.FACTORS
        try:
            fac = pd.DataFrame(
                np.random.default_rng(2).normal(0, 0.01, (len(adj), 5)),
                index=adj.index,
                columns=["Mkt-RF", "SMB", "HML", "RF", "MOM"],
            )
            tmp = Path(__file__).resolve().parent / "_tmp_factors.csv.gz"
            fac.to_csv(tmp)
            run.FACTORS = tmp
            run.FIRST_SCORE = "2006-06-01"
            m, b = run.evaluate(P)
            res = run.results(m, b)
        finally:
            run.FACTORS = saved
            tmp.unlink(missing_ok=True)
        self.assertGreater(len(m), 30)
        self.assertGreater(res["ic_combined"]["mean"], 0.02)
        # the planted drift is persistent, so trailing return (mom) legitimately carries some of it too: assert the
        # planted driver gets a clearly positive weight, not that it beats every correlated feature
        self.assertGreater(res["mean_ridge_weights"]["lowvol"], 0.05)
        self.assertEqual(
            set(res["gates"]),
            {
                "G1_ic_t_ge_3_and_9_of_12_years",
                "G2_net_spread_positive_at_100k",
                "G3_factor_alpha_t_ge_3",
                "G4_large_cap_ic_t_ge_2",
            },
        )


if __name__ == "__main__":
    unittest.main()
