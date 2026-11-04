"""Behavioral regressions for frozen research inputs, causality and durable budgets."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from idxsig.components.costs import CostModel
from idxsig.research_workflow.demo import fixture
from idxsig.research_workflow.spec import validate_dataset, validate_protocol
from idxsig.research_workflow.worker import run_batch, status
from idxsig.runtime.storage import digest


class ResearchWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "cohort"
        self.protocol, self.dataset, self.proposals = fixture()

    def run_batch(self, proposals=None):
        return run_batch(self.root, self.protocol, self.dataset, proposals or self.proposals)

    def test_real_evaluation_uses_later_entry_and_declared_costs(self):
        summary = self.run_batch()
        self.assertEqual(summary["counts"]["COMPLETED"], 1)
        evaluation = summary["results"][0]["evaluation"]
        fold = evaluation["folds"][0]
        rows = self.dataset["observations"]
        observed = next(
            row for row in fold["candidate"]["observations"] if row["status"] == "OBSERVED_PROXY"
        )
        index = observed["index"]
        cost = CostModel.from_dict(self.protocol["costs"])
        expected = cost.round_trip_return(rows[index + 1]["close"], rows[index + 4]["close"])
        self.assertEqual(observed["entry_at"], rows[index + 1]["observed_at"])
        self.assertEqual(observed["exit_at"], rows[index + 4]["observed_at"])
        self.assertEqual(observed["net_return_proxy"], float(expected))
        self.assertFalse(evaluation["model_fitted"])
        self.assertFalse(evaluation["profitability_validated"])
        self.assertFalse(evaluation["entry_permission"])
        self.assertEqual(evaluation["strategy_checks"]["candidate"]["status"], "PASS")

    def test_censored_observations_remain_in_denominator(self):
        self.proposals[0]["strategy"]["parameters"]["threshold"] = 0
        self.dataset["observations"] = [
            dict(row, close=100 + i) for i, row in enumerate(self.dataset["observations"])
        ]
        self.protocol["dataset_sha256"] = digest(self.dataset)
        result = self.run_batch()["results"][0]["evaluation"]["folds"][0]
        metrics = result["candidate"]["metrics"]
        self.assertEqual(metrics["opportunities"], 50)
        self.assertEqual(metrics["triggered"], 50)
        self.assertEqual(metrics["censored"], 4)
        self.assertEqual(metrics["observed_triggered"], 46)
        self.assertEqual(result["paired_unknown_opportunities"], 4)

    def test_same_hypothesis_renamed_does_not_consume_budget(self):
        original = self.run_batch()
        renamed = copy.deepcopy(self.proposals[0])
        renamed.update(id="renamed", hypothesis="New wording is not new evidence", author="ai")
        renamed["strategy"]["parameters"]["threshold"] = "0.002"
        second = self.run_batch([renamed])
        self.assertEqual(second["attempts_used"], 1)
        self.assertEqual(second["submissions"][0]["status"], "DUPLICATE")
        self.assertEqual(second["results"], original["results"])

    def test_budget_survives_restart_and_failed_proposal(self):
        bad = dict(self.proposals[0], strategy={"id": "UNKNOWN", "version": "1", "parameters": {}})
        first = self.run_batch([bad, self.proposals[0]])
        self.assertEqual(first["attempts_used"], 2)
        self.assertEqual(first["counts"], {"COMPLETED": 1, "FAILED": 1, "INTERRUPTED": 0})
        extra = copy.deepcopy(self.proposals[0])
        extra["strategy"]["parameters"]["threshold"] = 0.1
        second = self.run_batch([extra])
        self.assertEqual(second["submissions"][0]["status"], "BUDGET_EXHAUSTED")
        self.assertEqual(status(self.root)["attempts_remaining"], 0)

    def test_generated_code_fields_are_rejected_and_retained(self):
        injected = dict(self.proposals[0], code="print('not executed')")
        result = self.run_batch([injected])["results"][0]
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("supported fields", result["error"])
        self.assertEqual(status(self.root)["attempts_used"], 1)

    def test_protocol_cannot_be_changed_to_reset_budget(self):
        self.run_batch()
        self.protocol["max_attempts"] += 1
        with self.assertRaisesRegex(ValueError, "frozen"):
            self.run_batch()
        self.assertEqual(status(self.root)["attempts_remaining"], 1)

    def test_frozen_dataset_cannot_be_replaced(self):
        self.run_batch()
        self.dataset["observations"][0]["close"] = "999"
        self.protocol["dataset_sha256"] = digest(self.dataset)
        with self.assertRaisesRegex(ValueError, "frozen"):
            self.run_batch()

    def test_evaluator_change_blocks_further_work(self):
        self.run_batch()
        with patch("idxsig.research_workflow.worker.implementation_hash", return_value="0" * 64):
            self.assertFalse(status(self.root)["implementation_matches"])
            with self.assertRaisesRegex(ValueError, "frozen"):
                self.run_batch()

    def test_interrupted_evaluation_spends_budget_without_rerun(self):
        with patch("idxsig.research_workflow.worker.evaluate", side_effect=RuntimeError("crash")):
            with self.assertRaisesRegex(RuntimeError, "crash"):
                self.run_batch()
        self.assertEqual(status(self.root)["pending_attempts"], 1)
        with patch(
            "idxsig.research_workflow.worker.evaluate", side_effect=AssertionError("must not rerun")
        ):
            recovered = self.run_batch()
        self.assertEqual(recovered["attempts_used"], 1)
        self.assertEqual(recovered["counts"]["INTERRUPTED"], 1)
        self.assertEqual(recovered["submissions"][0]["status"], "DUPLICATE")

    def test_completion_write_recovers_without_second_evaluation(self):
        with patch("idxsig.research_workflow.worker._complete", side_effect=OSError("disk")):
            with self.assertRaisesRegex(OSError, "disk"):
                self.run_batch()
        with patch(
            "idxsig.research_workflow.worker.evaluate", side_effect=AssertionError("must not rerun")
        ):
            recovered = self.run_batch()
        self.assertEqual(recovered["counts"]["COMPLETED"], 1)
        self.assertEqual(recovered["attempts_used"], 1)

    def test_no_future_data_enters_signal_evaluation(self):
        from idxsig.components.strategy import evaluate_series as actual

        def leaking(spec, rows):
            result = actual(spec, rows)
            for row in result:
                row["signal"] = int(float(rows[-1]["close"]) > 105)
            return result

        with patch("idxsig.research_workflow.evaluator.evaluate_series", side_effect=leaking):
            result = self.run_batch()["results"][0]
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["strategy_checks"]["candidate"]["checks"]["prefix_invariance"]["status"], "FAIL"
        )
        self.assertNotIn("evaluation", result)

    def test_insufficient_warmup_is_unknown_not_a_pass(self):
        self.protocol["warmup_lengths"] = [1]
        result = self.run_batch()["results"][0]
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["strategy_checks"]["candidate"]["status"], "UNKNOWN")

    def test_mutated_immutable_result_is_detected(self):
        self.run_batch()
        result_files = [
            path
            for path in (self.root / "results").glob("*.json")
            if not path.name.startswith("attempt-")
        ]
        payload = json.loads(result_files[0].read_text())
        payload["status"] = "FAKE"
        result_files[0].write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            status(self.root)

    def test_torn_journal_is_blocked(self):
        self.run_batch()
        with (self.root / "runs.jsonl").open("ab") as stream:
            stream.write(b'{"unfinished":')
        with self.assertRaisesRegex(ValueError, "torn"):
            self.run_batch()

    def test_valid_prefix_journal_truncation_cannot_buy_evaluation(self):
        self.run_batch()
        (self.root / "runs.jsonl").write_bytes(b"")
        extra = copy.deepcopy(self.proposals[0])
        extra["strategy"]["parameters"]["threshold"] = 0.2
        with patch("idxsig.research_workflow.worker.evaluate") as evaluate:
            with self.assertRaisesRegex(ValueError, "reservation journal is incomplete"):
                self.run_batch([extra])
        evaluate.assert_not_called()

    def test_missing_reservation_intent_is_detected_before_work(self):
        self.run_batch()
        (self.root / "reservations" / "attempt-1.json").unlink()
        with patch("idxsig.research_workflow.worker.evaluate") as evaluate:
            with self.assertRaisesRegex(ValueError, "reservation journal is incomplete"):
                self.run_batch()
        evaluate.assert_not_called()

    def test_status_does_not_change_retained_bytes(self):
        self.run_batch()
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        status(self.root)
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_research_cannot_reuse_active_account_directory(self):
        self.root.mkdir()
        (self.root / "snapshot.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "dedicated root"):
            self.run_batch()

    def test_research_cannot_reuse_timing_only_runtime(self):
        (self.root / "timing").mkdir(parents=True)
        (self.root / "timing" / "report.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "dedicated root"):
            self.run_batch()
        self.assertFalse((self.root / "manifest.json").exists())

    def test_symlinked_root_is_rejected(self):
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic"):
            self.run_batch()
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_store_is_rejected(self):
        self.root.mkdir()
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        (self.root / "inputs").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic"):
            self.run_batch()
        self.assertEqual(list(outside.iterdir()), [])


class ResearchSpecificationTests(unittest.TestCase):
    def setUp(self):
        self.protocol, self.dataset, self.proposals = fixture()

    def test_fold_overlap_is_rejected(self):
        self.protocol["folds"][0]["validation_start"] = self.protocol["folds"][0]["train_end"]
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_protocol(self.protocol)

    def test_label_maturity_is_purged_at_split(self):
        self.protocol["folds"][0]["validation_start"] = self.dataset["observations"][30][
            "observed_at"
        ]
        validate_protocol(self.protocol)
        with self.assertRaisesRegex(ValueError, "embargo"):
            validate_dataset(self.dataset, self.protocol)

    def test_future_or_holdout_rows_cannot_be_read(self):
        self.dataset["observations"][-1]["observed_at"] = self.protocol["reserved_holdout_start"]
        self.protocol["dataset_sha256"] = digest(self.dataset)
        with self.assertRaisesRegex(ValueError, "holdout"):
            validate_dataset(self.dataset, self.protocol)

    def test_raw_hash_is_not_a_substitute_for_normalized_hash(self):
        self.dataset["source_hashes"] = ["f" * 64]
        with self.assertRaisesRegex(ValueError, "frozen content hash"):
            validate_dataset(self.dataset, self.protocol)

    def test_recorded_dataset_requires_source_declaration(self):
        self.dataset["kind"] = "recorded"
        self.protocol["dataset_sha256"] = digest(self.dataset)
        with self.assertRaisesRegex(ValueError, "declared source"):
            validate_dataset(self.dataset, self.protocol)

    def test_duplicate_or_mixed_instrument_observation_fails(self):
        for change in (
            {"symbol": "OTHER"},
            {"observed_at": self.dataset["observations"][0]["observed_at"]},
        ):
            dataset = copy.deepcopy(self.dataset)
            dataset["observations"][1].update(change)
            protocol = dict(self.protocol, dataset_sha256=digest(dataset))
            with self.assertRaises(ValueError):
                validate_dataset(dataset, protocol)

    def test_forward_source_clock_and_nonfinite_price_fail(self):
        for change in ({"event_at": self.protocol["reserved_holdout_start"]}, {"close": "NaN"}):
            dataset = copy.deepcopy(self.dataset)
            dataset["observations"][0].update(change)
            protocol = dict(self.protocol, dataset_sha256=digest(dataset))
            with self.assertRaises(ValueError):
                validate_dataset(dataset, protocol)

    def test_fold_evaluation_periods_cannot_overlap(self):
        duplicate = dict(self.protocol["folds"][0], id="second-fold")
        self.protocol["folds"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "disjoint"):
            validate_protocol(self.protocol)

    def test_price_proxy_cannot_claim_executable_quote_costs(self):
        self.protocol["costs"]["price_basis"] = "EXECUTABLE"
        self.protocol["costs"]["spread_bps"] = 0
        with self.assertRaisesRegex(ValueError, "MID"):
            validate_protocol(self.protocol)


if __name__ == "__main__":
    unittest.main()
