"""A rate limit ends this finite pull; a later run may retry explicitly."""

import io
import unittest
import urllib.error
from unittest.mock import patch

from idxsig.sources import binance


class BinanceAccessBlocks(unittest.TestCase):
    def test_block_or_rate_limit_is_returned_once_with_original_error_bytes(self):
        for code in (403, 418, 429, 451):
            error = urllib.error.HTTPError("https://data-api.binance.vision/api/v3/klines", code,
                                           "blocked", {"Retry-After": "60"}, io.BytesIO(b"provider-block"))
            with self.subTest(code=code), patch.object(binance.urllib.request, "urlopen", side_effect=error) as request, patch.object(binance.time, "sleep") as sleep:
                status, raw = binance._get("https://data-api.binance.vision/api/v3/klines")
                self.assertEqual((status, raw), (code, b"provider-block"))
                self.assertEqual(request.call_count, 1)
                sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
