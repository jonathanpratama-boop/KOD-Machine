"""Shared-cutoff navigation must keep independent evidence stores independent."""
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from html import unescape
import re

from fastapi.testclient import TestClient

from kod.workstation.web import create_app


CUTOFF = "2025-03-11T16:00:00Z"


class InvestigateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = create_app(self.tmp.name, offline=True, testing=True)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_independent_catalog_links_preserve_strict_observed_cutoff(self):
        self.app.state.store.upsert_security("ZEAL", "Separate company record", venue="OTHER", currency="USD")
        response = self.client.get("/investigate", params={"as_of": CUTOFF})
        self.assertEqual(response.status_code, 200)
        self.assertIn("no relationship to a ledger case is inferred", response.text)
        self.assertIn("No implied joins", response.text)
        hrefs = [unescape(s) for s in re.findall(r'href="([^"]+)"', response.text)]
        cutoff_links = [s for s in hrefs if "/replay?" in s or "/dossier?" in s or "/search?" in s]
        self.assertGreater(len(cutoff_links), 2)
        for link in cutoff_links:
            query = parse_qs(urlsplit(link).query)
            self.assertEqual(query["as_of"], [CUTOFF])
            if "/replay?" not in link:
                self.assertEqual(query["mode"], ["observed"])
                self.assertEqual(query["policy"], ["strict"])
            self.assertNotIn("reveal", query)

    def test_missing_ledger_does_not_block_company_evidence(self):
        self.app.state.replay_db = Path(self.tmp.name) / "missing-ledger.db"
        sec = self.app.state.store.upsert_security("ACME", "Acme Corp", venue="XNAS", currency="USD")
        response = self.client.get("/investigate", params={"as_of": CUTOFF})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Company evidence remains accessible", response.text)
        self.assertIn(f'/company/{sec["id"]}/dossier?', response.text)
        self.assertFalse(self.app.state.replay_db.exists())

    def test_catalog_text_is_escaped(self):
        self.app.state.store.upsert_security("ACME", '<script>alert("bad")</script>', venue="XNAS", currency="USD")
        page = self.client.get("/investigate", params={"as_of": CUTOFF}).text
        self.assertNotIn('<script>alert("bad")</script>', page)
        self.assertIn("&lt;script&gt;", page)

    def test_invalid_or_naive_timestamp_rejected(self):
        for cutoff in ("nonsense", "2025-03-11", "2025-03-11T16:00:00"):
            with self.subTest(cutoff=cutoff):
                self.assertEqual(self.client.get("/investigate", params={"as_of": cutoff}).status_code, 400)

    def test_nav_entry_and_replay_breadcrumb(self):
        self.assertIn('href="/investigate"', self.client.get("/").text)
        page = self.client.get("/replay", params={"case_id": "KOD-R-ZEAL-20250312", "as_of": CUTOFF}).text
        self.assertIn("/investigate?as_of=2025-03-11T16%3A00%3A00Z", page)


if __name__ == "__main__":
    unittest.main()
