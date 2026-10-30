"""Fixes for the external review (Ace), one class per finding.

#1 facts must cite archived evidence published by the horizon cutoff
#2 time comes from external RFC 3161 tokens, not the git commit date (see also test_timestamp.py)
#3 detector evaluations are frozen into the card hash at open; later ones are refused
#4 T-30D / T-72H / T-24H cutoffs are exactly 30 days / 72 hours / 24 hours before the decision cutoff
"""

import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from kod.cli import load_seed, open_and_evaluate
from kod.hashing import fmt_ts
from kod.ledger import LedgerError
from kod.score import build_report
from kod.timestamp import Stamp
from tests.support import FakeTimestamper, Lab, prospective_card
from tests.test_hardening import SEED, LabTest


class Ace1EvidenceContract(LabTest):
    def test_known_fact_without_evidence_is_refused(self):
        with self.assertRaisesRegex(LedgerError, "cites no evidence"):
            open_and_evaluate(self.ledger, self.card(evidence=None))
        self.assertEqual(self.case_rows(), [])

    def test_unknown_facts_need_no_evidence(self):
        card = self.card(
            facts={"dated_catalyst_known": None, "volume_creep_before_story": None}, evidence=None
        )
        open_and_evaluate(self.ledger, card)

    def test_evidence_published_after_the_horizon_cutoff_is_refused(self):
        late = self.lab.add_evidence(
            "Filing.", published=self.clock() - timedelta(days=10), name="late.html"
        )
        with self.assertRaisesRegex(LedgerError, "not published by the T-30D cutoff"):
            open_and_evaluate(self.ledger, self.card(evidence=[late]))
        card = self.card(evidence=[late])
        card["information_sets"]["T-30D"]["facts"] = {
            "dated_catalyst_known": None,
            "catalyst": None,
        }
        card["information_sets"]["T-30D"].pop("evidence")
        open_and_evaluate(self.ledger, card)  # cited only at T-72H and T-24H, where it was public

    def test_unknown_or_misplaced_citations_are_refused(self):
        with self.assertRaisesRegex(LedgerError, "not a recorded v2 evidence object"):
            open_and_evaluate(self.ledger, self.card(evidence=["0" * 64]))
        card = self.card(case_id="KOD-P-NULL", facts={"dated_catalyst_known": None}, evidence=None)
        card["information_sets"]["T-24H"]["evidence"] = {
            "dated_catalyst_known": [self.lab.evidence_id]
        }
        with self.assertRaisesRegex(LedgerError, "UNKNOWN"):
            open_and_evaluate(self.ledger, card)
        card["information_sets"]["T-24H"]["evidence"] = {"not_a_fact": [self.lab.evidence_id]}
        with self.assertRaisesRegex(LedgerError, "not a fact"):
            open_and_evaluate(self.ledger, card)

    def test_evidence_object_requires_provenance(self):
        from tests.support import evidence_meta

        path = Path(self.lab.tmp.name) / "x.pdf"
        path.write_bytes(b"%PDF filing")
        published = self.clock() - timedelta(days=6)
        base = evidence_meta(
            published,
            published + timedelta(days=2),
            retrieval_time=fmt_ts(self.clock() - timedelta(hours=1)),
        )
        with self.assertRaisesRegex(LedgerError, "provenance is required"):
            self.ledger.add_evidence({**base, "provenance": ""}, path)
        with self.assertRaisesRegex(LedgerError, "publication_time is after retrieval_time"):
            self.ledger.add_evidence({**base, "publication_time": fmt_ts(self.clock())}, path)
        with self.assertRaisesRegex(LedgerError, "in the future"):
            self.ledger.add_evidence({**base, "retrieval_time": "2026-10-09T00:00:00Z"}, path)
        with self.assertRaisesRegex(LedgerError, "evidence_grade"):
            self.ledger.add_evidence({**base, "evidence_grade": "E"}, path)
        evidence_id = self.ledger.add_evidence(base, path)
        with self.assertRaisesRegex(LedgerError, "already recorded"):
            self.ledger.add_evidence(base, path)
        obj = json.loads(self.lab.git("show", f"HEAD:registry/evidence-v2/{evidence_id}.json"))
        self.assertEqual(self.lab.git("show", f"HEAD:{obj['archived_copy']}"), "%PDF filing")
        self.assertEqual(obj["publication_time_basis"], "IDX disclosure system timestamp")

    def test_tampered_evidence_bytes_fail_verify(self):
        open_and_evaluate(self.ledger, self.card())
        self.assertTrue(self.verify()["ok"])
        obj = self.ledger.evidence_objects()[self.lab.evidence_id]
        doc = self.lab.repo / obj["archived_copy"]
        doc.write_text("Issuer announces a different date.")
        self.lab.git("commit", "-q", "-am", "rewrite the source")
        result = self.verify()
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("no longer matches content_sha256" in f["message"] for f in result["findings"])
        )

    def test_report_shows_evidence_coverage(self):
        open_and_evaluate(self.ledger, self.card())
        report = build_report(self.ledger)
        case = report["cases"]["PROSPECTIVE"][0]
        self.assertEqual(
            case["evidence"], {"known_facts": 6, "cited_facts": 6, "weakest_grade": "A"}
        )


