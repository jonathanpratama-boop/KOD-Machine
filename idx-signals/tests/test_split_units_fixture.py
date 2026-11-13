"""SPLIT_UNITS_V1 against the pinned observations of the KODCHECK challenge cases.

The expected classes in fixtures/split_units_cases.json were written by a separate agent from the rule text
(research/SPLIT_REVISIONS_v1/CONTRACT.md, part A) before any implementation existed. This module only loads them.
"""

import json
import unittest
from pathlib import Path

from idxsig import split_units

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "split_units_cases.json"


class PinnedObservations(unittest.TestCase):
    def test_every_pinned_class(self):
        rows = json.loads(FIXTURE.read_text(encoding="utf-8"))["rows"]
        self.assertEqual(len(rows), 178)
        for r in rows:
            with self.subTest(case=r["case"], observation=r["observation"]):
                got = split_units.classify(
                    r["close"],
                    r["previous"],
                    r["signal_session"],
                    r["events"],
                    [tuple(b) for b in r["bars"]],
                    r["previous_session"],
                    r["retrieved_on"],
                )
                self.assertEqual(got["class"], r["expected_class"])
                self.assertEqual(got["group"], split_units.GROUP[r["expected_class"]])

    def test_every_class_is_pinned_at_least_once(self):
        rows = json.loads(FIXTURE.read_text(encoding="utf-8"))["rows"]
        self.assertEqual({r["expected_class"] for r in rows}, set(split_units.CLASSES))


if __name__ == "__main__":
    unittest.main()
