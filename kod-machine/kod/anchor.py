"""Git anchor. Every open's hash is committed to git so its timestamp lives outside the database.

An anchor appends one line to an append-only registry file and writes the frozen
body next to it, then commits exactly those two paths. Other staged work is left
alone. A local commit date comes from the local clock, so the anchor that a
third party can rely on is the push: `--push` sends the commit to the remote at
open time, and `verify` reports whether each anchor commit is on a remote branch.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .hashing import canonical

REGISTRY_FILES = {"CASE": "opens.jsonl", "SCAN": "scans.jsonl"}
BODY_DIRS = {"CASE": "cards", "SCAN": "scans"}


class AnchorError(RuntimeError):
    pass


@dataclass(frozen=True)
class AnchorReceipt:
    commit: str
    registry_path: str
    committed_at: str
    pushed: bool
    push_error: str = ""


def _safe_name(record_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", record_id):
        raise AnchorError(f"record id {record_id!r} has characters that cannot name a registry file")
    return record_id.replace(":", "_")


class GitAnchor:
    def __init__(self, registry_dir: Path, push: bool = False, remote: str = "origin", extra_env=None,
                 trailer: str = ""):
        self.registry_dir = Path(registry_dir).resolve()
        self.push = push
        self.remote = remote
        # Optional lines appended to each anchor commit message (sign-off, co-author).
        self.trailer = trailer.strip()
        # Callable returning extra git environment. Tests use it to pin commit dates to a
        # fake clock, which is also why a local commit date alone proves nothing.
        self.extra_env = extra_env
        self._repo: Path | None = None

    def _env(self) -> dict:
        return {**os.environ, "GIT_TERMINAL_PROMPT": "0", **(self.extra_env() if self.extra_env else {})}

    # -- git plumbing -------------------------------------------------------

    def git(self, *args: str, check: bool = True) -> str:
        proc = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, env=self._env())
        if check and proc.returncode != 0:
            raise AnchorError(f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
        return proc.stdout

    @property
    def repo(self) -> Path:
        if self._repo is None:
            self.registry_dir.mkdir(parents=True, exist_ok=True)
            proc = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.registry_dir,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise AnchorError(f"registry {self.registry_dir} is not inside a git repository")
            self._repo = Path(proc.stdout.strip()).resolve()
        return self._repo

    def rel(self, path: Path) -> str:
        return Path(path).resolve().relative_to(self.repo).as_posix()

    # -- anchoring ----------------------------------------------------------

    def anchor(self, kind: str, record_id: str, sha: str, line: dict, body: dict) -> AnchorReceipt:
        if kind not in REGISTRY_FILES:
            raise AnchorError(f"unknown anchor kind {kind}")
        registry = self.registry_dir / REGISTRY_FILES[kind]
        body_path = self.registry_dir / BODY_DIRS[kind] / f"{_safe_name(record_id)}.json"
        if body_path.exists():
            raise AnchorError(f"{kind} {record_id} is already anchored; refusing rewrite")
        if self.git("status", "--porcelain", "--", self.rel(registry)).strip():
            raise AnchorError(f"{self.rel(registry)} has uncommitted edits; the registry is append-only")
        record = {"kind": kind, "record_id": record_id, "sha256": sha, **line}
        body_path.parent.mkdir(parents=True, exist_ok=True)
        size_before = registry.stat().st_size if registry.exists() else None
        paths = [self.rel(registry), self.rel(body_path)]
        try:
            body_path.write_text(json.dumps(body, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            with registry.open("a", encoding="utf-8") as fh:
                fh.write(canonical(record) + "\n")
            self.git("add", "--", *paths)
            message = f"kod anchor {kind.lower()} {record_id} {sha}"
            if self.trailer:
                message += "\n\n" + self.trailer
            self.git("commit", "-q", "-m", message, "--only", "--", *paths)
        except Exception:
            self.git("reset", "-q", "--", *paths, check=False)
            body_path.unlink(missing_ok=True)
            if size_before is None:
                registry.unlink(missing_ok=True)
            else:
                with registry.open("r+b") as fh:
                    fh.truncate(size_before)
            raise
        commit = self.git("rev-parse", "HEAD").strip()
        committed_at = self.git("show", "-s", "--format=%cI", commit).strip()
        pushed, push_error = False, ""
        if self.push:
            proc = subprocess.run(
                ["git", "push", self.remote, "HEAD"], cwd=self.repo, capture_output=True, text=True, env=self._env()
            )
            pushed = proc.returncode == 0
            push_error = "" if pushed else (proc.stderr.strip() or "push failed")
        return AnchorReceipt(commit, paths[0], committed_at, pushed, push_error)

    # -- verification helpers -----------------------------------------------

    def committed_records(self, commit: str, registry_path: str) -> list[dict]:
        text = self.git("show", f"{commit}:{registry_path}", check=False)
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def commit_time(self, commit: str) -> str | None:
        out = self.git("show", "-s", "--format=%cI", commit, check=False).strip()
        return out or None

    def is_ancestor_of_head(self, commit: str) -> bool:
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0

    def on_remote(self, commit: str) -> bool:
        return bool(self.git("branch", "-r", "--contains", commit, check=False).strip())
