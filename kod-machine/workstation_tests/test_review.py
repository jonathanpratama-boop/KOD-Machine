"""Regressions for the independent adversarial review of Gate A at the workstation boundary (filing headers, URLs, stored v1 documents, analyst inputs)."""

from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

import httpx

from kod.workstation import sources
from kod.workstation.services import ResearchService
from kod.workstation.store import Store

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "earnings_demo"
URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000315/q3fy25pr.htm"
HEADERS = (DEMO / "current_0001045810-24-000315-index-headers.html").read_bytes()
PRIOR_HEADERS = (DEMO / "prior_0001045810-24-000262-index-headers.html").read_bytes()
RELEASE = (DEMO / "current_q3fy25pr.htm").read_bytes()
NOW = "2026-10-23T12:00:00Z"


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "data"
        self.store = Store(self.root)
        self.service = ResearchService(self.store, clock=lambda: NOW)
        self.nvda = self.store.upsert_security("NVDA", "NVIDIA Corporation", cik="1045810")

    def ingest(self, headers, url=URL):
        return self.service.ingest(
            self.nvda["id"],
            RELEASE,
            "q3fy25pr.htm",
            url,
            sec_headers=headers,
            retrieved_at="2026-10-22T14:40:11Z",
        )


class HeaderReviewTests(Case):
    def test_every_accession_statement_in_the_header_must_agree(self):
        other = HEADERS.replace(
            b"SEC EDGAR Submission 0001045810-24-000315",
            b"SEC EDGAR Submission 0001045810-24-000262",
        )
        other = other.replace(b"0001045810-24-000315.hdr.sgml", b"0001045810-24-000262.hdr.sgml")
        with self.assertRaisesRegex(ValueError, "more than one accession number"):
            self.ingest(other)
        with self.assertRaisesRegex(ValueError, "more than one accession number"):
            self.ingest(
                HEADERS.replace(
                    b"CONFORMED SUBMISSION TYPE:",
                    b"Accession Number: 0001045810-24-000262\nCONFORMED SUBMISSION TYPE:",
                )
            )

    def test_a_longer_number_is_not_read_as_the_sources_accession(self):
        doc = self.ingest(HEADERS.replace(b"0001045810-24-000315", b"0001045810-24-0003159"))
        self.assertIsNone(doc["published_at"])
        self.assertNotEqual(doc["metadata"]["header_link"]["status"], "matched")

    def test_two_different_acceptance_times_establish_neither(self):
        for header in (
            HEADERS.replace(
                b"&lt;ACCEPTANCE-DATETIME&gt;20241120162120",
                b"&lt;ACCEPTANCE-DATETIME&gt;20240828162034",
            ),
            HEADERS.replace(
                b"<ACCEPTANCE-DATETIME>20241120162120", b"<ACCEPTANCE-DATETIME>20240828162034"
            ),
        ):
            doc = self.ingest(header)
            self.assertIsNone(doc["published_at"])
            self.assertEqual(doc["metadata"]["header_link"]["status"], "unestablished")
            self.assertIn("different acceptance times", doc["metadata"]["header_link"]["reason"])

    def test_a_header_naming_another_company_by_cik_tag_is_refused(self):
        sgml = (
            b"<SEC-HEADER>0001045810-24-000315.hdr.sgml : 20241120\n<ACCEPTANCE-DATETIME>20241120162120\n"
            b"<ACCESSION-NUMBER>0001045810-24-000315\n<CIK>0000320193\n</SEC-HEADER>"
        )
        with self.assertRaisesRegex(ValueError, "CIK disagree"):
            self.ingest(sgml)


class DotSegmentTests(Case):
    DOTTED = "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000262/../000104581024000315/q3fy25pr.htm"

    def test_a_dot_segment_url_cannot_borrow_another_filings_header(self):
        with self.assertRaisesRegex(ValueError, r"'\.' or '\.\.' path segments"):
            self.ingest(HEADERS, url=self.DOTTED)

    def test_the_fetcher_refuses_dot_segments_before_any_request(self):
        requested = []
        client = sources.SecClient(
            "test@example.com",
            transport=httpx.MockTransport(
                lambda r: requested.append(r.url.path) or httpx.Response(404)
            ),
        )
        with self.assertRaisesRegex(sources.SourceUnavailable, "path segments"):
            sources.import_url(self.service, self.nvda["id"], self.DOTTED, client=client)
        self.assertEqual(requested, [])


class StoredV1DocumentTests(Case):
    def test_an_acceptance_time_saved_under_the_v1_rule_is_rechecked(self):
        # v1 accepted any supplied header's acceptance time unless the accession conflicted with an SEC folder. Recreate such a row: a mirror URL carrying
        # the prior filing's header, with the published time v1 would have stored.
        doc = self.ingest(PRIOR_HEADERS, url="https://mirror.example.com/q3fy25pr.htm")
        self.assertIsNone(doc["published_at"])
        db = sqlite3.connect(self.store.path)
        with db:
            db.execute(
                "UPDATE documents SET published_at=?, published_basis=? WHERE id=?",
                (
                    "2024-08-28T20:21:16Z",
                    "SEC filing acceptance from supplied header (New York clock converted to UTC)",
                    doc["id"],
                ),
            )
        db.close()
        result = self.service.generate_note(
            self.nvda["id"], doc["id"], as_of="2024-09-01T00:00:00Z", mode="public"
        )["result"]
        self.assertFalse(result["cutoff"]["current_release_eligible"])
        self.assertEqual(result["facts"], [])
        self.assertIsNone(result["sources"][0]["published_at"])
        self.assertTrue(
            result["sources"][0]["published_basis"].startswith(
                "UNKNOWN: the stored acceptance time 2024-08-28T20:21:16Z"
            )
        )


class AnalystInputTests(unittest.TestCase):
    def test_an_unknown_currency_code_is_refused_not_applied(self):
        from fastapi.testclient import TestClient
        from kod.workstation.web import create_app

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "ws"
        service = ResearchService(Store(root), clock=lambda: NOW)
        client = TestClient(create_app(root, offline=True, service=service, testing=True))
        sec = service.store.upsert_security("ACME", "Acme Corp", venue="XTSE", currency="CAD")
        release = (
            b"<html><body><h1>Acme third-quarter 2024 results</h1><p>GAAP</p><p>Amounts in millions</p><table><tr><td></td><td>Q3 2023</td><td>Q3 2024</td></tr>"
            b"<tr><td>Revenue</td><td>$100</td><td>$120</td></tr></table></body></html>"
        )
        doc = service.ingest(
            sec["id"],
            release,
            "r.htm",
            "https://example.com/r.htm",
            published_at="2024-11-01T20:00:00Z",
        )
        token = re.search(r'name="csrf" value="([^"]+)"', client.get("/").text).group(1)
        page = client.post(
            f"/company/{sec['id']}/notes",
            data={
                "csrf": token,
                "current_id": doc["id"],
                "mode": "observed",
                "as_of": NOW,
                "reporting_currency": "zzz",
            },
        )
        self.assertIn("not an ISO 4217 currency code", page.text)
        self.assertEqual(service.store.notes(sec["id"]), [])


if __name__ == "__main__":
    unittest.main()
