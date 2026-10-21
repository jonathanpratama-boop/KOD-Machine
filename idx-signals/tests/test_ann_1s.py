import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import numpy as np

spec = importlib.util.spec_from_file_location("ann1s_run", Path(__file__).resolve().parents[1] / "research" / "BINANCE_ANN_1S" / "run.py")
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)
DAY = 86_400_000
T0 = 20_000 * DAY + 5 * 3_600_000


def ticks(T, jump=0.0, ramp_s=0.0, onset_s=0.0, step_ms=2000, seed=0):
    """Trades every `step_ms` from T-120 s to T+3900 s, alternating taker-sell (bid) and taker-buy (ask) with a 0.10 spread
    around a mid of 100 that rises by `jump` (a fraction) starting `onset_s` after T and taking `ramp_s` seconds."""
    rng = np.random.default_rng(seed)
    coarse = np.arange(T - 120_000, T + 3_900_000, step_ms)
    ts = np.union1d(coarse, np.arange(T - 10_000, T + 30_000, 100)) if step_ms > 100 else coarse   # fine near T
    frac = np.clip((ts - (T + onset_s * 1000)) / max(ramp_s * 1000, 1), 0, 1)
    mid = 100.0 * (1 + jump * frac) + rng.normal(0, 0.005, len(ts))
    m = np.arange(len(ts)) % 2 == 0                                   # True = seller-initiated = a trade at the bid
    price = np.where(m, mid - 0.05, mid + 0.05)
    return ts.astype(np.int64), price, m


class TickTests(unittest.TestCase):
    def test_reference_price_needs_three_fresh_trades(self):
        ts = np.array([1_000, 50_000, 70_000, 99_500, 100_000, 100_500])
        px = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])
        self.assertEqual(run.p0(ts, px, 100_000), 13.0)               # strictly before T: the trade at T is excluded
        self.assertIsNone(run.p0(ts, px, 200_000))                    # nothing in the last 60 s
        self.assertIsNone(run.p0(ts[:2], px[:2], 50_001))             # one trade only

    def test_price_at_and_first_trade(self):
        ts = np.array([100, 200, 300, 400])
        px = np.array([1.0, 2.0, 3.0, 4.0])
        m = np.array([True, False, True, False])
        self.assertEqual(run.price_at(ts, px, 250), 2.0)
        self.assertIsNone(run.price_at(ts, px, 50))
        self.assertEqual(run.first_trade(ts, px, m, 150, 1000, True), (200, 2.0))      # a taker buy
        self.assertEqual(run.first_trade(ts, px, m, 150, 1000, False), (300, 3.0))     # a taker sell
        self.assertIsNone(run.first_trade(ts, px, m, 150, 40, False))                  # outside the wait
        self.assertIsNone(run.first_trade(ts, px, m, 401, 1000, True))

    def test_capture_buys_the_ask_and_sells_the_bid(self):
        T = T0
        ts, px, m = ticks(T)                                          # flat market: the round trip pays the spread
        g = run.capture(ts, px, m, T, 2, 300)
        self.assertAlmostEqual(g, (100 - 0.05) / (100 + 0.05) - 1, delta=2e-4)
        self.assertLess(g, 0)

    def test_a_slow_jump_is_partly_capturable_and_a_fast_one_is_not(self):
        T = T0
        slow = ticks(T, jump=0.03, ramp_s=40)                          # the move takes 40 s
        fast = ticks(T, jump=0.03, ramp_s=0.5, onset_s=0.1, step_ms=100)   # done within the first second
        self.assertGreater(run.capture(slow[0], slow[1], slow[2], T, 2, 300), 0.025)
        self.assertLess(run.capture(fast[0], fast[1], fast[2], T, 2, 300), 0.001)
        self.assertGreater(run.capture(fast[0], fast[1], fast[2], T, 0.0, 300), 0.025)  # an instant order would catch it

    def test_half_move_time_and_spread(self):
        T = T0
        ts, px, m = ticks(T, jump=0.04, ramp_s=20)
        base = run.p0(ts, px, T)
        r60 = run.price_at(ts, px, T + 60_000) / base - 1
        t_half = run.half_move_time(ts, px, T, base, r60)
        self.assertAlmostEqual(t_half, 10.0, delta=2.5)
        sp = run.spread(ts, px, m, T - 60_000, T)
        self.assertAlmostEqual(sp, 0.001, delta=2e-4)                  # 0.10 on a mid of 100
        self.assertIsNone(run.spread(ts[:1], px[:1], m[:1], ts[0], ts[0] + 1))


