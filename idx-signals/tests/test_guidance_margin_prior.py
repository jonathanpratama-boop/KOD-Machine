import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from idxsig import guidance_margin_feed as feed


class PriorInventoryTest(unittest.TestCase):
    def inventory(self, *, second_page, candidate_text):
        url = "https://www.prnewswire.com/news/acme/"
        first = url + "?page=1&pagesize=100"
        second = url + "?page=2&pagesize=100"
        latest = dict(history_url=url, url=url+"current", wire_account="issuer",
                      published_at="2026-09-01T08:00:00+00:00", id="latest")
        feb = dict(id="id", url=url+"prior", wire_account="issuer", raw_sha256="raw",
                   text=candidate_text, text_sha256="text", published_at="2026-08-01T08:00:00+00:00")
        docs = {first: dict(raw_sha256="page1", next_url=second_page or second,
                            archive_links=[{"url": latest["url"]}]),
                second: dict(raw_sha256="page2", next_url=None, archive_links=[{"url": feb["url"]}]),
                feb["url"]: feb}
        with tempfile.TemporaryDirectory() as tmp, patch.object(feed, "retain_source", side_effect=lambda _, u, f: docs[u]):
            return feed.inventory(Path(tmp), latest)

    def test_follow_second_page_and_bind_exact_release(self):
        inv, prior = self.inventory(second_page=None, candidate_text="Full-year revenue and operating income guidance")
        self.assertTrue(inv["complete"])
        self.assertEqual(len(inv["archive_pages"]), 2)
        self.assertEqual(inv["releases"][0]["raw_sha256"], prior["raw_sha256"])

    def test_unrelated_archive_is_incomplete(self):
        inv, prior = self.inventory(second_page="https://www.prnewswire.com/news/another/", candidate_text="")
        self.assertTrue(inv["errors"])
        self.assertFalse(inv["complete"])
        self.assertIsNone(prior)

    def test_complete_search_with_no_matching_prior(self):
        inv, prior = self.inventory(second_page=None, candidate_text="Quarterly cash flow.")
        self.assertTrue(inv["complete"])
        self.assertIsNone(prior)
