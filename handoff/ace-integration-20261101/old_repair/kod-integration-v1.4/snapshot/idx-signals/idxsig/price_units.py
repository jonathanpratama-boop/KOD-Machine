"""Price-unit conversion v1, opt-in only; does not modify existing panel/strategy.

Precondition: prices are split-only adjusted to adjustment_reference, with a
separately verified complete split schedule for that reference. Not valid for
unidentified adjclose/total-return data, rights, mergers or spinoffs. A true
coverage flag records an upstream audit, not evidence established here.
"""

from datetime import date
import math

VERSION = "price-units-v1"


def _positive(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError("Finite positive number required")
    return float(value)


def _session(value):
    if not isinstance(value, str):
        raise ValueError("ISO session date required")
    try:
        d = date.fromisoformat(value)
    except ValueError as e:
        raise ValueError("Invalid session date") from e
    if d.isoformat() != value:
        raise ValueError("Canonical ISO session date required")
    return d


def split_conversion_factor(session, actions, adjustment_reference, *, coverage_complete=False):
    """Multiplier converting reference-adjusted prices into session quote units."""
    if coverage_complete is not True:
        raise ValueError("Unverified action coverage")
    day = _session(session)
    reference = _session(adjustment_reference)
    if day > reference:
        raise ValueError("Session beyond adjustment reference")
    factor = 1.0
    seen = set()
    for action in actions:
        try:
            effective = _session(action["effective_session"])
            numerator = _positive(action["new_shares"])
            denominator = _positive(action["old_shares"])
        except (KeyError, TypeError) as e:
            raise ValueError("Malformed split record") from e
        if effective in seen:
            raise ValueError("Duplicate/ambiguous same-session action")
        seen.add(effective)
        if effective > reference:
            raise ValueError("Action beyond adjustment reference")
        if effective > day:
            factor *= numerator / denominator
    return _positive(factor)


def as_traded(adjusted_price, session, actions, adjustment_reference, *, coverage_complete=False):
    return _positive(adjusted_price) * split_conversion_factor(
        session, actions, adjustment_reference, coverage_complete=coverage_complete
    )


def volume_as_traded(volume, price_factor, convention):
    if (
        isinstance(volume, bool)
        or not isinstance(volume, (int, float))
        or not math.isfinite(volume)
        or volume < 0
    ):
        raise ValueError("Finite nonnegative volume required")
    factor = _positive(price_factor)
    if convention == "AS_TRADED_SHARES":
        return float(volume)
    if convention == "SPLIT_ADJUSTED_SHARES":
        return float(volume) / factor
    raise ValueError("Unknown source volume adjustment convention")
