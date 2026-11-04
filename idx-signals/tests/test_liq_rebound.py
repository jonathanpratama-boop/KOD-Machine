"""LIQ_REBOUND_v1 on synthetic fixtures: timing, no look-ahead, fills, stops, cash, accounting, gates (no market data)."""

import importlib.util
import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

_spec = importlib.util.spec_from_file_location(
    "rebound", Path(__file__).resolve().parents[1] / "research/LIQ_REBOUND_v1/rebound.py"
)
rb = importlib.util.module_from_spec(_spec)
sys.modules["rebound"] = rb  # dataclasses need the module registered
_spec.loader.exec_module(rb)

T0 = pd.Timestamp("2021-01-01 00:00")


def spot(n, price=100.0, seed=0):
    ix = pd.date_range(T0, periods=n, freq="h")
    rng = np.random.default_rng(seed)
    c = price * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    o = np.concatenate([[price], c[:-1]])
    return pd.DataFrame(
        {
            "open": o,
            "high": np.maximum(o, c) * 1.001,
            "low": np.minimum(o, c) * 0.999,
            "close": c,
            "volume": 1.0,
        },
        index=ix,
    )


def flat(n, price=100.0):
    ix = pd.date_range(T0, periods=n, freq="h")
    p = np.full(n, price)
    return pd.DataFrame(
        {"open": p, "high": p * 1.001, "low": p * 0.999, "close": p, "volume": 1.0}, index=ix
    )


def oi_series(n_hours, start=1000.0, seed=1):
    t = pd.date_range(T0, periods=n_hours * 12, freq="5min")
    rng = np.random.default_rng(seed)
    return pd.Series(start * np.exp(np.cumsum(rng.normal(0, 0.001, len(t)))), index=t)


SMALL = rb.Config(sigma_bars=48, sigma_min=40, oi_bars=48, oi_min=40, hold_h=5)


class Legs(unittest.TestCase):
    def test_signal_rows_do_not_change_when_the_future_is_removed(self):
        n = 400
        s, oi = spot(n), oi_series(n)
        full = rb.legs(s, oi, SMALL)
        cut_at = 300
        s2 = s.copy()
        s2.iloc[cut_at + 1 :] = np.nan
        T = s.index[cut_at] + pd.Timedelta(hours=1)
        part = rb.legs(s2, oi[oi.index <= T], SMALL)
        cols = ["lr", "sigma", "oi_now", "oi_prev", "doi", "q", "cascade", "droponly", "control"]
        pd.testing.assert_frame_equal(full.iloc[: cut_at + 1][cols], part.iloc[: cut_at + 1][cols])

    def test_open_interest_respects_the_publication_lag_and_the_gap_tolerance(self):
        s = spot(30)
        t = s.index[10] + pd.Timedelta(hours=1)  # signal time of bar 10
        oi = pd.Series(
            [1.0, 2.0, 3.0],
            index=[
                t - pd.Timedelta(minutes=20),
                t - pd.Timedelta(minutes=5),
                t - pd.Timedelta(minutes=4),
            ],
        )
        lg = rb.legs(s, oi, SMALL)
        self.assertEqual(lg.oi_now.iloc[10], 2.0)  # the T-4min row is not yet usable
        oi2 = pd.Series(
            [1.0], index=[t - pd.Timedelta(minutes=21)]
        )  # 16 minutes before T-5min: too stale
        self.assertTrue(np.isnan(rb.legs(s, oi2, SMALL).oi_now.iloc[10]))

    def test_cascade_needs_both_legs_and_droponly_is_the_complement_on_the_oi_leg(self):
        n = 400
        s = spot(n)
        s.iloc[300:, :4] *= 0.5  # a crash closing at bar 300
        oi = oi_series(n)
        crash_t = s.index[300] + pd.Timedelta(hours=1)
        oi_cut = oi.copy()
        oi_cut[oi_cut.index >= crash_t - pd.Timedelta(hours=10)] *= 0.5  # OI collapses with it
        oi_up = oi.copy()
        oi_up[oi_up.index >= crash_t - pd.Timedelta(hours=10)] *= (
            1.5  # OI rises instead: not deleveraging
        )
        a = rb.legs(s, oi_cut, SMALL)
        b = rb.legs(s, oi_up, SMALL)
        self.assertTrue(a.cascade.iloc[300] and not a.droponly.iloc[300])
        self.assertTrue(b.price_leg.iloc[300])
        self.assertFalse(b.cascade.iloc[300])
        self.assertTrue(b.droponly.iloc[300])


