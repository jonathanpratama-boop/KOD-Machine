import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig import guidance_margin_unit_retry as repair


class TestUnitRetry(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.event = "a" * 24
        self.entry = {"status": "EXTRACTION_REJECTED"}
        self.store()
        self.out = self.root / "reader" / self.event
        self.out.mkdir(parents=True)
        (self.out / "response.json").write_text("{}")

    def store(self):
        (self.root / "feed_state.json").write_text(
            json.dumps({"entries": {self.event: self.entry}})
        )

    def test_unrelated_rejection_keeps_its_original_result(self):
        metric = {"unit": "PERCENT", "point": {"quote": "5 percent"}}
        output = {"current": {"operating_margin": metric}, "prior": {}}
        with patch.object(repair.reader, "_response_output", return_value=("CANDIDATE", output)):
            with self.assertRaisesRegex(ValueError, "unsupported USD scale"):
                repair.retry(self.root, self.event)
        self.assertFalse((self.root / "unit_reviews").exists())

    def test_replay_is_idempotent_even_if_status_has_since_changed(self):
        self.entry.update(status="AGENT_REVIEWED", unit_review_attempt=self.event + "-units-v2")
        self.store()
        with patch.object(repair.feed, "process_packet", side_effect=AssertionError):
            self.assertEqual(repair.retry(self.root, self.event), "AGENT_REVIEWED")

    def test_admitted_case_cannot_be_reread(self):
        (self.root / "approved").mkdir()
        (self.root / "approved" / (self.event + ".json")).write_text("{}")
        with self.assertRaisesRegex(ValueError, "unadmitted"):
            repair.retry(self.root, self.event)
