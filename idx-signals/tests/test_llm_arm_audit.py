"""Readiness checks cannot omit malformed calls, cherry-pick retries or peek at returns."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from idxsig.llm_arm.audit import STATEMENTS, audit, load_jsonl


def fixture(number=1):
    call = {
        "call_id": f"LLM-{number}",
        "set": f"SPEC-{number}",
        "ticker": f"T{number}",
        "market": "US",
        "signal_session": "2026-11-04",
        "called_at": "2026-11-04T23:01Z",
        "call": "ABSTAIN",
        "p": {name: 0.4 for name in STATEMENTS},
        "reasons": ["Evidence is insufficient"],
        "sources": [],
        "agrees_with_kod": True,
        "kod_numeric": "PASS; v2.4 forecast not sealed (no SEC contact)",
    }
    candidate = {
        "type": "SPECULATION_SET",
        "set_id": call["set"],
        "ticker": call["ticker"],
        "market": "US",
        "signal_session": call["signal_session"],
        "sealed_at": "2026-11-04T22:00:00Z",
        "entry_cutoff": "2026-11-05T14:30:00Z",
        "protocol": {"id": "KOD-SPEC-REGISTER-v1", "sha256": "a" * 64},
        "cone": [{"id": name, "prior": 0.5, "resolves_with": "BASE5"} for name in STATEMENTS],
    }
    resolution = {
        "type": "RESOLUTION",
        "set_id": call["set"],
        "window": "BASE5",
        "status": "RESOLVED",
        "ticker": call["ticker"],
        "market": "US",
        "signal_session": call["signal_session"],
        "protocol": copy.deepcopy(candidate["protocol"]),
        "resolved_at": "2026-11-12T22:00:00Z",
        "cone": [{"id": name, "prior": 0.5, "outcome": False} for name in STATEMENTS],
        "paired": {"candidate_net": -0.2, "diff": -0.1},
    }
    return call, candidate, resolution


class LlmArmAuditTests(unittest.TestCase):
    def test_missing_call_prior_uses_register_prior_without_excluding_abstention(self):
        call, candidate, resolution = fixture()
        result = audit([call], [candidate, resolution])
        self.assertEqual(result["counts"]["ABSTAIN"], 1)
        self.assertEqual(result["counts"]["without_source_urls"], 1)
        self.assertEqual(result["counts"]["call_prior_absent"], 1)
        self.assertEqual(result["counts"]["missing_register_priors"], 0)
        self.assertEqual(result["counts"]["complete_BASE5_outcomes"], 1)
        self.assertFalse(result["performance_evaluated"])
        self.assertFalse(result["promotion_permission"])

    def test_numeric_prose_cannot_prove_comparator(self):
        call, candidate, resolution = fixture()
        result = audit([call], [candidate, resolution])
        self.assertEqual(result["counts"]["numeric_forecast_declared_unsealed"], 1)
        self.assertEqual(result["learner_comparison"]["verified_calls"], 0)
        call["kod_numeric"] = "Forecast sealed and perfect"
        self.assertEqual(audit([call], [candidate])["learner_comparison"]["verified_calls"], 0)

    def test_next_day_resolution_does_not_count_for_five_day_statements(self):
        call, candidate, resolution = fixture()
        resolution["window"] = "NEXT1"
        result = audit([call], [candidate, resolution])
        self.assertEqual(result["counts"]["complete_BASE5_outcomes"], 0)
        self.assertEqual(result["counts"]["pending_or_unusable_BASE5"], 1)

    def test_outcomes_require_all_exact_boolean_statements(self):
        call, candidate, resolution = fixture()
        for bad in (None, 0, "false", {}, []):
            with self.subTest(outcome=bad):
                resolution["cone"][0]["outcome"] = bad
                self.assertEqual(
                    audit([call], [candidate, resolution])["counts"]["complete_BASE5_outcomes"], 0
                )

    def test_resolution_identity_protocol_and_priors_must_match(self):
        call, candidate, resolution = fixture()
        mutations = [
            {"ticker": "OTHER"},
            {"market": "IDX"},
            {"signal_session": "2026-11-03"},
            {"protocol": {"id": "CHANGED"}},
            {"resolved_at": "2026-11-04T22:59Z"},
            {"status": "UNRESOLVED"},
        ]
        for change in mutations:
            with self.subTest(change=change):
                row = dict(resolution, **change)
                self.assertEqual(
                    audit([call], [candidate, row])["counts"]["complete_BASE5_outcomes"], 0
                )
        resolution["cone"][0]["prior"] = 0.6
        self.assertEqual(
            audit([call], [candidate, resolution])["counts"]["complete_BASE5_outcomes"], 0
        )

    def test_duplicates_are_all_counted_and_never_arbitrarily_selected(self):
        call, candidate, resolution = fixture()
        second = dict(call, call_id="retry", call="BACK")
        result = audit([call, second], [candidate, resolution])
        self.assertEqual(result["counts"]["all_call_rows"], 2)
        self.assertEqual(result["counts"]["duplicate_set_call_rows"], 2)
        self.assertEqual(result["counts"]["complete_BASE5_outcomes"], 0)
        result = audit([call, call], [candidate, resolution])
        self.assertEqual(result["counts"]["duplicate_call_rows"], 2)
        self.assertEqual(result["counts"]["complete_BASE5_outcomes"], 0)

    def test_duplicate_sets_resolutions_and_statement_ids_fail_closed(self):
        call, candidate, resolution = fixture()
        for register in ([candidate, candidate, resolution], [candidate, resolution, resolution]):
            self.assertEqual(audit([call], register)["counts"]["complete_BASE5_outcomes"], 0)
        resolution["cone"].append(copy.deepcopy(resolution["cone"][0]))
        self.assertEqual(
            audit([call], [candidate, resolution])["counts"]["complete_BASE5_outcomes"], 0
        )

    def test_call_must_be_between_set_sealing_and_exclusive_entry_cutoff(self):
        call, candidate, resolution = fixture()
        for when in ("2026-11-04T21:59:59Z", candidate["entry_cutoff"], "2026-11-04T23:00:00"):
            with self.subTest(when=when):
                call["called_at"] = when
                self.assertEqual(
                    audit([call], [candidate, resolution])["counts"]["complete_BASE5_outcomes"], 0
                )

    def test_malformed_rows_are_visible_in_total_and_details(self):
        malformed = [None, [], 1, {}, {"call_id": [], "set": {}, "call": []}]
        result = audit(malformed, [None, {}, {"type": "UNKNOWN", "set_id": "X"}])
        self.assertEqual(result["counts"]["all_call_rows"], 5)
        self.assertEqual(result["counts"]["malformed_calls"], 5)
        self.assertEqual(result["counts"]["malformed_register_rows"], 3)
        self.assertEqual(len(result["calls"]), 5)

    def test_invalid_probabilities_cannot_count_as_complete(self):
        call, candidate, resolution = fixture()
        for probability in (True, float("nan"), float("inf"), -0.01, 1.01, 10**500, "0.5"):
            with self.subTest(probability=probability):
                call["p"][STATEMENTS[0]] = probability
                result = audit([call], [candidate, resolution])
                self.assertEqual(result["counts"]["malformed_calls"], 1)
                self.assertEqual(result["counts"]["complete_BASE5_outcomes"], 0)

    def test_zero_and_one_probabilities_and_false_outcomes_are_valid(self):
        call, candidate, resolution = fixture()
        call["p"][STATEMENTS[0]], call["p"][STATEMENTS[1]] = 0, 1
        self.assertEqual(
            audit([call], [candidate, resolution])["counts"]["complete_BASE5_outcomes"], 1
        )

    def test_missing_prior_is_counted_and_not_backfilled_from_call(self):
        call, candidate, resolution = fixture()
        call["prior"] = {name: 0.5 for name in STATEMENTS}
        del candidate["cone"][0]["prior"]
        result = audit([call], [candidate, resolution])
        self.assertEqual(result["counts"]["missing_register_priors"], 1)
        self.assertEqual(result["counts"]["complete_BASE5_outcomes"], 0)

    def test_no_performance_leak_even_when_first_look_size_reached(self):
        fixtures = [fixture(number) for number in range(60)]
        calls = [row[0] for row in fixtures]
        register = [record for row in fixtures for record in row[1:]]
        before = copy.deepcopy((calls, register))
        result = audit(calls, register)
        self.assertEqual(result["first_look"]["structurally_complete_calls"], 60)
        self.assertEqual(result["first_look"]["status"], "REQUIRES_INDEPENDENT_EVALUATOR")
        self.assertEqual((calls, register), before)
        self.assertNotIn("-0.2", json.dumps(result))
        self.assertFalse(result["performance_evaluated"])
        self.assertFalse(result["profitability_validated"])
        self.assertEqual(result["timestamp_verification"], "NOT_PERFORMED")

    def test_jsonl_loader_rejects_silent_row_loss_and_duplicate_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calls.jsonl"
            for raw in (b"{}", b"{}\n\n", b'{"a":1,"a":2}\n', b'{"p":NaN}\n', b"{broken}\n"):
                with self.subTest(raw=raw):
                    path.write_bytes(raw)
                    with self.assertRaises(ValueError):
                        load_jsonl(path)
            path.write_text("{}\nnull\n[]\n")
            with self.assertRaisesRegex(ValueError, "record must be an object"):
                load_jsonl(path)
            path.write_text("")
            self.assertEqual(load_jsonl(path), [])


if __name__ == "__main__":
    unittest.main()
