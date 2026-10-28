"""Gate E: the transparent driver model, versioned assumptions, dated prices, sensitivities and the conditional reverse valuation."""

from decimal import Decimal
import gzip
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

from kod.workstation import calculations, dossier, model, prices, scenarios
from kod.workstation.policy import DAY_END, AsOfPolicy
from kod.workstation.services import ResearchService
from kod.workstation.store import Store

ROOT = Path(__file__).resolve().parents[1]
CF = ROOT / "examples" / "companyfacts"
SOURCES = {(s["ticker"], s["kind"]): s for s in json.loads((CF / "SOURCES.json").read_text())}
TREAT = {"stock_compensation": "expensed_in_margin", "leases": "operating_cost_in_margin", "convertibles": "none_outstanding",
         "noncontrolling_interests": "none", "tax_losses": "none_material"}
CASE = {"horizon_years": 2, "base": {"revenue": "100", "fiscal_year_end": "2024-12-31"}, "currency": "USD", "valuation_date": "2025-03-01",
        "revenue_growth": "0.10", "operating_margin": "0.20", "cash_tax_rate": "0.25", "depreciation_rate": "0.05", "capex_rate": "0.06", "nwc_rate": "0.10",
        "discount_rate": "0.10", "terminal_growth": "0.02", "terminal_roic": "0.10",
        "bridge": {"cash": "10", "debt": "30", "other_senior_claims": "0", "as_of": "2024-12-31"},
        "shares": {"count": "10", "as_of": "2025-02-15", "basis": "diluted shares outstanding, analyst-reviewed"}, "treatments": TREAT}
META = {"currency": "USD", "timezone": "America/New_York", "adjustment": "raw", "session": "regular_close", "source": "test CSV", "feed_coverage": "one listing"}


def D(x):
    return Decimal(str(x))


class ModelArithmeticTests(unittest.TestCase):
    def test_an_independently_computed_case(self):
        v = model.run(model.validate(CASE))
        # Year 1: revenue 110, EBIT 22, tax 5.5, NOPAT 16.5, D&A 5.5, capex 6.6, NWC 1.0 -> FCFF 14.4
        # Year 2: revenue 121, EBIT 24.2, tax 6.05, NOPAT 18.15, D&A 6.05, capex 7.26, NWC 1.1 -> FCFF 15.84
        self.assertEqual([y["fcff"] for y in v.years], [D("14.4"), D("15.84")])
        self.assertEqual(v.terminal_value, D("18.15") * D("1.02") * (1 - D("0.02") / D("0.10")) / (D("0.10") - D("0.02")))   # 185.13
        expected_ev = D("14.4") / D("1.1") + D("15.84") / D("1.21") + D("185.13") / D("1.21")
        self.assertAlmostEqual(float(v.enterprise_value), float(expected_ev), places=9)
        self.assertAlmostEqual(float(v.equity_value), float(expected_ev + 10 - 30), places=9)
        self.assertAlmostEqual(float(v.per_share), float((expected_ev - 20) / 10), places=9)
        self.assertEqual(v.status, "ok")

    def test_signs_capex_consumes_growth_in_working_capital_consumes_and_shrinkage_releases(self):
        a = model.validate(CASE)
        more_capex = model.run(model.with_values(a, {"capex_rate": D("0.10")}))
        self.assertLess(more_capex.years[0]["fcff"], model.run(a).years[0]["fcff"])
        shrink = model.run(model.with_values(a, {"revenue_growth": D("-0.10")}))
        self.assertLess(shrink.years[0]["change_in_nwc"], 0)                              # revenue fell: working capital released
        self.assertEqual(shrink.years[0]["fcff"], shrink.years[0]["nopat"] + shrink.years[0]["depreciation"] - shrink.years[0]["capex"]
                         - shrink.years[0]["change_in_nwc"])

    def test_losses_earn_no_tax_credit_and_say_so(self):
        v = model.run(model.with_values(model.validate(CASE), {"operating_margin": D("-0.10")}))
        self.assertEqual(v.years[0]["taxes"], 0)
        self.assertTrue(any("no tax credit" in w for w in v.warnings))

    def test_terminal_reinvestment_above_nopat_is_invalid(self):
        v = model.run(model.validate({**CASE, "terminal_growth": "0.05", "terminal_roic": "0.04", "discount_rate": "0.09"}))
        self.assertEqual(v.status, "invalid")


