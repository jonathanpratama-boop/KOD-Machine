"""Gate F: structured thesis conditions (typed expression trees, three-valued evaluation, traces), the assumption -> scenario -> review path, and decision
packets that are frozen, exportable and reproducible."""

import gzip
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

from kod.workstation import decisions, financials, scenarios, thesis
from kod.workstation.domain import canonical, identity
from kod.workstation.policy import DAY_END, AsOfPolicy
from kod.workstation.services import ResearchService
from kod.workstation.store import Store

ROOT = Path(__file__).resolve().parents[1]
CF = ROOT / "examples" / "companyfacts"
SOURCES = {(s["ticker"], s["kind"]): s for s in json.loads((CF / "SOURCES.json").read_text())}
TREAT = {
    "stock_compensation": "expensed_in_margin",
    "leases": "operating_cost_in_margin",
    "convertibles": "none_outstanding",
    "noncontrolling_interests": "none",
    "tax_losses": "none_material",
}
ASSUMPTIONS = {
    "horizon_years": 5,
    "base": {"revenue": "215938000000", "fiscal_year_end": "2026-01-25"},
    "currency": "USD",
    "valuation_date": "2026-10-23",
    "revenue_growth": ["0.4", "0.25", "0.15", "0.1", "0.08"],
    "operating_margin": "0.60",
    "cash_tax_rate": "0.15",
    "depreciation_rate": "0.015",
    "capex_rate": "0.03",
    "nwc_rate": "0.15",
    "discount_rate": "0.10",
    "terminal_growth": "0.03",
    "terminal_roic": "0.30",
    "treatments": TREAT,
    "bridge": {
        "cash": "11000000000",
        "debt": "8500000000",
        "other_senior_claims": "0",
        "as_of": "2026-07-26",
    },
    "shares": {"count": "24300000000", "as_of": "2026-07-26", "basis": "test proxy"},
}
PCT = {"kind": "constant", "value": "20", "unit": "percent"}


def const(value, unit="percent", currency=None):
    return {
        "kind": "constant",
        "value": value,
        "unit": unit,
        **({"currency": currency} if currency else {}),
    }


def fake_dossier(changes):
    return {
        "changes": [
            {
                "key": k,
                "label": k,
                "measure": "percent growth",
                "periods": "",
                "status": "ok" if v is not None else "missing",
                "value": v,
                "unit": "percent",
                "calculation_id": "calc_" + k,
                "reasons": [] if v is not None else ["no data"],
            }
            for k, v in changes.items()
        ],
        "calculations": {},
        "history": {"quarterly": {}, "annual": {}, "instant": {}},
        "scenarios": [],
        "observations": {},
        "policy": {
            "cutoff": "2026-01-01T00:00:00Z",
            "mode": "observed",
            "policy_version": "KOD-ASOF-v1-day-end",
        },
        "view": "as_reported",
    }


