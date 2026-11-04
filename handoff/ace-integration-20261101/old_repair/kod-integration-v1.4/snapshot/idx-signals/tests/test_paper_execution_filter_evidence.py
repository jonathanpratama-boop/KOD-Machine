"""Filter applicability and explicit observed/simulated evidence, offline only."""
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D

from idxsig.paper_execution_feasibility import AverageReference, SimulatedCounts
from tests import test_paper_execution_feasibility as fixtures

T = fixtures.T


class Evidence(unittest.TestCase):
    setUp = fixtures.Feasibility.setUp
    run_estimate = fixtures.Feasibility.run_estimate

    def add(self, *rows):
        self.filters = replace(self.filters, filters=self.rows + rows)

    def percent(self):
        self.add({"filterType": "PERCENT_PRICE_BY_SIDE", "bidMultiplierUp": "1.2", "bidMultiplierDown": "0.5",
                  "askMultiplierUp": "2", "askMultiplierDown": "0.8", "avgPriceMins": 5})
        return AverageReference("AAAUSDT", D("100"), 5, T - timedelta(seconds=1), T - timedelta(seconds=2),
                                "fixture/avgPrice", "ABSENT", T - timedelta(seconds=1), "fixture/referencePrice:-2043")

    def test_inapplicable_filters_are_reported_not_silently_dropped(self):
        self.add({"filterType": "ICEBERG_PARTS", "limit": 1},
                 {"filterType": "MARKET_LOT_SIZE", "minQty": "0", "maxQty": "0", "stepSize": "0"},
                 {"filterType": "TRAILING_DELTA", "minTrailingAboveDelta": 10, "maxTrailingAboveDelta": 20,
                  "minTrailingBelowDelta": 10, "maxTrailingBelowDelta": 20},
                 {"filterType": "MAX_NUM_ORDER_AMENDS", "maxNumOrderAmends": 0},
                 {"filterType": "MAX_NUM_ORDER_LISTS", "maxNumOrderLists": 0})
        out = self.run_estimate()
        self.assertEqual(out.status, "COMPLETE")
        self.assertEqual(sum(":INAPPLICABLE:" in c for c in out.filter_checks), 5)

    def test_nonplain_intents_cannot_use_inapplicability(self):
        for fields in ({"order_type": "MARKET"}, {"time_in_force": "GTC"}, {"iceberg_quantity": D("1")},
                       {"trailing_delta": 10}, {"is_order_list": True}, {"is_amendment": True}):
            self.assertEqual(self.run_estimate(intent=replace(self.intent, **fields)).reason,
                             "ONLY_PLAIN_NEW_STANDALONE_LIMIT_IOC_SUPPORTED")

    def test_missing_reference_and_interval_mismatch(self):
        ref = self.percent()
        self.assertEqual(self.run_estimate().reason, "MISSING_AVERAGE_REFERENCE")
        self.assertEqual(self.run_estimate(average=replace(ref, minutes=1), max_reference_age=timedelta(seconds=10)).reason,
                         "AVERAGE_INTERVAL_MISMATCH")

    def test_percent_buy_sell_bounds(self):
        ref = self.percent()
        args = dict(average=ref, max_reference_age=timedelta(seconds=10))
        self.assertEqual(self.run_estimate(**args).status, "COMPLETE")
        self.assertEqual(self.run_estimate(intent=replace(self.intent, limit_price=D("120.05")), **args).reason, "PERCENT_PRICE_BY_SIDE")
        self.assertEqual(self.run_estimate(intent=replace(self.intent, side="SELL", limit_price=D("79.95")), **args).reason, "PERCENT_PRICE_BY_SIDE")
        self.assertNotEqual(self.run_estimate(intent=replace(self.intent, side="SELL", limit_price=D("200")), **args).reason, "PERCENT_PRICE_BY_SIDE")

    def test_override_presence_or_unknown_never_uses_average(self):
        ref = self.percent()
        for state in ("PRESENT", "UNKNOWN"):
            self.assertEqual(self.run_estimate(average=replace(ref, override_state=state), max_reference_age=timedelta(seconds=10)).reason,
                             "ACTIVE_OR_UNKNOWN_OVERRIDE_REFERENCE")

    def test_reference_recency_identity_and_time_order(self):
        ref = self.percent()
        for fields in ({"observed_at": T + timedelta(seconds=1)}, {"last_trade_at": T - timedelta(minutes=2)},
                       {"override_observed_at": T - timedelta(minutes=2)}, {"symbol": "BBB"}, {"override_source": ""},
                       {"last_trade_at": T}, {"price": D("0")}):
            with self.subTest(fields=fields):
                self.assertEqual(self.run_estimate(average=replace(ref, **fields), max_reference_age=timedelta(seconds=10)).status, "REJECTED")
        self.assertEqual(self.run_estimate(average=ref).reason, "INVALID_MAX_AGE")

    def test_count_evidence_absence_is_not_zero(self):
        self.add({"filterType": "MAX_NUM_ORDERS", "maxNumOrders": 5},
                 {"filterType": "MAX_NUM_ALGO_ORDERS", "maxNumAlgoOrders": 2})
        self.assertEqual(self.run_estimate().reason, "MISSING_SIMULATED_ACCOUNT_COUNTS")
        counts = SimulatedCounts("AAAUSDT", T, 4, 2)
        out = self.run_estimate(simulated_counts=counts, max_count_age=timedelta(seconds=10))
        self.assertEqual(out.status, "COMPLETE")
        self.assertIn("SIMULATED_ACCOUNT_COUNTS_ONLY:NOT_ACTUAL_ACCOUNT_VERIFICATION", out.assumptions)
        self.assertEqual(self.run_estimate(simulated_counts=replace(counts, open_orders=5), max_count_age=timedelta(seconds=10)).reason, "MAX_NUM_ORDERS")

    def test_algo_counts_no_increment_for_plain_limit_but_missing_fails(self):
        self.add({"filterType": "MAX_NUM_ALGO_ORDERS", "maxNumAlgoOrders": 2})
        self.assertEqual(self.run_estimate().reason, "MISSING_SIMULATED_ACCOUNT_COUNTS")
        counts = SimulatedCounts("AAAUSDT", T, 3, 2)
        self.assertEqual(self.run_estimate(simulated_counts=counts, max_count_age=timedelta(seconds=10)).status, "COMPLETE")
        self.assertEqual(self.run_estimate(simulated_counts=replace(counts, open_algo_orders=3), max_count_age=timedelta(seconds=10)).reason, "MAX_NUM_ALGO_ORDERS")

    def test_counts_invalid_future_stale_or_inconsistent(self):
        self.add({"filterType": "MAX_NUM_ORDERS", "maxNumOrders": 5})
        counts = SimulatedCounts("AAAUSDT", T, 0, 0)
        for fields in ({"open_orders": -1}, {"open_orders": True}, {"open_algo_orders": 1},
                       {"as_of": T + timedelta(seconds=1)}, {"as_of": T - timedelta(minutes=1)}, {"symbol": "BBB"}):
            self.assertEqual(self.run_estimate(simulated_counts=replace(counts, **fields), max_count_age=timedelta(seconds=10)).status, "REJECTED")

    def test_unknown_duplicate_and_malformed_inapplicable_remain_rejections(self):
        for row in ({"filterType": "UNKNOWN"}, {"filterType": "ICEBERG_PARTS"},
                    {"filterType": "ICEBERG_PARTS", "limit": True}):
            self.add(row)
            self.assertEqual(self.run_estimate().status, "REJECTED")
        self.add({"filterType": "ICEBERG_PARTS", "limit": 1}, {"filterType": "ICEBERG_PARTS", "limit": 1})
        self.assertEqual(self.run_estimate().reason, "DUPLICATE_FILTER:ICEBERG_PARTS")


if __name__ == "__main__":
    unittest.main()