class Ace2ExternalTimestamps(LabTest):
    def test_token_for_other_data_fails_verify(self):
        class Wrong(FakeTimestamper):
            def stamp(self, data):
                return super().stamp(b"something else")

        self.lab.anchor.timestamper = Wrong(self.clock)
        open_and_evaluate(self.ledger, self.card())
        result = self.verify()
        self.assertFalse(result["ok"])
        self.assertTrue(any("does not verify" in f["message"] for f in result["findings"]))

    def test_tokens_are_committed_with_the_line(self):
        open_and_evaluate(self.ledger, self.card())
        files = self.lab.git("show", "--name-only", "--format=", "HEAD").split()
        self.assertIn("registry/opens.jsonl", files)
        self.assertIn("registry/timestamps/case/KOD-P-T-1.fake.tsr", files)


class Ace3FrozenEvaluations(LabTest):
    def setUp(self):
        super().setUp()
        self.digest = open_and_evaluate(self.ledger, self.card())

    def test_card_hash_covers_the_evaluations(self):
        card = json.loads(self.lab.git("show", "HEAD:registry/cards/KOD-P-T-1.json"))
        frozen = {e["detector"]: e["status"] for e in card["detector_evaluations"]}
        stored = {
            r["detector"]: r["status"]
            for r in self.ledger.rows("SELECT * FROM detector_evaluations")
        }
        self.assertEqual(frozen, stored)
        self.assertEqual(frozen["DATED_CATALYST_KNOWN"], "SIGNAL")

    def test_late_evaluation_is_refused(self):
        with self.assertRaisesRegex(sqlite3.DatabaseError, "frozen at open"):
            self.ledger.conn.execute(
                "INSERT INTO detector_evaluations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "KOD-P-T-1:NEW:v9",
                    "KOD-P-T-1",
                    "NEW",
                    "v9",
                    "SIGNAL",
                    "{}",
                    fmt_ts(self.clock() + timedelta(days=6)),
                ),
            )
        self.ledger.conn.rollback()
        self.assertFalse(hasattr(self.ledger, "record_evaluation"))

    def test_evaluation_edited_in_the_db_fails_verify(self):
        conn = sqlite3.connect(self.ledger.path)
        conn.execute("DROP TRIGGER evals_no_update")
        conn.execute(
            "UPDATE detector_evaluations SET status = 'NO_SIGNAL' WHERE detector = 'DATED_CATALYST_KNOWN'"
        )
        conn.commit()
        conn.close()
        self.assertFalse(self.verify()["ok"])

    def test_rule_edited_in_place_fails_verify(self):
        from kod import detectors

        real = detectors.evaluate

        def edited(sets):
            out = real(sets)
            for row in out:
                if row["detector"] == "DATED_CATALYST_KNOWN":
                    row["status"] = "NO_SIGNAL"
            return out

        with mock.patch("kod.verify.evaluate", edited):
            result = self.verify()
        self.assertFalse(result["ok"])
        self.assertTrue(any("without a new version" in f["message"] for f in result["findings"]))

    def test_scan_entry_hash_covers_its_evaluations(self):
        from tests.test_hardening import entry, scan_payload

        self.ledger.log_scan(
            scan_payload(self.clock, [entry("AAAA", True, True), entry("BBBB", False, False)])
        )
        body = json.loads(self.lab.git("show", "HEAD:registry/scans/SCAN-T-1.json"))
        statuses = {
            e["detector"]: e["status"]
            for e in body["entries"]["SCAN-T-1:AAAA"]["detector_evaluations"]
        }
        self.assertEqual(statuses["DATED_CATALYST_KNOWN"], "SIGNAL")
        with self.assertRaisesRegex(sqlite3.DatabaseError, "frozen at scan time"):
            self.ledger.conn.execute(
                "INSERT INTO scan_evaluations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "SCAN-T-1:AAAA:NEW:v9",
                    "SCAN-T-1:AAAA",
                    "NEW",
                    "v9",
                    "SIGNAL",
                    "{}",
                    fmt_ts(self.clock() + timedelta(days=6)),
                ),
            )
        self.ledger.conn.rollback()
        self.assertTrue(self.verify()["ok"])


class Ace4HorizonOffsets(LabTest):
    def test_prospective_offsets_must_be_exact(self):
        card = self.card()
        card["information_sets"]["T-72H"]["cutoff"] = fmt_ts(
            self.clock() - timedelta(minutes=20) - timedelta(hours=71)
        )
        with self.assertRaisesRegex(
            LedgerError, "T-72H cutoff .* must be decision_cutoff minus 3 days"
        ):
            open_and_evaluate(self.ledger, card)

    def test_retrospective_offsets_must_be_exact_too(self):
        card = json.loads(SEED.read_text())["cases"][0]
        card["case_id"] = "KOD-R-OFFSET"
        card["information_sets"]["T-30D"]["cutoff"] = "2023-04-23T20:00:00Z"  # 31 days
        with self.assertRaisesRegex(LedgerError, "T-30D cutoff"):
            open_and_evaluate(self.ledger, card)

    def test_seed_cards_already_conform(self):
        self.assertEqual(load_seed(self.ledger, SEED), 3)


if __name__ == "__main__":
    unittest.main()
