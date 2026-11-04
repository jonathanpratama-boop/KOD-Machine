import json
import tempfile
import unittest
from unittest.mock import patch

import httpx

from kod.workstation import sources
from kod.workstation.demo import seed_demo
from kod.workstation.services import ResearchService
from kod.workstation.store import Store


def submissions(cik=320193, stamp="2024-10-31T20:30:25Z"):
    # Synthetic boundary fixture, using fields from the documented SEC schema.
    return json.dumps(
        {
            "cik": cik,
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-24-000120", "0000320193-24-000121"],
                    "form": ["8-K", "4"],
                    "primaryDocument": ["a8-k.htm", "form4.xml"],
                    "filingDate": ["2024-10-31", "2024-11-01"],
                    "acceptanceDateTime": [stamp, "2024-11-01T15:00:00Z"],
                    "items": ["2.02,9.01", ""],
                }
            },
        }
    ).encode()


class SourceTests(unittest.TestCase):
    def test_offline_never_calls_transport(self):
        transport = httpx.MockTransport(lambda request: self.fail("network must not be called"))
        with self.assertRaisesRegex(sources.SourceUnavailable, "Offline"):
            sources.SecClient("test@example.com", offline=True, transport=transport).get(
                "https://data.sec.gov/submissions/x.json"
            )

    def test_contact_is_required_without_disclosing_it(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            self.assertRaisesRegex(sources.SourceUnavailable, "KOD_SEC_CONTACT"),
        ):
            sources.SecClient(
                transport=httpx.MockTransport(lambda _: self.fail("unexpected request"))
            ).get("https://www.sec.gov/x")

    def test_offline_url_import_does_not_even_resolve_dns(self):
        with patch("socket.getaddrinfo", side_effect=AssertionError("DNS attempted")):
            with self.assertRaisesRegex(sources.SourceUnavailable, "Offline"):
                sources.import_url(
                    None,
                    "unused",
                    "https://www.sec.gov/x",
                    client=sources.SecClient("test@example.com", offline=True),
                )

    def test_plain_http_unapproved_hosts_and_credentials_refused(self):
        for url in (
            "http://www.sec.gov/x",
            "https://sec.gov.attacker.test/x",
            "https://127.0.0.1/x",
            "https://www.sec.gov:8443/x",
            "https://u:p@www.sec.gov/x",
            "https://www.sec.gov/x?secret=value",
        ):
            with self.subTest(url=url), self.assertRaises(sources.SourceUnavailable):
                sources.validate_url(url, check_dns=False)

    def test_redirect_to_private_network_refused(self):
        visited = []

        def handler(req):
            visited.append(str(req.url))
            return httpx.Response(302, headers={"location": "https://127.0.0.1/secrets"})

        with self.assertRaises(sources.SourceUnavailable):
            sources.SecClient("test@example.com", transport=httpx.MockTransport(handler)).get(
                "https://www.sec.gov/x"
            )
        self.assertEqual(len(visited), 1)

    def test_retry_429_and_stream_result(self):
        requests = []

        def handler(req):
            requests.append(req)
            return (
                httpx.Response(429, headers={"retry-after": "0"})
                if len(requests) == 1
                else httpx.Response(200, content=b"ok")
            )

        with patch("kod.workstation.sources.time.sleep"):
            self.assertEqual(
                sources.SecClient("test@example.com", transport=httpx.MockTransport(handler)).get(
                    "https://www.sec.gov/x"
                ),
                b"ok",
            )
        self.assertEqual(len(requests), 2)

    def test_403_is_failure_not_empty_success(self):
        with self.assertRaisesRegex(sources.SourceUnavailable, "403"):
            sources.SecClient(
                "test@example.com", transport=httpx.MockTransport(lambda _: httpx.Response(403))
            ).get("https://www.sec.gov/x")

    def test_response_size_limit(self):
        with (
            patch.object(sources, "MAX_BYTES", 3),
            self.assertRaisesRegex(sources.SourceUnavailable, "limit"),
        ):
            sources.SecClient(
                "test@example.com",
                transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"large")),
            ).get("https://www.sec.gov/x")

    def test_explicit_offset_and_new_york_dst_conventions(self):
        self.assertEqual(sources.acceptance_time("2024-10-31T20:30:25Z"), "2024-10-31T20:30:25Z")
        self.assertEqual(sources.acceptance_time("2024-07-01T16:00:00"), "2024-07-01T20:00:00Z")
        self.assertEqual(sources.acceptance_time("2024-01-02T16:00:00"), "2024-01-02T21:00:00Z")
        self.assertIsNone(sources.acceptance_time("2024-01-02"))
        self.assertIsNone(sources.acceptance_time("not a date"))

    def test_submissions_scope_source_time_and_cik_validation(self):
        rows = sources.normalize_submissions(submissions(), "0000320193")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["external_id"], "0000320193-24-000120")
        self.assertIn("/320193/000032019324000120/a8-k.htm", rows[0]["source_url"])
        self.assertEqual(rows[0]["published_at"], "2024-10-31")  # date precision only; see below
        with self.assertRaisesRegex(sources.SourceUnavailable, "CIK"):
            sources.normalize_submissions(submissions(), "2488")

    def test_missing_acceptance_still_gives_only_the_filing_date(self):
        row = sources.normalize_submissions(submissions(stamp=None), "320193")[0]
        self.assertEqual(row["published_at"], "2024-10-31")
        self.assertEqual(row["published_basis"], sources.SUBMISSIONS_DATE_BASIS)

    def test_feed_acceptance_time_is_not_trusted_because_it_runs_hours_late(self):
        # Real values for NVIDIA's Q3 FY2025 8-K (0001045810-24-000315): the feed says
        # 2024-11-21T02:21:20Z; the filing's own header says 16:21:20 New York (21:21:20Z) on
        # 2024-11-20. Trusting the feed would move the filing to the next day.
        body = json.loads(submissions(cik=1045810, stamp="2024-11-21T02:21:20.000Z"))
        recent = body["filings"]["recent"]
        recent["accessionNumber"][0], recent["filingDate"][0] = "0001045810-24-000315", "2024-11-20"
        row = sources.normalize_submissions(json.dumps(body).encode(), "1045810")[0]
        self.assertEqual(row["published_at"], "2024-11-20")
        self.assertEqual(row["metadata"]["acceptance_raw"], "2024-11-21T02:21:20.000Z")
        self.assertFalse(row["metadata"]["acceptance_raw_used"])
        with tempfile.TemporaryDirectory() as d:
            store = Store(d)
            sec = store.upsert_security("NVDA", "NVIDIA Corporation", "1045810")
            event = store.save_event(sec["id"], observed_at="2026-10-22T00:00:00Z", **row)
            self.assertIsNone(event["published_at"])  # never upgraded to a false precise time
            self.assertEqual(event["metadata"]["publication_date"], "2024-11-20")

    def test_bad_filing_date_is_a_failed_refresh(self):
        body = json.loads(submissions())
        body["filings"]["recent"]["filingDate"][0] = "31/10/2024"
        with self.assertRaisesRegex(sources.SourceUnavailable, "filing date"):
            sources.normalize_submissions(json.dumps(body).encode(), "320193")

    def test_bad_column_alignment_is_not_empty_feed(self):
        body = json.loads(submissions())
        body["filings"]["recent"]["form"] = []
        with self.assertRaisesRegex(sources.SourceUnavailable, "different lengths"):
            sources.normalize_submissions(json.dumps(body).encode(), "320193")

    def test_refresh_is_idempotent_preserves_raw_and_reports_failure(self):
        class Client:
            def get(self, url):
                return submissions()

        class Broken:
            def get(self, url):
                raise sources.SourceUnavailable("Provider unavailable")

        with tempfile.TemporaryDirectory() as d:
            store = Store(d)
            service = ResearchService(store)
            sec = store.upsert_security("AAPL", "Apple Inc.", "320193")
            self.assertEqual(sources.refresh_security(service, sec["id"], Client())["new_count"], 1)
            self.assertEqual(sources.refresh_security(service, sec["id"], Client())["new_count"], 0)
            self.assertEqual(len(store.events(sec["id"])), 1)
            doc = store.documents(sec["id"])[0]
            self.assertEqual(store.raw(doc["id"]), submissions())
            failed = sources.refresh_security(service, sec["id"], Broken())
            self.assertEqual(failed["status"], "failed")
            self.assertIn("unavailable", failed["message"])
            self.assertEqual(len(store.events(sec["id"])), 1)

    def test_ticker_lookup_does_not_need_or_call_trading_api(self):
        mapping = {
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [[320193, "Apple Inc.", "AAPL", "Nasdaq"]],
        }
        client = sources.SecClient(
            "test@example.com",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=mapping)),
        )
        self.assertEqual(client.resolve("aapl")["cik"], "0000320193")
        self.assertEqual(client.resolve("aapl")["venue"], "XNAS")


class RealReplayTests(unittest.TestCase):
    def test_four_company_replay_without_network_and_with_correct_facts(self):
        with (
            tempfile.TemporaryDirectory() as d,
            patch("socket.create_connection", side_effect=AssertionError("network")),
        ):
            service = ResearchService(Store(d))
            notes = seed_demo(service)
            expected = {"NVDA": "35082", "AMD": "6819", "AAPL": "94930", "MSFT": "65585"}
            for note in notes:
                result = note["result"]
                rev = next(f for f in result["facts"] if f["metric"] == "revenue")
                self.assertEqual(rev["value"], expected[result["ticker"]])
                self.assertIn("CONSENSUS UNKNOWN", note["markdown"])
                self.assertFalse(result["entry_permission"])
                self.assertEqual(result["mode"], "public")
                self.assertTrue(result["workstation"]["source_versions"])
            ids = {n["id"] for n in notes}
            self.assertEqual({n["id"] for n in seed_demo(service)}, ids)
            self.assertEqual(len(service.store.notes()), 4)
            self.assertEqual(len(Store(d).notes()), 4)


if __name__ == "__main__":
    unittest.main()
