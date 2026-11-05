"""Recoverable append-only local events with a second immutable intent copy.

An external checkpoint is still necessary to detect coordinated deletion or
replacement of both local copies. This is not a cryptographic timestamp service.
"""

from pathlib import Path

from ..runtime.storage import append_receipt, digest, immutable_json, read_json, read_receipts


def safe_root(path):
    root = Path(path).absolute()
    for parent in (root, *root.parents):
        if parent.is_symlink():
            raise ValueError("LLM store cannot use symbolic links")
    if root.exists():
        for item in root.rglob("*"):
            if item.is_symlink():
                raise ValueError("LLM artifacts cannot use symbolic links")
    return root


def events(root, recover=False):
    rows = read_receipts(root)
    folder = root / "events"
    intents = sorted(folder.glob("*.json")) if folder.exists() else []
    if len(intents) < len(rows):
        raise ValueError("missing immutable journal intent")
    for index, item in enumerate(intents, 1):
        if item.name != f"{index:06d}.json":
            raise ValueError("missing or reordered journal intent")
        intent = read_json(item)
        if index <= len(rows):
            row = {
                k: v for k, v in rows[index - 1].items() if k not in {"prev_hash", "record_hash"}
            }
            if intent != row:
                raise ValueError("journal differs from immutable intent")
        elif recover:
            rows.append(append_receipt(root, intent))
        else:
            raise ValueError("journal is incomplete; run recover to restore retained intents")
    for index, row in enumerate(rows, 1):
        if row.get("sequence") != index:
            raise ValueError("journal sequence mismatch")
    return rows


def append(root, kind, payload, recorded_at):
    rows = events(root, recover=True)
    event = {
        "sequence": len(rows) + 1,
        "kind": kind,
        "recorded_at": recorded_at,
        "payload": payload,
    }
    immutable_json(root / "events" / f"{event['sequence']:06d}.json", event)
    return append_receipt(root, event)


def checkpoint(root, rows):
    return {
        "manifest_sha256": digest(read_json(root / "manifest.json")),
        "event_count": len(rows),
        "head_sha256": rows[-1]["record_hash"] if rows else None,
    }


def verify_checkpoint(root, rows, expected):
    count = expected["event_count"]
    if type(count) is not int or count < 0 or count > len(rows):
        raise ValueError("external checkpoint has missing events")
    if checkpoint(root, rows[:count]) != expected:
        raise ValueError("external checkpoint does not match retained history")
