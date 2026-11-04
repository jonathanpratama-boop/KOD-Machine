"""One composed shadow path, including independent blockers and retained lineage."""

import copy
from decimal import Decimal
import tempfile
import unittest

from idxsig.components.plans import VERSION, evaluate_plan
from idxsig.components.strategy import SMA
from tests.test_components_strategy import observations


def plan_request():
    return {
        "schema_version": VERSION,
        "evidence_type": "synthetic",
        "strategy": {"id": SMA, "version": "1", "parameters": {"fast": 2, "slow": 3}},
        "observations": observations((100, 101, 102, 104)),
        "as_of": "2026-01-01T00:03:10Z",
        "portfolio": {"cash": "1000", "quantity": "0", "quote_currency": "USDT"},
        "quote": {
            "symbol": "BTCUSDT",
            "quote_currency": "USDT",
            "bid": "104",
            "ask": "105",
            "observed_at": "2026-01-01T00:03:09Z",
            "evidence_id": "fixture:quote:1",
        },
        "allocation": {"gross_weight": ".5", "symbol_limit": ".5"},
        "risk": {"max_gross": ".5", "max_symbol": ".5", "max_age_seconds": 60},
        "costs": {
            "id": "ASSUMED_SPOT_V1",
            "fee_rate": ".001",
            "spread_bps": "0",
            "slippage_bps": "0",
            "price_basis": "EXECUTABLE",
        },
        "expires_at": "2026-01-01T00:04:10Z",
    }