class Trades(unittest.TestCase):
    def test_entry_is_the_open_after_the_lag_and_exit_the_open_hold_bars_later(self):
        s = flat(50)
        s.loc[s.index[12], "open"] = 110.0  # entry bar for a signal at bar 10 (lag 1h: bar 10 + 2)
        s.loc[s.index[17], "open"] = 121.0  # exit bar: entry + 5
        tr = rb.simulate_trade(s, 10, (0.01, 0.02), SMALL)
        self.assertEqual((tr["entry_i"], tr["exit_i"], tr["exit_type"]), (12, 17, "TIME"))
        self.assertAlmostEqual(tr["gross"], 0.1)
        self.assertAlmostEqual(tr["net"], 0.99 * 0.98 * 1.1 - 1)

    def test_the_stop_fills_at_the_bar_low_never_at_the_level(self):
        s = flat(50)
        s.loc[s.index[14], "low"] = 50.0  # far below the 20% stop at 80
        tr = rb.simulate_trade(s, 10, (0, 0), SMALL)
        self.assertEqual((tr["exit_type"], tr["exit_i"], tr["exit_px"]), ("STOP_AT_LOW", 14, 50.0))

    def test_a_missing_exit_bar_rolls_to_the_next_valid_open_and_a_missing_entry_bar_skips(self):
        s = flat(50)
        s.iloc[17] = np.nan
        tr = rb.simulate_trade(s, 10, (0, 0), SMALL)
        self.assertEqual((tr["exit_i"], tr["exit_type"]), (18, "TIME_ROLLED"))
        s2 = flat(50)
        s2.iloc[12] = np.nan
        self.assertIsNone(rb.simulate_trade(s2, 10, (0, 0), SMALL))

    def test_no_trade_when_the_exit_falls_outside_the_data(self):
        self.assertIsNone(rb.simulate_trade(flat(16), 10, (0, 0), SMALL))


def data_with_flags(n, flags_by_sym, prices=None):
    out = {}
    for k, (sym, idx) in enumerate(flags_by_sym.items()):
        sp = (prices or {}).get(sym, flat(n))
        f = np.zeros(n, bool)
        f[idx] = True
        out[sym] = {
            "spot": sp,
            "legs": pd.DataFrame(
                {"cascade": f, "droponly": np.zeros(n, bool), "control": np.zeros(n, bool)},
                index=sp.index,
            ),
        }
    return out


class Account(unittest.TestCase):
    def test_sizes_debounces_and_balances(self):
        n = 120
        up = flat(n)
        up.loc[up.index[17], "open"] = 110.0  # A's exit open (signal 10 -> entry 12 -> exit 17)
        d = data_with_flags(n, {"A": [10, 11, 13], "B": [10]}, {"A": up})
        win = (T0, T0 + pd.Timedelta(hours=60))
        acct = rb.run_account(d, win, (0.0, 0.0), SMALL)
        self.assertEqual(rb.check_account(acct, SMALL), [])
        tr = pd.DataFrame(acct["trades"])
        self.assertEqual(
            sorted(tr.symbol), ["A", "B"]
        )  # A's signals at 11 and 13 are ignored while held
        a = tr[tr.symbol == "A"].iloc[0]
        self.assertAlmostEqual(a.notional, 5000.0)  # half of equity at the decision
        b = tr[tr.symbol == "B"].iloc[0]
        self.assertAlmostEqual(b.notional, 5000.0)  # the other half; never more than 100% invested
        self.assertAlmostEqual(acct["cash"], 10_000 + 500.0)

    def test_cash_caps_the_second_order_and_no_decision_after_the_window(self):
        n = 120
        d = data_with_flags(n, {"A": [10, 40], "B": [11]})
        cfg = replace(SMALL, size=0.8)
        acct = rb.run_account(d, (T0, T0 + pd.Timedelta(hours=30)), (0.0, 0.0), cfg)
        tr = pd.DataFrame(acct["trades"]).sort_values("entry_time")
        self.assertAlmostEqual(tr.notional.iloc[0], 8000.0)
        self.assertAlmostEqual(tr.notional.iloc[1], 2000.0)  # only the free cash
        self.assertEqual(len(tr), 2)  # A's signal at bar 40 is after the decision window
        self.assertTrue((acct["equity"].cash >= -1e-9).all())

    def test_a_signal_without_room_for_its_exit_is_skipped(self):
        n = 20
        d = data_with_flags(n, {"A": [15]})
        acct = rb.run_account(d, (T0, T0 + pd.Timedelta(hours=19)), (0.0, 0.0), SMALL)
        self.assertEqual(acct["trades"], [])
        self.assertEqual(acct["events"][0]["type"], "NO_ROOM_FOR_EXIT")

    def test_costs_reduce_the_proceeds_exactly(self):
        n = 60
        d = data_with_flags(n, {"A": [10]})
        acct = rb.run_account(d, (T0, T0 + pd.Timedelta(hours=30)), (0.0031, 0.0052), SMALL)
        t = acct["trades"][0]
        self.assertAlmostEqual(t["net"], (1 - 0.0031) * (1 - 0.0052) - 1)
        self.assertEqual(rb.check_account(acct, SMALL), [])


