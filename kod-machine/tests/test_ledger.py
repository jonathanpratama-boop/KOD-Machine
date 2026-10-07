import json
import tempfile
import unittest
from pathlib import Path

from kod.cli import load_seed, open_and_evaluate
from kod.ledger import Ledger, LedgerError
from kod.score import build_report

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "seeds" / "retrospective_cases.json"


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "kod.db"
        self.ledger = Ledger(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_and_calibration_excludes_hindsight(self):
        load_seed(self.ledger, SEED)
        report = build_report(self.ledger)
        self.assertEqual(report["counts"]["retrospective"], 2)
        self.assertEqual(report["counts"]["simulated_excluded"], 1)
        self.assertEqual(report["counts"]["prospective_open"], 1)
        self.assertEqual(report["counts"]["prospective_closed"], 0)
        self.assertEqual(report["calibration_status"], "NOT_STARTED")
        self.assertEqual(report["detector_table"], [])
        self.assertFalse(report["entry_permission"])

    def test_append_only(self):
        load_seed(self.ledger, SEED)
        self.ledger.assert_immutable()
        with self.assertRaises(LedgerError):
            self.ledger.close_case(
                "KOD-R-NVDA-20230524",
                {"window_label": "rewrite", "outcome_label": "NO_REPRICE", "source": "no"},
            )

    def test_investigate_requires_critic(self):
        card = json.loads(SEED.read_text())["cases"][0]
        card["case_id"] = "KOD-R-NO-CRITIC"
        card["critic"] = None
        card["disposition"] = "INVESTIGATE"
        with self.assertRaises(LedgerError):
            open_and_evaluate(self.ledger, card)

    def test_entry_eligible_refused(self):
        card = json.loads(SEED.read_text())["cases"][2]
        card["case_id"] = "KOD-P-ILLEGAL"
        card["disposition"] = "ENTRY_ELIGIBLE"
        with self.assertRaises(LedgerError):
            open_and_evaluate(self.ledger, card)

    def test_prospective_close_checks_hash(self):
        card = json.loads(SEED.read_text())["cases"][2]
        card["case_id"] = "KOD-P-HASH"
        open_and_evaluate(self.ledger, card)
        with self.assertRaises(LedgerError):
            self.ledger.close_case(
                "KOD-P-HASH",
                {
                    "window_label": "5d",
                    "outcome_label": "NO_REPRICE",
                    "source": "test",
                    "card_sha": "0" * 64,
                },
            )


if __name__ == "__main__":
    unittest.main()
