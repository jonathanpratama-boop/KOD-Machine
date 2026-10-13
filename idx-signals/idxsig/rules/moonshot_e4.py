"""Experiment E4 candidates and the frozen (detector, plan) pair (protocol KOD-GLOBAL-E4-v1): the fade.

E2 validated G2_RET30 (a +30% day) for detection in US equities and crypto and found that buying
the next open loses; the median five-session move after a flag was about -10% against 0% for
matched names. E4 asks whether the SHORT side of the E2 family's "already ran" detectors, under a
fixed family of execution plans (research/E4/protocol.json), earns a positive net return after
fees, slippage and carry, beats matched random shorts, and does so in every discovery year.

The four candidates' feature and flag code is copied from moonshot_g.py (a rule module may import
nothing from the package); tests/test_e4.py checks the copy flags exactly as the original. Until
discovery is done SELECTED is None, the candidates run as E4_CAND_<name> (original long plan, hold
5, so the harness can reproduce E2), and MOONSHOT_E4_D1 does not exist. After discovery SELECTED is
written here as a tuple (detector, entry_rule, entry_window, exit_rule, holding_days) and
committed before validation; MOONSHOT_E4_D1 then carries that plan on the short side
(rules.Rule.plan), and this module's hash covers it.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

RULE_ID = "MOONSHOT_E4_D1"
VERSION = "v1"
SIDE = "short"
CANDIDATES = ("G2_RET30", "G1_RET20_CLOSEHIGH", "G10_RET15_CLOSEHIGH", "G7_MOMENTUM5_30")
SELECTED = None  # frozen after discovery: (detector, entry_rule, entry_window, exit_rule, holding_days)
FEATURE_ARGS = ("close", "prev", "high", "low", "volume", "present", "tradeable", "open")
FAMILY = (
    ("G2_RET30", "day return >= +30%"),
    ("G1_RET20_CLOSEHIGH", "day return >= +20% and close in the top 20% of the day's range"),
    ("G10_RET15_CLOSEHIGH", "day return >= +15% and close in the top 10% of the day's range"),
    ("G7_MOMENTUM5_30", "5-session return >= +30%"),
)
RULE_TEXT = (
    "Experiment E4 (the fade): one of the E2 family's already-ran detectors G2_RET30, G1_RET20_CLOSEHIGH, "
    "G10_RET15_CLOSEHIGH, G7_MOMENTUM5_30 (research/E2/protocol.json) traded on the SHORT side with one "
    "execution plan from the family in research/E4/protocol.json, the pair selected on the discovery period by "
    "the rule pre-registered there. Signal at the close of session d when the detector holds; the short "
    "entry and its cover as the plan says."
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
    """Arrays shaped (names, sessions); column d uses columns <= d only. As moonshot_g.features."""
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
    ret1 = np.nan_to_num(f["ret1"])
    cpos = np.nan_to_num(f["cpos"])
    return {
        "G2_RET30": ret1 >= 0.30,
        "G1_RET20_CLOSEHIGH": (ret1 >= 0.20) & (cpos >= 0.8),
        "G10_RET15_CLOSEHIGH": (ret1 >= 0.15) & (cpos >= 0.9),
        "G7_MOMENTUM5_30": np.nan_to_num(f["ret5"]) >= 0.30,
    }


def _compute_for(name):
    def compute(m):
        f = features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
        return np.where(m.tradeable, family_flags(f)[name].astype(float), np.nan)

    return compute


def candidate_rule_id(name):
    return "E4_CAND_" + name


def selected_plan():
    """The frozen plan as rules.Rule.plan sees it (short side), or None."""
    if SELECTED is None:
        return None
    return {"entry_rule": SELECTED[1], "entry_window": SELECTED[2], "exit_rule": SELECTED[3], "side": SIDE}


def rules():
    from . import Rule

    out = [Rule(candidate_rule_id(name), VERSION, RULE_TEXT + " Candidate: " + name + " (no plan: the harness "
                "run names the side and plan).", 5, _compute_for(name), sys.modules[__name__])
           for name in CANDIDATES]
    if SELECTED is not None:
        out.append(Rule(RULE_ID, VERSION, RULE_TEXT + " Selected: " + SELECTED[0] + "; side short; plan: entry "
                        + SELECTED[1] + " within " + str(SELECTED[2]) + " session(s), exit " + SELECTED[3]
                        + ", hold " + str(SELECTED[4]) + ".", SELECTED[4], _compute_for(SELECTED[0]),
                        sys.modules[__name__], plan=selected_plan()))
    return out


def rule():
    return None
