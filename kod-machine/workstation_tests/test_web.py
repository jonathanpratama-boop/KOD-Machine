"""Behavioral checks for the actual local web forms and rendered research."""
from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from kod.workstation.services import ResearchService
from kod.workstation.store import Store
from kod.workstation.web import MAX_BODY, create_app

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "earnings_demo"
PUB = "2024-11-20T21:00:00Z"
NOW = "2026-10-23T04:00:00Z"


def release():
    return b'''<html><body><p>Acme Announces Financial Results for Third Quarter Fiscal 2025</p>
<p>Acme reported results for the third quarter ended October 27, 2024.</p>
<table><tr><td>GAAP</td></tr><tr><td>($ in millions, except earnings per share)</td><td>Q3 FY25</td><td>Q2 FY25</td><td>Q3 FY24</td></tr>
<tr><td>Revenue</td><td>$110</td><td>$100</td><td>$90</td></tr><tr><td>Net income</td><td>$22</td><td>$20</td><td>$18</td></tr>
<tr><td>Diluted earnings per share</td><td>$1.10</td><td>$1.00</td><td>$0.90</td></tr></table></body></html>'''


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "workspace"
        self.service = ResearchService(Store(self.root), clock=lambda: NOW)
        self.app = create_app(self.root, offline=True, service=self.service, testing=True)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def token(self, path="/"):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, response.text)
        token = re.search(r'name="csrf" value="([^"]+)"', response.text)
        self.assertIsNotNone(token, response.text)
        return token.group(1)

    def post(self, path, data=None, files=None, **kwargs):
        data = {"csrf": self.token(), **(data or {})}
        return self.client.post(path, data=data, files=files, **kwargs)

    def company(self, ticker="ACME", name="Acme Corp", cik=None):
        return self.service.store.upsert_security(ticker, name, cik=cik, venue="XNAS", currency="USD")

    def note(self):
        sec = self.company()
        doc = self.service.ingest(sec["id"], release(), "release.htm", "https://example.com/release.htm", published_at=PUB)
        saved = self.service.generate_note(sec["id"], doc["id"], as_of=NOW, mode="observed")
        return sec, doc, saved

    def test_empty_workspace_and_health_are_honest(self):
        response = self.client.get("/")
        self.assertIn("No events in this view", response.text)
        self.assertIn("OFFLINE", response.text)
        health = self.client.get("/health")
        self.assertIn("Never checked", health.text)
        self.assertIn("NOT IMPLEMENTED", health.text)
        self.assertIn("Unusual Whales", health.text)
        self.assertNotIn("api_key=", health.text)

    def test_full_form_journey_persists_note_annotation_and_export(self):
        added = self.post("/watchlist", {"ticker": "ACME", "name": "Acme Corp", "venue": "XNAS", "currency": "USD"})
        self.assertEqual(added.status_code, 200)
        sec = self.service.store.securities()[0]
        uploaded = self.post(f"/company/{sec['id']}/upload", {"role": "current", "source_url": "https://example.com/release.htm", "published_at": PUB}, files={"document": ("release.htm", release(), "text/html")})
        self.assertIn("Source preserved and parsed", uploaded.text)
        doc = next(d for d in self.service.store.documents(sec["id"]) if d["extraction_status"] == "parsed")
        generated = self.post(f"/company/{sec['id']}/notes", {"current_id": doc["id"], "mode": "observed", "as_of": NOW})
        self.assertEqual(generated.status_code, 200, generated.text)
        self.assertIn("Reported figures", generated.text)
        self.assertIn("CONSENSUS UNKNOWN", generated.text)
        self.assertIn("110", generated.text)
        note = self.service.store.notes(sec["id"])[0]
        annotated = self.post(f"/note/{note['id']}/annotations", {"thesis": "Demand may be improving", "invalidation": "Next revenue falls", "review_condition": "Next release"})
        self.assertIn("new annotation version", annotated.text)
        restarted = TestClient(create_app(self.root, offline=True, testing=True))
        self.addCleanup(restarted.close)
        recovered = restarted.get(f"/note/{note['id']}")
        self.assertIn("Demand may be improving", recovered.text)
        exported = restarted.get(f"/note/{note['id']}/export.json")
        self.assertEqual(exported.status_code, 200)
        self.assertFalse(exported.json()["entry_permission"])
        self.assertEqual(exported.json()["annotations"][0]["thesis"], "Demand may be improving")
        markdown = restarted.get(f"/note/{note['id']}/export.md")
        self.assertIn("User research annotation", markdown.text)
        self.assertIn("Demand may be improving", markdown.text)

    def test_unresolved_period_is_visible_and_the_analyst_records_it_through_the_form(self):
        sec = self.company()
        unstated = release().replace(b"Acme Announces Financial Results for Third Quarter Fiscal 2025", b"Acme financial results").replace(b"for the third quarter ended October 27, 2024", b"for the period")
        uploaded = self.post(f"/company/{sec['id']}/upload", {"role": "current", "source_url": "https://example.com/r.htm", "published_at": PUB}, files={"document": ("r.htm", unstated, "text/html")})
        self.assertIn("does not establish which quarter it reports", uploaded.text)
        page = self.client.get(f"/company/{sec['id']}").text
        self.assertIn("needs review", page)
        self.assertIn('name="period"', page)
        doc = self.service.store.documents(sec["id"])[0]
        withheld = self.post(f"/company/{sec['id']}/notes", {"current_id": doc["id"], "mode": "observed", "as_of": NOW})
        self.assertIn("reported period is unresolved", withheld.text)
        recorded = self.post(f"/company/{sec['id']}/notes", {"current_id": doc["id"], "mode": "observed", "as_of": NOW, "period": "Q3 FY25", "reporting_currency": "usd"})
        self.assertEqual(recorded.status_code, 200, recorded.text)
        self.assertIn("chosen by the analyst", recorded.text)
        latest = self.service.store.notes(sec["id"])[0]
        self.assertEqual(self.service.store.note(latest["id"])["result"]["analyst_inputs"]["reporting_currency"]["currency"], "USD")

    def test_csrf_and_cross_origin_changes_are_refused(self):
        self.assertEqual(self.client.post("/watchlist", data={"ticker": "EVIL", "name": "Bad"}).status_code, 403)
        token = self.token()
        cross = self.client.post("/watchlist", data={"csrf": token, "ticker": "EVIL", "name": "Bad"}, headers={"Origin": "https://evil.example"})
        self.assertEqual(cross.status_code, 403)
        self.assertFalse(self.service.store.securities())

    def test_default_app_rejects_untrusted_host(self):
        client = TestClient(create_app(self.root, offline=True), base_url="http://attacker.example")
        self.addCleanup(client.close)
        self.assertEqual(client.get("/").status_code, 400)

    def test_offline_refresh_and_import_never_call_provider(self):
        sec = self.company()
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")), patch("socket.getaddrinfo", side_effect=AssertionError("network forbidden")):
            refreshed = self.post(f"/company/{sec['id']}/refresh")
            imported = self.post(f"/company/{sec['id']}/import-url", {"source_url": "https://www.sec.gov/Archives/test.htm", "role": "current"})
        self.assertIn("SEC refresh is disabled", refreshed.text)
        self.assertIn("remote fetching is disabled", imported.text)
        self.assertFalse(self.service.store.documents(sec["id"]))

    def test_unsupported_html_is_preserved_and_cannot_be_selected_as_parsed(self):
        sec = self.company()
        response = self.post(f"/company/{sec['id']}/upload", {"role": "current"}, files={"document": ("unknown.html", b"<html><p>Unsupported financial narrative</p></html>", "text/html")})
        self.assertIn("this layout was not parsed", response.text)
        doc = self.service.store.documents(sec["id"])[0]
        self.assertEqual(doc["extraction_status"], "unsupported")
        self.assertIn("Source retained", response.text)
        self.assertIn("disabled", response.text)

    def test_document_and_annotation_text_is_escaped(self):
        sec, doc, note = self.note()
        evil = '<script>alert(1)</script> [click](javascript:alert(1)) ![tracking](https://evil.example/x)'
        response = self.post(f"/note/{note['id']}/annotations", {"thesis": evil})
        self.assertNotIn("<script>", response.text)
        self.assertIn("&lt;script&gt;", response.text)
        self.assertNotIn('<img src="https://evil.example', response.text)
        source = self.client.get(f"/source/{doc['id']}")
        self.assertTrue(source.headers["content-type"].startswith("text/plain"))
        self.assertEqual(source.headers["x-content-type-options"], "nosniff")

    def test_unavailable_source_time_withholds_figures_in_html_and_json(self):
        sec = self.company()
        doc = self.service.ingest(sec["id"], release(), "release.htm", "https://example.com/release.htm", published_at=PUB)
        saved = self.service.generate_note(sec["id"], doc["id"], as_of="2024-01-01T00:00:00Z", mode="public")
        response = self.client.get(f"/note/{saved['id']}")
        self.assertIn("WITHHELD BY CUTOFF", response.text)
        self.assertNotIn("Reported figures", response.text)
        self.assertNotIn("$110", response.text)
        exported = self.client.get(f"/note/{saved['id']}/export.json").json()
        self.assertEqual(exported["result"]["facts"], [])

    def test_source_ownership_mismatch_cannot_generate_note(self):
        sec, doc, _ = self.note()
        other = self.company("OTHER", "Other Co")
        response = self.post(f"/company/{other['id']}/notes", {"current_id": doc["id"], "mode": "observed", "as_of": NOW})
        self.assertFalse(self.service.store.notes(other["id"]))
        self.assertIn("Other Co", response.text)

    def test_missing_objects_and_unsafe_citation_are_useful_errors(self):
        self.assertEqual(self.client.get("/company/not-found").status_code, 404)
        self.assertEqual(self.client.get("/note/not-found").status_code, 404)
        self.assertEqual(self.client.get("/source/not-found").status_code, 404)
        sec = self.company()
        response = self.post(f"/company/{sec['id']}/upload", {"role": "current", "source_url": "javascript:alert(1)"}, files={"document": ("release.htm", release(), "text/html")})
        self.assertIn("valid http or https", response.text)
        self.assertFalse(self.service.store.documents(sec["id"]))

    def test_watchlist_removal_keeps_evidence(self):
        sec, doc, note = self.note()
        response = self.post(f"/watchlist/{sec['id']}/remove")
        self.assertIn("Saved evidence and notes are retained", response.text)
        self.assertFalse(self.service.store.securities())
        self.assertEqual(self.service.store.document(doc["id"])["id"], doc["id"])
        self.assertEqual(self.client.get(f"/note/{note['id']}").status_code, 200)

    def test_input_length_and_body_size_limits(self):
        response = self.client.post("/watchlist", content=b"x", headers={"Content-Length": str(MAX_BODY + 1), "Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(response.status_code, 413)
        response = self.post("/watchlist", {"ticker": "ACME", "name": "x" * 181})
        self.assertIn("180-character", response.text)
        self.assertFalse(self.service.store.securities())

    def test_streamed_request_without_content_length_is_still_bounded(self):
        def chunks():
            for _ in range(11):
                yield b"x" * (1024 * 1024)
        response = self.client.post("/watchlist", content=chunks(), headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(response.status_code, 413)
        self.assertFalse(self.service.store.securities())

    def test_online_identity_lookup_uses_explicit_source_metadata(self):
        online = TestClient(create_app(self.root, testing=True))
        self.addCleanup(online.close)
        page = online.get("/")
        token = re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)
        identity = {"ticker": "AAPL", "name": "Apple Inc.", "cik": "0000320193", "venue": "XNAS", "currency": "USD", "association": "verified_from_filing_metadata"}
        raw = b'{"fields":["cik","name","ticker","exchange"],"data":[[320193,"Apple Inc.","AAPL","Nasdaq"]]}'
        with patch("kod.workstation.sources.SecClient") as client_type:
            client = client_type.return_value
            client.resolve.return_value = identity
            client.last_mapping_raw = raw
            client.last_mapping_observed_at = NOW
            response = online.post("/watchlist/resolve", data={"csrf": token, "ticker": "AAPL"})
        client.resolve.assert_called_once_with("AAPL")
        self.assertIn("resolved from current SEC", response.text)
        self.assertIn("Apple Inc.", response.text)
        sec = self.service.store.securities()[0]
        self.assertEqual(sec["association"], "verified_from_filing_metadata")
        mapping = self.service.store.documents(sec["id"])[0]
        self.assertEqual(mapping["role"], "metadata")
        self.assertEqual(mapping["provider"], "sec_mapping")
        self.assertEqual(mapping["observed_at"], NOW)
        self.assertEqual(mapping["extraction_status"], "metadata")
        self.assertEqual(mapping["source_url"], "https://www.sec.gov/files/company_tickers_exchange.json")
        self.assertEqual(self.service.store.raw(mapping["id"]), raw)
        self.assertNotIn("company_tickers_exchange.json", online.get("/").text)

    def test_metadata_headers_and_provider_metadata_are_not_release_events(self):
        sec, doc, _ = self.note()
        self.service.store.save_document(sec["id"], b"<html>SEC header evidence</html>", "metadata_header_marker.html", "https://example.com/headers.html",
                                         role="metadata", provider="local", observed_at=NOW, extraction_status="not_applicable")
        self.service.store.save_document(sec["id"], b"{}", "submissions_marker.json", "https://data.sec.gov/submissions/CIK0000000001.json",
                                         role="other", provider="sec_submissions", observed_at=NOW, extraction_status="not_applicable")
        page = self.client.get("/")
        self.assertIn("release.htm", page.text)
        self.assertNotIn("metadata_header_marker", page.text)
        self.assertNotIn("submissions_marker", page.text)

    def test_job_failure_is_different_from_no_new_events(self):
        self.service.store.record_job("sec", "ACME", "success", "Checked successfully; no new filings", started_at=PUB, finished_at=PUB, new_count=0)
        self.service.store.record_job("sec", "ACME", "failed", "Source temporarily unavailable", started_at=NOW, finished_at=NOW)
        health = self.client.get("/health")
        self.assertIn("Source temporarily unavailable", health.text)
        self.assertIn("Checked successfully; no new filings", health.text)
        self.assertIn("2024-11-20", health.text)

    @unittest.skipUnless((DEMO / "current_q3fy25pr.htm").exists(), "real fixture not materialized")
    def test_real_release_is_rendered_via_same_upload_and_note_routes(self):
        sec = self.company("NVDA", "NVIDIA Corporation", "1045810")
        response = self.post(f"/company/{sec['id']}/upload", {"role": "current", "published_at": PUB, "source_url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000315/q3fy25pr.htm"}, files={"document": ("q3fy25pr.htm", (DEMO / "current_q3fy25pr.htm").read_bytes(), "text/html")})
        self.assertIn("Source preserved and parsed", response.text)
        doc = self.service.store.documents(sec["id"])[0]
        response = self.post(f"/company/{sec['id']}/notes", {"current_id": doc["id"], "mode": "observed", "as_of": NOW})
        self.assertIn("35,082", response.text)
        self.assertIn("0.78", response.text)
        self.assertIn("Evidence", response.text)


if __name__ == "__main__":
    unittest.main()


class DateOnlyEventTests(unittest.TestCase):
    def test_inbox_and_timeline_show_a_filing_date_as_date_only_and_sort_by_it(self):
        with tempfile.TemporaryDirectory() as d:
            service = ResearchService(Store(Path(d) / "w"), clock=lambda: NOW)
            store = service.store
            sec = store.upsert_security("NVDA", "NVIDIA Corporation", "1045810")
            for acc, day in (("0001045810-24-000262", "2024-08-28"), ("0001045810-24-000315", "2024-11-20")):
                store.save_event(sec["id"], acc, "8-K", f"8-K · {day}", "https://www.sec.gov/Archives/edgar/data/1045810/x/y.htm",
                                 published_at=day, published_basis="SEC filing date only", observed_at=NOW)
            self.assertEqual([e["external_id"] for e in store.events(sec["id"])], ["0001045810-24-000315", "0001045810-24-000262"])
            client = TestClient(create_app(Path(d) / "w", offline=True, service=service, testing=True))
            inbox = client.get("/").text
            self.assertIn("2024-11-20 (date only)", inbox)
            self.assertLess(inbox.index("2024-11-20 (date only)"), inbox.index("2024-08-28 (date only)"))
            self.assertIn("2024-11-20 (date only)", client.get("/company/" + sec["id"]).text)
            self.assertNotIn("2024-08-28 (date only)", client.get("/?after=2024-09-01").text)
            client.close()
