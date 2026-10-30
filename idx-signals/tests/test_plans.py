"""Execution plans (research/E3): conditional entries and exits on closing prices."""

import unittest

import numpy as np

from idxsig.execution import (
    ENTRY_RULES,
    EXIT_RULES,
    LONG_EXITS,
    SHORT_EXITS,
    SIDES,
    STATUS,
    ExecConfig,
    Market,
    execute,
)
from idxsig.market import Fees
from tests.support import flat_market, rebuild

FEES = (1 - 0.0025) / (1 + 0.0015)


def one(m, ticker=0, signal=2, **cfg):
    out = execute(
        m,
        np.array([ticker]),
        np.array([signal]),
        ExecConfig(holding_days=cfg.pop("holding", 5), **cfg),
    )
    return {k: v[0] for k, v in out.items()}


def set_close(a, i, session, price):
    """Close of one session and the reference price of the next ones (no corporate action)."""
    a["close"][i, session] = price
    a["high"][i, session] = max(price, a["prev"][i, session])
    a["low"][i, session] = min(price, a["prev"][i, session])
    a["prev"][i, session + 1 :] = price
    a["close"][i, session + 1 :] = price
    a["high"][i, session + 1 :] = price * 1.01
    a["low"][i, session + 1 :] = price * 0.99


