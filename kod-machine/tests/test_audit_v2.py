"""Hardening pass v2 (independent audit). Each test names the failure it prevents.

S0 legacy records keep verifying under their own hash recipes
S1 evidence: existence vs content, grade ceilings, publication vs retrieval time, strict citations
S2 GitHub server-side receipts: a local commit date is never enough
S3 detector outputs and detector code are frozen at prediction time
S4 AS-OF horizons are exact, timezone-normalised, and labelled correctly
"""

import http.server
import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from kod.anchor import GitAnchor
from kod.cli import open_and_evaluate
from kod.hashing import fmt_ts, sha256_obj
from kod.ledger import Ledger, LedgerError, freeze_card
from kod.remote import (
    LATE,
    MISMATCH,
    UNVERIFIED,
    GitHubActionsClient,
    RemoteUnavailable,
    repository_from_git,
)
from kod.verify import AUTHORITATIVE, calibration_eligibility, verify
from tests.support import evidence_meta
from tests.test_hardening import OUTCOME, LabTest

KOD_ROOT = Path(__file__).resolve().parents[1]


class S1EvidenceProvenance(LabTest):
    def meta(self, **overrides):
        published = self.clock() - timedelta(days=10)
        overrides.setdefault("retrieval_time", fmt_ts(self.clock() - timedelta(hours=1)))
        return evidence_meta(published, published + timedelta(days=2), **overrides)

    def add(self, text="Filing body.", **overrides):
        path = Path(self.lab.tmp.name) / f"e{len(self.ledger.evidence_objects())}.html"
        path.write_text(text)
        return self.ledger.add_evidence(self.meta(**overrides), path)

    def test_grade_a_needs_verified_existence_and_content(self):
        # Protects against: an operator labelling an unverified document grade A.
        with self.assertRaisesRegex(LedgerError, "supports at most grade C"):
            self.add(existence_method="NONE", content_method="NONE")
        with self.assertRaisesRegex(LedgerError, "supports at most grade B"):
            self.add(content_method="NONE")
        with self.assertRaisesRegex(LedgerError, "archive_time at or before the cutoff"):
            self.add(archive_time=fmt_ts(self.clock() - timedelta(days=1)))
        with self.assertRaisesRegex(LedgerError, "supports at most grade B"):
            self.add(source_type="SECONDARY")  # only a primary document can be grade A

    def test_publication_after_the_cutoff_is_rejected(self):
        # Protects against: citing a document as knowable at a cutoff it postdates.
        late = fmt_ts(self.clock() - timedelta(days=1))
        with self.assertRaisesRegex(LedgerError, "after as_of_cutoff"):
            self.add(
                publication_time=late,
                existence_method="NONE",
                content_method="NONE",
                evidence_grade="C",
                archive_url=None,
                archive_time=None,
            )
        # A retrospective account may postdate the cutoff, but only as grade D...
        d = self.add(
            source_type="RETROSPECTIVE",
            publication_time=late,
            existence_method="NONE",
            content_method="NONE",
            evidence_grade="D",
            archive_url=None,
            archive_time=None,
        )
        self.assertEqual(self.ledger.evidence_objects()[d]["grade_ceiling"], "D")
        # ...and a strict card refuses grade D.
        with self.assertRaisesRegex(LedgerError, "grade D"):
            open_and_evaluate(self.ledger, self.card(evidence=[d]))

    def test_retrieval_time_is_never_publication_time(self):
        # Protects against: "we downloaded it before the cutoff" standing in for "it was published then".
        eid = self.add(
            publication_time=None,
            publication_time_basis="",
            existence_method="NONE",
            content_method="NONE",
            evidence_grade="D",
            archive_url=None,
            archive_time=None,
        )
        obj = self.ledger.evidence_objects()[eid]
        self.assertIsNone(obj["publication_time"])  # not filled in from retrieval_time
        self.assertIsNotNone(obj["retrieval_time"])
        self.assertEqual(obj["grade_ceiling"], "D")
        with self.assertRaisesRegex(LedgerError, "supports at most grade D"):
            self.add(
                publication_time=None,
                publication_time_basis="",
                existence_method="NONE",
                content_method="NONE",
                evidence_grade="C",
                archive_url=None,
                archive_time=None,
            )
        with self.assertRaisesRegex(LedgerError, "retrieval time is not a publication time"):
            self.add(publication_time_basis="date we retrieved the page")
        card = self.card(
            case_id="KOD-R-RET",
            call_type="RETROSPECTIVE",
            evidence=[eid],
            integrity_level="STRICT-v3",
        )
        card.pop("outcome_window")
        with self.assertRaisesRegex(LedgerError, "grade D"):
            open_and_evaluate(self.ledger, card)

    def test_existence_and_content_are_recorded_separately(self):
        # Protects against: a timestamp that proves a filing existed being read as proof of its contents.
        eid = self.add(
            existence_method="PRIMARY_SOURCE_TIMESTAMP",
            content_method="NONE",
            evidence_grade="B",
            archive_url=None,
            archive_time=None,
        )
        obj = self.ledger.evidence_objects()[eid]
        self.assertTrue(obj["existence_verified"])
        self.assertFalse(obj["content_verified"])
        self.assertEqual(obj["grade_ceiling"], "B")
        with self.assertRaisesRegex(LedgerError, "content_verified=True disagrees"):
            self.add(content_method="NONE", content_verified=True, evidence_grade="B")
        with self.assertRaisesRegex(LedgerError, "needs the archived bytes"):
            self.ledger.add_evidence(self.meta(), None)  # no bytes: contents cannot be verified

    def test_live_capture_with_external_timestamp_is_grade_a(self):
        # Protects against: grade A for a historical page captured today. Only a capture stamped
        # before the cutoff verifies existence and contents by timestamp.
        future_cutoff = fmt_ts(self.clock() + timedelta(hours=2))
        eid = self.add(
            as_of_cutoff=future_cutoff,
            retrieval_time=fmt_ts(self.clock()),
            publication_time=fmt_ts(self.clock() - timedelta(hours=3)),
            existence_method="EXTERNAL_TIMESTAMP_RECEIPT",
            content_method="EXTERNAL_TIMESTAMP_RECEIPT",
            archive_url=None,
            archive_time=None,
        )
        self.assertEqual(self.ledger.evidence_objects()[eid]["evidence_grade"], "A")
        with self.assertRaisesRegex(
            LedgerError, "timestamped at or before the cutoff|external timestamp at or before"
        ):
            self.add(
                text="other",
                existence_method="EXTERNAL_TIMESTAMP_RECEIPT",
                content_method="EXTERNAL_TIMESTAMP_RECEIPT",
                archive_url=None,
                archive_time=None,
            )
        self.assertTrue(self.verify()["ok"])

    def test_grade_cannot_be_silently_upgraded(self):
        # Protects against: a C/D object becoming A by editing the database or the registry.
        eid = self.add(
            existence_method="NONE",
            content_method="NONE",
            evidence_grade="C",
            archive_url=None,
            archive_time=None,
        )
        with self.assertRaisesRegex(sqlite3.DatabaseError, "append-only"):
            self.ledger.conn.execute(
                "UPDATE evidence_objects SET evidence_grade = 'A' WHERE evidence_id = ?", (eid,)
            )
        self.ledger.conn.rollback()
        conn = sqlite3.connect(self.ledger.path)
        conn.execute("DROP TRIGGER evidence_objects_no_update")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "CHECK"):
            conn.execute(
                "UPDATE evidence_objects SET evidence_grade = 'A' WHERE evidence_id = ?", (eid,)
            )
        obj = json.loads(
            conn.execute(
                "SELECT object_json FROM evidence_objects WHERE evidence_id = ?", (eid,)
            ).fetchone()[0]
        )
        obj["evidence_grade"] = obj["grade_ceiling"] = "A"
        conn.execute(
            "UPDATE evidence_objects SET object_json = ?, evidence_grade = 'A', grade_ceiling = 'A' "
            "WHERE evidence_id = ?",
            (json.dumps(obj), eid),
        )
        conn.commit()
        conn.close()
        result = self.verify()
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                f["subject"] == f"evidence {eid[:12]}"
                for f in result["findings"]
                if f["level"] == "FAIL"
            )
        )

    def test_strict_primary_claim_needs_verified_primary_evidence(self):
        # Protects against: "primary_document_public: true" backed by a news story.
        secondary = self.add(source_type="SECONDARY", content_method="NONE", evidence_grade="B")
        facts = {"primary_document_public": True, "price_already_repriced": False}
        with self.assertRaisesRegex(LedgerError, "claims a primary document"):
            open_and_evaluate(self.ledger, self.card(facts=facts, evidence=[secondary]))
        open_and_evaluate(
            self.ledger, self.card(case_id="KOD-P-OK", facts=facts, evidence=[self.lab.evidence_id])
        )

    def test_fact_level_grade_claim_must_be_supported(self):
        # Protects against: a card asserting grade A for a fact whose evidence is weaker.
        c_grade = self.add(
            existence_method="NONE",
            content_method="NONE",
            evidence_grade="C",
            archive_url=None,
            archive_time=None,
        )
        card = self.card(evidence=[c_grade])
        card["information_sets"]["T-24H"]["fact_grades"] = {"dated_catalyst_known": "A"}
        with self.assertRaisesRegex(LedgerError, "claims grade A"):
            open_and_evaluate(self.ledger, card)

    def test_partial_retrospective_may_use_retrospective_sources(self):
        # Protects against: blocking honest reconstructions, while keeping them out of strict use.
        d = self.add(
            source_type="RETROSPECTIVE",
            publication_time=fmt_ts(self.clock() - timedelta(days=1)),
            existence_method="NONE",
            content_method="NONE",
            evidence_grade="D",
            archive_url=None,
            archive_time=None,
        )
        card = self.card(case_id="KOD-R-PART", call_type="RETROSPECTIVE", evidence=[d])
        card.pop("outcome_window")
        open_and_evaluate(self.ledger, card)
        self.assertEqual(
            self.ledger.rows("SELECT integrity_level FROM cases WHERE case_id = 'KOD-R-PART'")[0][
                0
            ],
            "PARTIAL",
        )

    def test_corroboration_needs_two_independent_publishers(self):
        b1 = self.add(
            source_type="SECONDARY", content_method="NONE", evidence_grade="B", publisher="Wire A"
        )
        b2 = self.add(
            text="second",
            source_type="SECONDARY",
            content_method="NONE",
            evidence_grade="B",
            publisher="Wire A",
        )
        with self.assertRaisesRegex(LedgerError, "two different publishers"):
            self.add(
                text="third",
                existence_method="CORROBORATED_CONTEMPORANEOUS",
                corroborated_by=[b1, b2],
                content_method="NONE",
                evidence_grade="B",
                archive_url=None,
                archive_time=None,
            )


