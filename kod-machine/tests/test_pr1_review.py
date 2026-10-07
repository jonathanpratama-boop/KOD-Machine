"""Regressions for the review of PR #1. Each test names the hole it closes."""

import sqlite3
import unittest
from datetime import timedelta

from kod.cli import open_and_evaluate
from kod.hashing import fmt_ts
from kod.score import build_report
from kod.verify import ANCHOR_FAILED, AUTHORITATIVE, calibration_eligibility, verify
from tests.support import Lab, prospective_card
from tests.test_hardening import entry, scan_payload


def drop_triggers(conn, table):
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall():
        conn.execute(f"DROP TRIGGER {name}")


class DeletedCallsAreNoticed(unittest.TestCase):
    def test_case_deleted_from_the_database_fails_verify(self):
        """Closes: a losing authoritative case deleted from every table (triggers dropped) vanishing
        from verify and from the report while its line stays in opens.jsonl."""
        lab = Lab()
        self.addCleanup(lab.cleanup)
        ledger, clock = lab.ledger, lab.clock
        cut, start = clock() - timedelta(minutes=20), clock() + timedelta(hours=1)
        sha = open_and_evaluate(ledger, prospective_card("KOD-P-LOSER", cut, start, start + timedelta(days=5),
                                                         evidence=[lab.evidence_id]))
        lab.push_head()
        clock.moment += timedelta(days=6)
        ledger.close_case("KOD-P-LOSER", {"window_label": "5D", "outcome_label": "NO_REPRICE", "source": "x",
                                          "card_sha": sha})
        conn = sqlite3.connect(ledger.path)
        for table in ("cases", "information_sets", "detector_evaluations", "critic_notes", "outcomes", "anchors"):
            drop_triggers(conn, table)
            conn.execute(f"DELETE FROM {table} WHERE {'record_id' if table == 'anchors' else 'case_id'} = 'KOD-P-LOSER'")
        conn.commit()
        conn.close()
        result = verify(ledger, lab.anchor, lab.timestamper, lab.github)
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing from the ledger" in f["message"] for f in result["findings"]))


class ScanEligibilityRebuildsTheHash(unittest.TestCase):
    def setUp(self):
        self.lab = Lab()
        self.addCleanup(self.lab.cleanup)

    def status(self):
        return calibration_eligibility(self.lab.ledger, self.lab.anchor, self.lab.github)[("SCAN", "SCAN-T-1")]["status"]

    def test_edited_window_start_cannot_turn_a_late_scan_authoritative(self):
        """Closes: moving a stored outcome_window_start later so a scan that reached GitHub after its
        window opened is counted."""
        lab = self.lab
        lab.ledger.log_scan(scan_payload(lab.clock, [entry("AAAA", True, True)]))
        lab.push_head(lab.clock() + timedelta(days=2))
        self.assertNotEqual(self.status(), AUTHORITATIVE)
        conn = sqlite3.connect(lab.ledger.path)
        drop_triggers(conn, "scan_runs")
        conn.execute("UPDATE scan_runs SET outcome_window_start = ?", (fmt_ts(lab.clock() + timedelta(days=3)),))
        conn.commit()
        conn.close()
        self.assertEqual(self.status(), ANCHOR_FAILED)

    def test_entry_inserted_into_an_authoritative_scan_disqualifies_it(self):
        """Closes: an extra flagged winner inserted into an already-authoritative scan feeding the lift table."""
        lab = self.lab
        sha = lab.ledger.log_scan(scan_payload(lab.clock, [entry("AAAA", True, True), entry("BBBB", False, False)]))
        lab.push_head()
        self.assertEqual(self.status(), AUTHORITATIVE)
        lab.ledger.conn.execute(
            "INSERT INTO scan_entries(entry_id, scan_id, symbol, venue, flagged, reconstruction_status, facts_json, "
            "entry_sha, recorded_at) VALUES (?,?,?,?,?,?,?,?,?)",
            ("SCAN-T-1:ZZZZ", "SCAN-T-1", "ZZZZ", "IDX", 1, "PARTIAL_PUBLIC", "{}", "0" * 64, fmt_ts(lab.clock())))
        lab.ledger.conn.commit()
        self.assertEqual(self.status(), ANCHOR_FAILED)
        report = build_report(lab.ledger, lab.anchor, lab.github)
        self.assertNotIn("SCAN-T-1", str(report["scan_log"].get("authoritative_scans", [])))
        self.assertTrue(sha)


if __name__ == "__main__":
    unittest.main()