class Stats(unittest.TestCase):
    def test_episodes_split_on_seven_day_gaps(self):
        t = ["2022-01-01 00:00", "2022-01-03 00:00", "2022-01-20 00:00", "2022-01-02 00:00"]
        self.assertEqual(rb.episodes(t, 7), [0, 0, 1, 0])

    def test_cluster_bootstrap_brackets_the_mean(self):
        x = np.array([0.02, 0.03, -0.01, 0.05, 0.04, 0.01])
        b = rb.cluster_bootstrap(x, [0, 0, 1, 2, 3, 3])
        self.assertTrue(b["lower95"] <= b["mean"] <= b["upper95"])
        self.assertEqual(b["episodes"], 4)

    def test_gates_and_verdicts(self):
        acc = {
            "trades": 25,
            "end_equity": 11000,
            "start": 10000,
            "max_drawdown": -0.1,
            "pnl_without_top3": 100,
        }
        res = {
            "discovery": {
                "accounts": {"A2": acc, "S1_delay4h": acc, "S2": acc},
                "episodes": 9,
                "bootstrap_A2": {"mean": 0.02, "lower_one_sided_95": 0.001},
                "placebo_A2": {"p90": 0.01},
                "mechanism": {
                    "control_trades": 6,
                    "cascade_gross_mean": 0.03,
                    "control_gross_mean": 0.0,
                },
            },
            "screen_2023": {"accounts": {"A2": {"trades": 4, "mean_net": 0.01}}},
        }
        self.assertEqual(rb.gates(res)["verdict"], "PROMISING")
        res["discovery"]["mechanism"]["control_trades"] = 2
        self.assertEqual(rb.gates(res)["verdict"], "INCONCLUSIVE")
        res["discovery"]["mechanism"]["control_trades"] = 6
        res["discovery"]["bootstrap_A2"]["lower_one_sided_95"] = -0.001
        self.assertEqual(rb.gates(res)["verdict"], "FAIL")
        res["discovery"]["bootstrap_A2"]["lower_one_sided_95"] = 0.001
        res["screen_2023"]["accounts"]["A2"] = {"trades": 2}
        self.assertEqual(rb.gates(res)["verdict"], "PROMISING")
        res["discovery"]["episodes"] = 7
        self.assertEqual(rb.gates(res)["verdict"], "INCONCLUSIVE")


