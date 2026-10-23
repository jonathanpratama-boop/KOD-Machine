"""Reproduced findings of the independent Gate G review (week-based quarters, comparison notes, refresh, prices, reverse valuation, provenance)."""

from decimal import Decimal
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from kod.workstation import decisions, dossier, financials, model, scenarios, thesis
from kod.workstation.policy import DAY_END, AsOfPolicy
from kod.workstation.services import ResearchService
from kod.workstation.store import Store

ROOT = Path(__file__).resolve().parents[1]
CF = ROOT / "examples" / "companyfacts"
SOURCES = {(s["ticker"], s["kind"]): s for s in json.loads((CF / "SOURCES.json").read_text())}
CIKS = {"AAPL": "320193", "COST": "909832", "TXN": "97476"}
NOW = "2026-10-23T12:00:00Z"
TREAT = {"stock_compensation": "expensed_in_margin", "leases": "operating_cost_in_margin", "convertibles": "none_outstanding",
         "noncontrolling_interests": "none", "tax_losses": "none_material"}
TXN_CASE = {"horizon_years": 5, "base": {"revenue": "15641000000", "fiscal_year_end": "2024-12-31"}, "currency": "USD", "valuation_date": "2025-03-01",
            "revenue_growth": "0.05", "operating_margin": "0.40", "cash_tax_rate": "0.13", "depreciation_rate": "0.08", "capex_rate": "0.10", "nwc_rate": "0.10",
            "discount_rate": "0.09", "terminal_growth": "0.03", "terminal_roic": "0.20", "treatments": TREAT,
            "bridge": {"cash": "3200000000", "debt": "12846000000", "other_senior_claims": "0", "as_of": "2024-12-31"},
            "shares": {"count": "919000000", "as_of": "2024-12-31", "basis": "test"}}


def policy(cutoff, mode="public"):
    return AsOfPolicy.parse(cutoff, mode, DAY_END)


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / "ws")
        self.now = [NOW]
        self.service = ResearchService(self.store, clock=lambda: self.now[0])

    def company(self, ticker):
        sec = self.store.upsert_security(ticker, ticker, cik=CIKS[ticker], now=self.now[0])
        facts, subs = SOURCES[(ticker, "companyfacts")], SOURCES[(ticker, "submissions")]
        self.service.import_companyfacts(sec["id"], gzip.decompress((CF / facts["fixture"]).read_bytes()), facts["url"], observed_at=facts["observed_at"],
                                         submissions=gzip.decompress((CF / subs["fixture"]).read_bytes()), submissions_url=subs["url"])
        return sec

    @staticmethod
    def change(d, key):
        return next(c for c in d["changes"] if c["key"] == key)

    @staticmethod
    def cells(d, group, metric, end):
        return [c for c in d["history"][group].get(metric, []) if c["period"]["end"] == end]


class WeekBasedQuarterTests(Case):
    def test_a_reported_sixteen_week_fourth_quarter_is_a_quarter_with_its_same_filing_comparative(self):
        # Costco's 10-K for fiscal 2010 tags the 16-week fourth quarter (and the year-ago one) directly.
        d = dossier.build(self.service, self.company("COST")["id"], policy("2010-11-15T00:00:00Z"))
        self.assertEqual(d["latest_quarter_end"], "2010-08-29")
        [q4] = self.cells(d, "quarterly", "revenue", "2010-08-29")
        self.assertEqual((q4["status"], q4["value"]), ("reported", "24125000000"))
        yoy = self.change(d, "revenue_yoy")
        self.assertEqual(yoy["status"], "ok")
        self.assertAlmostEqual(float(yoy["value"]), (24125 / 22378 - 1) * 100, places=6)
        self.assertIn("presented in the same filing (0001193125-10-230379)", yoy["comparison_basis"])

    def test_a_quarter_is_never_listed_twice_for_one_end_date(self):
        d = dossier.build(self.service, self.company("COST")["id"], policy("2010-06-15T00:00:00Z"))
        self.assertEqual(len(self.cells(d, "quarterly", "revenue", "2010-05-09")), 1)

    def test_quarter_on_quarter_growth_across_unequal_lengths_is_withheld_and_notes_follow_the_change(self):
        cost = self.company("COST")
        d = dossier.build(self.service, cost["id"], policy("2024-11-15T00:00:00Z"))
        qoq = self.change(d, "revenue_qoq")
        self.assertEqual(qoq["status"], "incompatible")                              # 16 weeks against 12: +36% would mostly be the extra weeks
        self.assertIn("112 vs 84 days", qoq["reasons"][0])
        self.assertNotIn("revenue_qoq", d["supported_changes"])
        self.assertEqual(self.change(d, "revenue_yoy")["status"], "ok")             # 16 against 17 weeks: shown, with the note
        self.now[0] = "2024-11-15T00:00:00Z"
        decisions.save_thesis(self.service, cost["id"], "T", "S", [thesis.comparison({"kind": "change", "key": "revenue_yoy"}, "<",
                                                                                     {"kind": "constant", "value": "0", "unit": "percent"}, "Review if revenue falls")], "r")
        review = decisions.review(self.service, cost["id"], policy("2024-11-16T00:00:00Z"))
        step = review["theses"][0]["evaluations"][0]["trace"][0]
        self.assertIn("112 vs 119 days", step["left"]["note"])
        stored = decisions.save_packet(self.service, cost["id"], policy("2024-11-16T00:00:00Z"), "as_reported", "Q", "C", "R")
        self.assertIn("112 vs 119 days", decisions.render_markdown(stored))

    def test_different_concepts_on_the_two_sides_are_named_and_the_basis_is_in_the_export(self):
        d = dossier.build(self.service, self.company("AAPL")["id"], policy("2019-03-08T00:00:00Z"))
        yoy = self.change(d, "revenue_yoy")
        self.assertIn("different XBRL concepts", yoy["concept_note"])
        self.assertIn("not presented in the current filing", yoy["comparison_basis"])
        text = dossier.render_markdown(d)
        self.assertIn("not presented in the current filing", text)
        self.assertIn("different XBRL concepts", text)


