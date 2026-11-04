"""Causal research contracts and unchanged incumbent economics."""

import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
import unittest

from idxsig.components.costs import CostModel
from idxsig.components.strategy import (
    RETURN,
    SMA,
    assess_risk,
    evaluate_batch,
    evaluate_series,
    evaluate_trend,
    portfolio_targets,
    registry,
    specification,
)
from idxsig.runtime import account
from idxsig.runtime.strategy import require_paper_profile
from tests.test_runtime_account import T0, bars, profile


def observations(prices=(100, 100, 101, 102, 110, 90)):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "observed_at": (start + timedelta(minutes=i)).isoformat(),
            "symbol": "BTCUSDT",
            "close": str(price),
        }
        for i, price in enumerate(prices)
    ]


class StrategyContracts(unittest.TestCase):
    def test_every_prefix_is_unchanged_when_future_crash_is_appended(self):
        original = observations()
        saved = copy.deepcopy(original)
        for strategy, params in (
            (SMA, {"fast": 2, "slow": 3}),
            (RETURN, {"lookback": 2, "threshold": 0.03}),
        ):
            all_rows = evaluate_series(strategy, original, params)
            for i in range(1, len(original) + 1):
                self.assertEqual(evaluate_series(strategy, original[:i], params), all_rows[:i])
        self.assertEqual(original, saved)

    def test_unknown_warmup_is_not_a_negative_signal(self):
        result = evaluate_series(SMA, observations(), {"fast": 2, "slow": 4})
        self.assertEqual([r["signal"] for r in result[:3]], [None, None, None])
        self.assertEqual(result[3]["status"], "READY")
        self.assertEqual(result[3]["signal"], 1)
        self.assertEqual(result[-1]["signal"], 0)

    def test_threshold_obeys_declared_observation_lookback(self):
        result = evaluate_series(
            RETURN, observations((100, 120, 80, 110)), {"lookback": 2, "threshold": 0.05}
        )
        self.assertEqual(result[2]["signal"], 0)
        self.assertEqual(result[3]["signal"], 0)

    def test_parameters_and_versions_are_not_silently_accepted(self):
        bad_specs = [
            {"id": SMA, "version": "2", "parameters": {"fast": 2, "slow": 3}},
            {"id": SMA, "version": "1", "parameters": {"fast": 3, "slow": 2}},
            {"id": SMA, "version": "1", "parameters": {"fast": True, "slow": 3}},
            {"id": RETURN, "version": "1", "parameters": {"lookback": 2, "threshold": "NaN"}},
            {"id": SMA, "version": "1", "parameters": {"fast": 2, "slow": 3}, "live_enabled": True},
            ["not-a-strategy"],
        ]
        for spec in bad_specs:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                evaluate_series(spec, observations())

    def test_bad_chronology_and_instruments_are_rejected(self):
        for transform in (
            lambda r: r[1].update(observed_at=r[0]["observed_at"]),
            lambda r: r[1].update(observed_at="2025-01-01T00:00:00Z"),
            lambda r: r[0].update(observed_at="2026-01-01"),
            lambda r: r[0].update(event_at="2027-01-01T00:00:00Z"),
            lambda r: r[1].update(symbol="ETHUSDT"),
            lambda r: r[0].update(close="Infinity"),
            lambda r: r[0].update(close="0"),
            lambda r: r[0].update(close=True),
        ):
            rows = observations()
            transform(rows)
            with self.assertRaises(ValueError):
                evaluate_series(SMA, rows)

    def test_cutoff_and_source_identity_are_retained(self):
        request = {
            "strategy": specification(SMA, {"fast": 2, "slow": 3}),
            "observations": observations(),
        }
        result = evaluate_batch(request)
        self.assertFalse(result["entry_enabled"])
        self.assertEqual(result, evaluate_batch(copy.deepcopy(request)))
        changed = copy.deepcopy(request)
        changed["observations"][0]["close"] = "99"
        self.assertNotEqual(result["input_sha256"], evaluate_batch(changed)["input_sha256"])
        request["as_of"] = observations()[0]["observed_at"]
        with self.assertRaisesRegex(ValueError, "cutoff"):
            evaluate_batch(request)

    def test_registry_cannot_admit_repricing_or_enable_live(self):
        self.assertTrue(all(not x["entry_enabled"] and not x["live_enabled"] for x in registry()))
        with self.assertRaises(ValueError):
            require_paper_profile(
                {"strategy_id": "SELECTIVE_REPRICING", "evidence_type": "synthetic"}
            )

    def test_incumbent_adapter_is_identical_to_existing_signal_economics(self):
        source = Path(account.__file__)
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        e = account._bars(bars(), "2026-11-01", T0, profile())
        raw, targets, metrics = account.signals(e, "2026-11-01", T0)
        self.assertEqual(
            evaluate_trend(e, "2026-11-01", T0),
            account.wire({"raw_weights": raw, "targets": targets, "metrics": metrics}),
        )
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)


