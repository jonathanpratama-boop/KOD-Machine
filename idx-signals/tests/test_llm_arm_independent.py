"""Independent acceptance tests authored from docs/LLM_ARM.md and public shapes.

The author did not inspect implementation files, existing tests, or demo.fixture
before writing these tests.  The data below is deliberately invented; captured
real evidence is exercised separately and must never be described as invented.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from idxsig.llm_arm import workbench
from idxsig.llm_arm.audit import audit, load_jsonl
from idxsig.llm_arm.contracts import STATEMENTS, VERSION
from idxsig.runtime.storage import digest


MODEL = {"provider": "independent-test-provider", "id": "frozen-test-model-v1"}
PROTOCOL = {"id": "INDEPENDENT_ENGINEERING_FIXTURE", "sha256": "1" * 64}
BEFORE = "2030-01-02T09:00:00Z"
PREPARED = "2030-01-02T09:01:00Z"
ANSWERED = "2030-01-02T09:01:10Z"
CUTOFF = "2030-01-02T09:05:00Z"
AFTER = "2030-01-02T09:06:00Z"
DUE = "2030-01-09T16:00:00Z"
CLOSED = "2030-01-10T09:00:00Z"


def clock(value: str):
    return lambda: value


def set_record(identifier: str) -> dict:
    return {
        "type": "SPECULATION_SET",
        "set_id": identifier,
        "record_hash": hashlib.sha256(identifier.encode()).hexdigest(),
        "market": "US",
        "ticker": "ZZTEST",
        "signal_session": "2030-01-01",
        "protocol": copy.deepcopy(PROTOCOL),
        "sealed_at": "2030-01-02T08:59:00Z",
        "entry_cutoff": CUTOFF,
        "plan": "BASE5",
        "windows": ["BASE5"],
        "cone": [
            {"id": statement, "prior": 0.5, "resolves_with": "BASE5"} for statement in STATEMENTS
        ],
    }


def specification(identifiers=("S-A",)) -> dict:
    return {
        "schema_version": VERSION,
        "cohort": "independently-authored-cohort",
        "model": copy.deepcopy(MODEL),
        "latency_budget_seconds": 45,
        "candidates": [
            {"set": set_record(identifier), "resolution_due_at": DUE, "learner": None}
            for identifier in identifiers
        ],
    }


def context() -> dict:
    return {
        "as_of": "2030-01-02T09:00:30Z",
        "observations": "Invented fixture: price and liquidity are unverified.",
        "sources": [
            {
                "id": "independent-source",
                "url": "https://example.org/independent-test-evidence",
                "retrieved_at": "2030-01-02T09:00:20Z",
                "content": "Invented fixture excerpt. No market observation is claimed.",
            }
        ],
    }


def response(packet: dict, call="ABSTAIN") -> dict:
    return {
        "packet_sha256": packet["packet_sha256"],
        "model": copy.deepcopy(MODEL),
        "call": call,
        "p": {statement: 0.25 for statement in STATEMENTS},
        "facts": [
            {
                "claim": "The packet labels its evidence invented.",
                "source_ids": ["independent-source"],
            }
        ],
        "inferences": ["Invented data cannot establish a trading edge."],
        "counterargument": "The fixed probabilities could be poorly calibrated.",
        "uncertainties": ["The actual price path is unknown."],
        "timing_assessment": "This is an engineering test submitted before entry cutoff.",
        "proposal": None,
    }


def resolution(identifier: str, *, net_return=-0.12, unknown=False, window="BASE5") -> dict:
    return {
        "type": "RESOLUTION",
        "set_id": identifier,
        "window": window,
        "status": "RESOLVED",
        "resolved_at": "2030-01-09T16:01:00Z",
        "market": "US",
        "ticker": "ZZTEST",
        "signal_session": "2030-01-01",
        "protocol": copy.deepcopy(PROTOCOL),
        "cone": [
            {"id": statement, "outcome": None if unknown else False} for statement in STATEMENTS
        ],
        "candidate": {"trade": {"net_return": net_return}},
    }


class IndependentWorkbenchAcceptance(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.root = self.parent / "cohort"

    def initialize(self, identifiers=("S-A",)):
        spec = specification(identifiers)
        workbench.initialize(self.root, spec, clock=clock(BEFORE))
        return spec

    def packet(self, identifier="S-A"):
        return workbench.prepare(self.root, identifier, context(), clock=clock(PREPARED))

    def cases(self, at=CLOSED):
        report = workbench.status(self.root, clock=clock(at))
        return {case["set_id"]: case for case in report["cases"]}

    def resolve_all(self, identifiers, *, unknown=()):
        rows = []
        for identifier in identifiers:
            rows.extend(
                [set_record(identifier), resolution(identifier, unknown=identifier in unknown)]
            )
        return workbench.resolve(self.root, rows, clock=clock(CLOSED))

    def test_finite_roster_is_copied_and_unenrolled_candidate_is_rejected(self):
        supplied_spec = self.initialize(("S-A", "S-B"))
        supplied_spec["candidates"].append(specification(("S-EXTRA",))["candidates"][0])
        supplied_spec["model"]["id"] = "mutated-after-enrolment"
        self.assertEqual(set(self.cases()), {"S-A", "S-B"})
        with self.assertRaises(Exception):
            self.packet("S-EXTRA")
        packet = self.packet()
        self.assertEqual(packet["model"], MODEL)

    def test_enrolment_at_entry_cutoff_is_not_prospective(self):
        with self.assertRaises(Exception):
            workbench.initialize(self.root, specification(), clock=clock(CUTOFF))

    def test_context_cannot_claim_future_asof_or_future_retrieval(self):
        self.initialize(("S-A", "S-B"))
        future_asof = context()
        future_asof["as_of"] = "2030-01-02T09:02:00Z"
        with self.assertRaises(Exception):
            workbench.prepare(self.root, "S-A", future_asof, clock=clock(PREPARED))
        future_source = context()
        future_source["sources"][0]["retrieved_at"] = "2030-01-02T09:00:31Z"
        with self.assertRaises(Exception):
            workbench.prepare(self.root, "S-B", future_source, clock=clock(PREPARED))
        self.assertEqual(self.packet()["model"], MODEL)

    def test_prepared_packet_is_frozen(self):
        self.initialize()
        self.packet()
        revised = context()
        revised["sources"][0]["content"] = "A changed observation after freezing."
        with self.assertRaises(Exception):
            workbench.prepare(self.root, "S-A", revised, clock=clock(PREPARED))

    def test_late_and_slow_first_submissions_remain_ineligible(self):
        self.initialize(("S-A", "S-B"))
        late_packet = self.packet("S-A")
        slow_packet = self.packet("S-B")
        late = workbench.record_response(
            self.root, "S-A", response(late_packet), clock=clock(AFTER)
        )
        slow = workbench.record_response(
            self.root, "S-B", response(slow_packet), clock=clock("2030-01-02T09:02:00Z")
        )
        self.assertEqual(late["status"], "LATE")
        self.assertEqual(slow["status"], "SLOW")
        cases = self.cases()
        self.assertNotEqual(cases["S-A"]["status"], "ADMITTED")
        self.assertNotEqual(cases["S-B"]["status"], "ADMITTED")

    def test_malformed_first_submission_is_retained_and_correction_cannot_replace_it(self):
        self.initialize()
        packet = self.packet()
        malformed = self.parent / "malformed.txt"
        malformed.write_text('{"call":', encoding="utf-8")
        rejected = workbench.record_file(self.root, "S-A", malformed, clock=clock(ANSWERED))
        retry = workbench.record_response(self.root, "S-A", response(packet), clock=clock(ANSWERED))
        self.assertEqual(rejected["status"], "REJECTED")
        self.assertNotEqual(retry["status"], "ADMITTED")
        self.resolve_all(("S-A",))
        case = self.cases()["S-A"]
        self.assertEqual(case["status"], "REJECTED")
        self.assertEqual(case["attempts"], 2)
        self.assertFalse(case["probability_scores"])
        journal_text = (self.root / "runs.jsonl").read_text(encoding="utf-8")
        self.assertIn("REJECTED", journal_text)
        self.assertIn('\\"call\\":', journal_text)

    def test_model_cannot_submit_code_outcomes_or_execution_permission(self):
        self.initialize(("S-CODE", "S-OUTCOME", "S-PERMISSION"))
        additions = (
            ("S-CODE", "code", "raise RuntimeError('must never execute')"),
            ("S-OUTCOME", "net_return", 100.0),
            ("S-PERMISSION", "entry_permission", True),
        )
        for identifier, field, value in additions:
            submitted = response(self.packet(identifier))
            submitted[field] = value
            result = workbench.record_response(
                self.root, identifier, submitted, clock=clock(ANSWERED)
            )
            self.assertEqual(result["status"], "REJECTED")
        report = workbench.status(self.root, clock=clock(AFTER))
        self.assertFalse(report["entry_permission"])
        self.assertFalse(report["model_service_running"])

    def test_response_must_match_frozen_model_packet_and_source_ids(self):
        identifiers = ("S-MODEL", "S-PACKET", "S-SOURCE")
        self.initialize(identifiers)
        wrong_model = response(self.packet("S-MODEL"), call="BACK")
        wrong_model["model"]["id"] = "unfrozen-model"
        wrong_packet = response(self.packet("S-PACKET"), call="BACK")
        wrong_packet["packet_sha256"] = "f" * 64
        wrong_source = response(self.packet("S-SOURCE"), call="BACK")
        wrong_source["facts"][0]["source_ids"] = ["not-in-frozen-packet"]
        for identifier, submitted in zip(identifiers, (wrong_model, wrong_packet, wrong_source)):
            result = workbench.record_response(
                self.root, identifier, submitted, clock=clock(ANSWERED)
            )
            self.assertEqual(result["status"], "REJECTED")

    def test_negative_outcome_of_abstention_is_retained_independently(self):
        self.initialize()
        result = workbench.record_response(
            self.root, "S-A", response(self.packet()), clock=clock(ANSWERED)
        )
        self.assertEqual(result["status"], "ADMITTED")
        self.resolve_all(("S-A",))
        case = self.cases()["S-A"]
        self.assertEqual(case["call"], "ABSTAIN")
        self.assertEqual(case["net_return"], -0.12)
        self.assertIsNotNone(case["probability_scores"])
        self.assertEqual(set(case["probability_scores"]), set(STATEMENTS))
        for scores in case["probability_scores"].values():
            self.assertEqual(scores["llm_brier"], 0.0625)
            self.assertEqual(scores["prior_brier"], 0.25)
            self.assertIsNone(scores["learner_brier"])
        report = workbench.status(self.root, clock=clock(CLOSED))
        self.assertTrue(report["complete"])
        self.assertFalse(report["entry_permission"])
        self.assertIn("NEGATIVE", json.dumps(report["alerts"]).upper())

    def test_next1_and_another_sets_base5_cannot_resolve_candidate(self):
        self.initialize()
        workbench.record_response(self.root, "S-A", response(self.packet()), clock=clock(ANSWERED))
        rows = [
            set_record("S-A"),
            resolution("S-A", window="NEXT1"),
            set_record("S-OTHER"),
            resolution("S-OTHER"),
        ]
        workbench.resolve(self.root, rows, clock=clock(CLOSED))
        report = workbench.status(self.root, clock=clock(CLOSED))
        self.assertFalse(report["complete"])
        self.assertIsNone(report["cases"][0]["net_return"])
        self.assertFalse(report["cases"][0].get("probability_scores"))
        with self.assertRaises(Exception):
            workbench.learning_memory(self.root, clock=clock(CLOSED))

    def test_closed_memory_includes_missing_rejected_unknown_and_negative_candidates(self):
        identifiers = ("S-ADMITTED", "S-REJECTED", "S-MISSING")
        self.initialize(identifiers)
        good = response(self.packet("S-ADMITTED"))
        workbench.record_response(self.root, "S-ADMITTED", good, clock=clock(ANSWERED))
        invalid = response(self.packet("S-REJECTED"))
        invalid["p"][STATEMENTS[0]] = 1.01
        workbench.record_response(self.root, "S-REJECTED", invalid, clock=clock(ANSWERED))
        with self.assertRaises(Exception):
            workbench.learning_memory(self.root, clock=clock(ANSWERED))
        self.resolve_all(identifiers, unknown=("S-MISSING",))
        memory = workbench.learning_memory(self.root, clock=clock(CLOSED))
        cases = {case["set_id"]: case for case in memory["cases"]}
        self.assertEqual(set(cases), set(identifiers))
        self.assertEqual(cases["S-MISSING"]["status"], "MISSING_RESPONSE")
        self.assertEqual(set(cases["S-MISSING"]["unknown_statements"]), set(STATEMENTS))
        self.assertFalse(cases["S-MISSING"]["probability_scores"])
        self.assertFalse(cases["S-REJECTED"]["probability_scores"])
        self.assertEqual(cases["S-REJECTED"]["net_return"], -0.12)
        self.assertEqual(cases["S-MISSING"]["net_return"], -0.12)
        self.assertFalse(memory["validated_edge"])

    def test_external_checkpoint_detects_removal_of_both_local_event_copies(self):
        self.initialize()
        packet = self.packet()
        earlier = self.parent / "earlier"
        shutil.copytree(self.root, earlier)
        workbench.record_response(self.root, "S-A", response(packet), clock=clock(ANSWERED))
        checkpoint = workbench.status(self.root, clock=clock(ANSWERED))["checkpoint"]
        shutil.rmtree(self.root)
        shutil.copytree(earlier, self.root)
        self.assertIsInstance(workbench.status(self.root, clock=clock(ANSWERED)), dict)
        with self.assertRaises(Exception):
            workbench.status(self.root, clock=clock(ANSWERED), expected_checkpoint=checkpoint)

    def test_intact_intent_recovers_truncated_journal(self):
        self.initialize()
        workbench.record_response(self.root, "S-A", response(self.packet()), clock=clock(ANSWERED))
        checkpoint = workbench.status(self.root, clock=clock(ANSWERED))["checkpoint"]
        journal = self.root / "runs.jsonl"
        lines = journal.read_bytes().splitlines(keepends=True)
        self.assertGreater(len(lines), 1)
        journal.write_bytes(b"".join(lines[:-1]))
        with self.assertRaises(Exception):
            workbench.status(self.root, clock=clock(ANSWERED))
        workbench.recover(self.root)
        recovered = workbench.status(
            self.root, clock=clock(ANSWERED), expected_checkpoint=checkpoint
        )
        self.assertEqual(recovered["checkpoint"], checkpoint)


class IndependentLegacyAuditAcceptance(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).parent / "fixtures" / "real" / "llm_arm_20261104.json"
        self.real = json.loads(path.read_text(encoding="utf-8"))

    def test_real_call_and_unrelated_real_resolution_do_not_create_base5_readiness(self):
        provenance = self.real["provenance"]
        self.assertEqual(provenance["repository"], "jonathanpratama-boop/KOD-Machine")
        self.assertEqual(len(provenance["call_file_sha256"]), 64)
        self.assertEqual(len(provenance["register_file_sha256"]), 64)
        self.assertEqual(len(self.real["calls"]), 1)
        self.assertEqual(self.real["calls"][0]["ticker"], "TREE")
        report = audit(self.real["calls"], self.real["register"])
        self.assertEqual(report["counts"]["complete_BASE5_outcomes"], 0)
        self.assertEqual(report["first_look"]["required_scored_calls"], 60)
        self.assertEqual(report["first_look"]["status"], "BELOW_FIRST_LOOK")
        self.assertFalse(report["performance_evaluated"])

    def test_synthetic_next1_resolution_cannot_count_as_base5(self):
        calls = copy.deepcopy(self.real["calls"])
        original = copy.deepcopy(self.real["register"][0])
        next1 = resolution(original["set_id"], window="NEXT1")
        for field in ("market", "ticker", "signal_session", "protocol"):
            next1[field] = copy.deepcopy(original[field])
        report = audit(calls, [original, next1])
        self.assertEqual(report["counts"]["complete_BASE5_outcomes"], 0)
        self.assertFalse(report["performance_evaluated"])

    def test_base5_with_wrong_statement_ids_cannot_count_as_complete(self):
        calls = copy.deepcopy(self.real["calls"])
        original = copy.deepcopy(self.real["register"][0])
        wrong_statements = resolution(original["set_id"])
        for field in ("market", "ticker", "signal_session", "protocol"):
            wrong_statements[field] = copy.deepcopy(original[field])
        wrong_statements["cone"] = [
            {"id": "DOWN10_1", "outcome": False},
            {"id": "UP10_1", "outcome": True},
            {"id": "BEATS_TWINS_1", "outcome": False},
        ]
        report = audit(calls, [original, wrong_statements])
        self.assertEqual(report["counts"]["complete_BASE5_outcomes"], 0)
        self.assertFalse(report["performance_evaluated"])

    def test_strict_jsonl_never_skips_malformed_or_nonobject_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "calls.jsonl"
            source.write_text('{"valid": true}\n{"truncated":\n', encoding="utf-8")
            with self.assertRaises(Exception):
                load_jsonl(source)
            source.write_text('{"valid": true}\n[]\n', encoding="utf-8")
            with self.assertRaises(Exception):
                load_jsonl(source)
            source.write_text('{"valid": true}\n', encoding="utf-8")
            self.assertEqual(load_jsonl(source), [{"valid": True}])


class IndependentEvidenceMonitorAcceptance(unittest.TestCase):
    """Monitor tests were authored from its public contract without source access."""

    def setUp(self):
        location = Path(__file__).resolve().parents[2] / "tools" / "watch_llm_arm.py"
        module_spec = importlib.util.spec_from_file_location("independent_llm_monitor", location)
        self.monitor = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(self.monitor)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name) / "repository"
        self.output = Path(self.temporary.name) / "monitor-output"
        directory = self.repository / "idx-signals" / "research" / "LLM_ARM_v1"
        directory.mkdir(parents=True)
        self.call_file = directory / "calls_INDEPENDENT.jsonl"
        call = {
            "call_id": "independent-monitor-call",
            "set": "S-A",
            "ticker": "ZZTEST",
            "market": "US",
            "signal_session": "2030-01-01",
            "called_at": ANSWERED,
            "call": "ABSTAIN",
            "p": {statement: 0.25 for statement in STATEMENTS},
            "prior": {statement: 0.5 for statement in STATEMENTS},
            "kod_numeric": "No sealed numeric comparator is supplied.",
            "agrees_with_kod": True,
            "reasons": ["This is independently invented engineering test data."],
            "sources": [],
        }
        self.call_file.write_text(json.dumps(call) + "\n", encoding="utf-8")
        register = self.repository / "idx-signals" / "paper" / "speculations.jsonl"
        register.parent.mkdir(parents=True)
        body = set_record("S-A")
        body.pop("record_hash")
        body["prev_hash"] = None
        row = {**body, "record_hash": digest(body)}
        register.write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_monitor_deduplicates_identical_input_and_keeps_snapshot_immutable(self):
        report = self.monitor.inspect(self.repository)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["issues"])
        first = self.monitor.watch(self.repository, self.output, clock=clock(BEFORE))
        snapshot = Path(first["snapshot_path"])
        journal = self.output / "runs.jsonl"
        original_snapshot = snapshot.read_bytes()
        original_journal = journal.read_bytes()
        repeated = self.monitor.watch(self.repository, self.output, clock=clock(AFTER))
        self.assertEqual(first["snapshot_sha256"], repeated["snapshot_sha256"])
        self.assertEqual(first["snapshot_path"], repeated["snapshot_path"])
        self.assertEqual(snapshot.read_bytes(), original_snapshot)
        self.assertEqual(journal.read_bytes(), original_journal)
        self.assertEqual(len(list((self.output / "snapshots").glob("*.json"))), 1)
        self.assertEqual(len(original_journal.splitlines()), 1)

    def test_monitor_retains_new_failure_and_preserves_previous_snapshot(self):
        first = self.monitor.watch(self.repository, self.output, clock=clock(BEFORE))
        original_path = Path(first["snapshot_path"])
        original_bytes = original_path.read_bytes()
        self.call_file.write_text('{"truncated":\n', encoding="utf-8")
        blocked = self.monitor.watch(self.repository, self.output, clock=clock(AFTER))
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertTrue(blocked["errors"])
        self.assertNotEqual(first["snapshot_sha256"], blocked["snapshot_sha256"])
        self.assertTrue(Path(blocked["snapshot_path"]).is_file())
        self.assertEqual(original_path.read_bytes(), original_bytes)
        self.assertEqual(len((self.output / "runs.jsonl").read_bytes().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
