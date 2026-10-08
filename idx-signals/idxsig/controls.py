"""Matched random controls.

A same-session random draw controls for market timing but not for what kind of name a
rule picks. A rule that keeps selecting illiquid Rp100 names would look "different from
random" because of the exposure, not because of the signal. The matched baseline draws
each control from names that, on the signal's own session, sit in the same buckets as the
signalled name. The same-session baseline is kept alongside it.

Every feature at session s is computed from data at or before s only (rolling windows end
at s, cross-sectional ranks use only names present at s), and the rule never sees them.
Features, in matching priority (controls v2):

  price_band   close <= Rp200, <= Rp5,000, above (the IDX tick and limit bands)
  liquidity    quintile of the 20-session median traded value (an ADV proxy)
  market_cap   quintile of close x IDX listed shares (mirror era only; unknown in TIER_3)
  volatility   tercile of the 20-session standard deviation of daily log returns
  momentum     tercile of the 20-session cumulative log return (the preceding return)
  drawdown     tercile of close / 60-session high close - 1
  listing_age  sessions since the name's first session in the panel: < 60, < 250, older or
               present since the panel's first session (age censored there)

Unknown values (too little history, no share counts) form their own bucket. When fewer than
MIN_POOL other names share every bucket, the lowest-priority feature is dropped, then the
next; the level used is counted in the report, with per-feature coverage. Controls v1 (the
first four features without market_cap) is kept to reproduce older runs.

Not matched on, because no point-in-time history exists in this data (NOT invented):
  sector       only a 2025-02 snapshot of IDX-IC sectors; using it would apply today's
               classification to the past and silently drop names delisted before it
  board        listing board is likewise a 2025-02 snapshot
  free_float   IDX `tradeble_shares` equals listed shares for most names, including
               ones with a controlling holder, so it does not measure free float
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

LOOKBACK = 20
DRAWDOWN_LOOKBACK = 60
MIN_POOL = 5


@dataclass(frozen=True)
class Feature:
    name: str
    buckets: int
    description: str
    availability: str


FEATURES = {
    "price_band": Feature("price_band", 3, "close <= Rp200 / <= Rp5,000 / above", "every tier"),
    "liquidity": Feature("liquidity", 5, "quintile of 20-session median traded value", "every tier"),
    "market_cap": Feature("market_cap", 5, "quintile of close x IDX listed shares", "TIER_1, TIER_2 (no share "
                          "counts after the mirror ends)"),
    "volatility": Feature("volatility", 3, "tercile of 20-session std of daily log returns", "every tier"),
    "momentum": Feature("momentum", 3, "tercile of 20-session cumulative log return", "every tier"),
    "drawdown": Feature("drawdown", 3, "tercile of close / 60-session high close - 1", "every tier"),
    "listing_age": Feature("listing_age", 3, "sessions since first panel session: <60 / <250 / older or "
                           "censored at the panel start", "every tier"),
}
UNAVAILABLE = {
    "sector": "only a 2025-02 snapshot (List Emiten/Sectors); not point-in-time, so not used",
    "board": "listing board known only as of the 2025-02 snapshot; not point-in-time, so not used",
    "free_float": "IDX tradeble_shares equals listed_shares for most names; it is not free float, so not used",
}
VERSIONS = {
    "v1": ("price_band", "liquidity", "volatility", "momentum"),
    "v2": ("price_band", "liquidity", "market_cap", "volatility", "momentum", "drawdown", "listing_age"),
}


def levels(version: str = "v2") -> tuple[tuple[str, ...], ...]:
    names = VERSIONS[version]
    return tuple(names[:i] for i in range(len(names), -1, -1))


def _bucket(values: np.ndarray, n: int) -> np.ndarray:
    """Cross-sectional bucket per session (column); -1 where unknown."""
    pct = pd.DataFrame(values).rank(axis=0, pct=True).to_numpy()
    out = np.where(np.isfinite(pct), np.minimum(np.ceil(pct * n) - 1, n - 1), -1)
    return out.astype(np.int8)


def _rolling(arr: np.ndarray, how: str, window: int) -> np.ndarray:
    frame = pd.DataFrame(arr.T).rolling(window, min_periods=window)
    return getattr(frame, how)().to_numpy().T


def features(m, version: str = "v2", band_edges: tuple = (200, 5000), as_traded: bool = False) -> dict[str, np.ndarray]:
    """band_edges: upper edges of the price bands (IDX default: Rp200, Rp5,000; see profiles.py).
    as_traded: band on the price as traded that session (Market.unit_factor), not the price
    rescaled by later splits. Return-based features and traded value are unit-free."""
    close = np.where(m.present, m.close, np.nan)
    level = close * m.unit_factor if as_traded else close
    band = np.searchsorted(np.array(band_edges, dtype=float), np.nan_to_num(level, nan=0.0), side="left")
    band = np.where(np.isfinite(close), band, -1).astype(np.int8)
    value = np.where(m.present, np.where(m.tradeable, np.nan_to_num(m.value), 0.0), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(m.tradeable & (m.prev > 0), np.log(m.close / m.prev), 0.0)
    logret = np.where(m.present, logret, np.nan)
    out = {
        "price_band": band,
        "liquidity": _bucket(np.where(m.present, _rolling(value, "median", LOOKBACK), np.nan), 5),
        "volatility": _bucket(np.where(m.present, _rolling(logret, "std", LOOKBACK), np.nan), 3),
        "momentum": _bucket(np.where(m.present, _rolling(logret, "sum", LOOKBACK), np.nan), 3),
    }
    if version == "v1":
        return out
    # close relative to its own 60-session high, on a share-count-free basis: the reference
    # chain (close / prev) is what IDX uses, so a split does not look like a crash.
    level = np.exp(np.nancumsum(np.nan_to_num(logret), axis=1))
    level = np.where(m.present, level, np.nan)
    high = _rolling(level, "max", DRAWDOWN_LOOKBACK)
    with np.errstate(divide="ignore", invalid="ignore"):
        drawdown = np.where(m.present, level / high - 1, np.nan)
        mcap = np.where(m.present & np.isfinite(m.listed_shares), close * m.listed_shares, np.nan)
    n_sessions = m.shape[1]
    first = np.where(m.present.any(axis=1), m.present.argmax(axis=1), n_sessions)
    age = np.arange(n_sessions)[None, :] - first[:, None]
    censored = (first == 0)[:, None]  # present since the panel's first session: true age unknown
    age_bucket = np.select([censored | (age >= 250), age >= 60], [2, 1], 0).astype(np.int8)
    out.update({
        "market_cap": _bucket(mcap, 5),
        "drawdown": _bucket(drawdown, 3),
        "listing_age": np.where(m.present, age_bucket, -1).astype(np.int8),
    })
    return out


def _codes(feats: dict[str, np.ndarray], version: str) -> list[np.ndarray]:
    codes = []
    for level in levels(version):
        code = np.zeros(feats["price_band"].shape, dtype=np.int64)
        for i, name in enumerate(level):
            code += (feats[name].astype(np.int64) + 1) * (8 ** i)
        codes.append(code)
    return codes


def matched_draws(evaluable: np.ndarray, feats: dict[str, np.ndarray], a_tick: np.ndarray, a_sig: np.ndarray,
                  draws: int, rng: np.random.Generator, version: str = "v2") -> tuple[np.ndarray, np.ndarray]:
    """Returns (control tickers shaped (draws, attempts), match level used per attempt)."""
    codes = _codes(feats, version)
    out = np.empty((draws, len(a_sig)), dtype=np.int64)
    level_used = np.empty(len(a_sig), dtype=np.int8)
    for s in np.unique(a_sig):
        cand = np.flatnonzero(evaluable[:, s])
        for col in np.flatnonzero(a_sig == s):
            n = a_tick[col]
            others = cand[cand != n]
            pool = others
            for level, code in enumerate(codes):
                pool = others[code[others, s] == code[n, s]]
                if len(pool) >= MIN_POOL or level == len(codes) - 1:
                    level_used[col] = level
                    break
            if not len(pool):
                pool = cand  # a session with a single evaluable name
            out[:, col] = rng.choice(pool, size=draws, replace=True)
    return out, level_used


def level_names(version: str = "v2") -> list[str]:
    return ["+".join(level) if level else "same session only" for level in levels(version)]


def coverage(feats: dict[str, np.ndarray], a_tick: np.ndarray, a_sig: np.ndarray, level_used: np.ndarray,
             version: str = "v2", band_names: tuple | None = None) -> dict:
    """How often each feature was known for the signalled name, and how often it was matched on.
    band_names: the market's price bands (profiles.py), which replace the IDX wording in the report."""
    names = VERSIONS[version]
    lv = levels(version)
    out = {}
    for i, name in enumerate(names):
        known = feats[name][a_tick, a_sig] >= 0 if len(a_tick) else np.array([], dtype=bool)
        matched = np.array([name in lv[k] for k in level_used], dtype=bool) if len(level_used) else known
        f = FEATURES[name]
        description = ("close in " + " / ".join(band_names)) if (name == "price_band" and band_names) else f.description
        out[name] = {"description": description, "availability": f.availability, "priority": i + 1,
                     "known_share": float(known.mean()) if len(known) else None,
                     "matched_share": float(matched.mean()) if len(matched) else None}
    full = float((level_used == 0).mean()) if len(level_used) else None
    return {"version": version, "features": out, "full_match_share": full, "min_pool": MIN_POOL,
            "not_available": UNAVAILABLE}
