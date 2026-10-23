"""Reproduced findings of the independent Gate G review (week-based quarters, comparison notes, refresh, prices, reverse valuation, provenance)."""

from decimal import Decimal
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from kod.workstation import decisions, dossier, model, scenarios, thesis
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
        sec = self.store.upsert_security(ticker, ticker, cik=CIKS[ticker])
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


class RefreshTests(Case):
    def client(self, body):
        import httpx
        from kod.workstation import sources
        return sources.SecClient("test@example.com", transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))

    def test_a_malformed_response_is_a_failed_job_not_a_traceback(self):
        from kod.workstation import sources
        txn = self.store.upsert_security("TXN", "Texas Instruments", cik=CIKS["TXN"])
        for body in (b'{"cik": null, "facts": {}}', b'{"cik": 97476, "facts": {"us-gaap": "x"}}'):
            with self.assertRaises(sources.SourceUnavailable):
                sources.refresh_companyfacts(self.service, txn["id"], client=self.client(body))
            self.assertEqual(self.store.jobs()[0]["status"], "failed")

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
        for close in ("200.00", "199.50", "210.00", "207.00"):          # in the review, these corrections lost to 200.00 by id order
            self.now[0] = "2026-10-20T00:00:00Z"
            scenarios.import_price_csv(self.service, sec["id"], b"date,close\n2026-10-16,200.00\n", "a.csv", self.META)
            if close == "200.00":
                continue
            self.now[0] = f"2026-10-2{3 if close != '207.00' else 4}T00:00:00Z"
            scenarios.import_price_csv(self.service, sec["id"], f"date,close\n2026-10-16,{close}\n".encode(), "b.csv", self.META)
            got = scenarios.price_at(self.service, sec["id"], policy("2026-10-25T00:00:00Z", "observed"))
            self.assertEqual(got["close"], close)
            before = scenarios.price_at(self.service, sec["id"], policy("2026-10-21T00:00:00Z", "observed"))
            self.assertEqual(before["close"], "200.00")                         # not yet recorded at that cutoff

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
        txn = self.company("TXN")
        cutoff = policy("2026-10-23T12:00:00Z", "observed")
        before = json.dumps(dossier.build(self.service, txn["id"], cutoff), sort_keys=True)
        self.store.upsert_security("TXN", "TI (renamed later)", cik=CIKS["TXN"])
        after = dossier.build(self.service, txn["id"], cutoff)
        self.assertEqual(json.dumps(after, sort_keys=True), before)
        self.assertNotIn("renamed later", dossier.render_markdown(after))


if __name__ == "__main__":
    unittest.main()