class EndToEnd(unittest.TestCase):
    def stage(self, jump, ramp_s, onset_s, n=60):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        (tmp / "research" / "BINANCE_ANN_1M" / "results").mkdir(parents=True)
        (tmp / "research" / "BINANCE_ANN_1M" / "feasibility").mkdir()
        (tmp / "research" / "BINANCE_ANN_1S" / "ticks").mkdir(parents=True)
        for f in ("results/events.csv", "feasibility/events.csv"):
            (tmp / "research" / "BINANCE_ANN_1M" / f).write_text("x\n1\n")
        series, parts, sizes, row = [], [], [], 0
        for i in range(n):
            t_event = T0 + i * DAY
            for kind in ("event", "placebo"):
                T = t_event - (DAY if kind == "placebo" else 0)
                a = ticks(T, jump=jump if kind == "event" else 0.0, ramp_s=ramp_s, onset_s=onset_s, seed=i)
                parts.append(a)
                sizes.append(len(a[0]))
                series.append({"row": row, "event_key": f"{i}|T{i}", "token": f"T{i}", "pair": f"T{i}USDT", "kind": kind, "T": int(T),
                               "t_event_ms": int(t_event), "trades": len(a[0]), "zips": []})
                row += 1
        npz = tmp / "research" / "BINANCE_ANN_1S" / "ticks" / "ticks.npz"
        np.savez_compressed(npz, ts=np.concatenate([p[0] for p in parts]), price=np.concatenate([p[1] for p in parts]),
                            qty=np.zeros(sum(sizes)), m=np.concatenate([p[2] for p in parts]), index=np.concatenate([[0], np.cumsum(sizes)]))
        sh = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
        man = {"series": series, "npz": {"path": "research/BINANCE_ANN_1S/ticks/ticks.npz", "sha256": sh(npz), "bytes": 0},
               "events_csv_sha256": sh(tmp / "research/BINANCE_ANN_1M/results/events.csv"),
               "feasibility_events_sha256": sh(tmp / "research/BINANCE_ANN_1M/feasibility/events.csv")}
        (tmp / "research" / "BINANCE_ANN_1S" / "ticks" / "MANIFEST.json").write_text(json.dumps(man))
        for p in (mock.patch.object(run, "HERE", tmp / "research" / "BINANCE_ANN_1S"), mock.patch.object(run, "ROOT", tmp),
                  mock.patch.object(run, "OUT", tmp / "research" / "BINANCE_ANN_1S" / "results"), mock.patch.object(run, "BOOT", 800)):
            p.start()
            self.addCleanup(p.stop)
        return tmp / "research" / "BINANCE_ANN_1S" / "results"

    def go(self, *a, **kw):
        out = self.stage(*a, **kw)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(), 0)
        return out, json.loads((out / "RESULT.json").read_text())

    def test_a_move_that_takes_seconds_passes(self):
        out, res = self.go(jump=0.03, ramp_s=40, onset_s=0.0)
        self.assertEqual(res["verdict"], "PASS", res["gates"])
        self.assertGreater(res["reaction"]["R_60"], 0.029)
        self.assertLess(res["reaction"]["share_done_by_1s"], 0.1)
        self.assertEqual(res["events"]["usable_event"], 60)
        for name in ("RESULT.json", "grid.csv", "grid_placebo.csv", "curve.csv", "events.csv"):
            self.assertTrue((out / name).exists(), name)
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            run.main()

    def test_a_move_inside_a_second_fails_with_that_reading(self):
        _, res = self.go(jump=0.03, ramp_s=0.5, onset_s=0.1)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertFalse(res["gates"]["G1_L2s_H300_net_t_ge_3"])
        self.assertGreaterEqual(res["reaction"]["share_done_by_1s"], 0.8)
        self.assertIn("within one second", res["reading"])

    def test_a_move_before_the_published_time_is_flagged_as_the_clock(self):
        _, res = self.go(jump=0.03, ramp_s=0.5, onset_s=-5.0)
        self.assertTrue(res["clock_flag"])
        self.assertIn("before the published time", res["reading"])


if __name__ == "__main__":
    unittest.main()