class S2RemoteTimestampReceipts(LabTest):
    def open_case(self, case_id="KOD-P-R", push_at=None, push=True):
        sha = open_and_evaluate(self.ledger, self.card(case_id=case_id))
        if push:
            self.lab.push_head(push_at)
        return sha

    def status(self, case_id):
        return calibration_eligibility(self.ledger, self.lab.anchor, self.lab.github)[case_id]

    def close(self, case_id, sha, label="REPRICED_UP"):
        self.clock.moment = self.clock() + timedelta(days=6)
        self.ledger.close_case(case_id, {**OUTCOME, "outcome_label": label, "card_sha": sha})

    def test_receipt_before_window_makes_the_case_authoritative(self):
        sha = self.open_case()
        self.assertEqual(self.status("KOD-P-R")["status"], AUTHORITATIVE)
        self.close("KOD-P-R", sha)
        report = self.report()
        self.assertEqual(report["counts"]["prospective_closed"], 1)

    def test_backdated_local_commit_alone_is_not_enough(self):
        # Protects against: a commit whose date claims it predates the outcome, never pushed in time.
        sha = self.open_case(push=False)
        self.assertTrue(self.lab.git("log", "-1", "--format=%cI").startswith("2026-10-07"))
        self.assertEqual(self.status("KOD-P-R")["status"], UNVERIFIED)
        self.close("KOD-P-R", sha)
        report = self.report()
        self.assertEqual(report["counts"]["prospective_closed"], 0)
        self.assertEqual(report["excluded_prospective"][UNVERIFIED]["outcomes"], {"REPRICED_UP": 1})

    def test_backdated_commit_pushed_after_the_window_is_late(self):
        # Protects against: creating the call after the event with a backdated commit date and pushing it.
        self.open_case(push_at=self.clock() + timedelta(days=2))
        judged = self.status("KOD-P-R")
        self.assertEqual(judged["status"], LATE)
        result = self.verify()
        self.assertTrue(any(LATE in f["message"] for f in result["findings"]))

    def test_receipt_must_be_for_exactly_the_anchor_commit(self):
        # Protects against: a later commit's run standing in for the anchor's.
        self.open_case(push=False)
        self.lab.git("commit", "-q", "--allow-empty", "-m", "later work")
        self.lab.push_head()
        self.assertEqual(self.status("KOD-P-R")["status"], UNVERIFIED)
        later = self.lab.github.runs[self.lab.git("rev-parse", "HEAD").strip()][0]
        with self.assertRaisesRegex(LedgerError, "not a push of anchor commit"):
            self.ledger.record_receipt("CASE", "KOD-P-R", later, "owner/repo")

    def test_stored_receipt_is_rechecked_against_github(self):
        # Protects against: editing the stored receipt time; GitHub is asked again.
        self.open_case()
        anchor_sha = self.ledger.rows("SELECT git_commit FROM anchors WHERE record_id = 'KOD-P-R'")[
            0
        ][0]
        run = self.lab.github.runs[anchor_sha][0]
        self.ledger.record_receipt("CASE", "KOD-P-R", run, "owner/repo")
        self.assertEqual(self.status("KOD-P-R")["status"], AUTHORITATIVE)
        conn = sqlite3.connect(self.ledger.path)
        conn.execute("DROP TRIGGER receipts_no_update")
        conn.execute(
            "UPDATE remote_timestamp_receipts SET remote_created_at = '2026-10-01T00:00:00Z'"
        )
        conn.commit()
        conn.close()
        self.assertEqual(self.status("KOD-P-R")["status"], MISMATCH)
        self.assertFalse(self.verify()["ok"])

    def test_deleted_run_makes_the_case_unverified_not_earlier(self):
        # Protects against: receipt deletion being mistaken for proof; it only removes proof.
        self.open_case()
        anchor_sha = self.ledger.rows("SELECT git_commit FROM anchors WHERE record_id = 'KOD-P-R'")[
            0
        ][0]
        self.lab.github.delete(self.lab.github.runs[anchor_sha][0].run_id)
        self.assertEqual(self.status("KOD-P-R")["status"], UNVERIFIED)

    def test_no_api_access_is_reported_and_excluded(self):
        self.open_case()
        self.lab.github.available = False
        judged = self.status("KOD-P-R")
        self.assertEqual(judged["status"], UNVERIFIED)
        self.assertIn("switched off", judged["reason"])
        self.assertTrue(
            self.verify()["ok"]
        )  # unverifiable is not corruption: it is excluded, not failed


