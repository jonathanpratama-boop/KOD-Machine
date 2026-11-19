"""Prospective admission, paired-account and missing-data regression checks."""

from copy import deepcopy
from decimal import Decimal
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig import guidance_margin_trial as trial
from idxsig.guidance_revision import moment


def facts(*, margin_up=True):
    def document(name, revenue, margin, published, received):
        raw = f"Revenue {revenue}; operating margin {margin}%."

        def metric(value, unit):
            literal = str(value)
            start = raw.index(literal)
            return {
                "form": "point",
                "unit": unit,
                "qualifier": "exact",
                "point": {"value": value, "start": start, "end": start + len(literal)},
            }

        return {
            "issuer_cik": "1234",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
            "period_kind": "FULL_YEAR",
            "basis": "GAAP",
            "definition_id": "gaap",
            "perimeter_id": "unchanged",
            "source": {
                "id": name,
                "url": "https://example.invalid/" + name,
                "raw_text": raw,
                "sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "locator": "Outlook",
                "representation": "retained_excerpt",
                "published_at": published,
                "received_at": received,
            },
            "revenue": metric(revenue, "USD_MILLIONS"),
            "operating_margin": metric(margin, "PERCENT"),
        }

    return {
        "schema_version": trial.SCHEMA,
        "purpose": "prospective",
        "event_id": "event-1",
        "current": document(
            "new", 120, 12 if margin_up else 8, "2026-11-16T21:11:00Z", "2026-11-16T21:12:00Z"
        ),
        "prior": document("old", 100, 10, "2026-08-01T12:00:00Z", "2026-11-16T21:12:00Z"),
        "external": {
            "attestor": "reviewer",
            "evidence_notes": "Synthetic unit-test source only",
            "source_authenticity": "VERIFIED",
            "metric_binding": "VERIFIED",
            "prior_completeness": "VERIFIED",
            "basis_comparable": "VERIFIED",
            "perimeter_comparable": "VERIFIED",
            "latest_prior_source_id": "old",
        },
        "clocks": {"extracted_at": "2026-11-16T21:13:00Z", "decision_at": "2026-11-16T21:14:00Z"},
    }


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "trial.jsonl"
        self.at("2026-11-16T21:10:00Z", trial.initialize, self.path)

    def at(self, timestamp, fn, *args, **kwargs):
        with patch.object(trial, "_clock", return_value=moment(timestamp)):
            return fn(*args, **kwargs)

    def admit(self, pair=None):
        return self.at(
            "2026-11-16T21:15:00Z",
            trial.admit,
            self.path,
            pair or facts(),
            ticker="TEST",
            reviewer="reviewer",
        )

    def bar(self, session="2026-11-17", price=110):
        return {
            "session": session,
            "open": 100,
            "high": max(100, price) + 1,
            "low": min(100, price) - 1,
            "close": price,
            "volume": 100000,
            "ticker": "TEST",
            "issuer_cik": "0001234",
            "provider": "synthetic",
            "fetched_at": session + "T21:05:00Z",
            "corporate_action_clear": True,
        }

    def observe(self, bar=None, at=None):
        bar = bar or self.bar()
        return self.at(
            at or bar["session"] + "T21:06:00Z",
            trial.observe_bar,
            self.path,
            event_id="event-1",
            bar=bar,
        )

    def test_initialization_dedup_and_corruption_fail_closed(self):
        self.at("2026-11-16T21:10:01Z", trial.initialize, self.path)
        self.assertEqual(len(trial.records(self.path)), 1)
        self.path.write_text(self.path.read_text().replace('"10000"', '"90000"'))
        with self.assertRaisesRegex(ValueError, "corrupt"):
            trial.status(self.path)

    def test_explicit_schema_missing_review_and_recent_cohort(self):
        dev = facts()
        dev["purpose"] = "development"
        with self.assertRaisesRegex(ValueError, "prospective"):
            self.admit(dev)
        missing = facts()
        missing["external"]["prior_completeness"] = "UNKNOWN"
        excluded = self.admit(missing)
        self.assertEqual(excluded["status"], "EXCLUDED")
        self.assertEqual(trial.status(self.path)["excluded"], 1)
        another = facts()
        another["event_id"] = "event-2"
        another["current"]["source"]["published_at"] = "2026-11-13T12:00:00Z"
        row = self.admit(another)
        self.assertEqual(row["status"], "ADMITTED")
        self.assertEqual(row["cohort"], "INITIAL_RECENT")
        self.assertEqual(row["schedule"]["entry_session"], "2026-11-17")

    def test_old_or_future_sources_not_admitted(self):
        old = facts()
        old["current"]["source"]["published_at"] = "2026-10-01T12:00:00Z"
        self.assertEqual(self.admit(old)["status"], "EXCLUDED")
        future = facts()
        future["event_id"] = "future"
        future["current"]["source"]["published_at"] = "2026-11-20T12:00:00Z"
        future["current"]["source"]["received_at"] = "2026-11-20T12:01:00Z"
        future["clocks"] = {
            "extracted_at": "2026-11-20T12:02:00Z",
            "decision_at": "2026-11-20T12:03:00Z",
        }
        with self.assertRaisesRegex(ValueError, "future"):
            self.admit(future)

    def test_both_arms_have_identical_entry_costs_and_pnl(self):
        event = self.admit()
        self.assertEqual(event["arms"], {"revenue": True, "revenue_and_margin": True})
        first = self.observe()
        self.assertEqual(first["pnl_usd"]["revenue"], first["pnl_usd"]["revenue_and_margin"])
        self.assertLess(Decimal(first["pnl_usd"]["revenue"]), Decimal("100"))
        self.assertEqual(self.observe()["record_hash"], first["record_hash"])
        self.assertEqual(trial.status(self.path)["horizons"]["1"]["paired_events"], 1)
        cohort = trial.status(self.path)["cohorts"]["NEW_RELEASE"]["horizons"]["1"]
        self.assertEqual(
            cohort["net_pnl_usd"]["revenue"], cohort["net_pnl_usd"]["revenue_and_margin"]
        )

    def test_status_counts_only_admitted_events_with_known_arm_choices(self):
        rows = trial.records(self.path)
        variants = [
            ("ADMITTED", {"revenue": True, "revenue_and_margin": True}),
            ("ADMITTED", {"revenue": True, "revenue_and_margin": False}),
            ("EXCLUDED", {"revenue": True, "revenue_and_margin": False}),
            ("ADMITTED", {}),
        ]
        rows.extend(
            {
                "kind": "ADMISSION",
                "status": status,
                "arms": arms,
                "cohort": "NEW_RELEASE",
                "event_id": str(i),
                "recorded_at": rows[0]["recorded_at"],
            }
            for i, (status, arms) in enumerate(variants)
        )
        with patch.object(trial, "records", return_value=rows):
            result = trial.status(self.path)
        self.assertEqual(result["admitted"], 3)
        self.assertEqual(result["informative_admissions"], 1)
        self.assertEqual(result["matching_admissions"], 1)
        self.assertEqual(result["filled_pairs"], 0)

    def test_margin_arm_cash_and_session_horizons_do_not_count_weekends(self):
        self.admit(facts(margin_up=False))
        self.observe(self.bar(price=90))
        third = self.observe(self.bar("2026-11-19", 95))
        fifth = self.observe(self.bar("2026-11-23", 96))
        self.assertEqual(third["descriptive_horizon"], 3)
        self.assertEqual(fifth["descriptive_horizon"], 5)
        self.assertEqual(fifth["pnl_usd"]["revenue_and_margin"], "0")
        self.assertLess(Decimal(fifth["pnl_usd"]["revenue"]), 0)

    def test_future_incomplete_stale_and_identity_mismatched_bars_fail(self):
        self.admit()
        for key, value in (
            ("ticker", "WRONG"),
            ("corporate_action_clear", False),
            ("high", 2),
            ("fetched_at", "2026-11-17T20:55:00Z"),
        ):
            bar = self.bar()
            bar[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.observe(bar)
        with self.assertRaisesRegex(ValueError, "current"):
            self.observe(at="2026-11-18T14:00:00Z")
        bar = self.bar()
        bar["fetched_at"] = "2026-11-18T21:05:00Z"
        with self.assertRaisesRegex(ValueError, "backfill"):
            self.observe(bar, at="2026-11-18T21:06:00Z")

    def test_missing_entry_is_recorded_instead_of_buying_a_later_open(self):
        self.admit()
        result = self.observe(self.bar("2026-11-18"))
        self.assertEqual(result["kind"], "MISSED_ENTRY")
        self.assertEqual(trial.status(self.path)["filled_pairs"], 0)
        self.assertEqual(trial.status(self.path)["missed_entries"], 1)

    def test_duplicate_facts_or_price_changes_cannot_rewrite_history(self):
        self.admit()
        same = self.admit()
        self.assertEqual(same["id"], "event:event-1")
        changed = deepcopy(facts())
        changed["external"]["evidence_notes"] = "changed"
        with self.assertRaisesRegex(ValueError, "sealed"):
            self.admit(changed)
        self.observe()
        with self.assertRaisesRegex(ValueError, "different bar"):
            self.observe(self.bar(price=111))

    def test_terminal_slot_closes_after_twenty_exchange_sessions(self):
        event = self.admit()
        self.observe()
        terminal_day = event["schedule"]["time_exit_session"]
        outcome = self.observe(self.bar(terminal_day))
        self.assertEqual(outcome["kind"], "CLOSE")
        self.assertEqual(outcome["held_sessions"], 20)
        self.assertFalse(outcome["missed_terminal_close"])
        self.assertEqual(trial.status(self.path)["closed_pairs"], 1)

    def test_realized_losses_reduce_shared_available_cash(self):
        event = self.admit(facts(margin_up=False))
        self.observe()
        self.observe(self.bar(event["schedule"]["time_exit_session"], 50))
        admitted = []
        for index in range(10):
            pair = facts()
            pair["event_id"] = "new-" + str(index)
            for which in ("current", "prior"):
                pair[which]["issuer_cik"] = str(2000 + index)
                pair[which]["source"]["received_at"] = "2026-12-16T21:12:00Z"
            pair["current"]["source"]["published_at"] = "2026-12-16T21:11:00Z"
            pair["clocks"] = {
                "extracted_at": "2026-12-16T21:13:00Z",
                "decision_at": "2026-12-16T21:14:00Z",
            }
            admitted.append(
                self.at(
                    "2026-12-16T21:15:00Z",
                    trial.admit,
                    self.path,
                    pair,
                    ticker="TEST",
                    reviewer="reviewer",
                )
            )
        self.assertEqual(sum(row["status"] == "ADMITTED" for row in admitted), 9)
        self.assertIn("insufficient shared paper cash", admitted[-1]["reasons"][0])

    def test_late_terminal_close_is_not_a_twenty_session_result(self):
        self.admit()
        self.observe()
        result = self.observe(self.bar("2026-12-16"))
        self.assertEqual(result["kind"], "CLOSE")
        self.assertTrue(result["missed_terminal_close"])
        report = trial.status(self.path)
        self.assertEqual(report["horizons"]["20"]["paired_events"], 0)
        self.assertEqual(report["missing_terminal_outcomes"], 1)


if __name__ == "__main__":
    unittest.main()
