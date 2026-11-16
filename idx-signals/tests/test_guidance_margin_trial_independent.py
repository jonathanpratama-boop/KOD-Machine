"""Independent counterexamples for the prospective comparison's evidence boundaries."""

from decimal import Decimal
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig import guidance_margin_trial as trial
from idxsig.guidance_revision import moment


def pair(index=0, *, margin=12, day="2026-11-16"):
    def doc(identity, revenue, operating_margin, published):
        raw = (
            f"Annual outlook: USD millions revenue {revenue}; operating margin {operating_margin}%."
        )

        def metric(value, unit):
            token = str(value)
            start = raw.rindex(token)
            return {
                "form": "point",
                "qualifier": "exact",
                "unit": unit,
                "point": {"value": value, "start": start, "end": start + len(token)},
            }

        return {
            "issuer_cik": str(9000 + index),
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
            "period_kind": "FULL_YEAR",
            "basis": "GAAP",
            "definition_id": "GAAP operating income",
            "perimeter_id": "same consolidated group",
            "revenue": metric(revenue, "USD_MILLIONS"),
            "operating_margin": metric(operating_margin, "PERCENT"),
            "source": {
                "id": identity,
                "url": "https://example.invalid/synthetic",
                "locator": "Annual outlook",
                "representation": "retained_excerpt",
                "raw_text": raw,
                "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "published_at": published,
                "received_at": day + "T21:03:00Z",
            },
        }

    return {
        "schema_version": trial.SCHEMA,
        "purpose": "prospective",
        "event_id": f"independent-{index}",
        "prior": doc(f"prior-{index}", 100, 10, "2026-08-01T12:00:00Z"),
        "current": doc(f"current-{index}", 102, margin, day + "T21:02:00Z"),
        "external": {
            "attestor": "independent synthetic test",
            "evidence_notes": "No real company",
            "source_authenticity": "VERIFIED",
            "metric_binding": "VERIFIED",
            "prior_completeness": "VERIFIED",
            "basis_comparable": "VERIFIED",
            "perimeter_comparable": "VERIFIED",
            "latest_prior_source_id": f"prior-{index}",
        },
        "clocks": {"extracted_at": day + "T21:04:00Z", "decision_at": day + "T21:05:00Z"},
    }


class IndependentTrialCounterexamples(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.jsonl"
        self.at("2026-11-16T21:00:00Z", trial.initialize, self.path)

    def at(self, clock, fn, *args, **kwargs):
        with patch.object(trial, "_clock", return_value=moment(clock)):
            return fn(*args, **kwargs)

    def admit(self, value, clock="2026-11-16T21:06:00Z"):
        return self.at(
            clock,
            trial.admit,
            self.path,
            value,
            ticker="TEST" + value["current"]["issuer_cik"],
            reviewer="independent test",
        )

    def bar(self, event, day, close=90, fetched=None):
        return {
            "session": day,
            "open": 100,
            "high": max(101, close),
            "low": min(89, close),
            "close": close,
            "volume": 100000,
            "provider": "synthetic",
            "fetched_at": fetched or day + "T21:20:00Z",
            "corporate_action_clear": True,
            "ticker": event["ticker"],
            "issuer_cik": event["issuer_cik"],
        }

    def observe(self, event, day, close=90):
        return self.at(
            day + "T21:21:00Z",
            trial.observe_bar,
            self.path,
            event_id=event["event_id"],
            bar=self.bar(event, day, close),
        )

    def test_deleting_required_margin_cannot_turn_a_case_into_evidence(self):
        value = pair()
        del value["current"]["operating_margin"]
        result = self.admit(value)
        self.assertEqual(result["status"], "EXCLUDED")
        self.assertEqual(result["qualification"]["status"], "MISSING")
        status = trial.status(self.path)
        self.assertEqual(status["admitted"], 0)
        self.assertTrue(all(row["paired_events"] == 0 for row in status["horizons"].values()))

    def test_future_review_and_open_bars_cannot_be_scored(self):
        value = pair()
        value["clocks"]["decision_at"] = "2026-11-18T00:00:00Z"
        with self.assertRaises(ValueError):
            self.admit(value)
        self.assertEqual(len(trial.records(self.path)), 1)
        event = self.admit(pair())
        with self.assertRaises(ValueError):
            self.at(
                "2026-11-17T19:00:00Z",
                trial.observe_bar,
                self.path,
                event_id=event["event_id"],
                bar=self.bar(event, "2026-11-17", fetched="2026-11-17T18:59:00Z"),
            )
        self.assertEqual(trial.status(self.path)["filled_pairs"], 0)

    def test_generator_based_cohort_totals_keep_both_arms_and_separate_recent(self):
        new = self.admit(pair())
        recent_pair = pair(1, margin=8)
        recent_pair["current"]["source"]["published_at"] = "2026-11-13T12:00:00Z"
        recent = self.admit(recent_pair)
        self.observe(new, "2026-11-17")
        self.observe(recent, "2026-11-17")
        results = trial.status(self.path)
        fresh = results["cohorts"]["NEW_RELEASE"]["horizons"]["1"]
        older = results["cohorts"]["INITIAL_RECENT"]["horizons"]["1"]
        self.assertEqual(fresh["paired_events"], 1)
        self.assertEqual(
            fresh["net_pnl_usd"]["revenue"], fresh["net_pnl_usd"]["revenue_and_margin"]
        )
        self.assertLess(Decimal(fresh["net_pnl_usd"]["revenue_and_margin"]), 0)
        self.assertEqual(older["paired_events"], 1)
        self.assertEqual(Decimal(older["net_pnl_usd"]["revenue_and_margin"]), 0)
        self.assertEqual(results["horizons"]["1"]["paired_events"], 2)

    def test_realized_loss_cannot_be_recycled_as_full_thousand_dollar_slot(self):
        events = [self.admit(pair(index)) for index in range(10)]
        self.observe(events[0], "2026-11-17")
        final = events[0]["schedule"]["time_exit_session"]
        self.observe(events[0], final)
        value = pair(20, day=final)
        admitted = self.admit(value, clock=final + "T22:00:00Z")
        self.assertEqual(admitted["status"], "EXCLUDED")
        self.assertTrue(any("cash" in reason for reason in admitted["reasons"]))

    def test_late_exit_does_not_manufacture_a_twenty_session_result(self):
        event = self.admit(pair())
        self.observe(event, "2026-11-17")
        import exchange_calendars as xc

        calendar = xc.get_calendar("XNYS")
        late = calendar.next_session(event["schedule"]["time_exit_session"]).date().isoformat()
        outcome = self.observe(event, late)
        self.assertTrue(outcome["missed_terminal_close"])
        status = trial.status(self.path)
        self.assertEqual(status["missing_terminal_outcomes"], 1)
        self.assertEqual(status["horizons"]["20"]["paired_events"], 0)


if __name__ == "__main__":
    unittest.main()
