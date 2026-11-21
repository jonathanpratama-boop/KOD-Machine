"""Independent tests drafted from protocol.json and declared public APIs.

The author did not inspect prepare.py, infer.py or evaluate.py before writing
these contracts. Synthetic values test timing/accounting, never trading merit.
"""
import json
from pathlib import Path
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from prepare import archive_time, causal_context
from infer import validate_input
from evaluate import evaluate


HERE = Path(__file__).resolve().parent


def event(identifier, prediction, gross, status="ok"):
    return {
        "event_id": identifier, "symbol": "SYNTHETICUSDT",
        "decision_time": "2025-03-02T00:00:00Z",
        "entry_time": "2025-03-02T01:00:00Z",
        "exit_time": "2025-03-03T01:00:00Z",
        "predicted_return": prediction, "actual_gross_return": gross,
        "status": status, "inference_seconds": 1.0,
    }


class IndependentContracts(unittest.TestCase):
    def setUp(self):
        self.decision = pd.Timestamp("2025-03-02T00:00:00Z")
        self.trigger = self.decision - pd.Timedelta(hours=1)
        times = pd.date_range(end=self.trigger + pd.Timedelta(hours=28), periods=196, freq="h")
        self.market = pd.DataFrame({
            "open": 10., "high": 12., "low": 9., "close": 11.,
            "volume": 100., "amount": 1100.,
            "close_time": times + pd.Timedelta(hours=1) - pd.Timedelta(microseconds=1),
        }, index=times)
        self.market.index.name = "timestamps"

    def test_future_market_and_next_entry_changes_do_not_change_model_input(self):
        first = causal_context(self.market, self.trigger, self.decision)
        altered = self.market.copy()
        future = altered.index >= self.decision
        altered.loc[future, ["open", "high", "low", "close", "volume", "amount"]] = 999999.
        second = causal_context(altered, self.trigger, self.decision)
        truncated = causal_context(self.market.loc[~future], self.trigger, self.decision)
        assert_frame_equal(first, second)
        assert_frame_equal(first, truncated)
        self.assertEqual(len(first), 168)
        self.assertEqual(first.index[-1], self.trigger)
        validate_input(first.reset_index(), {"decision_time": self.decision.isoformat(), "last_observed_close": 11.})

    def test_candle_closing_at_decision_is_unavailable(self):
        broken = self.market.copy()
        broken.loc[self.trigger, "close_time"] = self.decision
        with self.assertRaises(ValueError):
            causal_context(broken, self.trigger, self.decision)

    def test_same_instant_in_binance_ms_and_us(self):
        known = pd.Timestamp("2025-01-01T00:00:00Z")
        self.assertEqual(archive_time(1735689600000), known)
        self.assertEqual(archive_time(1735689600000000), known)

    def test_threshold_cost_cash_and_failure_share_one_denominator(self):
        rows = [event("accepted", .020001, .12),
                event("at_threshold", .02, -.08),
                event("failed_loss", None, -.18, "failed")]
        result = evaluate(rows)
        # Baseline: (+.10-.10-.20)/3. Combined: (+.10+0-.20)/3.
        self.assertAlmostEqual(result["baseline"]["mean_net_return"], -.20 / 3)
        self.assertAlmostEqual(result["combined_on_same_opportunities"]["mean_net_return"], -.10 / 3)
        self.assertEqual(result["counts"]["usable_outcomes"], 3)
        self.assertEqual(result["counts"]["selected"], 1)
        self.assertEqual(result["counts"]["rejected"], 1)
        self.assertEqual(result["counts"]["fallback"], 1)
        self.assertFalse(result["promotion_authorized"])

    def test_duplicate_opportunities_refused(self):
        with self.assertRaises(ValueError):
            evaluate([event("duplicate", .1, .1), event("duplicate", .1, .1)])

    def test_frozen_scope_is_bounded(self):
        protocol = json.loads((HERE / "protocol.json").read_text())
        self.assertEqual(protocol["cohort"]["selected"], 128)
        self.assertEqual(protocol["inference"]["threads"], 4)
        self.assertEqual(protocol["inference"]["sample_count"], 8)
        self.assertEqual(protocol["inference"]["max_runtime_seconds_per_event"], 3600)
        self.assertEqual(protocol["input"]["bars"], 168)
        self.assertEqual(protocol["decision_rule"]["round_trip_cost"], .02)


if __name__ == "__main__":
    unittest.main()
