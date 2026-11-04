"""Timing/unit contracts for the separately versioned E3 decision core.

Passing these checks establishes no historical or prospective return.
"""

import importlib.util
import unittest
from pathlib import Path

POLICY_PATH = Path(__file__).resolve().parents[1] / "research" / "E3_US_RETENTION_v1" / "policy.py"
SPEC = importlib.util.spec_from_file_location("e3_retention_policy", POLICY_PATH)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class RetentionPolicyTests(unittest.TestCase):
    def inputs(self):
        flags = [0] * 30
        flags[19] = 1
        return flags, [10.0] * 30, [1_000_000.0] * 30, [True] * 30

    def test_same_close_retained_then_next_open_plan(self):
        flags, closes, values, present = self.inputs()
        plan = policy.plan_at(flags, closes, values, present, 20)
        self.assertTrue(plan["enter"])
        self.assertEqual(
            (plan["origin_index"], plan["entry_index"], plan["target_exit_index"]), (19, 21, 26)
        )

    def test_failed_retention_abstains_even_if_later_recovery(self):
        flags, closes, values, present = self.inputs()
        closes[20], closes[21] = 9.99, 100.0
        self.assertFalse(policy.plan_at(flags, closes, values, present, 20)["enter"])
        self.assertFalse(policy.plan_at(flags, closes, values, present, 21)["enter"])

    def test_future_price_volume_and_flags_cannot_change_decision(self):
        flags, closes, values, present = self.inputs()
        before = policy.plan_at(flags, closes, values, present, 20)
        flags[21:], closes[21:], values[21:], present[21:] = (
            [1] * 9,
            [1e9] * 9,
            [0.0] * 9,
            [False] * 9,
        )
        self.assertEqual(before, policy.plan_at(flags, closes, values, present, 20))
        self.assertEqual(
            before, policy.plan_at(flags[:21], closes[:21], values[:21], present[:21], 20)
        )

    def test_missing_confirmation_session_is_not_forward_filled(self):
        flags, closes, values, present = self.inputs()
        present[20] = False
        self.assertFalse(policy.plan_at(flags, closes, values, present, 20)["enter"])

    def test_short_or_invalid_capacity_history_refuses(self):
        self.assertEqual(
            policy.capacity_at([1e6] * 19, [True] * 19, 18)["reason"], "INSUFFICIENT_HISTORY"
        )
        values = [1e6] * 20
        values[0] = float("nan")
        self.assertEqual(policy.capacity_at(values, [True] * 20, 19)["reason"], "INVALID_HISTORY")

    def test_capacity_counts_listed_zero_trade_days(self):
        values = [0.0] * 11 + [1e6] * 9
        self.assertFalse(policy.capacity_at(values, [True] * 20, 19)["eligible"])

    def test_price_volume_rescaling_preserves_dollar_budget_and_retention(self):
        flags, closes, values, present = self.inputs()
        before = policy.plan_at(flags, closes, values, present, 20)
        scaled_closes = [c * 20 for c in closes]
        scaled_values = [c * 20 * (v / c / 20) for c, v in zip(closes, values)]
        self.assertEqual(before, policy.plan_at(flags, scaled_closes, scaled_values, present, 20))

    def test_undefined_origin_and_unobserved_cutoff(self):
        self.assertFalse(policy.confirmation_at([1], [10.0], [True], 0))
        with self.assertRaisesRegex(ValueError, "not observed"):
            policy.confirmation_at([1], [10.0], [True], 1)


if __name__ == "__main__":
    unittest.main()
