from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from score_replay import load_decisions, periods, price_marks, sha, summarize


def epoch(day):
    return datetime.fromisoformat(day + "T09:30").replace(tzinfo=ZoneInfo("America/New_York")).timestamp()


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.row = {"event_id": "demo", "ticker": "TEST", "eligible": True, "revenue_buy": True,
                    "margin_buy": False, "release_published_at": "2025-11-26T21:10:00+00:00"}
        self.schedule, self.days = periods(self.row)
        self.chart = {"meta": {"symbol": "TEST", "currency": "USD", "instrumentType": "EQUITY",
                               "exchangeTimezoneName": "America/New_York"},
                      "timestamp": [epoch(v) for v in self.days.values()],
                      "indicators": {"quote": [{"open": [10] * 4, "close": [10, 12, 9, 11],
                                                 "low": [9] * 4, "high": [12] * 4, "volume": [55] * 4}]}}

    def test_post_close_next_session_holiday_and_costs(self):
        self.assertEqual(self.schedule["entry_session"], "2025-11-28")
        self.assertEqual(self.days[3], "2025-12-02")
        marks = price_marks(self.chart, "TEST", self.days, False)
        self.assertAlmostEqual(float(marks["1"]["revenue_usd"]), -4.98753117)
        self.assertEqual(marks["1"]["margin_usd"], "0")
        self.assertGreater(Decimal(marks["1"]["difference_usd"]), 0)

    def test_margin_buys_both_arms_match(self):
        marks = price_marks(self.chart, "TEST", self.days, True)
        self.assertEqual(Decimal(marks["20"]["difference_usd"]), 0)
        totals = summarize([{"marks": marks, "margin_buy": True, "entered": True}])
        self.assertEqual(totals["20"]["informative_pairs"], 0)
        self.assertEqual(totals["20"]["scored_pairs"], 1)

    def test_block_partial_horizons_on_actions_or_missing_marks(self):
        self.chart["events"] = {"dividends": {"id": {"date": epoch(self.days[5])}}}
        self.chart["indicators"]["quote"][0]["close"][1] = None
        marks = price_marks(self.chart, "TEST", self.days, False)
        self.assertIn("revenue_usd", marks["1"])
        self.assertEqual(marks["3"]["unavailable"], "Incomplete OHLCV")
        self.assertIn("split or dividend", marks["20"]["unavailable"])
        self.assertIsNone(summarize([{"marks": marks, "margin_buy": False, "entered": True}])["20"]["revenue_usd"])
        self.assertEqual(summarize([])["1"]["scored_pairs"], 0)

    def test_missing_price_session_or_unrelated_symbol(self):
        self.chart["timestamp"][-1] = epoch("2026-01-06")
        self.assertEqual(price_marks(self.chart, "TEST", self.days, True)["20"]["unavailable"], "Daily bar missing")
        with self.assertRaises(ValueError):
            price_marks(self.chart, "OTHER", self.days, True)

    def test_changed_decisions_rejected_before_price_io(self):
        with tempfile.TemporaryDirectory() as work:
            rows = Path(work) / "decisions.json"
            seal = Path(work) / "seal.json"
            raw = json.dumps([self.row]).encode()
            rows.write_bytes(raw)
            seal.write_text(json.dumps({"decisions_sha256": sha(raw)}))
            self.assertEqual(load_decisions(rows, seal)[0], [self.row])
            rows.write_bytes(raw + b"\n")
            with self.assertRaisesRegex(ValueError, "frozen"):
                load_decisions(rows, seal)


if __name__ == "__main__":
    unittest.main()
