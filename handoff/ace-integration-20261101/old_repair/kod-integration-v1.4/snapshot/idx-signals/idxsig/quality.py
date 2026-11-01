"""Data-quality tiers. Every run reports how many of its sessions fall in each tier.

TIER_1  mirror first snapshot .. source boundary (2021-01-22 .. 2025-02-21 for the pinned
        mirror). Exchange data (IDX daily summary). Survivorship-complete: a name that
        delisted in this span is present to its last session. Reference prices are IDX's
        own; daily share counts let the corporate-action registry corroborate splits.
        The default backtest window.
TIER_2  panel start .. day before the first snapshot (2019-07-29 .. 2021-01-21). Same
        exchange data, but survivor-biased: names that delisted before 2021-01-22 were
        never captured.
TIER_3  after the source boundary (2025-02-24 ..). Yahoo daily bars. Survivor-only
        (names delisted later stop at the boundary), reference prices rebuilt from
        Yahoo's split events (single-source corporate actions, never share-scaled), no
        share counts, no trade frequency.
"""

from __future__ import annotations

from datetime import date, timedelta

from .sources.idx_mirror import FIRST_SNAPSHOT

KNOWN_LIMITATIONS = (
    "TIER_2 sessions (before 2021-01-22) miss names that delisted before then: survivor-biased.",
    "TIER_3 sessions (after the mirror ends) are survivor-only Yahoo data; corporate actions there are "
    "single-source and trades held across them are excluded.",
    "Prices are daily closes; there is no intraday path, so a stop or limit inside the session is not modelled.",
    "Cash dividends are not added back: returns are price returns.",
    "Sector, board membership and free float are not available point-in-time; controls do not match on them.",
    "Trades held across a reference reset that is not a verified split, reverse split or stock dividend are "
    "excluded from scoring (rule and baselines alike), so names with rights issues are under-represented.",
    "Suspensions longer than the data are exited at the last traded close (EXIT_DATA_END), not marked to zero, "
    "unless data_end_exit='zero'.",
)


def _day(s: str) -> date:
    return date.fromisoformat(s)


def tiers(first_session: str, boundary: str, last_session: str) -> list[dict]:
    snap = _day(FIRST_SNAPSHOT)
    out = []
    if _day(first_session) < snap:
        out.append(
            {
                "tier": "TIER_2",
                "from": first_session,
                "to": (snap - timedelta(days=1)).isoformat(),
                "source": "idx_mirror",
                "survivorship": "survivor-biased (pre-snapshot delistings absent)",
                "corporate_actions": "exchange reference + share counts",
                "share_counts": True,
            }
        )
    out.append(
        {
            "tier": "TIER_1",
            "from": max(first_session, FIRST_SNAPSHOT),
            "to": boundary,
            "source": "idx_mirror",
            "survivorship": "complete",
            "corporate_actions": "exchange reference + share counts + Yahoo",
            "share_counts": True,
        }
    )
    if _day(last_session) > _day(boundary):
        out.append(
            {
                "tier": "TIER_3",
                "from": (_day(boundary) + timedelta(days=1)).isoformat(),
                "to": last_session,
                "source": "yahoo",
                "survivorship": "survivor-only",
                "corporate_actions": "Yahoo split events only (single source)",
                "share_counts": False,
            }
        )
    return sorted(out, key=lambda t: t["from"])


def tier_of(day: str, boundary: str) -> str:
    if day > boundary:
        return "TIER_3"
    return "TIER_1" if day >= FIRST_SNAPSHOT else "TIER_2"


def window_composition(dates, boundary: str) -> dict:
    """Sessions per tier for a run window (dates: datetime64[D] array)."""
    counts: dict[str, int] = {}
    for d in dates.astype(str):
        t = tier_of(d, boundary)
        counts[t] = counts.get(t, 0) + 1
    worst = max(counts) if counts else None
    return {"sessions_by_tier": dict(sorted(counts.items())), "lowest_tier": worst}


def composition_from(dates, tiers: list[dict]) -> dict:
    """Sessions per tier for a non-IDX panel, from the tiers its manifest declares."""
    counts: dict[str, int] = {}
    for d in dates.astype(str):
        tier = next((t["tier"] for t in tiers if t["from"] <= d <= t["to"]), "UNTIERED")
        counts[tier] = counts.get(tier, 0) + 1
    return {
        "sessions_by_tier": dict(sorted(counts.items())),
        "lowest_tier": max(counts) if counts else None,
    }
