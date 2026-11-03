"""The operational view must preserve the runner's evidence and paper-only boundary."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

from kod.workstation.operations import OperationsArchive, OperationsUnavailable, SCHEMA, canonical
from kod.workstation.web import create_app


def payload():
    return {
        "run": {"id": "RUN-TEST", "status": "PARTIAL", "mode": "synthetic",
                "as_of": "2026-11-04T00:00:00Z", "generated_at": "2026-11-04T00:05:00Z"},
        "health": {"sources": [{"name": "fixture", "status": "PARTIAL", "message": "One asset missing"}]},
        "candidates": [
            {"id": "c-btc", "instrument_id": "BINANCE:BTCUSDT", "symbol": "BTCUSDT",
             "state": "RESEARCHED", "as_of": "2026-11-04T00:00:00Z",
             "detected_at": "2026-11-04T00:01:00Z", "reasons": ["Group participation increased"],
             "blockers": ["No validated entry policy"], "plan": None},
            {"id": "c-eth", "instrument_id": "BINANCE:ETHUSDT", "symbol": "ETHUSDT",
             "state": "DETECTED", "reasons": ["Relative volume"], "blockers": []},
        ],
        "market_context": {"groups": [{"id": "majors", "name": "Major coins", "member_ids": ["BTCUSDT", "ETHUSDT"],
                                        "return_1d": .025, "breadth": .5, "relative_volume": 1.2,
                                        "coverage": .5, "as_of": "2026-11-04T00:00:00Z"}]},
        "account": {"cash": "1000", "reserved_cash": "0", "free_cash": "1000", "equity": None,
                    "nav_status": "UNAVAILABLE", "currency": "USDT", "realized_pnl": "0",
                    "unrealized_pnl": None, "positions": [], "orders": [], "fills": [],
                    "profile": "PAPER_ONLY"},
        "experiments": [{"id": "GROUP_TEST", "title": "Group participation", "status": "RESEARCH_ONLY",
                         "evidence_status": "UNPROVEN", "summary": "A prospective comparison is required."}],
    }


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.path = self.runtime / "snapshot.json"
        self.client = TestClient(create_app(self.root / "workstation", offline=True,
                                           testing=True, runtime_root=self.runtime))
        self.addCleanup(self.client.close)

    def write(self, value=None):
        data = payload() if value is None else value
        self.path.write_text(json.dumps({"schema_version": SCHEMA, "payload": data,
                                       "sha256": hashlib.sha256(canonical(data)).hexdigest()},
                                      ensure_ascii=False), encoding="utf-8")
        return data

    def test_missing_runtime_is_unavailable_not_zero_or_created(self):
        for route in ("/today", "/candidates", "/market-map", "/paper-portfolio", "/experiments"):
            page = self.client.get(route)
            self.assertEqual(page.status_code, 200)
            self.assertIn("No verified runtime view", page.text)
            self.assertNotIn("No open positions recorded.", page.text)
            self.assertNotIn("No candidates recorded</", page.text)
        self.assertEqual(list(self.runtime.iterdir()), [])

    def test_complete_read_journey_preserves_bytes_and_uses_real_payload(self):
        self.write()
        before = self.path.read_bytes()
        with patch("socket.create_connection", side_effect=AssertionError("No network")), \
             patch("socket.getaddrinfo", side_effect=AssertionError("No network")):
            for route in ("/today", "/candidates", "/candidate/c-btc", "/market-map",
                          "/paper-portfolio", "/experiments"):
                page = self.client.get(route)
                self.assertEqual(page.status_code, 200, page.text)
                self.assertIn("SYNTHETIC DEMONSTRATION", page.text)
                self.assertIn("RUN-TEST", page.text)
                self.assertIn("2026-11-04 00:00:00 UTC", page.text)
                self.assertIn(hashlib.sha256(canonical(payload())).hexdigest(), page.text)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual([x.name for x in self.runtime.iterdir()], ["snapshot.json"])
        detail = self.client.get("/candidate/c-btc").text
        self.assertIn("No validated entry policy", detail)
        self.assertIn("No executable plan recorded", detail)
        self.assertIn("2.5%", self.client.get("/market-map").text)
        self.assertIn("50.0%", self.client.get("/market-map").text)
        account = self.client.get("/paper-portfolio").text
        self.assertIn("NAV", account.upper())
        self.assertIn("Not available", account)
        self.assertIn("No fills recorded.", account)

    def test_filters_and_unknown_candidate_do_not_fabricate_results(self):
        self.write()
        state = self.client.get("/candidates?state=DETECTED").text
        self.assertIn("1 shown / 2 recorded", state)
        self.assertNotIn("Group participation increased", state)
        search = self.client.get("/candidates?q=group").text
        self.assertIn("1 shown / 2 recorded", search)
        self.assertIn("Group participation increased", search)
        missing = self.client.get("/candidates?q=unknown").text
        self.assertIn("No matching candidates", missing)
        self.assertEqual(self.client.get("/candidate/missing").status_code, 404)
        self.assertIn("No matching experiments", self.client.get("/experiments?status=APPROVED").text)

    def test_hash_failure_withholds_all_operational_data(self):
        self.write()
        envelope = json.loads(self.path.read_text())
        envelope["payload"]["account"]["equity"] = "999999"
        self.path.write_text(json.dumps(envelope))
        for route in ("/today", "/candidates", "/market-map", "/paper-portfolio", "/experiments"):
            page = self.client.get(route).text
            self.assertIn("failed its integrity check", page)
            self.assertNotIn("999999", page)
            self.assertNotIn("BTCUSDT", page)

    def test_malformed_schemas_duplicate_keys_and_nonfinite_are_withheld(self):
        variants = ['{"schema_version":"one","schema_version":"two"}',
                    '{"schema_version":"KOD_RUNTIME_SNAPSHOT_V1","payload":NaN}',
                    "not json"]
        for raw in variants:
            self.path.write_text(raw)
            with self.assertRaises(OperationsUnavailable):
                OperationsArchive(self.runtime).snapshot()
        malformed = payload()
        malformed["account"]["fills"] = "unknown"
        self.write(malformed)
        with self.assertRaisesRegex(OperationsUnavailable, "account fills"):
            OperationsArchive(self.runtime).snapshot()
        malformed = payload()
        malformed["candidates"].append(deepcopy(malformed["candidates"][0]))
        self.write(malformed)
        with self.assertRaisesRegex(OperationsUnavailable, "unique"):
            OperationsArchive(self.runtime).snapshot()

    def test_source_text_is_escaped_and_environment_override_is_respected(self):
        data = payload()
        data["candidates"][0]["reasons"] = ["<script>alert('bad')</script>"]
        data["experiments"][0]["title"] = "<img src=x onerror=alert(1)>"
        self.write(data)
        candidate = self.client.get("/candidate/c-btc").text
        self.assertNotIn("<script>", candidate)
        self.assertIn("&lt;script&gt;", candidate)
        self.assertNotIn("<img src=x", self.client.get("/experiments").text)
        with patch.dict(os.environ, {"KOD_RUNTIME_ROOT": str(self.runtime)}):
            self.assertEqual(OperationsArchive().snapshot()["payload"], data)

    def test_new_snapshot_is_read_on_each_request_and_old_routes_stay_available(self):
        self.write()
        self.assertIn("RUN-TEST", self.client.get("/today").text)
        next_payload = payload()
        next_payload["run"]["id"] = "RUN-NEXT"
        self.write(next_payload)
        self.assertIn("RUN-NEXT", self.client.get("/today").text)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertIn('href="/market-map"', self.client.get("/").text)

    def test_failed_attempt_is_visible_without_overwriting_verified_snapshot(self):
        self.write()
        before = self.path.read_bytes()
        (self.runtime / "last_attempt.json").write_text(json.dumps({
            "status": "FAILED", "error": "Provider failed <script>bad</script>",
            "as_of": "2026-11-04T00:10:00Z", "recorded_at": "2026-11-04T00:10:01Z",
            "account_may_have_partial_cycle": True}))
        for route in ("/today", "/candidates", "/market-map", "/paper-portfolio", "/experiments"):
            text = self.client.get(route).text
            self.assertIn("LATEST ATTEMPT FAILED", text)
            self.assertIn("Showing the last verified snapshot", text)
            self.assertIn("RUN-TEST", text)
            self.assertIn("part of the interrupted cycle", text)
            self.assertNotIn("<script>", text)
        self.assertEqual(self.path.read_bytes(), before)
        (self.runtime / "last_attempt.json").write_text("broken json")
        self.assertIn("LATEST ATTEMPT UNREADABLE", self.client.get("/today").text)

    def test_actual_runtime_demo_renders_every_operational_route(self):
        repository = Path(__file__).resolve().parents[2]
        subprocess.run([sys.executable, "-m", "idxsig.runtime", "--root", str(self.runtime), "demo"],
                       cwd=repository / "idx-signals", check=True, capture_output=True, text=True)
        snapshot = OperationsArchive(self.runtime).snapshot()
        before = self.path.read_bytes()
        identifier = snapshot["payload"]["candidates"][0]["id"]
        for route in ("/today", "/candidates", "/candidate/" + identifier,
                      "/market-map", "/paper-portfolio", "/experiments"):
            page = self.client.get(route)
            self.assertEqual(page.status_code, 200, page.text)
            self.assertIn("SYNTHETIC DEMONSTRATION", page.text)
            self.assertNotIn("No verified runtime view", page.text)
            self.assertIn(snapshot["sha256"], page.text)
        self.assertNotIn("No fills recorded.", self.client.get("/paper-portfolio").text)
        self.assertEqual(self.path.read_bytes(), before)

    def test_assessment_display_separates_observation_and_recorded_times(self):
        value = payload()
        value["candidates"][0]["assessment"] = {
            "version": 2, "owner": "analyst", "as_of": "2026-11-04T00:00:00Z",
            "recorded_at": "2026-11-04T00:02:00Z", "reason": "Corrected <script>reason</script>",
            "mechanism": "Hypothesis", "expires_at": "2026-11-05T00:00:00Z", "recheck_at": None,
            "evidence": [{"statement": "Observed group participation", "source": "retained://source",
                          "available_at": "2026-11-03T00:00:00Z", "observed_at": "2026-11-03T00:01:00Z"}]}
        self.write(value)
        page = self.client.get("/candidate/c-btc")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Analyst assessment", page.text)
        self.assertIn("VERSION 2", page.text)
        self.assertIn("2026-11-04 00:02:00 UTC", page.text)
        self.assertIn("retained://source", page.text)
        self.assertNotIn("<script>", page.text)


if __name__ == "__main__":
    unittest.main()
