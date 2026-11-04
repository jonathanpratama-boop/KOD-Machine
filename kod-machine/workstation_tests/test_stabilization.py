"""Regression tests for the stabilization review of 2026-10-30 (handoff: Ace's findings 2 and 4).

2. A valuation's explanation is read at its own cutoff: a business classification imported later never changes an
   earlier calculation, and a frozen decision packet still reproduces after the import.
4. Same-second price corrections are ordered by their recording sequence, not by their hash ids.
"""

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from kod.workstation import decisions, scenarios, migrations
from kod.workstation.policy import DAY_END, AsOfPolicy
from kod.workstation.services import ResearchService
from kod.workstation.store import Store

TREAT = {
    "stock_compensation": "expensed_in_margin",
    "leases": "operating_cost_in_margin",
    "convertibles": "none_outstanding",
    "noncontrolling_interests": "none",
    "tax_losses": "none_material",
}
CASE = {
    "horizon_years": 2,
    "base": {"revenue": "100", "fiscal_year_end": "2024-12-31"},
    "currency": "USD",
    "valuation_date": "2025-03-01",
    "revenue_growth": "0.10",
    "operating_margin": "0.20",
    "cash_tax_rate": "0.25",
    "depreciation_rate": "0.05",
    "capex_rate": "0.06",
    "nwc_rate": "0.10",
    "discount_rate": "0.10",
    "terminal_growth": "0.02",
    "terminal_roic": "0.10",
    "bridge": {"cash": "10", "debt": "30", "other_senior_claims": "0", "as_of": "2024-12-31"},
    "shares": {
        "count": "10",
        "as_of": "2025-02-15",
        "basis": "diluted shares outstanding, analyst-reviewed",
    },
    "treatments": TREAT,
}
META = {
    "currency": "USD",
    "timezone": "America/New_York",
    "adjustment": "raw",
    "session": "regular_close",
    "source": "test CSV",
    "feed_coverage": "one listing",
}


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.now = ["2024-12-01T12:00:00Z"]
        self.store = Store(Path(tmp.name) / "ws")
        self.service = ResearchService(self.store, clock=lambda: self.now[0])
        self.sec = self.store.upsert_security("ACME", "Acme Corp")

    def submissions(self, sic: str, description: str):
        raw = json.dumps(
            {"cik": "1", "sic": sic, "sicDescription": description, "filings": {"recent": {}}}
        ).encode()
        return self.store.save_document(
            self.sec["id"],
            raw,
            "submissions.json",
            "https://data.sec.gov/submissions/CIK0000000001.json",
            published_at=None,
            published_basis="API snapshot of the filing list",
            observed_at=self.now[0],
            role="metadata",
            association="verified_from_filing_metadata",
            provider="sec",
            external_id="submissions:1",
            extraction_status="metadata",
            metadata={
                "kind": "SEC submissions response",
                "cik": "1",
                "sic": sic,
                "sic_description": description,
            },
        )


class ClassificationAtTheCutoff(Case):
    def test_a_later_snapshot_does_not_change_an_earlier_valuation_or_its_packet(self):
        self.submissions("3571", "Electronic computers")  # held from 2024-12-01
        self.now[0] = "2024-12-02T12:00:00Z"
        v = scenarios.save_assumptions(
            self.service, self.sec["id"], "base", CASE, "an operating company"
        )
        first = scenarios.run_version(self.service, v["id"])
        self.assertEqual(first.valuation.status, "ok")
        self.now[0] = "2024-12-03T12:00:00Z"
        policy = AsOfPolicy.parse("2024-12-03T12:00:00Z", "observed", DAY_END)
        saved = decisions.save_packet(
            self.service,
            self.sec["id"],
            policy,
            "as_reported",
            "Keep watching?",
            "keep",
            "the model applies",
        )
        self.assertTrue(saved["packet"]["calculation_ids"])

        self.now[0] = "2024-12-10T12:00:00Z"
        self.submissions(
            "6022", "State commercial banks"
        )  # a later snapshot: the model would not apply
        again = scenarios.run_version(self.service, v["id"])
        self.assertEqual(again.valuation.status, "ok")  # read at the version's own time
        self.assertEqual(
            again.calculation_id, first.calculation_id
        )  # the same calculation, recorded once
        later = AsOfPolicy.parse("2024-12-11T00:00:00Z", "observed", DAY_END)
        self.assertIs(
            scenarios.business_type(self.service, self.sec["id"], later)["supported"], False
        )  # known at a later cutoff
        self.assertTrue(decisions.reproduce(self.service, saved["id"])["reproduced"])

    def test_the_selector_follows_the_policy(self):
        self.submissions("3571", "Electronic computers")
        self.now[0] = "2024-12-05T12:00:00Z"
        self.submissions("6022", "State commercial banks")
        observed_early = AsOfPolicy.parse("2024-12-02T00:00:00Z", "observed", DAY_END)
        observed_late = AsOfPolicy.parse("2024-12-06T00:00:00Z", "observed", DAY_END)
        public = AsOfPolicy.parse("2024-12-06T00:00:00Z", "public", DAY_END)
        self.assertEqual(
            self.service.submissions_at(self.sec["id"], observed_early)[0]["sic"], "3571"
        )
        self.assertEqual(
            self.service.submissions_at(self.sec["id"], observed_late)[0]["sic"], "6022"
        )
        self.assertEqual(
            self.service.submissions_at(self.sec["id"], public)[0]["sic"], "3571"
        )  # the earliest preserved
        self.assertEqual(
            self.service.submissions_at(
                self.sec["id"], AsOfPolicy.parse("2024-11-01T00:00:00Z", "observed", DAY_END)
            ),
            (None, None),
        )
        self.assertEqual(self.service.latest_submissions(self.sec["id"])["sic"], "6022")


class PriceRevisionOrder(Case):
    def test_same_second_corrections_are_ordered_by_recording(self):
        sid = self.sec["id"]
        policy = AsOfPolicy.parse("2024-12-02T00:00:00Z", "observed", DAY_END)
        scenarios.add_manual_price(self.service, sid, "2024-11-29", "100", META)
        scenarios.add_manual_price(
            self.service, sid, "2024-11-29", "101", META
        )  # the same second on the clock
        self.assertEqual(scenarios.price_at(self.service, sid, policy)["close"], "101")
        for close in range(102, 110):
            scenarios.add_manual_price(self.service, sid, "2024-11-29", str(close), META)
        self.assertEqual(scenarios.price_at(self.service, sid, policy)["close"], "109")
        self.assertEqual(scenarios.price_list(self.service, sid)[0]["close"], "109")
        scenarios.add_manual_price(
            self.service, sid, "2024-11-29", "100", META
        )  # re-recording an earlier price makes it current again
        self.assertEqual(scenarios.price_at(self.service, sid, policy)["close"], "100")
        db = sqlite3.connect(self.store.path)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], migrations.LATEST)
        seqs = [r[0] for r in db.execute("SELECT seq FROM price_observations ORDER BY seq")]
        self.assertEqual(seqs, list(range(1, len(seqs) + 1)))


if __name__ == "__main__":
    unittest.main()
