"""Independent network-adapter and orchestration checks; no external calls."""

from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "guidance_margin_run", Path(__file__).with_name("run.py")
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def event():
    return {
        "kind": "ADMISSION",
        "status": "ADMITTED",
        "event_id": "one",
        "ticker": "TEST",
        "issuer_cik": "123",
        "schedule": {"entry_session": "2026-11-17"},
    }


def response():
    stamp = int(datetime(2026, 11, 17, 14, 30, tzinfo=timezone.utc).timestamp())
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "TEST",
                        "currency": "USD",
                        "instrumentType": "EQUITY",
                        "exchangeTimezoneName": "America/New_York",
                    },
                    "timestamp": [stamp],
                    "indicators": {
                        "quote": [
                            {
                                "open": [10],
                                "high": [12],
                                "low": [9],
                                "close": [11],
                                "volume": [10000],
                            }
                        ]
                    },
                    "events": {},
                }
            ],
        }
    }


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)

    def fetch(self, packet):
        raw = json.dumps(packet).encode()
        with patch.object(runner.urllib.request, "urlopen", return_value=io.BytesIO(raw)):
            return runner.fetch_bar(self.state, event(), "2026-11-17")

    def test_price_evidence_is_retained_and_correct_identity_is_required(self):
        row = self.fetch(response())
        self.assertTrue(row["source_sha256"])
        self.assertTrue(row["corporate_action_clear"])
        self.assertEqual(len(list((self.state / "prices" / "TEST").glob("*.json"))), 1)
        for field, value in (
            ("symbol", "DIFFERENT"),
            ("currency", "EUR"),
            ("instrumentType", "CRYPTOCURRENCY"),
            ("exchangeTimezoneName", "Europe/London"),
        ):
            packet = response()
            packet["chart"]["result"][0]["meta"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.fetch(packet)

    def test_reported_split_blocks_unadjusted_price_accounting(self):
        packet = response()
        result = packet["chart"]["result"][0]
        result["events"] = {
            "splits": {"one": {"date": result["timestamp"][0], "splitRatio": "1:10"}}
        }
        row = self.fetch(packet)
        self.assertFalse(row["corporate_action_clear"])
        self.assertEqual(row["reported_corporate_actions"][0]["type"], "splits")

    def test_future_entry_and_already_recorded_session_do_not_fetch_or_fill(self):
        for rows, closed in (
            ([event()], "2026-11-16"),
            ([event(), {"kind": "BAR", "event_id": "one", "session": "2026-11-17"}], "2026-11-17"),
            ([event(), {"kind": "MISSED_ENTRY", "event_id": "one"}], "2026-11-18"),
        ):
            with (
                patch.object(runner.trial, "records", return_value=rows),
                patch.object(runner, "latest_closed_session", return_value=closed),
                patch.object(runner, "fetch_bar") as fetch,
            ):
                self.assertEqual(runner.update_prices(self.state, self.state / "journal"), [])
                fetch.assert_not_called()

    def test_exchange_calendar_excludes_weekend_and_unfinished_sessions(self):
        self.assertEqual(
            runner.latest_closed_session(datetime(2026, 11, 16, 20, 59, tzinfo=timezone.utc)),
            "2026-11-13",
        )
        self.assertEqual(
            runner.latest_closed_session(datetime(2026, 11, 16, 21, 21, tzinfo=timezone.utc)),
            "2026-11-16",
        )

    def test_existing_prices_settle_before_new_reviews_use_cash(self):
        order = []
        with (
            patch.object(runner.trial, "initialize"),
            patch.object(runner.trial, "status", return_value={"candidates": 0, "admitted": 0}),
            patch.object(
                runner, "update_prices", side_effect=lambda *args: order.append("prices") or []
            ),
            patch.object(
                runner, "import_reviews", side_effect=lambda *args: order.append("reviews") or []
            ),
        ):
            runner.cycle(self.state, self.state / "ciks.json", skip_feed=True)
        self.assertEqual(order, ["prices", "reviews"])


if __name__ == "__main__":
    unittest.main()