class GitHubClientHTTP(unittest.TestCase):
    """The real client against a local stand-in for api.github.com."""

    @classmethod
    def setUpClass(cls):
        cls.seen = []
        runs = {
            "workflow_runs": [
                {
                    "id": 7,
                    "head_sha": "a" * 40,
                    "event": "push",
                    "created_at": "2026-10-07T09:00:05Z",
                    "html_url": "u7",
                },
                {
                    "id": 8,
                    "head_sha": "a" * 40,
                    "event": "workflow_dispatch",
                    "created_at": "2026-10-07T08:00:00Z",
                    "html_url": "u8",
                },
            ]
        }

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                cls.seen.append((self.path, self.headers.get("Authorization")))
                if self.path.startswith("/repos/o/r/actions/runs?"):
                    body = json.dumps(runs).encode()
                    self.send_response(200)
                else:
                    body = b'{"message": "Not Found"}'
                    self.send_response(404)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.client = GitHubActionsClient("o/r", "tok", f"http://127.0.0.1:{cls.server.server_port}")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_runs_are_read_with_auth_and_only_push_events_count(self):
        from kod.remote import earliest_exact

        runs = self.client.runs_for_commit("a" * 40)
        self.assertEqual(self.seen[-1][1], "Bearer tok")
        self.assertIn("head_sha=" + "a" * 40, self.seen[-1][0])
        self.assertEqual(
            earliest_exact(runs, "a" * 40).run_id, "7"
        )  # the earlier dispatch run is not a push

    def test_api_errors_raise_unavailable(self):
        with self.assertRaises(RemoteUnavailable):
            self.client.run("99")

    def test_repository_is_read_from_the_git_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            import subprocess

            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/jon/KOD-Machine.git"],
                cwd=tmp,
                check=True,
            )
            self.assertEqual(repository_from_git(Path(tmp)), "jon/KOD-Machine")


