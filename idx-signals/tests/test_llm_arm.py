"""Adversarial checks for honest accounting, timing and cohort memory."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from idxsig.llm_arm.__main__ import main
from idxsig.llm_arm.demo import demo, fixture, response_for
from idxsig.llm_arm.workbench import (
    initialize,
    learning_memory,
    prepare,
    record_file,
    record_response,
    recover,
    resolve,
    status,
    watch,
)
from idxsig.runtime.storage import read_receipts


class LLMWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "cohort"
        self.spec, self.context, self.outcome = fixture()
        self.identifier = self.spec["candidates"][0]["set"]["set_id"]
        self.clock = lambda: "2030-01-01T00:00:02Z"
        initialize(self.root, self.spec, clock=self.clock)

    def packet(self):
        return prepare(self.root, self.identifier, self.context, clock=self.clock)

    def submit(self, response=None, clock=None):
        return record_response(
            self.root,
            self.identifier,
            response if response is not None else response_for(self.packet()),
            clock=clock or self.clock,
        )

    def resolve(self, outcome=None):
        return resolve(
            self.root,
            [self.spec["candidates"][0]["set"], outcome or self.outcome],
            clock=lambda: "2030-01-07T01:00:00Z",
        )

    def report(self):
        return status(self.root, clock=lambda: "2030-01-08T01:00:00Z")

    def test_demo_retains_loss_retry_and_abstention(self):
        root = Path(self.temporary.name) / "demo"
        result = demo(root)
        self.assertEqual(result, demo(root))
        self.assertEqual(result["cases"][0]["net_return"], -0.12)
        self.assertEqual(result["cases"][0]["call"], "ABSTAIN")
        self.assertEqual(result["cases"][0]["attempts"], 2)
        self.assertEqual(len(result["cases"][0]["probability_scores"]), 3)
        self.assertFalse(result["entry_permission"])
        self.assertFalse(result["model_service_running"])

    def test_first_submission_cannot_be_replaced_by_better_retry(self):
        self.submit()
        retry = response_for(self.packet())
        retry["call"] = "BACK"
        self.assertEqual(self.submit(retry)["status"], "REJECTED")
        self.assertEqual(self.report()["cases"][0]["call"], "ABSTAIN")

    def test_invalid_probability_is_retained_and_blocks_retry(self):
        response = response_for(self.packet())
        response["p"]["RUN30_5"] = 2
        self.assertEqual(self.submit(response)["status"], "REJECTED")
        self.assertEqual(self.submit()["status"], "REJECTED")
        self.assertEqual(self.report()["cases"][0]["attempts"], 2)

    def test_nonfinite_first_submission_cannot_disappear(self):
        response = response_for(self.packet())
        response["p"]["RUN30_5"] = float("nan")
        self.assertEqual(self.submit(response)["status"], "REJECTED")
        self.assertEqual(self.submit()["status"], "REJECTED")
        self.assertEqual(len([r for r in read_receipts(self.root) if r["kind"] == "RESPONSE"]), 2)

    def test_enormous_integer_is_retained(self):
        response = response_for(self.packet())
        response["p"]["RUN30_5"] = 10**400
        self.assertEqual(self.submit(response)["status"], "REJECTED")

    def test_malformed_json_file_consumes_first_submission(self):
        self.packet()
        path = Path(self.temporary.name) / "response.json"
        path.write_text('{"p":')
        result = record_file(self.root, self.identifier, path, clock=self.clock)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("invalid_json_sha256", result["response"])
        self.assertEqual(self.submit()["status"], "REJECTED")

    def test_missing_packet_response_is_logged(self):
        self.assertEqual(self.submit({"call": "BACK"})["status"], "REJECTED")
        self.assertEqual(self.submit()["status"], "REJECTED")

    def test_late_answer_cannot_become_timely(self):
        self.packet()

        def late():
            return "2030-01-01T01:00:00Z"

        self.assertEqual(self.submit(clock=late)["status"], "LATE")
        self.assertIsNone(self.report()["cases"][0]["call"])

    def test_slow_answer_cannot_enter_decision_sample(self):
        self.packet()
        self.assertEqual(self.submit(clock=lambda: "2030-01-01T00:02:00Z")["status"], "SLOW")

    def test_clock_reversal_is_blocked_and_retained(self):
        self.packet()
        self.assertEqual(self.submit(clock=lambda: "2030-01-01T00:00:01Z")["status"], "REJECTED")

    def test_future_source_and_context_rejected(self):
        self.context["sources"][0]["retrieved_at"] = "2030-01-02T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "after as-of"):
            self.packet()

    def test_future_comparator_cannot_leak_through_frozen_spec(self):
        candidate = self.spec["candidates"][0]
        candidate["learner"] = {
            "p": {row["id"]: 0.5 for row in candidate["set"]["cone"]},
            "made_at": "2030-01-01T00:30:00Z",
            "set_record_hash": candidate["set"]["record_hash"],
            "record_hash": "declared-test-comparator",
        }
        with self.assertRaisesRegex(ValueError, "unavailable at cohort"):
            initialize(Path(self.temporary.name) / "future", self.spec, clock=self.clock)

    def test_packet_cannot_be_rewritten(self):
        self.packet()
        self.context["observations"] = "Different interpretation after outcome"
        with self.assertRaisesRegex(ValueError, "frozen"):
            self.packet()

    def test_model_change_rejected_with_original_kept(self):
        response = response_for(self.packet())
        response["model"] = {"provider": "other", "id": "new"}
        self.assertEqual(self.submit(response)["status"], "REJECTED")

    def test_unknown_fact_source_rejected(self):
        response = response_for(self.packet())
        response["facts"][0]["source_ids"] = ["invented-url"]
        self.assertEqual(self.submit(response)["status"], "REJECTED")

    def test_unsourced_directional_call_rejected(self):
        response = response_for(self.packet())
        response.update(call="BACK", facts=[])
        self.assertEqual(self.submit(response)["status"], "REJECTED")

    def test_model_cannot_supply_outcome_or_code(self):
        for field in ("net_return", "code", "entry_permission"):
            with self.subTest(field=field):
                response = response_for(self.packet())
                response[field] = "overwrite history"
                self.assertEqual(self.submit(response)["status"], "REJECTED")

    def test_missing_responses_remain_in_denominator_and_alerts(self):
        result = self.report()
        self.assertEqual(result["expected_candidates"], 1)
        self.assertEqual(result["counts"], {"MISSING_RESPONSE": 1})
        self.assertIn("OUTCOME_OVERDUE", {a["code"] for a in result["alerts"]})

    def test_next1_is_not_a_five_day_outcome(self):
        self.submit()
        outcome = dict(self.outcome, window="NEXT1")
        self.assertEqual(self.resolve(outcome)["imported"], 0)
        self.assertFalse(self.report()["complete"])

    def test_loss_cannot_be_replaced(self):
        self.submit()
        self.resolve()
        changed = copy.deepcopy(self.outcome)
        changed["candidate"]["trade"]["net_return"] = 0.5
        with self.assertRaisesRegex(ValueError, "rewrite a loss"):
            self.resolve(changed)
        self.assertEqual(self.report()["cases"][0]["net_return"], -0.12)

    def test_different_set_same_id_does_not_resolve(self):
        altered = dict(self.spec["candidates"][0]["set"], record_hash="different")
        with self.assertRaisesRegex(ValueError, "exact frozen set"):
            resolve(self.root, [altered, self.outcome], clock=lambda: "2030-01-08T00:00:00Z")

    def test_ambiguous_outcomes_are_blocked(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            resolve(
                self.root,
                [self.spec["candidates"][0]["set"], self.outcome, self.outcome],
                clock=lambda: "2030-01-08T00:00:00Z",
            )

    def test_unknown_outcomes_are_explicit_not_scored_zero(self):
        self.submit()
        outcome = copy.deepcopy(self.outcome)
        outcome["cone"][0]["outcome"] = None
        self.resolve(outcome)
        case = self.report()["cases"][0]
        self.assertEqual(case["unknown_statements"], ["RUN30_5"])
        self.assertNotIn("RUN30_5", case["probability_scores"])

    def test_memory_includes_failure_and_loss_without_promotion(self):
        self.packet()
        self.submit({"bad": True})
        self.resolve()
        memory = learning_memory(self.root, clock=lambda: "2030-01-08T00:00:00Z")
        self.assertEqual(memory["cases"][0]["status"], "REJECTED")
        self.assertEqual(memory["cases"][0]["net_return"], -0.12)
        self.assertFalse(memory["validated_edge"])

    def test_unresolved_memory_is_blocked(self):
        self.submit()
        with self.assertRaisesRegex(ValueError, "every expected candidate"):
            learning_memory(self.root, clock=self.clock)

    def test_cohort_roster_model_cannot_reset_history(self):
        self.spec["model"]["id"] = "new-model"
        with self.assertRaisesRegex(ValueError, "frozen"):
            initialize(self.root, self.spec, clock=self.clock)

    def test_manifest_tamper_detected(self):
        path = self.root / "manifest.json"
        value = json.loads(path.read_text())
        value["spec"]["latency_budget_seconds"] = 500
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "manifest differs"):
            self.report()

    def test_truncated_journal_recovers_intents_without_losing_loss(self):
        self.submit()
        self.resolve()
        original = (self.root / "runs.jsonl").read_bytes()
        (self.root / "runs.jsonl").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.report()
        recover(self.root)
        self.assertEqual((self.root / "runs.jsonl").read_bytes(), original)
        self.assertEqual(self.report()["cases"][0]["net_return"], -0.12)

    def test_external_checkpoint_detects_deletion_of_both_local_copies(self):
        self.submit()
        expected = self.report()["checkpoint"]
        lines = (self.root / "runs.jsonl").read_bytes().splitlines(keepends=True)
        (self.root / "runs.jsonl").write_bytes(b"".join(lines[:-1]))
        sorted((self.root / "events").glob("*.json"))[-1].unlink()
        with self.assertRaisesRegex(ValueError, "missing events"):
            status(self.root, expected_checkpoint=expected, clock=self.clock)

    def test_torn_journal_blocks_new_submissions(self):
        self.packet()
        with (self.root / "runs.jsonl").open("ab") as stream:
            stream.write(b'{"torn":')
        with self.assertRaisesRegex(ValueError, "torn"):
            self.submit(response_for({"packet_sha256": "fake", "model": self.spec["model"]}))

    def test_implementation_change_blocks_writes(self):
        with patch("idxsig.llm_arm.workbench.implementation_hash", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "implementation changed"):
                self.packet()

    def test_alerts_are_persistent_deduplicated_and_not_sent(self):
        def clock():
            return "2030-01-08T01:00:00Z"

        report = watch(self.root, clock=clock)
        size = len(read_receipts(self.root))
        self.assertEqual(report["checkpoint"]["event_count"], size)
        self.assertEqual(report["checkpoint"], status(self.root, clock=clock)["checkpoint"])
        watch(self.root, clock=clock)
        self.assertEqual(len(read_receipts(self.root)), size)
        self.assertFalse(report["notifications_delivered"])

    def test_symlinked_journal_is_rejected(self):
        (self.root / "runs.jsonl").unlink()
        (self.root / "runs.jsonl").symlink_to(Path(self.temporary.name) / "elsewhere")
        with self.assertRaisesRegex(ValueError, "symbolic"):
            self.report()

    def test_cli_demo_uses_integrated_workbench(self):
        import contextlib
        import io

        output = io.StringIO()
        root = Path(self.temporary.name) / "cli"
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--root", str(root), "demo"]), 0)
        self.assertEqual(json.loads(output.getvalue())["cases"][0]["net_return"], -0.12)


if __name__ == "__main__":
    unittest.main()
