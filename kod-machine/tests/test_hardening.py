"""One test class per hardening rule.

1. Prospective opens: decision_cutoff within 1 hour of the open, and before the window starts.
2. Closes: card_sha is mandatory and must match; no close before the window ends.
3. `verify` recomputes every card hash from stored rows; each open's hash is committed to git.
4. Every scanned name is logged, opened or not; detectors report signal and no-signal hit
   rates and lift over the base rate.
"""

import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from kod.anchor import GitAnchor
from kod.cli import load_seed, open_and_evaluate
from kod.hashing import fmt_ts
from kod.ledger import Ledger, LedgerError
from kod.score import build_report, render_markdown
from kod.verify import verify
from tests.support import T0, Lab, prospective_card

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "seeds" / "retrospective_cases.json"
OUTCOME = {"window_label": "5 sessions", "outcome_label": "REPRICED_UP", "window_return_pct": 9.1, "source": "test close series"}


class LabTest(unittest.TestCase):
    def setUp(self):
        self.lab = Lab()
        self.ledger = self.lab.ledger
        self.clock = self.lab.clock

    def tearDown(self):
        self.lab.cleanup()

    def card(self, case_id="KOD-P-T-1", cutoff_offset=timedelta(minutes=-20),
             start_offset=timedelta(hours=1), length=timedelta(days=5), **kw):
        cutoff = self.clock() + cutoff_offset
        start = self.clock() + start_offset
        return prospective_card(case_id, cutoff, start, start + length, **kw)

    def case_rows(self):
        return self.ledger.rows("SELECT case_id FROM cases")

    def registry_lines(self):
        path = self.lab.registry / "opens.jsonl"
        return path.read_text().splitlines() if path.exists() else []


class Rule1ProspectiveOpenTiming(LabTest):
    def test_cutoff_more_than_one_hour_before_open_is_refused(self):
        with self.assertRaisesRegex(LedgerError, "within 1:00:00"):
            open_and_evaluate(self.ledger, self.card(cutoff_offset=timedelta(hours=-1, seconds=-1)))
        self.assertEqual(self.case_rows(), [])
        self.assertEqual(self.registry_lines(), [])

    def test_cutoff_more_than_one_hour_after_open_is_refused(self):
        with self.assertRaisesRegex(LedgerError, "within 1:00:00"):
            open_and_evaluate(self.ledger, self.card(cutoff_offset=timedelta(hours=2), start_offset=timedelta(hours=3)))

    def test_cutoff_inside_one_hour_is_accepted(self):
        digest = open_and_evaluate(self.ledger, self.card(cutoff_offset=timedelta(minutes=-59)))
        self.assertEqual(len(digest), 64)
        self.assertEqual(len(self.case_rows()), 1)

    def test_cutoff_at_or_after_window_start_is_refused(self):
        card = self.card(cutoff_offset=timedelta(minutes=30), start_offset=timedelta(minutes=30))
        with self.assertRaisesRegex(LedgerError, "not before the outcome window start"):
            open_and_evaluate(self.ledger, card)

    def test_open_after_window_start_is_refused(self):
        card = self.card(cutoff_offset=timedelta(minutes=-30), start_offset=timedelta(minutes=-10))
        with self.assertRaisesRegex(LedgerError, "outcome window started"):
            open_and_evaluate(self.ledger, card)

    def test_missing_window_is_refused(self):
        card = self.card()
        del card["outcome_window"]
        with self.assertRaisesRegex(LedgerError, "outcome_window"):
            open_and_evaluate(self.ledger, card)

    def test_information_set_after_cutoff_is_refused(self):
        card = self.card()
        card["information_sets"]["T-24H"]["cutoff"] = fmt_ts(self.clock() + timedelta(minutes=5))
        with self.assertRaisesRegex(LedgerError, "T-24H cutoff"):
            open_and_evaluate(self.ledger, card)

    def test_timezone_is_required(self):
        card = self.card()
        card["decision_cutoff"] = "2026-10-07T08:50:00"
        with self.assertRaisesRegex(LedgerError, "no timezone"):
            open_and_evaluate(self.ledger, card)

    def test_template_cannot_be_opened(self):
        template = json.loads((ROOT / "seeds" / "prospective_template.json").read_text())
        with self.assertRaises(LedgerError):
            open_and_evaluate(self.ledger, template)

    def test_prospective_open_needs_an_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare = Ledger(Path(tmp) / "kod.db", clock=self.clock)
            with self.assertRaisesRegex(LedgerError, "no git anchor"):
                open_and_evaluate(bare, self.card())
            bare.conn.close()


