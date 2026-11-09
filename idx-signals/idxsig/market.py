"""IDX market rules used by the execution model: lots, ticks, fees, auto-rejection limits.

Auto-rejection (ARA = upper limit, ARB = lower limit) is set against the reference price
(the previous close, reset by IDX on corporate-action dates). Regular-board schedule:

  until 2020-03-09   ARA = ARB: 35% (<= Rp200), 25% (Rp200-5,000), 20% (> Rp5,000); floor Rp50
  2020-03-10         ARB 10% flat (COVID; ARA unchanged)
  2020-03-13         ARB 7% flat (Kep-00025/BEI/03-2020)
  2023-06-05         ARB 15% flat (normalisation stage I)
  2023-09-04         ARB = ARA again (stage II)
  2025-04-08         ARB 15% flat (tariff shock)
  2026-09-28         ARB 15% flat above Rp10; Rp1-10 band moves +/- Rp1; floor Rp1 (Kep-00136/BEI/09-2026)
  2026-10-19         ARB 7% flat above Rp10 (Kep-00157/BEI/10-2026)
  2026-10-20         as 2026-10-19, but the ARB is a nominal Rp1 for references Rp11-14 (Kep-00158/BEI/10-2026)
  2027-01-01         UNCONFIRMED, see below

The October 2026 decisions apply to the Main, Development and New Economy boards. The acceleration
and special monitoring boards keep 10% (+/- Rp1 at Rp1-10; from 2023-06-12, full call auction from
2024-03-25). The data has no daily board membership, so limits() models the regular boards for every
name (a name on a 10% board is over-locked by 7% falls, as the old 15% rule under-locked it), and a
one-price bar at or beyond the 10% limit is also treated as locked. See README for sources. The decree
texts were not read; the schedule rests on the IDX trading-mechanism page, IDX press releases as
reposted by brokers, and press reports. On 2026-10-19 the 7% formula gives ARB = reference for
references Rp11-14, but two bars (BTEK, TAXI) closed 25% lower that day, so the real limit that day
is unknown; nothing in the ledger depends on it.

After 2026-12-31 no rule is confirmed. Kep-00136 announced ARB = ARA again from 2027-01-01, but BEI
called that conditional, replaced the decree twice in October, and both replacements run to
2026-12-31 and are to be re-evaluated. limits() therefore carries the last confirmed rule forward
(ARB 7%, Rp1 at Rp11-14) and emits RulesUnconfirmedWarning; the carried-forward period has its own
REGIMES entry labelled UNCONFIRMED so that reports keyed by regime separate it, and unconfirmed(days)
gives the mask. Carrying 7% forward is the cautious choice for exits (a narrower lower limit locks more
closes than an eventual reversion would). It is a modelling convention, not a claim about the exchange.
When BEI confirms a rule, replace the last entry and move RULES_CONFIRMED_THROUGH.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date

import numpy as np

LOT_SIZE = 100  # shares per lot (since 2014-01-06); the panel starts 2019-07-29

# Price fraction (tick) by price band, unchanged over the panel period.
TICK_BANDS = ((200, 1), (500, 2), (2000, 5), (5000, 10))
TICK_TOP = 25

# Regular-board ARA bands: price <= bound -> pct.
BANDS = ((200, 0.35), (5000, 0.25), (float("inf"), 0.20))
SPECIAL_BOARD_PCT = 0.10


@dataclass(frozen=True)
class Fees:
    """Broker commission + levy + VAT (+ 0.1% final tax on sales). Typical retail online broker."""

    buy: float = 0.0015
    sell: float = 0.0025


@dataclass(frozen=True)
class Regime:
    start: date
    arb_flat: float | None  # None: ARB mirrors the ARA bands
    floor: int  # minimum price on the regular market
    small_abs: bool  # Rp1-10 band moves +/- Rp1
    label: str
    arb_abs_max: float = 10.0  # references up to this price have a nominal Rp1 ARB (Rp1-10; Rp1-14 from 2026-10-20)


REGIMES = (
    Regime(date(2019, 7, 29), None, 50, False, "symmetric 35/25/20 (in force at panel start)"),
    Regime(date(2020, 3, 10), 0.10, 50, False, "COVID ARB 10%"),
    Regime(date(2020, 3, 13), 0.07, 50, False, "COVID ARB 7%"),
    Regime(date(2023, 6, 5), 0.15, 50, False, "ARB 15% (stage I)"),
    Regime(date(2023, 9, 4), None, 50, False, "symmetric 35/25/20 (stage II)"),
    Regime(date(2025, 4, 8), 0.15, 50, False, "ARB 15% (April 2025)"),
    Regime(date(2026, 9, 28), 0.15, 1, True, "ARB 15%, floor Rp1"),
    Regime(date(2026, 10, 19), 0.07, 1, True, "ARB 7%, floor Rp1 (Kep-00157/BEI/10-2026)"),
    Regime(
        date(2026, 10, 20),
        0.07,
        1,
        True,
        "ARB 7%, Rp11-14 ARB Rp1 (Kep-00158/BEI/10-2026)",
        arb_abs_max=14.0,
    ),
    Regime(
        date(2027, 1, 1),
        0.07,
        1,
        True,
        "UNCONFIRMED: 2026-10-20 rule carried forward, BEI 2027 rule pending",
        arb_abs_max=14.0,
    ),
)
RULES_START = REGIMES[0].start
# Last date for which the schedule above is confirmed. Later dates carry the last rule forward.
RULES_CONFIRMED_THROUGH = date(2026, 12, 31)


class RulesUnconfirmedWarning(UserWarning):
    """A limit was computed for a date after RULES_CONFIRMED_THROUGH: a carried-forward assumption."""


def unconfirmed(days) -> np.ndarray:
    """True where `days` is after the last date for which the auto-rejection rules are confirmed."""
    return np.asarray(days, dtype="datetime64[D]") > np.datetime64(RULES_CONFIRMED_THROUGH, "D")


def regime_index(days: np.ndarray) -> np.ndarray:
    """Index into REGIMES for each datetime64[D] in `days`."""
    starts = np.array([np.datetime64(r.start, "D") for r in REGIMES])
    if (days < starts[0]).any():
        raise ValueError(f"market rules start {RULES_START}; earlier dates are not modelled")
    return np.searchsorted(starts, days, side="right") - 1


def tick_size(price: np.ndarray) -> np.ndarray:
    price = np.asarray(price, dtype=float)
    conds = [price < bound for bound, _ in TICK_BANDS]
    return np.select(conds, [tick for _, tick in TICK_BANDS], TICK_TOP).astype(float)


def floor_tick(x: np.ndarray) -> np.ndarray:
    t = tick_size(x)
    return np.floor(x / t + 1e-9) * t


def ceil_tick(x: np.ndarray) -> np.ndarray:
    t = tick_size(x)
    return np.ceil(x / t - 1e-9) * t


def band_pct(ref: np.ndarray) -> np.ndarray:
    ref = np.asarray(ref, dtype=float)
    return np.select([ref <= b for b, _ in BANDS[:-1]], [p for _, p in BANDS[:-1]], BANDS[-1][1])


def limits(ref: np.ndarray, days: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Regular-board (ARA price, ARB price) for reference prices `ref` on `days`.

    Dates after RULES_CONFIRMED_THROUGH carry the last confirmed rule forward and emit
    RulesUnconfirmedWarning (this includes calls for markets without price limits)."""
    ref = np.asarray(ref, dtype=float)
    days = np.asarray(days, dtype="datetime64[D]")
    if unconfirmed(days).any():
        warnings.warn(
            f"IDX auto-rejection rules after {RULES_CONFIRMED_THROUGH} are not confirmed: the "
            "2026-10-20 rule (ARB 7%, Rp1 at Rp11-14) is carried forward. Only IDX lower-limit locks "
            "(exits that roll) depend on it; see idxsig/market.py.",
            RulesUnconfirmedWarning,
            stacklevel=2,
        )
    idx = regime_index(days)
    up_pct = band_pct(ref)
    arb_flat = np.array([np.nan if r.arb_flat is None else r.arb_flat for r in REGIMES])[idx]
    down_pct = np.where(np.isnan(arb_flat), up_pct, arb_flat)
    floor = np.array([r.floor for r in REGIMES], dtype=float)[idx]
    small_abs = np.array([r.small_abs for r in REGIMES])[idx]
    arb_abs_max = np.array([r.arb_abs_max for r in REGIMES])[idx]
    ara = floor_tick(ref * (1 + up_pct))
    arb = np.maximum(ceil_tick(ref * (1 - down_pct)), floor)
    small = small_abs & (ref <= 10)  # ARA: the Rp1-10 band only
    small_arb = small_abs & (ref <= arb_abs_max)  # ARB: also Rp11-14 from 2026-10-20
    ara = np.where(small, ref + 1, ara)
    arb = np.where(small_arb, np.maximum(ref - 1, 1), arb)
    return ara, arb


def special_limits(ref: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Special monitoring board: 10% both ways, +/- Rp1 at Rp1-10, floor Rp1."""
    ref = np.asarray(ref, dtype=float)
    ara = floor_tick(ref * (1 + SPECIAL_BOARD_PCT))
    arb = np.maximum(ceil_tick(ref * (1 - SPECIAL_BOARD_PCT)), 1)
    small = ref <= 10
    return np.where(small, ref + 1, ara), np.where(small, np.maximum(ref - 1, 1), arb)


def regime_labels() -> list[dict]:
    return [
        {
            "start": r.start.isoformat(),
            "arb_flat": r.arb_flat,
            "floor": r.floor,
            "small_abs": r.small_abs,
            "label": r.label,
        }
        for r in REGIMES
    ]
