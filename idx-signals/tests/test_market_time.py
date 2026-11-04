"""Timestamp and mapping regressions use synthetic data only."""

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from idxsig import e6
from idxsig.market_time import binance_bar_end, binance_datetime, binance_datetimes
from idxsig.runtime.data import SnapshotError, _milliseconds
from idxsig.symbols import resolve_futures_symbol


class MarketTimeTests(unittest.TestCase):
    def test_mixed_millisecond_and_microsecond_rows_keep_their_year(self):
        values = pd.Series([1735686000000, 1735689600000000], index=[4, 8], name="time")
        actual = binance_datetimes(values)
        self.assertEqual(actual.index.tolist(), [4, 8])
        self.assertEqual(actual.astype(str).tolist(), ["2024-12-31 23:00:00+00:00", "2025-01-01 00:00:00+00:00"])
        self.assertEqual(binance_datetimes(values.tolist()).dt.year.tolist(), [2024, 2025])

    def test_microsecond_close_does_not_round_into_next_bar(self):
        self.assertEqual(_milliseconds(1735693199999999), "2025-01-01T00:59:59.999999Z")
        self.assertEqual(binance_bar_end(1735693199999999), datetime(2025, 1, 1, 1, tzinfo=timezone.utc))

    def test_bad_units_nonfinite_fractional_and_boolean_are_rejected(self):
        for value in (True, None, 1735689600, 1735689600000000000, "NaN", "Infinity", -1, 1735689600000.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                binance_datetime(value)
        with self.assertRaises(SnapshotError):
            _milliseconds("NaN")

    def test_e6_holdout_is_rejected_before_manifest_or_archive_read(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("manifest opened")), patch.object(e6, "_read_zip", side_effect=AssertionError("archive opened")):
            with self.assertRaises(e6.HoldoutError):
                e6.load_manifest(Path("never-open.jsonl"), pd.Timestamp("2025-01-01", tz="UTC"))

    def test_e6_normalizes_per_row_before_building_hourly(self):
        header = '{}\n' + json.dumps({"symbol": "BTCUSDT", "month": "2022-12", "file": "synthetic.zip"})
        frame = pd.DataFrame({"open_time": [1672524000000, 1672527600000000],
                              "open": [1, 1], "high": [1, 1], "low": [1, 1], "close": [1, 1],
                              "quote": [1, 1], "tb_quote": [1, 1]})
        with patch.object(Path, "read_text", return_value=header), patch.object(e6, "_read_zip", return_value=frame), patch.object(e6, "build_hourly") as build:
            build.return_value.symbols = ["BTCUSDT"]
            e6.load_manifest(Path("synthetic.jsonl"))
        self.assertEqual(build.call_args.args[0]["BTCUSDT"].t.dt.year.tolist(), [2022, 2022])


class ContractIdentityTests(unittest.TestCase):
    def test_explicit_shib_multiplier_does_not_scale_funding_rate(self):
        row = resolve_futures_symbol("1000SHIBUSDT", at="2026-11-04T00:00:00Z")
        self.assertEqual(row["spot_symbol"], "SHIBUSDT")
        self.assertEqual(row["base_units_per_contract"], 1000)
        self.assertEqual(row["funding_rate_multiplier"], 1)
        self.assertEqual(row["availability"], "REQUIRES_AS_OF_EXCHANGE_METADATA")

    def test_mapping_is_not_applied_before_announcement_effective_date(self):
        self.assertEqual(resolve_futures_symbol("1000SHIBUSDT", at="2020-01-01T00:00:00Z")["status"], "NOT_YET_EFFECTIVE")

    def test_unknown_number_prefix_is_not_guessed(self):
        row = resolve_futures_symbol("1000UNKNOWNUSDT")
        self.assertEqual(row["status"], "UNMAPPED")
        self.assertIsNone(row["spot_symbol"])
        self.assertEqual(row["availability"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
