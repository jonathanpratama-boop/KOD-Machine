"""Atomic snapshots and append-only run receipts; no network or order routing."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

SNAPSHOT_VERSION = "KOD_RUNTIME_SNAPSHOT_V1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"nonfinite JSON: {x}")))


@contextlib.contextmanager
def locked(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".runtime.lock").open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = canonical(value) + b"\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def immutable_json(path, value):
    """Caller holds runtime lock; conflicting reuse is a hard error."""
    path = Path(path)
    if path.exists():
        if canonical(read_json(path)) != canonical(value):
            raise ValueError(f"immutable artifact conflict: {path.name}")
    else:
        atomic_json(path, value)


def read_receipts(root):
    path = Path(root) / "runs.jsonl"
    records, previous = [], None
    if not path.exists():
        return records
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("torn run receipt tail; preserve and recover before appending")
    for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line:
            raise ValueError(f"blank run receipt at line {number}")
        row = json.loads(line, object_pairs_hook=_pairs)
        body = {key: value for key, value in row.items() if key != "record_hash"}
        if body.get("prev_hash") != previous or digest(body) != row.get("record_hash"):
            raise ValueError(f"run receipt integrity failure at line {number}")
        records.append(row)
        previous = row["record_hash"]
    return records


def append_receipt(root, receipt):
    """Must be called while holding locked(root)."""
    root = Path(root)
    rows = read_receipts(root)
    body = dict(receipt, prev_hash=rows[-1]["record_hash"] if rows else None)
    row = dict(body, record_hash=digest(body))
    with (root / "runs.jsonl").open("ab") as stream:
        stream.write(canonical(row) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(root, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return row


def write_snapshot(root, payload):
    envelope = {"schema_version": SNAPSHOT_VERSION, "payload": payload, "sha256": digest(payload)}
    atomic_json(Path(root) / "snapshot.json", envelope)
    return envelope


def read_snapshot(root):
    envelope = read_json(Path(root) / "snapshot.json")
    if envelope.get("schema_version") != SNAPSHOT_VERSION or envelope.get("sha256") != digest(envelope.get("payload")):
        raise ValueError("snapshot integrity/schema failure")
    return envelope
