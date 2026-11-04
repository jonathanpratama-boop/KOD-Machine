"""Tests for kod_watch on fake plan/schedule trees in temporary directories.

Standard library only. Receipts are synthetic: they follow the shape that the deployed
observe.py writes (slot, scheduled_at, plan_sha256, observed_at, status, completed_at and
reason or error), because no real end.json existed when this kit was written. The plan and
deployment record are byte-exact copies of the deployed files (fixtures/deployed-2026-11-04).
No test opens a network connection: every ping goes to an injected fake.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest import mock
import urllib.error
import urllib.request

import kod_watch

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "deployed-2026-11-04"
PLAN_BYTES = (FIXTURES / "observation-plan.json").read_bytes()
PLAN = json.loads(PLAN_BYTES)
CANONICAL = hashlib.sha256(json.dumps(PLAN, sort_keys=True).encode()).hexdigest()
START = datetime(2026, 11, 4, 13, tzinfo=timezone.utc)
SLOT_URL = "https://hc-ping.example/slot-check-0001"
DAILY_URL = "https://hc-ping.example/daily-check-0002"
ENV = {"KOD_WATCH_SLOT_URL": SLOT_URL, "KOD_WATCH_DAILY_URL": DAILY_URL}
# observe.py's own reason text for an INTERRUPTED receipt.
INTERRUPTED = "Prior invocation started without a completion receipt; not recollected"


def slot_time(number: int) -> datetime:
    return START + timedelta(hours=4 * (number - 1))


def at(number: int, minutes: float) -> datetime:
    return slot_time(number) + timedelta(minutes=minutes)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


class Response:
    def __init__(self, status: int):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Network:
    """Fake HTTPS endpoint: each outcome is a status code or an exception to raise."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        outcome = self.outcomes.pop(0) if self.outcomes else 200
        if isinstance(outcome, Exception):
            raise outcome
        return Response(outcome)


class Tree:
    """Fake server layout: plan, deployment record and observe.py's schedule directory."""

    def __init__(self, root: Path):
        self.plan = root / "etc/kod/observation-plan.json"
        self.deployment = root / "opt/kod/audit/DEPLOYMENT.json"
        self.schedule = root / "var/lib/kod/schedule"
        self.plan.parent.mkdir(parents=True)
        self.plan.write_bytes(PLAN_BYTES)
        self.deployment.parent.mkdir(parents=True)
        self.deployment.write_bytes((FIXTURES / "DEPLOYMENT.json").read_bytes())
        self.schedule.mkdir(parents=True)

    def receipt(self, number: int, **fields) -> dict:
        value = {
            "slot": number,
            "scheduled_at": PLAN["slots"][number - 1],
            "plan_sha256": CANONICAL,
            "observed_at": kod_watch.stamp(at(number, 0.1)),
        }
        value.update(fields)
        return value

    def begin(self, number: int) -> None:
        write_json(self.schedule / f"slot-{number:02d}/begin.json", self.receipt(number))

    def record(self, number: int, status: str, **fields) -> dict:
        self.begin(number)
        end = self.receipt(number, status=status, completed_at=kod_watch.stamp(at(number, 2)))
        end.update(fields)
        write_json(self.schedule / f"slot-{number:02d}/end.json", end)
        return end

    def captured(self, *numbers: int) -> None:
        for number in numbers:
            self.record(number, "CAPTURED")

    def args(self, mode: str, *extra: str) -> list[str]:
        paths = ["--plan", str(self.plan), "--schedule", str(self.schedule)]
        return [mode, *paths, "--deployment", str(self.deployment), *extra]


class Run:
    def __init__(self, code, record, stderr, requests, sleeps):
        self.code = code
        self.record = record
        self.stderr = stderr
        self.requests = requests
        self.sleeps = sleeps

    @property
    def body(self) -> str:
        return self.record["body"]


class WatchTestCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.tree = Tree(self.root)

    def run_watch(self, mode, now, *extra, network=None, environ=ENV) -> Run:
        out, err = io.StringIO(), io.StringIO()
        network = Network() if network is None else network
        sleeps = []
        code = kod_watch.main(
            self.tree.args(mode, *extra),
            environ=environ,
            clock=lambda: now,
            open_url=network,
            sleep=sleeps.append,
            stdout=out,
            stderr=err,
        )
        record = json.loads(out.getvalue()) if out.getvalue() else None
        return Run(code, record, err.getvalue(), network.requests, sleeps)

    def assertPinged(self, run: Run, url: str, body: str) -> None:
        self.assertEqual(run.code, 0, run.stderr)
        self.assertEqual(len(run.requests), 1)
        request, timeout = run.requests[0]
        self.assertEqual(request.full_url, url)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.data, body.encode("utf-8"))
        self.assertEqual(request.get_header("Content-type"), "text/plain; charset=utf-8")
        self.assertEqual(timeout, kod_watch.TIMEOUT_SECONDS)
        self.assertEqual(run.body, body)
        self.assertTrue(run.record["delivered"])


class SlotModeTests(WatchTestCase):
    def test_all_captured_pings_success(self):
        self.tree.captured(1, 2, 3, 4, 5, 6)
        run = self.run_watch("slot", at(6, 12))
        self.assertPinged(
            run,
            SLOT_URL,
            "KOD OK: slot 6 2026-11-05T09:00Z CAPTURED; slots 1-6 CAPTURED, 0 failed; "
            "next 2026-11-05T13:00Z (20:00 WIB)",
        )
        self.assertEqual(run.record["result"], "OK")

    def test_missing_end_receipt_past_grace_fails(self):
        self.tree.captured(1, 2, 3, 4, 5)
        run = self.run_watch("slot", at(6, 12))
        self.assertPinged(
            run,
            SLOT_URL + "/fail",
            "KOD FAIL: slot 6 2026-11-05T09:00Z NOT_STARTED: no begin.json or end.json; "
            "slots 1-5 CAPTURED, 1 failed (6 NOT_STARTED); next 2026-11-05T13:00Z (20:00 WIB)",
        )
        self.assertEqual(run.record["result"], "FAIL")

    def test_begin_without_end_past_grace_fails(self):
        self.tree.captured(1, 2, 3, 4, 5)
        self.tree.begin(6)
        run = self.run_watch("slot", at(6, 12))
        self.assertEqual(run.requests[0][0].full_url, SLOT_URL + "/fail")
        self.assertIn(
            "slot 6 2026-11-05T09:00Z UNFINISHED: begin.json without end.json "
            "(interrupted or still running)",
            run.body,
        )

    def test_slot_inside_grace_is_not_judged_yet(self):
        self.tree.captured(1, 2, 3, 4, 5)
        run = self.run_watch("slot", at(6, 10.5))
        self.assertPinged(
            run,
            SLOT_URL,
            "KOD OK: slot 5 2026-11-05T05:00Z CAPTURED; slots 1-5 CAPTURED, 0 failed; "
            "next 2026-11-05T09:00Z (16:00 WIB)",
        )

    def test_grace_is_configurable(self):
        self.tree.captured(1, 2, 3, 4, 5)
        run = self.run_watch("slot", at(6, 12), "--grace-seconds", "300")
        self.assertEqual(run.requests[0][0].full_url, SLOT_URL)
        self.assertTrue(run.body.startswith("KOD OK: slot 5 2026-11-05T05:00Z CAPTURED;"))

    def test_other_statuses_fail_with_their_reason(self):
        cases = [
            ("MISSED", {}, "MISSED"),
            ("BLOCKED", {}, "BLOCKED"),
            ("PARTIAL", {}, "PARTIAL"),
            ("INTERRUPTED", {"reason": INTERRUPTED}, f"INTERRUPTED: {INTERRUPTED}"),
            ("FAILED", {"error": "capture failed: boom"}, "FAILED: capture failed: boom"),
        ]
        for status, fields, clause in cases:
            with self.subTest(status=status):
                self.setUp()
                self.tree.captured(1, 2, 3, 4, 5)
                self.tree.record(6, status, **fields)
                run = self.run_watch("slot", at(6, 12))
                self.assertPinged(
                    run,
                    SLOT_URL + "/fail",
                    f"KOD FAIL: slot 6 2026-11-05T09:00Z {clause}; slots 1-5 CAPTURED, "
                    f"1 failed (6 {status}); next 2026-11-05T13:00Z (20:00 WIB)",
                )

    def test_halted_fails_every_run(self):
        self.tree.captured(1, 2, 3, 4, 5)
        failed = self.tree.record(6, "FAILED", error="timing verification did not pass")
        write_json(self.tree.schedule / "HALTED.json", failed)
        halted = "HALTED.json present (slot 6 FAILED: timing verification did not pass)"
        first = self.run_watch("slot", at(6, 12))
        self.assertEqual(first.requests[0][0].full_url, SLOT_URL + "/fail")
        self.assertTrue(first.body.startswith(f"KOD FAIL: {halted}; slot 6 "), first.body)
        later = self.run_watch("slot", at(7, 12))
        self.assertPinged(
            later,
            SLOT_URL + "/fail",
            f"KOD FAIL: {halted}; slot 7 2026-11-05T13:00Z NOT_STARTED: no begin.json or "
            "end.json; slots 1-5 CAPTURED, 2 failed (6 FAILED, 7 NOT_STARTED); "
            "next 2026-11-05T17:00Z (2026-11-06 00:00 WIB)",
        )

    def test_before_first_slot_nothing_due(self):
        run = self.run_watch("slot", START - timedelta(hours=1))
        self.assertPinged(
            run, SLOT_URL, "KOD OK: no slot due yet; next 2026-11-04T13:00Z (20:00 WIB)"
        )

    def test_cohort_complete_is_reported_once_then_quiet(self):
        self.tree.captured(*range(1, 31))
        final = self.run_watch("slot", at(30, 12))
        self.assertPinged(
            final,
            SLOT_URL,
            "KOD OK COHORT COMPLETE: slot 30 2026-11-09T09:00Z CAPTURED; slots 1-30 CAPTURED, "
            "0 failed; slot watch finished: disable kod-watch-slot.timer and pause the slot check",
        )
        after = self.run_watch("slot", at(31, 12))
        self.assertEqual(after.code, 0)
        self.assertEqual(after.requests, [])
        self.assertEqual(after.record["result"], "QUIET")
        self.assertEqual(
            after.body,
            "nothing sent: cohort complete and already reported; "
            "disable kod-watch-slot.timer and pause the slot check",
        )
        self.assertIsNone(after.record["target"])
        self.assertIsNone(after.record["delivered"])

    def test_cohort_complete_with_failed_last_slot_pings_fail(self):
        self.tree.captured(*range(1, 30))
        self.tree.record(30, "MISSED")
        run = self.run_watch("slot", at(30, 12))
        self.assertEqual(run.requests[0][0].full_url, SLOT_URL + "/fail")
        self.assertTrue(run.body.startswith("KOD FAIL COHORT COMPLETE: slot 30 "), run.body)

    def test_plan_sha_mismatch_fails(self):
        self.tree.captured(1, 2, 3, 4, 5, 6)
        reformatted = (json.dumps(PLAN, indent=1) + "\n").encode()
        self.tree.plan.write_bytes(reformatted)
        observed = hashlib.sha256(reformatted).hexdigest()[:12]
        run = self.run_watch("slot", at(6, 12))
        self.assertPinged(
            run,
            SLOT_URL + "/fail",
            f"KOD FAIL: plan sha256 {observed} differs from deployment record bffe919924e5; "
            "slot 6 2026-11-05T09:00Z CAPTURED; slots 1-6 CAPTURED, 0 failed; "
            "next 2026-11-05T13:00Z (20:00 WIB)",
        )

    def test_receipt_written_under_another_plan_is_invalid(self):
        self.tree.captured(1, 2, 3, 4, 5)
        self.tree.record(6, "CAPTURED", plan_sha256="0" * 64)
        run = self.run_watch("slot", at(6, 12))
        self.assertEqual(run.requests[0][0].full_url, SLOT_URL + "/fail")
        self.assertIn(
            "slot 6 2026-11-05T09:00Z INVALID_RECEIPT: end.json plan_sha256 differs from the plan",
            run.body,
        )

    def test_unknown_status_and_wrong_slot_are_invalid(self):
        self.tree.captured(1, 2, 3, 4)
        self.tree.record(5, "DONE")
        self.tree.record(6, "CAPTURED", slot=5)
        run = self.run_watch("slot", at(6, 12))
        self.assertIn("slot 6 2026-11-05T09:00Z INVALID_RECEIPT: end.json is for slot 5", run.body)
        self.assertIn("2 failed (5 INVALID_RECEIPT, 6 INVALID_RECEIPT)", run.body)
        daily = self.run_watch("daily", at(6, 30))
        self.assertIn("2 failed (5 INVALID_RECEIPT, 6 INVALID_RECEIPT)", daily.body)

    def test_earlier_failure_is_listed_without_holding_the_check_down(self):
        self.tree.captured(1, 2, 3, 4, 6)
        self.tree.record(5, "MISSED")
        run = self.run_watch("slot", at(6, 12))
        self.assertPinged(
            run,
            SLOT_URL,
            "KOD OK: slot 6 2026-11-05T09:00Z CAPTURED; slots 1-4,6 CAPTURED, 1 failed "
            "(5 MISSED); next 2026-11-05T13:00Z (20:00 WIB)",
        )

    def test_unreadable_plan_fails_with_reason(self):
        self.tree.plan.unlink()
        run = self.run_watch("slot", at(6, 12))
        self.assertPinged(
            run,
            SLOT_URL + "/fail",
            f"KOD FAIL: plan unreadable: {self.tree.plan}: No such file or directory",
        )

    def test_invalid_plan_fails_with_reason(self):
        broken = dict(PLAN, slots=PLAN["slots"][:2] + PLAN["slots"][3:])
        self.tree.plan.write_text(json.dumps(broken))
        run = self.run_watch("slot", at(6, 12))
        self.assertEqual(run.requests[0][0].full_url, SLOT_URL + "/fail")
        self.assertIn("plan invalid: slots 2 and 3 are not four hours apart", run.body)

    def test_unexpected_watcher_error_is_reported_as_failure(self):
        with mock.patch.object(kod_watch, "assess", side_effect=RuntimeError("boom")):
            slot = self.run_watch("slot", at(6, 12))
            daily = self.run_watch("daily", at(6, 30))
        self.assertPinged(slot, SLOT_URL + "/fail", "KOD FAIL: watcher error: RuntimeError: boom")
        self.assertPinged(
            daily, DAILY_URL + "/fail", "KOD 2026-11-05: watcher error: RuntimeError: boom"
        )
        self.assertIn("Traceback", slot.stderr)