class ValidationTests(unittest.TestCase):
    def problems(self, **changes):
        try:
            model.validate({**CASE, **changes})
        except model.AssumptionError as exc:
            return " | ".join(exc.problems)
        return ""

    def test_every_problem_is_listed_and_nothing_is_defaulted(self):
        self.assertIn("horizon_years", self.problems(horizon_years=0))
        self.assertIn("horizon_years", self.problems(horizon_years=True))
        self.assertIn("needs 2 yearly values", self.problems(revenue_growth=["0.1", "0.2", "0.3"]))
        self.assertIn("binary float", self.problems(operating_margin=0.2))
        self.assertIn("must be finite", self.problems(discount_rate="NaN"))
        self.assertIn("must exceed terminal growth", self.problems(discount_rate="0.02", terminal_growth="0.02"))
        self.assertIn("declare a treatment for leases", self.problems(treatments={**TREAT, "leases": None}))
        self.assertIn("must not be negative", self.problems(bridge={**CASE["bridge"], "debt": "-5"}))
        self.assertIn("share count must be positive", self.problems(shares={**CASE["shares"], "count": "0"}))
        self.assertIn("basis", self.problems(shares={"count": "10", "as_of": "2025-02-15"}))
        self.assertIn("outside the accepted range", self.problems(cash_tax_rate="1.5"))
        self.assertEqual(self.problems(), "")

    def test_an_incomplete_or_late_bridge_gives_enterprise_value_only(self):
        for changes, reason in (({"bridge": {"cash": "10", "as_of": "2024-12-31"}}, "incomplete"), ({"shares": {}}, "no share count"),
                                ({"bridge": {**CASE["bridge"], "as_of": "2025-06-30"}}, "after the valuation date"),
                                ({"bridge": {"cash": "10", "debt": "30", "other_senior_claims": "0"}}, "no balance-sheet date")):
            v = model.run(model.validate({**CASE, **changes}))
            self.assertEqual((v.status, v.per_share), ("ev_only", None))
            self.assertIsNotNone(v.enterprise_value)
            self.assertTrue(any(reason in w for w in v.warnings), (reason, v.warnings))

    def test_banks_and_insurers_are_outside_the_model(self):
        v = model.run(model.validate(CASE), {"supported": False, "reason": "SIC 6021 is a bank or credit institution"})
        self.assertEqual((v.status, v.enterprise_value), ("not_applicable", None))

    def test_not_modelled_treatments_stay_visible(self):
        v = model.run(model.validate({**CASE, "treatments": {**TREAT, "leases": "not_modelled"}}))
        self.assertIn("leases: not modelled", v.limitations)


class SensitivityAndReverseTests(unittest.TestCase):
    def setUp(self):
        self.a = model.validate(CASE)

    def test_the_grid_holds_everything_else_and_marks_invalid_pairs(self):
        g = model.sensitivity(self.a, ("discount_rate", [D("0.02"), D("0.10")]), ("terminal_growth", [D("0.02"), D("0.03")]))
        self.assertEqual(g["cells"][1][0]["value"], str(model.run(self.a).per_share))       # the saved pair reproduces the saved result
        self.assertEqual(g["cells"][0][0]["status"], "invalid")                               # discount rate equal to terminal growth
        self.assertIn("revenue_growth", g["held_fixed"])
        self.assertNotIn("discount_rate", g["held_fixed"])
        with self.assertRaises(ValueError):
            model.sensitivity(self.a, ("discount_rate", [D("0.1")]), ("discount_rate", [D("0.1")]))

    def test_a_solved_parameter_reproduces_the_target(self):
        r = model.reverse(self.a, D("20"), "revenue_growth")
        self.assertEqual(r["status"], "solved")
        check = model.run(model.with_values(self.a, {"revenue_growth": D(r["value"])})).per_share
        self.assertLessEqual(abs(check - 20), D("0.0001"))
        self.assertIn("required under this model and these assumptions", r["label"])

    def test_no_solution_and_non_monotonic_and_undefined_brackets_are_reported(self):
        self.assertEqual(model.reverse(self.a, D("100000"), "revenue_growth")["status"], "no_solution")
        heavy = model.validate({**CASE, "horizon_years": 5, "base": {"revenue": "1000", "fiscal_year_end": "2024-12-31"}, "capex_rate": "0.4",
                                "operating_margin": "0.2", "revenue_growth": "0.0", "terminal_growth": "0.01", "cash_tax_rate": "0.20", "depreciation_rate": "0.03",
                                "shares": {"count": "100", "as_of": "2024-12-31", "basis": "test"}, "bridge": {"cash": "0", "debt": "0", "other_senior_claims": "0",
                                                                                                              "as_of": "2024-12-31"}})
        self.assertEqual(model.reverse(heavy, D("50"), "discount_rate")["status"], "not_monotonic")
        self.assertEqual(model.reverse(self.a, D("15"), "terminal_growth", (D("0.0"), D("0.12")))["status"], "invalid_bracket")   # crosses the 10% discount rate
        self.assertEqual(model.reverse(model.validate({**CASE, "shares": {}}), D("15"), "revenue_growth")["status"], "ev_only")
        with self.assertRaises(ValueError):
            model.reverse(self.a, D("-1"), "revenue_growth")