class ExpressionTests(unittest.TestCase):
    def test_only_the_typed_schema_is_accepted(self):
        bad = [
            {"op": "__import__", "left": {}, "right": {}},
            {"op": "<", "left": {"kind": "python", "code": "1"}, "right": PCT},
            {"op": "<", "left": {"kind": "change", "key": "revenue_yoy", "extra": 1}, "right": PCT},
            {"op": "<", "left": {"kind": "change", "key": "not_a_change"}, "right": PCT},
            {"op": "<", "left": const("1"), "right": const("2")},
            {
                "op": "<",
                "left": {"kind": "change", "key": "revenue_yoy"},
                "right": {"kind": "constant", "value": 0.2, "unit": "percent"},
            },
            {
                "op": "<",
                "left": {"kind": "change", "key": "revenue_yoy"},
                "right": const("5", "currency"),
            },
            {
                "op": "<",
                "left": {"kind": "change", "key": "revenue_yoy"},
                "right": const("5", "percent", "USD"),
            },
            {"op": "all", "args": []},
            {
                "op": "any",
                "args": [
                    {"op": "<", "left": {"kind": "change", "key": "revenue_yoy"}, "right": PCT}
                ]
                * 9,
            },
            {
                "op": "not",
                "arg": {
                    "op": "not",
                    "arg": {
                        "op": "not",
                        "arg": {
                            "op": "not",
                            "arg": {
                                "op": "not",
                                "arg": {
                                    "op": "<",
                                    "left": {"kind": "change", "key": "revenue_yoy"},
                                    "right": PCT,
                                },
                            },
                        },
                    },
                },
            },
        ]
        for e in bad:
            with self.subTest(e=json.dumps(e)[:80]), self.assertRaises(thesis.ConditionError):
                thesis.validate_expression(e)
        with self.assertRaises(thesis.ConditionError):
            thesis.parse_conditions(
                "__import__('os').system('true')"
            )  # text is parsed as JSON data, never executed
        with self.assertRaises(thesis.ConditionError):
            thesis.validate_conditions(
                [thesis.comparison({"kind": "change", "key": "revenue_yoy"}, "<", PCT, "a", "x")]
                * 2
            )  # duplicate ids

    def test_three_valued_logic_never_turns_a_gap_into_false(self):
        d = fake_dossier({"revenue_yoy": "10", "net_income_yoy": None})
        lt = lambda k: {"op": "<", "left": {"kind": "change", "key": k}, "right": PCT}  # noqa: E731
        cases = [
            (lt("revenue_yoy"), "triggered"),
            (lt("net_income_yoy"), "unresolved"),
            ({"op": "all", "args": [lt("revenue_yoy"), lt("net_income_yoy")]}, "unresolved"),
            ({"op": "any", "args": [lt("revenue_yoy"), lt("net_income_yoy")]}, "triggered"),
            (
                {
                    "op": "all",
                    "args": [{"op": "not", "arg": lt("revenue_yoy")}, lt("net_income_yoy")],
                },
                "not_triggered",
            ),
            ({"op": "not", "arg": lt("net_income_yoy")}, "unresolved"),
        ]
        for expression, expected in cases:
            v = {
                "id": "thv",
                "thesis_id": "t",
                "version": 1,
                "conditions": [{"id": "c", "label": "x", "expression": expression}],
            }
            with self.subTest(expression=thesis.describe(expression)):
                self.assertEqual(thesis.evaluate(v, d)[0]["status"], expected)

    def test_units_and_currencies_are_never_converted(self):
        d = fake_dossier({"revenue_yoy": "10"})
        d["scenarios"] = [
            {
                "scenario": "base",
                "name": "default",
                "version": 1,
                "version_id": "asmv",
                "per_share": "100",
                "enterprise_value": "1",
                "currency": "EUR",
                "status": "ok",
            }
        ]
        cases = [
            (
                {
                    "op": "<",
                    "left": {"kind": "change", "key": "revenue_yoy"},
                    "right": const("10", "percentage points"),
                },
                "units differ",
            ),
            (
                {
                    "op": "<",
                    "left": {
                        "kind": "scenario",
                        "scenario": "base",
                        "name": "default",
                        "measure": "per_share",
                    },
                    "right": const("150", "currency/share", "USD"),
                },
                "currencies differ",
            ),
        ]
        for expression, reason in cases:
            v = {
                "id": "thv",
                "thesis_id": "t",
                "version": 1,
                "conditions": [{"id": "c", "label": "x", "expression": expression}],
            }
            e = thesis.evaluate(v, d)[0]
            self.assertEqual(e["status"], "unresolved")
            self.assertIn(reason, e["trace"][0]["reason"])


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.now = ["2026-10-23T08:00:00Z"]
        self.store = Store(Path(tmp.name) / "ws")
        self.service = ResearchService(self.store, clock=lambda: self.now[0])
        self.sec = self.store.upsert_security("NVDA", "NVIDIA Corporation", cik="1045810")
        f, s = SOURCES[("NVDA", "companyfacts")], SOURCES[("NVDA", "submissions")]
        self.service.import_companyfacts(
            self.sec["id"],
            gzip.decompress((CF / f["fixture"]).read_bytes()),
            f["url"],
            observed_at=f["observed_at"],
            submissions=gzip.decompress((CF / s["fixture"]).read_bytes()),
            submissions_url=s["url"],
        )

    def at(self, moment):
        self.now[0] = moment
        return AsOfPolicy.parse(moment, "observed", DAY_END)

    def scenario_thesis(self, threshold="100"):
        return decisions.save_thesis(
            self.service,
            self.sec["id"],
            "AI capex cycle",
            "Demand stays strong.",
            [
                thesis.comparison(
                    {
                        "kind": "scenario",
                        "scenario": "base",
                        "name": "default",
                        "measure": "per_share",
                    },
                    "<",
                    const(threshold, "currency/share", "USD"),
                    f"Review if the base case falls below {threshold} per share",
                    "base_value",
                ),
                thesis.comparison(
                    {"kind": "change", "key": "capex_intensity_fy"},
                    ">",
                    const("10"),
                    "Review if capex intensity exceeds 10%",
                    "capex",
                ),
            ],
            "initial view",
        )


