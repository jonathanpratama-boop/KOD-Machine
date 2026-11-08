import unittest
import pandas as pd
from infer import validate_input, event_seed


class CausalityTests(unittest.TestCase):
    def setUp(self):
        times = pd.date_range(end='2025-01-08T00:00:00Z', periods=168, freq='h')
        self.frame = pd.DataFrame({name: [1.0] * 168 for name in ['open', 'high', 'low', 'close', 'volume', 'amount']})
        self.frame['timestamps'] = times
        self.frame['close_time'] = times + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1)
        self.row = {'decision_time': '2025-01-08T01:00:00Z', 'last_observed_close': 1.0}

    def test_ongoing_candle_is_rejected(self):
        self.frame.loc[167, 'close_time'] = pd.Timestamp(self.row['decision_time'])
        with self.assertRaisesRegex(ValueError, 'unfinished'):
            validate_input(self.frame, self.row)

    def test_gap_or_future_timestamp_is_rejected(self):
        self.frame.loc[167, 'timestamps'] += pd.Timedelta(hours=1)
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            validate_input(self.frame, self.row)

    def test_correct_completed_window_and_stable_seed(self):
        self.assertEqual(len(validate_input(self.frame, self.row)), 168)
        self.assertEqual(event_seed('event'), event_seed('event'))
        self.assertNotEqual(event_seed('event'), event_seed('another'))


if __name__ == '__main__':
    unittest.main()
