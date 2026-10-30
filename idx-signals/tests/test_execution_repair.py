"""Adversarial execution inputs and versioned split-risk repair (synthetic only)."""

import hashlib
import copy
import json
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
import numpy as np
import pandas as pd
from idxsig.execution import ExecConfig, execute
from idxsig import contract as C, results
from tests.support import flat_market, rebuild
from tests.test_contract import market, closed, run


class ValidatedInputs(unittest.TestCase):
    def test_integer_fields_reject_coercion(self):
        for field in ("entry_lag", "holding_days", "entry_window", "lot_size"):
            for value in (True, False, 1.5, "2", float("nan")):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    ExecConfig(**{"holding_days": 1, field: value})
        ExecConfig(holding_days=0)
        ExecConfig(holding_days=np.int64(1))

    def test_numerical_limits(self):
        for field in ("notional", "max_participation"):
            for value in (0, -1, float("inf"), float("nan"), True):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    ExecConfig(holding_days=1, **{field: value})
        with self.assertRaises(ValueError):
            ExecConfig(holding_days=1, max_participation=1.1)
        for field in ("carry_per_session", "liquidation", "jump_ratio"):
            for value in (float("nan"), float("inf"), -float("inf"), True, "1"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    ExecConfig(holding_days=1, **{field: value})
        for field, value in (("liquidation", 0), ("jump_ratio", 1), ("jump_ratio", 0)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                ExecConfig(holding_days=1, **{field: value})
        credit = ExecConfig(
            holding_days=1, side="short", entry_price="open", carry_per_session=-0.001
        )
        self.assertTrue(np.isfinite(execute(market(), [0], [2], credit)["net_return"]).all())
        for tiers in (
            ((float("inf"), float("nan")),),
            ((5, 0.01), (1, 0.02)),
            ((-1, 0.01),),
            ((1, -0.01),),
            ((float("inf"), 0.01), (20, 0.02)),
        ):
            with self.subTest(tiers=tiers), self.assertRaises(ValueError):
                ExecConfig(holding_days=1, cost_tiers=tiers)
        ExecConfig(holding_days=1, cost_tiers=((1, 0.01), (float("inf"), 0.001)))

    def test_indices_never_wrap_or_truncate(self):
        m = rebuild(*flat_market())
        for ticks, signals in (
            ([-1], [2]),
            ([0], [-1]),
            ([0.5], [2]),
            ([0], [True]),
            ([0], [999]),
            ([[0]], [2]),
            ([0, 1], [2]),
        ):
            with self.subTest(ticks=ticks, signals=signals), self.assertRaises(ValueError):
                execute(m, ticks, signals, ExecConfig(holding_days=1))
        out = execute(m, [0], [2], ExecConfig(holding_days=0))
        self.assertEqual(out["entry_idx"][0], out["exit_idx"][0])

    def test_return_only_scoring_uses_explicit_capacity_opt_out(self):
        from idxsig.execution import STATUS
        from tests.test_paper_v4 import V4

        for value in ("false", 0, 1, None, float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ExecConfig(holding_days=1, capacity_check=value)
        m = market()
        bounded = ExecConfig(holding_days=1, notional=1e15, max_participation=1)
        self.assertEqual(STATUS[execute(m, [0], [2], bounded)["status"][0]], "SKIP_LIQUIDITY")
        counterfactual = replace(bounded, capacity_check=False)
        self.assertTrue(np.isfinite(execute(m, [0], [2], counterfactual)["net_return"]).all())
        case = V4()
        case.setUp()
        self.addCleanup(case.tearDown)
        decision = case._decision()
        up = int(round(decision["verified_price"]["close"] * 1.05))
        from idxsig import paper

        result = paper.score(decision, case._bars([up] * 7))
        self.assertFalse(result["execution"]["capacity_check"])
        self.assertIn("return-only counterfactual", result["execution"]["capacity_note"])
        self.assertTrue(np.isfinite(result["execution"]["paper_trade"]["net_return"]))

    def test_writer_checks_before_publication(self):
        good = dict(
            ticker="T",
            status="EXITED",
            signal_date="2024-01-01",
            entry_date="2024-01-02",
            exit_date="2024-01-02",
            entry_price=10,
            exit_price=11,
            shares=1,
        )
        for change in (
            {"shares": 0},
            {"entry_price": float("nan")},
            {"exit_date": ""},
            {"entry_date": "yesterday"},
            {"net_return": float("nan")},
            {"gross_return": float("inf")},
        ):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    results.write_run(
                        {
                            "summary": {"config": {"entry_lag": 1}},
                            "trades": pd.DataFrame([{**good, **change}]),
                        },
                        root=Path(tmp),
                        allow_dirty=True,
                        commit=False,
                    )
                self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertEqual(results.chronology_problems({"config": {"entry_lag": 1}}, [good]), [])
        self.assertEqual(
            results.chronology_problems(
                {"config": {"entry_lag": 1, "data_end_exit": "zero"}},
                [{**good, "status": "EXIT_DATA_END", "exit_price": 0}],
            ),
            [],
        )
        self.assertEqual(
            results.chronology_problems(
                {"config": {"entry_lag": 1}},
                [{**good, "status": "INCOMPLETE", "net_return": float("nan")}],
            ),
            [],
        )
        legacy = {k: v for k, v in good.items() if k not in ("shares", "entry_price", "exit_price")}
        self.assertEqual(results.chronology_problems({}, [legacy]), [])
        with (
            tempfile.TemporaryDirectory() as tmp,
            self.assertRaisesRegex(ValueError, "missing shares"),
        ):
            results.write_run(
                {"summary": {"config": {"entry_lag": 1}}, "trades": pd.DataFrame([legacy])},
                root=Path(tmp),
                allow_dirty=True,
                commit=False,
            )


class SplitRiskContract(unittest.TestCase):
    def fixture(self):
        uf = np.ones((1, 30))
        uf[:, :21] = 10

        def edit(a):
            a["open"][0, 21] = 5.052
            a["high"][0, 21] = 5.1
            a["low"][0, 21] = 4.7

        return market(n_tickers=1, price=5.0, uf=uf, edit=edit), {20: [(0, 48)]}

    def test_legacy_spec_record_is_byte_compatible(self):
        values = asdict(C.SPEC)
        values.pop("version")
        old = {"contract_version": "EXEC-US-v2.1", **values}
        self.assertEqual(C.SPEC.record(), old)
        self.assertEqual(
            C.SPEC.sha256(), hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest()
        )
        self.assertEqual(C.ContractSpec.from_record(old), C.SPEC)

    def test_split_tier_change_resizes(self):
        m, signals = self.fixture()
        [old] = closed(run(m, signals, spec=C.SPEC))
        [new] = closed(run(m, signals, spec=C.SPEC_V2_2))
        self.assertGreater(-old["net_pnl_usd"], 100)
        self.assertLessEqual(-new["net_pnl_usd"], 100 + 1e-9)
        self.assertLess(new["shares_filled"], old["shares_filled"])
        self.assertTrue(new["entry_sizing_adjustment"])
        self.assertEqual(new["contract_version"], C.SPLIT_RISK_VERSION)
        self.assertLessEqual(new["entry_debit_usd"], new["reserved_usd"] + 1e-9)
        self.assertAlmostEqual(new["planned_risk_at_fill_usd"], -new["net_pnl_usd"])

    def test_below_stop_fee_boundary_respects_reserved_cash(self):
        uf = np.ones((1, 30))
        uf[:, :21] = 100

        def edit(a):
            a["open"][0, 21] = 0.9999

        m = market(n_tickers=1, price=1.0, uf=uf, edit=edit)
        old_spec = replace(C.SPEC, max_stop_distance=0.0002)
        new_spec = replace(C.SPEC_V2_2, max_stop_distance=0.0002)
        [old] = closed(run(m, {20: [(0, 100)]}, spec=old_spec))
        [new] = closed(run(m, {20: [(0, 100)]}, spec=new_spec))
        self.assertGreater(old["entry_debit_usd"], old["reserved_usd"])
        self.assertEqual(new["exit_reason"], "STOP_AT_OPEN_ON_ENTRY")
        self.assertLessEqual(new["entry_debit_usd"], new["reserved_usd"])
        self.assertEqual(new["shares_filled"], new["entry_size_caps"]["cash"])
        self.assertLessEqual(-new["net_pnl_usd"], new["risk_budget_usd"])

    def test_reverse_split_and_fractional_zero_release_cash(self):
        for new_factor in (10, 10_000):
            uf = np.ones((1, 30))
            uf[:, 21:] = new_factor
            m = market(n_tickers=1, price=5.0, uf=uf)
            account = run(m, {20: [(0, 4.8)]}, spec=C.SPEC_V2_2)
            [trade] = closed(account)
            self.assertFalse(account.state["orders"])
            self.assertFalse(account.state["positions"])
            if new_factor == 10:
                self.assertLessEqual(trade["planned_risk_at_fill_usd"], trade["risk_budget_usd"])
                self.assertLessEqual(trade["entry_debit_usd"], trade["reserved_usd"])
            else:
                self.assertEqual(trade["planned_shares_at_entry_units"], 0)
                self.assertTrue(trade["outcome"].startswith("UNFILLED_"))
                self.assertEqual(account.state["cash_usd"], C.SPEC_V2_2.starting_cash_usd)

    def test_new_forward_and_replay_match(self):
        m, signals = self.fixture()
        state = None
        for k in range(30):
            state, _ = C.forward_step(
                state, m.truncate(k), signals.get(k, []), str(m.dates[k]), spec=C.SPEC_V2_2
            )
        self.assertEqual(state, run(m, signals, spec=C.SPEC_V2_2).state)
        with self.assertRaises(ValueError):
            C.Account(C.SPEC, state)

    def test_invalid_inputs_fail_before_mutating_state(self):
        m = market()
        account = C.Account(C.SPEC_V2_2)
        for k, signals in (
            (-1, []),
            (True, []),
            (1.5, []),
            (20, [(-1, 95)]),
            (20, [(0.5, 95)]),
            (20, [(0, float("nan"))]),
        ):
            before = copy.deepcopy(account.state)
            with self.subTest(k=k, signals=signals), self.assertRaises(ValueError):
                account.step(m, k, signals)
            self.assertEqual(account.state, before)
        for first, last in ((-1, 20), (20, 19), (0, 30), (0, True)):
            with self.subTest(first=first, last=last), self.assertRaises(ValueError):
                C.replay(m, {}, first, last)
        for field in ("risk_fraction", "starting_cash_usd", "stop_slippage", "chase_limit"):
            for value in (True, "1", float("nan"), float("inf")):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    C.ContractSpec(version=C.SPLIT_RISK_VERSION, **{field: value})

    def test_ordinary_economics_unchanged(self):
        m = market()
        [old] = closed(run(m, {20: [(0, 95)]}, spec=C.SPEC))
        [new] = closed(run(m, {20: [(0, 95)]}, spec=C.SPEC_V2_2))
        for key in ("shares_filled", "entry_debit_usd", "net_pnl_usd", "exit_session"):
            self.assertEqual(old[key], new[key])


if __name__ == "__main__":
    unittest.main()
