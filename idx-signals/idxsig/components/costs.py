"""Named simulation costs with an explicit price basis.

MID prices need half of the declared spread on each leg. EXECUTABLE prices
already contain their bid/ask side, so adding spread again is rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


def decimal(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(f"{name}: finite number required")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name}: finite number required") from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError(f"{name}: invalid number")
    return result


@dataclass(frozen=True)
class CostModel:
    """A reproducible assumption set, not a verified venue fee quote."""

    id: str
    fee_rate: Decimal
    spread_bps: Decimal
    slippage_bps: Decimal
    price_basis: str

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("a named cost profile is required")
        for key in ("fee_rate", "spread_bps", "slippage_bps"):
            object.__setattr__(self, key, decimal(getattr(self, key), key))
        if self.fee_rate >= 1:
            raise ValueError("fee_rate must be below one")
        if not isinstance(self.price_basis, str) or self.price_basis not in {"MID", "EXECUTABLE"}:
            raise ValueError("price_basis must be MID or EXECUTABLE")
        if self.price_basis == "EXECUTABLE" and self.spread_bps != 0:
            raise ValueError("executable bid/ask prices already include spread")
        if self.impact >= 1:
            raise ValueError("spread and slippage must leave a positive sell price")

    @classmethod
    def from_dict(cls, value):
        fields = {"id", "fee_rate", "spread_bps", "slippage_bps", "price_basis"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("explicit named cost fields required")
        return cls(**value)

    @property
    def impact(self):
        return (self.spread_bps / 2 + self.slippage_bps) / Decimal(10000)

    def prices(self, entry, exit):
        """Convert reference prices to assumed buy and sell execution prices."""
        entry = decimal(entry, "entry", positive=True)
        exit = decimal(exit, "exit", positive=True)
        return entry * (1 + self.impact), exit * (1 - self.impact)

    def round_trip_return(self, entry, exit):
        """Net return on starting cash, charging the declared fee on each leg."""
        buy, sell = self.prices(entry, exit)
        return sell * (1 - self.fee_rate) / (buy * (1 + self.fee_rate)) - 1

    def as_dict(self):
        return {
            "id": self.id,
            "fee_rate": str(self.fee_rate),
            "spread_bps": str(self.spread_bps),
            "slippage_bps": str(self.slippage_bps),
            "price_basis": self.price_basis,
        }
