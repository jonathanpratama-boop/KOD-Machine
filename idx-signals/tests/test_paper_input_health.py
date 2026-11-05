"""Display health preserves the frozen US decision rules and all historical data."""

import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from idxsig import cli, paper, paper_book, paper_book_report, paper_account_report
from idxsig import paper_input_health as health
from idxsig.provenance import PKG_ROOT

NOW = datetime(2026, 11, 5, 15, tzinfo=timezone.utc)


def scan(session="2026-11-04", market="US", candidates=None):
    names = ["AAA"] if candidates is None else candidates
    return {"type": "SCAN", "market": market, "session": session,
            "discovered_at": session + "T23:00:00Z", "candidates_ranked": names,
            "result": "NO SIGNAL" if not names else f"{len(names)} CANDIDATE(S)",
            "data": {"not_scanned": 0}}


def event(session="2026-11-04", id="A", cutoff="2026-11-05T14:30:00Z"):
    return {"type": "SPECULATION_SET", "market": "US", "signal_session": session,
            "sealed_at": session + "T23:00:00Z", "entry_cutoff": cutoff, "set_id": id,
            "ticker": "AAA", "record_hash": id + "-hash",
            "protocol": {"id": "KOD-SPEC-REGISTER-v1.1"}}


def forecast(session="2026-11-04", id="A"):
    return {"type": "LEARNER3_FORECAST", "market": "US", "family": "SPEC_US",
            "learner": "LEARNER-v2.4", "protocol": {"id": "KOD-LEARNER-v2.4"},
            "signal_session": session, "made_at": session + "T23:05:00Z", "set_id": id,
            "entry_cutoff": "2026-11-05T14:30:00Z", "set_record_hash": id + "-hash"}