class AssumptionToReviewTests(Case):
    def test_an_assumption_change_reaches_the_condition_with_the_full_dependency(self):
        scenarios.save_assumptions(
            self.service, self.sec["id"], "base", ASSUMPTIONS, "illustrative"
        )
        self.scenario_thesis()
        first = decisions.review(self.service, self.sec["id"], self.at("2026-10-23T09:00:00Z"))
        before = {e["condition_id"]: e for e in first["theses"][0]["evaluations"]}
        self.assertEqual(before["base_value"]["status"], "not_triggered")
        self.assertEqual(
            before["capex"]["status"], "unresolved"
        )  # no capex KOD maps at this cutoff: a gap, not 'false'
        self.at("2026-10-23T10:00:00Z")
        scenarios.save_assumptions(
            self.service,
            self.sec["id"],
            "base",
            {**ASSUMPTIONS, "operating_margin": "0.40"},
            "margin compression",
        )
        after = decisions.review(self.service, self.sec["id"], self.at("2026-10-23T11:00:00Z"))
        e = next(e for e in after["theses"][0]["evaluations"] if e["condition_id"] == "base_value")
        self.assertEqual(e["status"], "triggered")
        at = e["trace"][0]["left"]["sources"]["assumption_trace"]
        self.assertEqual(
            (at["version"], at["changed"]),
            (2, [{"assumption": "operating_margin", "from": "0.60", "to": "0.40"}]),
        )
        self.assertTrue(at["calculation_id"].startswith("calc_"))
        self.assertEqual(e["thesis_version"], 1)
        old = decisions.review(
            self.service,
            self.sec["id"],
            AsOfPolicy.parse("2026-10-23T09:00:00Z", "observed", DAY_END),
        )
        self.assertEqual(
            next(e for e in old["theses"][0]["evaluations"] if e["condition_id"] == "base_value")[
                "status"
            ],
            "not_triggered",
        )

    def test_a_thesis_written_after_the_cutoff_is_not_used_for_it(self):
        self.scenario_thesis()
        self.assertEqual(
            decisions.review(
                self.service,
                self.sec["id"],
                AsOfPolicy.parse("2026-10-01T00:00:00Z", "observed", DAY_END),
            )["theses"],
            [],
        )
        db = sqlite3.connect(self.store.path)
        self.addCleanup(db.close)
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE thesis_versions SET statement='changed'")


