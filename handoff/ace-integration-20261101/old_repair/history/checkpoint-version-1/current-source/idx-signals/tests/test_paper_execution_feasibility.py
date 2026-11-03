"""Adversarial synthetic fixtures: no exchange requests, orders or ledger writes."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from idxsig.paper_execution_feasibility import BookSnapshot, FilterSnapshot, Intent, estimate

T = datetime(2026, 10, 31, 18, tzinfo=timezone.utc)


class Feasibility(unittest.TestCase):
    def setUp(self):
        self.rows = (
            {"filterType": "PRICE_FILTER", "minPrice": "0.01", "maxPrice": "10000", "tickSize": "0.05"},
            {"filterType": "LOT_SIZE", "minQty": "0.1", "maxQty": "100", "stepSize": "0.1"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
            {"filterType": "NOTIONAL", "minNotional": "10", "maxNotional": "10000"},
        )
        self.filters = FilterSnapshot("AAAUSDT", T - timedelta(seconds=1), "fixture/exchangeInfo", self.rows)
        self.book = BookSnapshot("AAAUSDT", T, "fixture/depth",
                                 ((D("99"), D("2")), (D("98"), D("3"))),
                                 ((D("100"), D("1")), (D("101"), D("2"))))
        self.intent = Intent("AAAUSDT", "BUY", D("2"), D("102"), T)

    def run_estimate(self, **kw):
        args = dict(intent=self.intent, book=self.book, filters=self.filters, now=T,
                    max_book_age=timedelta(seconds=5), max_filter_age=timedelta(minutes=1), fee_rate=D("0.001"))
        args.update(kw)
        return estimate(**args)

    def filters_with(self, index, **fields):
        rows = list(self.rows)
        rows[index] = {**rows[index], **fields}
        return replace(self.filters, filters=tuple(rows))

    def test_complete_depth_fee_and_no_input_mutation(self):
        out = self.run_estimate()
        self.assertEqual((out.status, out.filled, out.notional, out.fee_quote), ("COMPLETE", D("2"), D("201"), D("0.201")))
        self.assertEqual(out.fills, ((D("100"), D("1")), (D("101"), D("1"))))
        self.assertEqual(self.book.asks[-1][1], D("2"))

    def test_existing_microstructure_depth_walk_agrees_in_simple_case(self):
        # Reuse the existing walker as a cross-check, not float arithmetic for filters.
        from idxsig.microstructure import book_fill
        old = book_fill([(100., 1.), (101., 2.)], 201., 99.5, "buy")
        out = self.run_estimate()
        self.assertTrue(old["complete"])
        self.assertAlmostEqual(old["vwap"], float(out.notional / out.filled))

    def test_buy_rounding_never_increases_price_or_quantity(self):
        out = self.run_estimate(intent=replace(self.intent, quantity=D("2.09"), limit_price=D("101.049")))
        self.assertEqual((out.quantity, out.limit_price), (D("2.0"), D("101.00")))

    def test_sell_rounds_limit_up_and_walks_bids(self):
        out = self.run_estimate(intent=replace(self.intent, side="SELL", quantity=D("2.99"), limit_price=D("97.981")))
        self.assertEqual((out.quantity, out.limit_price, out.notional), (D("2.9"), D("98.00"), D("286.2")))

    def test_min_notional_checked_after_rounding(self):
        out = self.run_estimate(intent=replace(self.intent, quantity=D("0.199"), limit_price=D("99.99")))
        self.assertEqual(out.reason, "MIN_NOTIONAL")

    def test_max_notional_and_quantity_bounds(self):
        self.assertEqual(self.run_estimate(filters=self.filters_with(3, maxNotional="100")).reason, "MAX_NOTIONAL")
        self.assertEqual(self.run_estimate(intent=replace(self.intent, quantity=D("100.1"))).reason, "LOT_SIZE")
        self.assertEqual(self.run_estimate(intent=replace(self.intent, quantity=D("0.09"))).reason, "LOT_SIZE")

    def test_missing_filter_or_step_rejected(self):
        for rows in (self.rows[1:], self.rows[:2], (self.rows[0], {"filterType": "LOT_SIZE", "minQty": "0.1", "maxQty": "100"}, self.rows[2])):
            with self.subTest(rows=rows):
                self.assertEqual(self.run_estimate(filters=replace(self.filters, filters=rows)).status, "REJECTED")

    def test_zero_lot_step_fails_closed_but_zero_price_tick_is_disabled(self):
        self.assertEqual(self.run_estimate(filters=self.filters_with(1, stepSize="0")).status, "REJECTED")
        out = self.run_estimate(filters=self.filters_with(0, tickSize="0"), intent=replace(self.intent, limit_price=D("101.019")))
        self.assertEqual(out.limit_price, D("101.019"))
        self.assertEqual(out.status, "COMPLETE")

    def test_unknown_and_duplicate_filters_fail_closed(self):
        for row in ({"filterType": "PERCENT_PRICE"}, self.rows[0]):
            self.assertEqual(self.run_estimate(filters=replace(self.filters, filters=self.rows + (row,))).status, "REJECTED")

    def test_partial_depth_and_unfilled_rest_are_explicit(self):
        out = self.run_estimate(intent=replace(self.intent, quantity=D("4")))
        self.assertEqual((out.status, out.filled, out.unfilled, out.reason), ("PARTIAL", D("3"), D("1"), "INSUFFICIENT_DISPLAYED_DEPTH"))
        self.assertEqual(out.fee_quote, out.notional * D("0.001"))

    def test_limit_bounded_partial_and_no_touch(self):
        out = self.run_estimate(intent=replace(self.intent, limit_price=D("100")))
        self.assertEqual((out.status, out.filled, out.reason), ("PARTIAL", D("1"), "LIMIT_PRICE"))
        out = self.run_estimate(intent=replace(self.intent, limit_price=D("99")))
        self.assertEqual((out.status, out.filled, out.reason, out.fee_quote), ("UNFILLED", D("0"), "LIMIT_PRICE", D("0")))

    def test_dust_and_zero_displayed_quantity_not_invented(self):
        book = replace(self.book, asks=((D("100"), D("0.09")), (D("101"), D("0"))))
        out = self.run_estimate(book=book)
        self.assertEqual((out.status, out.filled), ("UNFILLED", D("0")))

    def test_stale_book_and_filters(self):
        self.assertEqual(self.run_estimate(now=T + timedelta(seconds=6)).reason, "STALE_BOOK")
        self.assertEqual(self.run_estimate(filters=replace(self.filters, observed_at=T - timedelta(minutes=2))).reason, "STALE_FILTERS")

    def test_future_book_filters_and_intent(self):
        later = T + timedelta(seconds=1)
        self.assertEqual(self.run_estimate(book=replace(self.book, observed_at=later)).reason, "FUTURE_BOOK")
        self.assertEqual(self.run_estimate(filters=replace(self.filters, observed_at=later)).reason, "FUTURE_FILTERS")
        self.assertEqual(self.run_estimate(intent=replace(self.intent, placed_at=later)).reason, "FUTURE_INTENT")

    def test_book_before_intent_and_filters_after_intent(self):
        self.assertEqual(self.run_estimate(book=replace(self.book, observed_at=T - timedelta(seconds=1))).reason, "BOOK_BEFORE_INTENT")
        self.assertEqual(self.run_estimate(intent=replace(self.intent, placed_at=T - timedelta(seconds=2))).reason, "FILTERS_AFTER_INTENT")

    def test_missing_data_identity_and_timezone(self):
        for kw in ({"book": None}, {"filters": None}, {"book": replace(self.book, symbol="BBB")}, {"now": T.replace(tzinfo=None)}, {"book": replace(self.book, source="")}):
            with self.subTest(kw=kw):
                self.assertEqual(self.run_estimate(**kw).status, "REJECTED")

    def test_malformed_books_and_nonfinite_inputs(self):
        for asks in (((D("100"), D("1")), (D("100"), D("2"))), ((D("100"), D("-1")),), ((D("98"), D("1")),), ()):
            with self.subTest(asks=asks):
                self.assertEqual(self.run_estimate(book=replace(self.book, asks=asks)).status, "REJECTED")
        for n in (D("NaN"), D("Infinity"), D("-1"), 1.01):
            self.assertEqual(self.run_estimate(intent=replace(self.intent, quantity=n)).status, "REJECTED")

    def test_invalid_filter_numbers_and_fees(self):
        for n in ("NaN", "-1", "garbage", 0.1):
            self.assertEqual(self.run_estimate(filters=self.filters_with(0, tickSize=n)).status, "REJECTED")
        for fee in (D("1"), D("-0.1"), D("NaN")):
            self.assertEqual(self.run_estimate(fee_rate=fee).status, "REJECTED")

    def test_disabled_price_bounds_and_invalid_bounds(self):
        self.assertEqual(self.run_estimate(filters=self.filters_with(0, minPrice="0", maxPrice="0")).status, "COMPLETE")
        self.assertEqual(self.run_estimate(filters=self.filters_with(0, minPrice="200", maxPrice="100")).status, "REJECTED")
        self.assertEqual(self.run_estimate(filters=self.filters_with(3, minNotional="20000")).status, "REJECTED")

    def test_filled_never_exceeds_request_or_displayed_depth(self):
        for raw in ("0.1", "0.29", "1", "2.01", "3", "4", "10"):
            out = self.run_estimate(intent=replace(self.intent, quantity=D(raw)))
            self.assertLessEqual(out.filled, out.quantity)
            self.assertEqual(out.filled + out.unfilled, out.quantity)
            self.assertLessEqual(out.filled, D("3"))
            for price, qty in out.fills:
                self.assertLessEqual(qty, dict(self.book.asks)[price])
                self.assertLessEqual(price, out.limit_price)


if __name__ == "__main__":
    unittest.main()
