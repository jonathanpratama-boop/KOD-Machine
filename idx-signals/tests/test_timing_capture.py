import copy
import json
import tempfile
import unittest
from pathlib import Path

from idxsig.timing_capture import (
    append_attempt,
    from_legacy,
    legacy_records,
    make_attempt,
    read_attempts,
    summarize,
    validate_attempt,
    verify,
)
from idxsig.timing_research import diagnose

T0 = "2026-11-04T00:00:00Z"
T1 = "2026-11-04T00:00:01Z"
T2 = "2026-11-04T00:00:02Z"
T3 = "2026-11-04T00:00:03Z"
T4 = "2026-11-04T00:00:04Z"
T5 = "2026-11-04T00:00:05Z"
T6 = "2026-11-04T00:00:06Z"


def attempt(identifier="a", **overrides):
    values = dict(
        detector_version="FIXED_COMPARATOR_v1",
        universe_snapshot_id="u1",
        evidence_id="e1",
        evidence_kind="synthetic",
        recorded_at=T5,
        status="DECIDED",
        source="fixture",
        times={
            "scheduled_at": T0,
            "started_at": T0,
            "published_at": T0,
            "received_at": T1,
            "features_ready_at": T2,
            "detected_at": T3,
            "decision_at": T4,
        },
    )
    values.update(overrides)
    return make_attempt(identifier, **values)