class S3FrozenDetectorOutputsAndCode(LabTest):
    def test_detector_code_change_without_new_version_is_refused(self):
        # Protects against: editing a detector in place so old calls appear to have said something else.
        with mock.patch("kod.ledger.detector_source_sha", return_value="f" * 64):
            with self.assertRaisesRegex(LedgerError, "a changed detector is a new rule version"):
                open_and_evaluate(self.ledger, self.card())
        with mock.patch("kod.verify.detector_source_sha", return_value="f" * 64):
            result = self.verify()
        self.assertFalse(result["ok"])

    def test_new_rule_version_leaves_old_calls_intact(self):
        # Protects against: a version bump rewriting what earlier cards evaluated.
        open_and_evaluate(self.ledger, self.card(case_id="KOD-P-OLD"))
        patches = [
            mock.patch(target, "KOD-DET-v1")
            for target in (
                "kod.detectors.RULE_VERSION",
                "kod.ledger.RULE_VERSION",
                "kod.verify.RULE_VERSION",
            )
        ]
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch("kod.ledger.detector_source_sha", return_value="e" * 64),
            mock.patch("kod.verify.detector_source_sha", return_value="e" * 64),
        ):
            ledger = Ledger(self.ledger.path, anchor=self.lab.anchor, clock=self.clock)
            open_and_evaluate(ledger, self.card(case_id="KOD-P-NEW"))
            versions = {
                r["case_id"]: r["detector_rule_version"] for r in ledger.rows("SELECT * FROM cases")
            }
            self.assertEqual(versions, {"KOD-P-OLD": "KOD-DET-v0", "KOD-P-NEW": "KOD-DET-v1"})
            old = {
                r["status"]
                for r in ledger.rows(
                    "SELECT rule_version AS status FROM detector_evaluations WHERE case_id = 'KOD-P-OLD'"
                )
            }
            self.assertEqual(old, {"KOD-DET-v0"})
            self.assertTrue(
                verify(ledger, self.lab.anchor, self.lab.timestamper, self.lab.github)["ok"]
            )
            ledger.conn.close()

    def test_outcome_never_reaches_the_detectors(self):
        # Protects against: an outcome field on a card influencing what the detectors say.
        seen = []
        from kod import detectors

        def spy(sets):
            seen.append(json.dumps(sets, sort_keys=True))
            return detectors.evaluate(sets)

        card = self.card()
        card["outcome"] = {"outcome_label": "REPRICED_UP", "window_return_pct": 50.0}
        with mock.patch("kod.ledger.evaluate", spy):
            sha = open_and_evaluate(self.ledger, card)
            self.clock.moment = self.clock() + timedelta(days=6)
            self.ledger.close_case("KOD-P-T-1", {**OUTCOME, "card_sha": sha})
        self.assertEqual(len(seen), 1)
        self.assertNotIn("REPRICED_UP", seen[0])
        self.assertEqual(set(json.loads(seen[0])), {"T-30D", "T-72H", "T-24H"})

    def test_card_freezes_rule_version_and_code_hash(self):
        open_and_evaluate(self.ledger, self.card())
        card = json.loads(self.lab.git("show", "HEAD:registry/cards/KOD-P-T-1.json"))
        self.assertEqual(card["card_hash_version"], "KOD-CARD-v3")
        self.assertEqual(card["integrity_level"], "STRICT-v3")
        self.assertEqual(card["detector"]["rule_version"], "KOD-DET-v0")
        self.assertEqual(len(card["detector"]["code_sha256"]), 64)


