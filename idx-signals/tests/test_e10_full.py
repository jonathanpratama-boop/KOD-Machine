import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location(
    "e10_full", Path(__file__).resolve().parents[1] / "research" / "E10" / "run_full.py"
)
full = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(full)
core = full.core


def random_panel(n=40, names=6, seed=3):
    rng = np.random.default_rng(seed)
    close = 20 * np.exp(np.cumsum(rng.normal(0, 0.03, (n, names)), axis=0))
    opn = close * np.exp(rng.normal(0, 0.02, (n, names)))
    low = np.minimum(opn, close) * (1 - rng.uniform(0, 0.04, (n, names)))
    high = np.maximum(opn, close) * 1.01
    return {
        "open": opn,
        "high": high,
        "low": low,
        "close": close,
        "value": np.full((n, names), 1e6),
        "unit_factor": np.ones((n, names)),
    }


class TradeManyTests(unittest.TestCase):
    def test_matches_single_name_trade(self):
        m = random_panel()
        for stop in (None, 0.05, 0.02):
            for hold in (1, 5, 20):
                got = full.trade_many(m, 4, np.arange(6), hold, stop)
                for j in range(6):
                    want = core.trade(m, 4, j, hold, stop)
                    for g, w in zip(got, want):
                        self.assertAlmostEqual(float(g[j]), float(w), places=12)

    def test_close_entry_buys_the_close_and_keeps_the_exit(self):
        m = random_panel()
        a, b, _, _, x = full.trade_many(m, 4, [0, 1], 20, entry="close")
        np.testing.assert_allclose(a, m["close"][4, [0, 1]])
        np.testing.assert_allclose(b, m["close"][23, [0, 1]])
        self.assertTrue((x == 23).all())

    def test_close_entry_stop_can_gap_on_the_next_open(self):
        m = random_panel()
        m["open"][5, 0] = m["close"][4, 0] * 0.9
        a, b, _, _, x = full.trade_many(m, 4, [0], 20, stop=0.05, entry="close")
        self.assertEqual((float(b[0]), int(x[0])), (m["open"][5, 0], 5))


class TimingTests(unittest.TestCase):
    DATES = np.array(["2021-03-04", "2021-03-05", "2021-03-08"])

    def test_after_close_uses_that_close(self):
        self.assertEqual(full.last_close_before("2021-03-05T16:05:00", self.DATES), 1)

    def test_premarket_and_intraday_use_previous_close(self):
        self.assertEqual(full.last_close_before("2021-03-05T08:00:00", self.DATES), 0)
        self.assertEqual(full.last_close_before("2021-03-05T12:00:00", self.DATES), 0)

    def test_weekend_uses_friday(self):
        self.assertEqual(full.last_close_before("2021-03-06T10:00:00", self.DATES), 1)

    def test_nothing_before(self):
        self.assertIsNone(full.last_close_before("2021-03-04T08:00:00", self.DATES))


class AccountTests(unittest.TestCase):
    def flat(self, n=30, names=3, price=10.0):
        one = np.full((n, names), price)
        return {
            "open": one.copy(),
            "high": one.copy(),
            "low": one.copy(),
            "close": one.copy(),
            "value": np.full((n, names), 1e6),
            "unit_factor": np.ones((n, names)),
        }

    def test_flat_price_loses_costs_and_commissions(self):
        m = self.flat()
        dates = np.array([f"d{i:02d}" for i in range(30)])
        trades = pd.DataFrame({"e": [2], "acceptance_ny": ["a"], "ticker": ["X"]})
        stats, eq = full.simulate(trades, m, {"X": 0}, dates, 0.10, 10, None)
        size = 0.10 * full.START_EQUITY
        c_in, c_out = 0.0015, 0.0015 + 0.0000278
        end = full.START_EQUITY - size - 2 + size * (1 - c_in) * (1 - c_out) - 2
        self.assertAlmostEqual(stats["end_equity"], end, places=6)
        self.assertEqual(
            (stats["trades_taken"], stats["trades_skipped"], stats["win_rate"]), (1, 0, 0.0)
        )
        self.assertEqual(eq.index[0], "d02")

    def test_full_slots_skip_later_trades(self):
        m = self.flat()
        dates = np.array([f"d{i:02d}" for i in range(30)])
        trades = pd.DataFrame(
            {"e": [2, 2, 3], "acceptance_ny": ["a", "b", "c"], "ticker": ["X", "Y", "Z"]}
        )
        stats, _ = full.simulate(trades, m, {"X": 0, "Y": 1, "Z": 2}, dates, 0.10, 1, None)
        self.assertEqual((stats["trades_taken"], stats["trades_skipped"]), (1, 2))

    def test_stop_exit_and_marked_drawdown(self):
        m = self.flat()
        m["low"][5, 0] = 9.0  # touches the 5% stop at 9.5
        m["close"][4, 0] = 9.8
        dates = np.array([f"d{i:02d}" for i in range(30)])
        trades = pd.DataFrame({"e": [2], "acceptance_ny": ["a"], "ticker": ["X"]})
        stats, eq = full.simulate(trades, m, {"X": 0}, dates, 0.20, 5, 0.05)
        size = 0.20 * full.START_EQUITY
        shares = size * (1 - 0.0015) / 10.0
        end = full.START_EQUITY - size - 2 + shares * 9.5 * (1 - 0.0015 - 0.0000278) - 2
        self.assertAlmostEqual(stats["end_equity"], end, places=6)
        self.assertAlmostEqual(eq["d04"], full.START_EQUITY - size - 2 + shares * 9.8, places=6)
        self.assertLess(stats["max_drawdown"], -0.01)


