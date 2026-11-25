"""Independent behavioral tests: temporary server failures must not seal a stop.

No network or real collector state. Expectations come from the recovery contract.
"""
import datetime as dt
import json
from pathlib import Path
import tempfile
import threading
import types
import unittest

import provider_recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.now = 100.0
        self.sleeps = []
        self.calls = []
        owner = self

        class Lane:
            def _gate(lane):
                if any((lane.root / p).exists() for p in ('PAUSED.json', 'PROVIDER_STOP.json')):
                    raise RuntimeError('stopped')

        def atomic(path, value):
            path.write_text(json.dumps(value))

        runtime = types.SimpleNamespace(RestLanes=Lane, _atomic=atomic, iso=lambda d: d.isoformat())
        def sleep(seconds):
            owner.sleeps.append(seconds)
            owner.now += seconds

        provider_recovery.install(runtime, monotonic=lambda: owner.now, sleep=sleep)
        self.lane = Lane()
        self.lane.root = self.root
        self.lane.lock = threading.RLock()
        self.lane.clock = lambda: dt.datetime(2026, 11, 16, tzinfo=dt.timezone.utc)
        self.response = {'status': 200, 'headers': {'X-MBX-USED-WEIGHT-1M': '2'}, 'body': b'data'}
        def network(url, timeout, max_bytes):
            owner.calls.append((url, timeout, max_bytes))
            return owner.response
        self.lane.network = network

    def request(self, timeout=10):
        return self.lane._market_transport('https://api.binance.com/api/v3/ticker/bookTicker', timeout, 4096)

    def test_failed_response_stays_failed_and_identical(self):
        for code in (500, 502, 503, 504, 599):
            with self.subTest(code=code):
                self.now += 100
                self.response = {'status': code, 'headers': {}, 'body': b'provider failure'}
                self.assertIs(self.request(), self.response)
                self.assertFalse((self.root / 'PROVIDER_STOP.json').exists())

    def test_access_and_rate_restrictions_still_stop(self):
        for code in (403, 418, 429, 451):
            with self.subTest(code=code):
                self.response = {'status': code, 'headers': {}, 'body': b'restricted'}
                self.assertIs(self.request(), self.response)
                stop = self.root / 'PROVIDER_STOP.json'
                self.assertEqual(json.loads(stop.read_text())['reason'], 'PROVIDER_ACCESS_OR_RATE_STOP')
                with self.assertRaises(RuntimeError):
                    self.request()
                stop.unlink()

    def test_retry_after_is_respected_even_on_server_error(self):
        self.response = {'status': 503, 'headers': {'Retry-After': '120'}, 'body': b'try later'}
        self.request()
        self.assertEqual(json.loads((self.root / 'PROVIDER_STOP.json').read_text())['reason'], 'PROVIDER_ACCESS_OR_RATE_STOP')

    def test_ambiguous_success_or_client_failure_still_stops(self):
        for code in (200, 400, 404, 499):
            with self.subTest(code=code):
                self.response = {'status': code, 'headers': {}, 'body': b'unknown'}
                self.request()
                stop = self.root / 'PROVIDER_STOP.json'
                self.assertEqual(json.loads(stop.read_text())['reason'], 'SHARED_WEIGHT_TELEMETRY_UNAVAILABLE')
                stop.unlink()

    def test_high_weight_still_stops_on_failure(self):
        self.response = {'status': 500, 'headers': {'X-MBX-USED-WEIGHT-1M': '301'}, 'body': b'failure'}
        self.request()
        self.assertEqual(json.loads((self.root / 'PROVIDER_STOP.json').read_text())['reason'], 'CONSERVATIVE_SHARED_IP_WEIGHT_CEILING')

    def test_backoff_consumes_time_budget(self):
        self.response = {'status': 500, 'headers': {}, 'body': b'failure'}
        self.request()
        self.request(timeout=5)
        self.assertEqual(self.sleeps, [2])
        self.assertEqual(self.calls[-1][1], 3)
        calls_before = len(self.calls)
        with self.assertRaises(TimeoutError):
            self.request(timeout=3)
        self.assertEqual(len(self.calls), calls_before)

    def test_backoff_is_bounded_and_recovery_resets_it(self):
        self.response = {'status': 503, 'headers': {}, 'body': b'failure'}
        for delay in (2, 4, 8, 16, 32, 60, 60, 60):
            self.request(timeout=70)
            self.assertEqual(self.lane._transient_retry_at - self.now, delay)
        self.response = {'status': 200, 'headers': {'X-MBX-USED-WEIGHT-1M': '2'}, 'body': b'recovered'}
        self.request(timeout=70)
        old_sleeps = len(self.sleeps)
        self.request()
        self.assertEqual(len(self.sleeps), old_sleeps)
        self.assertFalse((self.root / 'PROVIDER_STOP.json').exists())

    def test_operator_pause_is_never_bypassed(self):
        (self.root / 'PAUSED.json').write_text('{}')
        with self.assertRaises(RuntimeError):
            self.request()
        self.assertEqual(self.calls, [])

    def test_network_exception_is_not_swallowed(self):
        def broken(*args):
            raise OSError('connection lost')
        self.lane.network = broken
        with self.assertRaisesRegex(OSError, 'connection lost'):
            self.request()
        self.assertFalse((self.root / 'PROVIDER_STOP.json').exists())


if __name__ == '__main__':
    unittest.main()
