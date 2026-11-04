"""Historical names survive alias registration without retroactive information."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from kod.ids import load_aliases, resolve


class IdentifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ID_MAP.jsonl"
        self.row = {
            "schema_version": 1,
            "old": "E6",
            "new": "historical-discovery",
            "kind": "experiment",
            "since": "2026-11-04T00:00:00Z",
            "commit": "a" * 40,
            "reason": "synthetic compatibility test",
        }
        self.write(self.row)

    def write(self, *rows):
        self.path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def test_original_and_alias_resolve_without_changing_registry(self):
        before = self.path.read_bytes()
        for name in ("E6", "historical-discovery"):
            self.assertEqual(resolve(name, "2026-11-05T00:00:00Z", registry_path=self.path), "E6")
        self.assertEqual(self.path.read_bytes(), before)

    def test_future_alias_is_not_retroactively_available(self):
        self.assertEqual(
            resolve("historical-discovery", "2026-11-03T00:00:00Z", registry_path=self.path),
            "historical-discovery",
        )

    def test_empty_map_and_unknown_identifier_preserve_names(self):
        self.write()
        self.assertEqual(resolve("IGNITION_SCAN_v0", registry_path=self.path), "IGNITION_SCAN_v0")

    def test_unversioned_v1_reader_compatibility(self):
        row = {key: value for key, value in self.row.items() if key != "schema_version"}
        self.write(row)
        self.assertEqual(load_aliases(self.path)[0]["schema_version"], 1)

    def test_invalid_maps_fail(self):
        for change in (
            {"schema_version": 2},
            {"since": "2026-11-04"},
            {"commit": "unknown"},
            {"since": "2026-11-04T07:00:00+07:00"},
            {"kind": "money"},
        ):
            with self.subTest(change=change):
                self.write({**self.row, **change})
                with self.assertRaises(ValueError):
                    load_aliases(self.path)

    def test_rebinding_chaining_and_cycles_fail(self):
        for change in (
            {"old": "E7"},
            {"old": self.row["new"], "new": "third-name"},
            {"old": self.row["new"], "new": "E6"},
        ):
            with self.subTest(change=change):
                self.write(self.row, {**self.row, **change})
                with self.assertRaises(ValueError):
                    load_aliases(self.path)

    def test_missing_map_is_not_silently_empty(self):
        self.path.unlink()
        with self.assertRaises(ValueError):
            resolve("E6", registry_path=self.path)

    def test_path_alias_cannot_escape_repository(self):
        self.write({**self.row, "kind": "path", "old": "../original.json"})
        with self.assertRaises(ValueError):
            load_aliases(self.path)


if __name__ == "__main__":
    unittest.main()
