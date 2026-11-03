"""Experiment E1 detector family: ten simple, interpretable end-of-day rules.

One source of truth for the historical study (idxsig/e1.py), the backtest harness and the
live paper scan (idxsig/paper.py). Every feature at session d uses data through the close
of d only, from fields Yahoo also provides (no trade frequency, no share counts), so a rule
chosen historically can run live unchanged.

SELECTED names the one rule frozen after the discovery period (protocol KOD-IDX-E1-v1);
None until then, and rule() returns no rule. Changing SELECTED or any threshold changes
this module's hash and is a new detector version.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

RULE_ID = "MOONSHOT_E1_D1"
VERSION = "v1.1"  # v1.1: no crash on windows shorter than a lookback; flags identical where v1 ran
HOLDING_DAYS = 5
SELECTED = "F1_ARA"  # frozen 2026-10-08 from research/E1/discovery/detector_selection.csv
FAMILY = (
    ("F1_ARA", "close locked at the upper auto-rejection limit (ARA)"),
    ("F2_IGNITION_D", "ASTRA IGNITION v1 thresholds on daily bars: day return >= +3%, >= +1.5 pp above the "
                      "cross-sectional median, volume >= 3x its prior 20-session median"),
    ("F3_VOL5_RET10", "volume >= 5x prior 20-session median and day return >= +10%"),
    ("F4_VOL10", "volume >= 10x prior 20-session median"),
    ("F5_RET15_CLOSEHIGH", "day return >= +15% and close in the top 10% of the day's range"),
    ("F6_BREAKOUT60_VOL3", "close above the prior 60-session high and volume >= 3x median"),
    ("F7_ARA_VOL3", "ARA close and volume >= 3x median"),
    ("F8_ARA_EARLY", "ARA close and 20-session return (through today) below +50%"),
    ("F9_MOMENTUM5_30", "5-session return >= +30%"),
    ("F10_DD_REBOUND", "close >= 40% below its 60-session high, volume >= 5x median, day return >= +10%"),
)
RULE_TEXT = (
    "Experiment E1 detector D1: the single rule from FAMILY selected on the discovery period "
    "defined in research/E1/PROTOCOL.md, by the rule pre-registered there. Signal at the "
    "close of session d when that rule holds; hold 5 sessions."
)


def _roll(a, window, min_periods, how, shift):
    frame = pd.DataFrame(a.T).rolling(window, min_periods=min_periods)
    out = _stat(frame, how).to_numpy().T
    if shift:
        out = _lag(out, shift)
    return out


def _stat(frame, how):
    if how == "median":
        return frame.median()
    if how == "max":
        return frame.max()
    if how == "std":
        return frame.std()
    return frame.sum()


def _lag(a, k):
    out = np.full(a.shape, np.nan)
    if k < a.shape[1]:
        out[:, k:] = a[:, :-k]
    return out


def features(close, prev, high, low, volume, present, tradeable, lock_up):
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
    return {"ret1": ret1, "rel1": rel1, "ret5": ret5, "ret20": ret20, "volr": volr, "brk60": brk60,
            "dd60": dd60, "cpos": cpos, "ara": lock_up & tradeable}


def family_flags(f):
    volr = np.nan_to_num(f["volr"])
    ret1 = np.nan_to_num(f["ret1"])
    return {
        "F1_ARA": f["ara"],
        "F2_IGNITION_D": (ret1 >= 0.03) & (np.nan_to_num(f["rel1"]) >= 0.015) & (volr >= 3),
        "F3_VOL5_RET10": (volr >= 5) & (ret1 >= 0.10),
        "F4_VOL10": volr >= 10,
        "F5_RET15_CLOSEHIGH": (ret1 >= 0.15) & (np.nan_to_num(f["cpos"]) >= 0.9),
        "F6_BREAKOUT60_VOL3": f["brk60"] & (volr >= 3),
        "F7_ARA_VOL3": f["ara"] & (volr >= 3),
        "F8_ARA_EARLY": f["ara"] & (np.nan_to_num(f["ret20"], nan=9.0) < 0.5),
        "F9_MOMENTUM5_30": np.nan_to_num(f["ret5"]) >= 0.30,
        "F10_DD_REBOUND": (np.nan_to_num(f["dd60"]) <= -0.4) & (volr >= 5) & (ret1 >= 0.10),
    }


def compute(m):
    f = features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.lock_up)
    flag = family_flags(f)[SELECTED]
    return np.where(m.tradeable, flag.astype(float), np.nan)


def rule():
    from . import Rule

    if SELECTED is None:
        return None
    return Rule(RULE_ID, VERSION, RULE_TEXT + " Selected: " + SELECTED + ".", HOLDING_DAYS, compute,
                sys.modules[__name__])
