"""The void rule: a flag on a session where the name is already moving does not count.

A name is *extended* at session u when its level on the reference chain (cumulative close / reference price, so a
corporate-action reset is not a move) is more than `threshold` x the median of its levels over the `window`
sessions before u, with at least `min_periods` of them present. Only data through the close of u is used.

Used by research/LEAD_LADDER_v1 (events and pools at each lead) and by `idxsig run --void-extended`: an extended
session is not evaluable, so it carries no flag and its name is not drawn as a control, for the rule and its
baselines alike. Off by default, so every earlier run reproduces unchanged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_THRESHOLD = 1.10
DEFAULT_WINDOW = 20
DEFAULT_MIN_PERIODS = 10


def levels(present: np.ndarray, close: np.ndarray, prev: np.ndarray) -> np.ndarray:
    """Reference-chain level per (name, session); NaN where the name is not present."""
    with np.errstate(divide="ignore", invalid="ignore"):
        logret = np.where(present & (prev > 0) & (close > 0), np.log(close / prev), 0.0)
    return np.where(present, np.exp(np.cumsum(logret, axis=1)), np.nan)


def prior_median(
    level: np.ndarray, window: int = DEFAULT_WINDOW, min_periods: int = DEFAULT_MIN_PERIODS
) -> np.ndarray:
    """Median of each name's levels over the `window` sessions strictly before each session."""
    med = pd.DataFrame(level.T).rolling(window, min_periods=min_periods).median().to_numpy().T
    out = np.full(level.shape, np.nan)
    out[:, 1:] = med[:, :-1]
    return out


def extended(
    level: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
    window: int = DEFAULT_WINDOW,
    min_periods: int = DEFAULT_MIN_PERIODS,
) -> np.ndarray:
    """True where the level is more than `threshold` x its prior-window median (False where either is unknown)."""
    med = prior_median(level, window, min_periods)
    with np.errstate(invalid="ignore"):
        return np.isfinite(level) & np.isfinite(med) & (level > threshold * med)


def extended_market(
    m,
    threshold: float = DEFAULT_THRESHOLD,
    window: int = DEFAULT_WINDOW,
    min_periods: int = DEFAULT_MIN_PERIODS,
) -> np.ndarray:
    """`extended` for an execution.Market."""
    return extended(levels(m.present, m.close, m.prev), threshold, window, min_periods)