class PacketTests(Case):
    def test_a_packet_is_frozen_exportable_and_reproducible(self):
        scenarios.save_assumptions(
            self.service, self.sec["id"], "base", ASSUMPTIONS, "illustrative"
        )
        t = self.scenario_thesis()
        policy = self.at("2026-10-23T09:00:00Z")
        saved = decisions.save_packet(
            self.service,
            self.sec["id"],
            policy,
            "as_reported",
            "Keep watching?",
            "keep watching",
            "nothing triggered",
            t["id"],
            "2027-01-31",
            "next 10-Q",
            "Resolve on the FY2027 10-K revenue figure",
        )
        body = saved["packet"]
        self.assertEqual(body["decision"]["thesis_version_id"], t["id"])
        self.assertEqual(
            list(body["assumption_versions"])[0], body["dossier"]["scenarios"][0]["version_id"]
        )
        self.assertTrue(body["evidence_ids"] and body["calculation_ids"])
        self.assertIsNone(body["decision"]["hindsight_note"])
        self.assertEqual(decisions.reproduce(self.service, saved["id"])["reproduced"], True)
        md = decisions.render_markdown(decisions.packet(self.service, saved["id"]))
        self.assertIn("Keep watching?", md)
        self.assertIn("Review if the base case falls below 100 per share", md)
        # A later assumption version does not change the stored packet, and the packet still reproduces at its own cutoff.
        self.at("2026-10-23T10:00:00Z")
        scenarios.save_assumptions(
            self.service,
            self.sec["id"],
            "base",
            {**ASSUMPTIONS, "operating_margin": "0.40"},
            "margin compression",
        )
        self.assertTrue(decisions.reproduce(self.service, saved["id"])["reproduced"])
        # Evidence that becomes eligible at the packet's cutoff (recorded later, published earlier, public mode) is reported as a difference.
        public = decisions.save_packet(
            self.service,
            self.sec["id"],
            AsOfPolicy.parse("2025-01-01T00:00:00Z", "public", DAY_END),
            "as_reported",
            "Back then?",
            "reconstruction",
            "historical check",
        )
        self.assertIn(
            "recorded after its information cutoff", public["packet"]["decision"]["hindsight_note"]
        )
        p = financials.period("12 months", start="2023-01-30", end="2024-01-28")
        doc = self.store.save_document(
            self.sec["id"],
            b'{"synthetic": 1}',
            "x.json",
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
            published_at=None,
            published_basis="test",
            observed_at=self.now[0],
            role="other",
            association="user_asserted",
            provider="test",
            extraction_status="companyfacts",
            metadata={"kind": "test"},
        )
        row = {
            "id": identity("fob", "late"),
            "provider": "sec_companyfacts",
            "issuer_id": None,
            "security_id": self.sec["id"],
            "concept": "Revenues",
            "taxonomy": "us-gaap",
            "metric": "revenue",
            "metric_version": 1,
            "raw_value": "1",
            "value": "1",
            "unit": "currency",
            "scale": 1,
            "currency": "USD",
            "currency_basis": "x",
            "period_id": p.id,
            "basis": "GAAP",
            "context": "consolidated (companyfacts whole entity)",
            "dimensions_available": 0,
            "accession": "0000000000-24-000001",
            "form": "10-K/A",
            "filed": "2024-06-01",
            "amendment": 1,
            "source_document_id": doc["id"],
            "source_sha256": doc["sha256"],
            "evidence": canonical({"json_pointer": "/x"}),
            "published_at": None,
            "publication_date": "2024-06-01",
            "publication_precision": "date",
            "publication_basis": "x",
            "observed_at": self.now[0],
            "recorded_at": self.now[0],
            "parser_version": "x",
            "mapping_version": "x",
            "flags": "[]",
        }
        self.store.record_observations([p], [row])
        check = decisions.reproduce(self.service, public["id"])
        self.assertFalse(check["reproduced"])
        self.assertIn("dossier", check["differences"])

    def test_a_stored_packet_cannot_be_changed_and_tampering_is_detected(self):
        saved = decisions.save_packet(
            self.service,
            self.sec["id"],
            self.at("2026-10-23T09:00:00Z"),
            "as_reported",
            "Q?",
            "watch",
            "why",
        )
        db = sqlite3.connect(self.store.path)
        self.addCleanup(db.close)
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE decision_packets SET choice='buy'")
        with db:
            db.execute("DROP TRIGGER decision_packets_no_update")
            db.execute(
                "UPDATE decision_packets SET packet=replace(packet, '\"watch\"', '\"buy\"') WHERE id=?",
                (saved["id"],),
            )
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            decisions.packet(self.service, saved["id"])

    def test_inputs_are_bounded(self):
        policy = self.at("2026-10-23T09:00:00Z")
        for args, message in (
            (("", "watch", "why"), "question"),
            (("Q?", "", "why"), "choice"),
            (("Q?", "watch", ""), "rationale"),
        ):
            with self.assertRaisesRegex(ValueError, message):
                decisions.save_packet(self.service, self.sec["id"], policy, "as_reported", *args)
        with self.assertRaisesRegex(ValueError, "not current"):
            decisions.save_packet(
                self.service,
                self.sec["id"],
                policy,
                "as_reported",
                "Q?",
                "watch",
                "why",
                "thv_unknown",
            )
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            decisions.save_packet(
                self.service,
                self.sec["id"],
                policy,
                "as_reported",
                "Q?",
                "watch",
                "why",
                None,
                "next week",
            )