class S4ExactHorizons(LabTest):
    def test_timezone_offsets_are_normalised(self):
        card = self.card()
        cutoff = self.clock() - timedelta(minutes=20)
        card["decision_cutoff"] = cutoff.astimezone(
            __import__("datetime").timezone(timedelta(hours=7))
        ).isoformat()
        open_and_evaluate(self.ledger, card)  # same instant written in WIB: accepted

    def test_one_second_off_is_refused(self):
        card = self.card()
        cutoff = self.clock() - timedelta(minutes=20)
        card["information_sets"]["T-24H"]["cutoff"] = fmt_ts(
            cutoff - timedelta(hours=24, seconds=1)
        )
        with self.assertRaisesRegex(LedgerError, "T-24H cutoff"):
            open_and_evaluate(self.ledger, card)

    def test_label_must_match_its_offset(self):
        card = self.card()
        sets = card["information_sets"]
        sets["T-72H"], sets["T-24H"] = (
            sets["T-24H"],
            sets["T-72H"],
        )  # right timestamps, wrong labels
        with self.assertRaisesRegex(LedgerError, "T-72H cutoff .* must be"):
            open_and_evaluate(self.ledger, card)

    def test_unknown_horizon_label_is_refused(self):
        card = self.card()
        card["information_sets"]["T-48H"] = dict(card["information_sets"]["T-24H"])
        with self.assertRaisesRegex(LedgerError, "unexpected \\['T-48H'\\]"):
            open_and_evaluate(self.ledger, card)


