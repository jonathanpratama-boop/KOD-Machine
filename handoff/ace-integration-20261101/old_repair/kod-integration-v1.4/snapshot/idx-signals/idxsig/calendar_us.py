"""NYSE regular sessions: weekdays minus the exchange's full-day holidays, opening 09:30 New York time.

The opening time comes from the America/New_York time zone, so it is 13:30 UTC in summer and 14:30 UTC
in winter. Holidays follow the NYSE's standing rules (New Year's Day, Martin Luther King Jr. Day,
Washington's Birthday, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day,
Thanksgiving, Christmas, with the weekend observance rules). One-off closures, such as a national day
of mourning, are not modelled: a missing session in the bars still wins. Early closes do not move the open.

Older records keep the weekday-only rule and fixed 13:30 UTC cutoff they were sealed under
(paper._next_session, speculation.entry_cutoff); new versioned plans use this module.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from functools import cache
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
OPEN = time(9, 30)


def _easter(year: int) -> date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    """Saturday holidays are observed on Friday, Sunday holidays on Monday."""
    return (
        d - timedelta(days=1)
        if d.weekday() == 5
        else d + timedelta(days=1)
        if d.weekday() == 6
        else d
    )


@cache
def holidays(year: int) -> frozenset[date]:
    new_year = date(year, 1, 1)
    days = {
        _nth_weekday(year, 1, 0, 3),  # Martin Luther King Jr. Day
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday
        _easter(year) - timedelta(days=2),  # Good Friday
        _last_weekday(year, 5, 0),  # Memorial Day
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observed(date(year, 12, 25)),
    }
    if year >= 2022:
        days.add(_observed(date(year, 6, 19)))  # Juneteenth
    # the NYSE does not close on Friday 31 December for a Saturday New Year
    if new_year.weekday() != 5:
        days.add(_observed(new_year))
    return frozenset(days)


def is_session(d: date) -> bool:
    return d.weekday() < 5 and d not in holidays(d.year)


def next_session(d: date | str) -> date:
    d = date.fromisoformat(d) if isinstance(d, str) else d
    d += timedelta(days=1)
    while not is_session(d):
        d += timedelta(days=1)
    return d


def open_utc(d: date | str) -> datetime:
    """The regular opening time of session d, in UTC."""
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return datetime.combine(d, OPEN, NEW_YORK).astimezone(timezone.utc)
