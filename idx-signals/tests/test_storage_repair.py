"""Local POSIX durability/retry invariants; no live services."""

import gzip
import json
import multiprocessing
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from idxsig import paper, provenance


def _append_many(path, worker):
    for i in range(12):
        paper.append([{"type": "TEST", "worker": worker, "i": i}], Path(path))


def _die_before_publish(path):
    with provenance.exclusive_lock(Path(path)):
        with provenance.atomic_writer(Path(path), replace=True) as fh:
            fh.write(b"unpublished replacement\n")
            fh.flush()
            os._exit(17)


class ReceiptStub:
    authorities = {"freetsa": None, "sectigo": None}

    def __init__(self, fail=False):
        self.fail, self.calls = fail, 0

    def stamp(self, data):
        self.calls += 1
        if self.fail:
            raise OSError("service down")
        return [SimpleNamespace(authority=a, token=data + a.encode()) for a in self.authorities]


class StorageRepair(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "ledger.jsonl"

    def test_multiprocess_writers_share_one_chain(self):
        ctx = multiprocessing.get_context("fork")
        jobs = [ctx.Process(target=_append_many, args=(str(self.path), i)) for i in range(4)]
        for job in jobs:
            job.start()
        for job in jobs:
            job.join(20)
            if job.is_alive():
                job.kill()
                job.join()
                self.fail("writer did not finish")
            self.assertEqual(job.exitcode, 0)
        self.assertEqual(len(paper.ledger_lines(self.path)), 48)
        self.assertEqual(paper.verify_chain(self.path), [])

    def test_whole_batch_failure_preserves_exact_prefix(self):
        paper.append([{"type": "TEST", "id": 1}], self.path)
        before = self.path.read_bytes()
        with patch.object(provenance.os, "replace", side_effect=OSError("injected before publish")):
            with self.assertRaises(OSError):
                paper.append([{"type": "TEST", "id": 2}, {"type": "TEST", "id": 3}], self.path)
        self.assertEqual(self.path.read_bytes(), before)
        paper.append([{"type": "TEST", "id": 2}, {"type": "TEST", "id": 3}], self.path)
        self.assertTrue(self.path.read_bytes().startswith(before))
        self.assertEqual(len(paper.ledger_lines(self.path)), 3)

    def test_process_death_during_staging_preserves_published_bytes(self):
        paper.append([{"type": "TEST", "id": 1}], self.path)
        before = self.path.read_bytes()
        ctx = multiprocessing.get_context("fork")
        job = ctx.Process(target=_die_before_publish, args=(str(self.path),))
        job.start()
        job.join(10)
        self.assertEqual(job.exitcode, 17)
        self.assertEqual(self.path.read_bytes(), before)
        paper.append([{"type": "TEST", "id": 2}], self.path)
        self.assertEqual(paper.verify_chain(self.path), [])

    def test_existing_bytes_are_not_reserialized(self):
        rows = paper.append([{"type": "TEST", "id": 1}], self.path)
        self.path.write_bytes((json.dumps(rows[0]) + "\n").encode())
        before = self.path.read_bytes()
        paper.append([{"type": "TEST", "id": 2}], self.path)
        self.assertTrue(self.path.read_bytes().startswith(before))

    def test_exact_retry_is_idempotent_and_stale_head_is_rejected(self):
        one = paper.append([{"type": "TEST", "id": 1}], self.path, expected_head=None)
        before = self.path.read_bytes()
        self.assertEqual(paper.append([{"type": "TEST", "id": 1}], self.path), one)
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaisesRegex(RuntimeError, "head changed"):
            paper.append([{"type": "TEST", "id": 2}], self.path, expected_head=None)
        self.assertEqual(self.path.read_bytes(), before)

    def test_broken_input_is_refused_without_mutation(self):
        self.path.write_bytes(b'{"type": "TEST"}\n')
        before = self.path.read_bytes()
        with self.assertRaises(RuntimeError):
            paper.append([{"type": "TEST", "id": 1}], self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_receipt_failure_and_retry_never_duplicate_events(self):
        with patch.object(paper, "TOKENS", self.root / "tokens"):
            with self.assertRaises(paper.ReceiptPendingError) as got:
                paper.append([{"type": "TEST", "id": 1}], self.path, ReceiptStub(fail=True))
            before = self.path.read_bytes()
            stub = ReceiptStub()
            report = paper.retry_receipts(got.exception.record_hashes, self.path, stub)
            self.assertEqual(report["missing"], [])
            self.assertEqual(len(report["written"]), 2)
            paper.retry_receipts(got.exception.record_hashes, self.path, stub)
            self.assertEqual(stub.calls, 1)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(len(paper.ledger_lines(self.path)), 1)
            with self.assertRaises(ValueError):
                paper.retry_receipts(["not-committed"], self.path, stub)

    def test_gzip_is_identical_across_names_and_refuses_overwrite(self):
        frame = pd.DataFrame({"close": [100.0, 200.0]})
        a, b = self.root / "one.csv.gz", self.root / "different.csv.gz"
        provenance.write_csv_gz_exclusive(a, frame, index=False)
        provenance.write_csv_gz_exclusive(b, frame, index=False)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertEqual(gzip.decompress(a.read_bytes()), frame.to_csv(index=False).encode())
        before = a.read_bytes()
        with self.assertRaises(FileExistsError):
            provenance.write_csv_gz_exclusive(a, frame.iloc[:1], index=False)
        self.assertEqual(a.read_bytes(), before)

    def test_serializer_failure_exposes_no_partial_object(self):
        frame = pd.DataFrame({"close": [100]})
        out = self.root / "failed.csv.gz"
        with patch.object(frame, "to_csv", side_effect=OSError("serialize failed")):
            with self.assertRaises(OSError):
                provenance.write_csv_gz_exclusive(out, frame)
        self.assertFalse(out.exists())
        self.assertFalse(list(self.root.glob(".*.stage-*")))

    def test_panel_builds_same_second_and_failed_manifest_keep_old_hashes(self):
        from idxsig import global_panel

        frame = pd.DataFrame(
            {"date": pd.to_datetime(["2026-01-02"]), "ticker": ["ABC"], "close": [100.0]}
        )
        source = self.root / "source.jsonl"
        source.write_text("{}\n")
        data, manifests = self.root / "data", self.root / "manifests"
        manifests.mkdir()
        with (
            patch.object(global_panel, "check_files", return_value=[]),
            patch.object(global_panel, "load_us", return_value=(frame, {})),
            patch.object(global_panel, "_finish", side_effect=lambda df: (df, {})),
            patch.object(global_panel, "PANEL_DIR", data),
            patch.object(global_panel, "MANIFESTS", manifests),
            patch.object(global_panel, "rel", side_effect=str),
            patch.object(global_panel, "utc_stamp", return_value="2026-01-02T00:00:00Z"),
        ):
            first = global_panel.build("US", source, log=lambda _: None)
            meta = json.loads(first.read_text())
            before = Path(meta["panel"]).read_bytes()
            frame.loc[0, "close"] = 200.0
            second = global_panel.build("US", source, log=lambda _: None)
            self.assertNotEqual(first, second)
            self.assertEqual(Path(meta["panel"]).read_bytes(), before)
            self.assertEqual(provenance.sha256_file(Path(meta["panel"])), meta["sha256"])
            with patch.object(
                global_panel, "publish_bytes", side_effect=OSError("manifest failed")
            ):
                with self.assertRaises(OSError):
                    global_panel.build("US", source, log=lambda _: None)
            self.assertEqual(len(list(manifests.glob("*.json"))), 2)
            self.assertEqual(Path(meta["panel"]).read_bytes(), before)

    def test_same_second_build_ids_are_distinct_and_latest_uses_metadata(self):
        self.assertNotEqual(provenance.build_stamp(), provenance.build_stamp())
        for name, when in [
            ("panel-z.json", "2026-01-01T00:00:00Z"),
            ("panel-a.json", "2026-01-02T00:00:00Z"),
        ]:
            provenance.publish_bytes(
                self.root / name,
                json.dumps({"built_at": when, "panel": "x", "sha256": "x"}).encode(),
            )
        with patch.object(provenance, "MANIFESTS", self.root):
            self.assertEqual(provenance.latest_panel_manifest("panel").name, "panel-a.json")


if __name__ == "__main__":
    unittest.main()
