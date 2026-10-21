import importlib.util
import unittest
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1] / "research" / "BINANCE_ANN_1M"


def load(name):
    spec = importlib.util.spec_from_file_location(f"ann_{name}", BASE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run, fm = load("run"), load("fetch_minutes")
L = fm.L


def flat(price=100.0, traded=True):
    c = np.full(L, price)
    t = np.full(L, 5 if traded else 0, dtype=np.uint16)
    return c, t


class HelperTests(unittest.TestCase):
    def test_columns(self):
        self.assertEqual(run.col(-65), 0)
        self.assertEqual(run.col(0), 65)
        self.assertEqual(run.col(1455), L - 1)

    def test_ffill_carries_forward_and_leaves_the_start_missing(self):
        c = np.array([[np.nan, np.nan, 1.0, np.nan, 2.0, np.nan], [3.0, np.nan, np.nan, 4.0, np.nan, np.nan]])
        out = run.ffill(c)
        np.testing.assert_array_equal(out[0], [np.nan, np.nan, 1, 1, 2, 2])
        np.testing.assert_array_equal(out[1], [3, 3, 3, 4, 4, 4])

    def test_quality_needs_the_announcement_bar_and_thirty_prior_minutes(self):
        _, t = flat()
        self.assertTrue(run.quality(t))
        t2 = t.copy()
        t2[run.col(0)] = 0
        self.assertFalse(run.quality(t2))
        t3 = t.copy()
        t3[run.col(-60):run.col(-29)] = 0                         # 31 silent minutes leave 29 traded
        self.assertFalse(run.quality(t3))
        t4 = t.copy()
        t4[run.col(-60):run.col(-30)] = 0                         # 30 silent minutes leave exactly 30
        self.assertTrue(run.quality(t4))

    def test_gross_uses_closes_at_the_entry_and_exit_bars(self):
        c, _ = flat()
        c[run.col(4)], c[run.col(64)] = 100.0, 110.0
        self.assertAlmostEqual(run.gross(c, 4, 60), 0.10)

    def test_winsor_and_p(self):
        x = np.concatenate([np.zeros(98), [-5.0, 5.0]])
        self.assertLess(run.winsor(x).max(), 5.0)
        self.assertAlmostEqual(run.p_one_sided(0.0), 0.5)
        self.assertAlmostEqual(run.p_one_sided(3.0), 0.0013499, places=5)

    def test_cluster_boot_is_deterministic_and_sees_an_effect(self):
        rng = np.random.default_rng(1)
        days = np.repeat(np.arange(60), 3)
        x = 0.03 + rng.normal(0, 0.05, len(days))
        a, b = run.cluster_boot(x, days, boot=2000, seed=5), run.cluster_boot(x, days, boot=2000, seed=5)
        self.assertEqual(a, b)
        self.assertEqual((a["n"], a["clusters"]), (180, 60))
        self.assertGreater(a["t"], 3.0)
        self.assertGreater(a["lo95"], 0)
        z = run.cluster_boot(rng.normal(0, 0.05, len(days)), days, boot=2000, seed=5)
        self.assertLess(abs(z["t"]), 3.0)

    def test_clustering_widens_the_error_when_a_day_moves_together(self):
        rng = np.random.default_rng(2)
        days = np.repeat(np.arange(40), 5)
        shock = np.repeat(rng.normal(0, 0.05, 40), 5)
        x = shock + rng.normal(0, 0.005, len(days))
        clustered = run.cluster_boot(x, days, boot=3000, seed=1)["se"]
        pretend_independent = run.cluster_boot(x, np.arange(len(days)), boot=3000, seed=1)["se"]
        self.assertGreater(clustered, 1.5 * pretend_independent)


def build_study(effect=0.05, n_events=6, n_ctrl=12, silent_event=None, noise=0.0, seed=0):
    """A manifest, closes and trades for n_events events, each with n_ctrl candidate controls. The event's price rises by
    `effect` more than its controls in the hour after the announcement minute (offsets 0..60); controls drift by 1%."""
    series, closes, trades, events = [], [], [], []
    rng = np.random.default_rng(seed)
    for i in range(n_events):
        key = f"{1000 + i}|TOK{i}"
        events.append({"event_key": key, "token": f"TOK{i}", "pair": f"TOK{i}USDT", "t_ms": (18_000 + i * 3) * 86_400_000 + 5_000})
        cases = [("event", -1, 0.01 + effect + rng.normal(0, noise))] + [("control", k, 0.01 + rng.normal(0, noise / 2))
                                                                              for k in range(n_ctrl)]
        for role, rank, up in cases:
            c, t = flat()
            c[run.col(0):] = 100.0                                 # price before the announcement minute is 100
            ramp = np.linspace(100.0, 100.0 * (1 + up), 61)        # offsets 0..60
            c[run.col(0):run.col(60) + 1] = ramp
            c[run.col(60) + 1:] = ramp[-1]
            if role == "event" and silent_event == i:
                t[run.col(0)] = 0
            series.append({"row": len(closes), "event_key": key, "role": role, "rank": rank, "symbol": f"S{i}{rank}", "bars": 1})
            closes.append(c)
            trades.append(t)
    return {"series": series, "events": events}, np.array(closes), np.array(trades)


class StudyTests(unittest.TestCase):
    def test_planted_effect_is_recovered(self):
        man, closes, trades = build_study(effect=0.05)
        table = run.event_table(None, man, closes, trades)
        self.assertEqual([e["valid"] for e in table], [True] * 6)
        self.assertTrue(all(len(e["controls"]) == 10 for e in table))
        df = run.spec_values(table, run.ffill(closes), trades, 0, 60)
        self.assertEqual(len(df), 6)
        np.testing.assert_allclose(df.excess, 0.05, atol=1e-12)
        np.testing.assert_allclose(df.gross, 0.06, atol=1e-12)
        self.assertEqual(set(df.n_controls), {10})

    def test_event_silent_in_the_announcement_bar_is_dropped(self):
        man, closes, trades = build_study(silent_event=2)
        table = run.event_table(None, man, closes, trades)
        self.assertEqual([e["valid"] for e in table], [True, True, False, True, True, True])
        self.assertEqual(len(run.spec_values(table, run.ffill(closes), trades, 0, 60)), 5)

    def test_too_few_controls_drops_the_event(self):
        man, closes, trades = build_study(n_ctrl=4)
        table = run.event_table(None, man, closes, trades)
        self.assertFalse(any(e["valid"] for e in table))

    def test_a_delayed_entry_needs_a_trade_in_that_bar(self):
        man, closes, trades = build_study()
        trades[0][run.col(4)] = 0                                  # event 0 does not trade in the bar of a 4-minute delay
        table = run.event_table(None, man, closes, trades)
        d4 = run.spec_values(table, run.ffill(closes), trades, 4, 60)
        self.assertEqual(len(d4), 5)
        self.assertNotIn("1000|TOK0", set(d4.event_key))

    def test_paths_and_the_announcement_minute(self):
        man, closes, trades = build_study(effect=0.05)
        table = run.event_table(None, man, closes, trades)
        cf = run.ffill(closes)
        paths = run.path_means(table, cf)
        row = lambda m: paths[paths.m == m].iloc[0]  # noqa: E731
        self.assertAlmostEqual(row(-5).excess, 0.0)
        self.assertAlmostEqual(row(0).excess, 0.0)                 # the ramp starts at offset 0 at the base price
        self.assertAlmostEqual(row(60).excess, 0.05)
        self.assertAlmostEqual(row(60).event, 0.06)
        extra = run.pre_and_minute(table, cf)
        self.assertAlmostEqual(extra["pre_announcement_excess_m60_to_m1"], 0.0)
        self.assertAlmostEqual(extra["announcement_minute_excess"], 0.0)


class EndToEndTests(unittest.TestCase):
    """main() on a synthetic study in a temporary tree: files, gates, verdict, and the refusal to run twice."""

    def stage(self, effect, noise):
        import hashlib
        import json
        import tempfile
        import pandas as pd
        from unittest import mock

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        man, closes, trades = build_study(effect=effect, n_events=90, noise=noise, seed=4)
        (tmp / "research" / "X" / "minutes").mkdir(parents=True)
        (tmp / "research" / "X" / "feasibility").mkdir()
        npz = tmp / "research" / "X" / "minutes" / "minutes.npz"
        np.savez_compressed(npz, closes=closes.astype(np.float32), trades=trades)
        pd.DataFrame({"article_id": [1], "token": ["A"]}).to_csv(tmp / "research" / "X" / "feasibility" / "events.csv", index=False)
        man["npz"] = {"path": "research/X/minutes/minutes.npz", "sha256": hashlib.sha256(npz.read_bytes()).hexdigest()}
        man["events_csv_sha256"] = hashlib.sha256((tmp / "research" / "X" / "feasibility" / "events.csv").read_bytes()).hexdigest()
        man["panel_manifest"] = "none"
        (tmp / "research" / "X" / "minutes" / "MANIFEST.json").write_text(json.dumps(man))
        for p in (mock.patch.object(run, "HERE", tmp / "research" / "X"), mock.patch.object(run, "ROOT", tmp),
                  mock.patch.object(run, "OUT", tmp / "research" / "X" / "results"), mock.patch.object(run, "BOOT", 1500)):
            p.start()
            self.addCleanup(p.stop)
        return tmp / "research" / "X" / "results"

    def test_a_real_effect_passes_and_a_null_fails(self):
        import json
        import io
        from contextlib import redirect_stdout

        out = self.stage(effect=0.05, noise=0.02)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(), 0)
        res = json.loads((out / "RESULT.json").read_text())
        self.assertTrue(res["gates"]["G1_excess_t_ge_3"] and res["gates"]["G2_net_and_winsorised_net_gt_0"])
        self.assertTrue(res["gates"]["G4_delayed_5min_excess_gt_0"])
        self.assertEqual(res["events"]["valid"], 90)
        for name in ("RESULT.json", "events.csv", "grid.csv", "paths.csv"):
            self.assertTrue((out / name).exists(), name)
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            run.main()                                                # a second run is refused

    def test_no_effect_fails_g1(self):
        import json
        import io
        from contextlib import redirect_stdout

        out = self.stage(effect=0.0, noise=0.02)
        with redirect_stdout(io.StringIO()):
            run.main()
        res = json.loads((out / "RESULT.json").read_text())
        self.assertFalse(res["gates"]["G1_excess_t_ge_3"])
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(res["reading"].startswith("FAIL"))


