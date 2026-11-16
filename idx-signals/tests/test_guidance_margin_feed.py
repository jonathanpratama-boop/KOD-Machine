import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig import guidance_margin_feed as f


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        mapping = self.root / "map.csv"
        mapping.write_text("ticker,cik\nXYZ,1234\n")
        self.state = f.initialize(
            self.root / "run", mapping, started_at="2026-11-16T10:00:00+00:00", budget=55
        )
        self.run = self.root / "run"

    def tearDown(self):
        self.tmp.cleanup()

    def test_html_preserves_headers_negative_cells_and_ignores_navigation(self):
        raw = b"""<div class><p>Navigation 999</p></div><script type="application/ld+json">{"datePublished":"2026-11-16T04:00:00-05:00"}</script><div class="release-content"><h3>Full-year 2026 guidance (USD millions)</h3><table><tr><th colspan="2">Operating income</th></tr><tr><td>(12.5)</td><td>$100</td></tr></table><p>Adjusted excludes X</p><script>malicious()</script></div><p>footer</p>"""
        doc = f.parse_release(raw)
        self.assertIn("[colspan=2] Operating income", doc["text"])
        self.assertIn("| (12.5) | $100", doc["text"])
        self.assertNotIn("999", doc["text"])
        self.assertNotIn("malicious", doc["text"])
        self.assertEqual(doc["published_at"], "2026-11-16T09:00:00+00:00")

    def test_feed_rejects_undeclared_origin(self):
        raw = b"<rss><channel><item><title>x</title><link>https://evil.example/a</link><pubDate>Mon, 16 Nov 2026 10:30:00 +0000</pubDate></item></channel></rss>"
        with self.assertRaises(ValueError):
            f.parse_feed(raw)

    def test_receipt_is_not_rewritten_on_same_bytes(self):
        raw = b'<div class="release-content">full year revenue operating profit outlook</div>'
        with patch.object(
            f, "now", side_effect=["2026-11-16T10:30:00+00:00", "2026-11-16T11:30:00+00:00"]
        ):
            a = f.retain_source(
                self.run, "https://www.prnewswire.com/news-releases/example.html", lambda _: raw
            )
            b = f.retain_source(
                self.run, "https://www.prnewswire.com/news-releases/example.html", lambda _: raw
            )
        self.assertEqual(a["received_at"], b["received_at"])
        self.assertEqual(a["raw_sha256"], b["raw_sha256"])

    def test_new_recent_and_old_cohorts_dedup_and_no_api_for_negative(self):
        items = [
            ("new", "Mon, 16 Nov 2026 10:30:00 +0000"),
            ("recent", "Fri, 13 Nov 2026 10:30:00 +0000"),
            ("old", "Sun, 01 Nov 2026 10:30:00 +0000"),
        ]
        feed = (
            "<rss><channel>"
            + "".join(
                f"<item><title>{name}</title><link>https://www.prnewswire.com/news-releases/{name}.html</link><pubDate>{date}</pubDate></item>"
                for name, date in items
            )
            + "</channel></rss>"
        ).encode()

        def fetcher(url):
            return (
                feed
                if "/rss/" in url
                else b'<div class="release-content">A conference next week.</div>'
            )

        first = f.cycle(self.run, live=True, fetcher=fetcher)
        second = f.cycle(self.run, live=True, fetcher=fetcher)
        self.assertEqual(first["discovered_count"], 3)
        self.assertEqual(second["discovered_count"], 3)
        self.assertEqual(second["api_calls"], 0)
        self.assertEqual(
            {e["title"]: e["cohort"] for e in second["entries"]},
            {"new": "new_release", "recent": "initial_recent", "old": "development"},
        )

    def test_crash_reservation_persisted_before_network_and_kept_without_usage(self):
        with patch.object(f, "now", return_value="2026-11-16T10:30:00+00:00"):
            self.assertIsNone(f.reserve_call(self.run, self.state, 10000, "x"))
        saved = json.loads((self.run / "feed_state.json").read_text())
        self.assertGreater(saved["api_estimated_usd"], 0)
        reserved = saved["api_estimated_usd"]
        f.settle_call(self.run, self.state, "x", {"provider_calls": 1, "status": "TRANSPORT_ERROR"})
        self.assertEqual(self.state["api_estimated_usd"], reserved)
        self.assertEqual(self.state["api_reservations"]["x"]["status"], "UNSETTLED")

    def test_real_tokens_replace_conservative_reservation(self):
        with patch.object(f, "now", return_value="2026-11-16T10:30:00+00:00"):
            f.reserve_call(self.run, self.state, 10000, "x")
        f.settle_call(
            self.run,
            self.state,
            "x",
            {
                "provider_calls": 1,
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "input_tokens_details": {"cached_tokens": 100},
                },
            },
        )
        self.assertAlmostEqual(self.state["api_estimated_usd"], 0.005275)
        self.assertEqual(self.state["api_calls"], 1)

    def test_expiry_and_budget_prevent_calls(self):
        self.assertEqual(f.allowance(self.state, 1000, f.EXPIRY), "API_CREDIT_EXPIRED")
        self.assertEqual(
            f.allowance(self.state, 1000, "2026-12-03T13:32:00+00:00"),
            "API_CREDIT_EXPIRED",
        )
        self.assertIsNone(f.allowance(self.state, 1000, "2026-12-03T13:30:00+00:00"))
        self.state["api_estimated_usd"] = 54.53
        self.assertEqual(
            f.allowance(self.state, 1000, "2026-11-16T10:30:00+00:00"), "API_CREDIT_BUDGET_REACHED"
        )

    def test_missing_key_returns_reservation(self):
        with patch.object(f, "now", return_value="2026-11-16T10:30:00+00:00"):
            f.reserve_call(self.run, self.state, 10000, "x")
        f.settle_call(self.run, self.state, "x", {"provider_calls": 0})
        self.assertEqual(self.state["api_calls"], 0)
        self.assertEqual(self.state["api_estimated_usd"], 0)

    def test_identity_must_be_unique_and_in_dated_map(self):
        self.assertEqual(f.ticker_from_text("NASDAQ: XYZ", {"XYZ": "1234"}), ("XYZ", "1234"))
        self.assertEqual(f.ticker_from_text("NASDAQ: ABC", {"XYZ": "1234"}), (None, None))
        self.assertEqual(
            f.ticker_from_text("NYSE: XYZ and NASDAQ: ABC", {"XYZ": "1234", "ABC": "9"}),
            (None, None),
        )

    def test_feed_failure_remains_visible_without_erasing_previous(self):
        def fail(_):
            raise TimeoutError()

        result = f.cycle(self.run, fetcher=fail)
        self.assertEqual(result["state"], "DEGRADED")
        self.assertIn("TimeoutError", result["last_error"])
        self.assertEqual(result["fetch_error_count"], 1)


if __name__ == "__main__":
    unittest.main()
