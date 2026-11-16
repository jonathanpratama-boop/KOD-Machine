"""Independent contract tests against the frozen exporter and SQLite transactions."""
import ast
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('export_recovery', HERE / 'export_recovery.py')
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)


def make_engine():
    tree = ast.parse((HERE / 'source' / 'engine.py.snapshot').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ResearchEngine')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'export_incremental')
    namespace = dict(Path=Path, gzip=gzip, hashlib=hashlib, os=os, canonical=canonical)
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<frozen exporter>', 'exec'), namespace)

    class Engine:
        transaction = staticmethod(lambda engine: engine.db)
        export_incremental = namespace['export_incremental']

        def __init__(self):
            self.db = sqlite3.connect(':memory:')
            self.db.row_factory = sqlite3.Row
            self.db.execute('CREATE TABLE ledger(seq INTEGER PRIMARY KEY,kind TEXT,payload TEXT,hash TEXT)')
            self.db.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value INTEGER)')

        def get(self, key, default=None):
            row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
            return default if row is None else row[0]

        def set(self, key, value):
            self.db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', (key, value))

    engine = Engine()
    recovery.install(types.SimpleNamespace(ResearchEngine=Engine, canonical=canonical))
    return engine


class ExportRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.engine = make_engine()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.engine.db.close)

    def fill(self, n, boundaries):
        rows = [(i, 'RESEARCH_CHECKPOINT' if i in boundaries else 'DETECTOR', canonical({'i': i, 'note': 'α'}), hashlib.sha256(str(i).encode()).hexdigest()) for i in range(1, n + 1)]
        with self.engine.db:
            self.engine.db.executemany('INSERT INTO ledger VALUES(?,?,?,?)', rows)

    def records(self, result):
        return [json.loads(row) for row in gzip.decompress(Path(result['file']).read_bytes()).splitlines()]

    def test_large_transaction_preserved_exactly(self):
        self.fill(12002, {12001})
        r = self.engine.export_incremental(self.out)
        self.assertEqual((r['records'], r['last_seq']), (12001, 12001))
        expected = [dict(row) for row in self.engine.db.execute('SELECT * FROM ledger WHERE seq<=12001 ORDER BY seq')]
        self.assertEqual(self.records(r), expected)
        self.assertEqual(self.engine.get('export_seq'), 12001)
        self.assertEqual(r['sha256'], hashlib.sha256(Path(r['file']).read_bytes()).hexdigest())

    def test_small_chunk_bytes_unchanged(self):
        self.fill(8, {6})
        expected = ('\n'.join(canonical(dict(r)) for r in self.engine.db.execute('SELECT * FROM ledger WHERE seq<=6 ORDER BY seq')) + '\n').encode()
        r = self.engine.export_incremental(self.out)
        self.assertEqual(Path(r['file']).read_bytes(), gzip.compress(expected, compresslevel=6, mtime=0))
        self.assertEqual(r['last_seq'], 6)

    def test_two_boundaries_leave_trailing_transaction(self):
        self.fill(15003, {12001, 15002})
        first = self.engine.export_incremental(self.out)
        second = self.engine.export_incremental(self.out)
        self.assertEqual((first['last_seq'], second['last_seq']), (12001, 15002))
        self.assertEqual(len(self.records(first)) + len(self.records(second)), 15002)

    def test_no_boundary_leaves_cursor_and_files(self):
        self.fill(12001, set())
        with self.assertRaisesRegex(ValueError, 'bounded export'):
            self.engine.export_incremental(self.out)
        self.assertEqual(self.engine.get('export_seq', 0), 0)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_publish_failure_rolls_back_cursor_and_cleans_temp(self):
        self.fill(12001, {12001})
        with patch.object(recovery.os, 'replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.engine.export_incremental(self.out)
        self.assertEqual(self.engine.get('export_seq', 0), 0)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_published_chunk_before_cursor_commit_reused_on_retry(self):
        self.fill(12001, {12001})
        real_set = self.engine.set
        with patch.object(self.engine, 'set', side_effect=OSError('cursor failed')):
            with self.assertRaises(OSError):
                self.engine.export_incremental(self.out)
        self.assertEqual(self.engine.get('export_seq', 0), 0)
        before = list(self.out.glob('*.gz'))
        self.assertEqual(len(before), 1)
        self.engine.set = real_set
        result = self.engine.export_incremental(self.out)
        self.assertEqual(list(self.out.glob('*.gz')), before)
        self.assertEqual(result['last_seq'], 12001)
        self.assertEqual(self.engine.export_incremental(self.out), {'records': 0, 'last_seq': 12001})

    def test_retry_fsyncs_directory_after_prior_publication_failure(self):
        self.fill(12001, {12001})
        real_fsync = os.fsync
        calls = []

        def fail_directory_once(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError('directory sync failed')
            return real_fsync(fd)

        with patch.object(recovery.os, 'fsync', side_effect=fail_directory_once):
            with self.assertRaises(OSError):
                self.engine.export_incremental(self.out)
        self.assertEqual(self.engine.get('export_seq', 0), 0)
        with patch.object(recovery.os, 'fsync', wraps=real_fsync) as sync:
            self.engine.export_incremental(self.out)
            self.assertGreaterEqual(sync.call_count, 2)

    def test_gap_rejected_without_cursor_advance(self):
        self.fill(12002, {12002})
        with self.engine.db:
            self.engine.db.execute('DELETE FROM ledger WHERE seq=500')
        with self.assertRaisesRegex(ValueError, 'sequence gap'):
            self.engine.export_incremental(self.out)
        self.assertEqual(self.engine.get('export_seq', 0), 0)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_unrelated_error_not_swallowed(self):
        self.fill(2, {2})
        with self.assertRaisesRegex(ValueError, 'bounded export limit required'):
            self.engine.export_incremental(self.out, limit=0)
        self.assertEqual(self.engine.get('export_seq', 0), 0)


if __name__ == '__main__':
    unittest.main()