class Round2Tests(Case):
    """Findings of the second review round."""

    def test_reported_sixteen_and_seventeen_week_quarters_compare_with_a_note(self):
        d = dossier.build(self.service, self.company("COST")["id"], policy("2013-11-15T00:00:00Z"))
        yoy = self.change(d, "revenue_yoy")
        self.assertEqual(yoy["status"], "ok")
        self.assertAlmostEqual(float(yoy["value"]), (32487 / 32218 - 1) * 100, places=6)     # 10-K 0001445305-13-002422: 112 against 119 days
        self.assertIn("112 vs 119 days", yoy["duration_note"])
        self.assertIn("presented in the same filing (0001445305-13-002422)", yoy["comparison_basis"])

    def test_a_mis_tagged_duplicate_quarter_is_resolved_the_same_way_at_any_later_date(self):
        d = dossier.build(self.service, self.company("COST")["id"], policy("2010-10-19T00:00:00Z"))
        cells = self.cells(d, "quarterly", "revenue", "2010-05-09")
        self.assertEqual([c["period"]["start"] for c in cells], ["2010-02-15"])               # not the 91-day period one 10-Q mis-tagged

    def test_an_earlier_view_is_the_same_whether_or_not_later_filings_exist(self):
        full = json.loads(gzip.decompress((CF / "COST" / "companyfacts.json.gz").read_bytes()))
        subs = gzip.decompress((CF / "COST" / "submissions.json.gz").read_bytes())

        def view(facts, ticker, cutoff):
            sec = self.store.upsert_security(ticker, ticker, cik=CIKS["COST"], venue={"COST": "XNAS", "COSTX": "XNYS"}[ticker], now=NOW)
            if not self.store.documents(sec["id"]):
                self.service.import_companyfacts(sec["id"], json.dumps(facts).encode(), SOURCES[("COST", "companyfacts")]["url"],
                                                 observed_at=NOW, submissions=subs, submissions_url=SOURCES[("COST", "submissions")]["url"])
            d = dossier.build(self.service, sec["id"], policy(cutoff))
            cells = {g: {m: [(c["period"]["start"], c["period"]["end"], c["value"], c["status"]) for c in v] for m, v in d["history"][g].items()}
                     for g in ("quarterly", "annual")}
            return cells, [(c["key"], c["status"], c["value"], c.get("duration_note")) for c in d["changes"]]
        for cutoff in ("2010-10-20T00:00:00Z", "2011-06-11T00:00:00Z", "2012-03-17T00:00:00Z"):
            cut = json.loads(json.dumps(full))
            for concept in cut["facts"]["us-gaap"].values():
                for unit in concept["units"]:
                    concept["units"][unit] = [e for e in concept["units"][unit] if e["filed"] < cutoff[:10]]
            self.store = Store(Path(tempfile.mkdtemp()) / "a")
            self.service = ResearchService(self.store, clock=lambda: NOW)
            later = view(full, "COST", cutoff)
            only_before = view(cut, "COSTX", cutoff)
            self.assertEqual(later, only_before, cutoff)

    META = {"currency": "USD", "timezone": "America/New_York", "adjustment": "raw", "session": "regular_close", "source": "test", "feed_coverage": "one listing"}

    def test_reverting_a_price_correction_is_recorded_and_used(self):
        sec = self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"], now=NOW)
        for day, close in (("2026-10-20", "200.00"), ("2026-10-21", "210.00"), ("2026-10-22", "200.00")):
            self.now[0] = f"{day}T00:00:00Z"
            scenarios.import_price_csv(self.service, sec["id"], f"date,close\n2026-10-16,{close}\n".encode(), f"{day}.csv", self.META)
        self.assertEqual(scenarios.price_at(self.service, sec["id"], policy("2026-10-23T00:00:00Z", "observed"))["close"], "200.00")
        self.assertEqual(scenarios.price_at(self.service, sec["id"], policy("2026-10-21T12:00:00Z", "observed"))["close"], "210.00")

    def test_a_later_recorded_intraday_quote_does_not_replace_the_close(self):
        sec = self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"], now=NOW)
        self.now[0] = "2026-10-20T00:00:00Z"
        scenarios.import_price_csv(self.service, sec["id"], b"date,close\n2026-10-16,200.00\n", "c.csv", self.META)
        self.now[0] = "2026-10-21T00:00:00Z"
        scenarios.add_manual_price(self.service, sec["id"], "2026-10-16", "185.00", {**self.META, "session": "manual_quote", "source": "desk"},
                                   at="2026-10-16T18:00:00Z")
        self.assertEqual(scenarios.price_at(self.service, sec["id"], policy("2026-10-22T00:00:00Z", "observed"))["close"], "200.00")