class PriceTests(unittest.TestCase):
    def test_a_bad_row_rejects_the_whole_file_with_every_problem(self):
        bad = b"date,open,high,low,close,volume\n2024-11-20,1,2,0.5,1.5,100\n2024-11-20,1,2,0.5,1.5,\n2024-11-21,1,2,1.5,1.8,\n2024-11-22,,,,-3,\n2024-11-25,1,2,0.5,1.5,1.5\n24-11-26,1,2,0.5,1.5,\n2024-11-27,1,2,0.5,1.5,7,9\n"
        with self.assertRaises(prices.PriceError) as caught:
            prices.parse_csv(bad, META)
        text = " | ".join(caught.exception.problems)
        for expected in ("duplicate date 2024-11-20", "not coherent", "finite positive", "whole non-negative", "YYYY-MM-DD", "more fields than the header"):
            self.assertIn(expected, text)
        with self.assertRaises(prices.PriceError):
            prices.parse_csv(b"date,price\n2024-11-20,1\n", META)
        with self.assertRaises(prices.PriceError):
            prices.parse_csv(b"\xff\xfe", META)
        with self.assertRaises(prices.PriceError):
            prices.parse_csv(b"date,close\n2024-11-20,1\n", {**META, "adjustment": "unknown"})

    def test_coverage_gaps_and_missing_volume_are_reported_not_filled(self):
        p = prices.parse_csv(b"date,close,volume\n2024-11-22,10,\n2024-11-18,9,5\n", META)
        self.assertEqual([r["date"] for r in p["rows"]], ["2024-11-18", "2024-11-22"])
        self.assertEqual((p["coverage"]["weekdays_without_price"], p["coverage"]["volume_missing"]), (3, 1))
        self.assertIsNone(p["rows"][1]["volume"])

    def test_a_daily_close_counts_from_the_end_of_its_trading_day(self):
        self.assertEqual(prices.available_at("2024-11-29", "America/New_York"), "2024-11-30T05:00:00Z")
        self.assertEqual(prices.available_at("2024-07-01", "America/New_York"), "2024-07-02T04:00:00Z")
        with self.assertRaises(prices.PriceError):
            prices.manual({**META, "session": "manual_quote"}, "2024-11-29", "10")
        with self.assertRaises(prices.PriceError):
            prices.manual(META, "2024-11-29", "10", at="2024-11-29T15:00:00Z")


class ScenarioServiceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.now = ["2024-12-01T12:00:00Z"]
        self.store = Store(Path(tmp.name) / "ws")
        self.service = ResearchService(self.store, clock=lambda: self.now[0])
        self.sec = self.store.upsert_security("ACME", "Acme Corp")

    def test_versions_are_immutable_and_a_revision_makes_earlier_results_stale(self):
        v1 = scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "first view")
        r1 = scenarios.run_version(self.service, v1["id"])
        with self.assertRaisesRegex(ValueError, "identical"):
            scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "again")
        self.now[0] = "2024-12-02T12:00:00Z"
        v2 = scenarios.save_assumptions(self.service, self.sec["id"], "base", {**CASE, "operating_margin": "0.15"}, "margin pressure")
        r2 = scenarios.run_version(self.service, v2["id"])
        self.assertEqual((v2["version"], v2["supersedes"]), (2, v1["id"]))
        self.assertEqual(scenarios.changed_fields(v1["assumptions"], v2["assumptions"]), [("operating_margin", "0.20", "0.15")])
        with self.store._connection() as db:
            self.assertTrue(calculations.stale_reasons(db, r1.calculation_id))
            self.assertEqual(calculations.stale_reasons(db, r2.calculation_id), [])
            self.assertEqual(db.execute("SELECT new_id FROM calculation_supersessions WHERE old_id=?", (r1.calculation_id,)).fetchone()[0], r2.calculation_id)
        db = sqlite3.connect(self.store.path)
        self.addCleanup(db.close)
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE assumption_versions SET rationale='x'")
        with self.assertRaisesRegex(model.AssumptionError, "horizon"):
            scenarios.save_assumptions(self.service, self.sec["id"], "bull", {**CASE, "horizon_years": 99}, "bad")
        with self.assertRaisesRegex(ValueError, "rationale"):
            scenarios.save_assumptions(self.service, self.sec["id"], "bull", CASE, "")
        with self.assertRaisesRegex(ValueError, "bear, base or bull"):
            scenarios.save_assumptions(self.service, self.sec["id"], "moon", CASE, "x")

    def test_prices_are_immutable_idempotent_and_chosen_by_cutoff(self):
        csv = b"date,close\n2024-11-27,135.34\n2024-11-29,138.25\n"
        first = scenarios.import_price_csv(self.service, self.sec["id"], csv, "p.csv", META)
        self.assertEqual((first["rows"], first["added"]), (2, 2))
        self.assertEqual(scenarios.import_price_csv(self.service, self.sec["id"], csv, "p.csv", META)["added"], 0)
        public = AsOfPolicy.parse("2024-11-30T00:00:00Z", "public", DAY_END)
        self.assertEqual(scenarios.price_at(self.service, self.sec["id"], public)["observed_on"], "2024-11-27")      # the 29th's close is usable from 05:00Z on the 30th
        self.assertIsNone(scenarios.price_at(self.service, self.sec["id"], AsOfPolicy.parse("2024-11-30T00:00:00Z", "observed", DAY_END)))  # recorded later
        self.assertIsNone(scenarios.price_at(self.service, self.sec["id"], public, "split_adjusted"))
        db = sqlite3.connect(self.store.path)
        self.addCleanup(db.close)
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("DELETE FROM price_observations")

    def test_market_context_refuses_adjusted_prices_and_other_currencies(self):
        a = model.validate(CASE)
        v = model.run(a)
        row = {"id": "p", "close": "15", "observed_on": "2025-02-28", "currency": "USD", "adjustment": "raw", "source": "s", "session": "regular_close"}
        ok = scenarios.market_context({}, a, v, row)
        self.assertEqual((ok["status"], ok["market_value"]), ("ok", "150"))
        self.assertEqual(scenarios.market_context({}, a, v, {**row, "adjustment": "split_adjusted"})["status"], "not_comparable")
        self.assertEqual(scenarios.market_context({}, a, v, {**row, "currency": "EUR"})["status"], "not_comparable")
        self.assertEqual(scenarios.market_context({}, a, v, None)["status"], "no_price")

    def test_the_dossier_shows_only_scenarios_saved_by_its_cutoff(self):
        scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "first view")
        self.now[0] = "2025-01-15T12:00:00Z"
        scenarios.save_assumptions(self.service, self.sec["id"], "base", {**CASE, "operating_margin": "0.15"}, "later view")
        early = dossier.build(self.service, self.sec["id"], AsOfPolicy.parse("2024-12-31T00:00:00Z", "observed", DAY_END))
        late = dossier.build(self.service, self.sec["id"], AsOfPolicy.parse("2025-02-01T00:00:00Z", "observed", DAY_END))
        none = dossier.build(self.service, self.sec["id"], AsOfPolicy.parse("2024-11-01T00:00:00Z", "observed", DAY_END))
        self.assertEqual([s["version"] for s in early["scenarios"]], [1])
        self.assertEqual([s["version"] for s in late["scenarios"]], [2])
        self.assertEqual(none["scenarios"], [])


class ScenarioWebTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from kod.workstation.web import create_app
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / "ws")
        self.service = ResearchService(self.store, clock=lambda: "2026-10-23T12:00:00Z")
        self.client = TestClient(create_app(self.store.root, offline=True, service=self.service, testing=True))
        self.sec = self.store.upsert_security("NVDA", "NVIDIA Corporation", cik="1045810")
        f, s = SOURCES[("NVDA", "companyfacts")], SOURCES[("NVDA", "submissions")]
        self.service.import_companyfacts(self.sec["id"], gzip.decompress((CF / f["fixture"]).read_bytes()), f["url"], observed_at=f["observed_at"],
                                         submissions=gzip.decompress((CF / s["fixture"]).read_bytes()), submissions_url=s["url"])

    def token(self):
        return re.search(r'name="csrf" value="([^"]+)"', self.client.get("/").text).group(1)

    def form(self, **changes):
        data = {"csrf": self.token(), "scenario": "base", "name": "default", "horizon_years": "5", "currency": "USD", "valuation_date": "2024-11-29",
                "base_fiscal_year_end": "2024-01-28", "base_revenue": "60922", "revenue_growth": "90, 40, 25, 15, 10", "operating_margin": "55",
                "cash_tax_rate": "15", "depreciation_rate": "2", "capex_rate": "3", "nwc_rate": "15", "discount_rate": "10", "terminal_growth": "3",
                "terminal_roic": "30", "cash": "38487", "debt": "8463", "other_senior_claims": "0", "bridge_as_of": "2024-10-27", "share_count": "24774",
                "share_count_as_of": "2024-10-27", "share_count_basis": "diluted weighted-average shares, Q3 FY25, analyst-reviewed proxy",
                "rationale": "<b>illustrative</b> test assumptions", **{"treatment_" + k: v for k, v in TREAT.items()}}
        data.update(changes)
        return data

    def test_save_run_grid_what_if_reverse_and_prices_through_the_pages(self):
        page = self.client.get(f"/company/{self.sec['id']}/model?start=history")
        self.assertEqual(page.status_code, 200)
        self.assertIn('value="215938"', page.text)                                 # the latest eligible fiscal year (FY2026) suggested, in millions
        self.assertIn('name="revenue_growth" value=""', page.text)                 # no growth path is ever suggested
        saved = self.client.post(f"/company/{self.sec['id']}/model/assumptions", data=self.form(), follow_redirects=False)
        self.assertEqual(saved.status_code, 303)
        version_url = saved.headers["location"].split("?")[0]
        version_id = version_url.rsplit("/", 1)[1]
        stored = scenarios.assumption_version(self.service, version_id)["assumptions"]
        self.assertEqual((stored["revenue_growth"], stored["operating_margin"], stored["base"]["revenue"]), (["0.9", "0.4", "0.25", "0.15", "0.1"], "0.55", "60922000000"))
        page = self.client.get(version_url)
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("<b>illustrative</b>", page.text)                         # the rationale is escaped
        self.assertIn("what_if_row=", page.text)
        what_if = self.client.get(version_url, params={"what_if_row": "0.11", "what_if_column": "0.03"})
        self.assertIn("What-if, not saved", what_if.text)
        self.client.post(f"/company/{self.sec['id']}/prices/import", data={"csrf": self.token(), **META},
                         files={"file": ("nvda.csv", b"date,close\n2024-11-27,135.34\n2024-11-29,138.25\n", "text/csv")})
        solved = self.client.get(version_url, params={"as_of": "2024-11-30T06:00:00Z", "mode": "public", "solve": "operating_margin"})
        self.assertIn("required under this model and these assumptions", solved.text)
        self.assertIn("138.25", solved.text)
        bad = self.client.post(f"/company/{self.sec['id']}/model/assumptions", data=self.form(discount_rate="2", terminal_growth="3"), follow_redirects=True)
        self.assertIn("must exceed terminal growth", bad.text)
        self.assertEqual(self.client.get(f"/company/{self.sec['id']}/model/version/asmv_unknown").status_code, 404)
        rejected = self.client.post(f"/company/{self.sec['id']}/prices/import", data={"csrf": self.token(), **META},
                                    files={"file": ("bad.csv", b"date,close\n2024-11-27,-1\n", "text/csv")}, follow_redirects=True)
        self.assertIn("Nothing imported", rejected.text)
        listing = self.client.get(f"/company/{self.sec['id']}/prices")
        self.assertIn("138.25", listing.text)


if __name__ == "__main__":
    unittest.main()
