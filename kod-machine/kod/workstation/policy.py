"""One information-time policy for every read: notes, the dossier, search, calculations, models, thesis checks and exports.

A record is eligible at a cutoff only if its availability is evidenced before the cutoff (`public` reconstruction), and in `observed` mode also only if this
installation actually held it before the cutoff. Eligibility is decided BEFORE revisions are selected, figures are resolved, search results are ranked or
conditions are evaluated, so a later amendment can never change what an earlier cutoff shows.

Two named policies:
- KOD-ASOF-v1-strict: availability needs a timestamp at or before the cutoff. A date-only availability is not used (the existing note behaviour).
- KOD-ASOF-v1-day-end: a date-only availability counts from the end of that calendar day in its stated timezone (SEC filing dates: America/New_York).
  It never claims intraday knowledge; a filing dated D is first eligible at 00:00 on D+1 in New York.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from ..hashing import fmt_ts, parse_ts

STRICT = "KOD-ASOF-v1-strict"
DAY_END = "KOD-ASOF-v1-day-end"
POLICIES = (STRICT, DAY_END)
DATE_ZONE = "America/New_York"


@dataclass(frozen=True, slots=True)
class AsOfPolicy:
    cutoff: datetime
    mode: Literal["observed", "public"]
    policy_version: str = STRICT

    def __post_init__(self):
        if (
            not isinstance(self.cutoff, datetime)
            or self.cutoff.tzinfo is None
            or self.cutoff.utcoffset() is None
        ):
            raise ValueError("the cutoff must be a timezone-aware datetime")
        if self.mode not in ("observed", "public"):
            raise ValueError("mode must be observed or public")
        if self.policy_version not in POLICIES:
            raise ValueError("unknown information-time policy " + repr(self.policy_version))

    @classmethod
    def parse(
        cls, cutoff: str, mode: str = "observed", policy_version: str = STRICT
    ) -> "AsOfPolicy":
        return cls(parse_ts(cutoff), mode, policy_version)

    def as_dict(self) -> dict:
        return {
            "cutoff": fmt_ts(self.cutoff),
            "mode": self.mode,
            "policy_version": self.policy_version,
        }


def available_from(
    published_at: str | None,
    publication_date: str | None,
    policy: AsOfPolicy,
    zone: str = DATE_ZONE,
):
    """The earliest moment the policy lets this record count as available, or None if it never can."""
    if published_at:
        return parse_ts(published_at)
    if publication_date and policy.policy_version == DAY_END:
        day = date.fromisoformat(publication_date)
        return datetime.combine(
            day + timedelta(days=1), time(0, 0), tzinfo=ZoneInfo(zone)
        ).astimezone(timezone.utc)
    return None


def eligibility(record: dict, policy: AsOfPolicy) -> tuple[bool, tuple[str, ...]]:
    """(eligible, reasons it is not). `record` needs published_at, publication_date (optional), observed_at."""
    reasons = []
    start = available_from(record.get("published_at"), record.get("publication_date"), policy)
    if start is None:
        reasons.append(
            "publication_date_only_under_strict_policy"
            if record.get("publication_date")
            else "publication_time_unknown"
        )
    elif start > policy.cutoff:
        reasons.append("published_after_cutoff")
    if policy.mode == "observed":
        observed = record.get("observed_at")
        if not observed:
            reasons.append("observation_time_unknown")
        elif parse_ts(observed) > policy.cutoff:
            reasons.append("observed_after_cutoff")
    return not reasons, tuple(reasons)


def eligible(records, policy: AsOfPolicy):
    """The records eligible at the cutoff, in their given order. Apply this first; select, rank and evaluate afterwards."""
    return [r for r in records if eligibility(r, policy)[0]]
