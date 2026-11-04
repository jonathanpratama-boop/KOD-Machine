"""Keep the formatter away from historical and byte-pinned implementations."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "live_style", Path(__file__).resolve().parents[1] / "check_live_style.py"
)
style = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(style)


class LiveStyleScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tools").mkdir()
        (self.root / "live.py").write_text("VALUE = 1\n")
        (self.root / "pinned.py").write_text("VALUE=1\n")
        self.manifest = {
            "schema_version": "KOD_LIVE_STYLE_V1",
            "managed_paths": ["live.py"],
            "preserved_sha256": {
                "pinned.py": hashlib.sha256((self.root / "pinned.py").read_bytes()).hexdigest()
            },
        }

    def write_manifest(self):
        (self.root / "tools/live_code_style.json").write_text(json.dumps(self.manifest))

    def test_explicit_scope_keeps_pinned_bytes_separate(self):
        self.write_manifest()
        paths, pins = style.load_scope(self.root)
        self.assertEqual(paths, ["live.py"])
        self.assertEqual(list(pins), ["pinned.py"])

    def test_even_whitespace_in_pinned_source_is_rejected(self):
        self.write_manifest()
        (self.root / "pinned.py").write_text("VALUE = 1\n")
        with self.assertRaisesRegex(ValueError, "preserved code changed"):
            style.load_scope(self.root)

    def test_pinned_file_cannot_enter_formatter_allow_list(self):
        self.manifest["managed_paths"].append("pinned.py")
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "pinned code entered"):
            style.load_scope(self.root)

    def test_parent_escape_and_frozen_research_paths_are_rejected(self):
        self.manifest["managed_paths"] = ["../outside.py"]
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "escapes repository"):
            style.load_scope(self.root)
        (self.root / "idx-signals/research").mkdir(parents=True)
        (self.root / "idx-signals/research/run.py").write_text("VALUE = 1\n")
        self.manifest["managed_paths"] = ["idx-signals/research/run.py"]
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "historical/pinned"):
            style.load_scope(self.root)


if __name__ == "__main__":
    unittest.main()
