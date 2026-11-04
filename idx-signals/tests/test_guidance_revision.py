"""Checks for source admission, clocks, execution, risk and immutable recording."""

from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig import guidance_revision as g


ROOT = Path(g.__file__).resolve().parents[1] / "research" / "GUIDANCE_REVISION_v1"


class GuidanceTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((ROOT / "protocol.json").read_text())
        self.old = {
            "classification": "NUMERIC_ANNUAL_REVENUE",
            "issuer_cik": 2488,
            "fiscal_year": "2021",
            "metric": "full_year_revenue",
            "representation": "growth_percent",
            "currency": "USD",
            "units": "percent",
            "scope": "consolidated",
            "base_period": "2020",
            "forecast_level": "1.37",
            "accepted_at_utc": "2021-01-26T21:14:58+00:00",
            "accession": "old",
        }
        self.new = {
            **self.old,
            "forecast_level": "1.50",
            "accepted_at_utc": "2021-04-27T20:12:09+00:00",
            "accession": "new",
        }
        self.feature = g.revision(self.old, self.new, latest_prior_confirmed=True)

    def test_growth_revision_is_level_ratio_not_thirteen_percent(self):
        self.assertEqual(self.feature["classification"], "RAISED")
        self.assertAlmostEqual(
            float(self.feature["forecast_level_change_fraction"]), 1.5 / 1.37 - 1
        )

    def test_changed_period_base_scope_and_metric_cannot_compare(self):
        for key, value in [
            ("fiscal_year", "2022"),
            ("base_period", "2019"),
            ("scope", "post_acquisition"),
            ("metric", "EPS"),
        ]:
            altered = {**self.new, key: value}
            self.assertEqual(
                g.revision(self.old, altered, latest_prior_confirmed=True)["classification"],
                "INCOMPARABLE",
            )

    def test_lowered_unchanged_absent_and_unverified_prior_retained(self):
        for level, label in [("1.37", "UNCHANGED"), ("1.10", "LOWERED")]:
            self.assertEqual(
                g.revision(
                    self.old, {**self.new, "forecast_level": level}, latest_prior_confirmed=True
                )["classification"],
                label,
            )
        self.assertEqual(
            g.revision(self.old, {}, latest_prior_confirmed=True)["classification"],
            "NO_COMPARABLE_GUIDANCE",
        )
        self.assertEqual(
            g.revision(self.old, self.new, latest_prior_confirmed=False)["classification"],
            "REVIEW_REQUIRED",
        )

    def test_future_prior_rejected(self):
        with self.assertRaises(ValueError):
            g.revision(
                {**self.old, "accepted_at_utc": "2022-01-01T00:00:00Z"},
                self.new,
                latest_prior_confirmed=True,
            )

    def test_quote_and_numeric_binding(self):
        package = {
            "issuer_cik": 2488,
            "accession": "a",
            "accepted_at_utc": "2021-01-01T00:00:00Z",
            "raw_sha256": "x",
            "documents": {"d": "Full year 2021 revenue growth is 37 percent over 2020."},
        }
        review = {
            **self.old,
            "document": "d",
            "quote": package["documents"]["d"],
            "lower": 37,
            "upper": 37,
        }
        result = g.bind_guidance(package, review)
        self.assertEqual(result["forecast_level"], "1.37")
        for changes in [
            {"lower": 50, "upper": 50},
            {"quote": "invented"},
            {"issuer_cik": 999},
            {"fiscal_year": None},
        ]:
            with self.assertRaises(ValueError):
                g.bind_guidance(package, {**review, **changes})

    def test_sgml_identity_and_date_specific_timezone(self):
        raw = b"<SEC-DOCUMENT>\n<ACCEPTANCE-DATETIME>20210427161209\nACCESSION NUMBER: abc\nCENTRAL INDEX KEY: 0000002488\n<DOCUMENT><TYPE>EX-99.1\n<FILENAME>d\n<TEXT>revenue</TEXT></DOCUMENT>"
        self.assertEqual(
            g.submission(raw, 2488, "abc")["accepted_at_utc"], "2021-04-27T20:12:09+00:00"
        )
        with self.assertRaises(ValueError):
            g.submission(raw, 999, "abc")
        with self.assertRaises(ValueError):
            g.submission(raw, 2488, "other")

    def test_weekend_dst_holiday_and_twentieth_session(self):
        schedule = g.session_schedule("2026-10-17T07:20:00Z", "2026-10-16T20:01:00Z", self.p)
        self.assertEqual(schedule["entry_at_utc"], "2026-10-19T13:45:00+00:00")
        self.assertEqual(schedule["time_exit_session"], "2026-11-13")
        self.assertEqual(schedule["time_exit_at_utc"], "2026-11-13T21:00:00+00:00")
        holiday = g.session_schedule("2026-11-26T12:00:00Z", "2026-11-25T22:00:00Z", self.p)
        self.assertEqual(holiday["entry_session"], "2026-11-27")

    def test_calendar_does_not_depend_on_hosts_default_date_range(self):
        import exchange_calendars as xc

        original = xc.get_calendar

        def old_host(name, **kwargs):
            if not kwargs:
                return original(name, start="2020-01-01", end="2025-01-01")
            return original(name, **kwargs)

        with patch.object(xc, "get_calendar", old_host):
            schedule = g.session_schedule("2026-10-17T07:20:00Z", "2026-10-16T20:01:00Z", self.p)
        self.assertEqual(schedule["entry_session"], "2026-10-19")

    def test_calendar_range_can_begin_and_end_on_nontrading_days(self):
        schedule = g.session_schedule("2026-10-19T14:00:00Z", "2026-10-18T20:00:00Z", self.p)
        self.assertEqual(schedule["entry_session"], "2026-10-20")
        self.assertEqual(schedule["time_exit_session"], "2026-11-16")

    def wait(self):
        feature = {**self.feature, "fiscal_year": "2026"}
        return g.decide(
            feature,
            policy=self.p,
            created_at="2026-10-17T07:20:00Z",
            source_at="2026-10-16T20:01:00Z",
            retrieved_at="2026-10-17T07:00:00Z",
            reviewed_at="2026-10-17T07:05:00Z",
        )

    def execution(self, stamp="2026-10-19T13:45:05Z"):
        return {
            "issuer_cik": 2488,
            "instrument_id": 1832,
            "min_exposure_usd": 10,
            "max_units_per_order": 1000,
            "identity_verified": True,
            "underlying_stock_1x_verified": True,
            "stop_supported_verified": True,
            "allow_open": True,
            "whole_units": False,
            "quote": {"bid": 99.95, "ask": 100, "asOf": stamp},
        }

    def test_weekend_wait_is_unfilled_with_explicit_conditions(self):
        d = self.wait()
        self.assertEqual(d["action"], "PAPER_WAIT")
        self.assertEqual(d["filled_exposure_usd"], "0")
        self.assertEqual(d["exit"]["stop_fraction"], 0.05)
        self.assertEqual(d["expiry"], "2026-10-19T13:46:00+00:00")

    def test_future_information_blocks_decision(self):
        with self.assertRaises(ValueError):
            g.decide(
                self.feature,
                policy=self.p,
                created_at="2026-10-17T07:20:00Z",
                source_at="2026-10-16T20:00:00Z",
                retrieved_at="2026-10-17T07:21:00Z",
                reviewed_at="2026-10-17T07:00:00Z",
            )

    def test_quote_staleness_spread_and_future_stamp(self):
        q = self.execution()["quote"]
        self.assertIsNone(g.validate_quote(q, "2026-10-19T13:45:10Z", self.p))
        self.assertEqual(g.validate_quote(q, "2026-10-19T13:47:00Z", self.p), "STALE_QUOTE")
        self.assertEqual(g.validate_quote(q, "2026-10-17T13:45:00Z", self.p), "STALE_QUOTE")
        self.assertEqual(
            g.validate_quote({**q, "bid": 90}, "2026-10-19T13:45:10Z", self.p), "SPREAD_TOO_WIDE"
        )

    def test_no_premature_or_retrospective_fill_and_identity_cannot_alias(self):
        d = self.wait()
        e = self.execution()
        with self.assertRaises(ValueError):
            g.paper_fill(d, e, "2026-10-17T07:20:00Z", self.p, cash=10000, equity=10000)
        self.assertEqual(
            g.paper_fill(d, e, "2026-10-19T13:47:00Z", self.p, cash=10000, equity=10000)["action"],
            "MISSED_ENTRY",
        )
        with self.assertRaises(ValueError):
            g.paper_fill(
                d,
                {**e, "issuer_cik": 999},
                "2026-10-19T13:45:10Z",
                self.p,
                cash=10000,
                equity=10000,
            )
        self.assertEqual(
            g.paper_fill(
                d,
                {**e, "underlying_stock_1x_verified": False},
                "2026-10-19T13:45:10Z",
                self.p,
                cash=10000,
                equity=10000,
            )["action"],
            "EXECUTION_BLOCKED",
        )

    def test_size_obeys_cash_notional_loss_and_position_caps(self):
        size = g.risk_size(100, self.p, cash=10000, equity=10000)
        self.assertLessEqual(Decimal(size["notional_usd"]), 1000)
        self.assertLessEqual(Decimal(size["planned_stop_loss_usd"]), 50)
        small = g.risk_size(100, self.p, cash=500, equity=10000)
        self.assertLessEqual(Decimal(small["cash_required_usd"]), 500)
        self.assertEqual(
            g.risk_size(100, self.p, cash=10000, equity=10000, open_positions=1)["units"], "0"
        )

    def fill(self):
        return g.paper_fill(
            self.wait(), self.execution(), "2026-10-19T13:45:10Z", self.p, cash=10000, equity=10000
        )

    def test_funded_mark_and_gap_exit_do_not_invent_stop_price(self):
        fill = self.fill()
        mark = g.mark_position(
            fill,
            {"instrument_id": 1832, "bid": 90, "ask": 95, "asOf": "2026-10-20T13:45:00Z"},
            "2026-10-20T13:45:00Z",
            self.p,
            time_exit_at="2026-11-13T21:00:00Z",
            corporate_action_clear=True,
        )
        self.assertEqual(mark["reason"], "STOP_OBSERVED")
        self.assertEqual(Decimal(mark["filled_exit_price"]), Decimal("89.91"))
        self.assertLess(Decimal(mark["modeled_net_liquidation_pnl_usd"]), -50)
        blocked = g.mark_position(
            fill,
            {"instrument_id": 1832, "bid": 101, "ask": 101.1, "asOf": "2026-10-20T13:45:00Z"},
            "2026-10-20T13:45:00Z",
            self.p,
            time_exit_at="2026-11-13T21:00:00Z",
            corporate_action_clear=False,
        )
        self.assertEqual(blocked["action"], "VALUATION_BLOCKED")
        wrong = g.mark_position(
            fill,
            {"instrument_id": 100594, "bid": 0.29, "ask": 0.3, "asOf": "2026-10-20T13:45:00Z"},
            "2026-10-20T13:45:00Z",
            self.p,
            time_exit_at="2026-11-13T21:00:00Z",
            corporate_action_clear=True,
        )
        self.assertEqual(wrong["reason"], "QUOTE_SECURITY_MISMATCH")

    def test_ledger_idempotency_conflict_and_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "ledger.jsonl"
            row = {"id": "one", "action": "NO_SIGNAL"}
            stored = g.append_once(row, path)
            self.assertEqual(g.append_once(row, path), stored)
            self.assertEqual(len(path.read_text().splitlines()), 1)
            with self.assertRaises(ValueError):
                g.append_once({**row, "action": "BUY"}, path)
            path.write_text(path.read_text().replace("NO_SIGNAL", "BUY"))
            with self.assertRaises(ValueError):
                g.append_once({"id": "two"}, path)


if __name__ == "__main__":
    unittest.main()
