"""Experiment E2 detector family for markets without daily price limits (US equities, crypto).

Eleven simple end-of-day rules, fixed before any E2 analysis (protocol KOD-GLOBAL-E2-v1).
One rule per market is selected on that market's discovery period and written into
SELECTED; until then the market has no rule. Every feature at session d uses data through
the close of d only; the opening price of d is known at its close.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

VERSION = "v1"
HOLDING_DAYS = 5
SELECTED = (("US", None), ("CRYPTO", None))
FEATURE_ARGS = ("close", "prev", "high", "low", "volume", "present", "tradeable", "open")
FAMILY = (
    ("G1_RET20_CLOSEHIGH", "day return >= +20% and close in the top 20% of the day's range"),
    ("G2_RET30", "day return >= +30%"),
    ("G3_VOL5_RET10", "volume >= 5x prior 20-session median and day return >= +10%"),
    ("G4_VOL10", "volume >= 10x prior 20-session median"),
    ("G5_IGNITION_D", "ASTRA IGNITION v1 thresholds on daily bars: day return >= +3%, >= +1.5 pp above the "
                      "cross-sectional median, volume >= 3x its prior 20-session median"),
    ("G6_BREAKOUT60_VOL3", "close above the prior 60-session high and volume >= 3x median"),
    ("G7_MOMENTUM5_30", "5-session return >= +30%"),
    ("G8_DD_REBOUND", "close >= 40% below its 60-session high, volume >= 5x median, day return >= +10%"),
    ("G9_GAP10_HOLD", "open >= 10% above the prior close, close at or above the open, volume >= 3x median"),
    ("G10_RET15_CLOSEHIGH", "day return >= +15% and close in the top 10% of the day's range"),
    ("G11_HIGHVOL_ACTIVE", "20-session volatility of daily log returns >= 8% and volume >= 2x median"),
)
RULE_TEXT = (
    "Experiment E2 detector: the single rule from FAMILY selected on the market's discovery period defined "
    "in research/E2/protocol.json, by the rule pre-registered there. Signal at the close of session d when "
    "that rule holds; hold 5 sessions."
)


def _lag(a, k):
    out = np.full(a.shape, np.nan)
    if k < a.shape[1]:
        out[:, k:] = a[:, :-k]
    return out


def _roll(a, window, min_periods, how, shift):
    frame = pd.DataFrame(a.T).rolling(window, min_periods=min_periods)
    if how == "median":
        out = frame.median()
    elif how == "max":
        out = frame.max()
    else:
        out = frame.std()
    out = out.to_numpy().T
    return _lag(out, shift) if shift else out


def features(close, prev, high, low, volume, present, tradeable, opens):
    """Arrays shaped (names, sessions); column d uses columns <= d only."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ok = tradeable & (prev > 0)
        ret1 = np.where(ok, close / prev - 1, np.nan)
        logret = np.where(present & (prev > 0) & (close > 0), np.log(close / prev), 0.0)
        level = np.where(present, np.exp(np.cumsum(logret, axis=1)), np.nan)
        vol = np.where(tradeable, volume, np.nan)
        med_vol = _roll(vol, 20, 10, "median", 1)
        volr = np.where(med_vol > 0, vol / med_vol, np.nan)
        market = pd.DataFrame(ret1).median(axis=0).to_numpy()
        rel1 = ret1 - market[None, :]
        ret5 = level / _lag(level, 5) - 1
        ret20 = level / _lag(level, 20) - 1
        brk60 = level > _roll(level, 60, 20, "max", 1)
        dd60 = level / _roll(level, 60, 20, "max", 0) - 1
        span = high - low
        cpos = np.where(span > 0, (close - low) / span, np.where(ret1 > 0, 1.0, np.where(ret1 < 0, 0.0, 0.5)))
        gap = np.where(ok & (opens > 0), opens / prev - 1, np.nan)
        hold = np.where(np.isfinite(gap), close >= opens, False)
        vol20 = _roll(np.where(ok, logret, np.nan), 20, 15, "std", 0)
    return {"ret1": ret1, "rel1": rel1, "ret5": ret5, "ret20": ret20, "volr": volr, "brk60": brk60, "dd60": dd60,
            "cpos": cpos, "gap": gap, "hold": hold, "vol20": vol20}


def family_flags(f):
    volr = np.nan_to_num(f["volr"])
    ret1 = np.nan_to_num(f["ret1"])
    cpos = np.nan_to_num(f["cpos"])
    return {
        "G1_RET20_CLOSEHIGH": (ret1 >= 0.20) & (cpos >= 0.8),
        "G2_RET30": ret1 >= 0.30,
        "G3_VOL5_RET10": (volr >= 5) & (ret1 >= 0.10),
        "G4_VOL10": volr >= 10,
        "G5_IGNITION_D": (ret1 >= 0.03) & (np.nan_to_num(f["rel1"]) >= 0.015) & (volr >= 3),
        "G6_BREAKOUT60_VOL3": f["brk60"] & (volr >= 3),
        "G7_MOMENTUM5_30": np.nan_to_num(f["ret5"]) >= 0.30,
        "G8_DD_REBOUND": (np.nan_to_num(f["dd60"]) <= -0.4) & (volr >= 5) & (ret1 >= 0.10),
        "G9_GAP10_HOLD": (np.nan_to_num(f["gap"]) >= 0.10) & f["hold"] & (volr >= 3),
        "G10_RET15_CLOSEHIGH": (ret1 >= 0.15) & (cpos >= 0.9),
        "G11_HIGHVOL_ACTIVE": (np.nan_to_num(f["vol20"]) >= 0.08) & (volr >= 2),
    }


def _compute_for(name):
    def compute(m):
        f = features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
        return np.where(m.tradeable, family_flags(f)[name].astype(float), np.nan)

    return compute


def selected(market):
    return next((name for mk, name in SELECTED if mk == market), None)


def rules():
    from . import Rule

    out = []
    for market, name in SELECTED:
        if name is not None:
            out.append(Rule(f"MOONSHOT_E2_{market}_D1", VERSION, RULE_TEXT + " Market: " + market + ". Selected: "
                            + name + ".", HOLDING_DAYS, _compute_for(name), sys.modules[__name__]))
    return out


def rule():
    return None
