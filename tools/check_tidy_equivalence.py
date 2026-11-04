#!/usr/bin/env python3
"""Prove a mechanical tidy retains Python ASTs and an existing synthetic journal."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

from check_live_style import ROOT, load_scope


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def capture(output: Path) -> dict:
    """Capture fixed-input output; the result does not establish market performance."""
    if output.exists() or output.with_suffix(".runtime").exists():
        raise ValueError("golden capture requires a new output and runtime directory")
    paths, pins = load_scope()
    structures = {}
    for relative in paths:
        source = (ROOT / relative).read_text()
        syntax = ast.dump(ast.parse(source, filename=relative), include_attributes=False)
        structures[relative] = hashlib.sha256(syntax.encode()).hexdigest()
    sys.path[:0] = [str(ROOT / "idx-signals"), str(ROOT / "kod-machine")]
    from idxsig.runtime.demo import demo
    from idxsig.runtime.coordinator import verify as verify_runtime

    runtime = output.with_suffix(".runtime").resolve()
    with patch("idxsig.runtime.coordinator.now", return_value="2026-11-04T12:03:00Z"):
        result = demo(runtime)
    verification = verify_runtime(runtime)
    record = {
        "schema_version": "KOD_TIDY_GOLDEN_V1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "runtime_path": str(runtime),
        "managed_ast_sha256": structures,
        "preserved_sha256": pins,
        "synthetic_snapshot": result,
        "synthetic_snapshot_sha256": hashlib.sha256(encoded(result)).hexdigest(),
        "verification": verification,
        "profitability_validated": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded(record) + b"\n")
    return record


def compare(before: dict, after: dict) -> dict:
    differences = []
    for key in ("managed_ast_sha256", "preserved_sha256", "synthetic_snapshot"):
        if before[key] != after[key]:
            differences.append(key)
    sys.path[:0] = [str(ROOT / "idx-signals"), str(ROOT / "kod-machine")]
    from idxsig.runtime.coordinator import verify as verify_runtime

    # Read the pre-tidy journal with the post-tidy implementation; do not rebuild it.
    original_verification = verify_runtime(Path(before["runtime_path"]))
    return {
        "ok": not differences,
        "different_fields": differences,
        "managed_files": len(before["managed_ast_sha256"]),
        "original_journal_readable": bool(original_verification["ok"]),
        "snapshot_bytes_equal": encoded(before["synthetic_snapshot"]) == encoded(after["synthetic_snapshot"]),
        "scope": "formatting equivalence and synthetic history compatibility; not profitability",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args(argv)
    result = capture(args.output)
    if args.baseline:
        before = json.loads(args.baseline.read_text())
        report = compare(before, result)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["ok"] and report["original_journal_readable"] else 1
    print(json.dumps({"ok": True, "managed_files": len(result["managed_ast_sha256"]), "synthetic_snapshot_sha256": result["synthetic_snapshot_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