class PoolTests(unittest.TestCase):
    def daily(self, base="AAA", first=0, last=500, qv=2e6):
        days = np.arange(first, last)
        return {"base": base, "days": days, "qv": np.full(len(days), qv)}

    def test_pool_rules(self):
        d = {"OKUSDT": self.daily("OK"), "OWNUSDT": self.daily("OWN"), "NEARUSDT": self.daily("NEAR"),
             "USDCUSDT": self.daily("USDC"), "BTCUPUSDT": self.daily("BTCUP"), "ETHDOWNUSDT": self.daily("ETHDOWN"),
             "YOUNGUSDT": self.daily("YOUNG", first=290), "THINUSDT": self.daily("THIN", qv=5e5),
             "DEADUSDT": self.daily("DEAD", last=300), "BRIEFUSDT": self.daily("BRIEF", first=250, last=500),
             "EUROUSDT": self.daily("EUR")}
        pool = fm.pool_for(300, "OWNUSDT", {"NEARUSDT"}, d)
        self.assertEqual(pool, ["BRIEFUSDT", "OKUSDT"])            # 50 days of history is enough; every other rule excludes

    def test_permutation_is_seeded_by_the_event(self):
        pool = [f"P{i:02d}USDT" for i in range(40)]
        a, b = fm.permuted(pool, 123, "ABC"), fm.permuted(pool, 123, "ABC")
        self.assertEqual(a, b)
        self.assertEqual(sorted(a), sorted(pool))
        self.assertNotEqual(a, fm.permuted(pool, 124, "ABC"))
        self.assertNotEqual(a, fm.permuted(pool, 123, "ABD"))


if __name__ == "__main__":
    unittest.main()
