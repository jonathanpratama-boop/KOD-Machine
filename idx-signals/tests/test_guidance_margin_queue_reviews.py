import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig import guidance_margin_feed as feed


class QueueReviews(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        mapping = self.root / "map.csv"
        mapping.write_text("ticker,cik\n")
        state = feed.initialize(self.root, mapping, started_at="2026-11-16T00:00:00+00:00")
        url = "https://www.prnewswire.com/news-releases/acme.html"
        raw = (
            b'<input id="companies" value="Acme Corp"><input id="accountNumber" value="456">'
            b'<div class="release-content">Acme full-year revenue and operating margin outlook</div>'
        )
        self.doc = feed.retain_source(self.root, url, lambda _: raw)
        self.event = self.doc["id"]
        self.entry = dict(
            id=self.event,
            url=url,
            title="Acme results",
            status="IDENTITY_UNKNOWN",
            cohort="new_release",
            received_at="2026-11-16T10:00:00+00:00",
            published_at="2026-11-16T09:00:00+00:00",
            reason="Missing identity",
            source_sha256=self.doc["raw_sha256"],
        )
        state["entries"][self.event] = self.entry
        feed.write_json(self.root / "feed_state.json", state)
        self.args = dict(
            event_id=self.event,
            expected_status="IDENTITY_UNKNOWN",
            source_sha256=self.doc["raw_sha256"],
            reviewer="reviewer",
            reason="The report contains actuals only",
            decision="EXCLUDE",
            evidence_urls=[url],
            evidence_quote="Acme full-year revenue",
        )
        self.identity = dict(
            ticker="ACME",
            issuer_cik="1234",
            issuer_name="Acme Corp",
            source_url="https://data.sec.gov/submissions/CIK0000001234.json",
        )
        self.identity_args = dict(
            ticker="ACME", issuer_cik="1234", identity_evidence_url=self.identity["source_url"]
        )

    def apply(self, **overrides):
        with patch.object(feed, "resolve_identity", return_value=self.identity):
            return feed.apply_review(self.root, **(self.args | overrides))

    def state(self):
        return json.loads((self.root / "feed_state.json").read_text())

    def test_applies_once_preserves_clocks_original_flag_and_counts(self):
        receipt = self.apply()
        self.assertEqual(self.apply(), receipt)
        entry = self.state()["entries"][self.event]
        self.assertEqual(entry["received_at"], self.entry["received_at"])
        self.assertEqual(entry["published_at"], self.entry["published_at"])
        self.assertEqual(receipt["original_reason"], self.entry["reason"])
        self.assertEqual(receipt["request"]["expected_status"], self.entry["status"])
        self.assertEqual(receipt["release_received_at"], self.entry["received_at"])
        self.assertEqual(receipt, json.loads((self.root / entry["applied_reviews"][0]).read_text()))
        self.assertEqual(len(entry["applied_reviews"]), 1)
        report = json.loads((self.root / "FEED_STATUS.json").read_text())
        self.assertEqual(
            (
                report["review_closed_count"],
                report["review_pending_count"],
                report["excluded_count"],
            ),
            (1, 0, 1),
        )
        self.assertEqual(report["api_calls"], 0)
        with self.assertRaises(ValueError):
            self.apply(reason="Conflicting replacement")
        self.assertEqual(entry, self.state()["entries"][self.event])

    def test_legacy_manual_exclusions_are_counted_once(self):
        state = self.state()
        state["entries"][self.event].update(
            status="FACTS_NOT_ELIGIBLE",
            original_status="IDENTITY_UNKNOWN",
            manual_reviewed_at="2026-11-17T09:20:00+00:00",
        )
        report = feed.status(self.root, state)
        self.assertEqual(
            (
                report["review_closed_count"],
                report["review_pending_count"],
                report["excluded_count"],
            ),
            (1, 0, 1),
        )

    def test_stale_source_flag_and_unverified_evidence_leave_queue_intact(self):
        for change in [
            dict(source_sha256="a" * 64),
            dict(expected_status="MISSING_PRIOR"),
            dict(evidence_quote="invented quote"),
            dict(evidence_urls=[]),
            dict(evidence_quotes=["invented additional quote"]),
            self.identity_args | dict(issuer_cik="999"),
            self.identity_args | dict(ticker="Z"),
        ]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.apply(**change)
        self.assertEqual(self.state()["entries"][self.event], self.entry)
        raw = self.root / "sources" / self.event / (self.doc["raw_sha256"] + ".html")
        raw.write_text("tampered")
        with self.assertRaises(ValueError):
            self.apply()

    def test_receipt_first_crash_replays_without_replacing_or_duplicating(self):
        with patch.object(feed, "write_json", side_effect=OSError):
            with self.assertRaises(OSError):
                self.apply()
        files = list((self.root / "applied_reviews").rglob("*.json"))
        self.assertEqual(len(files), 1)
        original = files[0].read_bytes()
        self.assertEqual(self.state()["entries"][self.event], self.entry)
        self.assertEqual(self.apply(), json.loads(original))
        self.assertEqual(files[0].read_bytes(), original)

    def test_requeued_verified_identity_uses_retained_source_and_still_requires_prior(self):
        self.apply(decision="RETRY_IDENTITY", **self.identity_args)

        def fetcher(url):
            self.assertEqual(url, feed.FEED_URL)
            return b"<rss><channel/></rss>"

        report = feed.cycle(self.root, live=True, fetcher=fetcher)
        entry = report["entries"][0]
        self.assertEqual(
            (entry["status"], entry["ticker"], entry["issuer_cik"]),
            ("MISSING_PRIOR", "ACME", "1234"),
        )
        self.assertEqual(
            (
                report["review_pending_count"],
                report["candidate_count"],
                report["review_closed_count"],
            ),
            (1, 0, 0),
        )
        self.assertEqual(
            report["pending_reviews"],
            [
                {
                    "title": "Acme results",
                    "status": "MISSING_PRIOR",
                    "reason": feed.REVIEW_REASONS["MISSING_PRIOR"],
                }
            ],
        )
        self.assertEqual(report["api_calls"], 0)
        self.apply(decision="RETRY_IDENTITY", **self.identity_args)
        self.assertEqual(self.state()["entries"][self.event]["status"], "MISSING_PRIOR")

    def test_held_prior_prevents_paid_call_and_accepts_only_bound_earlier_evidence(self):
        earlier_url = "https://www.prnewswire.com/news-releases/earlier.html"
        earlier_raw = (
            b'<input id="accountNumber" value="456"><script type="application/ld+json">'
            b'{"datePublished":"2026-09-01T09:00:00+00:00"}</script>'
            b'<div class="release-content">Fiscal 2025 outlook</div>'
        )
        earlier = feed.retain_source(self.root, earlier_url, lambda _: earlier_raw)
        kwargs = self.identity_args | dict(
            decision="HOLD_MISSING_PRIOR", prior_url=earlier_url, prior_sha256=earlier["raw_sha256"]
        )
        with self.assertRaises(ValueError):
            self.apply(**kwargs, prior_quote="Fiscal 2026")
        receipt = self.apply(**kwargs, prior_quote="Fiscal 2025")
        self.assertEqual(receipt["request"]["prior_sha256"], earlier["raw_sha256"])
        report = feed.cycle(self.root, live=True, fetcher=lambda _: b"<rss><channel/></rss>")
        self.assertEqual(
            (report["review_pending_count"], report["review_closed_count"], report["api_calls"]),
            (1, 0, 0),
        )
        self.assertEqual(report["entries"][0]["status"], "MISSING_PRIOR")

    def test_identity_retry_never_repeats_existing_paid_attempt(self):
        (self.root / "reader" / self.event).mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "Existing reader"):
            self.apply(decision="RETRY_IDENTITY", **self.identity_args)
        self.assertEqual(self.state()["entries"][self.event], self.entry)

    def test_cli_applies_review_without_polling(self):
        path = self.root / "decision.json"
        path.write_text(json.dumps(self.args))
        output = io.StringIO()
        with (
            contextlib.redirect_stdout(output),
            patch.object(feed, "cycle", side_effect=AssertionError),
        ):
            feed.main(["--state", str(self.root), "--apply-review", str(path)])
        self.assertEqual(json.loads(output.getvalue())["decision"], "EXCLUDE")

    def test_ordinary_discovery_uses_fallback_and_runs_all_prior_checks(self):
        state = self.state()
        state["entries"][self.event]["status"] = "DISCOVERED"
        feed.write_json(self.root / "feed_state.json", state)
        raw = (self.root / "sources" / self.event / (self.doc["raw_sha256"] + ".html")).read_bytes()

        def fetcher(url):
            return b"<rss><channel/></rss>" if url == feed.FEED_URL else raw

        with patch.object(feed, "resolve_identity", return_value=self.identity):
            result = feed.cycle(self.root, live=True, fetcher=fetcher)
        self.assertEqual(result["entries"][0]["identity_evidence"], self.identity)
        self.assertEqual(result["entries"][0]["status"], "MISSING_PRIOR")
        self.assertEqual(result["api_calls"], 0)
