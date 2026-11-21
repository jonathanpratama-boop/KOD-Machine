"""Behavioral acceptance tests authored from CONTRACT.md, not implementation.

All synthetic records below are fictional development examples. No network,
provider calls, trade decisions, market outcomes or historical fills are used.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest

from idxsig.guidance_margin_facts import qualify, record_revision


def synthetic_document(
    source_id,
    published,
    received,
    *,
    current=False,
    revenue_form="range",
    revenue_tokens=None,
    result_kind="operating_profit",
    result_form="range",
    result_tokens=None,
):
    """Build exact character spans independently, with a multibyte prefix."""
    text = "µ Fictional full-year guidance; USD millions unless percent.\n"

    def metric(label, form, tokens, unit):
        nonlocal text
        text += label + ": "
        keys = {
            "point": ("point",),
            "range": ("low", "high"),
            "center_spread": ("center", "spread"),
        }[form]
        result = {"form": form, "unit": unit, "qualifier": "exact"}
        for index, (key, (literal, value)) in enumerate(zip(keys, tokens)):
            if index:
                text += " to " if form == "range" else " plus/minus "
            start = len(text)
            text += literal
            result[key] = {"value": value, "start": start, "end": len(text)}
        text += "\n"
        return result

    if revenue_tokens is None:
        revenue_tokens = (
            [("$1,100", 1100), ("$1,300", 1300)] if current else [("$900", 900), ("$1,100", 1100)]
        )
    if result_tokens is None:
        result_tokens = [("$132", 132), ("$156", 156)] if current else [("$90", 90), ("$110", 110)]
    revenue = metric("Revenue", revenue_form, revenue_tokens, "USD_MILLIONS")
    profit = metric(
        result_kind,
        result_form,
        result_tokens,
        "PERCENT" if result_kind == "operating_margin" else "USD_MILLIONS",
    )
    return {
        "issuer_cik": "0001234567",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "period_kind": "FULL_YEAR",
        "basis": "GAAP",
        "definition_id": "US-GAAP-no-adjustments",
        "perimeter_id": "issuer-consolidated-no-change",
        "source": {
            "id": source_id,
            "url": "https://example.invalid/" + source_id,
            "raw_text": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "locator": "synthetic outlook table",
            "representation": "retained_excerpt",
            "published_at": published,
            "received_at": received,
        },
        "revenue": revenue,
        result_kind: profit,
    }


def synthetic_pair():
    return {
        "schema_version": "guidance-margin-facts/v1",
        "event_id": "fictional-event-1",
        "purpose": "development",
        "prior": synthetic_document("prior-doc", "2026-08-01T12:00:00Z", "2026-08-01T12:00:05Z"),
        "current": synthetic_document(
            "current-doc", "2026-11-01T12:00:00Z", "2026-11-01T12:00:05Z", current=True
        ),
        "external": {
            "attestor": "synthetic-reviewer",
            "source_authenticity": "VERIFIED",
            "metric_binding": "VERIFIED",
            "prior_completeness": "VERIFIED",
            "latest_prior_source_id": "prior-doc",
            "basis_comparable": "VERIFIED",
            "perimeter_comparable": "VERIFIED",
            "evidence_notes": "Fictional test evidence only, no real issuer or historical receipt claim.",
        },
        "clocks": {"extracted_at": "2026-11-01T12:00:10Z", "decision_at": "2026-11-01T12:00:15Z"},
    }


def at_path(obj, path):
    for part in path.split("."):
        obj = obj[part]
    return obj


def change(obj, path, value):
    parts = path.split(".")
    parent = obj
    for part in parts[:-1]:
        parent = parent[part]
    parent[parts[-1]] = value


def remove(obj, path):
    parts = path.split(".")
    parent = obj
    for part in parts[:-1]:
        parent = parent[part]
    del parent[parts[-1]]


class QualificationTests(unittest.TestCase):
    def assert_status(self, pair, expected):
        result = qualify(pair)
        self.assertEqual(result["status"], expected, result)
        self.assertIsInstance(result["reasons"], list)
        if expected != "FACTS_READY":
            self.assertIsNone(result["derived"], result)
            self.assertTrue(result["reasons"], result)
        return result

    def test_independent_arithmetic_and_no_input_mutation(self):
        pair = synthetic_pair()
        before = deepcopy(pair)
        result = self.assert_status(pair, "FACTS_READY")
        self.assertEqual(pair, before)
        expected = {
            "current_revenue_midpoint": 1200,
            "prior_revenue_midpoint": 1000,
            "current_margin_midpoint_pct": 12,
            "prior_margin_midpoint_pct": 10,
            "revenue_revision_pct": 20,
            "margin_revision_pp": 2,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(result["derived"][key], value, places=9)

    def test_missing_required_evidence_never_passes(self):
        paths = [
            "schema_version",
            "event_id",
            "purpose",
            "current",
            "prior",
            "external",
            "clocks",
            "current.issuer_cik",
            "current.period_start",
            "current.period_end",
            "current.period_kind",
            "current.basis",
            "current.definition_id",
            "current.perimeter_id",
            "current.source",
            "current.source.id",
            "current.source.url",
            "current.source.raw_text",
            "current.source.sha256",
            "current.source.locator",
            "current.source.representation",
            "current.source.published_at",
            "current.source.received_at",
            "current.revenue",
            "current.operating_profit",
            "current.revenue.form",
            "current.revenue.unit",
            "current.revenue.qualifier",
            "current.revenue.low",
            "current.revenue.high",
            "current.revenue.low.value",
            "current.revenue.low.start",
            "current.revenue.low.end",
            "external.attestor",
            "external.source_authenticity",
            "external.metric_binding",
            "external.prior_completeness",
            "external.latest_prior_source_id",
            "external.basis_comparable",
            "external.perimeter_comparable",
            "external.evidence_notes",
            "clocks.extracted_at",
            "clocks.decision_at",
        ]
        for path in paths:
            with self.subTest(path=path):
                pair = synthetic_pair()
                remove(pair, path)
                self.assert_status(pair, "MISSING")

    def test_empty_required_text_is_missing(self):
        for path in (
            "event_id",
            "current.definition_id",
            "current.perimeter_id",
            "current.source.id",
            "current.source.url",
            "current.source.locator",
            "external.attestor",
            "external.evidence_notes",
        ):
            with self.subTest(path=path):
                pair = synthetic_pair()
                change(pair, path, "")
                self.assert_status(pair, "MISSING")

    def test_known_incompatibilities_take_precedence(self):
        changes = {
            "current.issuer_cik": "222",
            "current.period_start": "2026-02-01",
            "current.period_end": "2027-12-31",
            "current.period_kind": "QUARTER",
            "current.basis": "ADJUSTED",
            "current.definition_id": "recast-definition",
            "current.perimeter_id": "post-acquisition",
            "current.revenue.unit": "EUR_MILLIONS",
            "current.operating_profit.unit": "USD_THOUSANDS",
            "current.revenue.qualifier": "ambiguous",
            "external.latest_prior_source_id": "different-prior",
            "external.basis_comparable": "FAILED",
            "external.perimeter_comparable": "FAILED",
        }
        for path, value in changes.items():
            with self.subTest(path=path):
                pair = synthetic_pair()
                change(pair, path, value)
                self.assert_status(pair, "INCOMPARABLE")

    def test_no_substitution_of_other_profit_metrics(self):
        for substitute in ("eps", "ebitda", "net_income", "gross_profit", "fcf", "segment_noi"):
            with self.subTest(substitute=substitute):
                pair = synthetic_pair()
                pair["current"][substitute] = pair["current"].pop("operating_profit")
                self.assert_status(pair, "INCOMPARABLE")

    def test_external_checks_cannot_be_silently_assumed(self):
        for key in (
            "source_authenticity",
            "metric_binding",
            "prior_completeness",
            "basis_comparable",
            "perimeter_comparable",
        ):
            with self.subTest(key=key):
                pair = synthetic_pair()
                pair["external"][key] = "UNKNOWN"
                self.assert_status(pair, "UNVERIFIED")
        for key in ("source_authenticity", "metric_binding", "prior_completeness"):
            with self.subTest(failed=key):
                pair = synthetic_pair()
                pair["external"][key] = "FAILED"
                self.assert_status(pair, "UNVERIFIED")

    def test_blocker_precedence_and_retention(self):
        pair = synthetic_pair()
        pair["current"]["period_kind"] = "QUARTER"
        del pair["external"]["attestor"]
        pair["external"]["prior_completeness"] = "UNKNOWN"
        result = self.assert_status(pair, "INCOMPARABLE")
        joined = " ".join(result["reasons"]).lower()
        self.assertTrue("period" in joined or "full-year" in joined, joined)
        for term in ("attestor", "prior"):
            self.assertIn(term, joined)
        pair["current"]["period_kind"] = "FULL_YEAR"
        self.assert_status(pair, "MISSING")

    def test_source_integrity_tampering_fails(self):
        edits = {
            "current.source.sha256": "0" * 64,
            "current.source.raw_text": "different source contents",
            "current.revenue.low.start": -1,
            "current.revenue.low.end": 999999,
            "current.revenue.low.value": 1101,
        }
        for path, value in edits.items():
            with self.subTest(path=path):
                pair = synthetic_pair()
                change(pair, path, value)
                with self.assertRaises(ValueError):
                    qualify(pair)

    def test_unicode_character_offsets_not_byte_offsets(self):
        pair = synthetic_pair()
        pair["current"] = synthetic_document(
            "current-doc",
            "2026-11-01T12:00:00Z",
            "2026-11-01T12:00:05Z",
            current=True,
            revenue_tokens=[("1100", 1100), ("1300", 1300)],
        )
        self.assert_status(pair, "FACTS_READY")
        for key in ("start", "end"):
            pair["current"]["revenue"]["low"][key] += 1
        with self.assertRaises(ValueError):
            qualify(pair)

    def test_numeric_integrity_and_enums(self):
        for value in (True, False, float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value):
                pair = synthetic_pair()
                pair["current"]["revenue"]["low"]["value"] = value
                with self.assertRaises(ValueError):
                    qualify(pair)
        for path, value in (
            ("schema_version", "unknown/v9"),
            ("purpose", "live"),
            ("current.revenue.form", "verbal-growth"),
            ("current.revenue.qualifier", "sure"),
            ("external.metric_binding", "LIKELY"),
        ):
            with self.subTest(path=path):
                pair = synthetic_pair()
                change(pair, path, value)
                with self.assertRaises(ValueError):
                    qualify(pair)
        for pair in (None, [], "not an object"):
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                qualify(pair)

    def test_reversed_range_and_duplicate_profit_representation_fail(self):
        pair = synthetic_pair()
        pair["current"]["revenue"]["low"], pair["current"]["revenue"]["high"] = (
            pair["current"]["revenue"]["high"],
            pair["current"]["revenue"]["low"],
        )
        with self.assertRaises(ValueError):
            qualify(pair)
        pair = synthetic_pair()
        pair["current"]["operating_margin"] = deepcopy(pair["current"]["operating_profit"])
        with self.assertRaises(ValueError):
            qualify(pair)

    def test_zero_or_negative_revenue_is_incomparable(self):
        for value in (0, -100):
            with self.subTest(value=value):
                pair = synthetic_pair()
                pair["current"] = synthetic_document(
                    "current-doc",
                    "2026-11-01T12:00:00Z",
                    "2026-11-01T12:00:05Z",
                    current=True,
                    revenue_form="point",
                    revenue_tokens=[(str(value), value)],
                )
                self.assert_status(pair, "INCOMPARABLE")

    def test_operating_loss_is_valid_and_not_percentage_profit_growth(self):
        pair = synthetic_pair()
        pair["current"] = synthetic_document(
            "current-doc",
            "2026-11-01T12:00:00Z",
            "2026-11-01T12:00:05Z",
            current=True,
            result_tokens=[("(36)", -36), ("(12)", -12)],
        )
        result = self.assert_status(pair, "FACTS_READY")
        self.assertAlmostEqual(result["derived"]["current_margin_midpoint_pct"], -2)
        self.assertAlmostEqual(result["derived"]["margin_revision_pp"], -12)
        self.assertNotIn("profit_growth_pct", result["derived"])

    def test_direct_margin_point_and_center_spread(self):
        pair = synthetic_pair()
        pair["current"] = synthetic_document(
            "current-doc",
            "2026-11-01T12:00:00Z",
            "2026-11-01T12:00:05Z",
            current=True,
            revenue_form="center_spread",
            revenue_tokens=[("$1,200", 1200), ("$100", 100)],
            result_kind="operating_margin",
            result_form="point",
            result_tokens=[("12%", 12)],
        )
        result = self.assert_status(pair, "FACTS_READY")
        self.assertAlmostEqual(result["derived"]["revenue_revision_pct"], 20)
        self.assertAlmostEqual(result["derived"]["margin_revision_pp"], 2)
        pair["current"]["revenue"]["qualifier"] = "approximate"
        self.assert_status(pair, "FACTS_READY")

    def test_negative_spread_is_integrity_error(self):
        pair = synthetic_pair()
        pair["current"] = synthetic_document(
            "current-doc",
            "2026-11-01T12:00:00Z",
            "2026-11-01T12:00:05Z",
            current=True,
            revenue_form="center_spread",
            revenue_tokens=[("1200", 1200), ("-100", -100)],
        )
        with self.assertRaises(ValueError):
            qualify(pair)

    def test_leading_zero_issuer_identity_and_equal_or_negative_changes(self):
        pair = synthetic_pair()
        pair["current"]["issuer_cik"] = "1234567"
        self.assert_status(pair, "FACTS_READY")
        pair["current"] = synthetic_document(
            "current-doc", "2026-11-01T12:00:00Z", "2026-11-01T12:00:05Z"
        )
        result = self.assert_status(pair, "FACTS_READY")
        self.assertEqual(result["derived"]["revenue_revision_pct"], 0)
        self.assertEqual(result["derived"]["margin_revision_pp"], 0)

    def test_missing_historical_receipts_are_not_invented(self):
        pair = synthetic_pair()
        pair["prior"]["source"]["received_at"] = None
        pair["current"]["source"]["received_at"] = None
        before = deepcopy(pair)
        self.assert_status(pair, "UNVERIFIED")
        self.assertEqual(pair, before)
        for path in (
            "prior.source.published_at",
            "current.source.published_at",
            "clocks.extracted_at",
            "clocks.decision_at",
        ):
            with self.subTest(path=path):
                pair = synthetic_pair()
                change(pair, path, None)
                self.assert_status(pair, "UNVERIFIED")

    def test_future_evidence_and_reversed_clocks_fail(self):
        invalid = {
            "prior.source.published_at": "2026-11-02T12:00:00Z",
            "current.source.published_at": "2026-11-01T12:00:06Z",
            "current.source.received_at": "2026-11-01T12:00:11Z",
            "clocks.extracted_at": "2026-11-01T12:00:16Z",
            "clocks.decision_at": "2026-11-01T12:00:09Z",
        }
        for path, value in invalid.items():
            with self.subTest(path=path):
                pair = synthetic_pair()
                change(pair, path, value)
                with self.assertRaises(ValueError):
                    qualify(pair)
        pair = synthetic_pair()
        pair["prior"]["source"]["published_at"] = pair["current"]["source"]["published_at"]
        pair["prior"]["source"]["received_at"] = pair["current"]["source"]["received_at"]
        with self.assertRaises(ValueError):
            qualify(pair)

    def test_timezone_offsets_and_invalid_supplied_times(self):
        pair = synthetic_pair()
        pair["current"]["source"]["published_at"] = "2026-11-01T07:00:00-05:00"
        self.assert_status(pair, "FACTS_READY")
        for value in ("2026-11-01T12:00:00", "2026-02-30T12:00:00Z", "yesterday", 123):
            with self.subTest(value=value):
                pair = synthetic_pair()
                pair["current"]["source"]["published_at"] = value
                with self.assertRaises(ValueError):
                    qualify(pair)

    def test_internally_reversed_or_invalid_period_fails(self):
        for start, end in (
            ("2026-12-31", "2026-01-01"),
            ("2026-01-01", "2026-01-01"),
            ("2026-02-30", "2026-12-31"),
        ):
            with self.subTest(start=start, end=end):
                pair = synthetic_pair()
                pair["current"]["period_start"] = start
                pair["current"]["period_end"] = end
                with self.assertRaises(ValueError):
                    qualify(pair)

    def test_contract_author_development_fixtures(self):
        path = Path(__file__).parents[1] / "research/GUIDANCE_MARGIN_FACTS_v1/fixtures.json"
        fixtures = json.loads(path.read_text())["fixtures"]
        for fixture in fixtures:
            with self.subTest(fixture=fixture["id"]):
                self.assert_status(fixture["pair"], fixture["expected"]["status"])


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "facts.jsonl"

    def record(
        self,
        record_id="record-1",
        revision_of=None,
        recorded_at="2026-11-01T12:01:00Z",
        event_id="fictional-event-1",
    ):
        pair = synthetic_pair()
        pair["event_id"] = event_id
        return {
            "id": record_id,
            "event_id": event_id,
            "revision_of": revision_of,
            "recorded_at": recorded_at,
            "fact_pair": pair,
        }

    def assert_rejected_unchanged(self, record):
        before = self.path.read_bytes() if self.path.exists() else b""
        with self.assertRaises(ValueError):
            record_revision(record, self.path)
        after = self.path.read_bytes() if self.path.exists() else b""
        self.assertEqual(after, before)

    def test_append_corrected_record_preserves_original_bytes(self):
        first = self.record()
        original = deepcopy(first)
        result = record_revision(first, self.path)
        self.assertEqual(first, original)
        self.assertEqual(result["qualification"]["status"], "FACTS_READY")
        before = self.path.read_bytes()
        correction = self.record("record-2", "record-1", "2026-11-01T12:02:00Z")
        correction["fact_pair"]["external"]["evidence_notes"] = (
            "Later synthetic correction, original retained."
        )
        record_revision(correction, self.path)
        after = self.path.read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertEqual(len(after.splitlines()), 2)
        self.assertEqual(json.loads(after.splitlines()[0])["id"], "record-1")

    def test_nonready_observation_is_kept(self):
        record = self.record()
        record["fact_pair"]["current"]["source"]["received_at"] = None
        result = record_revision(record, self.path)
        self.assertEqual(result["qualification"]["status"], "UNVERIFIED")
        self.assertEqual(len(self.path.read_text().splitlines()), 1)

    def test_caller_cannot_override_qualification(self):
        record = self.record()
        record["qualification"] = {"status": "FACTS_READY"}
        self.assert_rejected_unchanged(record)

    def test_invalid_fact_is_not_journalled(self):
        record = self.record()
        record["fact_pair"]["current"]["revenue"]["low"]["value"] = 99999
        self.assert_rejected_unchanged(record)

    def test_duplicate_ids_reject_even_if_exact_replay(self):
        first = self.record()
        record_revision(first, self.path)
        self.assert_rejected_unchanged(first)
        changed = self.record(event_id="different-event")
        self.assert_rejected_unchanged(changed)

    def test_unknown_cross_event_and_stale_revision_targets_reject(self):
        self.assert_rejected_unchanged(self.record(revision_of="absent"))
        record_revision(self.record(), self.path)
        self.assert_rejected_unchanged(
            self.record("wrong-event", "record-1", "2026-11-01T12:02:00Z", "different-event")
        )
        record_revision(self.record("record-2", "record-1", "2026-11-01T12:02:00Z"), self.path)
        self.assert_rejected_unchanged(self.record("record-3", "record-1", "2026-11-01T12:03:00Z"))
        self.assert_rejected_unchanged(self.record("record-4", None, "2026-11-01T12:03:00Z"))

    def test_event_identity_mismatch_rejects(self):
        record = self.record()
        record["fact_pair"]["event_id"] = "another-event"
        self.assert_rejected_unchanged(record)

    def test_correction_cannot_be_backdated_or_recorded_before_decision(self):
        self.assert_rejected_unchanged(self.record(recorded_at="2026-11-01T12:00:14Z"))
        record_revision(self.record(), self.path)
        for at in ("2026-11-01T12:01:00Z", "2026-11-01T12:00:30Z", "2026-11-01T12:02:00", None):
            with self.subTest(at=at):
                self.assert_rejected_unchanged(self.record("record-2", "record-1", at))

    def test_corrupted_history_blocks_new_append(self):
        record_revision(self.record(), self.path)
        row = json.loads(self.path.read_text())
        row["event_id"] = "tampered-event"
        self.path.write_text(json.dumps(row) + "\n")
        self.assert_rejected_unchanged(self.record("record-2", "record-1", "2026-11-01T12:02:00Z"))

    def test_concurrent_revisions_cannot_both_replace_same_head(self):
        record_revision(self.record(), self.path)
        barrier = threading.Barrier(2)

        def attempt(identifier):
            candidate = self.record(identifier, "record-1", "2026-11-01T12:02:00Z")
            barrier.wait(timeout=5)
            try:
                record_revision(candidate, self.path)
                return "appended"
            except ValueError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ("record-a", "record-b")))
        self.assertCountEqual(results, ["appended", "rejected"])
        self.assertEqual(len(self.path.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