class RefreshTests(Case):
    def client(self, body):
        import httpx
        from kod.workstation import sources
        return sources.SecClient("test@example.com", transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))

    def test_a_malformed_response_is_a_failed_job_not_a_traceback(self):
        from kod.workstation import sources
        txn = self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"])
        for body in (b'{"cik": null, "facts": {}}', b'{"cik": 97476, "facts": {"us-gaap": "x"}}'):
            with self.assertRaisesRegex(sources.SourceUnavailable, "kept as evidence but no financial observation was recorded"):
                sources.refresh_companyfacts(self.service, txn["id"], client=self.client(body))
            self.assertEqual(self.store.jobs()[0]["status"], "failed")
            self.assertFalse(financials.FinancialRepository(self.store).all_for(txn["id"]))

    def test_one_refresh_records_one_job(self):
        import httpx
        from kod.workstation import sources

        def respond(request):
            kind = "companyfacts" if "companyfacts" in request.url.path else "submissions"
            return httpx.Response(200, content=gzip.decompress((CF / "TXN" / f"{kind}.json.gz").read_bytes()))
        txn = self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"])
        sources.refresh_companyfacts(self.service, txn["id"], client=sources.SecClient("test@example.com", transport=httpx.MockTransport(respond)))
        self.assertEqual([j["status"] for j in self.store.jobs()], ["success"])


class ModelAndPriceTests(Case):
    META = {"currency": "USD", "timezone": "America/New_York", "adjustment": "raw", "session": "regular_close", "source": "test", "feed_coverage": "one listing"}

    def test_a_price_correction_for_the_same_day_is_used_once_recorded(self):
        sec = self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"])
        for day, close in (("2026-10-13", "199.50"), ("2026-10-14", "210.00"), ("2026-10-15", "207.00")):   # in the review these lost by id order
            self.now[0] = "2026-10-20T00:00:00Z"
            scenarios.import_price_csv(self.service, sec["id"], f"date,close\n{day},200.00\n".encode(), f"a{day}.csv", self.META)
            self.now[0] = "2026-10-23T00:00:00Z"
            scenarios.import_price_csv(self.service, sec["id"], f"date,close\n{day},{close}\n".encode(), f"b{day}.csv", self.META)
            self.assertEqual(scenarios.price_at(self.service, sec["id"], policy("2026-10-25T00:00:00Z", "observed"))["close"], close)
            self.assertEqual(scenarios.price_at(self.service, sec["id"], policy("2026-10-21T00:00:00Z", "observed"))["close"], "200.00")  # not yet recorded

    def test_reverse_valuation_reports_solved_only_within_its_tolerance(self):
        a = model.validate({**TXN_CASE, "terminal_growth": "0.0199"})
        r = model.reverse(a, Decimal("57777"), "discount_rate", bracket=(Decimal("0.0200"), Decimal("0.021")))
        if r["status"] == "solved":
            self.assertLessEqual(abs(Decimal(r["residual"])), Decimal("0.0001"))
        else:
            self.assertEqual(r["status"], "not_converged")
            self.assertIn("tolerance", r["reasons"][0])
        ok = model.reverse(model.validate(TXN_CASE), Decimal("100"), "operating_margin")
        self.assertEqual(ok["status"], "solved")
        self.assertLessEqual(abs(Decimal(ok["residual"])), Decimal("0.0001"))

    def test_every_history_suggestion_cites_its_observations(self):
        d = dossier.build(self.service, self.company("TXN")["id"], policy("2025-03-01T00:00:00Z"))
        suggested = model.suggest_from_history(d)["values"]
        self.assertTrue(suggested)
        for name, item in suggested.items():
            self.assertTrue(item.get("observation_ids"), name)


class ObservedNameTests(Case):
    def test_a_later_rename_does_not_reach_an_earlier_observed_view(self):
        self.now[0] = "2026-10-23T11:00:00Z"
        txn = self.company("TXN")
        cutoff = policy("2026-10-23T12:00:00Z", "observed")
        before = json.dumps(dossier.build(self.service, txn["id"], cutoff), sort_keys=True)
        self.store.upsert_security("TXN", "TI (renamed later)", cik=CIKS["TXN"], now="2026-10-24T00:00:00Z")
        after = dossier.build(self.service, txn["id"], cutoff)
        self.assertEqual(json.dumps(after, sort_keys=True), before)
        self.assertNotIn("renamed later", dossier.render_markdown(after))
        self.assertEqual(after["company"]["name"], "TXN")                      # the name recorded with the identity held by the cutoff


if __name__ == "__main__":
    unittest.main()
