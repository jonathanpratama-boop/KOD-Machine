"""Which commits a push-time check reads, and how it reports findings to GitHub.

Two ways to name the commits, shared by the push-time checks in tools/:
  --range BASE..HEAD   strict: both ends must be commits and BASE an ancestor of HEAD.
  --push BEFORE AFTER  GitHub's push values (github.event.before, github.sha). BEFORE is all
                       zeros when the push creates the branch; after a force-push it is not an
                       ancestor of AFTER and may be missing from the clone. In those cases only the
                       AFTER commit is read (against its first parent) and the reason is printed as
                       a ::notice. No other input falls back; anything else is a RangeError.

Not claimed: a head-only fallback reads less than the push may contain (earlier commits pushed
with a new branch or a force-push are not read). Standard library only: CI runs the checks before
installing requirements.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
import subprocess

ZERO_SHA = "0" * 40
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
FULL_SHA = re.compile(r"[0-9a-f]{40}")


class RangeError(Exception):
    """The commits to read cannot be determined; the message says why."""


@dataclass(frozen=True)
class CommitRange:
    base: str | None  # None: only `head` is read, against its first parent
    head: str
    fallback: str | None = None  # why a push is read as its head commit alone

    def __str__(self) -> str:
        if self.base is None:
            return f"{self.head[:12]} (head commit only)"
        return f"{self.base[:12]}..{self.head[:12]}"


def git_bytes(*args: str) -> bytes:
    proc = subprocess.run(["git", *args], capture_output=True)
    if proc.returncode:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise RangeError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout


def git(*args: str) -> str:
    return git_bytes(*args).decode("utf-8", "surrogateescape")


def commit_sha(rev: str) -> str | None:
    """The full id of commit `rev`, or None when this repository has no such commit."""
    if rev.startswith("-"):
        return None
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def is_ancestor(ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant], capture_output=True, text=True
    )
    if proc.returncode not in (0, 1):
        raise RangeError(f"git merge-base --is-ancestor failed: {proc.stderr.strip()}")
    return proc.returncode == 0


def from_range(spec: str) -> CommitRange:
    base, separator, head = spec.partition("..")
    if not separator or not base or not head or head.startswith("."):
        raise RangeError(f"--range must be BASE..HEAD, got {spec!r}")
    shas = []
    for rev in (base, head):
        sha = commit_sha(rev)
        if sha is None:
            raise RangeError(f"--range: {rev!r} is not a commit in this repository")
        shas.append(sha)
    if not is_ancestor(*shas):
        raise RangeError(f"--range: {base} is not an ancestor of {head}")
    return CommitRange(*shas)


def from_push(before: str, after: str) -> CommitRange:
    for name, value in (("before", before), ("after", after)):
        if not FULL_SHA.fullmatch(value):
            raise RangeError(f"--push: {name} must be a 40-character commit id, got {value!r}")
    head = commit_sha(after)
    if head is None:
        raise RangeError(f"--push: after {after} is not a commit in this repository")
    if before == ZERO_SHA:
        return CommitRange(None, head, "new branch (before is all zeros)")
    base = commit_sha(before)
    if base is None:
        reason = f"before {before[:12]} is not in this clone (force-push or rewritten history)"
        return CommitRange(None, head, reason)
    if not is_ancestor(base, head):
        reason = f"before {before[:12]} is not an ancestor of {after[:12]} (force-push)"
        return CommitRange(None, head, reason)
    return CommitRange(base, head)


def add_range_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--range", metavar="BASE..HEAD", help="strict: the commits after BASE")
    group.add_argument(
        "--push",
        nargs=2,
        metavar=("BEFORE", "AFTER"),
        help="GitHub push values; a new branch or force-push reads AFTER alone",
    )


def resolve(args: argparse.Namespace) -> CommitRange:
    return from_range(args.range) if args.range is not None else from_push(*args.push)


def parents(sha: str) -> list[str]:
    return git("rev-list", "--parents", "-n", "1", sha).split()[1:]


def compared_tree(commits: CommitRange) -> str:
    """What the range is compared against: BASE, else the head's first parent or the empty tree."""
    if commits.base is not None:
        return commits.base
    first = parents(commits.head)[:1]
    return first[0] if first else EMPTY_TREE


def changed_paths(old: str, new: str, *, added_only: bool = False, under: str = "") -> list[str]:
    """Paths that differ between two commits; a rename counts as a deletion plus an addition."""
    raw = git(
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        *(["--diff-filter=A"] if added_only else []),
        old,
        new,
        "--",
        *([under] if under else []),
    )
    return [path for path in raw.split("\0") if path]


def blob(commit: str, path: str) -> bytes:
    return git_bytes("cat-file", "blob", f"{commit}:{path}")


def workflow_command(command: str, message: str, **properties: object) -> str:
    """A GitHub Actions workflow command such as ::warning file=a.py,line=3::text, escaped."""
    fields = ",".join(
        f"{key}={_escape(str(value), True)}"
        for key, value in properties.items()
        if value is not None
    )
    return f"::{command}{' ' + fields if fields else ''}::{_escape(message, False)}"


def _escape(text: str, is_property: bool) -> str:
    text = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return text.replace(":", "%3A").replace(",", "%2C") if is_property else text
