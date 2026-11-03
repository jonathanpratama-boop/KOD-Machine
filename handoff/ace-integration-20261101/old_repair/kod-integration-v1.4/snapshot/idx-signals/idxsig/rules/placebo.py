"""PLACEBO: a deterministic coin flip. Harness self-check, not a trading rule.

It reads no prices, so against date-matched random entries it should show no lift beyond
sampling noise. If it ever does, the harness (not the market) is biased.
"""

from __future__ import annotations

import sys
import zlib

import numpy as np

RULE_ID = "PLACEBO_COINFLIP"
VERSION = "v1"
HOLDING_DAYS = 5
PROBABILITY = 0.01
RULE_TEXT = (
    "Signal on session d for ticker t when splitmix64(crc32(t) * 2^20 + days_since_epoch(d)) / 2^64 < 0.01, "
    "for every ticker that traded on session d. Hold 5 sessions. No price input."
)


def _splitmix64(x: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore"):
        z = x + np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return z ^ (z >> np.uint64(31))


def compute(market) -> np.ndarray:
    t = np.array([zlib.crc32(s.encode()) for s in market.tickers], dtype=np.uint64)[:, None]
    d = market.dates.astype("datetime64[D]").astype(np.int64).astype(np.uint64)[None, :]
    with np.errstate(over="ignore"):
        u = _splitmix64(t * np.uint64(1 << 20) + d).astype(np.float64) / 2.0**64
    out = (u < PROBABILITY).astype(float)
    return np.where(market.tradeable, out, np.nan)


def rule():
    from . import Rule

    return Rule(RULE_ID, VERSION, RULE_TEXT, HOLDING_DAYS, compute, sys.modules[__name__], kind="PLACEBO")
