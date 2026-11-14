import json
import math
import unittest

from evaluate import classify, evaluate


def record(identifier, gross, prediction, status="ok", day=1):
    return dict(event_id=identifier, symbol="TESTUSDT", decision_time=f"2025-01-{day:02d}T00:00:00Z",
                entry_time=f"2025-01-{day:02d}T01:00:00Z", exit_time=None,
                predicted_return=prediction, status=status, actual_gross_return=gross, inference_seconds=1)


class EvaluationTests(unittest.TestCase):
    def test_rejections_keep_common_opportunity_denominator(self):
        result = evaluate([record("winner", .12, .05), record("loser", -.08, .01)])
        self.assertEqual(result["counts"]["selected"], 1)
        self.assertEqual(result["counts"]["rejected"], 1)
        self.assertAlmostEqual(result["baseline"]["mean_net_return"], 0)
        self.assertAlmostEqual(result["combined_on_same_opportunities"]["mean_net_return"], .05)
        self.assertAlmostEqual(result["paired_mean_delta"], .05)
        self.assertEqual(result["cash_baseline_mean_net_return"], 0)
        self.assertTrue(result["combined_beats_cash"])

    def test_failed_forecast_preserves_loss_as_fallback(self):
        result = evaluate([record("failure", -.10, None, "failed")])
        self.assertEqual(result["counts"]["fallback"], 1)
        self.assertAlmostEqual(result["combined_on_same_opportunities"]["mean_net_return"], -.12)
        self.assertEqual(result["paired_mean_delta"], 0)
        self.assertFalse(result["promotion_authorized"])
        self.assertFalse(result["combined_beats_cash"])

    def test_winner_removal_gate_blocks_nonpositive_or_missing_delta(self):
        for sensitivity in (None, 0, -.001):
            with self.subTest(sensitivity=sensitivity):
                self.assertEqual(classify(True, True, [.01, .02], sensitivity),
                                 "NO_DEMONSTRATED_IMPROVEMENT")
        self.assertEqual(classify(True, True, [.01, .02], .001),
                         "PROMISING_EXPLORATORY_ONLY")

    def test_missing_outcome_is_reported_and_blocks_promising(self):
        rows = [record(str(i), -.10, .01, day=i % 20 + 1) for i in range(50)]
        rows += [record(f"win{i}", .12, .1, day=i % 20 + 1) for i in range(10)]
        rows.append(record("missing", None, .1))
        result = evaluate(rows)
        self.assertEqual(result["counts"]["usable_outcomes"], 60)
        self.assertEqual(result["missing_outcome_event_ids"], ["missing"])
        self.assertEqual(result["verdict"], "INSUFFICIENT_EVIDENCE")

    def test_nonfinite_prediction_falls_back_outcome_excluded(self):
        result = evaluate([record("bad_prediction", -.08, math.nan),
                           record("bad_outcome", math.inf, .1)])
        self.assertEqual(result["counts"]["fallback"], 1)
        self.assertEqual(result["counts"]["missing_or_nonfinite_outcomes"], 1)
        self.assertAlmostEqual(result["combined_on_same_opportunities"]["mean_net_return"], -.10)
        json.dumps(result, allow_nan=False)

    def test_threshold_is_strict(self):
        self.assertEqual(evaluate([record("at_cost", .1, .02)])["counts"]["rejected"], 1)

    def test_forecast_error_uses_observed_close_denominator(self):
        row = record("different_entry_price", .2, .05)
        row["actual_forecast_target_return"] = .08
        result = evaluate([row])
        self.assertEqual(result["forecast_error_count"], 1)
        self.assertAlmostEqual(result["forecast_mae"], .03)
        self.assertAlmostEqual(result["flat_zero_return_mae"], .08)
        self.assertAlmostEqual(result["baseline"]["mean_net_return"], .18)

    def test_duplicate_event_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([record("same", .1, .1), record("same", -.1, .01)])

    def test_date_clusters_are_utc_and_bootstrap_deterministic(self):
        rows = [record("a", -.08, 0), record("b", .12, .1, day=2)]
        rows[0]["decision_time"] = "2025-01-02T01:00:00+07:00"
        first, second = evaluate(rows), evaluate(rows)
        self.assertEqual(first, second)
        self.assertEqual(first["counts"]["decision_utc_dates"], 2)
        self.assertEqual(first["paired_delta_95pct_date_cluster_bootstrap"], [0, .1])

    def test_small_positive_example_stays_exploratory(self):
        rows = [record(str(i), -.10, .01, day=i % 20 + 1) for i in range(50)]
        rows += [record(f"win{i}", .12, .1, day=i % 20 + 1) for i in range(10)]
        result = evaluate(rows)
        self.assertEqual(result["verdict"], "PROMISING_EXPLORATORY_ONLY")
        self.assertFalse(result["promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
