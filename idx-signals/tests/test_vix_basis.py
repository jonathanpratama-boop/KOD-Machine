"""VIX_BASIS_v1 on synthetic prices: front selection, daily roll, the lagged short trade, costs, continuation, gates."""

import importlib.util
import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "research/VIX_BASIS_v1"
spec = importlib.util.spec_from_file_location("vix_basis", HERE / "vix_basis.py")
vb = importlib.util.module_from_spec(spec)
sys.modules["vix_basis"] = vb
spec.loader.exec_module(vb)


def make(n=40, f1=20.0, f2=21.0, vix=18.0):
    """Two contracts: A expires at session 15, B at session 39; flat prices unless changed by the test."""
    days = pd.bdate_range("2010-01-04", periods=n)
    settle = pd.DataFrame({"A": f1, "B": f2}, index=days)
    settle.loc[days[16] :, "A"] = np.nan  # A has expired
    expiry = pd.Series({"A": days[15], "B": days[39]})
    data = {
        "settle": settle,
        "expiry": expiry,
        "vix": pd.Series(vix, index=days),
        "sessions": days,
        "spx": pd.Series(1000.0, index=days),
        "qa": {},
    }
    return data, days


class Front(unittest.TestCase):
    def test_front_needs_min_days_and_roll_is_per_trading_day(self):
        data, days = make()
        fr = vb.front_and_roll(data, 10)
        self.assertEqual(fr.contract[days[0]], "A")  # 15 sessions left
        self.assertEqual(fr.days[days[0]], 15)
        self.assertAlmostEqual(fr.roll[days[0]], (20 - 18) / 15)
        self.assertEqual(fr.contract[days[6]], "B")  # A has 9 left: too few
        self.assertEqual(fr.days[days[6]], 33)

    def test_signal_sides(self):
        fr = pd.DataFrame(
            {"roll": [0.2, 0.05, -0.2]}, index=pd.bdate_range("2010-01-04", periods=3)
        )
        self.assertEqual(vb.signal(fr, vb.PRIMARY).tolist(), [-1, 0, 0])
        self.assertEqual(
            vb.signal(fr, replace(vb.PRIMARY, side="both")).tolist(), [-1, 0, 1]
        )
        self.assertEqual(
            vb.signal(fr, replace(vb.PRIMARY, side="always_short")).tolist(),
            [-1, -1, -1],
        )


class Simulate(unittest.TestCase):
    def test_one_lagged_short_trade_with_costs(self):
        data, days = make(
            vix=19.5
        )  # roll = (21 - 19.5)/33 < 0.10 on B; A: (20-19.5)/15 < 0.10: no signal
        data["vix"].iloc[:] = 30.0  # backwardation everywhere: never short
        data["vix"].iloc[6] = 15.0  # one contango day on B: roll = (21-15)/33 = 0.18
        data["settle"].loc[days[7] :, "B"] = 20.0  # fall after the entry session
        rule = replace(vb.PRIMARY, weight=0.5)
        fr = vb.front_and_roll(data, rule.min_days)
        tr, eq = vb.simulate(data, fr, rule, str(days[0].date()), str(days[-1].date()))
        self.assertEqual(len(tr), 1)
        t = tr.iloc[0]
        self.assertEqual(
            t.entry_date, days[7]
        )  # decided on day 6, entered at day 7's settlement
        self.assertEqual(t.exit_date, days[12])  # 5 sessions later
        self.assertEqual(t.entry, 20.0)  # day 7's settlement (already 20)
        net = (0.0 - 2 * rule.cost_points) / 20.0
        self.assertAlmostEqual(t.net_return, net)
        self.assertAlmostEqual(eq.equity.iloc[-1], vb.START_EQUITY * (1 + 0.5 * net))

    def test_profit_on_a_fall_and_continuation_costs_nothing(self):
        data, days = make()
        data["vix"].iloc[:] = 30.0
        data["vix"].iloc[6:13] = 15.0  # contango on days 6..12
        data["settle"].loc[days[10] :, "B"] = 19.0
        rule = replace(vb.PRIMARY, weight=1.0)
        fr = vb.front_and_roll(data, rule.min_days)
        tr, _ = vb.simulate(data, fr, rule, str(days[0].date()), str(days[-1].date()))
        self.assertEqual(len(tr), 2)
        first, second = tr.iloc[0], tr.iloc[1]
        self.assertTrue(
            first.continued
        )  # day 11's decision is still short in B: no exit cost
        self.assertTrue(first.entry_paid)
        self.assertFalse(first.exit_paid)
        self.assertAlmostEqual(first.net_return, (21 - 19) / 21 - rule.cost_points / 21)
        self.assertFalse(second.entry_paid)
        self.assertTrue(second.exit_paid)

    def test_window_end_closes_with_cost_and_missing_price_delays_exit(self):
        data, days = make()
        data["vix"].iloc[:] = 15.0  # always contango
        data["settle"].loc[days[12], "B"] = (
            np.nan
        )  # no settlement on the scheduled exit day of the first trade
        rule = replace(vb.PRIMARY, weight=0.2)
        fr = vb.front_and_roll(data, rule.min_days)
        tr, eq = vb.simulate(data, fr, rule, str(days[6].date()), str(days[20].date()))
        self.assertTrue(tr.iloc[-1].get("closed_at_window_end", False))
        self.assertTrue((pd.to_datetime(tr.exit_date) != days[12]).all())
        self.assertFalse(eq.in_position.iloc[-1])


