"""Read-only timing UI, independent from an account or idxsig installation."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

from kod.workstation.operations import (
    OperationsUnavailable,
    TimingArchive,
    TIMING_SCHEMA,
    TIMING_STAGES,
    canonical,
    timing_context_views,
)
from kod.workstation.web import create_app

T0 = "2026-11-04T00:00:00Z"
T1 = "2026-11-04T00:00:01Z"
T2 = "2026-11-04T00:00:02Z"


def timing_payload():
    stats = {"known": 1, "unknown": 0, "median_seconds": 1, "p95_seconds": 1, "max_seconds": 1}
    row = {
        "schema_version": "KOD_TIMING_ATTEMPT_V1",
        "id": "attempt-1",
        "detector_version": "FIXED_v1",
        "universe_snapshot_id": "membership-1",
        "evidence_id": "receipt-1",
        "evidence_kind": "synthetic",
        "source": "fixture-source",
        "recorded_at": T2,
        "status": "NO_TRIGGER",
        "entry_permission": False,
        **{name: None for name in TIMING_STAGES},
        "scheduled_at": T0,
        "received_at": T1,
        "threshold": {"at": None, "basis": "UNKNOWN", "evidence_id": None, "reference_at": None},
        "clock": {"status": "UNKNOWN"},
        "external_timestamp": {"status": "NOT_REQUESTED"},
        "links": {"run_id": "run-1", "candidate_id": "candidate-1"},
        "reason": "No actual trigger was observed.",
    }
    return {
        "as_of": T2,
        "attempts": [row],
        "calendar": [],
        "shadow": [],
        "clock": {"status": "UNKNOWN"},
        "integrity": {"ok": True, "entry_permission": False, "attempts": 1, "revisions": 1},
        "summary": {
            "schema_version": "KOD_TIMING_CAPTURE_REPORT_V1",
            "as_of": T2,
            "entry_permission": False,
            "attempts": 1,
            "statuses": {"NO_TRIGGER": 1},
            "missing_stages": {name: int(row[name] is None) for name in TIMING_STAGES},
            "clock_statuses": {"UNKNOWN": 1},
            "external_timestamp_statuses": {"NOT_REQUESTED": 1},
            "cohorts": [
                {
                    "evidence_kind": "synthetic",
                    "detector_version": "FIXED_v1",
                    "attempts": 1,
                    "statuses": {"NO_TRIGGER": 1},
                    "stages": {"receipt_to_features": stats},
                }
            ],
            "source_latency": [
                {
                    "source": "fixture-source",
                    "evidence_kind": "synthetic",
                    "attempts": 1,
                    "lag": stats,
                    "clock_conflicts": 0,
                    "failures": 0,
                }
            ],
            "records": [{"id": "attempt-1", "seconds": {"analyst": None}}],
            "limitations": ["No profitability claim."],
        },
    }


class TimingOperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.report = self.runtime / "timing/report.json"
        self.client = TestClient(
            create_app(
                self.root / "workstation", offline=True, testing=True, runtime_root=self.runtime
            )
        )
        self.addCleanup(self.client.close)

    def write(self, value=None):
        payload = timing_payload() if value is None else value
        self.report.parent.mkdir(parents=True, exist_ok=True)
        self.report.write_text(
            json.dumps(
                {
                    "schema_version": TIMING_SCHEMA,
                    "payload": payload,
                    "sha256": hashlib.sha256(canonical(payload)).hexdigest(),
                }
            )
        )
        return payload

    def test_missing_report_is_unknown_and_get_does_not_create_runtime(self):
        response = self.client.get("/timing")
        self.assertEqual(response.status_code, 200)
        self.assertIn("No verified timing view", response.text)
        self.assertIn("No timing report is available", response.text)
        self.assertFalse(self.runtime.exists())

    def test_intraday_only_root_renders_without_account_or_network(self):
        self.write()
        before = self.report.read_bytes()
        with (
            patch("socket.create_connection", side_effect=AssertionError("network forbidden")),
            patch("socket.getaddrinfo", side_effect=AssertionError("network forbidden")),
        ):
            page = self.client.get("/timing")
        self.assertEqual(page.status_code, 200)
        self.assertIn("SYNTHETIC DEMONSTRATION INCLUDED", page.text)
        self.assertIn("1 shown / 1 retained", page.text)
        self.assertIn("NO_TRIGGER", page.text)
        self.assertIn("fixture-source", page.text)
        self.assertIn("Unknown", page.text)
        self.assertIn("No post-decision quote assessments", page.text)
        self.assertNotIn("No verified timing view", page.text)
        self.assertEqual(self.report.read_bytes(), before)
        self.assertEqual(
            [
                p.relative_to(self.runtime).as_posix()
                for p in self.runtime.rglob("*")
                if p.is_file()
            ],
            ["timing/report.json"],
        )

    def test_tampered_hash_withholds_all_payload_fields(self):
        self.write()
        value = json.loads(self.report.read_text())
        value["payload"]["attempts"][0]["source"] = "DO_NOT_DISPLAY"
        self.report.write_text(json.dumps(value))
        page = self.client.get("/timing")
        self.assertEqual(page.status_code, 200)
        self.assertIn("failed its integrity check", page.text)
        self.assertNotIn("DO_NOT_DISPLAY", page.text)
        self.assertNotIn("attempt-1", page.text)

    def test_malformed_schema_count_and_chronology_are_withheld(self):
        variants = []
        wrong_schema = timing_payload()
        wrong_schema["summary"]["schema_version"] = "UNKNOWN"
        variants.append(wrong_schema)
        wrong_count = timing_payload()
        wrong_count["summary"]["attempts"] = 2
        variants.append(wrong_count)
        future = timing_payload()
        future["attempts"][0]["recorded_at"] = "2026-11-05T00:00:00Z"
        variants.append(future)
        malformed_threshold = timing_payload()
        malformed_threshold["attempts"][0]["threshold"]["at"] = "not a time"
        variants.append(malformed_threshold)
        permission = timing_payload()
        permission["attempts"][0]["entry_permission"] = True
        variants.append(permission)
        for payload in variants:
            with self.subTest(payload=payload):
                self.write(payload)
                with self.assertRaises(OperationsUnavailable):
                    TimingArchive(self.runtime).snapshot()
                self.assertIn("No verified timing view", self.client.get("/timing").text)

    def test_duplicate_keys_nonfinite_and_oversize_refused(self):
        self.write()
        for raw in ('{"schema_version":"a","schema_version":"b"}', '{"payload":NaN}', "not json"):
            self.report.write_text(raw)
            with self.assertRaises(OperationsUnavailable):
                TimingArchive(self.runtime).snapshot()
        self.write()
        with patch("kod.workstation.operations.MAX_BYTES", 10):
            with self.assertRaisesRegex(OperationsUnavailable, "size"):
                TimingArchive(self.runtime).snapshot()

    def test_symlink_report_and_parent_refused(self):
        self.write()
        original = self.root / "outside.json"
        self.report.rename(original)
        self.report.symlink_to(original)
        with self.assertRaises(OperationsUnavailable):
            TimingArchive(self.runtime).snapshot()
        self.report.unlink()
        self.report.parent.rmdir()
        target = self.root / "outside"
        target.mkdir()
        original.rename(target / "report.json")
        self.report.parent.symlink_to(target, target_is_directory=True)
        with self.assertRaises(OperationsUnavailable):
            TimingArchive(self.runtime).snapshot()

    def test_xss_and_unowned_references_never_become_links(self):
        payload = timing_payload()
        payload["attempts"][0]["reason"] = "<script>alert(1)</script>"
        payload["attempts"][0]["links"] = {
            "candidate_id": "javascript:alert(1)",
            "url": "https://evil.example",
        }
        payload["calendar"] = [{"id": "<img src=x onerror=alert(1)>"}]
        self.write(payload)
        page = self.client.get("/timing").text
        self.assertNotIn("<script>", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn('href="javascript:', page)
        self.assertNotIn('href="https://evil.example', page)
        self.assertNotIn('href="/candidate/javascript:', page)

    def test_links_require_matching_verified_runtime_identity(self):
        from test_operations import payload, SCHEMA

        self.write()
        legacy = payload()
        legacy["run"]["id"] = "run-1"
        legacy["candidates"][0]["id"] = "candidate-1"
        (self.runtime / "snapshot.json").write_text(
            json.dumps(
                {
                    "schema_version": SCHEMA,
                    "payload": legacy,
                    "sha256": hashlib.sha256(canonical(legacy)).hexdigest(),
                }
            )
        )
        page = self.client.get("/timing").text
        self.assertIn('href="/candidate/candidate-1"', page)
        self.assertIn('href="/today">run-1', page)
        self.assertIn('href="/timing"', self.client.get("/today").text)

    def test_context_join_preserves_cohort_and_actual_retention_time(self):
        payload = timing_payload()
        item = {
            "recorded_at": T1,
            "as_of": T0,
            "context": {
                "calendar": {
                    "events": [
                        {"id": "<script>event</script>", "event_at": T2, "timing_state": "UPCOMING"}
                    ]
                },
                "preparations": [{"branch": "UPPER_AND_LOWER"}],
                "shadow": [{"decision_id": "decision-1", "status": "INDICATIVE_ONLY"}],
                "avoid": [{"liquidity": "UNKNOWN"}],
                "source_validation": "Declarations only.",
            },
        }
        identity = hashlib.sha256(canonical(item)).hexdigest()
        payload["contexts"] = [item]
        payload["attempts"][0]["detector_version"] = "CONTEXT_PREPARATION_V1"
        payload["attempts"][0]["links"]["context_id"] = identity
        view = timing_context_views(payload)[0]
        self.assertEqual(
            (view["evidence_kind"], view["recorded_at"], view["as_of"]), ("synthetic", T1, T0)
        )
        self.write(payload)
        page = self.client.get("/timing").text
        self.assertIn("Analytical cutoff", page)
        self.assertIn("Actually retained", page)
        self.assertIn("Avoid observations · hypotheses, no automatic veto", page)
        self.assertIn("synthetic context · indicative quote assessment", page)
        self.assertIn("&lt;script&gt;event&lt;/script&gt;", page)
        self.assertNotIn("<script>event", page)
        self.assertIn("A source request is not another scheduled run", page)
        payload["attempts"][0]["links"]["context_id"] = "unrelated"
        self.assertEqual(timing_context_views(payload)[0]["evidence_kind"], "UNKNOWN")
        payload["attempts"][0]["links"]["context_id"] = identity
        payload["attempts"][0]["detector_version"] = "UNRELATED_DETECTOR"
        self.assertEqual(timing_context_views(payload)[0]["evidence_kind"], "UNKNOWN")

    def test_legacy_flattened_context_has_unknown_provenance(self):
        payload = timing_payload()
        payload["calendar"] = [{"events": [{"id": "old-event"}]}]
        payload["shadow"] = [{"decision_id": "old-decision"}]
        view = timing_context_views(payload)[0]
        self.assertEqual(view["evidence_kind"], "UNKNOWN")
        self.assertIsNone(view["recorded_at"])
        self.assertEqual(view["calendar"], [{"id": "old-event"}])
        self.write(payload)
        page = self.client.get("/timing").text
        self.assertIn("Context provenance is unavailable", page)
        self.assertIn("old-event", page)

    def test_malformed_context_and_link_never_crash_page(self):
        variants = []
        link = timing_payload()
        link["attempts"][0]["links"]["candidate_id"] = []
        variants.append(link)
        for context in (
            {"recorded_at": "2026-11-05T00:00:00Z", "as_of": T0, "context": {"calendar": {}}},
            {"recorded_at": T0, "as_of": T1, "context": {"calendar": {}}},
            {"recorded_at": T1, "as_of": T0, "context": {"calendar": {"events": ["bad"]}}},
            {"recorded_at": T1, "as_of": T0, "context": {"calendar": {}, "shadow": {}}},
        ):
            payload = timing_payload()
            payload["contexts"] = [context]
            variants.append(payload)
        calendar = timing_payload()
        calendar["calendar"] = [{"events": None}]
        variants.append(calendar)
        permission = timing_payload()
        permission["entry_permission"] = True
        variants.append(permission)
        for payload in variants:
            with self.subTest(payload=payload):
                self.write(payload)
                page = self.client.get("/timing")
                self.assertEqual(page.status_code, 200)
                self.assertIn("No verified timing view", page.text)

    def test_old_runtime_snapshot_pages_work_without_timing(self):
        from test_operations import payload, SCHEMA

        self.runtime.mkdir()
        legacy = payload()
        (self.runtime / "snapshot.json").write_text(
            json.dumps(
                {
                    "schema_version": SCHEMA,
                    "payload": legacy,
                    "sha256": hashlib.sha256(canonical(legacy)).hexdigest(),
                }
            )
        )
        before = (self.runtime / "snapshot.json").read_bytes()
        self.assertIn("RUN-TEST", self.client.get("/today").text)
        self.assertIn("No verified timing view", self.client.get("/timing").text)
        self.assertEqual((self.runtime / "snapshot.json").read_bytes(), before)

    def test_known_times_sorted_and_missing_stages_explicit(self):
        from kod.workstation.operations import timing_timeline

        row = deepcopy(timing_payload()["attempts"][0])
        row.update(started_at=T0, detected_at=T2)
        timeline = timing_timeline(row)
        known = [r["at"] for r in timeline if r["at"]]
        self.assertEqual(known, sorted(known))
        self.assertEqual(len(timeline), len(TIMING_STAGES) + 1)
        self.assertIsNone(timeline[-1]["at"])

    def test_actual_timing_demo_renders_with_original_account_routes(self):
        repository = Path(__file__).resolve().parents[2]
        subprocess.run(
            [sys.executable, "-m", "idxsig.runtime", "--root", str(self.runtime), "timing-demo"],
            cwd=repository / "idx-signals",
            check=True,
            capture_output=True,
            text=True,
        )
        before = self.report.read_bytes()
        snapshot = TimingArchive(self.runtime).snapshot()
        page = self.client.get("/timing")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("No verified timing view", page.text)
        self.assertIn("SYNTHETIC DEMONSTRATION INCLUDED", page.text)
        self.assertIn(snapshot["sha256"], page.text)
        self.assertIn("SOURCE_REQUEST_V1", page.text)
        self.assertIn("INDICATIVE", page.text)
        self.assertIn("synthetic context · indicative quote assessment", page.text)
        self.assertIn("Actually retained", page.text)
        self.assertNotIn("Context provenance is unavailable", page.text)
        self.assertIn("SYNTHETIC DEMONSTRATION", self.client.get("/today").text)
        self.assertNotIn("No fills recorded.", self.client.get("/paper-portfolio").text)
        self.assertEqual(before, self.report.read_bytes())


if __name__ == "__main__":
    unittest.main()
