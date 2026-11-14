import unittest
from pathlib import Path
import hashlib
import json
import pandas as pd
from prepare import archive_time, causal_context, parse_kline_csv


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.trigger = pd.Timestamp("2025-01-08T00:00:00Z")
        self.decision = self.trigger + pd.Timedelta(hours=1)
        grid = pd.date_range(end=self.trigger, periods=168, freq="h")
        self.frame = pd.DataFrame({"open": 1., "high": 2., "low": .5, "close": 1.1,
                                   "volume": 10., "amount": 11.,
                                   "close_time": grid + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1)}, index=grid)

    def test_milliseconds_and_microseconds_match(self):
        self.assertEqual(archive_time(1735689600000), archive_time(1735689600000000))
        self.assertEqual(archive_time(1735689600000000), pd.Timestamp("2025-01-01T00:00:00Z"))

    def test_full_context_keeps_only_available_bars(self):
        future = self.frame.iloc[[-1]].copy()
        future.index += pd.Timedelta(hours=1)
        future["close"] = 999.
        context = causal_context(pd.concat([self.frame, future]), self.trigger, self.decision)
        self.assertEqual(len(context), 168)
        self.assertEqual(context.iloc[-1]["close"], 1.1)

    def test_rejects_unclosed_final_candle(self):
        self.frame.loc[self.trigger, "close_time"] = self.decision
        with self.assertRaisesRegex(ValueError, "unclosed"):
            causal_context(self.frame, self.trigger, self.decision)

    def test_rejects_missing_or_duplicate_hours(self):
        for frame in [self.frame.iloc[1:], pd.concat([self.frame, self.frame.iloc[[-1]]])]:
            with self.assertRaisesRegex(ValueError, "missing_or_duplicate"):
                causal_context(frame, self.trigger, self.decision)

    def test_literal_verified_archive_fixture(self):
        fixtures = Path(__file__).parent / "fixtures"
        raw = (fixtures / "real_kline.csv").read_bytes()
        source = json.loads((fixtures / "real_kline_source.json").read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), source["fixture_sha256"])
        frame = parse_kline_csv(raw)
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.index[0], pd.Timestamp("2025-11-01T00:00:00Z"))
        self.assertEqual(frame.index[1], pd.Timestamp("2025-11-01T01:00:00Z"))
        self.assertEqual(frame.iloc[0]["close_time"], pd.Timestamp("2025-11-01T00:59:59.999999Z"))
        self.assertEqual(frame.iloc[0]["amount"], 244485.36591)


if __name__ == "__main__":
    unittest.main()