class MoreSimulate(unittest.TestCase):
    def run_rule(self, data, days, rule, a=0, b=-1):
        fr = vb.front_and_roll(data, rule.min_days)
        return vb.simulate(data, fr, rule, str(days[a].date()), str(days[b].date()))

    def test_lag_two_enters_two_sessions_after_the_decision(self):
        data, days = make()
        data["vix"].iloc[:] = 30.0
        data["vix"].iloc[6] = 15.0
        tr, _ = self.run_rule(data, days, vb.replace(vb.PRIMARY, lag=2))
        self.assertEqual(tr.iloc[0].entry_date, days[8])

    def test_both_sides_flips_to_long_in_backwardation_with_costs(self):
        data, days = make()
        data["vix"].iloc[:] = 21.0  # roll 0 on B: flat
        data["vix"].iloc[6] = 15.0  # contango: short
        data["vix"].iloc[11] = (
            27.0  # backwardation on the decision before the short's exit: long
        )
        tr, _ = self.run_rule(data, days, vb.replace(vb.PRIMARY, side="both"))
        self.assertEqual(tr.side.tolist()[:2], [-1, 1])
        self.assertTrue(tr.iloc[0].exit_paid and tr.iloc[1].entry_paid)
        self.assertNotEqual(tr.iloc[0].position, tr.iloc[1].position)

    def test_always_short_pays_both_sides_when_the_front_changes(self):
        data, days = make(n=40)
        tr, _ = self.run_rule(data, days, vb.replace(vb.PRIMARY, side="always_short"))
        a_to_b = tr[(tr.contract == "A") & tr.exit_paid]
        self.assertEqual(
            len(a_to_b), 1
        )  # A is closed with a cost when the decision names B
        first_b = tr[tr.contract == "B"].iloc[0]
        self.assertTrue(first_b.entry_paid)
        self.assertTrue(
            (pd.to_datetime(tr[tr.contract == "A"].exit_date) <= days[15]).all()
        )  # never past expiry

    def test_whole_contracts_round_and_skip_zero(self):
        rule = vb.replace(vb.PRIMARY, multiplier=100.0)
        self.assertEqual(vb.contracts(rule, 10_000.0, 20.0), 1)
        self.assertEqual(
            vb.contracts(rule, 10_000.0, 45.0), 0
        )  # 0.44 contracts rounds to 0: no position
        self.assertIsNone(vb.contracts(vb.PRIMARY, 10_000.0, 45.0))
        self.assertEqual(
            vb._notional(rule, 10_000.0, 1, 21.0), 2100.0
        )  # notional at the fill price
        self.assertAlmostEqual(vb._notional(vb.PRIMARY, 10_000.0, None, 45.0), 2000.0)

    def test_positions_aggregate_continuations(self):
        data, days = make()
        data["vix"].iloc[:] = 30.0
        data["vix"].iloc[6:13] = 15.0
        data["settle"].loc[days[10] :, "B"] = 19.0
        rule = vb.replace(vb.PRIMARY, weight=1.0)
        tr, eq = self.run_rule(data, days, rule)
        out = vb.summarize(tr, eq, rule)
        self.assertEqual(out["segments"], 2)
        self.assertEqual(out["trades"], 1)  # one position of two segments
        want = (
            tr.pnl.sum() / tr.notional.iloc[0]
        )  # the P&L over the notional it opened with, not compounded
        self.assertAlmostEqual(out["mean_net"], want)
        self.assertAlmostEqual(out["pnl_total"], tr.pnl.sum())
        self.assertAlmostEqual(eq.equity.iloc[-1], vb.START_EQUITY + tr.pnl.sum())