class Rule2Close(LabTest):
    def setUp(self):
        super().setUp()
        self.digest = open_and_evaluate(self.ledger, self.card())
        self.window_end = self.clock() + timedelta(hours=1) + timedelta(days=5)

    def test_card_sha_is_mandatory(self):
        self.clock.moment = self.window_end + timedelta(minutes=1)
        with self.assertRaisesRegex(LedgerError, "card_sha .* is required"):
            self.ledger.close_case("KOD-P-T-1", OUTCOME)

    def test_card_sha_must_match(self):
        self.clock.moment = self.window_end + timedelta(minutes=1)
        with self.assertRaisesRegex(LedgerError, "does not match"):
            self.ledger.close_case("KOD-P-T-1", {**OUTCOME, "card_sha": "f" * 64})

    def test_close_before_window_end_is_refused(self):
        self.clock.moment = self.window_end - timedelta(seconds=1)
        with self.assertRaisesRegex(LedgerError, "outcome window ends"):
            self.ledger.close_case("KOD-P-T-1", {**OUTCOME, "card_sha": self.digest})
        self.assertEqual(self.ledger.rows("SELECT * FROM outcomes"), [])

    def test_close_after_window_end_with_hash_is_accepted_once(self):
        self.clock.moment = self.window_end
        self.ledger.close_case("KOD-P-T-1", {**OUTCOME, "card_sha": self.digest})
        with self.assertRaisesRegex(LedgerError, "already recorded"):
            self.ledger.close_case("KOD-P-T-1", {**OUTCOME, "outcome_label": "NO_REPRICE", "card_sha": self.digest})

    def test_retrospective_close_also_needs_card_sha(self):
        card = json.loads(SEED.read_text())["cases"][0]
        digest = open_and_evaluate(self.ledger, card)
        with self.assertRaisesRegex(LedgerError, "card_sha"):
            self.ledger.close_case(card["case_id"], card["outcome"])
        self.ledger.close_case(card["case_id"], {**card["outcome"], "card_sha": digest})


