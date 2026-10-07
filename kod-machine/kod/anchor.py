"""Git anchor. Every open's hash is committed to git so its timestamp lives outside the database.

An anchor appends one line to an append-only registry file, writes the frozen body next
to it, and commits exactly those paths. Other staged work is left alone.

The git commit date is not evidence of time: it comes from the committer's clock, and a
backdated commit pushed later still shows its backdated date. The time evidence is the
RFC 3161 tokens (kod/timestamp.py): before the commit, the exact registry line is sent as
a digest to independent timestamp authorities and their signed tokens are committed with
it under registry/timestamps/. `verify` checks those tokens, not the commit date.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .hashing import canonical, fmt_ts

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
    timestamps: list = field(default_factory=list)  # [{"authority", "path", "time"}]
    timestamp_errors: list = field(default_factory=list)


def _safe_name(record_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", record_id):
        raise AnchorError(f"record id {record_id!r} has characters that cannot name a registry file")
    return record_id.replace(":", "_")


def anchor_line(record: dict) -> bytes:
    """The exact bytes of a registry line; this is what the timestamp authorities sign."""
    return canonical(record).encode("utf-8")


class GitAnchor:
    def __init__(self, registry_dir: Path, push: bool = False, remote: str = "origin", extra_env=None,
                 trailer: str = "", timestamper=None):
        self.registry_dir = Path(registry_dir).resolve()
        self.push = push
        self.remote = remote
        # Optional lines appended to each anchor commit message (sign-off, co-author).
        self.trailer = trailer.strip()
        # Callable returning extra git environment. Tests use it to pin commit dates to a
        # fake clock, which is also why a local commit date alone proves nothing.
        self.extra_env = extra_env
        self.timestamper = timestamper
        self._repo: Path | None = None

    def _env(self) -> dict:
        return {**os.environ, "GIT_TERMINAL_PROMPT": "0", **(self.extra_env() if self.extra_env else {})}

    # -- git plumbing -------------------------------------------------------

    def git(self, *args: str, check: bool = True) -> str:
        proc = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, env=self._env())
        if check and proc.returncode != 0:
            raise AnchorError(f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
        return proc.stdout

    def git_bytes(self, *args: str) -> bytes | None:
        proc = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, env=self._env())
        return proc.stdout if proc.returncode == 0 else None

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

    def _commit(self, paths: list[str], message: str) -> str:
        self.git("add", "--", *paths)
        if self.trailer:
            message += "\n\n" + self.trailer
        self.git("commit", "-q", "-m", message, "--only", "--", *paths)
        return self.git("rev-parse", "HEAD").strip()

    def _push(self) -> tuple[bool, str]:
        if not self.push:
            return False, ""
        proc = subprocess.run(
            ["git", "push", self.remote, "HEAD"], cwd=self.repo, capture_output=True, text=True, env=self._env()
        )
        return proc.returncode == 0, "" if proc.returncode == 0 else (proc.stderr.strip() or "push failed")

    # -- anchoring ----------------------------------------------------------

    def anchor(self, kind: str, record_id: str, sha: str, line: dict, body: dict,
               require_timestamp: bool = False) -> AnchorReceipt:
        if kind not in REGISTRY_FILES:
            raise AnchorError(f"unknown anchor kind {kind}")
        registry = self.registry_dir / REGISTRY_FILES[kind]
        name = _safe_name(record_id)
        body_path = self.registry_dir / BODY_DIRS[kind] / f"{name}.json"
        if body_path.exists():
            raise AnchorError(f"{kind} {record_id} is already anchored; refusing rewrite")
        if self.git("status", "--porcelain", "--", self.rel(registry)).strip():
            raise AnchorError(f"{self.rel(registry)} has uncommitted edits; the registry is append-only")
        record = {"kind": kind, "record_id": record_id, "sha256": sha, **line}
        data = anchor_line(record)
        stamps, stamp_errors = [], []
        if self.timestamper is not None:
            stamps = self.timestamper.stamp(data)
            stamp_errors = list(getattr(self.timestamper, "last_errors", []))
        if require_timestamp and not stamps:
            detail = "; ".join(stamp_errors) or "no timestamp authority is configured"
            raise AnchorError(f"no external timestamp for {kind.lower()} {record_id}: {detail}")
        token_dir = self.registry_dir / "timestamps" / kind.lower()
        token_paths = [token_dir / f"{name}.{s.authority}.tsr" for s in stamps]
        written: list[Path] = []
        size_before = registry.stat().st_size if registry.exists() else None
        paths = [self.rel(registry), self.rel(body_path)]
        try:
            body_path.parent.mkdir(parents=True, exist_ok=True)
            body_path.write_text(json.dumps(body, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written.append(body_path)
            for stamp, path in zip(stamps, token_paths):
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as fh:
                    fh.write(stamp.token)
                written.append(path)
                paths.append(self.rel(path))
            with registry.open("ab") as fh:
                fh.write(data + b"\n")
            commit = self._commit(paths, f"kod anchor {kind.lower()} {record_id} {sha}")
        except Exception:
            self.git("reset", "-q", "--", *paths, check=False)
            for path in written:
                path.unlink(missing_ok=True)
            if size_before is None:
                registry.unlink(missing_ok=True)
            else:
                with registry.open("r+b") as fh:
                    fh.truncate(size_before)
            raise
        committed_at = self.git("show", "-s", "--format=%cI", commit).strip()
        pushed, push_error = self._push()
        timestamps = [
            {"authority": s.authority, "path": self.rel(p), "time": fmt_ts(s.time)} for s, p in zip(stamps, token_paths)
        ]
        return AnchorReceipt(commit, paths[0], committed_at, pushed, push_error, timestamps, stamp_errors)

    def store_files(self, files: dict[Path, bytes], message: str) -> str:
        """Write new files (never overwrite) and commit exactly them. Returns the commit."""
        written, paths = [], []
        try:
            for path, data in files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as fh:
                    fh.write(data)
                written.append(path)
                paths.append(self.rel(path))
            return self._commit(paths, message)
        except Exception:
            self.git("reset", "-q", "--", *paths, check=False)
            for path in written:
                path.unlink(missing_ok=True)
            raise

    # -- verification helpers -----------------------------------------------

    def committed_records(self, commit: str, registry_path: str) -> list[dict]:
        text = self.git("show", f"{commit}:{registry_path}", check=False)
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def committed_file(self, commit: str, path: str) -> bytes | None:
        return self.git_bytes("show", f"{commit}:{path}")

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