class PlanTests(unittest.TestCase):
    def test_rule_sets_are_fixed(self):
        self.assertEqual(ENTRY_RULES, ("fixed", "confirm", "pullback", "unlock"))
        self.assertEqual(EXIT_RULES, ("fixed", "stop_ref", "first_down", "stop_high", "first_up"))
        self.assertEqual(LONG_EXITS, ("fixed", "stop_ref", "first_down"))
        self.assertEqual(SHORT_EXITS, ("fixed", "stop_high", "first_up"))
        self.assertEqual(SIDES, ("long", "short"))

    def test_default_plan_is_the_original_model(self):
        t, d, a = flat_market(price=3000.0)
        base = one(rebuild(t, d, a))
        explicit = one(rebuild(t, d, a), entry_rule="fixed", exit_rule="fixed")
        self.assertEqual(base["entry_idx"], 3)
        self.assertEqual(base["exit_idx"], 8)
        for key in ("status", "entry_idx", "exit_idx", "net_return"):
            self.assertEqual(base[key], explicit[key])
        self.assertEqual(
            ExecConfig(holding_days=5).plan,
            {
                "entry_rule": "fixed",
                "entry_window": 1,
                "exit_rule": "fixed",
                "holding_days": 5,
                "side": "long",
            },
        )

    def test_confirm_waits_for_a_close_above_the_signal_close(self):
        t, d, a = flat_market(price=1000.0)
        set_close(a, 0, 2, 1100.0)  # signal close
        set_close(a, 0, 3, 1100.0)  # flat: not above
        set_close(a, 0, 4, 1150.0)  # above: enter here
        r = one(rebuild(t, d, a), entry_rule="confirm", entry_window=3)
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["entry_idx"], 4)
        self.assertEqual(r["entry_price"], 1150.0)
        self.assertEqual(r["exit_idx"], 9)
        none = one(rebuild(t, d, a), entry_rule="confirm", entry_window=1)
        self.assertEqual(STATUS[none["status"]], "SKIP_NO_TRIGGER")
        self.assertEqual(none["entry_idx"], -1)

    def test_confirm_refuses_a_locked_close_and_takes_the_next_one(self):
        t, d, a = flat_market(price=1000.0)
        set_close(a, 0, 2, 1100.0)
        set_close(a, 0, 3, 1375.0)  # 1100 * 1.25: locked at ARA (2024 regular band)
        set_close(a, 0, 4, 1400.0)  # unlocked, above the signal close
        r = one(rebuild(t, d, a), entry_rule="confirm", entry_window=3)
        self.assertEqual(r["entry_idx"], 4)
        fixed = one(rebuild(t, d, a))
        self.assertEqual(STATUS[fixed["status"]], "SKIP_ARA_LOCK")

    def test_pullback_waits_for_a_close_below_the_signal_close(self):
        t, d, a = flat_market(price=1000.0)
        set_close(a, 0, 2, 1100.0)
        set_close(a, 0, 3, 1150.0)
        set_close(a, 0, 4, 1050.0)  # below the signal close
        r = one(rebuild(t, d, a), entry_rule="pullback", entry_window=3)
        self.assertEqual(r["entry_idx"], 4)
        self.assertEqual(r["entry_price"], 1050.0)

    def test_unlock_enters_at_the_first_unlocked_close(self):
        t, d, a = flat_market(price=1000.0)
        set_close(a, 0, 2, 1250.0)  # locked
        set_close(a, 0, 3, 1560.0)  # 1250 * 1.25 floored to tick 5: locked again
        set_close(a, 0, 4, 1500.0)  # unlocked
        r = one(rebuild(t, d, a), entry_rule="unlock", entry_window=3)
        self.assertEqual(r["entry_idx"], 4)
        self.assertEqual(
            STATUS[one(rebuild(t, d, a), entry_rule="unlock", entry_window=1)["status"]],
            "SKIP_NO_TRIGGER",
        )

    def test_conditional_entry_past_the_data_is_no_entry_session(self):
        t, d, a = flat_market(n_sessions=4)
        r = one(rebuild(t, d, a), signal=3, entry_rule="unlock", entry_window=3)
        self.assertEqual(STATUS[r["status"]], "SKIP_NO_ENTRY_SESSION")

    def test_stop_ref_exits_at_the_first_close_at_or_below_the_signal_reference(self):
        t, d, a = flat_market(price=1000.0)
        set_close(a, 0, 2, 1200.0)  # signal: reference 1000, close 1200
        set_close(a, 0, 5, 1000.0)  # back at the reference
        r = one(rebuild(t, d, a), exit_rule="stop_ref")
        self.assertEqual(r["entry_idx"], 3)
        self.assertEqual(r["exit_idx"], 5)
        self.assertEqual(r["rolled_sessions"], 0)
        self.assertAlmostEqual(r["net_return"], (1000.0 / 1200.0) * FEES - 1)
        fixed = one(rebuild(t, d, a))
        self.assertEqual(fixed["exit_idx"], 8)

    def test_stop_ref_rolls_while_the_stop_session_is_locked_at_arb(self):
        t, d, a = flat_market(price=1000.0)
        set_close(a, 0, 2, 1200.0)
        set_close(a, 0, 5, 900.0)  # 1200 * 0.75: locked at ARB, no sale
        set_close(a, 0, 6, 950.0)
        r = one(rebuild(t, d, a), exit_rule="stop_ref")
        self.assertEqual(r["exit_idx"], 6)
        self.assertEqual(r["rolled_sessions"], 1)

    def test_stop_ref_compares_on_the_reference_chain_across_a_split(self):
        t, d, a = flat_market(price=5000.0)
        set_close(a, 0, 2, 6000.0)  # reference 5000, close 6000
        a["prev"][0, 5] = 1200.0  # 1:5 split effective session 5: 6000 -> 1200 is not a fall
        a["close"][0, 5:] = 1200.0
        a["prev"][0, 6:] = 1200.0
        a["high"][0, 5:] = 1212.0
        a["low"][0, 5:] = 1188.0
        r = one(rebuild(t, d, a), exit_rule="stop_ref")
        self.assertEqual(r["exit_idx"], 8)  # no stop: the fixed exit

    def test_first_down_exits_on_the_first_down_close(self):
        t, d, a = flat_market(price=1000.0)
        set_close(a, 0, 2, 1200.0)
        set_close(a, 0, 4, 1300.0)
        set_close(a, 0, 6, 1250.0)  # first close below its reference after the entry
        r = one(rebuild(t, d, a), exit_rule="first_down")
        self.assertEqual(r["exit_idx"], 6)
        self.assertAlmostEqual(r["net_return"], (1250.0 / 1200.0) * FEES - 1)

    def test_conditional_exit_never_runs_past_the_fixed_exit(self):
        t, d, a = flat_market(price=1000.0)
        set_close(a, 0, 2, 1200.0)
        set_close(a, 0, 9, 500.0)  # after the fixed exit
        r = one(rebuild(t, d, a), exit_rule="stop_ref", holding=3)
        self.assertEqual(r["exit_idx"], 6)

    def test_plan_arguments_are_checked(self):
        t, d, a = flat_market()
        with self.assertRaises(ValueError):
            one(
                rebuild(t, d, a), entry_rule="unlock", entry_price="open"
            )  # no locks at an open entry
        with self.assertRaises(ValueError):
            one(rebuild(t, d, a), entry_rule="confirm", entry_window=0)
        with self.assertRaises(ValueError):
            one(rebuild(t, d, a), entry_rule="never")
        with self.assertRaises(ValueError):
            one(rebuild(t, d, a), exit_rule="stop_high")  # a short exit on a long
        with self.assertRaises(ValueError):
            one(rebuild(t, d, a), side="short")  # closing-auction entries
        with self.assertRaises(ValueError):
            one(rebuild(t, d, a), side="sideways")


