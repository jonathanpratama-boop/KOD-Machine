"""Gate C: SEC companyfacts history from real preserved responses (fetched 2026-10-23, trimmed to the mapped concepts; see examples/companyfacts/)."""

from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from kod.workstation import companyfacts, financials, quarters
from kod.workstation.financials import FinancialRepository
from kod.workstation.policy import DAY_END, AsOfPolicy
from kod.workstation.services import ResearchService
from kod.workstation.store import Store

ROOT = Path(__file__).resolve().parents[1]
CF = ROOT / "examples" / "companyfacts"
NOW = "2026-10-23T12:00:00Z"
CIKS = {"NVDA": "1045810", "AAPL": "320193", "AMD": "2488", "MSFT": "789019", "TXN": "97476", "COST": "909832", "JPM": "19617", "PLUG": "1093691"}
OBSERVED = {s["ticker"]: s["observed_at"] for s in json.loads((CF / "SOURCES.json").read_text()) if s["kind"] == "companyfacts"}


def fixture(ticker, kind="companyfacts"):
    return gzip.decompress((CF / ticker / f"{kind}.json.gz").read_bytes())


class FixtureIntegrityTests(unittest.TestCase):
    def test_fixtures_match_their_recorded_hashes(self):
        for s in json.loads((CF / "SOURCES.json").read_text()):
            self.assertEqual(hashlib.sha256((CF / s["fixture"]).read_bytes()).hexdigest(), s["fixture_sha256"], s["fixture"])
            self.assertTrue(s["url"].startswith("https://data.sec.gov/"))


class CompanyFactsCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / "ws")
        self.service = ResearchService(self.store, clock=lambda: NOW)

    def company(self, ticker):
        sec = self.store.upsert_security(ticker, ticker, cik=CIKS[ticker])
        coverage = self.service.import_companyfacts(sec["id"], fixture(ticker), f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(CIKS[ticker]):010d}.json",
                                                    observed_at=OBSERVED[ticker], submissions=fixture(ticker, "submissions"),
                                                    submissions_url=f"https://data.sec.gov/submissions/CIK{int(CIKS[ticker]):010d}.json")
        return sec, coverage

    def figures(self, sec, metric, policy, view="as_reported"):
        return financials.resolve(FinancialRepository(self.store).observations(sec["id"], metric, policy), policy, view)


class ImportTests(CompanyFactsCase):
    def test_values_tags_units_and_pointers_are_kept_exactly(self):
        sec, coverage = self.company("NVDA")
        self.assertEqual(coverage["absent_metrics"], [])
        self.assertEqual(coverage["added"], coverage["observations"])
        data = json.loads(fixture("NVDA"))
        everything = FinancialRepository(self.store).all_for(sec["id"])
        self.assertEqual(len(everything), coverage["observations"])
        units = set()
        for o in everything:
            node = companyfacts.resolve_pointer(data, o.evidence["json_pointer"])
            units.add(o.unit)
            self.assertEqual(Decimal(str(node["val"])), o.value)
            self.assertEqual((node["accn"], node["form"], node["filed"]), (o.accession, o.form, o.filed))
            self.assertEqual(o.publication_date, node["filed"])
            self.assertIsNone(o.published_at)                              # a filing date is never turned into a precise time
        self.assertEqual(units, {"currency", "currency/share", "shares"})   # every unit kind, including the per-share key 'USD/shares'
        self.assertEqual(companyfacts.json_pointer("units", "USD/shares", 0), "/units/USD~1shares/0")
        # Importing the same response again records nothing new.
        self.assertEqual(self.service.import_companyfacts(sec["id"], fixture("NVDA"), "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
                                                          observed_at=OBSERVED["NVDA"])["added"], 0)

    def test_the_wrong_company_and_unknown_units_are_refused_or_reported(self):
        sec = self.store.upsert_security("AMD", "AMD", cik="2488")
        with self.assertRaisesRegex(ValueError, "not the selected company"):
            self.service.import_companyfacts(sec["id"], fixture("NVDA"), "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json")
        _, coverage = self.company("COST")
        self.assertIn("us-gaap:EarningsPerShareDiluted [pure]", coverage["unmapped_units"])
        self.assertIn("operating_expenses", coverage["absent_metrics"])

    def test_a_bank_is_marked_outside_the_operating_company_model(self):
        _, coverage = self.company("JPM")
        self.assertEqual(coverage["business_type"]["supported"], False)
        self.assertIn("bank", coverage["business_type"]["reason"])
        _, coverage = self.company("TXN")
        self.assertTrue(coverage["business_type"]["supported"])


