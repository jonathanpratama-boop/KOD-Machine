#!/usr/bin/env python3
"""Conservative CI routing. Uncertainty costs minutes, never missing checks.

All PRs and manual runs run full suites. Non-default branch pushes run integrity
only. Default pushes may reuse a successful full-test parent baseline for a
narrowly defined append-only forecast update. Integrity
and the exact-push receipt run independently of this decision.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

WORKFLOW = ".github/workflows/checks.yml"
# No blanket data/, research/, docs/, or extension exclusions. New formats run tests.
FORECAST_LOGS = frozenset({
    "idx-signals/paper/ledger.jsonl",
    "idx-signals/paper/speculations.jsonl",
    "idx-signals/paper/catalysts.jsonl",
    "idx-signals/paper/learner.jsonl",
    "idx-signals/paper/learner_v2.jsonl",
    "idx-signals/paper/learner_v3.jsonl",
    "idx-signals/paper/learner_v3_evaluations.jsonl",
    "idx-signals/paper/sensors/sensors.jsonl",
    "kod-machine/registry/opens.jsonl",
    "kod-machine/registry/scans.jsonl",
    "kod-machine/registry/receipts.jsonl",
})


def forecast_only(changes: list[tuple[str, str]]) -> bool:
    return bool(changes) and all(
        status in {"A", "M"} and path in FORECAST_LOGS
        for status, path in changes
    )


def changed_files(before: str, after: str) -> list[tuple[str, str]]:
    for sha in (before, after):
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or sha == "0" * 40:
            raise ValueError("missing/initial commit baseline")
    # Never treat a force-push that drops code/history as a routine forecast append.
    subprocess.run(["git", "merge-base", "--is-ancestor", before, after], check=True,
                   capture_output=True)
    raw = subprocess.check_output([
        "git", "diff", "--name-status", "--no-renames", "-z", before, after,
    ]).decode("utf-8").split("\0")
    if raw[-1] != "" or (len(raw) - 1) % 2:
        raise ValueError("invalid git diff output")
    return list(zip(raw[0:-1:2], raw[1:-1:2]))


def api_get(path: str) -> dict:
    # GitHub.com repository, fixed trusted host; never send token to event-provided URLs.
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def runs(repo: str, sha: str, event: str, get=api_get) -> list[dict]:
    query = urllib.parse.urlencode({"head_sha": sha, "event": event, "per_page": 100})
    result = get(f"/repos/{repo}/actions/runs?{query}")
    return [r for r in result["workflow_runs"] if
            r.get("head_sha") == sha and r.get("event") == event
            and r.get("path") == WORKFLOW]


def full_baseline(repo: str, sha: str, get=api_get) -> bool:
    for run in runs(repo, sha, "push", get):
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            continue
        # Do not reuse a run whose suites were skipped: an actual full-test baseline
        # is required. A second forecast push may therefore run full tests again.
        jobs = get(f"/repos/{repo}/actions/runs/{int(run['id'])}/jobs?per_page=100")["jobs"]
        successes = {j["name"] for j in jobs if j.get("conclusion") == "success"}
        if {"code-tests", "workstation"} <= successes:
            return True
    return False


def decide(event_name: str, event: dict, get=api_get, diff=changed_files) -> tuple[bool, str]:
    if event_name != "push":
        return True, "PRs and other events run all suites"
    try:
        repo = event["repository"]["full_name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("invalid repository")
        sha, before = event["after"], event["before"]
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("invalid head SHA")
        # Full suites belong to PRs and the default branch, not both events for
        # every topic commit. Push receipts/integrity never depend on this choice.
        default_ref = "refs/heads/" + event["repository"]["default_branch"]
        if event.get("ref", "").startswith("refs/heads/") and event["ref"] != default_ref:
            return False, "topic-branch push: integrity now, full suites on PR/manual run"
        if event.get("ref", "").startswith("refs/heads/"):
            if forecast_only(diff(before, sha)) and full_baseline(repo, before, get):
                return False, "forecast logs only; parent has successful full suites"
        return True, "code, unknown paths, or no verified full-test baseline"
    except Exception as exc:
        # Do not print URLs, response bodies, or tokens from API exceptions.
        return True, f"routing unavailable ({type(exc).__name__}); running all suites"


def main() -> None:
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        selected, reason = decide(os.environ.get("GITHUB_EVENT_NAME", ""), event)
    except Exception as exc:
        selected, reason = True, f"event unavailable ({type(exc).__name__}); running all suites"
    value = str(selected).lower()
    print(f"run-tests={value}: {reason}")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"run-tests={value}\n")


if __name__ == "__main__":
    main()