class InputHealth(unittest.TestCase):
    def status(self, **overrides):
        args = dict(scans=[scan()], sets=[event()], forecasts=[forecast()], now=NOW)
        args.update(overrides)
        return health.summarize(**args)

    def test_missing_config_is_explicit_execution_evidence_and_clears(self):
        self.assertEqual(self.status(sec_contact_configured=False)["state"], "BLOCKED_CONFIGURATION")
        self.assertEqual(self.status(sec_contact_configured=True)["state"], "CURRENT")
        self.assertIsNone(self.status()["sec_contact_configured"])

    def test_configuration_values_never_returned(self):
        sentinel = "private-contact-not-for-output"
        self.assertTrue(health.sec_configured({"KOD_SEC_CONTACT": sentinel}))
        text = health.banner(self.status(sec_contact_configured=True))
        self.assertNotIn(sentinel, text)
        with self.assertRaises(ValueError):
            self.status(sec_contact_configured=sentinel)

    def test_configuration_matches_override_precedence(self):
        from idxsig.us_actions import DEFAULT_USER_AGENT
        self.assertFalse(health.sec_configured({"KOD_SEC_CONTACT": "  "}))
        self.assertFalse(health.sec_configured({"IDXSIG_SEC_USER_AGENT": DEFAULT_USER_AGENT, "KOD_SEC_CONTACT": "present"}))
        self.assertTrue(health.sec_configured({"IDXSIG_SEC_USER_AGENT": "declared-contact"}))

    def test_fresh_idx_and_crypto_cannot_hide_stale_us_scan(self):
        s = self.status(scans=[scan("2026-10-30"), scan(market="IDX"), scan(market="CRYPTO")])
        self.assertEqual(s["state"], "STALE_INPUT")
        self.assertEqual(s["last_us_scan_session"], "2026-10-30")

    def test_latest_compatible_forecast_only(self):
        incompatible = []
        for change in ({"learner": "LEARNER-v2.3"}, {"market": "IDX"},
                       {"protocol": {"id": "KOD-LEARNER-v2.2"}}, {"family": "SPEC_IDX"},
                       {"type": "LEARNER2_FORECAST"}, {"made_at": "2026-11-06T00:00:00Z"}):
            incompatible.append({**forecast(), **change})
        s = self.status(forecasts=[forecast("2026-10-30", "OLD"), *incompatible])
        self.assertEqual(s["latest_forecast_session"], "2026-10-30")
        self.assertEqual(s["compatible_forecast_count"], 1)
        self.assertEqual(s["state"], "STALE_INPUT")

    def test_pending_and_missed_cutoffs_separate(self):
        before = self.status(forecasts=[], now=NOW.replace(hour=14, minute=29))
        self.assertEqual(before["state"], "WAITING_FORECAST")
        self.assertEqual((before["pending_forecast_count"], before["missed_forecast_count"]), (1, 0))
        at = self.status(forecasts=[], now=NOW.replace(hour=14, minute=30))
        self.assertEqual(at["state"], "STALE_INPUT")
        self.assertEqual((at["pending_forecast_count"], at["missed_forecast_count"]), (0, 1))

    def test_historical_misses_preserved_after_current_forecast_recovers(self):
        s = self.status(sets=[event(), event("2026-11-02", "OLD", "2026-11-03T14:30:00Z")])
        self.assertEqual(s["state"], "CURRENT")
        self.assertEqual(s["missed_forecast_count"], 1)
        self.assertIn("historical sets missed before cutoff: 1", health.banner(s))

    def test_no_opportunity_requires_actual_empty_us_scan(self):
        s = self.status(scans=[scan(candidates=[])], sets=[], forecasts=[])
        self.assertEqual(s["state"], "CURRENT_NO_OPPORTUNITY")
        self.assertEqual(self.status(sets=[], forecasts=[])["state"], "NO_FORECAST")
        self.assertEqual(self.status(scans=[], sets=[], forecasts=[])["state"], "UNAVAILABLE")

    def test_partial_empty_scan_is_not_no_opportunity(self):
        partial = scan(candidates=[])
        partial["data"]["not_scanned"] = 20
        self.assertEqual(self.status(scans=[partial], sets=[], forecasts=[])["state"], "PARTIAL_INPUT")

    def test_missing_register_candidates_cannot_report_current(self):
        s = self.status(scans=[scan(candidates=["AAA", "BBB"])])
        self.assertEqual(s["state"], "PARTIAL_INPUT")
        self.assertEqual(s["candidates_without_eligible_set_count"], 1)

    def test_invalid_cutoff_does_not_imply_pending(self):
        s = self.status(sets=[{**event(), "entry_cutoff": "invalid"}], forecasts=[])
        self.assertEqual(s["state"], "UNAVAILABLE")
        self.assertEqual(s["pending_forecast_count"], 0)

    def test_late_or_unbound_forecast_cannot_clear_missing_input(self):
        for change in ({"made_at": "2026-11-05T14:30:00Z"}, {"set_record_hash": "wrong"}):
            self.assertEqual(self.status(forecasts=[{**forecast(), **change}])["state"], "STALE_INPUT")

    def test_weekend_not_automatically_stale(self):
        now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        self.assertEqual(health.expected_session(now), "2026-11-05")
        s = self.status(now=now, scans=[scan("2026-11-06", candidates=[])], sets=[], forecasts=[])
        self.assertEqual(s["state"], "CURRENT_NO_OPPORTUNITY")

    def test_future_scan_and_future_set_do_not_create_knowledge(self):
        s = self.status(scans=[scan("2026-11-06")], sets=[event("2026-11-06")], forecasts=[])
        self.assertEqual(s["state"], "UNAVAILABLE")
        self.assertEqual(s["pending_forecast_count"], 0)

    def test_read_failure_cannot_be_empty_success(self):
        s = self.status(read_errors=["learner_v3.jsonl: unreadable"])
        self.assertEqual(s["state"], "UNAVAILABLE")

    def test_no_timezone_rejected(self):
        with self.assertRaises(ValueError):
            self.status(now=NOW.replace(tzinfo=None))

    def test_summary_never_mutates_inputs(self):
        args = dict(scans=[scan()], sets=[event()], forecasts=[forecast()], now=NOW)
        before = copy.deepcopy(args)
        health.summarize(**args)
        self.assertEqual(args, before)

    def test_render_is_pure_and_does_not_infer_cloud_config_from_local_env(self):
        with mock.patch.object(health, "load", side_effect=AssertionError("unexpected I/O")):
            a = paper_account_report.render([])
            b = paper_account_report.render([])
            c = paper_book_report.render([])
        self.assertEqual(a, b)
        self.assertIn("NOT_ASSESSED", a)
        self.assertIn("NOT_ASSESSED", c)
        self.assertNotIn("BLOCKED_CONFIGURATION", a)

    def test_both_reports_expose_same_warning_before_old_totals(self):
        state = self.status(sec_contact_configured=False)
        for text in (paper_account_report.render([], input_health=state),
                     paper_book_report.render([], input_health=state)):
            self.assertIn("BLOCKED_CONFIGURATION", text)
            self.assertLess(text.index("US forecast input health"), text.index("The three plain answers"))

    def test_frozen_sources_and_protocols_unchanged(self):
        for name in ("PAPER_BOOK_v1", "PAPER_ACCOUNT_v1"):
            protocol = json.loads((PKG_ROOT / "research" / name / "protocol.json").read_text())
            for path, expected in protocol["pins"].items():
                target = PKG_ROOT / path
                if target.exists():
                    self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), expected, path)

    def test_cli_book_report_uses_new_renderer_and_explicit_runtime_presence(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "PAPER_BOOK.md"
            state = self.status(sec_contact_configured=False)
            with mock.patch.object(paper_book, "REPORT", target), mock.patch.object(paper_book, "trades", return_value=[]), \
                 mock.patch.object(health, "load", return_value=state) as load, mock.patch.dict("os.environ", {}, clear=True), \
                 redirect_stdout(io.StringIO()):
                cli.main(["paper-book-report"])
            load.assert_called_once_with(sec_contact_configured=False)
            self.assertIn("BLOCKED_CONFIGURATION", target.read_text())

    def test_no_plan_refreshes_warning_without_appending_a_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "PAPER_BOOK.md"
            state = self.status(sec_contact_configured=False)
            with mock.patch.object(paper_book, "REPORT", target), mock.patch.object(paper_book, "trades", return_value=[]), \
                 mock.patch.object(paper_book, "plan_records", return_value=[]), \
                 mock.patch.object(health, "load", return_value=state), \
                 mock.patch.object(paper, "append", side_effect=AssertionError("must not append")), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["paper-book-plan"]), 0)
            self.assertIn("BLOCKED_CONFIGURATION", target.read_text())


if __name__ == "__main__":
    unittest.main()
