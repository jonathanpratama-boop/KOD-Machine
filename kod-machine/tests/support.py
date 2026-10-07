"""Test fixtures: a throwaway git repository for anchors, a settable clock, a fake timestamp
authority that follows that clock, archived evidence, and card builders."""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kod.anchor import GitAnchor
from kod.hashing import fmt_ts, parse_ts, sha256_bytes
from kod.ledger import Ledger
from kod.timestamp import Stamp, TimestampError

T0 = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, moment: datetime = T0):
        self.moment = moment

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, **kwargs) -> None:
        self.moment += timedelta(**kwargs)


class FakeTimestamper:
    """Stands in for an RFC 3161 authority: a token that binds the data's digest to the test
    clock. Not cryptographic; the real authorities are tested in test_timestamp.py."""

    def __init__(self, clock: Clock, name: str = "fake"):
        self.clock = clock
        self.name = name
        self.last_errors: list[str] = []
        self.down = False

    def stamp(self, data: bytes) -> list[Stamp]:
        if self.down:
            self.last_errors = [f"{self.name}: unreachable"]
            return []
        token = json.dumps({"sha256": sha256_bytes(data), "time": fmt_ts(self.clock())}).encode()
        return [Stamp(self.name, token, self.clock())]

    def verify(self, authority: str, token: bytes, data: bytes) -> datetime:
        if authority != self.name:
            raise TimestampError(f"unknown timestamp authority {authority!r}")
        body = json.loads(token)
        if body["sha256"] != sha256_bytes(data):
            raise TimestampError("token does not match the data")
        return parse_ts(body["time"])


class Lab:
    """A ledger whose anchors land in a fresh git repository, stamped by a fake authority."""

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
        self.timestamper = FakeTimestamper(self.clock)
        self.anchor = GitAnchor(self.registry, extra_env=self.git_dates, timestamper=self.timestamper)
        self.ledger = Ledger(Path(self.tmp.name) / "kod.db", anchor=self.anchor, clock=self.clock)
        self.evidence_id = self.add_evidence("Issuer announces earnings date.", published=self.clock() - timedelta(days=40))

    def add_evidence(self, text: str, published: datetime, grade: str = "A", name: str = "doc.html") -> str:
        path = Path(self.tmp.name) / name
        path.write_text(text)
        return self.ledger.add_evidence(path, {
            "source_url": "https://www.idx.co.id/example",
            "publisher": "IDX disclosure system",
            "published_at": fmt_ts(published),
            "published_at_basis": "disclosure system timestamp",
            "retrieved_at": fmt_ts(self.clock() - timedelta(hours=2)),
            "grade": grade,
        })

    def git_dates(self) -> dict:
        stamp = fmt_ts(self.clock())
        return {"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True).stdout

    def cleanup(self) -> None:
        self.ledger.conn.close()
        self.tmp.cleanup()


def prospective_card(case_id: str, cutoff: datetime, window_start: datetime, window_end: datetime,
                     facts: dict | None = None, evidence: list[str] | None = None, **extra) -> dict:
    facts = facts if facts is not None else {"dated_catalyst_known": True, "catalyst": "scheduled print"}

    def info_set(delta):
        payload = {"cutoff": fmt_ts(cutoff - delta), "reconstruction_status": "PARTIAL_PUBLIC",
                   "facts": copy.deepcopy(facts)}
        if evidence:
            payload["evidence"] = {k: list(evidence) for k, v in facts.items() if v is not None}
        return payload

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
            h: info_set(delta)
            for h, delta in (("T-30D", timedelta(days=30)), ("T-72H", timedelta(hours=72)), ("T-24H", timedelta(hours=24)))
        },
    }
    card.update(extra)
    return card
