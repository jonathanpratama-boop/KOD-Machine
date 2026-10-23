"""Gate D: the company dossier (longitudinal history, meaningful comparisons, provenance) and cutoff-aware archive search, on real preserved SEC responses."""

from decimal import Decimal
import gzip
import json
from pathlib import Path
import re
import tempfile
import unittest

from kod.workstation import dossier, financials, search
from kod.workstation.domain import canonical, identity
from kod.workstation.policy import DAY_END, STRICT, AsOfPolicy
from kod.workstation.services import ResearchService
from kod.workstation.store import Store

ROOT = Path(__file__).resolve().parents[1]
CF = ROOT / "examples" / "companyfacts"
SOURCES = {(s["ticker"], s["kind"]): s for s in json.loads((CF / "SOURCES.json").read_text())}
CIKS = {"NVDA": "1045810", "AAPL": "320193", "AMD": "2488", "MSFT": "789019", "TXN": "97476", "COST": "909832", "JPM": "19617", "PLUG": "1093691"}
NOW = "2026-10-23T12:00:00Z"


def policy(cutoff, mode="public", version=DAY_END):
    return AsOfPolicy.parse(cutoff, mode, version)


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / "ws")
        self.service = ResearchService(self.store, clock=lambda: NOW)

    def company(self, ticker):
        sec = self.store.upsert_security(ticker, ticker, cik=CIKS[ticker])
        facts, subs = SOURCES[(ticker, "companyfacts")], SOURCES[(ticker, "submissions")]
        self.service.import_companyfacts(sec["id"], gzip.decompress((CF / facts["fixture"]).read_bytes()), facts["url"], observed_at=facts["observed_at"],
                                         submissions=gzip.decompress((CF / subs["fixture"]).read_bytes()), submissions_url=subs["url"])
        return sec

    def build(self, sec, cutoff, mode="public", view="as_reported", version=DAY_END):
        return dossier.build(self.service, sec["id"], policy(cutoff, mode, version), view)

    @staticmethod
    def change(d, key):
        return next(c for c in d["changes"] if c["key"] == key)


