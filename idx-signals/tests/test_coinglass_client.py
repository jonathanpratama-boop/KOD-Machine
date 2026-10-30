import hashlib
import json
import os
import traceback
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest import mock
from urllib.parse import parse_qs, urlparse

from idxsig.sources import coinglass as cg


KEY = "coinglass-unit-test-credential"
PARAMS = {"exchange": "Binance", "symbol": "BTCUSDT", "interval": "4h"}


def response(data=None, *, code="0", message="", status=200, headers=None):
    data = [{"time": 1704067200000, "close": "100"}] if data is None else data
    return status, headers or {}, json.dumps({"code": code, "msg": message, "data": data}).encode()


class FakeHTTP:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.delays = []
        self.elapsed = 0.0
        self.epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)

    def transport(self, url, headers, timeout):
        self.calls.append((url, dict(headers), timeout, self.elapsed))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def sleep(self, seconds):
        self.delays.append(seconds)
        self.elapsed += seconds

    def client(self, **kwargs):
        return cg.CoinGlassClient(KEY, transport=self.transport, sleep=self.sleep,
                                 monotonic=lambda: self.elapsed,
                                 clock=lambda: self.epoch + timedelta(seconds=self.elapsed), **kwargs)


class CoinGlassClientTests(unittest.TestCase):
    def test_exact_host_header_payload_and_safe_metadata(self):
        fake = FakeHTTP([response()])
        result = fake.client().request("price", **PARAMS, limit=50)
        url, headers, timeout, _ = fake.calls[0]
        parsed = urlparse(url)
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path),
                         ("https", "open-api-v4.coinglass.com", "/api/futures/price/history"))
        self.assertEqual(headers["CG-API-KEY"], KEY)
        self.assertEqual(timeout, 25.0)
        self.assertEqual(parse_qs(parsed.query)["symbol"], ["BTCUSDT"])
        self.assertEqual(result.data[0]["close"], "100")
        self.assertEqual(result.metadata["sha256"], hashlib.sha256(result.raw).hexdigest())
        self.assertEqual(result.metadata["params"], {**PARAMS, "limit": 50})
        self.assertEqual(result.metadata["attempts"], 1)
        self.assertEqual(result.metadata["requested_at"], "2024-01-01T00:00:00.000Z")
        self.assertNotIn(KEY, url + repr(result))
        self.assertNotIn("headers", result.metadata)

    def test_environment_key_and_missing_or_invalid_configuration(self):
        with mock.patch.dict(os.environ, {cg.API_KEY_ENV: KEY}):
            client = cg.CoinGlassClient(transport=lambda *args: response(["BTC"]))
            self.assertEqual(client.request("supported_coins").data, ["BTC"])
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(cg.CoinGlassError) as caught:
                cg.CoinGlassClient()
            self.assertEqual(caught.exception.kind, "unauthorized")
        for key in ("", "bad\nheader", "a b", "ü", 123):
            with self.subTest(key=key), self.assertRaises(cg.CoinGlassError):
                cg.CoinGlassClient(key)
        for kwargs in ({"max_attempts": 0}, {"max_attempts": 4}, {"max_attempts": True},
                       {"timeout": 26}, {"timeout": float("nan")}, {"timeout": True},
                       {"requests_per_minute": 0}, {"requests_per_minute": float("inf")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(cg.CoinGlassError):
                cg.CoinGlassClient(KEY, **kwargs)

    def test_endpoint_and_parameter_allowlist_before_network(self):
        fake = FakeHTTP([])
        client = fake.client()
        cases = [("https://evil.invalid/x", PARAMS), ("../price", PARAMS),
                 ("price", {**PARAMS, "api_key": "secret"}), ("price", {"symbol": "BTCUSDT"}),
                 ("price", {**PARAMS, "interval": "2h"}), ("price", {**PARAMS, "exchange": "x\r\nHeader"}),
                 ("price", {**PARAMS, "limit": 1001}), ("price", {**PARAMS, "limit": True}),
                 ("price", {**PARAMS, "start_time": 1.5}),
                 ("price", {**PARAMS, "start_time": 100, "end_time": 100}),
                 ("rsi", {**PARAMS, "window": 0}), ("rsi", {**PARAMS, "series_type": "volume"}),
                 ("macd", {**PARAMS, "fast_window": 26, "slow_window": 12}),
                 ("open_interest", {**PARAMS, "unit": "BTC"}),
                 ("boll", {**PARAMS, "mult": float("nan")}),
                 ("supported_coins", {"exchange": "Binance"})]
        for endpoint, params in cases:
            with self.subTest(endpoint=endpoint, params=params), self.assertRaises(cg.CoinGlassError):
                client.request(endpoint, **params)
        self.assertFalse(fake.calls)
        with self.assertRaises(cg.CoinGlassError) as caught:
            client.request("price", **{**PARAMS, "symbol": KEY})
        self.assertEqual(caught.exception.kind, "security")

    def test_supported_catalogs_and_every_indicator_registry(self):
        pairs = {"Binance": [{"instrument_id": "BTCUSDT", "base_asset": "BTC", "quote_asset": "USDT"}]}
        fake = FakeHTTP([response(["BTC", "ETH"]), response(pairs)] + [response([]) for _ in range(6)])
        client = fake.client()
        self.assertEqual(client.request("supported_coins").data, ["BTC", "ETH"])
        self.assertEqual(client.request("supported_pairs", exchange="Binance").data, pairs)
        for name in ("rsi", "macd", "ma", "ema", "boll", "atr"):
            result = client.request(name, **PARAMS)
            self.assertEqual(result.data, [])
            self.assertIn("/api/futures/indicators/", result.metadata["path"])
        self.assertEqual(cg.validate_request("open_interest", {**PARAMS, "unit": "coin"})["unit"], "coin")

    def test_http_200_provider_errors_and_live_plan_message_are_not_success(self):
        for code, message, expected in (("401", "Invalid API key", "unauthorized"),
                                        ("401", "Upgrade plan", "plan"),
                                        ("405", "", "plan"), ("400", "bad parameter", "schema"),
                                        ("404", "missing", "provider"), ("422", "bad", "schema")):
            fake = FakeHTTP([response(code=code, message=message)])
            with self.subTest(code=code, message=message), self.assertRaises(cg.CoinGlassError) as caught:
                fake.client().request("price", **PARAMS)
            self.assertEqual(caught.exception.kind, expected)
            self.assertEqual(caught.exception.provider_code, code)
            self.assertEqual(len(fake.calls), 1)

    def test_rate_limit_retry_after_and_pacing(self):
        fake = FakeHTTP([response(code="429", headers={"Retry-After": "7"}), response(), response()])
        client = fake.client()
        result = client.request("price", **PARAMS)
        self.assertEqual(result.metadata["attempts"], 2)
        self.assertEqual(result.metadata["observed_at"], "2024-01-01T00:00:07.000Z")
        client.request("funding", **PARAMS)
        self.assertEqual([c[3] for c in fake.calls], [0, 7, 9])
        self.assertLessEqual(max(fake.delays), cg.MAX_RETRY_DELAY)

    def test_http_date_retry_after_and_excessive_delay_does_not_retry_early(self):
        epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)
        date = format_datetime(epoch + timedelta(seconds=10), usegmt=True)
        fake = FakeHTTP([response(status=429, code="429", headers={"retry-after": date}), response()])
        self.assertEqual(fake.client().request("price", **PARAMS).metadata["attempts"], 2)
        self.assertEqual(fake.calls[1][3], 10)
        fake = FakeHTTP([response(status=429, code="429", headers={"Retry-After": "120"})])
        with self.assertRaises(cg.CoinGlassError) as caught:
            fake.client().request("price", **PARAMS)
        self.assertEqual(caught.exception.kind, "rate")
        self.assertEqual(caught.exception.retry_after, 120)
        self.assertEqual(len(fake.calls), 1)
        self.assertFalse(fake.delays)

    def test_transient_failures_have_a_hard_attempt_limit_and_safe_traceback(self):
        for replies, expected in (([TimeoutError(KEY)] * 3, "transport"),
                                  ([response(code="500")] * 3, "provider"),
                                  ([(408, {}, b"request timeout")] * 3, "provider"),
                                  ([(503, {}, b"gateway failed")] * 3, "provider"),
                                  ([RuntimeError("headers=" + KEY)] * 3, "transport")):
            fake = FakeHTTP(replies)
            with self.subTest(expected=expected), self.assertRaises(cg.CoinGlassError) as caught:
                fake.client().request("price", **PARAMS)
            self.assertEqual(caught.exception.kind, expected)
            self.assertEqual(len(fake.calls), 3)
            self.assertNotIn(KEY, "".join(traceback.format_exception(caught.exception)))

    def test_redirects_refused_without_followup_request(self):
        fake = FakeHTTP([(302, {"Location": "https://evil.invalid/"}, b"")])
        with self.assertRaises(cg.CoinGlassError) as caught:
            fake.client().request("price", **PARAMS)
        self.assertEqual(caught.exception.kind, "security")
        self.assertEqual(len(fake.calls), 1)
        self.assertIsNone(cg._NoRedirects().redirect_request(None, None, 302, "", {}, "https://evil.invalid"))

    def test_credentials_reflected_in_raw_or_escaped_json_are_discarded(self):
        escaped = "".join("\\u%04x" % ord(c) for c in KEY)
        bodies = [json.dumps({"code": "401", "msg": KEY}).encode(),
                  ('{"code":"0","data":[{"value":"' + escaped + '"}]}').encode()]
        for body in bodies:
            fake = FakeHTTP([(200, {}, body)])
            with self.subTest(body=body), self.assertRaises(cg.CoinGlassError) as caught:
                fake.client().request("price", **PARAMS)
            self.assertEqual(caught.exception.kind, "security")
            self.assertNotIn(KEY, str(caught.exception))

    def test_malformed_success_shape_and_nonfinite_json_rejected(self):
        bodies = [b"not json", b'{"data":[]}', b'{"code":false,"data":[]}',
                  b'{"code":"0","data":null}', b'{"code":"0","data":[42]}',
                  b'{"code":"0","data":[{"close":NaN}]}']
        for body in bodies:
            fake = FakeHTTP([(200, {}, body)])
            with self.subTest(body=body), self.assertRaises(cg.CoinGlassError) as caught:
                fake.client().request("price", **PARAMS)
            self.assertEqual(caught.exception.kind, "schema")
            self.assertEqual(len(fake.calls), 1)

    def test_default_transport_uses_redirect_refusing_opener(self):
        class Reply:
            code = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return cg.BASE_URL + "/api/futures/supported-coins"
            def read(self, size): return response(["BTC"])[2]
        opener = mock.Mock()
        opener.open.return_value = Reply()
        with mock.patch.object(cg, "build_opener", return_value=opener) as build:
            out = cg.CoinGlassClient(KEY).request("supported_coins")
        self.assertEqual(out.data, ["BTC"])
        self.assertIsInstance(build.call_args.args[0], cg._NoRedirects)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, cg.BASE_URL + "/api/futures/supported-coins")
        self.assertEqual(request.get_header("Cg-api-key"), KEY)


if __name__ == "__main__":
    unittest.main()