class RevisionTests(CompanyFactsCase):
    def test_apples_fy2008_restatement_is_shown_as_reported_or_latest_by_cutoff(self):
        sec, _ = self.company("AAPL")
        fy2008 = lambda figures: next(f for f in figures if f.period.start_date == "2007-09-30" and f.period.end_date == "2008-09-27")  # noqa: E731
        before = AsOfPolicy.parse("2009-12-31T00:00:00Z", "public", DAY_END)
        after = AsOfPolicy.parse("2010-02-01T00:00:00Z", "public", DAY_END)
        self.assertEqual(fy2008(self.figures(sec, "net_income", before)).value, Decimal("4834000000"))       # 10-K filed 2009-10-27
        self.assertEqual(fy2008(self.figures(sec, "net_income", before, "latest")).value, Decimal("4834000000"))  # the 10-K/A is not yet public
        self.assertEqual(fy2008(self.figures(sec, "net_income", after)).value, Decimal("4834000000"))
        latest = fy2008(self.figures(sec, "net_income", after, "latest"))
        self.assertEqual(latest.value, Decimal("6119000000"))                                                    # 10-K/A filed 2010-01-25
        self.assertTrue(latest.other_ids)

    def test_date_only_filings_are_not_eligible_under_the_strict_policy(self):
        sec, _ = self.company("AAPL")
        self.assertEqual(FinancialRepository(self.store).observations(sec["id"], "net_income", AsOfPolicy.parse("2026-10-23T00:00:00Z", "public")), [])

    def test_observed_mode_cannot_claim_possession_before_the_download(self):
        sec, _ = self.company("AAPL")
        early = AsOfPolicy.parse("2020-01-01T00:00:00Z", "observed", DAY_END)
        self.assertEqual(FinancialRepository(self.store).observations(sec["id"], "net_income", early), [])
        self.assertTrue(FinancialRepository(self.store).observations(sec["id"], "net_income", AsOfPolicy.parse("2026-10-24T00:00:00Z", "observed", DAY_END)))

    def test_sign_and_scale_disagreements_between_filings_are_flagged(self):
        sec, _ = self.company("PLUG")
        policy = AsOfPolicy.parse("2026-10-24T00:00:00Z", "public", DAY_END)
        figures = {(f.period.start_date, f.period.end_date): f for f in self.figures(sec, "net_income", policy)}
        self.assertTrue(any("sign" in w for w in figures[("2010-01-01", "2010-12-31")].warnings))
        self.assertTrue(any("factor of 100" in w for w in figures[("2011-01-01", "2011-03-31")].warnings))


class QuarterTests(CompanyFactsCase):
    def setUp(self):
        super().setUp()
        self.sec, _ = self.company("NVDA")
        self.policy = AsOfPolicy.parse("2026-10-24T00:00:00Z", "public", DAY_END)

    def series(self, metric):
        figures = [f for f in self.figures(self.sec, metric, self.policy) if f.basis == "GAAP" and f.unit in ("currency", "currency/share")]
        return quarters.quarterly(figures, metric)

    def test_q4_is_derived_from_annual_minus_nine_months_for_revenue_only(self):
        by_end = {q.end: q for q in self.series("revenue")}
        q4 = by_end["2025-01-26"]                                          # fiscal 2025 fourth quarter
        self.assertEqual((q4.status, q4.value), ("derived", Decimal("39331000000")))
        self.assertIn("12 months minus 9 months", q4.calculation.detail["formula"])
        self.assertEqual(by_end["2024-10-27"].status, "reported")
        self.assertEqual(by_end["2024-10-27"].value, Decimal("35082000000"))
        eps = {q.end: q for q in self.series("eps_diluted")}
        self.assertNotIn("2025-01-26", eps)                                # Q4 EPS is never annual minus nine months
        self.assertIn("not additive", quarters.not_derivable_reason("eps_diluted"))
        self.assertIsNotNone(quarters.not_derivable_reason("cash_and_equivalents"))

    def test_ttm_needs_four_contiguous_quarters_of_a_flow(self):
        series = self.series("revenue")
        result = quarters.ttm(series, "2025-01-26", "revenue")
        self.assertEqual((result.status, result.value), ("ok", Decimal("130497000000")))  # equals fiscal 2025 annual revenue
        gap = [q for q in series if q.end != "2024-07-28"]
        self.assertEqual(quarters.ttm(gap, "2025-01-26", "revenue").status, "missing")
        self.assertEqual(quarters.ttm(series, "2025-01-26", "eps_diluted").status, "not_applicable")
        self.assertEqual(quarters.ttm(series, "2025-01-26", "total_assets").status, "not_applicable")