class ComparisonTests(Case):
    def test_a_stock_split_never_distorts_per_share_or_share_count_changes(self):
        nvda = self.company("NVDA")
        d = self.build(nvda, "2024-09-01T00:00:00Z")                 # NVIDIA's 10-for-1 split took effect in June 2024
        eps, shares = self.change(d, "eps_diluted_yoy"), self.change(d, "diluted_shares_yoy")
        self.assertEqual(d["latest_quarter_end"], "2024-07-28")
        self.assertEqual(eps["status"], "ok")
        self.assertAlmostEqual(float(eps["value"]), 168.0, places=1)  # 0.67 vs the split-adjusted 0.25 the same 10-Q presents
        self.assertIn("same filing", eps["comparison_basis"])
        self.assertLess(abs(float(shares["value"])), 2)               # not +900% against the pre-split count first reported in 2023
        self.assertIn("same filing", shares["comparison_basis"])

    def test_without_a_same_filing_comparative_share_measures_are_withheld_and_flows_flagged(self):
        nvda = self.company("NVDA")
        d = self.build(nvda, "2024-09-01T00:00:00Z")
        s = dossier._Series("eps_diluted", [], [], dossier._Index([]), policy("2024-09-01T00:00:00Z"), "as_reported")
        self.assertEqual(s.comparable_pair("2024-07-28"), (None, None, "no current quarter figure"))
        # Remove the current 10-Q's comparatives: per-share falls back to nothing, revenue to a flagged fallback.
        repo = financials.FinancialRepository(self.store)
        pol = policy("2024-09-01T00:00:00Z")
        eligible = [o for o in repo.observations(nvda["id"], None, pol) if not (o.accession == "0001045810-24-000264" and o.period.end_date == "2023-07-30")]
        figures = financials.resolve([o for o in eligible if o.provider == "sec_companyfacts"], pol)
        index = dossier._Index(eligible)
        eps = dossier._Series("eps_diluted", figures, eligible, index, pol, "as_reported")
        cur, prior, how = eps.comparable_pair("2024-07-28")
        self.assertIsNone(prior)
        self.assertIn("stock split", how)
        rev = dossier._Series("revenue", figures, eligible, index, pol, "as_reported")
        cur, prior, how = rev.comparable_pair("2024-07-28")
        self.assertEqual(prior.value, Decimal("13507000000"))
        self.assertIn("not presented in the current filing", how)
        self.assertTrue(d)

    def test_a_fourth_quarter_is_compared_using_comparatives_from_the_same_two_filings(self):
        nvda = self.company("NVDA")
        d = self.build(nvda, "2025-03-01T00:00:00Z")
        rev = self.change(d, "revenue_yoy")
        self.assertEqual(d["latest_quarter_end"], "2025-01-26")
        self.assertIn("derived from the comparatives presented in the same filings", rev["comparison_basis"])
        self.assertAlmostEqual(float(rev["value"]), (39331 - 22103) / 22103 * 100, places=3)
        self.assertTrue(rev["derived_inputs"])
        self.assertEqual(self.change(d, "eps_diluted_yoy")["status"], "missing")        # Q4 EPS is never annual minus nine months
        self.assertIn("not additive", self.change(d, "eps_diluted_yoy")["reasons"][0])

    def test_margins_change_in_points_and_a_loss_base_is_not_divided_by(self):
        amd = self.company("AMD")
        d = self.build(amd, "2024-08-15T00:00:00Z")
        margin = self.change(d, "operating_margin_yoy")
        self.assertEqual((margin["unit"], margin["status"]), ("percentage points", "ok"))
        self.assertAlmostEqual(float(margin["value"]), (269 / 5835 - (-20) / 5359) * 100, places=3)
        plug = self.company("PLUG")
        p = self.build(plug, "2024-12-01T00:00:00Z")
        self.assertEqual(self.change(p, "net_income_yoy")["status"], "not_applicable")    # Plug Power's year-ago quarter was a loss
        self.assertEqual(self.change(p, "cash_conversion_fy")["status"], "not_applicable")

    def test_a_bank_gets_no_operating_company_cash_flow_ratios(self):
        jpm = self.company("JPM")
        d = self.build(jpm, NOW, "observed")
        self.assertIs(d["coverage"]["business_type"]["supported"], False)
        for key in ("cash_conversion_fy", "capex_intensity_fy", "cfo_minus_capex_fy"):
            self.assertEqual(self.change(d, key)["status"], "not_applicable")
            self.assertIn("bank", self.change(d, key)["reasons"][0])

    def test_supported_changes_follow_the_published_catalog_order(self):
        aapl = self.company("AAPL")
        d = self.build(aapl, NOW, "observed")
        order = [k for k, *_ in dossier.CHANGES]
        self.assertEqual(d["supported_changes"], [k for k in order if self.change(d, k)["status"] == "ok"][:dossier.SUPPORTED_SHOWN])
        self.assertEqual([c["key"] for c in d["changes"]], order)


class RevisionTests(Case):
    def test_as_reported_and_latest_views_and_the_restatement_question(self):
        aapl = self.company("AAPL")
        first = self.build(aapl, "2010-02-01T00:00:00Z")
        latest = self.build(aapl, "2010-02-01T00:00:00Z", view="latest")

        def fy2008(d):
            return next(c for c in d["history"]["annual"]["net_income"] if c["period"]["end"] == "2008-09-27")
        self.assertEqual(fy2008(first)["value"], "4834000000")
        self.assertEqual(fy2008(latest)["value"], "6119000000")
        self.assertEqual(fy2008(first)["revisions"][0]["form"], "10-K/A")
        self.assertTrue(any("10-K/A" in q["text"] and "Net income" in q["text"] for q in first["questions"]) or
                        any(r["label"] == "Net income" and r["form"] == "10-K/A" for r in first["revisions"]))

    def test_a_restated_annual_figure_is_not_differenced_with_an_unrestated_nine_months(self):
        aapl = self.company("AAPL")
        first = self.build(aapl, "2010-02-01T00:00:00Z")
        latest = self.build(aapl, "2010-02-01T00:00:00Z", view="latest")
        q4 = lambda d: next((c for c in d["history"]["quarterly"]["revenue"] if c["period"]["end"] == "2008-09-27"), None)  # noqa: E731
        self.assertEqual((q4(first)["status"], q4(first)["value"]), ("derived", "7895000000"))
        self.assertEqual(q4(latest)["status"], "not_derivable")
        self.assertIn("accounting vintages", " ".join(q4(latest)["reasons"]))

    def test_rounding_differences_are_not_revisions(self):
        nvda = self.company("NVDA")
        d = self.build(nvda, "2016-06-01T00:00:00Z")                  # fiscal 2014 revenue: 4,130,162 thousand, later shown as 4,130 million
        cells = [c for cells in d["history"]["annual"].values() for c in cells]
        self.assertTrue(all(not financials.same_within_rounding(Decimal(c["value"]), Decimal(r["value"])) for c in cells for r in c["revisions"]))
        self.assertTrue(any(c["rounding_differences"] for c in cells))       # later filings rounding to millions are counted, not listed as revisions
        self.assertTrue(financials.same_within_rounding(Decimal("4130162000"), Decimal("4130000000")))
        self.assertFalse(financials.same_within_rounding(Decimal("24006000000"), Decimal("24578000000")))
        self.assertFalse(financials.same_within_rounding(Decimal("2.48"), Decimal("0.25")))


