"""Inspection must not invent prices, fills, clocks, or runtime mutations."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from kod.workstation.decision_inspector import DecisionInspector, _plot
from kod.workstation.operations import canonical, TIMING_SCHEMA, OperationsUnavailable
from kod.workstation.web import create_app
from test_timing_operations import timing_payload

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "idx-signals") not in sys.path:
    sys.path.insert(0, str(REPO / "idx-signals"))


def hashes(root):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


class DecisionInspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.client = TestClient(
            create_app(
                self.root / "workstation", offline=True, testing=True, runtime_root=self.runtime
            )
        )
        self.addCleanup(self.client.close)

    def write_report(self, payload):
        path = self.runtime / "timing/report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": TIMING_SCHEMA,
                    "payload": payload,
                    "sha256": hashlib.sha256(canonical(payload)).hexdigest(),
                }
            )
        )

    def demo(self):
        from idxsig.runtime.timing_demo import timing_demo

        return timing_demo(self.runtime)

    def page(self, identity, **params):
        return self.client.get("/timing/attempt", params={"id": identity, **params})

    def test_unknown_id_404_and_missing_report_creates_nothing(self):
        page = self.page("anything")
        self.assertEqual(page.status_code, 200)
        self.assertIn("No verified attempt view", page.text)
        self.assertFalse(self.runtime.exists())
        self.write_report(timing_payload())
        self.assertEqual(self.page("../outside").status_code, 404)

    def test_timing_only_attempt_retains_unknown_prices_decisions_and_fills(self):
        self.write_report(timing_payload())
        before = hashes(self.runtime)
        with patch("socket.getaddrinfo", side_effect=AssertionError("network forbidden")):
            page = self.page("attempt-1")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Decision inspector", page.text)
        self.assertIn("DECLARED / UNVERIFIED CHRONOLOGY", page.text)
        self.assertIn("execution claims are withheld", page.text)
        self.assertIn("Unknown", page.text)
        self.assertNotIn('<polyline class="inspector-price"', page.text)
        self.assertEqual(before, hashes(self.runtime))
        self.assertIn("/timing/attempt?id=attempt-1", self.client.get("/timing").text)

    def test_actual_capture_verifies_source_bytes_and_charts_without_writes(self):
        demo = self.demo()
        before = hashes(self.runtime)
        with patch("socket.getaddrinfo", side_effect=AssertionError("network forbidden")):
            view = DecisionInspector(self.runtime).attempt(demo["capture_attempt_id"])
            page = self.page(demo["capture_attempt_id"])
        self.assertEqual(view["price_status"], "VERIFIED_RETAINED_BYTES")
        self.assertEqual(len(view["bars"]), 2)
        self.assertEqual(view["symbol"], "BTCUSDT")
        self.assertEqual(view["capture"]["interval"], "1m")
        self.assertIn('<polyline class="inspector-price"', page.text)
        self.assertIn("SYNTHETIC DEMONSTRATION", page.text)
        self.assertIn("Local receipt", page.text)
        self.assertIn("No linked simulated fill", page.text)
        self.assertEqual(before, hashes(self.runtime))

    def test_symbol_switch_and_outside_membership_fail_closed(self):
        identity = self.demo()["capture_attempt_id"]
        view = DecisionInspector(self.runtime).attempt(identity, symbol="ETHUSDT")
        self.assertEqual(view["symbol"], "ETHUSDT")
        self.assertTrue(all(row["symbol"] == "ETHUSDT" for row in view["bars"]))
        page = self.page(identity, symbol="UNOWNED")
        self.assertIn("outside retained membership", page.text)
        self.assertNotIn('<polyline class="inspector-price"', page.text)

    def test_capture_hash_tamper_withholds_prices_but_preserves_chronology(self):
        identity = self.demo()["capture_attempt_id"]
        path = self.runtime / "timing/captures" / (identity + ".json")
        body = json.loads(path.read_text())
        body["bars"][0]["close"] = "99999"
        path.write_text(json.dumps(body))
        page = self.page(identity)
        self.assertIn("Linked capture bytes changed", page.text)
        self.assertNotIn("99999", page.text)
        self.assertIn("Observation and decision timeline", page.text)
        self.assertNotIn('<polyline class="inspector-price"', page.text)

    def test_raw_evidence_tamper_withholds_prices(self):
        identity = self.demo()["capture_attempt_id"]
        capture = json.loads((self.runtime / "timing/captures" / (identity + ".json")).read_text())
        evidence = next(row for row in capture["evidence"] if "klines" in row["source_url"])
        (self.runtime / "evidence" / evidence["path"]).write_bytes(b"[]")
        view = DecisionInspector(self.runtime).attempt(identity)
        self.assertEqual(view["price_status"], "UNAVAILABLE")
        self.assertIn("evidence hash mismatch", view["price_reason"])
        self.assertIsNone(view["plot"])

    def test_symlink_and_path_escape_are_not_followed(self):
        payload = timing_payload()
        payload["attempts"][0]["links"].update(
            capture_path="../outside.json",
            capture_sha256="0" * 64,
            capture_membership_id="universe_" + "0" * 64,
        )
        self.write_report(payload)
        self.assertIn("DECLARED / UNVERIFIED CHRONOLOGY", self.page("attempt-1").text)
        identity = self.demo()["capture_attempt_id"]
        source = self.runtime / "timing/captures" / (identity + ".json")
        dest = self.root / "outside.json"
        source.rename(dest)
        source.symlink_to(dest)
        self.assertIn("uses a symlink", self.page(identity).text)

    def test_source_request_uses_its_verified_parent_and_symbol(self):
        identity = self.demo()["capture_attempt_id"]
        report = json.loads((self.runtime / "timing/report.json").read_text())
        candidates = [
            row
            for row in report["payload"]["attempts"]
            if row["links"].get("parent_attempt_id") == identity
        ]
        capture = json.loads((self.runtime / "timing/captures" / (identity + ".json")).read_text())
        index = next(
            i for i, request in enumerate(capture["requests"]) if request.get("symbol") == "ETHUSDT"
        )
        child = next(row for row in candidates if row["id"].endswith(":request:" + str(index)))
        view = DecisionInspector(self.runtime).attempt(child["id"])
        self.assertEqual(view["price_status"], "VERIFIED_RETAINED_BYTES")
        self.assertEqual(view["capture_owner"], identity)
        self.assertEqual(view["symbol"], "ETHUSDT")
        child["evidence_id"] = "unrelated-receipt"
        self.write_report(report["payload"])
        self.assertIn("differs from retained timing journal", self.page(child["id"]).text)

    def test_matching_paper_fill_is_simulated_and_never_an_interpolated_marker(self):
        self.demo()
        report = json.loads((self.runtime / "timing/report.json").read_text())
        filled = next(row for row in report["payload"]["attempts"] if row["links"].get("fill_id"))
        view = DecisionInspector(self.runtime).attempt(filled["id"])
        self.assertIsNotNone(view["fill"])
        self.assertIsNone(view["plot"])
        page = self.page(filled["id"])
        self.assertIn("matches the timing record", page.text)
        self.assertIn("not a real order", page.text)
        filled["links"]["fill_record_sha256"] = "f" * 64
        self.write_report(report["payload"])
        with self.assertRaisesRegex(OperationsUnavailable, "differs from retained timing journal"):
            DecisionInspector(self.runtime).attempt(filled["id"])

    def test_xss_and_reference_urls_remain_escaped_text(self):
        payload = timing_payload()
        payload["attempts"][0]["reason"] = "<script>alert(1)</script>"
        payload["attempts"][0]["links"]["external"] = "javascript:alert(1)"
        payload["summary"]["records"][0]["clock_conflicts"] = ["source_to_receipt"]
        self.write_report(payload)
        page = self.page("attempt-1")
        self.assertIn("&lt;script&gt;", page.text)
        self.assertNotIn("<script>", page.text)
        self.assertNotIn('href="javascript:', page.text)
        self.assertIn("CLOCK CONFLICT", page.text)
        self.assertIn("not predictive lead", page.text)

    def test_rehashed_projection_cannot_invent_a_decision_or_delay(self):
        identity = self.demo()["capture_attempt_id"]
        path = self.runtime / "timing/report.json"
        original = json.loads(path.read_text())["payload"]
        for field in ("attempt", "summary"):
            value = json.loads(json.dumps(original))
            if field == "attempt":
                row = next(row for row in value["attempts"] if row["id"] == identity)
                row["decision_at"] = row["received_at"]
            else:
                row = next(row for row in value["summary"]["records"] if row["id"] == identity)
                row["seconds"]["analyst"] = 0.0
            self.write_report(value)
            page = self.page(identity)
            self.assertIn("Chronology verification failed", page.text)
            self.assertNotIn('<polyline class="inspector-price"', page.text)
            self.assertNotIn("Observation and decision timeline", page.text)

    def test_missing_original_journal_cannot_preserve_verified_price_claim(self):
        identity = self.demo()["capture_attempt_id"]
        journal = self.runtime / "timing/attempts.jsonl"
        journal.rename(self.runtime / "journal-offline.jsonl")
        view = DecisionInspector(self.runtime).attempt(identity)
        self.assertEqual(view["chronology_status"], "DECLARED_REPORT_ONLY")
        self.assertIsNone(view["plot"])
        self.assertIsNone(view["fill"])
        self.assertNotEqual(view["price_status"], "VERIFIED_RETAINED_BYTES")

    def test_public_capture_is_compatible_with_prospective_attempt_cohort(self):
        from idxsig.runtime.timing import capture_intraday
        from idxsig.runtime.timing_demo import DEMO_TIME, synthetic_fetcher

        # Fake transport supplies a production-shaped public_market receipt.
        result = capture_intraday(
            self.runtime,
            scheduled_at=DEMO_TIME.isoformat(),
            symbols=["BTCUSDT"],
            bars=2,
            fetcher=synthetic_fetcher,
            clock=lambda: DEMO_TIME.isoformat(),
            evidence_kind="public_market",
        )
        view = DecisionInspector(self.runtime).attempt(result["attempt_id"])
        self.assertEqual(view["attempt"]["evidence_kind"], "prospective")
        self.assertEqual(view["price_status"], "VERIFIED_RETAINED_BYTES")
        self.assertEqual(len(view["bars"]), 2)
        self.assertIsNone(view["attempt"]["decision_at"])

    def test_legacy_clock_claim_is_separated_from_raw_evidence_assessment(self):
        payload = timing_payload()
        payload["attempts"][0]["clock"]["offset_seconds"] = "1793797157.055892788"
        self.write_report(payload)
        assessment = {
            "status": "DERIVED_FROM_RETAINED_RAW",
            "original_claim_valid": False,
            "system_time_offset_seconds": "0.001661492",
            "conditional_error_bound_seconds": "0.0265711735",
            "reason": "legacy offset used the reference-time column",
        }
        before = hashes(self.runtime)
        with patch("idxsig.runtime.timing_evidence.assess_retained_clock", return_value=assessment):
            detail = self.page("attempt-1").text
            overview = self.client.get("/timing").text
        self.assertIn("original clock-offset claim is unverified or incorrect", detail)
        self.assertIn("0.001661492 s", detail)
        self.assertIn("Original clock declaration", detail)
        self.assertIn("Original clock labels", overview)
        self.assertIn("DERIVED_FROM_RETAINED_RAW", overview)
        self.assertEqual(before, hashes(self.runtime))

    def test_bar_gaps_are_not_connected_and_unknown_stage_has_no_marker(self):
        bars = [
            {
                "open_time": "2026-11-04T00:00:00Z",
                "bar_end_at": "2026-11-04T00:01:00Z",
                "close": "100",
            },
            {
                "open_time": "2026-11-04T00:02:00Z",
                "bar_end_at": "2026-11-04T00:03:00Z",
                "close": "102",
            },
        ]
        chart = _plot(bars, {"decision_at": "2026-11-04T00:02:00Z"})
        self.assertEqual(len(chart["segments"]), 2)
        self.assertEqual(len(chart["markers"]), 1)
        self.assertEqual(chart["markers"][0]["label"], "Decision")
        self.assertNotIn("price", chart["markers"][0])


if __name__ == "__main__":
    unittest.main()
