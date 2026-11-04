#!/usr/bin/env python3
"""Check the explicit first-party style scope without touching historical code."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools/live_code_style.json"


def load_scope(root: Path = ROOT) -> tuple[list[str], dict[str, str]]:
    """Validate an exact allow-list and verify excluded compatibility anchors."""
    root = root.resolve()
    manifest = json.loads((root / "tools/live_code_style.json").read_text())
    if manifest.get("schema_version") != "KOD_LIVE_STYLE_V1":
        raise ValueError("unsupported live style schema")
    paths = manifest["managed_paths"]
    pins = manifest["preserved_sha256"]
    if not isinstance(paths, list) or len(paths) != len(set(paths)):
        raise ValueError("style paths must be a unique list")
    forbidden = ("/research/", "/results/", "/registry/", "/vendor/")
    for relative in [*paths, *pins]:
        path = Path(relative)
        resolved = (root / path).resolve()
        if path.is_absolute() or ".." in path.parts or not resolved.is_relative_to(root):
            raise ValueError(f"style path escapes repository: {relative}")
        if not resolved.is_file() or (root / path).is_symlink():
            raise ValueError(f"style path unavailable or symlinked: {relative}")
    for relative in paths:
        if not relative.endswith(".py") or relative.startswith("handoff/"):
            raise ValueError(f"not maintained Python: {relative}")
        if any(part in "/" + relative for part in forbidden) or relative in pins:
            raise ValueError(f"historical/pinned code entered style scope: {relative}")
    for relative, expected in pins.items():
        observed = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(f"preserved code changed: {relative}")
    return paths, pins


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", action="store_true", help="format only the explicit scope")
    parser.add_argument("--lint-only", action="store_true", help="check correctness before tidy")
    args = parser.parse_args(argv)
    if args.format and args.lint_only:
        parser.error("--format and --lint-only are mutually exclusive")
    paths, _ = load_scope()
    prefix = [sys.executable, "-m", "ruff"]
    if not args.lint_only:
        command = [*prefix, "format", *([] if args.format else ["--check"]), *paths]
        subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run([*prefix, "check", *paths], cwd=ROOT, check=True)
    load_scope()  # Formatting must not have changed a preserved anchor.
    print(json.dumps({"ok": True, "managed_files": len(paths), "formatted": args.format}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