class Rule3VerifyAndGitAnchor(LabTest):
    def setUp(self):
        super().setUp()
        load_seed(self.ledger, SEED)
        self.digest = open_and_evaluate(self.ledger, self.card())

    def test_open_hash_is_committed_to_git(self):
        committed = self.lab.git("show", "HEAD:registry/opens.jsonl")
        record = json.loads(committed.splitlines()[-1])
        self.assertEqual(record["record_id"], "KOD-P-T-1")
        self.assertEqual(record["sha256"], self.digest)
        card = json.loads(self.lab.git("show", "HEAD:registry/cards/KOD-P-T-1.json"))
        self.assertEqual(card["case_id"], "KOD-P-T-1")
        self.assertIn("kod anchor case KOD-P-T-1", self.lab.git("log", "-1", "--format=%s"))
        self.assertEqual(self.lab.git("status", "--porcelain"), "")

    def test_clean_ledger_verifies(self):
        result = verify(self.ledger, self.lab.anchor)
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["stats"]["cases"], 4)
        self.assertEqual(result["stats"]["anchors_verified"], 4)
        fails = [f for f in result["findings"] if f["level"] == "FAIL"]
        self.assertEqual(fails, [])

    def _tamper(self, sql: str, params=()):
        conn = sqlite3.connect(self.ledger.path)
        for table in ("cases", "information_sets", "anchors"):
            for op in ("update", "delete"):
                prefix = {"cases": "cases", "information_sets": "sets", "anchors": "anchors"}[table]
                conn.execute(f"DROP TRIGGER IF EXISTS {prefix}_no_{op}")
        conn.execute(sql, params)
        conn.commit()
        conn.close()

    def test_edited_case_row_fails_verify(self):
        self._tamper("UPDATE cases SET story_hypothesis = 'rewritten after the outcome' WHERE case_id = 'KOD-P-T-1'")
        result = verify(self.ledger, self.lab.anchor)
        self.assertFalse(result["ok"])
        self.assertTrue(any("KOD-P-T-1" in f["subject"] and "hash to" in f["message"] for f in result["findings"]))

    def test_edited_information_set_fails_verify(self):
        self._tamper("UPDATE information_sets SET payload_json = '{}' WHERE set_id = 'KOD-P-T-1:T-24H'")
        self.assertFalse(verify(self.ledger, self.lab.anchor)["ok"])

    def test_rewritten_hash_everywhere_in_the_db_still_fails_against_git(self):
        conn = sqlite3.connect(self.ledger.path)
        conn.row_factory = sqlite3.Row
        conn.close()
        self._tamper("UPDATE cases SET disposition = 'REJECT' WHERE case_id = 'KOD-P-T-1'")
        # Recompute the forged hash and write it into every DB copy.
        from kod.ledger import freeze_card
        from kod.hashing import sha256_obj
        row = dict(self.ledger.rows("SELECT * FROM cases WHERE case_id = 'KOD-P-T-1'")[0])
        sets = {r["horizon"]: json.loads(r["payload_json"]) for r in self.ledger.rows(
            "SELECT * FROM information_sets WHERE case_id = 'KOD-P-T-1'")}
        critic = dict(self.ledger.rows("SELECT * FROM critic_notes WHERE case_id = 'KOD-P-T-1'")[0])
        forged = sha256_obj(freeze_card(row, sets, critic, row["card_hash_version"]))
        self._tamper("UPDATE cases SET card_sha = ? WHERE case_id = 'KOD-P-T-1'", (forged,))
        self._tamper("UPDATE anchors SET anchored_sha = ? WHERE record_id = 'KOD-P-T-1'", (forged,))
        result = verify(self.ledger, self.lab.anchor)
        self.assertFalse(result["ok"])
        self.assertTrue(any("does not contain this hash" in f["message"] for f in result["findings"]))

    def test_registry_line_removed_from_git_fails_verify(self):
        path = self.lab.registry / "opens.jsonl"
        kept = [line for line in path.read_text().splitlines() if "KOD-P-T-1" not in line]
        path.write_text("\n".join(kept) + "\n")
        self.lab.git("commit", "-q", "-am", "drop a line")
        result = verify(self.ledger, self.lab.anchor)
        self.assertFalse(result["ok"])
        self.assertTrue(any("removed" in f["message"] for f in result["findings"]))

    def test_anchor_committed_after_window_start_fails_verify(self):
        late = fmt_ts(self.clock() + timedelta(days=2))
        self.lab.anchor.extra_env = lambda: {"GIT_AUTHOR_DATE": late, "GIT_COMMITTER_DATE": late}
        open_and_evaluate(self.ledger, self.card(case_id="KOD-P-LATE"))
        result = verify(self.ledger, self.lab.anchor)
        self.assertFalse(result["ok"])
        self.assertTrue(any(
            f["subject"] == "case KOD-P-LATE" and "not before the outcome window start" in f["message"]
            for f in result["findings"]
        ))

    def test_anchor_failure_rolls_back_the_open(self):
        with tempfile.TemporaryDirectory() as outside:
            ledger = Ledger(Path(outside) / "kod.db", anchor=GitAnchor(Path(outside) / "registry"), clock=self.clock)
            with self.assertRaisesRegex(LedgerError, "git anchor failed"):
                open_and_evaluate(ledger, self.card(case_id="KOD-P-T-2"))
            self.assertEqual(ledger.rows("SELECT * FROM cases"), [])
            ledger.conn.close()

    def test_registry_with_uncommitted_edits_refuses_new_anchor(self):
        (self.lab.registry / "opens.jsonl").write_text("tampered\n")
        with self.assertRaisesRegex(LedgerError, "uncommitted edits"):
            open_and_evaluate(self.ledger, self.card(case_id="KOD-P-T-3"))
        self.assertEqual(len(self.ledger.rows("SELECT * FROM cases WHERE case_id = 'KOD-P-T-3'")), 0)


