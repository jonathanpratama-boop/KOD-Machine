"""US_BREAKOUT_v1: the prior-60-session closing-high breakout, as signal code and a one-trade runner.

Specified in research/US_BREAKOUT_v1/PROTOCOL.md (frozen before any result). Everything here
works on bars through the decision session only; `tests/test_breakout.py` checks that signals at
session s do not change when later sessions are removed.

The trading itself is EXEC-US-v2.1 (`contract.py`): `run_trade` gives each trade a fresh $10,000
account and a one-name market slice, so trades are independent and cash never competes. The
account-level run (shared cash, priority) is the contract's own `replay`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .contract import SPEC, Account, ContractSpec
from .execution import Market

LOOKBACK = 60
COOLDOWN = 5
MIN_PRICE = 5.0
MIN_ADV_USD = 1_000_000.0
PRICE_EDGES = (10.0, 25.0, 100.0)  # $5-10, 10-25, 25-100, 100+
ADV_EDGES = (2e6, 5e6, 20e6, 100e6)  # <2M, 2-5M, 5-20M, 20-100M, 100M+


def _rolling(a: np.ndarray, fn, window: int, min_periods: int) -> np.ndarray:
    return getattr(pd.DataFrame(a.T).rolling(window, min_periods=min_periods), fn)().to_numpy().T


def levels_and_signals(m: Market):
    """(level, raw signal, history ok). level[n, s] = highest adjusted close of sessions s-60..s-1.
    raw signal: close[s] > level, the name has 60 listed-and-traded prior sessions, and traded on s.
    Everything at column s uses columns <= s only."""
    traded = m.present & (np.nan_to_num(m.volume) > 0) & np.isfinite(m.close)
    close = np.where(m.present, m.close, np.nan)
    level = np.roll(_rolling(close, "max", LOOKBACK, LOOKBACK), 1, axis=1)
    level[:, 0] = np.nan
    prior_traded = np.roll(_rolling(traded.astype(float), "sum", LOOKBACK, LOOKBACK), 1, axis=1)
    prior_traded[:, 0] = np.nan
    history = prior_traded == LOOKBACK
    with np.errstate(invalid="ignore"):
        raw = history & traded & (np.nan_to_num(m.close) > level)
    return level, raw, history


def cooldown_mask(raw: np.ndarray) -> np.ndarray:
    """True where a raw signal is within COOLDOWN sessions after an earlier raw signal of the same name."""
    prior = np.zeros(raw.shape, dtype=bool)
    for lag in range(1, COOLDOWN + 1):
        prior[:, lag:] |= raw[:, :-lag]
    return raw & prior


def adv_usd(m: Market) -> np.ndarray:
    """Median traded value (USD) of the 20 sessions through each session, among listed sessions."""
    value = np.where(m.present, np.nan_to_num(m.value), np.nan)
    return _rolling(value, "median", 20, 1)


def cells(close_traded: np.ndarray, adv: np.ndarray) -> np.ndarray:
    """Matching cell id: price bucket x ADV bucket (-1 if below the eligibility floor)."""
    p = np.searchsorted(np.array(PRICE_EDGES), close_traded, side="right")
    a = np.searchsorted(np.array(ADV_EDGES), adv, side="right")
    return np.where((close_traded >= MIN_PRICE) & (adv >= MIN_ADV_USD), p * 5 + a, -1)


def submarket(m: Market, n: int, lo: int, hi: int) -> Market:
    arrays = {f: getattr(m, f)[[n], lo:hi] for f in Market.FIELDS}
    return Market(m.tickers[[n]], m.dates[lo:hi], **arrays, unit_factor=m.unit_factor[[n], lo:hi])


def run_trade(
    m: Market,
    n: int,
    s: int,
    invalidation: float,
    spec: ContractSpec = SPEC,
    lead: int = 20,
    tail: int = 14,
) -> dict:
    """One decision after the close of s in a fresh account, one-name market. Returns the trade's
    record: the closed order (rejected, unfilled or exited) or, if the data ends first, status OPEN."""
    lo, hi = max(0, s - lead), min(m.shape[1], s + tail)
    sub, rel = submarket(m, n, lo, hi), s - lo
    acc = Account(spec)
    acc.step(sub, rel, [(0, invalidation)])
    for k in range(rel + 1, sub.shape[1]):
        if not acc.state["orders"] and not acc.state["positions"]:
            break
        acc.step(sub, k, [])
    st = acc.state
    if st["closed"]:
        return st["closed"][-1]
    return {"outcome": "OPEN", "plan": None}
