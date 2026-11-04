#!/usr/bin/env python3
"""Refuse any change that edits or deletes an append-only record.

Frozen directories: a file, once committed, may never be modified, deleted or renamed.
  idx-signals/results/runs/      one directory per backtest run
  idx-signals/data/manifests/    provenance of every downloaded data file
  idx-signals/data/corporate_actions/ca_registry-*  corporate-action registries, one file per build
  idx-signals/data/corporate_actions/us_splits-*    US split schedules with SEC evidence, one per build
  idx-signals/data/archive/      archived original inputs (Git LFS)
  idx-signals/research/          experiment protocols and their results, one directory per stage
  idx-signals/paper/scans/, idx-signals/paper/timestamps/   frozen scan snapshots and their tokens
  kod-machine/registry/cards/    frozen KOD cards, one per open
  kod-machine/registry/scans/    frozen KOD scans
  kod-machine/registry/evidence/ archived evidence bytes and metadata (v1)
  kod-machine/registry/evidence-v2/ evidence objects v2, archived bytes, content timestamps
  kod-machine/registry/timestamps/  RFC 3161 tokens
  kod-machine/tsa/               pinned timestamp-authority certificates
  kod-machine/research/          KOD case studies: protocols, evidence and findings, one directory per stage

Append-only logs: the new content must start with the old content, byte for byte.
  idx-signals/results/RUNS.jsonl
  idx-signals/data/corporate_actions/manual.csv   primary-source entries (correct by adding a row)
  idx-signals/paper/ledger.jsonl  prospective paper scans, decisions and outcomes
  idx-signals/paper/speculations.jsonl  sealed speculation sets and their resolutions
  idx-signals/paper/sensors/sensors.jsonl  free public sensor alerts
  idx-signals/paper/catalysts.jsonl  sealed catalyst sets, batches, tags and their resolutions
  idx-signals/paper/learner.jsonl  the learner's sealed forecasts (LEARNER_v1, withdrawn; kept and verified)
  idx-signals/paper/learner_v2.jsonl  the learner's sealed forecasts (LEARNER_v2)
  kod-machine/registry/opens.jsonl
  kod-machine/registry/scans.jsonl
  kod-machine/registry/receipts.jsonl

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
    "handoff/astra/protocols/",
    "costs/",
    "docs/schemas/",
    "schemas/",
    "idx-signals/results/runs/",
    "idx-signals/data/manifests/",
    "idx-signals/data/corporate_actions/ca_registry-",
    "idx-signals/data/corporate_actions/us_splits-",
    "idx-signals/data/archive/",
    "idx-signals/research/",
    "idx-signals/paper/scans/",
    "idx-signals/paper/timestamps/",
    "kod-machine/registry/",
    "kod-machine/tsa/",
    "kod-machine/research/",
)
APPEND_ONLY = (
    "registry/ids/ID_MAP.jsonl",
    "idx-signals/results/RUNS.jsonl",
    "idx-signals/data/corporate_actions/manual.csv",
    "idx-signals/paper/ledger.jsonl",
    "idx-signals/paper/speculations.jsonl",
    "idx-signals/paper/sensors/sensors.jsonl",
    "idx-signals/paper/catalysts.jsonl",
    "idx-signals/paper/learner.jsonl",
    "idx-signals/paper/learner_v2.jsonl",
    "idx-signals/paper/learner_v3.jsonl",
    "idx-signals/paper/learner_v3_evaluations.jsonl",
    "idx-signals/paper/premove_shadow.jsonl",
    "idx-signals/paper/paper_book.jsonl",
    "idx-signals/paper/paper_account.jsonl",
    "idx-signals/paper/crypto_account.jsonl",
    "kod-machine/registry/opens.jsonl",
    "kod-machine/registry/scans.jsonl",
    "kod-machine/registry/receipts.jsonl",
)
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def git(*args: str, check: bool = True) -> bytes:
    proc = subprocess.run(["git", *args], capture_output=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {proc.stderr.decode().strip()}")
    return proc.stdout


def blob(ref: str | None, path: str) -> bytes:
    spec = f":{path}" if ref is None else f"{ref}:{path}"
    # A failed read must never masquerade as an empty historical prefix.
    return git("show", spec)


def changes(raw: bytes):
    """Read git's NUL format; tabs/newlines in a path cannot evade protection."""
    fields = iter(raw.split(b"\0"))
    for field in fields:
        if not field:
            continue
        code = field.decode("ascii")
        count = 2 if code[0] in ("R", "C") else 1
        try:
            paths = [next(fields).decode("utf-8", "surrogateescape") for _ in range(count)]
        except StopIteration as exc:
            raise SystemExit("git returned an incomplete diff record") from exc
        if any(not path for path in paths):
            raise SystemExit("git returned an empty diff path")
        yield code, paths


def check(old: str, new: str | None) -> list[str]:
    """Compare tree `old` with commit `new`, or with the index when `new` is None."""
    args = ["diff", "--name-status", "-z", "-M"] + (
        ["--cached", old] if new is None else [old, new]
    )
    problems = []
    for code, paths in changes(git(*args)):
        kind = code[0]
        source = paths[0]
        label = new[:12] if new else "staged"
        if kind == "A":
            continue
        # Explicit logs may grow within a frozen directory; all other bytes stay fixed.
        if source in APPEND_ONLY:
            if kind != "M":
                problems.append(f"{label}: {code} {' -> '.join(paths)} (append-only log)")
                continue
            before, after = blob(old, source), blob(new, source)
            if not after.startswith(before):
                problems.append(f"{label}: {source} rewrites earlier lines (append-only log)")
        elif source.startswith(FROZEN_DIRS):
            problems.append(f"{label}: {code} {' -> '.join(paths)} (frozen record)")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true")
    group.add_argument("--range")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    problems: list[str] = []
    if args.staged:
        has_head = (
            subprocess.run(
                ["git", "rev-parse", "--verify", "-q", "HEAD"], capture_output=True
            ).returncode
            == 0
        )
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
