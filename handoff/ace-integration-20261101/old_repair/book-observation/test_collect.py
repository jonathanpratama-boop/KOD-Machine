import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import collect

RAW = json.dumps({"lastUpdateId": 1, "bids": [["99", "2"], ["98", "3"]],
                  "asks": [["100", "1"], ["101", "2"]]}).encode()


class Clock:
    def __init__(self): self.t = 1793473200.
    def now(self): return self.t
    def sleep(self, seconds): self.t += seconds


class Collector(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / 'run'
        self.clock = Clock()

    def run_capture(self, getter):
        return collect.run(self.out, getter=getter, clock=self.clock.now, sleep=self.clock.sleep)

    def test_full_schedule_exact_180_requests_no_extra_endpoints(self):
        urls = []
        def getter(url):
            urls.append(url)
            self.clock.t += 1
            return 200, {}, RAW
        result = self.run_capture(getter)
        self.assertEqual((result['requests'], result['successful_books'], result['missing']), (180, 180, 0))
        self.assertEqual(len(urls), 180)
        self.assertTrue(all(u.startswith('https://data-api.binance.vision/api/v3/depth?symbol=') for u in urls))
        self.assertEqual(self.clock.t, 1793473200. + 59 * 120 + 3)
        lines = [json.loads(x) for x in (self.out / 'observations.jsonl').read_text().splitlines()]
        self.assertEqual(len(lines), 180)
        self.assertFalse(lines[0]['metrics']['fills']['1000']['buy']['complete'])

    def test_451_stops_without_host_fallback_or_remaining_requests(self):
        calls = []
        result = self.run_capture(lambda u: (calls.append(u) or (451, {}, b'restricted')))
        self.assertEqual((len(calls), result['missing'], result['failed'], result['state']), (1, 179, 1, 'STOPPED'))

    def test_other_4xx_stops_as_missing_source(self):
        for code in (401, 403, 404, 405, 407, 418):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as td:
                result = collect.run(Path(td)/'run', getter=lambda u: (code, {}, b'error'), clock=self.clock.now, sleep=self.clock.sleep)
                self.assertEqual(result['requests'], 1)

    def test_429_waits_until_retry_after_and_does_not_backfill(self):
        times = []
        def getter(u):
            times.append(self.clock.t)
            return (429, {'Retry-After':'240'}, b'rate limit') if len(times) == 1 else (200, {}, RAW)
        result = self.run_capture(getter)
        self.assertEqual(times[1]-times[0], 240)
        self.assertEqual((result['requests'], result['missing']), (175, 5))

    def test_429_without_valid_header_stops(self):
        result = self.run_capture(lambda u: (429, {}, b'rate limit'))
        self.assertEqual((result['requests'], result['state']), (1, 'STOPPED'))

    def test_retry_after_http_date_and_bad_header(self):
        self.assertEqual(collect.retry_after({'retry-after':'Sat, 31 Oct 2026 19:05:00 GMT'}, 1793473200.), 1793473500.)
        self.assertIsNone(collect.retry_after({'Retry-After':'nonsense'}, 0))

    def test_invalid_books_fail_without_fabricated_metrics(self):
        result = self.run_capture(lambda u: (200, {}, b'{"bids":[],"asks":[]}'))
        self.assertEqual((result['successful_books'], result['failed']), (0, 180))
        self.assertTrue(all('metrics' not in json.loads(x) for x in (self.out/'observations.jsonl').read_text().splitlines()))

    def test_malformed_crossed_nonfinite_depth_rejected(self):
        for bids, asks in (([["101", "1"]], [["100", "1"]]), ([["NaN", "1"]], [["100", "1"]]),
                           ([["99", "1"]], [["100", "1"], ["100", "2"]])):
            with self.assertRaises(ValueError): collect.metrics(json.dumps({'bids':bids,'asks':asks}).encode())

    def test_restart_will_not_overwrite_prior_capture(self):
        self.run_capture(lambda u: (403, {}, b'blocked'))
        with self.assertRaises(FileExistsError): self.run_capture(lambda u: (200, {}, RAW))

    def test_missed_slots_not_backfilled(self):
        calls=[]
        def getter(u):
            calls.append(u)
            if len(calls)==1:self.clock.t += 300
            return 200,{},RAW
        result=self.run_capture(getter)
        self.assertEqual(result['missing'],5)


if __name__ == '__main__': unittest.main()
