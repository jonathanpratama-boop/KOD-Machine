"""Experiment E5 (E5-CEILING, protocol KOD-GLOBAL-E5-v1 draft): the daily-bar predictability ceiling.

Does any pre-registered combination of daily-bar features carry direction for sessions t+1..t+5,
or is the lab's validated detection variance detection? The family is one ranker per market and
arm: Arm A scores logit_U (the E30 ranker), Arm B scores logit_U - logit_D (the directional
ranker), each an L2 logistic regression fitted once on discovery by idxsig/e5.py over the
feature columns in FEATURE_ORDER. Beside them two descriptive detectors from KOD-DET-v0:
A0_CREEP_QUIET (volume creep and a quiet price, kod/detectors.py:72-86) and A1_CREEP_QUIET_NR
(A0 and not yet re-priced), the KOD population row.

Features (every column s uses sessions <= s only; names x sessions arrays):
  * the E1/E2 weak-signal list (E1-SIGNALS-v1 / E2-SIGNALS-v1): ret1, rel1, ret5, ret20, volr,
    brk60, dd60, cpos, gap copied from rules/moonshot_g.py; valr, rngr, vol20, up5, zero20, age,
    logval20 copied from e1.Study._signals (vol20 counts a present but untraded session as a zero
    log return, as the research tables did); ara from rules/moonshot_e1.py. age and zero20 are NaN
    before a name's first present session (e1.Study leaves them negative / zero there). age counts sessions
    since the name's FIRST LISTED session, not since the window's first column: the market passes
    listed_before (sessions listed before the window; execution.Market carries it through slice()), so a
    window that starts after a listing gives the same age, ranks and scores (audit finding B, v1.1); the
    count is left-censored at the pinned panel's first session, which is declared, not invented.
  * the pre-spike block: creep5v20 = median volume t-4..t / median volume t-24..t-5 over present
    sessions (an untraded session is zero volume); rngr5 = median rngr t-4..t; vc10_60 = vol10 /
    vol60; quiet = rngr5 <= 1.0 and |ret5| <= 2 vol20 sqrt(5) (kod-machine/research/ZEALAND_PILOT_v1/
    03_card/price_facts.py, same logic); not_repriced = ret20 < 0.30; rebase = some session s0 in
    [t-40, t-6] was a spike (ret1 >= 0.30, or on IDX a close locked at ARA, where a +30% close is
    impossible above Rp200) with level(t) <= pre + 0.5 (peak - pre) and min level(t-4..t) >= pre,
    pre = level(s0-1), peak = max level(s0..t).
  * rank transform: per-session cross-sectional percentile rank, (rank - 0.5) / n with average
    ties, among the names present and tradeable at that session; the pool is masked by `present`
    before ranking so a name listed later never changes an earlier column (prefix-first); a NaN
    value ranks 0.5; the squared rank enters too; binaries enter as 0/1.
  * FEATURE_WARMUP = 60: every array features() returns is NaN in the first 60 columns of the view
    (the longest look-back, brk60/dd60/vol60, is only window-invariant from there).

Flags: a session is flagged on the first session a name's score is >= the market's threshold
after at least five sessions KNOWN to be outside the set (trailing: column s reads columns
s-5..s only). A session with no score (the feature warm-up) is unknown, neither in nor out, so
it never counts towards the five: the first flag any window can emit is at column
FEATURE_WARMUP + DEBOUNCE, with five real out-of-set sessions behind it, and the same session
carries the same flag whatever earlier column the window starts at. A0/A1 are debounced the
same way (a session in the warm-up has no detector state).
  * WARMUP = FEATURE_WARMUP + DEBOUNCE = 65: compute() is NaN in the first 65 columns of the view.
    A harness window therefore starts WARMUP sessions before its period (read the literal; the
    protocol draft's "60" is the feature warm-up alone, which would put the debounce's lead-in
    inside the period).

Coefficients, intercepts and thresholds are module-level literals, None until discovery freezes
them (then validation refuses unless they equal discovery/model.json); the rule hash covers them.
A candidate rule whose literals are None refuses to compute (a harness run on an unfrozen ranker
would be a silent zero-signal run); family_flags() reports it as no flags, so a feature table or a
study can still be built. One FEATURE_ORDER serves every market: a feature a market does not have
(gap on IDX, ara off IDX) ranks 0.5 or is 0 there, a constant column the fit sees as such.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

RULE_ID = "MOONSHOT_E5"
VERSION = "v1"
SIDE = "long"
HOLDING_DAYS = 5
FEATURE_WARMUP = 60  # features() NaN in the first 60 columns of the view
DEBOUNCE = 5  # a flag needs this many trailing sessions known to be outside the set
WARMUP = FEATURE_WARMUP + DEBOUNCE  # compute() NaN in the first 65 columns; the harness lead-in
MARKETS = ("IDX", "US", "CRYPTO")
ARMS = ("A", "B")
CANDIDATES = ("IDX_A", "IDX_B", "US_A", "US_B", "CRYPTO_A", "CRYPTO_B", "A0_CREEP_QUIET", "A1_CREEP_QUIET_NR")
FEATURE_ARGS = ("close", "prev", "high", "low", "volume", "value", "present", "tradeable", "lock_up", "open",
                "listed_before")
RANKED = ("ret1", "rel1", "ret5", "ret20", "volr", "valr", "rngr", "cpos", "vol20", "dd60", "up5", "zero20", "age",
          "logval20", "gap", "creep5v20", "rngr5", "vc10_60")
BINARY = ("brk60", "ara", "quiet", "not_repriced", "rebase")
# The column order the coefficient literals refer to: the 18 ranks, their squares, the 5 binaries.
FEATURE_ORDER = (
    "ret1_r", "rel1_r", "ret5_r", "ret20_r", "volr_r", "valr_r", "rngr_r", "cpos_r", "vol20_r", "dd60_r", "up5_r",
    "zero20_r", "age_r", "logval20_r", "gap_r", "creep5v20_r", "rngr5_r", "vc10_60_r",
    "ret1_r2", "rel1_r2", "ret5_r2", "ret20_r2", "volr_r2", "valr_r2", "rngr_r2", "cpos_r2", "vol20_r2", "dd60_r2",
    "up5_r2", "zero20_r2", "age_r2", "logval20_r2", "gap_r2", "creep5v20_r2", "rngr5_r2", "vc10_60_r2",
    "brk60", "ara", "quiet", "not_repriced", "rebase",
)
# Frozen after discovery (stage 3 of the protocol): per market a tuple of len(FEATURE_ORDER) floats,
# a float intercept, and the arm's score threshold (the discovery 99.5th percentile). None until then.
COEF_U = (("IDX", None), ("US", None), ("CRYPTO", None))
COEF_D = (("IDX", None), ("US", None), ("CRYPTO", None))
INTERCEPT_U = (("IDX", None), ("US", None), ("CRYPTO", None))
INTERCEPT_D = (("IDX", None), ("US", None), ("CRYPTO", None))
THRESHOLD_A = (("IDX", None), ("US", None), ("CRYPTO", None))
THRESHOLD_B = (("IDX", None), ("US", None), ("CRYPTO", None))
SELECTED = None  # frozen after validation: ((market, arm), ...), e.g. (("IDX", "A"), ("CRYPTO", "B"))
CREEP_MIN = 1.5
QUIET_RNGR_MAX = 1.0
QUIET_BAND = 2.0
NOT_REPRICED_MAX = 0.30
SPIKE_RET = 0.30
REBASE_MIN_LAG = 6
REBASE_MAX_LAG = 40
REBASE_RETRACE = 0.5
VOL10_MIN = 8
VOL60_MIN = 45
FAMILY = (
    ("IDX_A", "IDX, Arm A: logit_U of the frozen IDX fit at or above THRESHOLD_A, first entry after 5 sessions out"),
    ("IDX_B", "IDX, Arm B: logit_U - logit_D of the frozen IDX fits at or above THRESHOLD_B, debounced"),
    ("US_A", "US, Arm A: logit_U of the frozen US fit at or above THRESHOLD_A, debounced"),
    ("US_B", "US, Arm B: logit_U - logit_D of the frozen US fits at or above THRESHOLD_B, debounced"),
    ("CRYPTO_A", "CRYPTO, Arm A: logit_U of the frozen CRYPTO fit at or above THRESHOLD_A, debounced"),
    ("CRYPTO_B", "CRYPTO, Arm B: logit_U - logit_D of the frozen CRYPTO fits at or above THRESHOLD_B, debounced"),
    ("A0_CREEP_QUIET", "KOD-DET-v0 VOLUME_CREEP_PRICE_QUIET: creep5v20 >= 1.5 and quiet, debounced"),
    ("A1_CREEP_QUIET_NR", "A0 and not re-priced (ret20 < +30%), debounced"),
)
RULE_TEXT = (
    "Experiment E5 (the ceiling): per market one ranker, Arm A = logit_U or Arm B = logit_U - logit_D, L2 logistic "
    "regressions over the ranked daily-bar features in FEATURE_ORDER fitted once on the market's discovery period "
    "(research/E5/protocol.json), coefficients and thresholds frozen here as literals; signal at the close of "
    "session d on the first session the score is at or above the threshold after five sessions outside it. "
    "A0_CREEP_QUIET and A1_CREEP_QUIET_NR are the KOD-DET-v0 volume-creep descriptive detectors, debounced alike. "
    "Entry and exit as the market plan says; long only."
)


def _lag(a, k):
    out = np.full(a.shape, np.nan)
    if k < a.shape[1]:
        out[:, k:] = a[:, :-k]
    return out


def _lagb(a, k):
    out = np.zeros(a.shape, dtype=bool)
    if k < a.shape[1]:
        out[:, k:] = a[:, :-k]
    return out


def _stat(frame, how):
    if how == "median":
        return frame.median()
    if how == "max":
        return frame.max()
    if how == "min":
        return frame.min()
    if how == "std":
        return frame.std()
    return frame.sum()


def _roll(a, window, min_periods, how, shift):
    frame = pd.DataFrame(a.T).rolling(window, min_periods=min_periods)
    out = _stat(frame, how).to_numpy().T
    if shift:
        out = _lag(out, shift)
    return out


def _warm(a, n):
    """A float copy with the first n columns NaN."""
    out = np.array(a, dtype=float)
    out[:, :n] = np.nan
    return out


def _of(table, market):
    for key, val in table:
        if key == market:
            return val
    return None


def _rebase(level, spike):
    """Some spike s0 in [t-40, t-6]; level(t) has given back at least half of the move from
    level(s0-1) to the peak since, and level(t-4..t) stayed at or above level(s0-1)."""
    min5 = _roll(level, 5, 5, "min", 0)
    out = np.zeros(level.shape, dtype=bool)
    peak = np.array(level, dtype=float)
    with np.errstate(invalid="ignore"):
        for k in range(1, REBASE_MAX_LAG + 1):
            peak = np.maximum(peak, _lag(level, k))  # max of level(t-k..t); NaN if any session is missing
            if k >= REBASE_MIN_LAG:
                pre = _lag(level, k + 1)
                out |= _lagb(spike, k) & (level <= pre + REBASE_RETRACE * (peak - pre)) & (min5 >= pre)
    return out


def raw_features(close, prev, high, low, volume, value, present, tradeable, lock_up, opens, listed_before=None):
    """Unranked features as float arrays (names, sessions); column d uses columns <= d only. listed_before:
    per name, the sessions it was listed before column 0 (required: age is never counted from the window
    start)."""
    if listed_before is None:
        raise ValueError("moonshot_e5 needs listed_before (sessions each name was listed before this window; "
                         "execution.Market.listed_before): age is not counted from the window start")
    lb = np.asarray(listed_before, dtype=float)
    if lb.shape != (close.shape[0],) or not np.all(np.isfinite(lb)) or np.any(lb < 0):
        raise ValueError("listed_before must be one finite non-negative count per name")
    with np.errstate(divide="ignore", invalid="ignore"):
        # --- rules/moonshot_g.features, verbatim
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
        # --- e1.Study._signals, verbatim (valr, rngr, vol20, up5, zero20, age, logval20); ara as moonshot_e1
        tr = tradeable
        val = np.where(tr, value, np.nan)
        med_val = _roll(val, 20, 10, "median", 1)
        rng = np.where(tr & (prev > 0), (high - low) / prev, np.nan)
        med_rng = _roll(rng, 20, 10, "median", 1)
        slogret = np.where(tr & (prev > 0), np.log(close / prev), np.where(present, 0.0, np.nan))
        first = np.where(present.any(axis=1), present.argmax(axis=1), present.shape[1])
        untraded = (present & ~tr).astype(float)
        valr = np.where(med_val > 0, val / med_val, np.nan)
        rngr = np.where(med_rng > 0, rng / med_rng, np.nan)
        vol20 = _roll(slogret, 20, 15, "std", 0)
        up5 = _roll(np.where(present, (np.nan_to_num(ret1) > 0).astype(float), np.nan), 5, 5, "sum", 0)
        zero20 = _roll(untraded, 20, 20, "sum", 1)
        cols = np.arange(present.shape[1])[None, :]
        first_eff = np.where(lb > 0, -lb, first.astype(float))  # listed before the window: age keeps counting
        age = np.where(cols >= first_eff[:, None], cols - first_eff[:, None], np.nan)  # NaN before the listing
        logval20 = np.log10(_roll(val, 20, 10, "median", 0))
        listed = cols >= first[:, None]  # NaN before the first present session of this window (zero20)
        zero20 = np.where(listed, zero20, np.nan)
        ara = lock_up & tradeable
        # --- the pre-spike block (ZEALAND price_facts.py definitions)
        vol_p = np.where(present, np.nan_to_num(volume), np.nan)
        v_recent = _roll(vol_p, 5, 5, "median", 0)
        v_base = _roll(vol_p, 20, 20, "median", 5)
        creep5v20 = np.where(v_base > 0, v_recent / v_base, np.nan)
        rngr5 = _roll(rngr, 5, 5, "median", 0)
        vol10 = _roll(slogret, 10, VOL10_MIN, "std", 0)
        vol60 = _roll(slogret, 60, VOL60_MIN, "std", 0)
        vc10_60 = np.where(vol60 > 0, vol10 / vol60, np.nan)
        quiet = (rngr5 <= QUIET_RNGR_MAX) & (np.abs(ret5) <= QUIET_BAND * vol20 * np.sqrt(5.0))
        not_repriced = ret20 < NOT_REPRICED_MAX
        spike = (np.nan_to_num(ret1) >= SPIKE_RET) | ara
        rebase = _rebase(level, spike)
    return {"ret1": ret1, "rel1": rel1, "ret5": ret5, "ret20": ret20, "volr": volr, "valr": valr, "rngr": rngr,
            "cpos": cpos, "vol20": vol20, "dd60": dd60, "up5": up5, "zero20": zero20, "age": age,
            "logval20": logval20, "gap": gap, "creep5v20": creep5v20, "rngr5": rngr5, "vc10_60": vc10_60,
            "brk60": brk60.astype(float), "ara": ara.astype(float), "quiet": quiet.astype(float),
            "not_repriced": not_repriced.astype(float), "rebase": rebase.astype(float)}


def rank_features(f, present, tradeable):
    """Per session, the percentile rank (rank - 0.5) / n of every RANKED feature among the names present
    and tradeable at that session (masked before ranking; NaN -> 0.5), its square, and the binaries as
    0/1; every output NaN in the first FEATURE_WARMUP columns."""
    pool = present & tradeable
    out = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        for name in RANKED:
            frame = pd.DataFrame(np.where(pool, f[name], np.nan))
            count = frame.notna().sum(axis=0).to_numpy(dtype=float)[None, :]
            r = (frame.rank(axis=0, method="average").to_numpy() - 0.5) / count
            r = np.where(np.isfinite(r), r, 0.5)
            out[name + "_r"] = _warm(r, FEATURE_WARMUP)
            out[name + "_r2"] = _warm(r * r, FEATURE_WARMUP)
    for name in BINARY:
        out[name] = _warm(f[name], FEATURE_WARMUP)
    return out


def features(close, prev, high, low, volume, value, present, tradeable, lock_up, opens, listed_before=None):
    """raw_features plus rank_features in one dict; every array NaN in the first FEATURE_WARMUP columns."""
    f = raw_features(close, prev, high, low, volume, value, present, tradeable, lock_up, opens, listed_before)
    f.update(rank_features(f, present, tradeable))
    return {k: _warm(v, FEATURE_WARMUP) for k, v in f.items()}


def score(ranked, coef, intercept):
    """intercept + sum of coef[i] * ranked[FEATURE_ORDER[i]]: the logit."""
    if len(coef) != len(FEATURE_ORDER):
        raise ValueError(f"{len(coef)} coefficients for {len(FEATURE_ORDER)} feature columns")
    out = np.full(ranked[FEATURE_ORDER[0]].shape, float(intercept))
    for name, c in zip(FEATURE_ORDER, coef):
        out = out + float(c) * ranked[name]
    return out


def debounce(state, known=None):
    """True on the first session of a run of True after at least DEBOUNCE sessions known to be False
    (trailing: column s reads columns s-DEBOUNCE..s only; never before DEBOUNCE sessions of history).
    `known` marks the sessions whose state is defined; an unknown session (the warm-up) is neither
    in nor out and never counts towards the DEBOUNCE, so a window's first flag has DEBOUNCE real
    out-of-set sessions behind it wherever the window starts. known=None: every session is known."""
    state = np.asarray(state, dtype=bool)
    known = np.ones(state.shape, dtype=bool) if known is None else np.asarray(known, dtype=bool)
    ok = np.zeros(state.shape, dtype=bool)
    ok[:, DEBOUNCE:] = True
    for k in range(1, DEBOUNCE + 1):
        ok &= _lagb(known & ~state, k)
    return state & known & ok


def flags(score_, threshold):
    """Debounced entries into {score >= threshold}; a NaN score is unknown (not outside the set)."""
    known = np.isfinite(score_)
    with np.errstate(invalid="ignore"):
        state = known & (score_ >= float(threshold))
    return debounce(state, known)


def arm_score(f, market, arm):
    """The arm's score from the frozen literals, or None while any of them is None."""
    coef, icpt = _of(COEF_U, market), _of(INTERCEPT_U, market)
    if coef is None or icpt is None:
        return None
    s = score(f, coef, icpt)
    if arm == "B":
        coef_d, icpt_d = _of(COEF_D, market), _of(INTERCEPT_D, market)
        if coef_d is None or icpt_d is None:
            return None
        s = s - score(f, coef_d, icpt_d)
    return s


