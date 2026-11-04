"""Strategy/mandate registry. Availability of code does not promote a strategy."""

from __future__ import annotations

TREND_ID = "TREND_SHARED_PAPER_V2"


def registry():
    return [
        {
            "id": TREND_ID,
            "status": "PAPER_CANDIDATE",
            "asset_class": "CRYPTO_SPOT",
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "signal": "SMA10 > SMA40",
            "sizing": "per-coin inverse volatility, shared-cash normalization",
            "live_enabled": False,
            "minimum_forward_days": 90,
            "approval": "Recorded Nov 1 paper mandate; this runtime is a new execution profile/cohort",
            "risk": "persistent 25% drawdown or negative trailing 90-return mean; neither is a hard loss cap",
            "evidence": "Shared-account historical replay does not establish prospective outperformance",
        },
        {
            "id": "SELECTIVE_REPRICING",
            "status": "RESEARCH_ONLY",
            "horizon_sessions": "1-5, exact entry-count convention required",
            "planned_price_stop_max": "0.05",
            "live_enabled": False,
            "entry_enabled": False,
            "reason": "No strategy promotion follows from a discovery rank or analyst narrative",
        },
        {
            "id": "MARKET_CONTEXT",
            "status": "DESCRIPTIVE_ONLY",
            "entry_enabled": False,
            "reason": "No validated next-stop route; isolation does not establish manipulation",
        },
    ]


def require_paper_profile(profile):
    if profile.get("live_enabled", False) or profile.get("mode", "paper") != "paper":
        raise ValueError("this release supports paper operation only")
    if profile.get("strategy_id", TREND_ID) != TREND_ID:
        raise ValueError("strategy is not admitted to this paper-account adapter")
    if profile.get("evidence_type") not in ("synthetic", "public_market"):
        raise ValueError("explicit synthetic or public_market profile required")
    return profile
