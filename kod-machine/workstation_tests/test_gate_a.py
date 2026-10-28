"""Gate A at the workstation boundary: a filing header proves a filing's acceptance time only when its accession is this source's; a listing currency is never the
reporting currency; a release whose quarter is unresolved is kept for review, not labelled with a guess."""

from pathlib import Path
import tempfile
import unittest

from kod.workstation.services import ResearchService
from kod.workstation.store import Store

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "earnings_demo"
NVDA_URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000315/q3fy25pr.htm"

RELEASE = b"""<html><body><h1>Acme third-quarter 2024 results</h1>
<p>GAAP</p><p>Amounts in millions</p><table>
<tr><td></td><td>Q3 2023</td><td>Q3 2024</td></tr>
<tr><td>Revenue</td><td>$100</td><td>$120</td></tr>
<tr><td>Diluted earnings per share</td><td>$1.00</td><td>$1.20</td></tr>
</table></body></html>"""
UNSTATED = RELEASE.replace(b"<h1>Acme third-quarter 2024 results</h1>", b"<h1>Acme financial results</h1>")


class HeaderAccessionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / "data")
        self.service = ResearchService(self.store, clock=lambda: "2026-10-23T12:00:00Z")
        self.nvda = self.store.upsert_security("NVDA", "NVIDIA Corporation", cik="1045810")
        self.headers = (DEMO / "current_0001045810-24-000315-index-headers.html").read_bytes()
        self.release = (DEMO / "current_q3fy25pr.htm").read_bytes()

    def ingest(self, headers, url=NVDA_URL, **kw):
        return self.service.ingest(self.nvda["id"], self.release, "q3fy25pr.htm", url, sec_headers=headers, retrieved_at="2026-10-22T14:40:11Z", **kw)

    def test_matching_accession_gives_the_filing_acceptance_time(self):
        doc = self.ingest(self.headers)
        self.assertEqual(doc["published_at"], "2024-11-20T21:21:20Z")
        self.assertIn("accession number matches the source URL", doc["published_basis"])
        self.assertEqual(doc["metadata"]["header_link"], {"status": "matched", "accession": "0001045810-24-000315",
                                                          "reason": "the header's accession number is the source URL's filing folder"})

    def test_missing_accession_keeps_the_acceptance_as_an_assertion_only(self):
        bare = b"CENTRAL INDEX KEY: 0001045810\n<ACCEPTANCE-DATETIME>20241120162120"
        doc = self.ingest(bare)
        self.assertIsNone(doc["published_at"])
        self.assertTrue(doc["published_basis"].startswith("UNKNOWN: a supplied header asserts SEC acceptance"))
        self.assertEqual(doc["metadata"]["asserted_header_acceptance"], "2024-11-20T21:21:20Z")
        self.assertEqual(doc["metadata"]["header_link"]["status"], "unestablished")
        header_doc = self.store.document(doc["metadata"]["sec_headers_document_id"])
        self.assertIsNone(header_doc["published_at"])

    def test_conflicting_accession_is_refused(self):
        other = self.headers.replace(b"0001045810-24-000315", b"0001045810-24-000262")
        with self.assertRaisesRegex(ValueError, "different filing"):
            self.ingest(other)
        two = self.headers.replace(b"ACCESSION NUMBER:\t\t0001045810-24-000315", b"ACCESSION NUMBER:\t\t0001045810-24-000262")
        with self.assertRaisesRegex(ValueError, "more than one accession"):
            self.ingest(two)
        self.assertEqual(self.store.documents(self.nvda["id"]), [])

    def test_a_header_cannot_be_tied_to_a_non_sec_url(self):
        doc = self.ingest(self.headers, url="https://example.com/nvidia-q3.htm")
        self.assertIsNone(doc["published_at"])
        self.assertEqual(doc["metadata"]["header_link"]["status"], "unestablished")
        self.assertIn("not an SEC Archives filing folder", doc["published_basis"])

    def test_a_supplied_publication_time_is_kept_with_an_unestablished_header(self):
        bare = b"CENTRAL INDEX KEY: 0001045810\n<ACCEPTANCE-DATETIME>20241120162120"
        doc = self.ingest(bare, published_at="2024-11-20T21:20:00Z")
        self.assertEqual((doc["published_at"], doc["published_basis"]), ("2024-11-20T21:20:00Z", "publication timestamp supplied by the user"))


class ReportingCurrencyAndPeriodTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / "data")
        self.service = ResearchService(self.store, clock=lambda: "2026-10-23T12:00:00Z")
        self.acme = self.store.upsert_security("ACME", "Acme", cik="1234", venue="XTSE", currency="CAD")

    def ingest(self, raw):
        return self.service.ingest(self.acme["id"], raw, "r.htm", "https://example.com/r.htm", published_at="2024-11-01T20:00:00Z", retrieved_at="2024-11-01T20:10:00Z")

    def test_listing_currency_is_not_the_reporting_currency(self):
        doc = self.ingest(RELEASE)
        result = self.service.generate_note(self.acme["id"], doc["id"], as_of="2024-11-01T21:00:00Z")["result"]
        self.assertEqual({f["currency"] for f in result["facts"]}, {"USD"})
        self.assertTrue(all("CURRENCY_ASSUMED_USD_FROM_$_SIGN" in f["flags"] for f in result["facts"]))
        recorded = self.service.generate_note(self.acme["id"], doc["id"], as_of="2024-11-01T21:00:00Z", reporting_currency="CAD")["result"]
        self.assertEqual({f["currency"] for f in recorded["facts"]}, {"CAD"})
        self.assertEqual(recorded["analyst_inputs"]["reporting_currency"]["recorded_by"], "analyst (workstation)")

    def test_an_unresolved_period_is_kept_for_review_and_can_be_recorded(self):
        doc = self.ingest(UNSTATED)
        self.assertEqual(doc["extraction_status"], "needs_review")
        self.assertIn("does not state which quarter", doc["metadata"]["review_reason"])
        withheld = self.service.generate_note(self.acme["id"], doc["id"], as_of="2024-11-01T21:00:00Z")
        self.assertEqual((withheld["result"]["status"], withheld["result"]["facts"]), ("PERIOD_UNRESOLVED", []))
        self.assertIn("reported period is unresolved", withheld["markdown"])
        chosen = self.service.generate_note(self.acme["id"], doc["id"], as_of="2024-11-01T21:00:00Z", period="Q3 2024")["result"]
        self.assertEqual((chosen["period"], chosen["period_resolution"]["basis"]), ("Q3 2024", "ANALYST_OVERRIDE"))
        self.assertEqual([(p["prior_period"], p["relation"]) for p in chosen["prior_period"] if p["metric"] == "revenue"], [("Q3 2023", "YEAR_OVER_YEAR")])


if __name__ == "__main__":
    unittest.main()
