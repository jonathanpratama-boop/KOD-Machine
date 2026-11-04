#!/usr/bin/env python3
"""Read-only historical byte, manifest and RFC3161 audit with explicit coverage.

No data is fetched, records repaired, hashes replaced or timestamps regenerated.
An unavailable archive or unsupported manifest is reported, never counted as a
verified file. Existing domain-specific ``kod verify`` / ``idxsig verify-runs``
remain authoritative for their schema and ledger invariants.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

from check_append_only import APPEND_ONLY, FROZEN_DIRS

ROOT = Path(__file__).resolve().parents[1]
HEX = re.compile(r"[0-9a-f]{64}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(root: Path, name: str) -> Path:
    """Historical paths are data, and cannot direct reads outside the repository."""
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("invalid relative path")
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError("path escapes repository")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("symlink escapes repository")
    return path


def inventory(root: Path, tree_inventory: Path | None = None) -> list[str]:
    if tree_inventory:
        tree = json.loads(tree_inventory.read_text())
        if tree.get("truncated"):
            raise ValueError("cannot audit a truncated tree inventory")
        return sorted(row["path"] for row in tree["tree"] if row["type"] == "blob")
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True)
    if proc.returncode == 0:
        return sorted(p.decode("utf-8", "surrogateescape") for p in proc.stdout.split(b"\0") if p)
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    )


def snapshot(root: Path, paths: list[str]) -> dict:
    rows = []
    for name in paths:
        if name not in APPEND_ONLY and not name.startswith(FROZEN_DIRS):
            continue
        path = safe_path(root, name)
        data = path.read_bytes() if path.is_file() else None
        rows.append(
            {
                "path": name,
                "bytes": len(data) if data is not None else None,
                "sha256": digest(data) if data is not None else None,
            }
        )
    return {
        "schema_version": 1,
        "kind": "KOD-HISTORY-BYTE-SNAPSHOT",
        "files": rows,
        "available": sum(row["sha256"] is not None for row in rows),
    }


def compare_snapshot(root: Path, baseline: dict) -> list[dict]:
    if baseline.get("schema_version") != 1 or not isinstance(baseline.get("files"), list):
        raise ValueError("unsupported historical byte snapshot")
    rows = []
    for original in baseline["files"]:
        name = original["path"]
        path = safe_path(root, name)
        if not original.get("sha256"):
            status, reason = "UNAVAILABLE", "baseline payload was unavailable"
        elif not path.is_file():
            status, reason = "FAIL", "previously present historical payload is missing"
        else:
            data = path.read_bytes()
            if name in APPEND_ONLY:
                data = data[: original["bytes"]]
            same = digest(data) == original["sha256"] and len(data) == original["bytes"]
            status, reason = (
                ("VERIFIED", "original bytes preserved")
                if same
                else ("FAIL", "original bytes changed")
            )
        rows.append({"path": name, "status": status, "reason": reason})
    return rows


def _json_payload(path: Path):
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    if path.name.endswith((".jsonl", ".jsonl.gz")):
        return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return json.loads(raw)


def _claims(value):
    if isinstance(value, list):
        for entry in value:
            yield from _claims(entry)
    elif isinstance(value, dict):
        if "sha256" in value:
            yield value
        for key, child in value.items():
            if key != "sha256" and isinstance(child, (dict, list)):
                yield from _claims(child)


def _claim_path(root: Path, manifest: str, claim: dict) -> Path:
    # These adapters identify original historical layouts, not renamed files.
    if manifest == "kod-machine/kod/workstation/research_evidence/manifest.json":
        return safe_path(root, str(PurePosixPath(manifest).parent / (claim["id"] + ".json")))
    if "file" in claim:
        return safe_path(root, str(PurePosixPath(manifest).parent / claim["file"]))
    value = claim.get("path") or claim.get("panel")
    if not isinstance(value, str):
        raise LookupError("hash claim has no supported file/path/panel field")
    if manifest.startswith("idx-signals/data/manifests/") and not value.startswith("idx-signals/"):
        return safe_path(root, "idx-signals/" + value)
    if value.startswith(("idx-signals/", "kod-machine/", "docs/", "handoff/")):
        return safe_path(root, value)
    return safe_path(root, str(PurePosixPath(manifest).parent / value))


def verify_manifests(root: Path, paths: list[str]) -> list[dict]:
    results = []
    for name in paths:
        if "manifest" not in name.lower() or not name.endswith((".json", ".jsonl", ".jsonl.gz")):
            continue
        path = safe_path(root, name)
        if not path.is_file():
            results.append(
                {"manifest": name, "status": "UNAVAILABLE", "reason": "manifest bytes unavailable"}
            )
            continue
        try:
            payload = _json_payload(path)
        except (OSError, ValueError, UnicodeError) as exc:
            results.append(
                {
                    "manifest": name,
                    "status": "FAIL",
                    "reason": type(exc).__name__ + ": invalid manifest",
                }
            )
            continue
        claims = list(_claims(payload))
        if not claims:
            results.append(
                {
                    "manifest": name,
                    "status": "UNSUPPORTED",
                    "reason": "no supported path/SHA256 claims",
                }
            )
        for index, claim in enumerate(claims):
            row = {"manifest": name, "claim": index}
            try:
                if not isinstance(claim["sha256"], str) or not HEX.fullmatch(claim["sha256"]):
                    raise LookupError("claim does not contain a SHA256 file digest")
                target = _claim_path(root, name, claim)
                row["path"] = target.relative_to(root).as_posix()
                if not target.is_file():
                    row.update(status="UNAVAILABLE", reason="referenced data is not present")
                else:
                    data = target.read_bytes()
                    if data.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                        row.update(
                            status="UNAVAILABLE",
                            reason="Git LFS pointer; original payload unavailable",
                        )
                    elif digest(data) != claim["sha256"]:
                        row.update(status="FAIL", reason="SHA256 mismatch")
                    else:
                        row.update(
                            status="VERIFIED", reason="original file SHA256 matches manifest"
                        )
            except LookupError as exc:
                row.update(status="UNSUPPORTED", reason=str(exc))
            except (ValueError, OSError, KeyError, TypeError) as exc:
                row.update(
                    status="FAIL", reason=type(exc).__name__ + ": invalid or unsafe hash claim"
                )
            results.append(row)
    return results


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def token_payloads(root: Path, paths: list[str]) -> tuple[dict[str, bytes], list[dict]]:
    """Rebuild signed payload associations from original ledgers, never filenames alone."""
    payloads, failures = {}, []
    for name in paths:
        paper = name.startswith("idx-signals/paper/") and name.endswith(".jsonl")
        registry = name in ("kod-machine/registry/opens.jsonl", "kod-machine/registry/scans.jsonl")
        if not (paper or registry) or not (root / name).is_file():
            continue
        try:
            for row in _json_payload(root / name):
                if paper and isinstance(row, dict) and "record_hash" in row:
                    original = row["record_hash"]
                    rebuilt = digest(
                        _canonical({k: v for k, v in row.items() if k != "record_hash"})
                    )
                    if rebuilt != original:
                        failures.append(
                            {
                                "path": name,
                                "status": "FAIL",
                                "reason": "record_hash does not match original record",
                            }
                        )
                        continue
                    for authority in ("freetsa", "sectigo"):
                        payloads[f"idx-signals/paper/timestamps/{original}.{authority}.tsr"] = (
                            original.encode("ascii")
                        )
                elif registry:
                    record_name = row["record_id"].replace(":", "_")
                    kind = row["kind"].lower()
                    for authority in ("freetsa", "sectigo"):
                        payloads[
                            f"kod-machine/registry/timestamps/{kind}/{record_name}.{authority}.tsr"
                        ] = _canonical(row)
        except (ValueError, TypeError, KeyError, UnicodeError):
            failures.append(
                {
                    "path": name,
                    "status": "FAIL",
                    "reason": "signed-payload ledger cannot be decoded",
                }
            )
    return payloads, failures


def verify_tokens(root: Path, paths: list[str], verifier=None) -> list[dict]:
    payloads, results = token_payloads(root, paths)
    if verifier is None and shutil.which("openssl"):
        sys.path.insert(0, str(root / "kod-machine"))
        try:
            from kod.timestamp import RFC3161Timestamper

            verifier = RFC3161Timestamper()
        except ImportError:
            pass
    for name in paths:
        if not name.endswith(".tsr"):
            continue
        row = {"path": name}
        token = safe_path(root, name)
        authority = token.name.rsplit(".", 2)[-2] if token.name.count(".") >= 2 else None
        data = payloads.get(name)
        if data is None:
            original_name = token.name.rsplit(".", 2)[0]
            if original_name.endswith((".json", ".jsonl", ".md")):
                direct = (
                    token.parent.parent / original_name
                    if token.parent.name == "timestamps"
                    else token.parent / original_name
                )
                if direct.is_file() and direct.resolve().is_relative_to(root.resolve()):
                    data = direct.read_bytes()
        if not token.is_file():
            row.update(status="UNAVAILABLE", reason="token bytes unavailable")
        elif data is None:
            row.update(
                status="UNAVAILABLE", reason="original signed payload association unavailable"
            )
        elif verifier is None:
            row.update(status="UNAVAILABLE", reason="offline RFC3161 verifier unavailable")
        else:
            try:
                stamp = verifier.verify(authority, token.read_bytes(), data)
                row.update(
                    status="VERIFIED",
                    reason="signature binds original payload under pinned trust chain",
                    timestamp=stamp.isoformat(),
                    payload_sha256=digest(data),
                )
            except FileNotFoundError:
                row.update(
                    status="UNAVAILABLE", reason="verifier or pinned certificate unavailable"
                )
            except Exception as exc:
                row.update(
                    status="FAIL", reason="RFC3161 verification failed: " + type(exc).__name__
                )
        results.append(row)
    return results


def report(root: Path, paths: list[str], baseline: dict | None = None, *, verifier=None) -> dict:
    sections = {
        "manifests": verify_manifests(root, paths),
        "tokens": verify_tokens(root, paths, verifier),
    }
    if baseline is not None:
        sections["preservation"] = compare_snapshot(root, baseline)
    counts = {key: dict(Counter(row["status"] for row in rows)) for key, rows in sections.items()}
    statuses = {row["status"] for rows in sections.values() for row in rows}
    status = (
        "FAIL"
        if "FAIL" in statuses
        else "PARTIAL"
        if statuses - {"VERIFIED"} or not statuses
        else "VERIFIED"
    )
    return {
        "schema_version": 1,
        "kind": "KOD-HISTORY-AUDIT",
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        **sections,
        "limits": [
            "No archive data is fetched or rewritten.",
            "Signature verification proves payload binding, not tradability or timely prediction.",
            "Only explicit supported manifest layouts are checked; unsupported coverage remains visible.",
            "Use existing domain verifiers for ledger chains, schemas and outcome chronology.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tree-inventory", type=Path)
    parser.add_argument("--snapshot", type=Path, help="write original-byte inventory before edits")
    parser.add_argument("--compare", type=Path, help="compare with a previously saved snapshot")
    parser.add_argument(
        "--report", type=Path, help="write detailed verification and coverage report"
    )
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    paths = inventory(root, args.tree_inventory)
    if args.snapshot:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        with args.snapshot.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(snapshot(root, paths), indent=2) + "\n")
    baseline = json.loads(args.compare.read_text()) if args.compare else None
    result = report(root, paths, baseline)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "counts": result["counts"]}, sort_keys=True))
    return (
        1
        if result["status"] == "FAIL" or (args.require_complete and result["status"] != "VERIFIED")
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