class Fixes(unittest.TestCase):
    def run_rule(self, data, days, rule, a=0, b=-1):
        fr = vb.front_and_roll(data, rule.min_days)
        return vb.simulate(data, fr, rule, str(days[a].date()), str(days[b].date()))

    def test_closures_count_only_before_they_are_known(self):
        data, days = make()
        closure, known = days[10], days[4]
        data["settle"] = data["settle"].drop(index=closure)
        data["vix"] = data["vix"].drop(index=closure)
        data["sessions"] = data["sessions"].drop(closure)
        data["closures"] = {closure: known}
        fr = vb.front_and_roll(data, 10)
        self.assertEqual(
            fr.days[days[0]], 15
        )  # expected session still counted before it is known
        self.assertEqual(
            fr.days[days[4]], 10
        )  # known: not counted (A has 11 sessions left to 15, minus the closure)
        self.assertEqual(fr.contract[days[5]], "B")

    def test_no_entry_on_the_last_session_of_the_window(self):
        data, days = make()
        data["vix"].iloc[:] = 30.0
        data["vix"].iloc[18] = (
            15.0  # decision on day 18, entry would be day 19 = the window's last session
        )
        tr, _ = self.run_rule(data, days, vb.PRIMARY, 0, 19)
        self.assertEqual(len(tr), 0)

    def test_whole_contracts_pay_for_a_change_in_count_and_close_at_zero(self):
        rule = vb.replace(vb.PRIMARY, multiplier=100.0, weight=0.2)
        data, days = make()
        data["vix"].iloc[:] = 2.0  # always contango
        data["settle"].loc[days[6] :, "B"] = 10.0
        data["settle"].loc[days[11] :, "B"] = (
            5.0  # the price halves: 2 contracts become 4 at the continuation
        )
        tr, _ = self.run_rule(
            data, days, rule, 6, 30
        )  # day 6: B is the front (A has 9 sessions left)
        first = tr.iloc[0]
        self.assertEqual(
            first.contracts, 2
        )  # sized at the decision-day settlement 10.0: 0.2 x 10000 / 1000
        self.assertTrue(first.continued)
        self.assertEqual(tr.iloc[1].contracts, 4)
        self.assertAlmostEqual(first.resize_cost_usd, 2 * rule.cost_points * 100)
        data2, days2 = make()
        data2["vix"].iloc[:] = 2.0
        data2["settle"].loc[days2[6] :, "B"] = 10.0
        data2["settle"].loc[days2[11] :, "B"] = (
            40.0  # the short loses; 0.2 x equity / 4000 rounds to 0 contracts
        )
        tr2, _ = self.run_rule(data2, days2, rule, 6, 30)
        self.assertFalse(tr2.iloc[0].continued)
        self.assertTrue(tr2.iloc[0].exit_paid)

    def test_good_friday_2015_is_not_a_business_day(self):
        self.assertIn(pd.Timestamp("2015-04-03"), vb.NON_BUSINESS_DAYS)