class CutoffInvarianceTests(Case):
    def amendment(self, sec, value="99999000000", filed="2024-12-15"):
        """Record a synthetic later amendment restating NVIDIA's fiscal 2024 revenue (an observation of a made-up document)."""
        doc = self.store.save_document(sec["id"], b'{"synthetic": "amendment"}', "amendment.json", "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
                                       published_at=None, published_basis="synthetic test amendment", observed_at=NOW, role="other",
                                       association="user_asserted", provider="test", extraction_status="companyfacts", metadata={"kind": "test"})
        p = financials.period("12 months", start="2023-01-30", end="2024-01-28")
        oid = identity("fob", "synthetic", value)
        row = {"id": oid, "provider": "sec_companyfacts", "issuer_id": None, "security_id": sec["id"], "concept": "Revenues", "taxonomy": "us-gaap",
               "metric": "revenue", "metric_version": 1, "raw_value": value, "value": value, "unit": "currency", "scale": 1, "currency": "USD",
               "currency_basis": "UNIT_OF_MEASURE", "period_id": p.id, "basis": "GAAP", "context": "consolidated (companyfacts whole entity)", "dimensions_available": 0,
               "accession": "0009999999-24-000001", "form": "10-K/A", "filed": filed, "amendment": 1, "source_document_id": doc["id"], "source_sha256": doc["sha256"],
               "evidence": canonical({"json_pointer": "/synthetic"}), "published_at": None, "publication_date": filed, "publication_precision": "date",
               "publication_basis": "synthetic", "observed_at": NOW, "recorded_at": NOW, "parser_version": "test", "mapping_version": "test", "flags": "[]"}
        self.store.record_observations([p], [row])
        return oid

    def test_a_later_amendment_changes_nothing_at_an_earlier_cutoff(self):
        nvda = self.company("NVDA")
        before = {view: json.dumps(self.build(nvda, "2024-09-01T00:00:00Z", view=view), sort_keys=True) for view in ("as_reported", "latest")}
        md_before = dossier.render_markdown(self.build(nvda, "2024-09-01T00:00:00Z"))
        oid = self.amendment(nvda)
        for view in ("as_reported", "latest"):
            self.assertEqual(json.dumps(self.build(nvda, "2024-09-01T00:00:00Z", view=view), sort_keys=True), before[view])
        self.assertEqual(dossier.render_markdown(self.build(nvda, "2024-09-01T00:00:00Z")), md_before)
        later = self.build(nvda, "2025-01-01T00:00:00Z", view="latest")
        fy = next(c for c in later["history"]["annual"]["revenue"] if c["period"]["end"] == "2024-01-28")
        self.assertEqual(fy["observation_ids"], [oid])
        self.assertTrue(fy["revisions"])

    def test_the_strict_policy_admits_no_date_only_filing(self):
        nvda = self.company("NVDA")
        d = self.build(nvda, NOW, "observed", version=STRICT)
        self.assertEqual(d["coverage"]["eligible_observations"], 0)
        self.assertIn("never eligible", d["coverage"]["policy_note"])
        self.assertEqual(d["supported_changes"], [])

    def test_observed_mode_needs_the_download_before_the_cutoff(self):
        nvda = self.company("NVDA")
        self.assertEqual(self.build(nvda, "2025-06-01T00:00:00Z", "observed")["coverage"]["eligible_observations"], 0)
        self.assertGreater(self.build(nvda, "2025-06-01T00:00:00Z", "public")["coverage"]["eligible_observations"], 0)