def arm_threshold(market, arm):
    return _of(THRESHOLD_A if arm == "A" else THRESHOLD_B, market)


def frozen(name):
    """Whether the candidate can compute: A0/A1 always; an arm once its literals are all set."""
    if name in ("A0_CREEP_QUIET", "A1_CREEP_QUIET_NR"):
        return True
    market, arm = name.split("_")
    need = [_of(COEF_U, market), _of(INTERCEPT_U, market), arm_threshold(market, arm)]
    if arm == "B":
        need += [_of(COEF_D, market), _of(INTERCEPT_D, market)]
    return all(x is not None for x in need)


def detector_states(f):
    """Raw (undebounced) KOD-DET-v0 states: A0 = creep and quiet; A1 = A0 and not re-priced. A
    detector fact that is undefined at a session (creep5v20 NaN) makes the state False there, as
    kod/detectors.py reports no SIGNAL on a None fact; only the warm-up has no state at all."""
    creep = np.nan_to_num(f["creep5v20"], nan=-1.0)
    a0 = (creep >= CREEP_MIN) & (f["quiet"] == 1.0)
    return {"A0_CREEP_QUIET": a0, "A1_CREEP_QUIET_NR": a0 & (f["not_repriced"] == 1.0)}


def family_flags(f):
    """Debounced flags for every FAMILY member: an arm without frozen literals has none."""
    shape = f["ret1"].shape
    out = {}
    for market in MARKETS:
        for arm in ARMS:
            name = market + "_" + arm
            s, thr = arm_score(f, market, arm), arm_threshold(market, arm)
            out[name] = np.zeros(shape, dtype=bool) if s is None or thr is None else flags(s, thr)
    known = np.isfinite(f["quiet"])  # the detector state exists once the features are warm
    for name, state in detector_states(f).items():
        out[name] = debounce(state, known)
    return out


