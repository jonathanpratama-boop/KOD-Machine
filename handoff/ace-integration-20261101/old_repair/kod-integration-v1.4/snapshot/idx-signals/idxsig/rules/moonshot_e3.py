"""Experiment E3 candidates and the frozen (detector, plan) pair (protocol KOD-IDX-E3-v1).

E1 froze F1_ARA as D1: validated for detection, failed for execution under the one plan the
harness had (buy the next close, hold five sessions). E3 searches a fixed family of execution
plans (research/E3/protocol.json) for the three ARA members of the E1 family. Their feature and
flag code is copied from moonshot_e1.py (a rule module may import nothing from the package);
tests/test_e3.py checks the copy flags exactly as the original.

Until discovery is done SELECTED is None, the candidates run as E3_CAND_<name> (original plan,
hold 5), and MOONSHOT_E3_D1 does not exist. After discovery SELECTED is written here as a tuple
(detector, entry_rule, entry_window, exit_rule, holding_days) and committed before validation;
MOONSHOT_E3_D1 then carries that plan (rules.Rule.plan), and this module's hash covers it.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

RULE_ID = "MOONSHOT_E3_D1"
VERSION = "v1"
CANDIDATES = ("F1_ARA", "F7_ARA_VOL3", "F8_ARA_EARLY")
SELECTED = None  # frozen after discovery: (detector, entry_rule, entry_window, exit_rule, holding_days)
FAMILY = (
    ("F1_ARA", "close locked at the upper auto-rejection limit (ARA)"),
    ("F7_ARA_VOL3", "ARA close and volume >= 3x median"),
    ("F8_ARA_EARLY", "ARA close and 20-session return (through today) below +50%"),
)
RULE_TEXT = (
    "Experiment E3: one of the ARA detectors F1_ARA, F7_ARA_VOL3, F8_ARA_EARLY (E1 family, research/E1/"
    "PROTOCOL.md) with one execution plan from the family in research/E3/protocol.json, the pair selected "
    "on the discovery period by the rule pre-registered there. Signal at the close of session d when the "
    "detector holds; entry and exit as the plan says."
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
    """Arrays shaped (names, sessions); column d uses columns <= d only. As moonshot_e1.features."""
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
    return {
        "F1_ARA": f["ara"],
        "F7_ARA_VOL3": f["ara"] & (volr >= 3),
        "F8_ARA_EARLY": f["ara"] & (np.nan_to_num(f["ret20"], nan=9.0) < 0.5),
    }


def _compute_for(name):
    def compute(m):
        f = features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.lock_up)
        return np.where(m.tradeable, family_flags(f)[name].astype(float), np.nan)

    return compute


def candidate_rule_id(name):
    return "E3_CAND_" + name


def selected_plan():
    """The frozen plan as rules.Rule.plan sees it, or None."""
    if SELECTED is None:
        return None
    return {"entry_rule": SELECTED[1], "entry_window": SELECTED[2], "exit_rule": SELECTED[3]}


def rules():
    from . import Rule

    out = [Rule(candidate_rule_id(name), VERSION, RULE_TEXT + " Candidate: " + name + " (original plan).", 5,
                _compute_for(name), sys.modules[__name__]) for name in CANDIDATES]
    if SELECTED is not None:
        out.append(Rule(RULE_ID, VERSION, RULE_TEXT + " Selected: " + SELECTED[0] + "; plan: entry " + SELECTED[1]
                        + " within " + str(SELECTED[2]) + " session(s), exit " + SELECTED[3] + ", hold "
                        + str(SELECTED[4]) + ".", SELECTED[4], _compute_for(SELECTED[0]), sys.modules[__name__],
                        plan=selected_plan()))
    return out


def rule():
    return None