RELEASE = """<html><body><h1>Acme Reports Third Quarter 2024 Results</h1><p>{body}</p><p>GAAP</p><p>Amounts in millions</p><table>
<tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td></tr></table></body></html>"""


class SearchTests(Case):
    def setUp(self):
        super().setUp()
        self.acme = self.store.upsert_security("ACME", "Acme Corp")

    def add(self, body, published, name="r.htm", security=None):
        return self.service.ingest((security or self.acme)["id"], RELEASE.format(body=body).encode(), name, "https://example.com/" + name,
                                   published_at=published, retrieved_at=published)

    def run_search(self, query, cutoff, **kw):
        return search.search(self.store, self.service.archive, query, policy(cutoff, "observed"), **kw)

    def test_future_sources_are_excluded_before_ranking_and_do_not_move_scores(self):
        self.add("Widget demand grew in Europe while gadget demand fell.", "2024-10-01T20:00:00Z", "a.htm")
        self.add("Gadget inventory rose.", "2024-10-02T20:00:00Z", "b.htm")
        before = self.run_search("widget demand", "2024-11-01T00:00:00Z")
        self.add("Widget widget widget demand demand: a later release mentioning widgets often.", "2025-02-01T20:00:00Z", "future.htm")
        after = self.run_search("widget demand", "2024-11-01T00:00:00Z")
        self.assertEqual(before, after)                                                      # results, scores and counts alike
        later = self.run_search("widget demand", "2025-03-01T00:00:00Z")
        self.assertEqual(later["results"][0]["filename"], "future.htm")
        self.assertNotEqual(later["results"][1]["score"], before["results"][0]["score"])  # corpus statistics include the new source only from its date

    def test_repeated_copies_count_once_and_list_every_source(self):
        self.add("Widget demand grew strongly this quarter in every region we serve.", "2024-10-01T20:00:00Z", "a.htm")
        other = self.store.upsert_security("ACM2", "Acme Holdings")
        self.add("Widget demand grew strongly this quarter in every region we serve.", "2024-10-01T21:00:00Z", "copy.htm", other)
        r = self.run_search("widget demand", "2024-11-01T00:00:00Z")
        hit = r["results"][0]
        self.assertEqual(len(hit["also_in"]), 1)
        self.assertEqual(r["coverage"]["distinct_passages"], r["coverage"]["passages"] - r["coverage"]["passages"] // 2)

    def test_filters_period_and_company(self):
        self.add("Widget demand grew.", "2024-10-01T20:00:00Z", "a.htm")
        other = self.store.upsert_security("OTHR", "Other Corp")
        self.add("Widget demand fell.", "2024-10-01T20:00:00Z", "o.htm", other)
        self.assertEqual({x["ticker"] for x in self.run_search("widget", "2024-11-01T00:00:00Z", security_ids=[other["id"]])["results"]}, {"OTHR"})
        self.assertEqual(len(self.run_search("widget", "2024-11-01T00:00:00Z", period="Q3 2024")["results"]), 2)
        none = self.run_search("widget", "2024-11-01T00:00:00Z", period="Q2 2024")
        self.assertEqual((none["results"], none["coverage"]["excluded"]), ([], {"outside_period_filter": 2}))
        with self.assertRaises(ValueError):
            self.run_search("widget", "2024-11-01T00:00:00Z", source_types=["tweets"])

    def test_a_passage_link_refuses_a_source_after_the_cutoff(self):
        doc = self.add("Widget demand grew.", "2025-02-01T20:00:00Z", "future.htm")
        with self.assertRaisesRegex(ValueError, "not eligible"):
            search.passage_context(self.store, self.service.archive, doc["id"], 0, policy("2024-11-01T00:00:00Z", "observed"))
        self.assertEqual(search.passage_context(self.store, self.service.archive, doc["id"], 0)["passage"]["index"], 0)

    def test_passages_are_deterministic_and_keep_headings_with_their_text(self):
        raw = b"<html><body><h2>Data Center</h2><p>Record quarterly Data Center revenue of $30.8 billion, up 17% from Q2 and up 112% from a year ago.</p></body></html>"
        first, second = search.passages(raw, "x.htm"), search.passages(raw, "x.htm")
        self.assertEqual(first, second)
        self.assertTrue(first[0]["text"].startswith("Data Center Record quarterly"))


class WebTests(Case):
    def setUp(self):
        super().setUp()
        from fastapi.testclient import TestClient
        from kod.workstation.web import create_app
        self.client = TestClient(create_app(self.store.root, offline=True, service=self.service, testing=True))

    def text(self, response):
        import html
        return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", response.text)))

    def test_dossier_page_exports_and_drill_downs_share_one_read_model(self):
        nvda = self.company("NVDA")
        q = {"as_of": "2024-09-01T00:00:00Z", "mode": "public", "policy": "day-end"}
        page = self.client.get(f"/company/{nvda['id']}/dossier", params=q)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Revenue, latest quarter vs year-ago quarter", self.text(page))
        exported = self.client.get(f"/company/{nvda['id']}/dossier.json", params=q).json()
        direct = self.build(nvda, "2024-09-01T00:00:00Z")
        self.assertEqual({k: v for k, v in exported.items() if k != "entry_permission"}, json.loads(json.dumps(direct)))
        self.assertIs(exported["entry_permission"], False)
        md = self.client.get(f"/company/{nvda['id']}/dossier.md", params=q).text
        self.assertEqual(md, dossier.render_markdown(direct))
        calc_id = self.change(direct, "eps_diluted_yoy")["calculation_id"]
        calc = self.client.get(f"/company/{nvda['id']}/dossier/calculation/{calc_id}", params=q)
        self.assertEqual(calc.status_code, 200)
        obs_id = direct["calculations"][calc_id]["inputs"][0]["id"]
        self.assertIn(f"/observation/{obs_id}", calc.text)
        obs = self.client.get(f"/observation/{obs_id}", params=q)
        self.assertIn("the preserved response holds this value at this pointer", self.text(obs))
        self.assertEqual(self.client.get(f"/company/{nvda['id']}/dossier/calculation/calc_missing", params=q).status_code, 404)
        self.assertEqual(self.client.get(f"/company/{nvda['id']}/dossier", params={"as_of": "last week"}).status_code, 400)
        self.assertEqual(self.client.get(f"/company/{nvda['id']}/dossier", params={"mode": "psychic"}).status_code, 400)

    def test_an_observation_after_the_cutoff_is_not_shown_for_that_cutoff(self):
        nvda = self.company("NVDA")
        late = next(o for o in financials.FinancialRepository(self.store).all_for(nvda["id"], "revenue") if o.filed and o.filed > "2025-01-01")
        self.assertEqual(self.client.get(f"/observation/{late.id}", params={"as_of": "2024-09-01T00:00:00Z", "mode": "public"}).status_code, 404)
        self.assertEqual(self.client.get(f"/observation/{late.id}").status_code, 200)

    def test_search_page_escapes_source_text(self):
        acme = self.store.upsert_security("ACME", "Acme Corp")
        self.service.ingest(acme["id"], RELEASE.format(body="Widget &lt;script&gt;alert(1)&lt;/script&gt; demand grew.").encode(), "r.htm",
                            "https://example.com/r.htm", published_at="2024-10-01T20:00:00Z", retrieved_at="2024-10-01T20:00:00Z")
        page = self.client.get("/search", params={"q": "widget", "as_of": "2024-11-01T00:00:00Z"})
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("<script>alert(1)</script>", page.text)
        self.assertIn("<mark>Widget</mark>", page.text)
        self.assertEqual(self.client.get("/search", params={"q": "x" * 500}).status_code, 200)        # truncated to the limit, not an error page


if __name__ == "__main__":
    unittest.main()