class WebTests(Case):
    def setUp(self):
        super().setUp()
        from fastapi.testclient import TestClient
        from kod.workstation.web import create_app

        self.now[0] = "2026-10-23T12:00:00Z"
        self.client = TestClient(
            create_app(self.store.root, offline=True, service=self.service, testing=True)
        )

    def token(self):
        return re.search(r'name="csrf" value="([^"]+)"', self.client.get("/").text).group(1)

    def test_thesis_builder_review_and_decision_pages(self):
        n = self.sec["id"]
        tree = [
            {
                "id": "tree",
                "label": "Review if net income shrank",
                "expression": {
                    "op": "not",
                    "arg": {
                        "op": ">",
                        "left": {"kind": "change", "key": "net_income_yoy"},
                        "right": const("0"),
                    },
                },
            }
        ]
        saved = self.client.post(
            f"/company/{n}/thesis",
            data={
                "csrf": self.token(),
                "title": "AI cycle",
                "statement": "Demand <b>holds</b>.",
                "rationale": "test",
                "c1_label": "Review if quarterly operating margin < 50%",
                "c1_left": "margin:operating_margin_latest_quarter",
                "c1_op": "<",
                "c1_right": "constant",
                "c1_value": "50",
                "c1_unit": "percent",
                "advanced_conditions": json.dumps(tree),
            },
            follow_redirects=True,
        )
        self.assertIn("Saved", saved.text)
        self.assertNotIn("Demand <b>holds</b>", saved.text)
        self.assertIn(
            "not triggered · Review if quarterly operating margin",
            re.sub(r"<[^>]+>", " ", saved.text).replace("  ", " "),
        )
        recorded = self.client.post(
            f"/company/{n}/thesis/review",
            data={
                "csrf": self.token(),
                "as_of": "2026-10-23T12:00:00Z",
                "mode": "observed",
                "policy": "day-end",
                "view": "as_reported",
            },
            follow_redirects=True,
        )
        self.assertEqual(recorded.status_code, 200)
        self.assertIn("Recorded 2 condition evaluations", recorded.text)
        rejected = self.client.post(
            f"/company/{n}/thesis",
            data={
                "csrf": self.token(),
                "title": "x",
                "statement": "x",
                "rationale": "x",
                "advanced_conditions": '[{"id": "a", "label": "b", "expression": {"op": "eval", "left": 1}}]',
            },
            follow_redirects=True,
        )
        self.assertIn("unknown operator", rejected.text)
        dossier = self.client.get(f"/company/{n}/dossier")
        version_id = re.search(
            r'name="thesis_version_id"><option value="">none</option><option value="([^"]+)"',
            dossier.text,
        ).group(1)
        packet = self.client.post(
            f"/company/{n}/decisions",
            data={
                "csrf": self.token(),
                "as_of": "2026-10-23T12:00:00Z",
                "mode": "observed",
                "policy": "day-end",
                "view": "as_reported",
                "question": "Keep watching?",
                "choice": "watch",
                "rationale": "<script>x</script>",
                "thesis_version_id": version_id,
            },
            follow_redirects=True,
        )
        self.assertEqual(packet.status_code, 200)
        self.assertNotIn("<script>x</script>", packet.text)
        pid = re.search(r"/packet/(pkt_[0-9a-f]+)\.md", packet.text).group(1)
        self.assertEqual(
            self.client.get(f"/packet/{pid}.json").json()["packet"]["decision"]["rationale"],
            "<script>x</script>",
        )
        self.assertIn("# Decision packet: NVDA", self.client.get(f"/packet/{pid}.md").text)
        self.assertIn(
            "Reproduced", self.client.get(f"/packet/{pid}", params={"reproduce": "1"}).text
        )
        self.assertEqual(self.client.get("/packet/pkt_unknown").status_code, 404)


if __name__ == "__main__":
    unittest.main()
