"""Hermetic temporary Git repositories for the push-time check tests (standard library only)."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

TOOLS = Path(__file__).resolve().parents[1]
ZERO_SHA = "0" * 40
# A fixed identity and UTC clock. The user's Git configuration (commit signing, hooks, default
# branch) is never read, so the fixtures behave the same on a workstation and in CI.
ENV = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
ENV.update(
    GIT_CONFIG_GLOBAL=os.devnull,
    GIT_CONFIG_NOSYSTEM="1",
    GIT_MERGE_AUTOEDIT="no",
    GIT_AUTHOR_NAME="fixture",
    GIT_AUTHOR_EMAIL="fixture.invalid",
    GIT_COMMITTER_NAME="fixture",
    GIT_COMMITTER_EMAIL="fixture.invalid",
    GIT_AUTHOR_DATE="2026-11-04T12:00:00+00:00",
    GIT_COMMITTER_DATE="2026-11-04T12:00:00+00:00",
)


class Repo:
    """A repository in `root` with a `main` branch; commit() and merge() return the new HEAD."""

    def __init__(self, root: Path):
        self.root = root
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", *args], cwd=self.root, env=ENV, capture_output=True, text=True
        )
        if proc.returncode:
            raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
        return proc.stdout.strip()

    def write(self, files: dict[str, str]) -> None:
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def append(self, name: str, text: str) -> None:
        with (self.root / name).open("a", encoding="utf-8") as handle:
            handle.write(text)

    def commit(self, message: str, files: dict[str, str] | None = None) -> str:
        self.write(files or {})
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.head()

    def merge(self, branch: str, message: str, files: dict[str, str] | None = None) -> str:
        """A --no-ff merge of `branch`; `files` are added in the merge commit itself."""
        if files is None:
            self.git("merge", "-q", "--no-ff", "-m", message, branch)
            return self.head()
        self.git("merge", "-q", "--no-ff", "--no-commit", branch)
        return self.commit(message, files)

    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def run(self, tool: str, *args: str) -> subprocess.CompletedProcess:
        """Run tools/<tool> exactly as CI does, with this repository as the working directory."""
        return subprocess.run(
            [sys.executable, str(TOOLS / tool), *args],
            cwd=self.root,
            env=ENV,
            capture_output=True,
            text=True,
        )