def scan_payload(clock, entries, scan_id="SCAN-T-1", hit_label="REPRICED_UP"):
    return {
        "scan_id": scan_id,
        "scanner": "ASTRA",
        "universe_id": "IDX-TEST",
        "decision_cutoff": fmt_ts(clock() - timedelta(minutes=5)),
        "outcome_window": {"start": fmt_ts(clock() + timedelta(hours=1)), "end": fmt_ts(clock() + timedelta(days=5))},
        "hit_label": hit_label,
        "entries": entries,
    }


def entry(symbol, flagged, catalyst):
    return {
        "symbol": symbol,
        "venue": "IDX",
        "flagged": flagged,
        "reconstruction_status": "PARTIAL_PUBLIC",
        "facts": {"dated_catalyst_known": catalyst},
    }


class Rule4ScanLogAndLift(LabTest):
    def setUp(self):
        super().setUp()
        # 10 names. Flagged: A-D (3 hits). Not flagged: E-J (1 hit). Base rate 4/10.
        # DATED_CATALYST_KNOWN fires on A, B, E, F (2 hits of 4); silent on the rest (2 hits of 6).
        self.names = {
            "AAAA": (True, True, "REPRICED_UP"),
            "BBBB": (True, True, "REPRICED_UP"),
            "CCCC": (True, False, "REPRICED_UP"),
            "DDDD": (True, False, "NO_REPRICE"),
            "EEEE": (False, True, "NO_REPRICE"),
            "FFFF": (False, True, "NO_REPRICE"),
            "GGGG": (False, False, "REPRICED_UP"),
            "HHHH": (False, False, "REPRICED_DOWN"),
            "IIII": (False, False, "NO_REPRICE"),
            "JJJJ": (False, None, "NO_REPRICE"),
        }
        scan = scan_payload(self.clock, [entry(s, f, c) for s, (f, c, _) in self.names.items()])
        self.scan_sha = self.ledger.log_scan(scan)
        self.window_end = self.clock() + timedelta(days=5)

    def outcomes(self):
        return {
            "scan_id": "SCAN-T-1",
            "scan_sha": self.scan_sha,
            "outcomes": [
                {"symbol": s, "outcome_label": label, "source": "test close series"}
                for s, (_, _, label) in self.names.items()
            ],
        }

    def test_every_name_is_logged_and_anchored(self):
        self.assertEqual(len(self.ledger.rows("SELECT * FROM scan_entries")), 10)
        self.assertEqual(len(self.ledger.rows("SELECT * FROM scan_entries WHERE flagged = 0")), 6)
        self.assertEqual(len(self.ledger.rows("SELECT * FROM scan_evaluations")), 50)
        record = json.loads(self.lab.git("show", "HEAD:registry/scans.jsonl").splitlines()[-1])
        self.assertEqual(record["sha256"], self.scan_sha)
        self.assertEqual(record["n_entries"], 10)

    def test_opened_and_not_opened_flags_are_counted(self):
        card = self.card(case_id="KOD-P-AAAA", scan_entry_id="SCAN-T-1:AAAA")
        open_and_evaluate(self.ledger, card)
        counts = build_report(self.ledger)["counts"]
        self.assertEqual(counts["scan_flagged"], 4)
        self.assertEqual(counts["scan_flagged_opened"], 1)
        self.assertEqual(counts["scan_flagged_not_opened"], 3)

    def test_unknown_scan_entry_link_is_refused(self):
        with self.assertRaisesRegex(LedgerError, "unknown scan entry"):
            open_and_evaluate(self.ledger, self.card(case_id="KOD-P-X", scan_entry_id="SCAN-T-1:ZZZZ"))

    def test_scan_close_rules(self):
        with self.assertRaisesRegex(LedgerError, "outcome window ends"):
            self.ledger.close_scan(self.outcomes())
        self.clock.moment = self.window_end
        with self.assertRaisesRegex(LedgerError, "scan_sha"):
            self.ledger.close_scan({**self.outcomes(), "scan_sha": None})
        with self.assertRaisesRegex(LedgerError, "does not match"):
            self.ledger.close_scan({**self.outcomes(), "scan_sha": "0" * 64})
        self.assertEqual(self.ledger.close_scan(self.outcomes()), 10)

    def test_overdue_unclosed_names_are_visible(self):
        self.clock.moment = self.window_end + timedelta(days=1)
        partial = self.outcomes()
        partial["outcomes"] = partial["outcomes"][:4]  # only the flagged names
        self.ledger.close_scan(partial)
        self.assertEqual(build_report(self.ledger)["counts"]["scan_overdue_unclosed"], 6)

    def test_signal_and_no_signal_hit_rates_and_lift(self):
        self.clock.moment = self.window_end
        self.ledger.close_scan(self.outcomes())
        rows = {r["detector"]: r for r in build_report(self.ledger)["scan_log"]["lift"]}
        flag = rows["FLAG:ASTRA"]
        self.assertEqual((flag["signals"], flag["signal_hits"]), (4, 3))
        self.assertEqual((flag["no_signal"], flag["no_signal_hits"]), (6, 1))
        self.assertAlmostEqual(flag["base_rate"], 0.4)
        self.assertAlmostEqual(flag["lift"], 0.75 / 0.4)
        cat = rows["DATED_CATALYST_KNOWN"]
        self.assertEqual((cat["signals"], cat["signal_hits"]), (4, 2))
        self.assertEqual((cat["no_signal"], cat["no_signal_hits"]), (5, 2))
        self.assertEqual(cat["insufficient_data"], 1)
        self.assertAlmostEqual(cat["base_rate"], 4 / 9)
        self.assertAlmostEqual(cat["lift"], 0.5 / (4 / 9))
        self.assertIn("FLAG:ASTRA", render_markdown(build_report(self.ledger)))
        self.assertTrue(verify(self.ledger, self.lab.anchor)["ok"])

    def test_prospective_detector_table_has_no_signal_side(self):
        start = self.clock() + timedelta(hours=1)
        open_and_evaluate(self.ledger, self.card(case_id="KOD-P-YES", facts={"dated_catalyst_known": True}))
        sha_yes = self.ledger.rows("SELECT card_sha FROM cases WHERE case_id = 'KOD-P-YES'")[0][0]
        open_and_evaluate(self.ledger, self.card(case_id="KOD-P-NO", facts={"dated_catalyst_known": False}))
        sha_no = self.ledger.rows("SELECT card_sha FROM cases WHERE case_id = 'KOD-P-NO'")[0][0]
        self.clock.moment = start + timedelta(days=5)
        self.ledger.close_case("KOD-P-YES", {**OUTCOME, "card_sha": sha_yes})
        self.ledger.close_case("KOD-P-NO", {**OUTCOME, "outcome_label": "NO_REPRICE", "card_sha": sha_no})
        rows = {r["detector"]: r for r in build_report(self.ledger)["detector_table"]}
        cat = rows["DATED_CATALYST_KNOWN"]
        self.assertEqual(cat["signal_hit_rate"], 1.0)
        self.assertEqual(cat["no_signal_hit_rate"], 0.0)
        self.assertEqual(cat["base_rate"], 0.5)
        self.assertEqual(cat["lift"], 2.0)
        self.assertIsNone(rows["COVERAGE_INCOMPLETE"]["lift"])  # fired on both: no no-signal side

    def test_scan_timing_gate(self):
        late = scan_payload(self.clock, [entry("KKKK", True, True)], scan_id="SCAN-T-2")
        late["decision_cutoff"] = fmt_ts(self.clock() - timedelta(hours=3))
        with self.assertRaisesRegex(LedgerError, "within 1:00:00"):
            self.ledger.log_scan(late)


if __name__ == "__main__":
    unittest.main()
