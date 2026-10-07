#!/usr/bin/env python3
"""Refuse any change that edits or deletes an append-only record.

Frozen directories: a file, once committed, may never be modified, deleted or renamed.
  idx-signals/results/runs/      one directory per backtest run
  idx-signals/data/manifests/    provenance of every downloaded data file
  kod-machine/registry/cards/    frozen KOD cards, one per open
  kod-machine/registry/scans/    frozen KOD scans
  kod-machine/registry/evidence/ archived evidence bytes and metadata
  kod-machine/registry/timestamps/  RFC 3161 tokens
  kod-machine/tsa/               pinned timestamp-authority certificates

Append-only logs: the new content must start with the old content, byte for byte.
  idx-signals/results/RUNS.jsonl
  kod-machine/registry/opens.jsonl
  kod-machine/registry/scans.jsonl

Usage:
  check_append_only.py --staged        pre-commit: staged index against HEAD
  check_append_only.py --range A..B    every commit in A..B against its first parent
  check_append_only.py --all           every commit reachable from HEAD
"""

from __future__ import annotations

import argparse
import subprocess
import sys

FROZEN_DIRS = (
    "idx-signals/results/runs/",
    "idx-signals/data/manifests/",
    "kod-machine/registry/cards/",
    "kod-machine/registry/scans/",
    "kod-machine/registry/evidence/",
    "kod-machine/registry/timestamps/",
    "kod-machine/tsa/",
)
APPEND_ONLY = (
    "idx-signals/results/RUNS.jsonl",
    "kod-machine/registry/opens.jsonl",
    "kod-machine/registry/scans.jsonl",
)
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def git(*args: str, check: bool = True) -> bytes:
    proc = subprocess.run(["git", *args], capture_output=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {proc.stderr.decode().strip()}")
    return proc.stdout


def blob(ref: str | None, path: str) -> bytes:
    spec = f":{path}" if ref is None else f"{ref}:{path}"
    return git("show", spec, check=False)


def check(old: str, new: str | None) -> list[str]:
    """Compare tree `old` with commit `new`, or with the index when `new` is None."""
    args = ["diff", "--name-status", "-M"] + (["--cached", old] if new is None else [old, new])
    problems = []
    for line in git(*args).decode().splitlines():
        parts = line.split("\t")
        code, paths = parts[0], parts[1:]
        kind = code[0]
        source = paths[0]
        label = new[:12] if new else "staged"
        if kind == "A":
            continue
        if source.startswith(FROZEN_DIRS):
            problems.append(f"{label}: {code} {' -> '.join(paths)} (frozen record)")
            continue
        if source in APPEND_ONLY:
            if kind != "M":
                problems.append(f"{label}: {code} {' -> '.join(paths)} (append-only log)")
                continue
            before, after = blob(old, source), blob(new, source)
            if not after.startswith(before):
                problems.append(f"{label}: {source} rewrites earlier lines (append-only log)")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true")
    group.add_argument("--range")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    problems: list[str] = []
    if args.staged:
        has_head = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], capture_output=True).returncode == 0
        problems = check("HEAD" if has_head else EMPTY_TREE, None)
    else:
        spec = args.range if args.range else "HEAD"
        commits = git("rev-list", "--reverse", "--first-parent", spec).decode().split()
        for commit in commits:
            parents = git("rev-list", "--parents", "-n", "1", commit).decode().split()[1:]
            problems += check(parents[0] if parents else EMPTY_TREE, commit)
    for p in problems:
        print(f"append-only violation: {p}", file=sys.stderr)
    if not problems:
        print("append-only: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