class DailyModeTests(WatchTestCase):
    def test_daily_summary_text_exact(self):
        self.tree.captured(1, 2, 3, 4, 5, 6)
        run = self.run_watch("daily", datetime(2026, 11, 5, 9, 30, tzinfo=timezone.utc))
        self.assertPinged(
            run,
            DAILY_URL,
            "KOD 2026-11-05: slots 1-6 CAPTURED, 0 failed, next 2026-11-05T13:00Z (20:00 WIB)",
        )

    def test_scheduled_daily_line_at_0130_utc(self):
        self.tree.captured(1, 2, 3, 4)
        run = self.run_watch("daily", datetime(2026, 11, 5, 1, 30, tzinfo=timezone.utc))
        self.assertPinged(
            run,
            DAILY_URL,
            "KOD 2026-11-05: slots 1-4 CAPTURED, 0 failed, next 2026-11-05T05:00Z (12:00 WIB)",
        )

    def test_failure_in_last_day_pings_fail(self):
        self.tree.captured(1, 2, 4)
        self.tree.record(3, "MISSED")
        run = self.run_watch("daily", datetime(2026, 11, 5, 1, 30, tzinfo=timezone.utc))
        self.assertPinged(
            run,
            DAILY_URL + "/fail",
            "KOD 2026-11-05: slots 1-2,4 CAPTURED, 1 failed (3 MISSED), "
            "next 2026-11-05T05:00Z (12:00 WIB)",
        )

    def test_failure_older_than_a_day_is_listed_but_pings_success(self):
        self.tree.captured(1, 2, 4, 5, 6, 7, 8, 9, 10)
        self.tree.record(3, "MISSED")
        run = self.run_watch("daily", datetime(2026, 11, 6, 1, 30, tzinfo=timezone.utc))
        self.assertPinged(
            run,
            DAILY_URL,
            "KOD 2026-11-06: slots 1-2,4-10 CAPTURED, 1 failed (3 MISSED), "
            "next 2026-11-06T05:00Z (12:00 WIB)",
        )

    def test_halted_daily_line_pings_fail(self):
        self.tree.captured(1, 2, 3)
        failed = self.tree.record(4, "FAILED", error="timing verification did not pass")
        write_json(self.tree.schedule / "HALTED.json", failed)
        run = self.run_watch("daily", datetime(2026, 11, 6, 1, 30, tzinfo=timezone.utc))
        self.assertPinged(
            run,
            DAILY_URL + "/fail",
            "KOD 2026-11-06: HALTED.json present (slot 4 FAILED: timing verification did not "
            "pass); slots 1-3 CAPTURED, 7 failed (4 FAILED, 5 NOT_STARTED, 6 NOT_STARTED, "
            "7 NOT_STARTED, 8 NOT_STARTED, 9 NOT_STARTED, 10 NOT_STARTED), "
            "next 2026-11-06T05:00Z (12:00 WIB)",
        )

    def test_daily_before_first_slot_and_after_cohort(self):
        before = self.run_watch("daily", datetime(2026, 11, 4, 1, 30, tzinfo=timezone.utc))
        self.assertPinged(
            before, DAILY_URL, "KOD 2026-11-04: no slot due yet, next 2026-11-04T13:00Z (20:00 WIB)"
        )
        self.tree.captured(*range(1, 31))
        after = self.run_watch("daily", datetime(2026, 11, 10, 1, 30, tzinfo=timezone.utc))
        self.assertPinged(
            after, DAILY_URL, "KOD 2026-11-10: slots 1-30 CAPTURED, 0 failed, cohort complete"
        )


