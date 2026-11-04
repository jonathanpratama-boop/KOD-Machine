import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from idxsig.runtime.backup import backup, restore, MANIFEST, SCHEMA


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'runtime'
        self.root.mkdir()
        (self.root / 'inputs').mkdir()
        (self.root / 'inputs' / 'raw.bin').write_bytes(b'\x00\xff\x01')
        (self.root / 'profile.json').write_text('{"paper":true}')
        self.archive = self.base / 'backup.zip'
        self.restored = self.base / 'restored'

    def crafted(self, names, files=None):
        files = files or {name: {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()} for name, body in names}
        with zipfile.ZipFile(self.archive, 'w') as z:
            for name, body in names:
                z.writestr(name, body)
            z.writestr(MANIFEST, json.dumps({'schema_version': SCHEMA, 'files': files}))

    def test_exact_binary_round_trip_and_new_destination_only(self):
        result = backup(self.root, self.archive)
        self.assertEqual(result['files'], 2)
        self.assertEqual(restore(self.archive, self.restored)['files'], 2)
        self.assertEqual((self.restored / 'inputs/raw.bin').read_bytes(), b'\x00\xff\x01')
        self.assertFalse((self.restored / '.runtime.lock').exists())
        with self.assertRaises(FileExistsError):
            restore(self.archive, self.restored)
        with self.assertRaises(FileExistsError):
            backup(self.root, self.archive)

    def test_corruption_creates_no_destination(self):
        self.crafted([('a', b'bad')], {'a': {'bytes': 3, 'sha256': '0'*64}})
        with self.assertRaises(ValueError):
            restore(self.archive, self.restored)
        self.assertFalse(self.restored.exists())

    def test_traversal_absolute_duplicate_and_ambiguous_paths_rejected(self):
        for name in ('../outside', '/absolute', 'a/../b', 'a\\b', 'a//b', './a', 'C:/x'):
            with self.subTest(name=name):
                self.crafted([(name, b'x')])
                with self.assertRaises(ValueError):
                    restore(self.archive, self.restored)
                self.assertFalse(self.restored.exists())
        self.crafted([('a', b'x'), ('a', b'x')])
        with self.assertRaises(ValueError):
            restore(self.archive, self.restored)

    def test_symbolic_links_refused_in_source_and_archive(self):
        (self.root / 'linked').symlink_to(self.root / 'profile.json')
        with self.assertRaises(ValueError):
            backup(self.root, self.archive)
        self.assertFalse(self.archive.exists())
        entry = zipfile.ZipInfo('link')
        entry.create_system = 3
        entry.external_attr = 0o120777 << 16
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr(entry, '../outside')
            z.writestr(MANIFEST, json.dumps({'schema_version': SCHEMA, 'files': {}}))
        with self.assertRaises(ValueError):
            restore(self.archive, self.restored)

    def test_size_limits_reject_before_restore(self):
        self.crafted([('a', b'x'*100)])
        with patch('idxsig.runtime.backup.MAX_FILE_BYTES', 50), self.assertRaises(ValueError):
            restore(self.archive, self.restored)
        self.assertFalse(self.restored.exists())

    def test_backup_inside_runtime_refused(self):
        with self.assertRaises(ValueError):
            backup(self.root, self.root / 'recursive.zip')

    def test_started_timing_attempt_survives_backup_without_invented_completion(self):
        from idxsig.runtime.timing import Attempt
        from idxsig.runtime.timing_evidence import verify_linked_evidence
        from idxsig.timing_capture import read_attempts

        clock = lambda: "2026-11-04T00:30:00Z"
        with patch("idxsig.runtime.timing.shutil.which", return_value=None):
            attempt = Attempt(self.root, detector="BACKUP_FIXTURE_V1", source="synthetic",
                              kind="synthetic", members=["BTCUSDT"], clock=clock)
        original = read_attempts(self.root)
        self.assertEqual(original[0]["status"], "STARTED")
        backup(self.root, self.archive)
        restore(self.archive, self.restored)
        recovered = read_attempts(self.restored)
        self.assertEqual(recovered, original)
        self.assertTrue(verify_linked_evidence(self.restored, recovered)["ok"])
        self.assertIsNone(recovered[0]["decision_at"])
        self.assertIsNone(recovered[0]["fill_at"])
        # Completing the original cannot revise the already-published backup.
        attempt.finish("NO_TRIGGER")
        self.assertEqual(read_attempts(self.restored)[0]["status"], "STARTED")


if __name__ == '__main__':
    unittest.main()
