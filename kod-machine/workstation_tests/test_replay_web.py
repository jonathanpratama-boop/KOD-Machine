"""Offline UI checks against the repository's preserved, retrospective ZEAL case."""
from pathlib import Path
import re
import tempfile
import unittest

from fastapi.testclient import TestClient

from kod.workstation.web import create_app


ROOT = Path(__file__).resolve().parents[1]
CASE = "KOD-R-ZEAL-20250312"
LATE = "2026-10-30T00:00:00Z"
EARLY = "2025-03-11T16:00:00Z"


class ReplayWebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client = TestClient(create_app(self.tmp.name, testing=True, offline=True))
        self.addCleanup(self.client.close)

    def page(self, **params):
        response = self.client.get("/replay", params={"case_id": CASE, "as_of": LATE, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return response.text

    def test_integrated_navigation_and_historical_withholding(self):
        self.assertIn('href="/replay"', self.client.get("/").text)
        page = self.page(as_of=EARLY)
        self.assertIn("No recorded call at this cutoff", page)
        self.assertIn("No evidence available at this cutoff", page)
        self.assertIn("Historical reconstruction, not a prediction", page)
        self.assertNotIn("Partnering of the obesity candidates", page)
        self.assertNotIn("REPRICED_UP", page)

    def test_separate_reveal_and_default_response_contains_no_outcome(self):
        page = self.page()
        self.assertIn("Recorded retrospective reconstruction", page)
        self.assertIn("Reveal outcome", page)
        self.assertNotIn("REPRICED UP", page)
        revealed = self.page(reveal="outcome")
        self.assertIn("REPRICED UP", revealed)
        self.assertIn("Hide outcome", revealed)
        # A fresh replay request carries no previous reveal state.
        self.assertNotIn("REPRICED UP", self.page())
        earlier = self.page(as_of=EARLY, reveal="outcome")
        self.assertNotIn("REPRICED UP", earlier)
        self.assertIn("No outcome recorded by this cutoff", earlier)

    def test_sandbox_does_not_change_original_identity_or_record(self):
        original, filtered = self.page(), self.page(minimum_grade="A")
        pattern = r"Original snapshot SHA-256 <code>([a-f0-9]{64})</code>"
        self.assertEqual(re.search(pattern, original).group(1), re.search(pattern, filtered).group(1))
        self.assertIn("0 / 8", filtered)
        self.assertIn("8 / 8", original)
        for page in (original, filtered):
            self.assertIn("WATCH", page)
            self.assertIn("Recorded retrospective reconstruction", page)
            self.assertIn("No strategy threshold or model prediction is recalculated", page)

    def test_controls_reset_reveal_and_sandbox(self):
        page = self.page(reveal="outcome", minimum_grade="A")
        controls = re.search(r'<form class="filter-bar panel replay-controls".*?</form>', page, re.S).group(0)
        self.assertNotIn('name="reveal"', controls)
        self.assertNotIn('name="minimum_grade"', controls)
        timeline = re.search(r'<nav class="replay-timeline".*?</nav>', page, re.S).group(0)
        self.assertNotIn("reveal=", timeline)
        self.assertNotIn("minimum_grade=", timeline)

    def test_invalid_inputs_and_unknown_case_fail_closed(self):
        for params in ({"as_of": "2025-03-11"}, {"minimum_grade": "Z"}):
            self.assertEqual(self.client.get("/replay", params={"case_id": CASE, **params}).status_code, 400)
        self.assertEqual(self.client.get("/replay", params={"case_id": "../../other.db"}).status_code, 404)

    def test_missing_ledger_is_honest_and_not_created(self):
        absent = Path(self.tmp.name) / "absent.db"
        with TestClient(create_app(Path(self.tmp.name) / "other", testing=True, replay_db=absent)) as client:
            page = client.get("/replay")
            self.assertEqual(page.status_code, 200)
            self.assertIn("Replay unavailable", page.text)
            self.assertIn("no database was created", page.text)
        self.assertFalse(absent.exists())


if __name__ == "__main__":
    unittest.main()