class TimingCaptureTests(unittest.TestCase):
    def test_missing_is_null_and_failure_in_denominator(self):
        failed = attempt("failed", times={"started_at": T0}, status="FAILED")
        report = summarize([attempt(), failed], as_of=T5)
        self.assertEqual(report["attempts"], 2)
        self.assertEqual(report["statuses"]["FAILED"], 1)
        self.assertEqual(report["missing_stages"]["received_at"], 1)
        self.assertEqual(report["cohorts"][0]["stages"]["analyst"]["known"], 1)
        self.assertEqual(report["cohorts"][0]["stages"]["analyst"]["unknown"], 1)
        self.assertIsNone(report["cohorts"][0]["stages"]["fill_after_quote"]["median_seconds"])
        self.assertFalse(report["entry_permission"])

    def test_synthetic_recorded_and_prospective_not_pooled(self):
        rows = [
            attempt(),
            attempt("b", evidence_kind="recorded"),
            attempt("c", evidence_kind="prospective"),
            attempt("d", detector_version="OTHER_v1"),
        ]
        report = summarize(rows, as_of=T5)
        self.assertEqual(len(report["cohorts"]), 4)
        self.assertEqual(len(report["source_latency"]), 3)
        self.assertTrue(all(r["attempts"] == 1 for r in report["cohorts"]))

    def test_duplicate_attempts_rejected_from_summary(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            summarize([attempt(), attempt()], as_of=T5)

    def test_unknown_schema_and_fields_rejected(self):
        row = attempt()
        row["schema_version"] = "NEXT_UNREVIEWED_VERSION"
        with self.assertRaisesRegex(ValueError, "schema"):
            validate_attempt(row)
        row = attempt()
        row["outcome"] = {"future_gain": 900}
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_attempt(row)

    def test_empty_wrong_container_types_are_not_silently_defaulted(self):
        for field in (
            "times",
            "threshold",
            "clock",
            "durations_ns",
            "links",
            "prices",
            "external_timestamp",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                attempt(**{field: []})

    def test_recorded_receipt_can_precede_replay_start(self):
        row = attempt(
            evidence_kind="recorded",
            times={"received_at": T0, "started_at": T1, "features_ready_at": T2, "decision_at": T3},
        )
        self.assertEqual(row["received_at"], T0)
        with self.assertRaisesRegex(ValueError, "precedes"):
            attempt(times={"started_at": T3, "features_ready_at": T2}, status="COMPLETED")

    def test_utc_normalization_and_input_not_mutated(self):
        row = attempt(times={"received_at": "2026-11-04T07:00:01+07:00"}, status="COMPLETED")
        self.assertEqual(row["received_at"], T1)
        original = copy.deepcopy(row)
        validate_attempt(row)
        self.assertEqual(row, original)

    def test_naive_future_and_reversed_local_times_rejected(self):
        for times in (
            {"received_at": "2026-11-04T00:00:01"},
            {"received_at": T6},
            {"received_at": T3, "decision_at": T2},
        ):
            with self.assertRaises(ValueError):
                attempt(times=times)
        with self.assertRaisesRegex(ValueError, "cutoff"):
            summarize([attempt()], as_of=T4)

    def test_source_clock_conflict_retained_but_not_reported_as_lead(self):
        row = attempt(times={"received_at": T1}, source_time=T6, status="COMPLETED")
        report = summarize([row], as_of=T5)
        self.assertEqual(report["source_latency"][0]["clock_conflicts"], 1)
        self.assertEqual(report["source_latency"][0]["lag"]["unknown"], 1)
        self.assertEqual(
            report["records"][0]["signed_clock_differences_seconds"]["source_to_receipt"], -5
        )
        self.assertIsNone(report["records"][0]["seconds"]["source_to_receipt"])

    def test_threshold_requires_real_basis_evidence_and_causal_time(self):
        for threshold in (
            {"at": T2, "basis": "UNKNOWN", "evidence_id": "e1", "reference_at": T0},
            {"at": T2, "basis": "QUOTE", "evidence_id": None, "reference_at": T0},
            {"at": T4, "basis": "QUOTE", "evidence_id": "e1", "reference_at": T0},
            {"at": T2, "basis": "QUOTE", "evidence_id": "e1", "reference_at": T3},
        ):
            with self.assertRaises(ValueError):
                attempt(threshold=threshold)
        row = attempt(
            threshold={
                "at": T0,
                "basis": "COMPLETED_BAR",
                "evidence_id": "bar1",
                "reference_at": None,
            }
        )
        detail = summarize([row], as_of=T5)["records"][0]
        self.assertIsNone(detail["seconds"]["threshold"])
        self.assertEqual(detail["seconds"]["collection_after_threshold"], 1)

    def test_clock_measurement_needs_evidence_and_time(self):
        with self.assertRaises(ValueError):
            attempt(
                clock={
                    "status": "MEASURED_EXTERNAL",
                    "offset_seconds": 0.1,
                    "observed_at": T0,
                    "evidence_id": None,
                }
            )
        with self.assertRaises(ValueError):
            attempt(
                clock={
                    "status": "UNKNOWN",
                    "offset_seconds": 0,
                    "observed_at": None,
                    "evidence_id": None,
                }
            )
        row = attempt(
            clock={
                "status": "MEASURED_EXTERNAL",
                "offset_seconds": "-0.125",
                "observed_at": T0,
                "evidence_id": "clock-receipt",
            }
        )
        self.assertEqual(row["clock"]["offset_seconds"], "-0.125")

    def test_monotonic_duration_independent_of_wall_clock_lag(self):
        row = attempt(source_time=T6, durations_ns={"fetch": 125000000, "unobserved": None})
        detail = summarize([row], as_of=T5)["records"][0]
        self.assertEqual(detail["monotonic_seconds"]["fetch"], 0.125)
        self.assertIsNone(detail["monotonic_seconds"]["unobserved"])
        for bad in (-1, True, 1.5, float("nan")):
            with self.assertRaises(ValueError):
                attempt(durations_ns={"fetch": bad})

    def test_local_hash_never_becomes_external_verification(self):
        with self.assertRaisesRegex(ValueError, "external timestamp"):
            attempt(external_timestamp={"status": "VERIFIED"})
        with self.assertRaises(ValueError):
            attempt(external_timestamp={"status": "PRESENT_UNVERIFIED"})
        row = attempt(
            external_timestamp={
                "status": "PRESENT_UNVERIFIED",
                "token_sha256": "a" * 64,
                "evidence_id": "tsa-receipt",
            }
        )
        self.assertEqual(
            summarize([row], as_of=T5)["external_timestamp_statuses"], {"PRESENT_UNVERIFIED": 1}
        )

    def test_prices_require_time_identity_and_never_become_profit(self):
        first = {
            "price": "100",
            "venue": "proxy",
            "symbol": "A",
            "currency": "USD",
            "evidence_id": "q1",
            "observed_at": T3,
        }
        second = dict(first, price="102", observed_at=T4, evidence_id="q2")
        row = attempt(prices={"detected_at": first, "decision_at": second})
        detail = summarize([row], as_of=T5)["records"][0]
        self.assertEqual(detail["price_drift_fraction"]["detected_at_to_decision_at"], "0.02")
        mismatch = attempt(
            prices={"detected_at": first, "decision_at": dict(second, venue="another")}
        )
        self.assertIsNone(
            summarize([mismatch], as_of=T5)["records"][0]["price_drift_fraction"][
                "detected_at_to_decision_at"
            ]
        )
        with self.assertRaisesRegex(ValueError, "unavailable"):
            attempt(prices={"detected_at": dict(first, observed_at=T4)})

    def test_nonfinite_and_boolean_prices_rejected(self):
        for bad in ("NaN", "Infinity", True, 0, -1):
            with self.assertRaises(ValueError):
                attempt(
                    prices={
                        "detected_at": {
                            "price": bad,
                            "venue": "proxy",
                            "symbol": "A",
                            "currency": "USD",
                            "evidence_id": "q1",
                            "observed_at": T3,
                        }
                    }
                )

    def test_immutable_journal_retry_revision_and_as_of_read(self):
        with tempfile.TemporaryDirectory() as directory:
            row = attempt()
            one = append_attempt(directory, row)
            self.assertEqual(one, append_attempt(directory, row))
            two_row = copy.deepcopy(row)
            two_row.update(recorded_at=T6, executable_at=T5, fill_at=T6, status="FILLED")
            two = append_attempt(directory, two_row)
            self.assertEqual(two["version"], 2)
            self.assertEqual(two["supersedes"], one["record_hash"])
            self.assertEqual(read_attempts(directory, as_of=T5), [row])
            self.assertEqual(read_attempts(directory), [two_row])
            report = verify(directory)
            self.assertEqual((report["attempts"], report["revisions"]), (1, 2))
            self.assertEqual(report["external_verification"], "LOCAL_HASH_CHAIN_ONLY")

    def test_revisions_cannot_rewrite_known_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            row = attempt()
            append_attempt(directory, row)
            for key, value in (
                ("decision_at", T5),
                ("evidence_id", "other"),
                ("universe_snapshot_id", "later-universe"),
                ("recorded_at", T4),
            ):
                changed = copy.deepcopy(row)
                changed[key] = value
                with self.assertRaises(ValueError):
                    append_attempt(directory, changed)
            self.assertEqual(verify(directory)["revisions"], 1)

    def test_terminal_failure_retry_requires_new_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            row = attempt(status="FAILED")
            append_attempt(directory, row)
            with self.assertRaisesRegex(ValueError, "new attempt identity"):
                append_attempt(directory, dict(row, status="COMPLETED"))

    def test_unknown_threshold_revision_preserves_known_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            row = attempt(
                threshold={"at": None, "basis": "UNKNOWN", "evidence_id": None, "reference_at": T0}
            )
            append_attempt(directory, row)
            changed = copy.deepcopy(row)
            changed["threshold"] = {
                "at": T2,
                "basis": "QUOTE",
                "evidence_id": "q1",
                "reference_at": T1,
            }
            with self.assertRaisesRegex(ValueError, "reference_at"):
                append_attempt(directory, changed)
            changed["threshold"]["reference_at"] = T0
            self.assertEqual(append_attempt(directory, changed)["version"], 2)

    def test_timing_directory_symlinks_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            outside = Path(directory) / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "timing").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                append_attempt(root, attempt())
            self.assertEqual(list(outside.iterdir()), [])

    def test_status_cannot_regress_or_erase_completed_decision(self):
        for original, changed in (
            ("DECIDED", "STARTED"),
            ("COMPLETED", "DETECTED"),
            ("NO_ACTION", "UNKNOWN"),
            ("BLOCKED", "DECIDED"),
        ):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as directory:
                row = attempt(status=original)
                append_attempt(directory, row)
                with self.assertRaises(ValueError):
                    append_attempt(directory, dict(row, status=changed))

    def test_unavailable_external_time_cannot_claim_known_token(self):
        for status in ("NOT_REQUESTED", "UNAVAILABLE"):
            with self.assertRaisesRegex(ValueError, "cannot claim"):
                attempt(external_timestamp={"status": status, "token_sha256": "a" * 64})

    def test_old_input_receipt_without_publication_never_becomes_source_lag(self):
        row = attempt(
            times={"started_at": T2, "received_at": T2, "decision_at": T4},
            links={"original_capture_at": T0},
            source="RETAINED_INPUT_READ",
        )
        report = summarize([row], as_of=T5)
        self.assertIsNone(report["source_latency"][0]["lag"]["median_seconds"])
        self.assertEqual(report["source_latency"][0]["lag"]["unknown"], 1)

    def test_status_cannot_claim_unobserved_decision_detection_or_fill(self):
        for status in ("DETECTED", "DECIDED", "FILLED"):
            with (
                self.subTest(status=status),
                self.assertRaisesRegex(ValueError, "requires an observed"),
            ):
                attempt(status=status, times={"received_at": T1})

    def test_journal_sequence_and_version_are_strict_integers(self):
        from idxsig.runtime.storage import canonical, digest

        for field in ("sequence", "version"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                envelope = append_attempt(directory, attempt())
                envelope[field] = True
                envelope["record_hash"] = digest(
                    {k: v for k, v in envelope.items() if k != "record_hash"}
                )
                (Path(directory) / "timing/attempts.jsonl").write_bytes(canonical(envelope) + b"\n")
                artifact = Path(directory) / "timing/records" / (envelope["record_hash"] + ".json")
                artifact.write_bytes(canonical(envelope) + b"\n")
                with self.assertRaises(ValueError):
                    verify(directory)

    def test_corrupted_journal_torn_tail_and_artifact_fail_closed(self):
        for kind in ("journal", "torn", "artifact", "whitespace", "missing"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                item = append_attempt(directory, attempt())
                journal = Path(directory) / "timing/attempts.jsonl"
                artifact = Path(directory) / "timing/records" / (item["record_hash"] + ".json")
                if kind == "journal":
                    journal.write_bytes(
                        journal.read_bytes().replace(b'"sequence":1', b'"sequence":2')
                    )
                elif kind == "torn":
                    journal.write_bytes(journal.read_bytes()[:-1])
                elif kind == "artifact":
                    artifact.write_text("{}")
                elif kind == "whitespace":
                    artifact.write_bytes(artifact.read_bytes() + b"\n")
                else:
                    artifact.unlink()
                with self.assertRaises(ValueError):
                    append_attempt(directory, attempt("next"))

    def test_orphan_artifact_from_interrupted_append_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            first = append_attempt(directory, attempt())
            journal = Path(directory) / "timing/attempts.jsonl"
            journal.unlink()
            self.assertEqual(append_attempt(directory, attempt()), first)
            self.assertEqual(verify(directory)["revisions"], 1)

    def test_duplicate_json_key_rejected_even_when_other_bytes_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            append_attempt(directory, attempt())
            journal = Path(directory) / "timing/attempts.jsonl"
            journal.write_bytes(
                journal.read_bytes().replace(b'"sequence":1', b'"sequence":1,"sequence":1')
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify(directory)

    def test_backup_restores_all_timing_evidence(self):
        from idxsig.runtime.backup import backup, restore

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            append_attempt(source, attempt())
            saved = verify(source)
            backup(source, Path(directory) / "copy.zip")
            restore(Path(directory) / "copy.zip", Path(directory) / "restored")
            self.assertEqual(verify(Path(directory) / "restored"), saved)

    def test_legacy_round_trip_preserves_original_diagnostic(self):
        old = {
            "id": "legacy",
            "detector_version": "v0",
            "evidence_kind": "recorded",
            "universe_snapshot_id": "u",
            "evidence_id": "e",
            "published_at": T0,
            "received_at": T1,
            "detected_at": T2,
            "decision_at": T3,
            "outcome": {"gain": 900, "time": "2030-01-01T00:00:00Z"},
        }
        before = json.dumps(old, sort_keys=True)
        new = from_legacy(old, recorded_at=T5)
        self.assertEqual(diagnose([old], as_of=T5), diagnose(legacy_records([new]), as_of=T5))
        self.assertEqual(json.dumps(old, sort_keys=True), before)
        self.assertEqual(new["status"], "UNKNOWN")

    def test_empty_store_and_report_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_attempts(directory), [])
            self.assertEqual(verify(directory)["attempts"], 0)
        report = summarize([], as_of=T5)
        self.assertEqual(report["attempts"], 0)
        self.assertEqual(report["source_latency"], [])


if __name__ == "__main__":
    unittest.main()