class Expiry(unittest.TestCase):
    def test_rule_with_good_friday_shift(self):
        self.assertEqual(str(vb.rule_expiry("2015-03").date()), "2015-03-18")
        self.assertEqual(
            str(vb.rule_expiry("2008-02").date()), "2008-02-19"
        )  # 21 Mar 2008 was Good Friday
        self.assertEqual(str(vb.rule_expiry("2022-03").date()), "2022-03-15")
        self.assertEqual(
            str(vb.rule_expiry("2024-01").date()), vb.SEALED_EXPIRIES["2024-01"]
        )
        self.assertEqual(
            str(vb.rule_expiry("2024-02").date()), vb.SEALED_EXPIRIES["2024-02"]
        )
        self.assertEqual(str(vb.good_friday(2020)), "2020-04-10")


class Gates(unittest.TestCase):
    def res(self, **kw):
        base = {
            "trades": 60,
            "end_equity": 12000.0,
            "pnl_without_top5": 100.0,
            "mean_net": 0.01,
            "boot_net": {"lower_one_sided_95": 0.001},
            "max_drawdown_daily": -0.2,
            "years_positive": 7,
        }
        base.update(kw)
        ok = {"end_equity": 11000.0}
        return {
            "primary": base,
            "S1_double_costs": dict(ok),
            "S2_lag_2": dict(ok),
            "N1_threshold_0.05": dict(ok),
            "N2_threshold_0.15": dict(ok),
        }

    def test_discovery_and_validation(self):
        g = vb.discovery_gates(self.res())
        self.assertTrue(all(v == "PASS" for v in g.values()))
        v = vb.validation_gates(self.res())
        self.assertEqual(vb.verdict(g, v), "CONFIRMED")
        self.assertEqual(vb.verdict(g, {**v, "V3_drawdown": "FAIL"}), "NOT_CONFIRMED")
        self.assertEqual(
            vb.verdict(vb.discovery_gates(self.res(trades=10)), None), "INCONCLUSIVE"
        )
        self.assertEqual(
            vb.verdict(vb.discovery_gates(self.res(max_drawdown_daily=-0.4)), None),
            "FAIL",
        )
        r = self.res()
        r["N2_threshold_0.15"]["end_equity"] = 9000.0
        self.assertEqual(vb.discovery_gates(r)["D5_not_brittle"], "FAIL")


class GateFailures(unittest.TestCase):
    def base(self, **kw):
        r = Gates.res(Gates(), **kw)
        return r

    def test_each_discovery_and_validation_gate_fails_safe(self):
        cases = {
            "D1_account": {"pnl_without_top5": None},
            "D2_net": {"boot_net": {"lower_one_sided_95": None}},
            "D6_years": {"years_positive": 5},
        }
        for gate, kw in cases.items():
            self.assertEqual(vb.discovery_gates(self.base(**kw))[gate], "FAIL", gate)
        r = self.base()
        r["S2_lag_2"]["end_equity"] = 9999.0
        self.assertEqual(vb.discovery_gates(r)["D4_stress"], "FAIL")
        self.assertEqual(
            vb.validation_gates(self.base(end_equity=9000.0))["V1_account"], "FAIL"
        )
        self.assertEqual(
            vb.validation_gates(self.base(mean_net=None))["V2_net"], "FAIL"
        )
        r = self.base()
        r["S1_double_costs"]["end_equity"] = 9000.0
        self.assertEqual(vb.validation_gates(r)["V4_costs"], "FAIL")


class Dates(unittest.TestCase):
    def test_both_date_formats(self):
        d = vb._dates(pd.Series(["06/09/2009", "2013-01-02"]))
        self.assertEqual([str(x.date()) for x in d], ["2009-06-09", "2013-01-02"])

    def test_windows_end_before_the_sealed_holdout(self):
        self.assertLess(vb.VALIDATION[1], vb.SEALED_FROM)
        self.assertLess(vb.DISCOVERY[1], vb.VALIDATION[0])


if __name__ == "__main__":
    unittest.main()