class PingTests(WatchTestCase):
    def test_retries_with_backoff_then_delivers(self):
        network = Network(urllib.error.URLError("temporary failure"), 503, 200)
        run = self.run_watch("slot", START - timedelta(hours=1), network=network)
        self.assertEqual(run.code, 0, run.stderr)
        self.assertEqual(len(run.requests), 3)
        self.assertEqual(run.sleeps, [2, 4])
        self.assertEqual(run.record["attempts"], 3)
        self.assertEqual(
            run.record["errors"], ["attempt 1: URLError: temporary failure", "attempt 2: HTTP 503"]
        )

    def test_http_error_and_timeout_are_retried(self):
        error = urllib.error.HTTPError(SLOT_URL, 500, "Server Error", {}, None)
        network = Network(error, TimeoutError("timed out"), 200)
        run = self.run_watch("slot", START - timedelta(hours=1), network=network)
        self.assertTrue(run.record["delivered"])
        self.assertEqual(
            run.record["errors"], ["attempt 1: HTTP 500", "attempt 2: TimeoutError: timed out"]
        )

    def test_gives_up_after_three_retries(self):
        failures = [urllib.error.URLError("unreachable") for _ in range(4)]
        run = self.run_watch("slot", START - timedelta(hours=1), network=Network(*failures))
        self.assertEqual(run.code, 1)
        self.assertEqual(len(run.requests), 4)
        self.assertEqual(run.sleeps, [2, 4, 8])
        self.assertFalse(run.record["delivered"])
        self.assertIn("kod-watch: ping not delivered after 4 attempts", run.stderr)
        self.assertNotIn("slot-check-0001", run.stderr)

    def test_dry_run_sends_nothing_and_redacts_the_url(self):
        self.tree.captured(1, 2, 3, 4, 5)
        out, err = io.StringIO(), io.StringIO()
        network = Network()
        code = kod_watch.main(
            self.tree.args("slot", "--dry-run"),
            environ=ENV,
            clock=lambda: at(6, 12),
            open_url=network,
            sleep=lambda seconds: None,
            stdout=out,
            stderr=err,
        )
        self.assertEqual(code, 0)
        self.assertEqual(network.requests, [])
        record = json.loads(out.getvalue())
        self.assertTrue(record["dry_run"])
        self.assertIsNone(record["delivered"])
        self.assertEqual(record["target"], "https://hc-ping.example/.../fail")
        self.assertTrue(record["body"].startswith("KOD FAIL: slot 6 "))
        self.assertNotIn("slot-check-0001", out.getvalue() + err.getvalue())

    def test_refuses_missing_and_unsafe_urls(self):
        cases = {
            "": "KOD_WATCH_SLOT_URL is not set",
            "http://hc-ping.example/slot": "must be an https:// URL",
            "https://user:secret@hc-ping.example/slot": "without credentials, query or fragment",
            "https://hc-ping.example/slot?x=1": "without credentials, query or fragment",
            "https://hc-ping.example": "must include the check path",
            "https://hc-ping.example/slot/fail": "base ping URL, not its /fail",
        }
        for value, message in cases.items():
            with self.subTest(value=value):
                network = Network()
                environ = dict(ENV, KOD_WATCH_SLOT_URL=value)
                run = self.run_watch("slot", at(6, 12), network=network, environ=environ)
                self.assertEqual(run.code, 2)
                self.assertEqual(network.requests, [])
                self.assertIn(message, run.stderr)
                self.assertIsNone(run.record)

    def test_https_opener_verifies_certificates_and_refuses_redirects(self):
        contexts, built, opened = [], [], []

        class Opener:
            def open(self, request, timeout):
                opened.append((request, timeout))
                return Response(200)

        def https_handler(context):
            contexts.append(context)
            return "https-handler"

        def build_opener(*handlers):
            built.append(handlers)
            return Opener()

        request = urllib.request.Request(SLOT_URL, b"body", method="POST")
        with (
            mock.patch.object(kod_watch.urllib.request, "HTTPSHandler", https_handler),
            mock.patch.object(kod_watch.urllib.request, "build_opener", build_opener),
        ):
            kod_watch.open_https(request, kod_watch.TIMEOUT_SECONDS)
        refuse, handler = built[0]
        self.assertIsInstance(refuse, kod_watch._RefuseRedirect)
        self.assertEqual(handler, "https-handler")
        self.assertEqual(contexts[0].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(contexts[0].check_hostname)
        self.assertEqual(opened, [(request, kod_watch.TIMEOUT_SECONDS)])
        downgrade = "http://hc-ping.example/slot-check-0001"
        self.assertIsNone(refuse.redirect_request(request, None, 302, "Found", {}, downgrade))

    def test_daily_mode_uses_only_the_daily_url(self):
        run = self.run_watch("daily", START, environ={"KOD_WATCH_DAILY_URL": DAILY_URL})
        self.assertEqual(run.requests[0][0].full_url, DAILY_URL)

    def test_never_writes_to_any_kod_path(self):
        self.tree.captured(1, 2, 3, 4, 5)
        self.tree.begin(6)
        write_json(self.tree.schedule / "HALTED.json", self.tree.receipt(6, status="FAILED"))
        before = snapshot(self.root)
        failures = [urllib.error.URLError("down") for _ in range(4)]
        self.run_watch("slot", at(6, 12))
        self.run_watch("slot", at(6, 12), "--dry-run")
        self.run_watch("slot", at(6, 12), network=Network(*failures))
        self.run_watch("slot", at(31, 12))
        self.run_watch("daily", at(6, 30))
        self.run_watch("daily", at(6, 30), "--dry-run")
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(
            sorted(p.name for p in self.tree.schedule.iterdir()),
            ["HALTED.json", "slot-01", "slot-02", "slot-03", "slot-04", "slot-05", "slot-06"],
        )


class DeployedFixtureTests(unittest.TestCase):
    def test_deployed_plan_digests(self):
        deployment = json.loads((FIXTURES / "DEPLOYMENT.json").read_bytes())
        file_digest = hashlib.sha256(PLAN_BYTES).hexdigest()
        self.assertEqual(file_digest, deployment["plan_sha256"])
        self.assertEqual(
            file_digest, "bffe919924e56a48d49e92045f86e3ee4678ac5ae03aad8287ae8d6e6af6af6b"
        )
        # kod-status printed this canonical digest at handoff; observe.py writes it into receipts.
        self.assertEqual(
            kod_watch.receipt_plan_digest(PLAN),
            "693394f0efffc485a0892a4b5b2115454a858ff0d50ff6daeaff7717c7e2cbb9",
        )

    def test_deployed_plan_has_no_problems_before_the_first_slot(self):
        assessment = kod_watch.assess(
            FIXTURES / "observation-plan.json",
            FIXTURES / "no-schedule-yet",
            FIXTURES / "DEPLOYMENT.json",
            START - timedelta(minutes=1),
            kod_watch.GRACE_SECONDS,
        )
        self.assertEqual(assessment.problems, ())
        self.assertEqual(len(assessment.slots), 30)
        self.assertEqual(kod_watch.stamp(assessment.slots[-1].scheduled_at), "2026-11-09T09:00:00Z")


INSTALLED = "/opt/kod/watch/kod_watch.py"
DEPENDENCIES = frozenset(
    "After Before Requires Requisite Wants BindsTo PartOf Upholds Conflicts OnFailure OnSuccess "
    "PropagatesReloadTo ReloadPropagatedFrom".split()
)


def unit(name: str) -> dict[tuple[str, str], list[str]]:
    """Directives of a systemd unit file as (section, key) -> values, in file order."""
    entries, section = {}, None
    for line in (HERE / "systemd" / name).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        key, separator, value = line.partition("=")
        if not separator or section is None:
            raise ValueError(f"{name}: not a directive: {line!r}")
        entries.setdefault((section, key), []).append(value)
    return entries


class UnitFileTests(unittest.TestCase):
    def test_services_run_as_kod_read_only_with_the_environment_file(self):
        for mode in ("slot", "daily"):
            with self.subTest(mode=mode):
                service = unit(f"kod-watch-{mode}.service")
                expected = {
                    "Type": ["oneshot"],
                    "User": ["kod"],
                    "Group": ["kod"],
                    "EnvironmentFile": ["/etc/kod/watch.env"],
                    "ProtectSystem": ["strict"],
                    "ReadOnlyPaths": ["/etc/kod /opt/kod /var/lib/kod"],
                    "NoNewPrivileges": ["true"],
                    "ExecStart": [
                        f"/usr/bin/python3 -I -B {INSTALLED} {mode} --plan {kod_watch.PLAN} "
                        f"--schedule {kod_watch.SCHEDULE} --deployment {kod_watch.DEPLOYMENT}"
                    ],
                }
                for key, values in expected.items():
                    self.assertEqual(service.get(("Service", key)), values, key)
                self.assertNotIn(("Service", "ReadWritePaths"), service)
                read_only = service[("Service", "ReadOnlyPaths")][0].split()
                for path in (kod_watch.PLAN, kod_watch.SCHEDULE, kod_watch.DEPLOYMENT):
                    self.assertTrue(any(path.is_relative_to(root) for root in read_only), path)

    def test_watch_units_never_depend_on_the_observation_scheduler(self):
        for name in sorted(p.name for p in (HERE / "systemd").iterdir()):
            with self.subTest(unit=name):
                for (_, key), values in unit(name).items():
                    if key in DEPENDENCIES:
                        self.assertFalse(any("kod-observe" in v for v in values), (key, values))

    def test_timers(self):
        expected = {
            "slot": "*-*-* 01,05,09,13,17,21:12:00 UTC",
            "daily": "*-*-* 01:30:00 UTC",
        }
        for mode, calendar in expected.items():
            with self.subTest(mode=mode):
                timer = unit(f"kod-watch-{mode}.timer")
                self.assertEqual(timer[("Timer", "OnCalendar")], [calendar])
                self.assertEqual(timer[("Timer", "Unit")], [f"kod-watch-{mode}.service"])
                self.assertEqual(timer[("Timer", "Persistent")], ["true"])
                self.assertEqual(timer[("Install", "WantedBy")], ["timers.target"])

    def test_slot_timer_fires_after_the_slot_it_follows_is_judged(self):
        calendar = unit("kod-watch-slot.timer")[("Timer", "OnCalendar")][0]
        hours_text, minute, second = calendar.split()[1].split(":")
        hours = sorted(int(hour) for hour in hours_text.split(","))
        slots = [datetime.fromisoformat(s.replace("Z", "+00:00")) for s in PLAN["slots"]]
        self.assertEqual(sorted({s.hour for s in slots}), hours)
        self.assertEqual({(s.minute, s.second) for s in slots}, {(0, 0)})
        self.assertEqual({b - a for a, b in zip(hours, hours[1:])}, {4})
        self.assertEqual(kod_watch.SLOT_PERIOD, timedelta(hours=4))
        offset = int(minute) * 60 + int(second)
        self.assertGreater(offset, PLAN["late_after_seconds"] + kod_watch.GRACE_SECONDS)


def snapshot(root: Path) -> dict:
    """Every path below root with its type, mode, size, mtime and content digest."""
    state = {}
    for directory, names, files in os.walk(root):
        for name in sorted(names + files):
            path = Path(directory, name)
            info = path.lstat()
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            relative = str(path.relative_to(root))
            state[relative] = (info.st_mode, info.st_size, info.st_mtime_ns, digest)
    return state


if __name__ == "__main__":
    unittest.main()
