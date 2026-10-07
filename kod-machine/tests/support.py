"""Test fixtures: a throwaway git repository for anchors, a settable clock, card builders."""

from __future__ import annotations

import copy
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kod.anchor import GitAnchor
from kod.hashing import fmt_ts
from kod.ledger import Ledger

T0 = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, moment: datetime = T0):
        self.moment = moment

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, **kwargs) -> None:
        self.moment += timedelta(**kwargs)


class Lab:
    """A ledger whose anchors land in a fresh git repository."""

    def __init__(self, clock: Clock | None = None):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "kod-test")
        self.git("config", "user.email", "kod-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("commit", "-q", "--allow-empty", "-m", "root")
        self.clock = clock or Clock()
        self.registry = self.repo / "registry"
        self.anchor = GitAnchor(self.registry, extra_env=self.git_dates)
        self.ledger = Ledger(Path(self.tmp.name) / "kod.db", anchor=self.anchor, clock=self.clock)

    def git_dates(self) -> dict:
        stamp = fmt_ts(self.clock())
        return {"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True).stdout

    def cleanup(self) -> None:
        self.ledger.conn.close()
        self.tmp.cleanup()


def prospective_card(case_id: str, cutoff: datetime, window_start: datetime, window_end: datetime,
                     facts: dict | None = None, **extra) -> dict:
    facts = facts if facts is not None else {"dated_catalyst_known": True, "catalyst": "scheduled print"}
    card = {
        "case_id": case_id,
        "symbol": "TEST",
        "venue": "IDX",
        "call_type": "PROSPECTIVE",
        "decision_cutoff": fmt_ts(cutoff),
        "outcome_window": {"start": fmt_ts(window_start), "end": fmt_ts(window_end)},
        "universe_id": "TEST-UNIVERSE",
        "reconstruction_status": "PARTIAL_PUBLIC",
        "story_hypothesis": "Test card.",
        "disposition": "WATCH",
        "critic": {
            "loss_path": "Nothing happens.",
            "missing_evidence": "Everything not in the facts.",
            "invalidation": "No repricing inside the window.",
        },
        "information_sets": {
            h: {"cutoff": fmt_ts(cutoff - delta), "reconstruction_status": "PARTIAL_PUBLIC", "facts": copy.deepcopy(facts)}
            for h, delta in (("T-30D", timedelta(days=30)), ("T-72H", timedelta(hours=72)), ("T-24H", timedelta(hours=24)))
        },
    }
    card.update(extra)
    return card
