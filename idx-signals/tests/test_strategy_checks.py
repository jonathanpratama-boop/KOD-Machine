"""Signals must not depend on future rows, hidden state, or unstable warm-up."""

import copy
import unittest

from idxsig.strategy_checks import run_strategy_checks


def observations():
    return [{"observed_at": f"2026-01-{i + 1:02d}T00:00:00Z", "close": 100 + i} for i in range(12)]


def causal(rows):
    return [
        {"observed_at": row["observed_at"], "status": "READY", "signal": 1, "value": row["close"]}
        for row in rows
    ]


class StrategyCheckTests(unittest.TestCase):
    def test_causal_stable_signal_passes_and_inputs_remain_unchanged(self):
        rows = observations()
        original = copy.deepcopy(rows)
        report = run_strategy_checks(causal, rows, warmup_lengths=(4, 8))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"]["prefix_invariance"]["prefixes_checked"], 12)
        self.assertEqual(rows, original)
        self.assertFalse(report["entry_permission"])

    def test_future_full_sample_normalization_fails_prefix_check(self):
        def leaking(rows):
            final = rows[-1]["close"]
            return [dict(row, value=row["value"] / final) for row in causal(rows)]

        report = run_strategy_checks(leaking, observations(), warmup_lengths=(4,))
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["prefix_invariance"]["status"], "FAIL")

    def test_hidden_state_fails_repeatability(self):
        calls = []

        def stateful(rows):
            calls.append(1)
            return [dict(row, signal=len(calls) % 2) for row in causal(rows)]

        report = run_strategy_checks(stateful, observations())
        self.assertEqual(report["checks"]["repeatability"]["status"], "FAIL")

    def test_causal_but_seed_sensitive_indicator_fails_warmup(self):
        def recursive(rows):
            average = rows[0]["close"]
            result = []
            for row in rows:
                average = 0.5 * average + 0.5 * row["close"]
                result.append(
                    {
                        "observed_at": row["observed_at"],
                        "status": "READY",
                        "signal": 1,
                        "value": average,
                    }
                )
            return result

        report = run_strategy_checks(recursive, observations(), warmup_lengths=(4, 8))
        self.assertEqual(report["checks"]["prefix_invariance"]["status"], "PASS")
        self.assertEqual(report["checks"]["warmup_stability"]["status"], "FAIL")

    def test_tolerance_cannot_hide_changed_signal(self):
        def changes(rows):
            return [dict(row, signal=int(len(rows) > 8)) for row in causal(rows)]

        report = run_strategy_checks(changes, observations(), warmup_lengths=(4,), atol=100)
        self.assertEqual(report["checks"]["prefix_invariance"]["status"], "FAIL")
        self.assertEqual(report["checks"]["warmup_stability"]["status"], "FAIL")

    def test_missing_or_unready_warmup_is_unknown(self):
        def warming(rows):
            return [
                dict(row, status="WARMUP" if i < 5 else "READY", signal=None if i < 5 else 1)
                for i, row in enumerate(causal(rows))
            ]

        for lengths in ((), (4,), (12,)):
            with self.subTest(lengths=lengths):
                report = run_strategy_checks(warming, observations(), warmup_lengths=lengths)
                self.assertEqual(report["status"], "UNKNOWN")
                self.assertEqual(report["checks"]["prefix_invariance"]["status"], "PASS")

    def test_mutation_and_malformed_output_are_reported_as_failures(self):
        def mutation(rows):
            rows[0]["close"] = 999
            return causal(rows)

        for callback in (
            mutation,
            lambda rows: [],
            lambda rows: [dict(r, value=float("nan")) for r in causal(rows)],
        ):
            with self.subTest(callback=callback):
                report = run_strategy_checks(callback, observations())
                self.assertEqual(report["checks"]["evaluator_contract"]["status"], "FAIL")

    def test_invalid_configuration_is_rejected(self):
        for lengths in ((0,), (13,), (4, 4), (True,)):
            with self.subTest(lengths=lengths), self.assertRaises(ValueError):
                run_strategy_checks(causal, observations(), warmup_lengths=lengths)
        for tolerance in (float("nan"), -1, True):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                run_strategy_checks(causal, observations(), atol=tolerance)


if __name__ == "__main__":
    unittest.main()
