import json
from pathlib import Path
import tempfile
import unittest

from idxsig.experiment_catalog import load_catalog


def record():
    return {"id": "X", "status": "RESEARCH_CLOSED", "evidence_level": "REPORTED_RETROSPECTIVE",
            "live_eligible": False, "limitations": ["not rerun"],
            "sources": [{"path": "evidence/report.md", "ref": "a" * 40}]}


class CatalogSafety(unittest.TestCase):
    def write(self, root, records):
        (root / "configs").mkdir(exist_ok=True)
        (root / "configs/experiments.json").write_text(json.dumps({"schema_version": 1, "experiments": records}))

    def test_missing_source_is_explicit_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, [record()])
            r = load_catalog(root)[0]
            self.assertEqual(r["source_status"], "SOURCE_MISSING")
            self.assertEqual(r["missing_sources"], ["evidence/report.md"])
            (root / "evidence").mkdir()
            (root / "evidence/report.md").write_text("reported result")
            self.assertEqual(load_catalog(root)[0]["source_status"], "PRESENT_NOT_RERUN")

    def test_catalog_cannot_grant_live_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = record()
            row["live_eligible"] = True
            self.write(root, [row])
            with self.assertRaisesRegex(ValueError, "live eligibility"):
                load_catalog(root)

    def test_duplicate_experiment_or_escaping_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, [record(), record()])
            with self.assertRaisesRegex(ValueError, "unique"):
                load_catalog(root)
            row = record()
            row["sources"][0]["path"] = "../outside.md"
            self.write(root, [row])
            with self.assertRaisesRegex(ValueError, "inside"):
                load_catalog(root)


if __name__ == "__main__":
    unittest.main()