class PortfolioRiskContracts(unittest.TestCase):
    def test_portfolio_respects_caps_and_leaves_cash(self):
        targets = portfolio_targets(
            {"BTC": 1, "ETH": 1, "OTHER": 0}, gross_weight="0.8", symbol_limit="0.3"
        )
        self.assertEqual(targets, {"BTC": "0.3", "ETH": "0.3", "OTHER": "0"})
        self.assertEqual(sum(map(Decimal, targets.values())), Decimal("0.6"))

    def test_signal_strength_cannot_bypass_independent_gate(self):
        targets = portfolio_targets({"BTC": 1})
        self.assertEqual(
            assess_risk(targets)["reasons"], ["STRATEGY_NOT_ADMITTED", "DATA_NOT_FRESH"]
        )
        self.assertFalse(assess_risk(targets, fresh=True)["allowed"])
        self.assertFalse(assess_risk(targets, admitted=True)["allowed"])

    def test_breach_remains_blocked_even_with_admission(self):
        result = assess_risk({"BTC": ".7", "ETH": ".6"}, admitted=True, fresh=True, max_symbol=".5")
        self.assertEqual(result["reasons"], ["GROSS_LIMIT", "SYMBOL_LIMIT"])
        self.assertFalse(result["allowed"])

    def test_unknown_signal_and_leverage_are_not_allocations(self):
        for signal in (None, -1, 2, True, "1"):
            with self.assertRaises(ValueError):
                portfolio_targets({"BTC": signal})
        with self.assertRaises(ValueError):
            portfolio_targets({"BTC": 1}, gross_weight="1.01")
        with self.assertRaises(ValueError):
            assess_risk({"BTC": "-.1"}, admitted=True, fresh=True)


class CostContracts(unittest.TestCase):
    def profile(self, **changes):
        values = {
            "id": "ASSUMED_SPOT_V1",
            "fee_rate": "0.001",
            "spread_bps": "10",
            "slippage_bps": "5",
            "price_basis": "MID",
        }
        values.update(changes)
        return CostModel.from_dict(values)

    def test_round_trip_accounts_for_fees_spread_slippage_once(self):
        model = self.profile()
        buy, sell = model.prices("100", "110")
        self.assertEqual(buy, Decimal("100.100"))
        self.assertEqual(sell, Decimal("109.890"))
        cash = Decimal("1000")
        quantity = cash / (buy * Decimal("1.001"))
        final = quantity * sell * Decimal(".999")
        self.assertAlmostEqual(model.round_trip_return("100", "110"), final / cash - 1)

    def test_executable_quote_prices_do_not_charge_another_spread(self):
        with self.assertRaisesRegex(ValueError, "already include spread"):
            self.profile(price_basis="EXECUTABLE")
        model = self.profile(
            price_basis="EXECUTABLE", spread_bps="0", slippage_bps="0", fee_rate="0"
        )
        self.assertEqual(model.round_trip_return("101", "99"), Decimal(99) / Decimal(101) - 1)

    def test_missing_or_nonfinite_costs_do_not_become_zero(self):
        with self.assertRaises(ValueError):
            CostModel.from_dict({"id": "incomplete"})
        for changes in (
            {"fee_rate": "NaN"},
            {"fee_rate": "1"},
            {"slippage_bps": "10000"},
            {"spread_bps": "-1"},
            {"price_basis": "CLOSE"},
            {"price_basis": []},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.profile(**changes)

    def test_cost_profile_round_trip_is_deterministic(self):
        model = self.profile()
        restored = CostModel.from_dict(model.as_dict())
        self.assertEqual(model, restored)
        self.assertEqual(model.round_trip_return(100, 100), restored.round_trip_return(100, 100))
        self.assertLess(model.round_trip_return(100, 100), 0)


if __name__ == "__main__":
    unittest.main()