class EndToEndSmokeTest(unittest.TestCase):
    """main() on a synthetic panel in a scratch tree: wiring only, no claim about any result."""

    def test_main_runs_and_refuses_a_second_run(self):
        import gzip
        import json
        import tempfile

        rng = np.random.default_rng(11)
        dates = np.array(pd.bdate_range("2021-01-04", periods=420).strftime("%Y-%m-%d"))
        names = 40
        tickers = np.array([f"T{i:02d}" for i in range(names)])
        m = random_panel(len(dates), names, seed=5)
        m["value"] = rng.uniform(6e5, 5e6, (len(dates), names))
        ev, rel = [], []
        for k in range(60):
            e = 30 + 5 * k
            t = tickers[k % names]
            acc = f"0000-{k:04d}"
            when = f"{dates[e - 1]}T16:30:00"
            ev.append(
                {
                    "accession": acc,
                    "ticker": t,
                    "class": ("RAISE", "MAINTAIN", "CUT")[k % 3],
                    "kind": "dollar",
                    "level_change": 0.02,
                    "acceptance_ny": when,
                }
            )
            rel.append({"accession": acc, "ticker": t, "status": "OK", "acceptance_ny": when})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            e10 = root / "research" / "E10"
            (e10 / "feasibility").mkdir(parents=True)
            pd.DataFrame(ev).to_csv(e10 / "feasibility" / "events.csv.gz", index=False)
            pd.DataFrame(rel).to_csv(e10 / "feasibility" / "releases.csv.gz", index=False)
            (e10 / "protocol.json").write_text(json.dumps({"hashes": {}}))
            etoro = root / "data" / "raw" / "etoro" / "20261016T190421Z"
            etoro.mkdir(parents=True)
            (etoro / "instruments.json").write_text(
                json.dumps(
                    {
                        "InstrumentDisplayDatas": [
                            {"SymbolFull": "T01", "InstrumentTypeID": 5, "ExchangeID": 4}
                        ]
                    }
                )
            )
            saved = (full.ROOT, full.E10, full.OUT, core.load_panel)
            full.ROOT, full.E10, full.OUT = root, e10, e10 / "results"
            core.load_panel = lambda: (dates, tickers, {t: i for i, t in enumerate(tickers)}, m)
            try:
                self.assertEqual(full.main(), 0)
                out = json.loads((e10 / "results" / "RESULT.json").read_text())
                self.assertEqual(out["trades"] + sum(out["skipped"].values()), 60)
                self.assertIn("G6_account_A_beats_start_and_shadow", out["gates"])
                self.assertIn("20", out["classes"]["RAISE"]["drift_curve_excess"])
                for name in ("A", "A_shadow", "B", "B_shadow"):
                    self.assertGreater(out["accounts"][name]["trades_taken"], 0)
                curves = pd.read_csv(e10 / "results" / "accounts.csv.gz")
                self.assertEqual(list(curves.columns), ["date", "A", "A_shadow", "B", "B_shadow"])
                with self.assertRaises(SystemExit):
                    full.main()
            finally:
                full.ROOT, full.E10, full.OUT, core.load_panel = saved


if __name__ == "__main__":
    unittest.main()
