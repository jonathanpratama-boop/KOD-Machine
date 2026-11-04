"""Exact Binance epoch normalization at the row boundary.

The public spot archive switched from milliseconds to microseconds in 2025.
A file or concatenated panel may contain both. Never choose one unit from the
maximum of a whole column. This module reads timestamps, not market outcomes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable

BINANCE_TIME_SOURCE = "https://github.com/binance/binance-public-data#spot"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
MIN_EPOCH_MS = 946684800000  # 2000-01-01; rejects seconds mistakenly passed as ms.
MAX_EPOCH_MS = 4102444800000  # 2100-01-01, exclusive.


def binance_time_unit(value: object) -> str:
    """Return ms/us for one integer epoch value; reject ambiguous bad inputs."""
    if isinstance(value, bool) or value is None:
        raise ValueError("Binance timestamp must be an integer millisecond or microsecond epoch")
    try:
        epoch = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid Binance epoch timestamp") from exc
    if not epoch.is_finite() or epoch != epoch.to_integral_value():
        raise ValueError("Binance timestamp must be a finite integer")
    if MIN_EPOCH_MS <= epoch < MAX_EPOCH_MS:
        return "ms"
    if MIN_EPOCH_MS * 1000 <= epoch < MAX_EPOCH_MS * 1000:
        return "us"
    raise ValueError("Binance timestamp is outside the supported 2000–2100 ms/us range")


def binance_datetime(value: object) -> datetime:
    """Normalize exactly, including the final microsecond of an archive bar."""
    unit = binance_time_unit(value)
    micros = int(Decimal(str(value))) * (1000 if unit == "ms" else 1)
    return EPOCH + timedelta(microseconds=micros)


def binance_datetimes(values: Iterable[object]):
    """Return a UTC pandas Series, preserving an input Series' index and name."""
    import pandas as pd

    converted = [binance_datetime(value) for value in values]
    return pd.Series(
        converted,
        index=values.index if isinstance(values, pd.Series) else None,
        name=values.name if isinstance(values, pd.Series) else None,
        dtype="datetime64[ns, UTC]",
    )


def binance_bar_end(value: object) -> datetime:
    """Exclusive bar end from Binance's inclusive close timestamp."""
    return binance_datetime(value) + timedelta(
        microseconds=1000 if binance_time_unit(value) == "ms" else 1
    )