class ReconciliationTests(CompanyFactsCase):
    def test_the_release_agrees_with_the_10q_within_printed_rounding(self):
        sec, _ = self.company("NVDA")
        demo = ROOT / "examples" / "earnings_demo"
        self.service.ingest(sec["id"], (demo / "current_q3fy25pr.htm").read_bytes(), "q3fy25pr.htm",
                            "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000315/q3fy25pr.htm",
                            sec_headers=(demo / "current_0001045810-24-000315-index-headers.html").read_bytes(), retrieved_at="2026-10-22T14:40:11Z")
        policy = AsOfPolicy.parse("2026-10-24T00:00:00Z", "public", DAY_END)
        everything = FinancialRepository(self.store).observations(sec["id"], None, policy)
        release = [o for o in everything if o.provider == "issuer_release_table" and o.period.end_date == "2024-10-27"]
        rows = {(r["metric"], r["basis"]): r for r in financials.reconcile(release, [o for o in everything if o.provider == "sec_companyfacts"])}
        self.assertEqual(rows[("revenue", "GAAP")]["status"], "agrees")
        self.assertEqual(rows[("eps_diluted", "GAAP")]["status"], "agrees")
        self.assertEqual(rows[("net_income", "GAAP")]["status"], "agrees")
        self.assertEqual(rows[("revenue", "NON-GAAP")]["status"], "not_compared")
        self.assertEqual(rows[("revenue", "GAAP")]["tolerance"], "500000")

    def test_filing_chronology_lists_the_source_filings_in_order(self):
        sec, _ = self.company("AAPL")
        chronology = companyfacts.filing_chronology(FinancialRepository(self.store).all_for(sec["id"]), self.service.latest_submissions(sec["id"]))
        self.assertEqual([c["filed"] for c in chronology], sorted(c["filed"] for c in chronology))
        amendment = next(c for c in chronology if c["accession"] == "0001193125-10-012091")
        self.assertEqual((amendment["form"], amendment["amendment"]), ("10-K/A", True))


if __name__ == "__main__":
    unittest.main()


class FiledHistoryRefreshTests(CompanyFactsCase):
    """The explicit live refresh path (two SEC requests under the company's lock), with an injected transport serving the preserved TXN responses."""

    def client(self, status=200):
        import httpx
        from kod.workstation import sources
        self.requested = []

        def respond(request):
            self.requested.append(request.url.path)
            if status != 200:
                return httpx.Response(status)
            return httpx.Response(200, content=fixture("TXN") if "companyfacts" in request.url.path else fixture("TXN", "submissions"))
        return sources.SecClient("test@example.com", transport=httpx.MockTransport(respond))

    def test_a_refresh_records_observations_and_a_success_job(self):
        from kod.workstation import sources
        txn = self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"])
        first = sources.refresh_companyfacts(self.service, txn["id"], client=self.client())
        self.assertEqual(self.requested, ["/api/xbrl/companyfacts/CIK0000097476.json", "/submissions/CIK0000097476.json"])
        self.assertGreater(first["added"], 1000)
        self.assertIn("new filed-history observation", first["message"])
        job = self.store.jobs()[0]
        self.assertEqual((job["provider"], job["status"]), ("sec-companyfacts", "success"))
        again = sources.refresh_companyfacts(self.service, txn["id"], client=self.client())
        self.assertEqual(again["added"], 0)                                            # the same response adds nothing

    def test_a_failed_refresh_is_recorded_as_failed_and_changes_nothing(self):
        from kod.workstation import sources
        txn = self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"])
        with self.assertRaises(sources.SourceUnavailable):
            sources.refresh_companyfacts(self.service, txn["id"], client=self.client(status=404))
        self.assertEqual(self.store.jobs()[0]["status"], "failed")
        self.assertFalse(FinancialRepository(self.store).all_for(txn["id"]))

    def test_the_command_line_offers_the_filed_history_refresh(self):
        import contextlib
        import io
        from unittest.mock import patch
        from kod.workstation import cli
        self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"])
        out = io.StringIO()
        with patch.dict("os.environ", {}, clear=True), contextlib.redirect_stdout(out):
            code = cli.main(["refresh", "--filed-history", "--ticker", "TXN", "--data-dir", str(self.store.root)])
        self.assertEqual(code, 2)                                                          # no KOD_SEC_CONTACT: a failure, reported, not an empty success
        self.assertIn("KOD_SEC_CONTACT", out.getvalue())
