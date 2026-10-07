"""Matched random controls.

A same-session random draw controls for market timing but not for what kind of name a
rule picks. A rule that keeps selecting illiquid Rp100 names would look "different from
random" because of the exposure, not because of the signal. The matched baseline draws
each control from names that, on the signal's own session, sit in the same buckets as the
signalled name:

  price_band   close <= Rp200, <= Rp5,000, above (the IDX tick and limit bands)
  liquidity    quintile of the 20-session median traded value
  volatility   tercile of the 20-session standard deviation of daily log returns
  momentum     tercile of the 20-session cumulative log return

Every feature uses data up to and including that session only. When fewer than
MIN_POOL other names share all four buckets, the last bucket is dropped, then the next,
and the level used is counted in the report. The signalled name itself is never its own
control. Not available in this data: market cap and free float (no share counts after
2025-02), sector history, daily board membership.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

LOOKBACK = 20
MIN_POOL = 5
FEATURES = ("price_band", "liquidity", "volatility", "momentum")
LEVELS = (FEATURES, FEATURES[:3], FEATURES[:2], FEATURES[:1], ())
BUCKETS = {"liquidity": 5, "volatility": 3, "momentum": 3}


def _bucket(values: np.ndarray, n: int) -> np.ndarray:
    """Cross-sectional bucket per session (column); -1 where unknown."""
    pct = pd.DataFrame(values).rank(axis=0, pct=True).to_numpy()
    out = np.where(np.isfinite(pct), np.minimum(np.ceil(pct * n) - 1, n - 1), -1)
    return out.astype(np.int8)


def features(m) -> dict[str, np.ndarray]:
    close = np.where(m.present, m.close, np.nan)
    band = np.select([close <= 200, close <= 5000], [0, 1], 2).astype(np.int8)
    band = np.where(np.isfinite(close), band, -1).astype(np.int8)
    value = np.where(m.present, np.where(m.tradeable, np.nan_to_num(m.value), 0.0), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(m.tradeable & (m.prev > 0), np.log(m.close / m.prev), 0.0)
    logret = np.where(m.present, logret, np.nan)

    def rolling(arr, how):
        frame = pd.DataFrame(arr.T).rolling(LOOKBACK, min_periods=LOOKBACK)
        return getattr(frame, how)().to_numpy().T

    liquidity = np.where(m.present, rolling(value, "median"), np.nan)
    volatility = np.where(m.present, rolling(logret, "std"), np.nan)
    momentum = np.where(m.present, rolling(logret, "sum"), np.nan)
    return {
        "price_band": band,
        "liquidity": _bucket(liquidity, BUCKETS["liquidity"]),
        "volatility": _bucket(volatility, BUCKETS["volatility"]),
        "momentum": _bucket(momentum, BUCKETS["momentum"]),
    }


def _codes(feats: dict[str, np.ndarray]) -> list[np.ndarray]:
    codes = []
    for level in LEVELS:
        code = np.zeros(feats["price_band"].shape, dtype=np.int64)
        for i, name in enumerate(level):
            code += (feats[name].astype(np.int64) + 1) * (8 ** i)
        codes.append(code)
    return codes


def matched_draws(evaluable: np.ndarray, feats: dict[str, np.ndarray], a_tick: np.ndarray, a_sig: np.ndarray,
                  draws: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Returns (control tickers shaped (draws, attempts), match level used per attempt)."""
    codes = _codes(feats)
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


def level_names() -> list[str]:
    return ["+".join(level) if level else "same session only" for level in LEVELS]