def _compute_for(name):
    def compute(m):
        if not frozen(name):
            raise RuntimeError(f"{candidate_rule_id(name)}: the {name} ranker has no frozen coefficients, intercept or "
                               "threshold in rules/moonshot_e5.py (discovery not done, or its literals not committed); "
                               "it computes nothing until they are frozen")
        f = features(m.close, m.prev, m.high, m.low, m.volume, m.value, m.present, m.tradeable, m.lock_up, m.open,
                     m.listed_before)
        return _warm(np.where(m.tradeable, family_flags(f)[name].astype(float), np.nan), WARMUP)

    return compute


def candidate_rule_id(name):
    return "E5_CAND_" + name


def selected_rule_id(market):
    return RULE_ID + "_" + market + "_D1"


def rules():
    from . import Rule

    out = [Rule(candidate_rule_id(name), VERSION, RULE_TEXT + " Candidate: " + name + " (" + text + "; no plan: the "
                "harness run names the market plan).", HOLDING_DAYS, _compute_for(name), sys.modules[__name__])
           for name, text in FAMILY]
    if SELECTED is not None:
        for market, arm in SELECTED:
            name = market + "_" + arm
            if not frozen(name):
                raise RuntimeError(f"SELECTED names {name} but its coefficients or threshold are not frozen")
            out.append(Rule(selected_rule_id(market), VERSION, RULE_TEXT + " Selected for " + market + ": arm " + arm
                            + ".", HOLDING_DAYS, _compute_for(name), sys.modules[__name__]))
    return out


def rule():
    return None