class PlanContracts(unittest.TestCase):
    def test_signal_allocation_risk_submit_share_one_identity(self):
        request = plan_request()
        original = copy.deepcopy(request)
        plan = evaluate_plan(request)
        self.assertEqual(request, original)
        self.assertEqual(plan["evaluation"]["decisions"][-1]["signal"], 1)
        self.assertEqual(plan["proposed_targets"], {"BTCUSDT": "0.5"})
        self.assertTrue(plan["risk"]["allowed"])
        event = plan["submit_event"]
        self.assertEqual(event["decision"]["input_sha256"], plan["input_sha256"])
        self.assertEqual(event["order_id"], plan["plan_id"])
        self.assertEqual(event["decision"]["scope"], "SHADOW_SIMULATION")
        self.assertLessEqual(
            Decimal(event["quantity"]) * Decimal(event["limit_price"]) * Decimal("1.001"),
            Decimal(500),
        )
        self.assertFalse(plan["legacy_account_entry_enabled"])
        self.assertFalse(plan["live_enabled"])
        self.assertEqual(plan, evaluate_plan(request))

    def test_stale_quote_blocks_a_positive_signal(self):
        request = plan_request()
        request["quote"]["observed_at"] = "2026-01-01T00:00:00Z"
        result = evaluate_plan(request)
        self.assertIsNone(result["submit_event"])
        self.assertIn("DATA_NOT_FRESH", result["risk"]["reasons"])

    def test_stale_signal_blocks_even_with_fresh_quote(self):
        request = plan_request()
        request["as_of"] = "2026-01-01T00:05:00Z"
        request["quote"]["observed_at"] = request["as_of"]
        request["expires_at"] = "2026-01-01T00:06:00Z"
        self.assertIsNone(evaluate_plan(request)["submit_event"])

    def test_risk_limits_override_valid_signal_and_allocation(self):
        request = plan_request()
        request["risk"]["max_symbol"] = ".25"
        result = evaluate_plan(request)
        self.assertIsNone(result["submit_event"])
        self.assertIn("SYMBOL_LIMIT", result["risk"]["reasons"])

    def test_warmup_is_unknown_not_an_instruction_to_liquidate(self):
        request = plan_request()
        request["observations"] = request["observations"][:1]
        request["portfolio"]["quantity"] = "2"
        result = evaluate_plan(request)
        self.assertIsNone(result["submit_event"])
        self.assertIsNone(result["proposed_targets"])
        self.assertIn("SIGNAL_WARMUP_UNKNOWN", result["risk"]["reasons"])

    def test_known_negative_signal_can_propose_reducing_holdings(self):
        request = plan_request()
        request["observations"] = observations((105, 104, 102, 100))
        request["portfolio"]["quantity"] = "2"
        result = evaluate_plan(request)
        self.assertEqual(result["submit_event"]["side"], "SELL")
        self.assertEqual(Decimal(result["submit_event"]["quantity"]), Decimal(2))

    def test_negative_signal_with_no_holdings_creates_no_order(self):
        request = plan_request()
        request["observations"] = observations((105, 104, 102, 100))
        self.assertIsNone(evaluate_plan(request)["submit_event"])

    def test_sell_sizing_keeps_exposure_within_cap_after_costs_reduce_nav(self):
        request = plan_request()
        request["portfolio"].update(cash="0", quantity="10")
        request["quote"].update(bid="100", ask="100")
        request["costs"]["fee_rate"] = ".01"
        result = evaluate_plan(request)
        event = result["submit_event"]
        quantity = Decimal(event["quantity"])
        self.assertEqual(event["side"], "SELL")
        self.assertGreater(quantity, Decimal(5))
        cash_after = quantity * Decimal(100) * Decimal(".99")
        inventory_after = (Decimal(10) - quantity) * Decimal(100)
        self.assertLessEqual(inventory_after / (cash_after + inventory_after), Decimal(".5"))
        self.assertTrue(result["sizing_estimate"]["risk"]["allowed"])

    def test_sell_sizing_also_accounts_for_spread_and_slippage(self):
        request = plan_request()
        request["portfolio"].update(cash="20", quantity="10")
        request["quote"].update(bid="100", ask="105")
        request["costs"].update(fee_rate=".01", slippage_bps="100")
        result = evaluate_plan(request)
        event = result["submit_event"]
        quantity = Decimal(event["quantity"])
        cash_after = Decimal(20) + quantity * Decimal(99) * Decimal(".99")
        inventory_after = (Decimal(10) - quantity) * Decimal(100)
        self.assertLessEqual(inventory_after / (cash_after + inventory_after), Decimal(".5"))

    def test_future_quote_and_crossed_market_are_invalid(self):
        for change in (
            {"observed_at": "2026-01-01T00:03:11Z"},
            {"bid": "110"},
            {"symbol": "ETHUSDT"},
            {"evidence_id": ""},
            {"quote_currency": "USD"},
        ):
            request = plan_request()
            request["quote"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluate_plan(request)

    def test_mutated_inputs_get_new_decision_identity(self):
        request = plan_request()
        before = evaluate_plan(request)
        request["quote"]["ask"] = "106"
        after = evaluate_plan(request)
        self.assertNotEqual(before["plan_id"], after["plan_id"])

    def test_malformed_evidence_type_is_explicit_validation_failure(self):
        request = plan_request()
        request["evidence_type"] = []
        with self.assertRaisesRegex(ValueError, "synthetic or recorded"):
            evaluate_plan(request)

    def test_generated_intent_is_consumed_by_actual_simulation_executor(self):
        from idxsig.components.execution import execution_run

        plan = evaluate_plan(plan_request())
        submit = plan["submit_event"]
        profile = {
            "schema_version": "KOD_SIMULATION_EXECUTOR_V1",
            "simulation_only": True,
            "evidence_type": "synthetic",
            "id": "PIPELINE_TEST_V1",
            "initial_cash": "1000",
            "initial_holdings": {},
            "fee_rate": ".001",
            "quote_currency": "USDT",
            "symbols": ["BTCUSDT"],
        }
        fill = {
            "event_id": "fill:event:1",
            "kind": "fill",
            "at": "2026-01-01T00:03:12Z",
            "order_id": submit["order_id"],
            "fill_id": "fill:1",
            "quantity": submit["quantity"],
            "price": "105",
            "evidence_id": "fixture:quote:2",
            "observed_at": "2026-01-01T00:03:11Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            first = execution_run(directory, {"profile": profile, "events": [submit, fill]})
            second = execution_run(directory, {"profile": profile, "events": [submit, fill]})
            self.assertEqual(first, second)
            self.assertEqual(first["event_count"], 2)


if __name__ == "__main__":
    unittest.main()