def open_market(price=10.0, n_sessions=20):
    """A market without price limits (US / crypto shape): opens equal to closes, one price."""
    t, d, a = flat_market(price=price, volume=1e6, n_sessions=n_sessions)
    a["open"] = np.full(a["close"].shape, price)
    return t, d, a


def build_open(t, d, a) -> Market:
    return Market.build(
        t,
        d,
        a["close"],
        a["prev"],
        a["high"],
        a["low"],
        a["volume"],
        a["value"],
        a["present"],
        a.get("listed_shares"),
        opens=a["open"],
        price_limits=False,
    )


def set_bar(a, i, session, open_=None, close=None, high=None, low=None):
    """One session's bar; the next sessions' reference follows the close."""
    if open_ is not None:
        a["open"][i, session] = open_
    if close is not None:
        a["close"][i, session] = close
        a["prev"][i, session + 1 :] = close
        a["close"][i, session + 1 :] = close
        a["open"][i, session + 1 :] = close
    c = a["close"][i, session]
    a["high"][i, session] = max(high if high is not None else c, c, a["open"][i, session])
    a["low"][i, session] = min(low if low is not None else c, c, a["open"][i, session])
    a["high"][i, session + 1 :] = a["close"][i, session + 1 :]
    a["low"][i, session + 1 :] = a["close"][i, session + 1 :]


CRYPTO_COSTS = dict(
    lot_size=1,
    entry_price="open",
    notional=5000.0,
    fees=Fees(0.001, 0.001),
    cost_tiers=((float("inf"), 0.001),),
    ca_mode="adjusted",
)


def short(m, signal=2, holding=3, carry=0.0005, **cfg):
    out = execute(
        m,
        np.array([0]),
        np.array([signal]),
        ExecConfig(
            holding_days=holding, side="short", carry_per_session=carry, **{**CRYPTO_COSTS, **cfg}
        ),
    )
    return {k: v[0] for k, v in out.items()}


