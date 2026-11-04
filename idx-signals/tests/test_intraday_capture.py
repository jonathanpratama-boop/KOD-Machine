"""Finite capture tests: no public requests and no real outcome data."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from idxsig.runtime.data import SnapshotError
from idxsig.runtime.intraday import PublicResponse, collect_intraday, load_intraday

NOW = datetime(2026, 11, 4, 12, 3, tzinfo=timezone.utc)


def candle(at, interval=60, microseconds=False):
    scale = 1_000_000 if microseconds else 1000
    return [
        int(at.timestamp()) * scale,
        "100",
        "110",
        "90",
        "105",
        "20",
        int((at + timedelta(seconds=interval)).timestamp()) * scale - 1,
        "2000",
    ]


class IntradayCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "capture.json"
        self.evidence = self.root / "evidence"
        self.calls = []
        self.candles = [
            candle(NOW - timedelta(minutes=2)),
            candle(NOW - timedelta(minutes=1), microseconds=True),
        ]

    def fetcher(self, path, params, *, timeout):
        self.calls.append((path, params))
        if path.endswith("/time"):
            body = {"serverTime": int(NOW.timestamp() * 1000)}
        elif path.endswith("/exchangeInfo"):
            body = {
                "symbols": [
                    {
                        "symbol": symbol,
                        "baseAsset": symbol[:-4],
                        "quoteAsset": "USDT",
                        "status": "TRADING",
                        "isSpotTradingAllowed": True,
                    }
                    for symbol in json.loads(params["symbols"])
                ]
            }
        elif path.endswith("/klines"):
            body = self.candles
        elif path.endswith("/bookTicker"):
            body = {
                "symbol": params["symbol"],
                "bidPrice": "100",
                "askPrice": "101",
                "bidQty": "2",
                "askQty": "3",
            }
        else:
            body = {
                "lastUpdateId": 1,
                "bids": [["100", "2"], ["99", "3"]],
                "asks": [["101", "2"], ["102", "3"]],
            }
        return PublicResponse(200, json.dumps(body).encode())

    def capture(self, **kwargs):
        options = {
            "scheduled_at": NOW.isoformat(),
            "bars": 2,
            "clock": lambda: NOW,
            "fetcher": self.fetcher,
            "evidence_kind": "synthetic",
        }
        options.update(kwargs)
        with patch(
            "urllib.request.OpenerDirector.open", side_effect=AssertionError("network attempted")
        ):
            return collect_intraday(
                self.output, self.evidence, options.pop("symbols", ["BTCUSDT"]), **options
            )

    def test_complete_capture_has_raw_evidence_membership_and_unknown_trigger(self):
        value = self.capture()
        self.assertEqual(value["status"], "COLLECTED")
        self.assertEqual(value["coverage"]["complete"], 1)
        self.assertEqual(len(value["bars"]), 2)
        self.assertEqual(len(value["evidence"]), 5)
        self.assertIsNone(value["threshold_crossing_at"])
        self.assertFalse(value["entry_permission"])
        self.assertEqual(value["quotes"][0]["execution_venue_role"], "PROXY_ONLY")
        self.assertIsNone(value["quotes"][0]["source_time"])
        self.assertEqual(value["clock_integrity"]["ntp_status"], "UNVERIFIED")
        self.assertTrue((self.evidence / value["membership_path"]).exists())
        self.assertTrue(all(request["elapsed_ns"] >= 0 for request in value["requests"]))

    def test_forming_candle_is_excluded_and_gap_is_never_filled(self):
        self.candles = [self.candles[0], candle(NOW)]
        value = self.capture()
        self.assertEqual(value["status"], "PARTIAL")
        self.assertEqual(len(value["bars"]), 1)
        self.assertEqual(len(value["symbol_status"][0]["missing_bar_open_times"]), 1)
        self.assertEqual(len(value["excluded_bars"]), 1)

    def test_block_stops_provider_and_retains_error_bytes_and_denominator(self):
        fetcher = Mock(return_value=PublicResponse(451, b"blocked by provider"))
        value = self.capture(fetcher=fetcher, symbols=["BTCUSDT", "ETHUSDT"])
        self.assertEqual(fetcher.call_count, 1)
        self.assertEqual(value["status"], "BLOCKED")
        self.assertEqual(value["coverage"]["requested"], 2)
        self.assertEqual(value["coverage"]["not_attempted"], 2)
        self.assertEqual(
            (self.evidence / value["evidence"][0]["path"]).read_bytes(), b"blocked by provider"
        )

    def test_rate_limit_does_not_retry_or_switch_hosts(self):
        fetcher = Mock(return_value=PublicResponse(429, b'{"code":-1003}', {"retry_after": "60"}))
        value = self.capture(fetcher=fetcher)
        self.assertEqual(fetcher.call_count, 1)
        self.assertEqual(value["requests"][0]["retry_after"], "60")

    def test_captcha_response_stops_subsequent_requests(self):
        fetcher = Mock(return_value=PublicResponse(200, b"<html>captcha</html>"))
        value = self.capture(fetcher=fetcher)
        self.assertEqual(fetcher.call_count, 1)
        self.assertEqual(value["status"], "BLOCKED")

    def test_missing_metadata_is_reported_without_invented_instrument(self):
        original = self.fetcher

        def missing(path, params, *, timeout):
            return (
                PublicResponse(200, b'{"symbols":[]}')
                if path.endswith("exchangeInfo")
                else original(path, params, timeout=timeout)
            )

        value = self.capture(fetcher=missing)
        self.assertEqual(value["coverage"]["failed"], 1)
        self.assertEqual(value["bars"], [])

    def test_invalid_config_and_future_schedule_make_no_request(self):
        for kwargs in (
            {"interval": "1d"},
            {"symbols": ["BTCUSDT", "BTCUSDT"]},
            {"bars": True},
            {"scheduled_at": "2026-11-05T00:00:00Z"},
            {"timeout": float("nan")},
        ):
            fetcher = Mock()
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.capture(fetcher=fetcher, **kwargs)
            fetcher.assert_not_called()

    def test_completed_capture_replay_performs_no_requests(self):
        first = self.capture()
        fetcher = Mock(side_effect=AssertionError("replay attempted network"))
        second = self.capture(fetcher=fetcher)
        self.assertEqual(first, second)
        fetcher.assert_not_called()
        with self.assertRaisesRegex(ValueError, "different scheduled"):
            self.capture(fetcher=fetcher, symbols=["ETHUSDT"])

    def test_tampered_raw_or_normalized_quote_is_rejected(self):
        value = self.capture()
        disk = json.loads(self.output.read_text())
        disk["quotes"][0]["ask"] = "101.5"
        self.output.write_text(json.dumps(disk))
        with self.assertRaisesRegex(SnapshotError, "differs from raw"):
            load_intraday(self.output, self.evidence)
        self.output.write_text(
            json.dumps({key: item for key, item in value.items() if key != "capture_sha256"})
        )
        (self.evidence / value["evidence"][0]["path"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(SnapshotError, "hash mismatch"):
            load_intraday(self.output, self.evidence)

    def test_duplicate_candles_fail_symbol_without_duplicate_rows(self):
        self.candles.append(self.candles[0])
        value = self.capture()
        self.assertEqual(value["bars"], [])
        self.assertEqual(value["status"], "PARTIAL")
        self.assertIn("duplicate", value["symbol_status"][0]["reason"])

    def test_source_clock_skew_is_estimate_never_ntp_verification(self):
        original = self.fetcher

        def skew(path, params, *, timeout):
            return (
                PublicResponse(
                    200, json.dumps({"serverTime": int(NOW.timestamp() * 1000) + 7000}).encode()
                )
                if path.endswith("/time")
                else original(path, params, timeout=timeout)
            )

        value = self.capture(fetcher=skew)
        self.assertEqual(value["clock_integrity"]["source_offset_midpoint_ms"], 7000)
        self.assertEqual(
            value["clock_integrity"]["source_clock_status"], "MIDPOINT_ESTIMATE_NOT_NTP"
        )
        self.assertIsNone(value["clock_integrity"]["ntp_offset_ms"])

    def test_deleted_normalized_observation_is_rejected(self):
        self.capture()
        disk = json.loads(self.output.read_text())
        disk["bars"].pop()
        self.output.write_text(json.dumps(disk))
        with self.assertRaisesRegex(SnapshotError, "membership differs"):
            load_intraday(self.output, self.evidence)

    def test_five_minute_window_is_frozen_before_requests(self):
        end = NOW.replace(minute=0)
        self.candles = [
            candle(end - timedelta(minutes=10), interval=300),
            candle(end - timedelta(minutes=5), interval=300),
        ]
        value = self.capture(interval="5m")
        self.assertEqual(value["window_end_at"], "2026-11-04T12:00:00Z")
        self.assertEqual(value["status"], "COLLECTED")
        params = next(params for path, params in self.calls if path.endswith("/klines"))
        self.assertEqual(params["endTime"], int(end.timestamp()) * 1000 - 1)

    def test_transport_failure_is_recorded_without_invented_receipt(self):
        fetcher = Mock(side_effect=TimeoutError("provider timeout"))
        value = self.capture(fetcher=fetcher)
        self.assertEqual(value["coverage"]["failed"], 1)
        self.assertEqual(value["evidence"], [])
        self.assertIsNone(value["requests"][0]["received_at"])
        self.assertEqual(value["requests"][0]["status"], "FAILED")
        self.assertEqual(value["requests"][0]["recorded_at"], "2026-11-04T12:03:00Z")

    def test_complete_coverage_cannot_be_claimed_for_a_missing_bar(self):
        self.candles.pop()
        self.capture()
        disk = json.loads(self.output.read_text())
        disk["symbol_status"][0]["status"] = "COMPLETE"
        disk["coverage"].update(complete=1, partial=0)
        self.output.write_text(json.dumps(disk))
        with self.assertRaisesRegex(SnapshotError, "complete coverage"):
            load_intraday(self.output, self.evidence)

    def test_metadata_asset_identity_must_match_symbol(self):
        original = self.fetcher

        def mismatch(path, params, *, timeout):
            return (
                PublicResponse(
                    200,
                    b'{"symbols":[{"symbol":"BTCUSDT","baseAsset":"DOGE","quoteAsset":"USDT","status":"TRADING"}]}',
                )
                if path.endswith("/exchangeInfo")
                else original(path, params, timeout=timeout)
            )

        value = self.capture(fetcher=mismatch)
        self.assertEqual(value["coverage"]["failed"], 1)
        self.assertEqual(value["instruments"], [])

    def test_string_clock_integrates_with_runtime_clock(self):
        value = self.capture(clock=lambda: "2026-11-04T12:03:00Z")
        self.assertEqual(value["status"], "COLLECTED")

    def test_partial_capture_cannot_be_promoted_by_relabeling_status(self):
        self.candles.pop()
        self.capture()
        disk = json.loads(self.output.read_text())
        disk["status"] = "COLLECTED"
        self.output.write_text(json.dumps(disk))
        with self.assertRaisesRegex(SnapshotError, "overall status"):
            load_intraday(self.output, self.evidence)

    def test_instrument_metadata_cannot_be_changed_after_capture(self):
        self.capture()
        disk = json.loads(self.output.read_text())
        disk["instruments"][0]["base_asset"] = "DOGE"
        self.output.write_text(json.dumps(disk))
        with self.assertRaisesRegex(SnapshotError, "instrument differs"):
            load_intraday(self.output, self.evidence)


if __name__ == "__main__":
    unittest.main()
