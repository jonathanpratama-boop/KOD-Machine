"""Remote timestamp receipts: when an anchor commit first reached GitHub, by GitHub's clock.

A git commit date is written by the committer and can say anything. A commit that is on
GitHub today proves nothing about when it got there. What GitHub records itself is the
workflow run it creates when a push arrives: the run's `created_at` is set by GitHub's
servers and its `head_sha` is the pushed commit. So the receipt for an anchor is the
earliest push-triggered run whose head_sha is exactly the anchor commit.

What it proves: the anchor commit, and therefore the frozen hash in it, was on GitHub no
later than `created_at`. A backdated commit pushed after the outcome gets a run created
after the outcome. What it does not prove: anything if the run is deleted (an admin can
delete runs). Deletion cannot make a call look earlier; it can only make a call
unverifiable, and an unverifiable call is excluded and counted, so selective deletion
shows up as excluded calls in the report.

Verification never trusts a time stored locally. It asks GitHub again. Without API
access the status is REMOTE_TIMESTAMP_UNVERIFIED and the case does not count.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .hashing import fmt_ts, parse_ts, sha256_bytes

PROVIDER = "GITHUB_ACTIONS"
VERIFIED = "REMOTE_TIMESTAMP_VERIFIED"
UNVERIFIED = "REMOTE_TIMESTAMP_UNVERIFIED"
LATE = "REMOTE_TIMESTAMP_LATE"
MISMATCH = "REMOTE_RECEIPT_MISMATCH"


class RemoteUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Run:
    run_id: str
    head_sha: str
    event: str
    created_at: datetime
    html_url: str
    response_sha256: str


def repository_from_git(repo_dir: Path | None = None) -> str | None:
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=repo_dir, capture_output=True, text=True
    )
    if proc.returncode != 0:
        return None
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", proc.stdout.strip())
    return f"{match.group(1)}/{match.group(2)}" if match else None


class GitHubActionsClient:
    def __init__(
        self,
        repository: str | None = None,
        token: str | None = None,
        api_url: str | None = None,
        repo_dir: Path | None = None,
        timeout: float = 20.0,
    ):
        self.token = (
            token
            if token is not None
            else (os.environ.get("KOD_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN"))
        )
        self.repository = (
            repository or os.environ.get("GITHUB_REPOSITORY") or repository_from_git(repo_dir)
        )
        self.api_url = (
            api_url or os.environ.get("GITHUB_API_URL") or "https://api.github.com"
        ).rstrip("/")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.token and self.repository)

    @property
    def why_unavailable(self) -> str:
        if not self.token:
            return "no GitHub API token (set GITHUB_TOKEN or KOD_GITHUB_TOKEN with actions:read)"
        return "repository unknown (set GITHUB_REPOSITORY=owner/repo)"

    def _get(self, path: str) -> tuple[dict, bytes]:
        req = urllib.request.Request(
            f"{self.api_url}{path}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "kod-machine-verify",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as exc:
            raise RemoteUnavailable(f"GitHub API {exc.code} for {path}") from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise RemoteUnavailable(f"GitHub API unreachable: {exc}") from exc
        return json.loads(body), body

    @staticmethod
    def _run(obj: dict, raw: bytes) -> Run:
        return Run(
            str(obj["id"]),
            obj["head_sha"],
            obj["event"],
            parse_ts(obj["created_at"]),
            obj.get("html_url", ""),
            sha256_bytes(raw),
        )

    def runs_for_commit(self, sha: str) -> list[Run]:
        body, _ = self._get(
            f"/repos/{self.repository}/actions/runs?head_sha={sha}&event=push&per_page=100"
        )
        runs = []
        for obj in body.get("workflow_runs", []):
            runs.append(self._run(obj, json.dumps(obj, sort_keys=True).encode()))
        return runs

    def run(self, run_id: str) -> Run:
        body, raw = self._get(f"/repos/{self.repository}/actions/runs/{run_id}")
        return self._run(body, raw)


def earliest_exact(runs: list[Run], sha: str) -> Run | None:
    exact = [r for r in runs if r.head_sha == sha and r.event == "push"]
    return min(exact, key=lambda r: r.created_at) if exact else None


def remote_status(client, anchor_sha: str, deadline: str | None, recorded: list[dict]) -> dict:
    """Status of one anchor commit against GitHub. Never reads a time from the database
    without confirming it against the API."""
    out = {
        "status": UNVERIFIED,
        "anchor_sha": anchor_sha,
        "reason": "",
        "remote_created_at": None,
        "run_id": None,
        "url": None,
    }
    if client is None or not client.available:
        out["reason"] = (
            client.why_unavailable if client is not None else "no GitHub client configured"
        )
        return out
    try:
        runs = client.runs_for_commit(anchor_sha)
        for rec in recorded:
            live = next((r for r in runs if r.run_id == rec["remote_event_id"]), None)
            if live is None:
                try:
                    live = client.run(rec["remote_event_id"])
                except RemoteUnavailable:
                    live = None
            if live is None:
                out["reason"] = (
                    f"recorded receipt run {rec['remote_event_id']} is no longer on GitHub"
                )
                continue
            if live.head_sha != anchor_sha or live.created_at != parse_ts(rec["remote_created_at"]):
                out.update(
                    status=MISMATCH,
                    reason=(
                        f"recorded receipt says run {rec['remote_event_id']} for {anchor_sha[:12]} at "
                        f"{rec['remote_created_at']}; GitHub says {live.head_sha[:12]} at {fmt_ts(live.created_at)}"
                    ),
                )
                return out
    except RemoteUnavailable as exc:
        out["reason"] = str(exc)
        return out
    run = earliest_exact(runs, anchor_sha)
    if run is None:
        out["reason"] = out["reason"] or "GitHub has no push-triggered run for this exact commit"
        return out
    out.update(remote_created_at=fmt_ts(run.created_at), run_id=run.run_id, url=run.html_url)
    if deadline and run.created_at >= parse_ts(deadline):
        out.update(
            status=LATE,
            reason=(
                f"the commit first reached GitHub at {fmt_ts(run.created_at)}, not before {deadline}"
            ),
        )
        return out
    out.update(status=VERIFIED, reason="")
    return out
