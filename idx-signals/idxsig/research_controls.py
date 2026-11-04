"""Prospective, opt-in control eligibility without future-trigger exclusions.

Historical controls v1-v4 and frozen Hermes runners are unchanged. Callers supply
an independently retained as-of eligible universe and trigger observations. This
helper does not prove universe completeness or create an outcome-based holdout.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any


def _timestamp(value: str | datetime) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be ISO 8601 with an offset") from exc
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone aware")
    return value.astimezone(timezone.utc)


def _symbol(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("symbol must be a nonempty, unpadded string")
    return value


def past_only_control_pool(
    eligible_symbols: Iterable[str],
    observed_triggers: Iterable[Mapping[str, Any]],
    *,
    at: str | datetime,
    lookback: timedelta,
) -> tuple[str, ...]:
    """Exclude only triggers observed in ``(at - lookback, at]``.

    ``observed_at`` means the timestamp when the trigger became available to the
    collector. It must not be backdated to a price peak or an earlier source event.
    Future triggers and outcome fields never affect the returned pool. An empty
    pool stays empty; callers must record unavailable controls rather than select
    the treated instrument as its own control. A selection protocol must separately
    exclude the treated symbol and retain its universe/evidence identifiers.
    """
    cutoff = _timestamp(at)
    if not isinstance(lookback, timedelta) or lookback <= timedelta(0):
        raise ValueError("lookback must be a positive timedelta")
    start = cutoff - lookback
    if isinstance(eligible_symbols, (str, bytes)):
        raise ValueError("eligible_symbols must be an iterable of distinct symbols")
    universe = [_symbol(value) for value in eligible_symbols]
    if len(set(universe)) != len(universe):
        raise ValueError("eligible symbols must be distinct")
    excluded = set()
    for record in observed_triggers:
        if not isinstance(record, Mapping) or not {"symbol", "observed_at"} <= record.keys():
            raise ValueError("trigger requires symbol and observed_at")
        symbol = _symbol(record["symbol"])
        observed_at = _timestamp(record["observed_at"])
        if start < observed_at <= cutoff:
            excluded.add(symbol)
    return tuple(sorted(set(universe) - excluded))
