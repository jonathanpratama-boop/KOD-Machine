"""Explicit research identity mappings; never infer market availability.

Contract multipliers convert quoted prices/quantities, not funding rates. A
mapping does not prove a perpetual was listed at a historical decision time.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ContractMapping:
    futures_symbol: str
    spot_symbol: str
    base_units_per_contract: int
    effective_from: str
    source_url: str
    mapping_version: str = "BINANCE_CONTRACT_MAP_V1"


CONTRACT_MAPPINGS = (
    ContractMapping(
        futures_symbol="1000SHIBUSDT",
        spot_symbol="SHIBUSDT",
        base_units_per_contract=1000,
        effective_from="2021-05-10T13:00:00Z",
        source_url="https://www.binance.com/en/support/announcement/detail/fa934b93fea6494fb7361d45ca7cc98a",
    ),
)


def resolve_futures_symbol(symbol: str, *, at: str | None = None) -> dict:
    """Resolve only sourced exceptions. Unknown is never 'no perpetual exists'."""
    if not isinstance(symbol, str) or not symbol or not symbol.isalnum():
        raise ValueError("explicit alphanumeric futures symbol required")
    moment = None
    if at is not None:
        moment = datetime.fromisoformat(at.replace("Z", "+00:00"))
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("mapping cutoff requires timezone")
        moment = moment.astimezone(timezone.utc)
    match = next((item for item in CONTRACT_MAPPINGS if item.futures_symbol == symbol), None)
    if match is None:
        return {
            "status": "UNMAPPED",
            "futures_symbol": symbol,
            "spot_symbol": None,
            "base_units_per_contract": None,
            "availability": "UNKNOWN",
        }
    if moment is not None and moment < datetime.fromisoformat(
        match.effective_from.replace("Z", "+00:00")
    ):
        return {
            "status": "NOT_YET_EFFECTIVE",
            "futures_symbol": symbol,
            "spot_symbol": None,
            "base_units_per_contract": None,
            "availability": "UNKNOWN",
        }
    return {
        **asdict(match),
        "status": "MAPPED",
        "availability": "REQUIRES_AS_OF_EXCHANGE_METADATA",
        "funding_rate_multiplier": 1,
    }
