"""Sensors: parsing, dedupe, hash chain, raw hashes, failure isolation. No network."""

import gzip
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from idxsig import sensors

BSKY = {"feed": [
    {"post": {"uri": "at://did:x/app.bsky.feed.post/aaa", "author": {"handle": "unusualwhales.bsky.social"},
              "record": {"createdAt": "2026-10-26T22:47:44Z", "text": "BREAKING: Nvidia, $NVDA, earnings beat; Apple (AAPL) too"},
              "likeCount": 5, "repostCount": 1}},
    {"post": {"uri": "at://did:y/app.bsky.feed.post/bbb", "author": {"handle": "someone.bsky.social"},
              "record": {"createdAt": "2026-10-26T20:00:00Z", "text": "reposted thing $TSLA"}}, "reason": {"$type": "repost"}},
]}
EFTS = {"hits": {"hits": [{"_id": "0001234567-26-000012:ex991.htm", "_source": {"adsh": "0001234567-26-000012", "file_date": "2026-10-26",
                                                                              "form": "8-K", "display_names": ["Acme Bio Inc (ACME) (CIK 0001234567)"],
                                                                              "ciks": ["0001234567"], "period_ending": "2026-10-24"}}]}}


def fake_fetch(url, user_agent=None, timeout=30):
    if "bsky" in url:
        return json.dumps(BSKY).encode()
    if "efts.sec.gov" in url:
        return json.dumps(EFTS).encode()
    if "stocktwits" in url:
        return json.dumps({"symbols": [{"symbol": "CLS", "title": "Celestica"}, {"symbol": "SLV", "title": "Silver"}]}).encode()
    if "coingecko" in url:
        return json.dumps({"coins": [{"item": {"id": "quack-ai", "symbol": "q", "name": "Quack AI", "market_cap_rank": 77}}]}).encode()
    if "binance" in url:
        return json.dumps({"data": {"catalogs": [{"catalogName": "New Cryptocurrency Listing", "articles": [
            {"code": "abc123", "title": "Binance Will List Foo (FOO)", "releaseDate": 1761500000000}]}]}}).encode()
    raise RuntimeError("unknown url")


def boom(url, user_agent=None, timeout=30):
    raise OSError("feed down")


class ParseTests(unittest.TestCase):
    def test_symbols_in(self):
        self.assertEqual(sensors.symbols_in("Nvidia, $NVDA, and Apple (AAPL) and $NVDA again"), ["NVDA", "AAPL"])
        self.assertEqual(sensors.symbols_in("no tickers here"), [])

    def test_bluesky_skips_reposts_and_builds_urls(self):
        alerts, raw = sensors.bluesky("unusualwhales.bsky.social", fetcher=fake_fetch)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["symbols"], ["NVDA", "AAPL"])
        self.assertEqual(alerts[0]["url"], "https://bsky.app/profile/unusualwhales.bsky.social/post/aaa")
        self.assertEqual(alerts[0]["posted_at"], "2026-10-26T22:47:44Z")

    def test_edgar_symbols_and_url(self):
        alerts, raw = sensors.edgar_8k(("fast track",), fetcher=fake_fetch, today="2026-10-27")
        self.assertEqual(alerts[0]["symbols"], ["ACME"])
        self.assertEqual(alerts[0]["url"], "https://www.sec.gov/Archives/edgar/data/1234567/000123456726000012/ex991.htm")
        self.assertEqual(alerts[0]["posted_at"], "2026-10-26")

    def test_other_sources_parse(self):
        self.assertEqual(sensors.stocktwits_trending(fetcher=fake_fetch, today="2026-10-27")[0][1]["symbols"], ["SLV"])
        self.assertEqual(sensors.coingecko_trending(fetcher=fake_fetch, today="2026-10-27")[0][0]["symbols"], ["Q"])
        b = sensors.binance_listings(fetcher=fake_fetch)[0][0]
        self.assertEqual(b["symbols"], ["FOO"])
        self.assertTrue(b["posted_at"].startswith("2025-10-26"))


class PullTests(unittest.TestCase):
    def test_pull_chains_dedupes_and_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            log, raw = Path(d) / "sensors.jsonl", Path(d) / "raw"
            src = sensors.default_sources(fetcher=fake_fetch)
            t0 = datetime(2026, 10, 27, 1, 0, tzinfo=timezone.utc)
            first = sensors.pull(src, log=log, raw_dir=raw, now=t0)
            self.assertEqual(first["errors"], {})
            self.assertEqual(first["alerts_new"], 1 + 2 + 1 + 1 + 1)
            second = sensors.pull(src, log=log, raw_dir=raw, now=datetime(2026, 10, 27, 2, 0, tzinfo=timezone.utc))
            self.assertEqual(second["alerts_new"], 0)  # same items, same day: nothing new
            lines = [json.loads(x) for x in log.read_text().splitlines()]
            self.assertEqual(sum(r["type"] == "SENSOR_PULL" for r in lines), 2)
            self.assertEqual(lines[1]["prev_hash"], lines[0]["record_hash"])
            # raw bytes are what the record says they are
            rp = sensors._abs(lines[0]["raw_path"])
            with gzip.open(rp, "rb") as fh:
                import hashlib
                self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), lines[0]["raw_sha256"])
            self.assertEqual(sensors.verify(log), [])
            # tamper
            rp.write_bytes(gzip.compress(b"{}"))
            self.assertTrue(any("mismatch" in p for p in sensors.verify(log)))

    def test_one_dead_feed_does_not_lose_the_others(self):
        with tempfile.TemporaryDirectory() as d:
            src = sensors.default_sources(fetcher=fake_fetch)
            src["bluesky:unusualwhales.bsky.social"] = lambda: sensors.bluesky("x", fetcher=boom)
            out = sensors.pull(src, log=Path(d) / "s.jsonl", raw_dir=Path(d) / "raw",
                               now=datetime(2026, 10, 27, tzinfo=timezone.utc))
            self.assertIn("bluesky:unusualwhales.bsky.social", out["errors"])
            self.assertEqual(out["alerts_new"], 5)


if __name__ == "__main__":
    unittest.main()
