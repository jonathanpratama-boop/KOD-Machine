"""US_SPLIT_ARTIFACTS_v1 classifier: the first-match table of RULE.md, as pure functions."""

from __future__ import annotations

THRESHOLD = 0.30
CLASSES = (
    "UNKNOWN",
    "ARTIFACT_CONFIRMED",
    "ARTIFACT_PROVIDER_ONLY",
    "SPLIT_REAL_MOVE",
    "UNEXPLAINED_GAP",
    "CLEAN",
)


def window_events(events: list[dict], prev_day: str, signal_day: str) -> list[dict]:
    """Events effective strictly after prev_day and on or before signal_day (ISO dates)."""
    return [e for e in events if prev_day < e["effective_session"] <= signal_day]


def classify(
    window_splits: list[dict],
    adj_ret1: float | None,
    sec_statuses: list[str],
    fetch_ok: bool,
) -> str:
    if not fetch_ok or adj_ret1 is None:
        return "UNKNOWN"
    if window_splits:
        if adj_ret1 < THRESHOLD:
            if "VERIFIED" in sec_statuses:
                return "ARTIFACT_CONFIRMED"
            return "ARTIFACT_PROVIDER_ONLY"
        return "SPLIT_REAL_MOVE"
    if adj_ret1 < THRESHOLD:
        return "UNEXPLAINED_GAP"
    return "CLEAN"