class ShortSideTests(unittest.TestCase):
    def test_short_sells_at_the_open_and_covers_at_the_close_with_carry(self):
        t, d, a = open_market()
        set_bar(a, 0, 6, close=9.0)  # the fade: the exit close (entry 3 + hold 3) is 10% lower
        r = short(build_open(t, d, a))
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual((r["entry_idx"], r["exit_idx"]), (3, 6))
        self.assertEqual(r["entry_price"], 10.0)
        self.assertAlmostEqual(r["gross_return"], 0.10)
        # sold at 10 less 0.1% fee and 0.1% slippage, bought back at 9 plus the same, 3 sessions of carry
        self.assertAlmostEqual(r["net_return"], (1 - 0.002) - 0.9 * (1 + 0.002) - 3 * 0.0005)
        up = short(build_open(*open_market()))  # flat: fees and carry only
        self.assertAlmostEqual(up["net_return"], (1 - 0.002) - (1 + 0.002) - 3 * 0.0005)
        self.assertAlmostEqual(short(build_open(*open_market()), carry=0.0)["net_return"], -0.004)

    def test_short_loses_more_than_its_notional_when_the_name_doubles(self):
        t, d, a = open_market()
        set_bar(a, 0, 6, close=22.0)
        r = short(build_open(t, d, a))
        self.assertLess(r["net_return"], -1.0)  # uncapped: the squeeze risk the stop exists for

    def test_stop_high_covers_at_the_first_close_at_or_above_the_signal_high(self):
        t, d, a = open_market()
        set_bar(a, 0, 2, close=10.5, high=11.0)  # the signal session: closed 10.5, traded up to 11
        set_bar(a, 0, 4, close=11.2)
        r = short(build_open(t, d, a), holding=5, exit_rule="stop_high")
        self.assertEqual((r["entry_idx"], r["exit_idx"]), (3, 4))
        self.assertAlmostEqual(r["gross_return"], 1 - 11.2 / 10.5)
        below = open_market()
        set_bar(below[2], 0, 2, close=10.5, high=11.0)
        set_bar(below[2], 0, 4, close=10.9)  # above the close, below the high: no stop
        self.assertEqual(short(build_open(*below), holding=5, exit_rule="stop_high")["exit_idx"], 8)

    def test_first_up_covers_at_the_first_up_close(self):
        t, d, a = open_market()
        set_bar(a, 0, 4, close=9.8)
        set_bar(a, 0, 5, close=9.9)  # up versus its reference 9.8
        r = short(build_open(t, d, a), holding=5, exit_rule="first_up")
        self.assertEqual(r["exit_idx"], 5)

    def test_short_confirm_waits_for_an_open_below_the_signal_close_and_pullback_for_one_above(
        self,
    ):
        t, d, a = open_market()
        set_bar(a, 0, 2, close=10.5)
        a["open"][0, 3] = 10.6  # a gap up: not a confirmation for a short
        a["open"][0, 4] = 10.2  # a gap down: enter here
        m = build_open(t, d, a)
        r = short(m, entry_rule="confirm", entry_window=3)
        self.assertEqual((r["entry_idx"], r["entry_price"]), (4, 10.2))
        self.assertEqual(short(m, entry_rule="pullback", entry_window=3)["entry_idx"], 3)
        self.assertEqual(
            STATUS[short(m, entry_rule="confirm", entry_window=1)["status"]], "SKIP_NO_TRIGGER"
        )
        # the same conditions read the other way round for a long at the open
        long_ = execute(
            m,
            np.array([0]),
            np.array([2]),
            ExecConfig(holding_days=3, entry_rule="confirm", entry_window=3, **CRYPTO_COSTS),
        )
        self.assertEqual(long_["entry_idx"][0], 3)

    def test_short_rules_are_checked(self):
        m = build_open(*open_market())
        with self.assertRaises(ValueError):
            short(m, exit_rule="stop_ref")
        with self.assertRaises(ValueError):
            short(m, entry_rule="unlock")
        t, d, a = flat_market(price=1000.0)
        a["open"] = np.full(a["close"].shape, 1000.0)
        a["close"][0, 3] = 1250.0  # a bar locked at ARA: the short side is not modelled there
        a["high"][0, 3] = 1250.0
        a["prev"][0, 4:] = 1250.0
        with self.assertRaises(ValueError):
            execute(
                rebuild(t, d, a),
                np.array([0]),
                np.array([1]),
                ExecConfig(holding_days=3, side="short", entry_price="open"),
            )

    def test_liquidation_caps_the_loss_at_the_first_high_beyond_the_trigger(self):
        t, d, a = open_market()
        set_bar(a, 0, 5, close=19.0, high=20.5)  # the session's high crosses 2x the entry (10)
        set_bar(a, 0, 8, close=30.0)
        r = short(build_open(t, d, a), holding=5, liquidation=1.0)
        self.assertTrue(r["liquidated"])
        self.assertEqual((r["entry_idx"], r["exit_idx"]), (3, 5))
        self.assertEqual(r["exit_price"], 20.0)
        self.assertAlmostEqual(r["net_return"], (1 - 0.002) - 2.0 * (1 + 0.002) - 2 * 0.0005)
        self.assertEqual(r["rolled_sessions"], 0)
        free = short(
            build_open(t, d, a), holding=5
        )  # no cap: the loss runs to the close of session 8
        self.assertFalse(free["liquidated"])
        self.assertLess(free["net_return"], -2.0)
        below = open_market()
        set_bar(below[2], 0, 5, close=19.0, high=19.9)
        self.assertFalse(short(build_open(*below), holding=5, liquidation=1.0)["liquidated"])
        with self.assertRaises(ValueError):
            short(build_open(*open_market()), liquidation=0.0)

    def test_a_redenomination_sized_jump_is_not_a_trade(self):
        t, d, a = open_market()
        set_bar(a, 0, 5, close=120.0)  # x12 in a session: a redenomination, not a move
        r = short(build_open(t, d, a), holding=5, jump_ratio=10.0)
        self.assertEqual(STATUS[r["status"]], "EXCLUDED_DATA_JUMP")
        self.assertTrue(np.isnan(r["net_return"]))
        real = open_market()
        set_bar(real[2], 0, 5, close=30.0)  # x3: a real squeeze, scored
        self.assertEqual(
            STATUS[short(build_open(*real), holding=5, jump_ratio=10.0)["status"]], "EXITED"
        )
        long_ = execute(
            build_open(t, d, a),
            np.array([0]),
            np.array([2]),
            ExecConfig(holding_days=5, jump_ratio=10.0, **CRYPTO_COSTS),
        )
        self.assertEqual(STATUS[long_["status"][0]], "EXCLUDED_DATA_JUMP")
        self.assertEqual(STATUS[-1], "EXCLUDED_DATA_JUMP")  # appended, never inserted

    def test_split_scales_the_shares_owed(self):
        t, d, a = open_market(price=5000.0)
        a["prev"][0, 5] = 1000.0  # 1:5 split effective session 5
        a["close"][0, 5:] = 1000.0
        a["open"][0, 5:] = 1000.0
        a["prev"][0, 6:] = 1000.0
        a["high"][0, 5:] = 1000.0
        a["low"][0, 5:] = 1000.0
        r = short(build_open(t, d, a), ca_mode="exclude")
        self.assertEqual(r["share_factor"], 5.0)
        self.assertAlmostEqual(r["gross_return"], 0.0)