class Hygiene(unittest.TestCase):
    def test_zero_and_frozen_open_interest_rows_become_gaps(self):
        t = pd.date_range(T0, periods=8, freq="5min")
        s = pd.Series([10.0, 0.0, 11.0, 12.0, 12.0, 12.0, 12.0, 13.0], index=t)
        c = rb.clean_oi(s)
        self.assertEqual(
            c.tolist(), [10.0, 11.0, 12.0, 13.0]
        )  # zero dropped; 4-row frozen run keeps its first
        two = pd.Series([1.0, 2.0, 2.0, 3.0], index=t[:4])
        self.assertEqual(
            rb.clean_oi(two).tolist(), [1.0, 2.0, 2.0, 3.0]
        )  # a pair is not a frozen run

    def test_a_zero_row_cannot_fake_a_collapse(self):
        s = spot(30)
        t = s.index[10] + pd.Timedelta(hours=1)
        oi = pd.Series(
            [5.0, 0.0], index=[t - pd.Timedelta(minutes=30), t - pd.Timedelta(minutes=5)]
        )
        lg = rb.legs(s, rb.clean_oi(oi), SMALL)
        self.assertTrue(np.isnan(lg.doi.iloc[10]) or lg.doi.iloc[10] > -1)
        self.assertFalse(lg.cascade.iloc[10])

    def test_halted_placeholder_bars_are_missing(self):
        k = flat(5).assign(trades=[10, 0, 10, 10, 10])
        k.loc[k.index[3], "volume"] = 0.0
        h = rb.halted_to_nan(k)
        self.assertTrue(h.iloc[[1, 3]][["open", "close"]].isna().all().all())
        self.assertTrue(h.iloc[[0, 2, 4]].open.notna().all())

    def test_the_control_excludes_a_cascade_aftermath_but_keeps_earlier_hours(self):
        n = 300
        s = spot(n)
        lg = rb.legs(s, oi_series(n), SMALL)
        lg["valid"], lg["price_leg"] = True, True
        lg["cascade"] = False
        lg.loc[lg.index[200], "cascade"] = True
        lg["droponly"] = ~lg.cascade
        span = 1 + SMALL.entry_lag_h + SMALL.hold_h
        near = lg.cascade.astype(float).rolling(span + 1, min_periods=1).max().astype(bool)
        control = lg.droponly & ~near
        self.assertTrue(
            control.iloc[199]
        )  # before the cascade: a buyer without the OI leg would buy here
        self.assertFalse(control.iloc[200 + span])  # inside the aftermath window
        self.assertTrue(control.iloc[200 + span + 1])


class Consistency(unittest.TestCase):
    def test_a_missed_fill_keeps_the_coin_out_until_the_scheduled_exit(self):
        n = 80
        d = data_with_flags(n, {"A": [10, 11, 12, 20]})

        class AlwaysFail:
            calls = 0

            def random(self):
                AlwaysFail.calls += 1
                return 0.0 if AlwaysFail.calls == 1 else 1.0

        acct = rb.run_account(
            d, (T0, T0 + pd.Timedelta(hours=40)), (0.0, 0.0), SMALL, fail_rng=AlwaysFail()
        )
        # signal 10 misses at bar 12; the coin is out until bar 17, so 11 and 12 are ignored and 20 trades
        self.assertEqual([t["signal_i"] for t in acct["trades"]], [20])

    def test_debounced_waits_for_a_missing_entry_bar_like_the_account(self):
        s = flat(80)
        s.iloc[12] = np.nan
        flags = np.zeros(80, bool)
        flags[[10, 11, 12]] = True
        tr = rb.debounced(s, flags, np.arange(80), (0, 0), SMALL)
        self.assertEqual(
            [t["signal_i"] for t in tr], [12]
        )  # 11 is ignored while signal 10's order waits
        d = {"A": {"spot": s, "legs": pd.DataFrame({"cascade": flags}, index=s.index)}}
        acct = rb.run_account(d, (T0, T0 + pd.Timedelta(hours=40)), (0.0, 0.0), SMALL)
        self.assertEqual([t["signal_i"] for t in acct["trades"]], [12])

    def test_an_unresolved_position_fails_the_account_check(self):
        acct = {
            "equity": pd.DataFrame({"equity": [1.0], "invested": [0.0], "cash": [1.0]}),
            "events": [{"type": "UNRESOLVED"}],
            "trades": [],
            "cash": 1.0,
        }
        self.assertIn("unresolved position at the end of the data", rb.check_account(acct, SMALL))

    def test_the_frozen_k_must_follow_from_the_feasibility_counts(self):
        good = {"discovery": {"cascade_total": 31, "cascade_episodes": 9}}
        bad = {"discovery": {"cascade_total": 10, "cascade_episodes": 9}}
        self.assertEqual(rb.choose_k({"3.0": bad, "2.5": good, "2.0": good}), 2.5)
        self.assertEqual(rb.choose_k({"3.0": bad, "2.5": bad, "2.0": bad}), 2.0)


if __name__ == "__main__":
    unittest.main()
