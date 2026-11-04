"""Audit completeness stays explicit; missing bytes can never become a pass."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("history_audit", TOOLS / "check_history_integrity.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class FixtureVerifier:
    """Dependency injection checks payload routing; production uses OpenSSL."""

    def verify(self, authority, token, data):
        if authority != "freetsa" or token != b"fixture:" + data:
            raise ValueError("wrong payload or authority")
        return datetime(2026, 11, 4, tzinfo=timezone.utc)


class HistoryAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_snapshot_detects_frozen_rewrite_but_allows_log_append(self):
        frozen = "idx-signals/research/a.json"
        ledger = "registry/ids/ID_MAP.jsonl"
        self.write(frozen, b"original")
        self.write(ledger, b"old\n")
        baseline = audit.snapshot(self.root, [frozen, ledger])
        self.write(ledger, b"old\nnew\n")
        self.assertTrue(all(x["status"] == "VERIFIED" for x in audit.compare_snapshot(self.root, baseline)))
        self.write(frozen, b"rewritten")
        self.assertEqual(audit.compare_snapshot(self.root, baseline)[0]["status"], "FAIL")

    def test_missing_baseline_bytes_remain_unavailable(self):
        name = "idx-signals/research/missing.json"
        baseline = audit.snapshot(self.root, [name])
        self.write(name, b"available later")
        self.assertEqual(audit.compare_snapshot(self.root, baseline)[0]["status"], "UNAVAILABLE")

    def test_manifests_check_original_bytes_and_missing_data(self):
        manifest = "idx-signals/data/manifests/example.jsonl"
        self.write("idx-signals/data/a.bin", b"original")
        rows = [{"manifest": "example"}, {"path": "data/a.bin", "sha256": audit.digest(b"original")},
                {"path": "data/unavailable.bin", "sha256": "a" * 64}]
        self.write(manifest, "\n".join(json.dumps(x) for x in rows).encode())
        checked = audit.verify_manifests(self.root, [manifest])
        self.assertEqual([x["status"] for x in checked], ["VERIFIED", "UNAVAILABLE"])
        self.write("idx-signals/data/a.bin", b"changed")
        self.assertEqual(audit.verify_manifests(self.root, [manifest])[0]["status"], "FAIL")

    def test_unknown_manifest_shape_is_not_verified(self):
        name = "manifest.json"
        self.write(name, b'{"old_format": "unknown"}')
        self.assertEqual(audit.verify_manifests(self.root, [name])[0]["status"], "UNSUPPORTED")

    def test_manifest_cannot_read_outside_repository(self):
        self.write("manifest.json", json.dumps({"path": "../private", "sha256": "a" * 64}).encode())
        self.assertEqual(audit.verify_manifests(self.root, ["manifest.json"])[0]["status"], "FAIL")

    def test_digest_token_requires_a_recomputed_original_record(self):
        body = {"type": "FORECAST", "id": "synthetic", "prev_hash": None}
        digest = audit.digest(audit._canonical(body))
        ledger = "idx-signals/paper/learner_v2.jsonl"
        token = f"idx-signals/paper/timestamps/{digest}.freetsa.tsr"
        self.write(ledger, json.dumps({**body, "record_hash": digest}).encode() + b"\n")
        self.write(token, b"fixture:" + digest.encode())
        results = audit.verify_tokens(self.root, [ledger, token], FixtureVerifier())
        self.assertEqual(results[0]["status"], "VERIFIED")
        self.write(ledger, json.dumps({**body, "id": "rewritten", "record_hash": digest}).encode())
        statuses = [x["status"] for x in audit.verify_tokens(self.root, [ledger, token], FixtureVerifier())]
        self.assertEqual(statuses, ["FAIL", "UNAVAILABLE"])

    def test_registry_token_uses_original_canonical_line(self):
        row = {"kind": "CASE", "record_id": "OLD:1", "sha256": "a" * 64}
        ledger = "kod-machine/registry/opens.jsonl"
        token = "kod-machine/registry/timestamps/case/OLD_1.freetsa.tsr"
        self.write(ledger, json.dumps(row).encode())
        self.write(token, b"fixture:" + audit._canonical(row))
        self.assertEqual(audit.verify_tokens(self.root, [ledger, token], FixtureVerifier())[0]["status"], "VERIFIED")

    def test_missing_token_or_payload_is_unavailable(self):
        token = f"idx-signals/paper/timestamps/{'a' * 64}.freetsa.tsr"
        self.assertEqual(audit.verify_tokens(self.root, [token], FixtureVerifier())[0]["status"], "UNAVAILABLE")
        self.write(token, b"invalid")
        self.assertEqual(audit.verify_tokens(self.root, [token], FixtureVerifier())[0]["status"], "UNAVAILABLE")

    def test_bad_signature_and_empty_audit_cannot_pass(self):
        self.write("example.json", b"original")
        self.write("example.json.freetsa.tsr", b"invalid")
        self.assertEqual(audit.verify_tokens(self.root, ["example.json.freetsa.tsr"], FixtureVerifier())[0]["status"], "FAIL")
        self.assertEqual(audit.report(self.root, [], verifier=FixtureVerifier())["status"], "PARTIAL")

    def test_snapshot_writer_is_exclusive(self):
        output = self.root / "snapshot.json"
        self.assertEqual(audit.main(["--root", str(self.root), "--snapshot", str(output)]), 0)
        with self.assertRaises(FileExistsError):
            audit.main(["--root", str(self.root), "--snapshot", str(output)])


if __name__ == "__main__":
    unittest.main()