EDGE_BODY = """
def compute(m):
    out = np.zeros(m.shape)
    out[0, ::7] = 1.0
    out[1, 3::11] = 1.0
    return np.where(m.tradeable, out, np.nan)
"""


class HarnessPlanTests(unittest.TestCase):
    def test_holdout_matches_the_e1_protocol(self):
        import json
        from pathlib import Path

        from idxsig.backtest import HOLDOUT

        proto = json.loads(
            (Path(__file__).resolve().parents[1] / "research" / "E1" / "protocol.json").read_text()
        )
        self.assertEqual(list(HOLDOUT), proto["periods"]["holdout"])

    def test_detector_window_touching_the_holdout_is_refused_unless_final(self):
        from idxsig.backtest import HoldoutSealed, RunConfig
        from tests.rulekit import module_rule, with_rule
        from tests.support import random_walk_panel, run_synthetic

        df, meta = random_walk_panel(start="2023-10-02", n_sessions=120)  # runs into 2024
        rule = module_rule("EDGEH", EDGE_BODY)
        with with_rule(rule):
            with self.assertRaises(HoldoutSealed):
                run_synthetic(RunConfig("EDGEH", random_draws=5), df, meta)
            out = run_synthetic(RunConfig("EDGEH", random_draws=5, holdout_final=True), df, meta)
            self.assertTrue(out["summary"]["config"]["holdout_final"])
            before = run_synthetic(RunConfig("EDGEH", random_draws=5, end="2023-12-29"), df, meta)
            self.assertEqual(before["summary"]["universe"]["last_session"], "2023-12-29")
        run_synthetic(
            RunConfig("PLACEBO_COINFLIP", random_draws=5), df, meta
        )  # a placebo is not a detector

    def test_runs_carry_the_plan_and_a_rule_plan_is_the_default(self):
        import dataclasses

        from idxsig.backtest import RunConfig, plan_text
        from idxsig.results import render_report
        from tests.rulekit import module_rule, with_rule
        from tests.support import random_walk_panel, run_synthetic

        df, meta = random_walk_panel()
        frozen = {"entry_rule": "confirm", "entry_window": 3, "exit_rule": "stop_ref"}
        rule = dataclasses.replace(module_rule("PLANNED", EDGE_BODY), plan=frozen)
        with with_rule(rule):
            out = run_synthetic(RunConfig("PLANNED", random_draws=5), df, meta)
            plan = out["summary"]["execution"]["plan"]
            self.assertEqual(plan, {**frozen, "holding_days": 5, "side": "long"})
            self.assertEqual(out["summary"]["config"]["entry_rule"], "confirm")
            self.assertEqual(out["summary"]["execution"]["plan_text"], plan_text(plan))
            summary = {
                **out["summary"],
                "code": {"commit": "test", "dirty": False},
            }  # write_run adds this
            self.assertIn(
                "- Plan: buy at the first close in s+1..s+3 that is above",
                render_report("t", summary),
            )
            forced = run_synthetic(
                RunConfig("PLANNED", random_draws=5, entry_rule="fixed", exit_rule="fixed"),
                df,
                meta,
            )
            self.assertEqual(
                forced["summary"]["execution"]["plan"],
                {
                    "entry_rule": "fixed",
                    "entry_window": 1,
                    "exit_rule": "fixed",
                    "holding_days": 5,
                    "side": "long",
                },
            )
        plain = module_rule("PLAIN", EDGE_BODY)
        with with_rule(plain):
            out = run_synthetic(RunConfig("PLAIN", random_draws=5), df, meta)
            self.assertEqual(out["summary"]["execution"]["plan"]["entry_rule"], "fixed")


if __name__ == "__main__":
    unittest.main()