class S0LegacyRecordsStillVerify(unittest.TestCase):
    def test_committed_ledger_verifies_under_new_code(self):
        # Protects against: the migration or a new hash recipe breaking existing v1 seed cards.
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "kod.db"
            shutil.copy(KOD_ROOT / "var" / "kod.db", db)
            ledger = Ledger(db, anchor=GitAnchor(KOD_ROOT / "registry"))
            seeds = dict(
                ledger.rows(
                    "SELECT case_id, card_hash_version FROM cases WHERE case_id IN "
                    "('KOD-R-NVDA-20230524', 'KOD-R-SMCI-202408', 'KOD-S-PIPELINE-001')"
                )
            )
            self.assertEqual(
                seeds,
                {
                    "KOD-R-NVDA-20230524": "KOD-CARD-v1",
                    "KOD-R-SMCI-202408": "KOD-CARD-v1",
                    "KOD-S-PIPELINE-001": "KOD-CARD-v1",
                },
            )
            result = verify(ledger, ledger.anchor, None, None)
            ledger.conn.close()
            self.assertTrue(result["ok"], [f for f in result["findings"] if f["level"] == "FAIL"])

    def test_v0_and_v2_recipes_still_rebuild(self):
        # Protects against: silently changing an old recipe instead of adding a version.
        case = {
            "case_id": "C",
            "symbol": "x",
            "venue": "IDX",
            "call_type": "RETROSPECTIVE",
            "decision_cutoff": "2024-01-31T00:00:00Z",
            "story_hypothesis": "h",
            "disposition": "WATCH",
            "universe_id": "u",
            "reconstruction_status": "PARTIAL_PUBLIC",
            "doctrine_sha": "d",
            "outcome_window_start": None,
            "outcome_window_end": None,
            "scan_entry_id": None,
        }
        sets = {
            h: {"cutoff": "2024-01-01T00:00:00Z", "facts": {}} for h in ("T-30D", "T-72H", "T-24H")
        }
        # Pinned: these are the hashes the code at the hardening's starting HEAD (4a63e6f) produces.
        self.assertEqual(
            sha256_obj(freeze_card(case, sets, None, None)),
            "96b5ac3d6629eca8377a8d1d401210ce679dbbb80cb2c9cf08572dc4f75b4307",
        )
        self.assertEqual(
            sha256_obj(freeze_card(case, sets, None, "KOD-CARD-v1")),
            "6a41aeabda9efaba650fecc626063e72e277db60cd9d076f7521a1677e13d596",
        )
        self.assertEqual(
            sha256_obj(freeze_card(case, sets, None, "KOD-CARD-v2", [])),
            "8b080e20ce06647b2c6c0199fbe58f777fde0f452630147255fb36d2cb4d57cf",
        )
        self.assertNotIn("integrity_level", freeze_card(case, sets, None, "KOD-CARD-v2", []))


if __name__ == "__main__":
    unittest.main()
