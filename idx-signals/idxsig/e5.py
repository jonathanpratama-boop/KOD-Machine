"""Experiment E5 (research/E5/protocol.json, KOD-GLOBAL-E5-v1, E5-CEILING): the daily-bar predictability ceiling.

Does any pre-registered combination of daily-bar features carry direction for sessions t+1..t+5
beyond matched controls, or is the lab's validated detection variance detection? Per market one
ranker per arm (A = logit_U, B = logit_U - logit_D), two L2 logistic fits on discovery over the 41
feature columns of rules/moonshot_e5.FEATURE_ORDER, a threshold fixed once at the discovery 99.5th
percentile, debounced flags. Stages, each a new directory under research/E5/<MARKET>/ (frozen by
the commit guard):

  reproduce   the market's precondition run re-run from its recorded config on the pinned panel
  discovery   stage 1 (information, fill-independent) then stage 2 (execution: harness runs under
              the market plan for the arms that passed the stage-1 gate) in one command
  freeze      discovery/model.json copied into the module's literal tables, SELECTED set (stage 3)
  validation  the validation period only, recorded harness runs per admissible arm (stage 4)

Every parameter is read from the protocol (PROTOCOL_KEYS lists what and where); nothing numeric is
fixed here. The holdout is never loaded: assert_within_validation refuses any window end past the
market's validation end before a RunConfig or Study is built, and the harness refuses it again.
"""

from __future__ import annotations

import ast
import contextlib
import importlib.util
import itertools
import json
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd

from . import e1, e3
from .backtest import GLOBAL_HOLDOUT, HOLDOUT, HoldoutSealed, RunConfig, paired_excess, run
from .e1 import wilson
from .e3 import _now, _runtime, plan_row, recorded_run, write_csv, write_json
from .execution import Market, reference_level
from .market import REGIMES, regime_index
from .profiles import PROFILES
from .provenance import PKG_ROOT, rel, sha256_file
from .results import code_state, write_run
from .rules import moonshot_e5

E5_DIR = PKG_ROOT / "research" / "E5"
PROTOCOL = E5_DIR / "protocol.json"
MODULE_PATH = Path(moonshot_e5.__file__)
STAGES = ("reproduce", "discovery", "freeze", "validation")
MARKETS = ("IDX", "US", "CRYPTO")
ARMS = ("A", "B")
DETECTORS = ("A0_CREEP_QUIET", "A1_CREEP_QUIET_NR")
LITERAL_TABLES = ("COEF_U", "COEF_D", "INTERCEPT_U", "INTERCEPT_D", "THRESHOLD_A", "THRESHOLD_B")
MODEL_KEYS = {"COEF_U": "coef_U", "COEF_D": "coef_D", "INTERCEPT_U": "intercept_U", "INTERCEPT_D": "intercept_D",
              "THRESHOLD_A": "threshold_A", "THRESHOLD_B": "threshold_B"}
SCORED_STATUS = ("EXITED", "EXIT_DATA_END")
PLAN_KEYS = e3.PLAN_KEYS
PLAN_FIELDS = ("market", "entry_rule", "entry_window", "exit_rule", "holding_days", "fill_model", "units", "ca_mode",
               "notional", "max_participation", "fee_buy", "fee_sell", "quarantine", "jump_ratio")
_LOAD_COUNTER = itertools.count()
# Every protocol.json key this module reads, as a dotted path (<M> = a market of MARKETS), and the stage
# that reads it. tests/test_e5.py checks each one resolves in the draft protocol.
PROTOCOL_KEYS = (
    ("protocol_id", "all"), ("frozen_before_analysis", "all"), ("search_size", "all"), ("claims", "all"),
    ("harness.warmup_sessions", "all"), ("periods.discovery", "e1.Study"), ("periods.validation", "e1.Study"),
    ("weak_signals.continuous", "e1.Study"), ("weak_signals.binary", "e1.Study"),
    ("features.order", "discovery"),
    ("markets.<M>.panel_format", "all"), ("markets.<M>.panel_manifest", "cli"), ("markets.<M>.panel_sha256", "cli"),
    ("markets.IDX.registry_manifest", "cli"), ("markets.<M>.precondition_runs", "reproduce"),
    ("markets.<M>.periods.discovery", "all"), ("markets.<M>.periods.validation", "all"),
    ("markets.<M>.pool_units", "discovery, validation"), ("markets.<M>.discovery_years", "discovery"),
    ("markets.<M>.primary_arm", "discovery"),
    ("matched_controls.detection_stage.pool_version", "discovery, validation"),
    ("matched_controls.detection_stage.draws", "discovery, validation"),
    ("matched_controls.detection_stage.seed", "discovery, validation"),
    ("matched_controls.paired_statistic.resamples", "discovery, validation"),
    ("matched_controls.paired_statistic.seed", "discovery, validation"),
    ("matched_controls.paired_statistic.cluster", "discovery, validation"),
    ("labels.horizon", "discovery, validation"), ("labels.threshold", "discovery, validation"),
    ("labels.unit_reset_censoring.markets", "discovery, validation"),
    ("labels.unit_reset_censoring.ratio", "discovery, validation"),
    ("labels.unit_reset_censoring.sessions_before", "discovery, validation"),
    ("learner.iterations", "discovery"), ("learner.lambda_per_row", "discovery"),
    ("learner.negative_subsample", "discovery"), ("learner.negative_weight", "discovery"), ("learner.seed", "discovery"),
    ("learner.threshold_percentile", "discovery"),
    ("plans.<M>.primary", "discovery, validation"), ("plans.<M>.sensitivities", "discovery, validation"),
    *((f"plans.<M>.primary.{k}", "discovery, validation (harness_config)") for k in PLAN_FIELDS),
    ("harness.entry_lag", "discovery, validation"), ("harness.random_draws", "discovery, validation"),
    ("harness.seed", "discovery, validation"), ("harness.overlap", "discovery, validation"),
    ("harness.data_end_exit", "discovery, validation"), ("harness.controls_version", "discovery, validation"),
    ("harness.controls_version_reported", "discovery, validation"), ("harness.lookahead_cuts", "discovery, validation"),
    ("selection.min_scored", "discovery (e3.admissibility)"),
    ("selection.max_p_one_sided_vs_matched", "discovery (e3.admissibility)"),
    ("selection.min_scored_per_year", "discovery (e3.admissibility)"),
    ("stages.0_reproduce.rule_side_fields", "reproduce"),
    ("stages.0_reproduce.accepted_deviation.field", "reproduce"),
    ("stages.0_reproduce.accepted_deviation.abs_tolerance", "reproduce"),
    ("stages.1_information.gate_to_stage_2.min_flags", "discovery"),
    ("stages.1_information.gate_to_stage_2.alpha", "discovery"),
    ("stages.1_information.gate_to_stage_2.min_flags_per_year", "discovery"),
    ("stages.1_information.primaries", "discovery"),
    ("stages.1_information.a1_gate.min_lift", "discovery"), ("stages.1_information.a1_gate.max_p", "discovery"),
    ("stages.1_information.pre_move_split_ret1", "discovery"),
    ("stages.1_information.univariate.controls_per_event", "discovery"),
    ("stages.1_information.univariate.controls_seed", "discovery"),
    ("stages.1_information.univariate.auc_bootstrap", "discovery"),
    ("stages.1_information.univariate.auc_seed", "discovery"),
    ("stages.1_information.univariate.top_share", "discovery"),
    ("stages.2_execution.alpha_paired_net", "discovery"), ("stages.2_execution.exit_participation_max", "discovery"),
    ("validation.min_scored.<M>", "validation"), ("validation.alpha_paired_net", "validation"),
    ("validation.max_p_one_sided_vs_matched", "validation"), ("validation.claim_level", "validation"),
)


# ---------------------------------------------------------------------------------------------- protocol
def protocol(path: Path | None = None) -> tuple[dict, str]:
    path = path or PROTOCOL
    return json.loads(Path(path).read_text(encoding="utf-8")), sha256_file(path)


def get(proto: dict, path: str):
    """The value at a dotted path of the protocol; KeyError names the missing key."""
    node = proto
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise KeyError(f"protocol has no {path!r} (missing {key!r})")
        node = node[key]
    return node


def use_protocol(path: Path) -> Path:
    """Point every stage at this protocol file; the file's directory holds the stage outputs
    (research/E5 for v1, research/E5/<version>/ for an addendum)."""
    global PROTOCOL
    PROTOCOL = Path(path)
    return PROTOCOL


def version_dir() -> Path:
    return PROTOCOL.parent


def _rel(path: Path) -> str:
    """rel() for paths inside the package, the absolute path otherwise (tests, temp dirs)."""
    path = Path(path)
    return rel(path) if path.resolve().is_relative_to(PKG_ROOT) else str(path)


def market_dir(market: str) -> Path:
    if market not in MARKETS:
        raise ValueError(f"unknown E5 market {market!r}; CRYPTO_CLOSE is a sensitivity inside CRYPTO")
    return version_dir() / market


def stage_dir(market: str, stage: str) -> Path:
    if stage not in STAGES:
        raise ValueError(f"unknown E5 stage {stage!r}")
    return market_dir(market) / stage


def spec_market(market: str) -> str:
    """The protocol markets entry a RunConfig market reads: CRYPTO_CLOSE shares CRYPTO's."""
    return PROFILES[market].market


def assert_within_validation(proto: dict, market: str, end) -> None:
    """Refuse any window end past the market's validation end or inside the sealed holdout, before a
    RunConfig or Study is built. `end` is an ISO date (string or datetime64)."""
    mk = spec_market(market)
    v_end = get(proto, f"markets.{mk}.periods.validation")[1]
    sealed = HOLDOUT if mk == "IDX" else GLOBAL_HOLDOUT
    end = str(np.datetime64(end, "D"))
    if end > v_end or end >= sealed[0]:
        raise HoldoutSealed(f"window end {end} is past the {mk} validation end {v_end} (holdout {sealed[0]}.."
                            f"{sealed[1]} is sealed; E5 never loads it)")


def sessions_of(panel_df: pd.DataFrame) -> np.ndarray:
    return np.array(sorted(panel_df["date"].unique()), dtype="datetime64[D]")


def window_for(proto: dict, market: str, sessions: np.ndarray, period: str) -> dict:
    """The study/harness window of `period` for `market`: WARMUP sessions before the period's first
    session (clipped to the panel's first session, the shortfall recorded) up to the period's end."""
    mk = spec_market(market)
    start, end = get(proto, f"markets.{mk}.periods.{period}")
    warm = int(get(proto, "harness.warmup_sessions"))
    if warm != moonshot_e5.WARMUP:
        raise ValueError(f"protocol warm-up {warm} differs from moonshot_e5.WARMUP {moonshot_e5.WARMUP}")
    assert_within_validation(proto, market, end)
    first = int(np.searchsorted(sessions, np.datetime64(start, "D"), side="left"))
    last = int(np.searchsorted(sessions, np.datetime64(end, "D"), side="right")) - 1
    if first >= len(sessions) or last < first:
        raise ValueError(f"the panel has no sessions in the {mk} {period} period {start}..{end}")
    lo = max(0, first - warm)
    return {"period": period, "period_start": start, "period_end": end, "start": str(sessions[lo]), "end": end,
            "first_period_session": str(sessions[first]), "last_period_session": str(sessions[last]),
            "lead_in_sessions": int(first - lo), "warmup_sessions": warm,
            "lead_in_short": bool(first - lo < warm)}


def build_study(proto: dict, market: str, panel_df: pd.DataFrame, meta: dict, protocol_path: Path | None = None,
                period: str = "discovery") -> e1.Study:
    """e1.Study on the panel sliced to the market's window of `period` (its warm-up start .. the
    market's validation end, where the study seals itself), with the protocol's detection pool and the
    market's declared panel format passed explicitly."""
    mk = spec_market(market)
    sessions = sessions_of(panel_df)
    window = window_for(proto, market, sessions, period)
    v_end = get(proto, f"markets.{mk}.periods.validation")[1]
    assert_within_validation(proto, market, v_end)
    dates = panel_df["date"].to_numpy().astype("datetime64[D]")
    # v1.1 (audit finding A): the study holds the period's sessions only, never a later row; and (finding B)
    # each name's listing history before the window start rides along, counted on the full pinned panel
    # (left-censored at its first session), so age does not depend on where the window starts.
    study_end = window["end"]
    lo = int(np.searchsorted(sessions, np.datetime64(window["start"], "D"), side="left"))
    first_date = panel_df.groupby("ticker")["date"].min()
    first_idx = np.searchsorted(sessions, first_date.to_numpy().astype("datetime64[D]"), side="left")
    listed_before = pd.Series(np.maximum(0, lo - first_idx).astype(np.int64), index=first_date.index)
    window["study_end"] = study_end
    window["listed_before"] = {"definition": "sessions since the name's first present session in the pinned panel "
                                             "that fall before the window start",
                               "panel_first_session": str(sessions[0]), "left_censored_names": int((first_idx == 0).sum())}
    keep = (dates >= np.datetime64(window["start"], "D")) & (dates <= np.datetime64(study_end, "D"))
    df = panel_df.loc[keep].reset_index(drop=True)
    df["sessions_listed_before"] = df["ticker"].map(listed_before).astype(np.int64)
    study = e1.Study(df, meta, protocol_path=protocol_path or PROTOCOL, profile=PROFILES[mk],
                     family_module=moonshot_e5, pool_units=get(proto, f"markets.{mk}.pool_units"),
                     pool_version=get(proto, "matched_controls.detection_stage.pool_version"),
                     panel_format=get(proto, f"markets.{mk}.panel_format"))
    study.e5_window = window
    return study


# ------------------------------------------------------------------------------------------------ labels
def _lead(a: np.ndarray, k: int) -> np.ndarray:
    return e1._lead(a, k)


def labels(study: e1.Study, proto: dict, market: str) -> dict:
    """U, the raw D inputs and the censoring masks on the study market. U = r5max >= threshold - 1 as
    e1.Study; r5min = min level(t+1..t+H)/level(t) - 1; a unit reset (crypto) censors the labels of
    the sessions_before sessions up to it and the plan-window return of any flag whose window t+1..t+H+1
    contains it. Float arrays: 1/0 where labelled, NaN elsewhere."""
    mk = spec_market(market)
    H = int(get(proto, "labels.horizon"))
    x = float(get(proto, "labels.threshold"))
    m, L = study.m, study.level
    ahead = np.stack([_lead(L, k) for k in range(1, H + 1)])
    with np.errstate(divide="ignore", invalid="ignore"):
        ratios = ahead / L[None] - 1
    fin = np.isfinite(ratios)
    has_fwd = fin.any(axis=0)
    r5min = np.where(has_fwd, np.nanmin(np.where(fin, ratios, np.inf), axis=0), np.nan)
    r5max = np.where(has_fwd, np.nanmax(np.where(fin, ratios, -np.inf), axis=0), np.nan)
    cens = get(proto, "labels.unit_reset_censoring")
    reset = np.zeros(m.shape, dtype=bool)
    resets = []
    if mk in cens["markets"]:
        R = float(cens["ratio"])
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(m.present & (m.prev > 0), m.close / m.prev, 1.0)
        reset = m.present & ((ratio >= R) | (ratio <= 1 / R))
        resets = [{"ticker": str(m.tickers[n]), "date": str(m.dates[d]), "ratio": float(ratio[n, d])}
                  for n, d in zip(*np.nonzero(reset))]
    before = int(cens["sessions_before"])
    censor_label = np.zeros(m.shape, dtype=bool)
    for k in range(0, before + 1):
        censor_label |= _lead(reset.astype(float), k) == 1.0
    censor_plan = np.zeros(m.shape, dtype=bool)
    for k in range(1, H + 2):
        censor_plan |= _lead(reset.astype(float), k) == 1.0
    labelled = has_fwd & ~censor_label
    u = np.where(labelled, (np.nan_to_num(r5max, nan=-np.inf) >= x - 1).astype(float), np.nan)
    return {"U": u, "r5min": np.where(labelled, r5min, np.nan), "labelled": labelled, "censor_plan": censor_plan,
            "unit_resets": resets, "horizon": H, "threshold": x}


def d_label(lab: dict, market: str, evaluable: np.ndarray, proto: dict) -> tuple[np.ndarray, dict]:
    """D: min level ratio <= 1/threshold off IDX; on IDX rate-matched so P(D) = P(U) over the evaluable
    discovery ticker-days (the k-th smallest r5min, k = the U positives there), fixed once."""
    r5min, u = lab["r5min"], lab["U"]
    x = float(lab["threshold"])
    sel = evaluable & np.isfinite(u) & np.isfinite(r5min)
    if spec_market(market) == "IDX":
        k = int(np.nansum(u[sel]))
        vals = np.sort(r5min[sel])
        thr = float(vals[k - 1]) if k > 0 else -np.inf
        rule = "rate-matched"
    else:
        thr = 1.0 / x - 1.0
        rule = "fixed"
    d = np.where(np.isfinite(r5min), (np.nan_to_num(r5min, nan=np.inf) <= thr).astype(float), np.nan)
    n = int(sel.sum())
    info = {"rule": rule, "threshold_min_ratio_minus_1": thr if np.isfinite(thr) else None,
            "evaluable_ticker_days": n,
            "P_U": float(np.nansum(u[sel]) / n) if n else None, "P_D": float(np.nansum(d[sel]) / n) if n else None}
    return d, info


def known_features(f: dict) -> np.ndarray:
    out = np.ones(f[moonshot_e5.FEATURE_ORDER[0]].shape, dtype=bool)
    for k in moonshot_e5.FEATURE_ORDER:
        out &= np.isfinite(f[k])
    return out


def evaluable_mask(study: e1.Study, proto: dict, market: str, period: str, lab: dict) -> np.ndarray:
    """e1.Study.elig and the market's own period (t and t+H inside it), the debounce lead-in (column >=
    WARMUP of the study window), the label present and every feature column known."""
    mk = spec_market(market)
    start, end = get(proto, f"markets.{mk}.periods.{period}")
    H = int(lab["horizon"])
    dates = study.dates
    n_s = len(dates)
    in_period = (dates >= np.datetime64(start, "D")) & (dates <= np.datetime64(end, "D"))
    fwd_ok = np.zeros(n_s, dtype=bool)
    fwd_ok[: n_s - H] = dates[H:] <= np.datetime64(end, "D")
    lead_ok = np.arange(n_s) >= moonshot_e5.WARMUP
    cols = in_period & fwd_ok & lead_ok
    return study.elig[period] & cols[None, :] & lab["labelled"] & known_features(study.base_feats)


def constant_columns(f: dict, mask: np.ndarray) -> dict:
    """Per feature column, whether it is constant over the masked cells (its single value then)."""
    out = {}
    for k in moonshot_e5.FEATURE_ORDER:
        v = f[k][mask]
        if not len(v):
            out[k] = {"constant": None, "value": None}
            continue
        lo, hi = float(np.min(v)), float(np.max(v))
        out[k] = {"constant": bool(lo == hi), "value": lo if lo == hi else None}
    return out


# ------------------------------------------------------------------------------------------------ learner
def design(f: dict, n_idx: np.ndarray, d_idx: np.ndarray) -> np.ndarray:
    return np.column_stack([f[k][n_idx, d_idx] for k in moonshot_e5.FEATURE_ORDER])


def fit_logistic(X: np.ndarray, y: np.ndarray, w: np.ndarray, lam: float, iterations: int) -> dict:
    """L2 logistic regression by IRLS (Newton) from beta = 0, a fixed number of iterations, the ridge on
    the coefficients only; the linear predictor is clipped to [-30, 30] before the sigmoid. numpy only."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.asarray(w, dtype=float)
    if X.ndim != 2 or len(y) != len(X) or len(w) != len(X):
        raise ValueError("X, y and w must have one row per observation")
    if not (y == 1).any() or not (y == 0).any():
        raise ValueError("the fit needs both classes")
    n, p = X.shape
    Xa = np.hstack([np.ones((n, 1)), X])
    pen = float(lam) * np.eye(p + 1)
    pen[0, 0] = 0.0
    beta = np.zeros(p + 1)
    step = np.zeros(p + 1)
    for _ in range(int(iterations)):
        eta = np.clip(Xa @ beta, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-eta))
        grad = Xa.T @ (w * (y - mu)) - pen @ beta
        H = (Xa * (w * mu * (1 - mu))[:, None]).T @ Xa + pen
        step = np.linalg.solve(H, grad)
        beta = beta + step
    eta = np.clip(Xa @ beta, -30, 30)
    mu = 1.0 / (1.0 + np.exp(-eta))
    with np.errstate(divide="ignore", invalid="ignore"):
        ll = w * (y * np.log(mu) + (1 - y) * np.log(1 - mu))
    return {"intercept": float(beta[0]), "coef": [float(b) for b in beta[1:]], "iterations": int(iterations),
            "lambda": float(lam), "deviance": float(-2 * np.nansum(ll)), "max_abs_step_last": float(np.abs(step).max()),
            "converged": bool(np.abs(step).max() < 1e-8)}


def fit_label(f: dict, n_idx: np.ndarray, d_idx: np.ndarray, y: np.ndarray, learner: dict, name: str) -> dict:
    """One label's fit on the rows (n_idx, d_idx): all positives plus a seeded subsample of the negatives,
    floor(negative_subsample x negatives) drawn without replacement in row order, weighted."""
    y = np.asarray(y, dtype=float)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    if not len(pos) or not len(neg):
        raise ValueError(f"label {name}: {len(pos)} positives and {len(neg)} negatives; the fit needs both classes")
    rng = np.random.default_rng(int(learner["seed"]))
    n_sample = int(np.floor(len(neg) * float(learner["negative_subsample"])))
    chosen = np.sort(rng.choice(neg, size=n_sample, replace=False)) if n_sample else neg[:0]
    rows = np.sort(np.concatenate([pos, chosen]))
    weights = np.where(y[rows] == 1, 1.0, float(learner["negative_weight"]))
    lam = float(learner["lambda_per_row"]) * len(rows)
    fit = fit_logistic(design(f, n_idx[rows], d_idx[rows]), y[rows], weights, lam, int(learner["iterations"]))
    fit.update({"label": name, "n_rows_used": int(len(rows)), "n_positives": int(len(pos)),
                "n_negatives": int(len(neg)), "n_negatives_sampled": int(n_sample),
                "negative_weight": float(learner["negative_weight"]), "seed": int(learner["seed"]),
                "feature_order": list(moonshot_e5.FEATURE_ORDER)})
    return fit


def arm_scores(f: dict, model: dict) -> dict:
    s_u = moonshot_e5.score(f, model["coef_U"], model["intercept_U"])
    s_d = moonshot_e5.score(f, model["coef_D"], model["intercept_D"])
    return {"A": s_u, "B": s_u - s_d}


def threshold(score: np.ndarray, evaluable: np.ndarray, percentile: float) -> float:
    v = score[evaluable]
    v = v[np.isfinite(v)]
    if not len(v):
        raise ValueError("no evaluable ticker-day to fix a threshold on")
    return float(np.percentile(v, float(percentile)))


def harness_mask(flags: np.ndarray, m: Market) -> np.ndarray:
    """Flags as the harness signals them: tradeable sessions from column WARMUP on."""
    out = np.asarray(flags, dtype=bool) & m.tradeable
    out[:, : moonshot_e5.WARMUP] = False
    return out


def arm_flags(score: np.ndarray, thr: float, m: Market) -> np.ndarray:
    return harness_mask(moonshot_e5.flags(score, thr), m)


def detector_flags(f: dict, m: Market) -> dict:
    known = np.isfinite(f["quiet"])
    return {name: harness_mask(moonshot_e5.debounce(state, known), m)
            for name, state in moonshot_e5.detector_states(f).items()}


def e1_threshold_key(study: e1.Study, ratio: float) -> float:
    """The e1.Study THRESHOLDS key (a return, 0.30) for a level ratio (1.30)."""
    want = ratio - 1.0
    key = min(study.start, key=lambda k: abs(k - want))
    if abs(key - want) > 1e-9:
        raise ValueError(f"e1.Study has no event threshold for a {ratio} level ratio (has {sorted(study.start)})")
    return key


def auc(score: np.ndarray, y: np.ndarray) -> float | None:
    """P(score of a positive > score of a negative) + 0.5 P(tie), rank-based (average ties)."""
    ok = np.isfinite(score) & np.isfinite(y)
    s, t = score[ok], y[ok]
    n_pos, n_neg = int((t == 1).sum()), int((t == 0).sum())
    if not n_pos or not n_neg:
        return None
    ranks = pd.Series(s).rank(method="average").to_numpy()
    return float((ranks[t == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


# ----------------------------------------------------------------------------------------- plan window
def plan_window_return(m: Market, entry_price: str, holding: int) -> np.ndarray:
    """The fill-independent return on the reference chain of a flag at column t: entry level at the close
    of t+1 (entry_price "close") or at level(t+1) x open(t+1)/close(t+1) ("open"), exit level at the close
    of session t+1+holding; NaN where either is missing."""
    L = reference_level(m)
    entry = _lead(L, 1)
    if entry_price == "open":
        with np.errstate(divide="ignore", invalid="ignore"):
            opens = np.where(np.nan_to_num(m.open) > 0, m.open, np.nan)
            entry = entry * _lead(opens, 1) / _lead(m.close, 1)
    exit_ = _lead(L, 1 + int(holding))
    with np.errstate(divide="ignore", invalid="ignore"):
        r = exit_ / entry - 1
    return np.where(np.isfinite(r), r, np.nan)


# ------------------------------------------------------------------------------- detection controls
def flag_cells(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Flag cells in (session, ticker-index) order."""
    n_idx, d_idx = np.nonzero(mask)
    order = np.lexsort((n_idx, d_idx))
    return n_idx[order], d_idx[order]


def detection_draws(study: e1.Study, n_idx: np.ndarray, d_idx: np.ndarray, evaluable: np.ndarray, draws: int,
                    seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Matched controls per flag: e1.Study._pool (the protocol's pool keys, relaxed from the last to
    N_CONTROLS), `draws` draws with replacement from one generator in flag order; (draws, k) and the
    relaxation level per flag. A flag whose pool is empty draws itself (reported by level -1)."""
    out = np.empty((int(draws), len(n_idx)), dtype=np.int64)
    level = np.empty(len(n_idx), dtype=np.int64)
    rng = np.random.default_rng(int(seed))
    for j, (n, d) in enumerate(zip(n_idx, d_idx)):
        pool, lv = study._pool(int(n), int(d), evaluable)
        if not len(pool):
            pool, lv = np.array([n]), -1
        level[j] = lv
        out[:, j] = rng.choice(pool, size=int(draws), replace=True)
    return out, level


def _cluster_index(keys: np.ndarray) -> tuple[np.ndarray, int]:
    _, inv = np.unique(np.asarray(keys).astype(str), return_inverse=True)
    return inv, (int(inv.max()) + 1 if len(inv) else 0)


def ratio_bootstrap(num: np.ndarray, den: np.ndarray, clusters: np.ndarray, resamples: int, seed: int) -> dict:
    """Cluster bootstrap of sum(num)/sum(den) over clusters (sessions): the 95% interval. Resamples in
    fixed chunks of 1000 so the stream does not depend on memory."""
    ok = np.isfinite(num) & np.isfinite(den)
    num, den = num[ok], den[ok]
    inv, k = _cluster_index(np.asarray(clusters)[ok])
    if k == 0:
        return {"ratio": None, "ci95": None, "n_clusters": 0}
    s_num, s_den = np.bincount(inv, weights=num, minlength=k), np.bincount(inv, weights=den, minlength=k)
    point = float(s_num.sum() / s_den.sum()) if s_den.sum() else None
    rng = np.random.default_rng(int(seed))
    vals = np.empty(int(resamples))
    chunk = 1000
    with np.errstate(divide="ignore", invalid="ignore"):
        for i in range(0, int(resamples), chunk):
            idx = rng.integers(0, k, size=(min(chunk, int(resamples) - i), k))
            vals[i:i + len(idx)] = s_num[idx].sum(axis=1) / s_den[idx].sum(axis=1)
    fin = vals[np.isfinite(vals)]
    ci = [float(np.percentile(fin, 2.5)), float(np.percentile(fin, 97.5))] if len(fin) else None
    return {"ratio": point, "ci95": ci, "n_clusters": int(k), "resamples_finite": int(len(fin))}


def _label_stats(hit: np.ndarray, ctrl: np.ndarray, base: float, sessions: np.ndarray, resamples: int,
                 seed: int) -> dict:
    """Precision of the flags with Wilson bounds, lift vs base, the matched-control draw distribution
    (e1.evaluate's convention: portfolio means of the draws, one-sided p) and a session-cluster CI of the
    lift vs matched (ratio of flag hits to control-mean hits)."""
    n = int(len(hit))
    k = int(np.nansum(hit))
    lo, hi = wilson(k, n)
    precision = k / n if n else None
    port = ctrl.mean(axis=1) if n else np.array([np.nan])  # (draws,): mean hit rate of each control portfolio
    matched = float(np.nanmean(port)) if n else None
    lift = ratio_bootstrap(hit, ctrl.mean(axis=0), sessions, resamples, seed) if n else {"ratio": None, "ci95": None}
    return {"flags": n, "hits": k, "precision": precision, "precision_lo95": None if n == 0 else float(lo),
            "precision_hi95": None if n == 0 else float(hi), "base_rate": float(base),
            "lift_vs_base": (precision / base) if n and base else None,
            "matched_random_mean": matched,
            "matched_random_p2_5": float(np.nanpercentile(port, 2.5)) if n else None,
            "matched_random_p97_5": float(np.nanpercentile(port, 97.5)) if n else None,
            "lift_vs_matched": (precision / matched) if n and matched else None,
            "lift_vs_matched_ci95": lift["ci95"],
            "p_one_sided_vs_matched": float((1 + (port >= precision).sum()) / (1 + len(port))) if n else None}


def paired_frame(dates: np.ndarray, outcome: np.ndarray, ctrl: np.ndarray, cluster: str) -> pd.DataFrame:
    """A trades-shaped frame for backtest.paired_excess: the flag outcome and the mean outcome of its
    finite control draws (NaN when none is finite)."""
    fin = np.isfinite(ctrl)
    n_fin = fin.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(fin, ctrl, 0.0).sum(axis=0) / n_fin
    return pd.DataFrame({cluster: np.asarray(dates).astype(str), "net_return": np.asarray(outcome, dtype=float),
                         "matched_mean_net_return": np.where(n_fin > 0, mean, np.nan)})


def flag_block(study: e1.Study, lab: dict, d_arr: np.ndarray, f: dict, r_plan: np.ndarray, n_idx: np.ndarray,
               d_idx: np.ndarray, draws: np.ndarray, level: np.ndarray, evaluable: np.ndarray, years: list[int],
               proto: dict, market: str) -> dict:
    """Every Stage-1 statistic of one flag set: E30 and D30 blocks, the directional ratio, the plan-window
    paired excess with per-year means, the pre-move split and (IDX) the split by ARB regime."""
    ps = get(proto, "matched_controls.paired_statistic")
    resamples, seed, cluster = int(ps["resamples"]), int(ps["seed"]), str(ps["cluster"])
    u = lab["U"]
    dates = study.dates[d_idx]
    years_of_flags = study.dates.astype("datetime64[Y]").astype(int)[d_idx] + 1970
    base_u = float(np.nanmean(u[evaluable])) if evaluable.any() else float("nan")
    base_d = float(np.nanmean(d_arr[evaluable])) if evaluable.any() else float("nan")
    hit_u, hit_d = u[n_idx, d_idx], d_arr[n_idx, d_idx]
    ctrl_u, ctrl_d = u[draws, d_idx[None, :]], d_arr[draws, d_idx[None, :]]
    rf, rc = r_plan[n_idx, d_idx], r_plan[draws, d_idx[None, :]]
    frame = paired_frame(dates, rf, rc, cluster)
    paired = paired_excess(frame, resamples=resamples, seed=seed, cluster=cluster)
    excess = (frame["net_return"] - frame["matched_mean_net_return"]).to_numpy()
    by_year = {}
    for y in years:
        sel = years_of_flags == y
        ex = excess[sel]
        ex = ex[np.isfinite(ex)]
        by_year[str(y)] = {"flags": int(sel.sum()), "flags_with_return": int(len(ex)),
                           "mean_excess": float(ex.mean()) if len(ex) else None,
                           "n_clusters": int(len(np.unique(dates[sel][np.isfinite(excess[sel])])))}
    with np.errstate(divide="ignore", invalid="ignore"):
        matched_ratio = float(np.nansum(ctrl_u) / np.nansum(ctrl_d)) if len(n_idx) and np.nansum(ctrl_d) else None
    out = {
        "flags": int(len(n_idx)), "sessions_with_flag": int(len(np.unique(d_idx))),
        "distinct_names": int(len(np.unique(n_idx))),
        "match_level_used": {str(int(v)): int((level == v).sum()) for v in np.unique(level)} if len(level) else {},
        "E30": _label_stats(hit_u, ctrl_u, base_u, dates, resamples, seed),
        "D30": _label_stats(hit_d, ctrl_d, base_d, dates, resamples, seed),
        "directional_ratio": {**ratio_bootstrap(hit_u, hit_d, dates, resamples, seed), "matched_ratio": matched_ratio},
        "plan_window": {"flags_with_return": int(paired["n"]),
                        "mean_return_flags": float(np.nanmean(rf)) if np.isfinite(rf).any() else None,
                        "mean_return_matched": float(np.nanmean(rc)) if np.isfinite(rc).any() else None,
                        "paired": paired},
        "by_year": by_year,
    }
    split = float(get(proto, "stages.1_information.pre_move_split_ret1"))
    ret1 = f["ret1"][n_idx, d_idx]
    out["pre_move_split"] = {}
    for name, sel in (("ret1_below", np.nan_to_num(ret1, nan=-np.inf) < split),
                      ("ret1_at_or_above", np.nan_to_num(ret1, nan=-np.inf) >= split)):
        sub = paired_excess(frame[sel], resamples=resamples, seed=seed, cluster=cluster) if sel.any() else None
        out["pre_move_split"][name] = {
            "flags": int(sel.sum()),
            "E30": _label_stats(hit_u[sel], ctrl_u[:, sel], base_u, dates[sel], resamples, seed) if sel.any() else None,
            "paired": sub}
    if spec_market(market) == "IDX":
        reg = regime_index(study.dates[d_idx]) if len(d_idx) else np.array([], dtype=int)
        out["by_regime"] = {}
        for r in np.unique(reg):
            sel = reg == r
            out["by_regime"][REGIMES[int(r)].label] = {
                "flags": int(sel.sum()),
                "E30_precision": float(np.nanmean(hit_u[sel])), "D30_precision": float(np.nanmean(hit_d[sel])),
                "paired": paired_excess(frame[sel], resamples=resamples, seed=seed, cluster=cluster)}
    return out


def stage1_gate(block: dict, proto: dict, years: list[int]) -> dict:
    """The gate to Stage 2: flags >= min_flags, paired plan-window excess > 0 with cluster p < alpha, mean
    excess > 0 in every discovery year with >= min_flags_per_year flags; NOT judged when n_clusters < 2."""
    g = get(proto, "stages.1_information.gate_to_stage_2")
    reasons, judged = [], True
    if block["flags"] < int(g["min_flags"]):
        reasons.append(f"flags {block['flags']} < {g['min_flags']}")
    paired = block["plan_window"]["paired"]
    if paired["n_clusters"] < 2:
        judged = False
        reasons.append(f"not judged: {paired['n_clusters']} signal-session clusters (< 2)")
    else:
        if not (paired["mean_excess"] is not None and paired["mean_excess"] > 0):
            reasons.append(f"paired plan-window excess {paired['mean_excess']} not positive")
        if not (paired["p_one_sided"] is not None and paired["p_one_sided"] < float(g["alpha"])):
            reasons.append(f"cluster-bootstrap p {paired['p_one_sided']} not below {g['alpha']}")
    for y in years:
        yr = block["by_year"].get(str(y), {})
        if yr.get("flags", 0) >= int(g["min_flags_per_year"]) and not (yr.get("mean_excess") or 0) > 0:
            reasons.append(f"mean excess in {y} not positive ({yr.get('flags')} flags)")
    return {"judged": judged, "passed": bool(judged and not reasons), "reasons": reasons}


def a1_gate(block: dict, proto: dict) -> dict:
    g = get(proto, "stages.1_information.a1_gate")
    e30 = block["E30"]
    lift, p = e30.get("lift_vs_matched"), e30.get("p_one_sided_vs_matched")
    reasons = []
    if lift is None or not lift >= float(g["min_lift"]):
        reasons.append(f"lift vs matched {lift} below {g['min_lift']}")
    if p is None or not p < float(g["max_p"]):
        reasons.append(f"p vs matched {p} not below {g['max_p']}")
    return {"passed": not reasons, "reasons": reasons,
            "lift_ci95_excludes_1": bool(e30["lift_vs_matched_ci95"] and e30["lift_vs_matched_ci95"][0] > 1.0)}


# ------------------------------------------------------------------------------------- univariate table
def univariate_table(study: e1.Study, lab: dict, f: dict, evaluable: np.ndarray, proto: dict) -> pd.DataFrame:
    """Per ranked / binary feature on discovery: the matched-set AUC of U-episode starts against their
    matched non-event controls (E1 signal_stats, bootstrap over events) and the feature's own debounced
    top-share flag: E30 precision, lift vs base and vs matched controls."""
    uv = get(proto, "stages.1_information.univariate")
    det = get(proto, "matched_controls.detection_stage")
    m = study.m
    u = lab["U"]
    key = e1_threshold_key(study, float(lab["threshold"]))
    n_ev, d_ev = flag_cells(evaluable & study.start[key])
    non_event = ~study.qraw[key]
    k_ctrl = int(uv["controls_per_event"])
    ctrl = np.full((len(n_ev), k_ctrl), -1, dtype=np.int64)
    for i, (n, d) in enumerate(zip(n_ev, d_ev)):
        pool, _ = study._pool(int(n), int(d), evaluable, non_event)
        rng = np.random.default_rng(int(uv["controls_seed"]) + i)
        chosen = rng.choice(pool, size=min(k_ctrl, len(pool)), replace=False) if len(pool) else pool
        ctrl[i, : len(chosen)] = np.sort(chosen)
    rng = np.random.default_rng(int(uv["auc_seed"]))
    boot_n = int(uv["auc_bootstrap"])
    pct = 100.0 * (1.0 - float(uv["top_share"]))
    base = float(np.nanmean(u[evaluable])) if evaluable.any() else float("nan")
    rows = []
    for name in moonshot_e5.RANKED + moonshot_e5.BINARY:
        ev = f[name][n_ev, d_ev] if len(n_ev) else np.array([])
        cv = np.where(ctrl >= 0, f[name][np.maximum(ctrl, 0), d_ev[:, None]], np.nan) if len(n_ev) else np.empty((0, k_ctrl))
        with np.errstate(invalid="ignore"):
            fin = np.isfinite(cv) & np.isfinite(ev)[:, None]
            scores = ((ev[:, None] > cv) & fin).sum(axis=1) + 0.5 * ((ev[:, None] == cv) & fin).sum(axis=1)
            counts = fin.sum(axis=1)
        used = np.flatnonzero(counts > 0)
        auc_ = float(scores[used].sum() / counts[used].sum()) if len(used) else None
        boots = np.full(boot_n, np.nan)
        for b in range(boot_n):
            if len(used):
                idx = rng.choice(used, size=len(used), replace=True)
                boots[b] = scores[idx].sum() / counts[idx].sum()
        if name in moonshot_e5.RANKED:
            rank = f[name + "_r"]
            thr = threshold(rank, evaluable, pct)
            flags = arm_flags(rank, thr, m)
        else:
            thr = 1.0
            flags = harness_mask(moonshot_e5.debounce(f[name] == 1.0, np.isfinite(f[name])), m)
        n_fl, d_fl = flag_cells(flags & evaluable)
        draws, _ = detection_draws(study, n_fl, d_fl, evaluable, int(det["draws"]), int(det["seed"]))
        ps = get(proto, "matched_controls.paired_statistic")
        stats = _label_stats(u[n_fl, d_fl], u[draws, d_fl[None, :]], base, study.dates[d_fl], int(ps["resamples"]),
                             int(ps["seed"]))
        rows.append({"feature": name, "kind": "ranked" if name in moonshot_e5.RANKED else "binary",
                     "events": int(len(n_ev)), "events_with_value": int(np.isfinite(ev).sum()),
                     "controls_with_value": int(np.isfinite(cv).sum()),
                     "event_median": float(np.nanmedian(ev)) if np.isfinite(ev).any() else None,
                     "control_median": float(np.nanmedian(cv)) if np.isfinite(cv).any() else None,
                     "auc": auc_, "auc_lo95": float(np.nanpercentile(boots, 2.5)) if np.isfinite(boots).any() else None,
                     "auc_hi95": float(np.nanpercentile(boots, 97.5)) if np.isfinite(boots).any() else None,
                     "flag_threshold": thr, "flags": stats["flags"], "E30_hits": stats["hits"],
                     "E30_precision": stats["precision"], "E30_precision_lo95": stats["precision_lo95"],
                     "E30_base": base, "lift_vs_base": stats["lift_vs_base"],
                     "matched_random_mean": stats["matched_random_mean"], "lift_vs_matched": stats["lift_vs_matched"],
                     "lift_vs_matched_lo95": (stats["lift_vs_matched_ci95"] or [None, None])[0],
                     "lift_vs_matched_hi95": (stats["lift_vs_matched_ci95"] or [None, None])[1],
                     "p_one_sided_vs_matched": stats["p_one_sided_vs_matched"]})
    return pd.DataFrame(rows)


# -------------------------------------------------------------------------------------- harness (stage 2)
def harness_config(proto: dict, market: str, rule_id: str, start: str, end: str, overrides: dict | None = None,
                   ) -> RunConfig:
    """The market plan (plans.<MARKET>.primary) with `overrides` (a sensitivity) as a RunConfig on the
    window start..end; the window end is checked against the validation end first."""
    h = get(proto, "harness")
    base = dict(get(proto, f"plans.{market}.primary"))
    base.update(overrides or {})
    run_market = base.pop("market")
    assert_within_validation(proto, run_market, end)
    return RunConfig(
        rule_id=rule_id, market=run_market, start=str(start), end=str(end),
        holding_days=int(base["holding_days"]), entry_rule=base["entry_rule"], entry_window=int(base["entry_window"]),
        exit_rule=base["exit_rule"], entry_lag=int(h["entry_lag"]), notional=float(base["notional"]),
        max_participation=float(base["max_participation"]), fee_buy=float(base["fee_buy"]),
        fee_sell=float(base["fee_sell"]), overlap=h["overlap"], random_draws=int(h["random_draws"]),
        seed=int(h["seed"]), data_end_exit=h["data_end_exit"], ca_mode=base["ca_mode"],
        lookahead_cuts=h["lookahead_cuts"], controls_version=base.get("controls_version", h["controls_version"]),
        units=base["units"], fill_model=base["fill_model"], quarantine=base["quarantine"],
        jump_ratio=base["jump_ratio"], tick_cost=bool(base.get("tick_cost", False)),
    )


def run_summary_path(out: Path, run_market: str, name: str, spec_id: str) -> Path:
    """Where a Stage-2 harness summary goes: <stage>/runs/<RunConfig market>/<arm>_<run>.json, so a
    sensitivity profile (CRYPTO_CLOSE) is keyed by its own name inside the market's stage directory."""
    path = out / "runs" / run_market / f"{name}_{spec_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def run_specs(proto: dict, market: str) -> list[dict]:
    """The harness runs of one arm: the primary, every pre-registered sensitivity, the v2-controls report."""
    specs = [{"id": "primary", "overrides": {}, "judged": True}]
    specs += [{"id": s["id"], "overrides": dict(s["overrides"]), "judged": bool(s["judged"])}
              for s in get(proto, f"plans.{market}.sensitivities")]
    specs.append({"id": "controls_" + get(proto, "harness.controls_version_reported"),
                  "overrides": {"controls_version": get(proto, "harness.controls_version_reported")}, "judged": False})
    return specs


def _with_entry(table: tuple, market: str, value) -> tuple:
    value = tuple(float(v) for v in value) if isinstance(value, (list, tuple)) else (None if value is None else float(value))
    return tuple((mk, value if mk == market else v) for mk, v in table)


@contextlib.contextmanager
def literals_from(model: dict, market: str):
    """The market's model.json values in the module's literal tables for the duration of the block (the
    Stage-2 harness runs, before the freeze); restored afterwards. The module source, hence the rule
    hash, is untouched: every row records literals_sha256 of the model file instead."""
    saved = {k: getattr(moonshot_e5, k) for k in LITERAL_TABLES}
    try:
        for table, key in MODEL_KEYS.items():
            setattr(moonshot_e5, table, _with_entry(saved[table], market, model[key]))
        yield
    finally:
        for k, v in saved.items():
            setattr(moonshot_e5, k, v)


def exit_participation(trades: pd.DataFrame, volume: pd.Series) -> np.ndarray:
    """Exit shares (shares x share factor, panel units) over the exit session's panel volume; NaN for
    unscored trades or an unknown volume."""
    scored = trades["status"].isin(SCORED_STATUS).to_numpy()
    out = np.full(len(trades), np.nan)
    if not scored.any():
        return out
    sub = trades.loc[scored]
    idx = pd.MultiIndex.from_arrays([sub["ticker"].astype(str).to_numpy(),
                                     pd.to_datetime(sub["exit_date"]).to_numpy().astype("datetime64[ns]")])
    vol = volume.reindex(idx).to_numpy(dtype=float)
    shares = sub["shares"].to_numpy(dtype=float) * sub["share_factor"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out[scored] = np.where(vol > 0, shares / vol, np.nan)
    return out


def volume_series(panel_df: pd.DataFrame) -> pd.Series:
    s = pd.Series(panel_df["volume"].to_numpy(dtype=float),
                  index=pd.MultiIndex.from_arrays([panel_df["ticker"].astype(str).to_numpy(),
                                                   panel_df["date"].to_numpy().astype("datetime64[ns]")]))
    return s[~s.index.duplicated(keep="first")]


def breakeven_precision(trades: pd.DataFrame, u_of: pd.Series) -> dict:
    """In-flag break-even precision p* = (matched - E[net | not E30]) / (E[net | E30] - E[net | not E30])
    over the scored trades (E30 = the U label of the signal session); descriptive."""
    scored = trades["status"].isin(SCORED_STATUS).to_numpy()
    sub = trades.loc[scored]
    if not len(sub):
        return {"scored": 0, "p_star": None}
    idx = pd.MultiIndex.from_arrays([sub["ticker"].astype(str).to_numpy(), sub["signal_date"].astype(str).to_numpy()])
    u = u_of.reindex(idx).to_numpy(dtype=float)
    net = sub["net_return"].to_numpy(dtype=float)
    matched = sub["matched_mean_net_return"].to_numpy(dtype=float)
    ok = np.isfinite(u) & np.isfinite(net)
    hit, miss = net[ok & (u == 1)], net[ok & (u == 0)]
    e_hit = float(hit.mean()) if len(hit) else None
    e_miss = float(miss.mean()) if len(miss) else None
    mm = float(np.nanmean(matched)) if np.isfinite(matched).any() else None
    p_star = None
    if e_hit is not None and e_miss is not None and mm is not None and e_hit != e_miss:
        p_star = float((mm - e_miss) / (e_hit - e_miss))
    return {"scored": int(len(sub)), "labelled": int(ok.sum()), "E30_share": float(np.nanmean(u[ok])) if ok.any() else None,
            "net_given_E30": e_hit, "net_given_not_E30": e_miss, "matched_mean_net": mm, "p_star": p_star}


def u_lookup(m: Market, H: int, x: float) -> pd.Series:
    """U per (ticker, signal date) on a harness window: max level(t+1..t+H)/level(t) >= x, NaN where no
    forward session exists inside the window."""
    L = reference_level(m)
    ahead = np.stack([_lead(L, k) for k in range(1, H + 1)])
    with np.errstate(divide="ignore", invalid="ignore"):
        ratios = ahead / L[None]
    fin = np.isfinite(ratios)
    has = fin.any(axis=0)
    rmax = np.where(has, np.nanmax(np.where(fin, ratios, -np.inf), axis=0), np.nan)
    u = np.where(has, (rmax >= x).astype(float), np.nan)
    n_idx, d_idx = np.nonzero(has)
    return pd.Series(u[n_idx, d_idx], index=pd.MultiIndex.from_arrays([m.tickers[n_idx].astype(str),
                                                                        m.dates[d_idx].astype(str)]))


def subset_row(trades: pd.DataFrame, keep: np.ndarray, years: list[int], proto: dict) -> dict:
    """The exit-capacity subset of a run's scored trades as an admissibility row: scored, average net,
    per-year averages and the paired net statistic (which stands in for the harness p on a subset)."""
    ps = get(proto, "matched_controls.paired_statistic")
    sub = trades.loc[keep & trades["status"].isin(SCORED_STATUS).to_numpy()]
    net = sub["net_return"].to_numpy(dtype=float)
    paired = paired_excess(sub, resamples=int(ps["resamples"]), seed=int(ps["seed"]), cluster=str(ps["cluster"]))
    row = {"scored": int(len(sub)), "avg_net_return": float(net.mean()) if len(net) else None,
           "p_one_sided_vs_matched": paired["p_one_sided"], "paired_net_n_clusters": paired["n_clusters"],
           "paired_net_mean_excess": paired["mean_excess"]}
    yrs = pd.to_datetime(sub["signal_date"]).dt.year.to_numpy() if len(sub) else np.array([], dtype=int)
    for y in years:
        sel = yrs == y
        row[f"scored_{y}"] = int(sel.sum())
        row[f"avg_net_return_{y}"] = float(net[sel].mean()) if sel.any() else None
    return row


def harness_row(summary: dict, trades: pd.DataFrame, arm: str, spec: dict, plan: dict, years: list[int],
                proto: dict, volume: pd.Series | None, u_of: pd.Series | None, literals_sha: str | None) -> dict:
    """One plans.csv row: e3.plan_row of the harness summary plus the run's settings, the paired net
    statistic, the exit-capacity subset and the break-even bound."""
    ps = get(proto, "matched_controls.paired_statistic")
    row = plan_row(summary, arm, plan, years)
    cfg = summary["config"]
    row.update({"arm": arm, "run": spec["id"], "judged": bool(spec["judged"]), "market_profile": cfg["market"],
                "fill_model": cfg.get("fill_model"), "units": cfg.get("units"), "quarantine": cfg.get("quarantine"),
                "controls_version": cfg["controls_version"], "fee_buy": cfg["fee_buy"], "fee_sell": cfg["fee_sell"],
                "max_participation": cfg["max_participation"], "tick_cost": cfg.get("tick_cost", False),
                "jump_ratio": cfg.get("jump_ratio"), "lookahead_mode": summary["lookahead_check"]["mode"],
                "window_start": summary["config"]["start"], "window_end": summary["config"]["end"],
                "literals_sha256": literals_sha})
    scored = trades["status"].isin(SCORED_STATUS).to_numpy()
    gross = trades.loc[scored, "gross_return"].to_numpy(dtype=float)
    row["avg_gross_return"] = float(gross.mean()) if len(gross) else None
    matched = row.get("matched_random_avg_net_return")
    row["rule_minus_matched"] = (row["avg_net_return"] - matched) if (row["avg_net_return"] is not None
                                                                     and matched is not None) else None
    paired = paired_excess(trades, resamples=int(ps["resamples"]), seed=int(ps["seed"]), cluster=str(ps["cluster"]))
    for k in ("n", "n_clusters", "mean_excess", "p_one_sided"):
        row[f"paired_net_{k}"] = paired[k]
    row["paired_net_ci95_lo"], row["paired_net_ci95_hi"] = paired["ci95"] or (None, None)
    if volume is not None:
        part = exit_participation(trades, volume)
        cap = float(get(proto, "stages.2_execution.exit_participation_max"))
        keep = np.nan_to_num(part, nan=np.inf) <= cap
        row["exit_participation_median"] = float(np.nanmedian(part)) if np.isfinite(part).any() else None
        row["exit_participation_share_above"] = float((np.nan_to_num(part, nan=-1) > cap).mean()) if scored.any() else None
        for k, v in subset_row(trades, keep, years, proto).items():
            row[f"exit_subset_{k}"] = v
    if u_of is not None:
        row.update({f"breakeven_{k}": v for k, v in breakeven_precision(trades, u_of).items()})
    return row


def admissibility_stage2(primary: dict, sensitivities: list[dict], proto: dict, years: list[int]) -> dict:
    """Stage-2 admissibility: e3.admissibility verbatim on the primary row, the paired net excess (p <
    alpha_paired_net, not judged under 2 clusters), every judged sensitivity's rule-minus-matched > 0, and
    the same rule on the exit-capacity subset (prefixed exit_subset_ fields of the primary row)."""
    s2 = get(proto, "stages.2_execution")
    alpha = float(s2["alpha_paired_net"])
    sel = get(proto, "selection")
    reasons = list(e3.admissibility(primary, proto, years))
    judged = True
    if (primary.get("paired_net_n_clusters") or 0) < 2:
        judged = False
        reasons.append(f"not judged: {primary.get('paired_net_n_clusters')} signal-session clusters (< 2)")
    else:
        if not ((primary.get("paired_net_mean_excess") or 0) > 0):
            reasons.append(f"paired net excess {primary.get('paired_net_mean_excess')} not positive")
        p = primary.get("paired_net_p_one_sided")
        if p is None or not p < alpha:
            reasons.append(f"paired net p {p} not below {alpha}")
    for s in sensitivities:
        if not s.get("judged", True):
            continue
        d = s.get("rule_minus_matched")
        if d is None or not d > 0:
            reasons.append(f"sensitivity {s.get('run')}: rule minus matched {d} not positive")
    if "exit_subset_scored" in primary:
        sub = {k[len("exit_subset_"):]: v for k, v in primary.items() if k.startswith("exit_subset_")}
        if sub["scored"] < int(sel["min_scored"]):
            reasons.append(f"exit-capacity subset: scored {sub['scored']} < {sel['min_scored']}")
        if sub["avg_net_return"] is None or not sub["avg_net_return"] > 0:
            reasons.append("exit-capacity subset: average net return not positive")
        if (sub.get("paired_net_n_clusters") or 0) < 2:
            judged = False
            reasons.append("exit-capacity subset: not judged (< 2 clusters)")
        elif sub["p_one_sided_vs_matched"] is None or not sub["p_one_sided_vs_matched"] < alpha:
            reasons.append(f"exit-capacity subset: paired net p {sub['p_one_sided_vs_matched']} not below {alpha}")
        for y in years:
            n, a = sub.get(f"scored_{y}", 0), sub.get(f"avg_net_return_{y}")
            if n >= int(sel["min_scored_per_year"]) and (a is None or not a > 0):
                reasons.append(f"exit-capacity subset: average net return in {y} not positive ({n} scored)")
    else:
        reasons.append("exit-capacity subset missing")
    return {"judged": judged, "admissible": bool(judged and not reasons), "reasons": reasons}


def select_arm(adm: dict, rows: dict, market: str, proto: dict) -> str | None:
    """SELECTED for the market: its primary arm when admissible, else the admissible arm with the larger
    paired net mean excess on the primary run, ties to A; None when nothing is admissible."""
    ok = [a for a in ARMS if adm.get(a, {}).get("admissible")]
    if not ok:
        return None
    primary = get(proto, f"markets.{spec_market(market)}.primary_arm")
    if primary in ok:
        return primary
    ok.sort(key=lambda a: (-(rows[a].get("paired_net_mean_excess") or 0.0), ARMS.index(a)))
    return ok[0]


# ---------------------------------------------------------------------------------------- stage 3 freeze
def _format_table(name: str, entries) -> list[str]:
    lines = [f"{name} = ("]
    for mk, val in entries:
        if val is None:
            lines.append(f"    ({mk!r}, None),")
        elif isinstance(val, (list, tuple)):
            body = ", ".join(repr(float(v)) for v in val) + ","
            lines.append(f"    ({mk!r}, (")
            lines += [f"        {w}" for w in textwrap.wrap(body, width=100, break_long_words=False,
                                                            break_on_hyphens=False)]
            lines.append("    )),")
        else:
            lines.append(f"    ({mk!r}, {float(val)!r}),")
    lines.append(")")
    return lines


def module_literals(source: str) -> dict:
    """The literal tables and SELECTED of a moonshot_e5 source text, with the line span of each."""
    tree = ast.parse(source)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in LITERAL_TABLES + ("SELECTED",):
                out[name] = {"value": ast.literal_eval(node.value), "lineno": node.lineno, "end_lineno": node.end_lineno}
    missing = [n for n in LITERAL_TABLES + ("SELECTED",) if n not in out]
    if missing:
        raise ValueError(f"module source has no literal {missing}")
    return out


def freeze_source(source: str, model: dict, market: str, selected_arm: str | None) -> str:
    """The module source with the market's model.json values written into its literal tables and
    (market, selected_arm) added to SELECTED. Refuses when any of the market's literals is already set or
    the market is already in SELECTED."""
    lits = module_literals(source)
    for table in LITERAL_TABLES:
        if dict(lits[table]["value"]).get(market) is not None:
            raise RuntimeError(f"{table} already carries literals for {market}: the freeze refuses to overwrite them")
    selected = lits["SELECTED"]["value"]
    if selected is not None and any(mk == market for mk, _ in selected):
        raise RuntimeError(f"SELECTED already names {market}")
    lines = source.splitlines()
    edits = []
    for table, key in MODEL_KEYS.items():
        entries = _with_entry(tuple(lits[table]["value"]), market, model[key])
        edits.append((lits[table]["lineno"], lits[table]["end_lineno"], _format_table(table, entries)))
    if selected_arm is not None:
        new_sel = tuple(selected or ()) + ((market, selected_arm),)
        text = "SELECTED = (" + ", ".join(f"({mk!r}, {arm!r})" for mk, arm in new_sel) + ",)"
        edits.append((lits["SELECTED"]["lineno"], lits["SELECTED"]["end_lineno"],
                      [text + "  # frozen after discovery: ((market, arm), ...)"]))
    for lineno, end, new in sorted(edits, key=lambda e: -e[0]):
        lines[lineno - 1: end] = new
    return "\n".join(lines) + "\n"


def check_frozen(model: dict, market: str, module=None) -> list[str]:
    """Why the module's literals for `market` are not discovery/model.json's; empty when they are."""
    module = module or moonshot_e5
    out = []
    for table, key in MODEL_KEYS.items():
        have = dict(getattr(module, table)).get(market)
        want = model[key]
        if have is None:
            out.append(f"{table}[{market}] is None")
        elif isinstance(want, (list, tuple)):
            if len(have) != len(want) or any(float(a) != float(b) for a, b in zip(have, want)):
                out.append(f"{table}[{market}] differs from model.json")
        elif float(have) != float(want):
            out.append(f"{table}[{market}] {have} != model.json {want}")
    return out


def load_module_from(path: Path):
    """A moonshot_e5 source file as a module of the idxsig.rules package (its `from . import Rule` and its
    `sys.modules[__name__]` resolve), under a name of its own so the real module is never replaced."""
    name = f"idxsig.rules._e5_frozen_check_{next(_LOAD_COUNTER)}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------------------------------- stamps, io
def _stamp(proto_sha: str, proto: dict, market: str, stage: str, meta: dict, registry=None) -> dict:
    return {"protocol_id": proto["protocol_id"], "protocol_sha256": proto_sha,
            "frozen_before_analysis": bool(proto["frozen_before_analysis"]), "market": market, "stage": stage,
            "computed_at": _now(), "panel_sha256": meta["sha256"], "panel_manifest": meta.get("_manifest"),
            "panel_format": meta.get("format"), "registry_sha256": registry[1]["sha256"] if registry else None,
            "detector_module_sha256": sha256_file(MODULE_PATH), "code": code_state(), "runtime": _runtime(),
            "search_size": proto["search_size"], "claims": proto["claims"],
            "holdout": "sealed: never loaded; every window end is checked against the validation end before a "
                       "Study or RunConfig exists, and the harness refuses it again"}


def check_panel(proto: dict, market: str, meta: dict) -> None:
    mk = spec_market(market)
    want = get(proto, f"markets.{mk}.panel_sha256")
    if meta["sha256"] != want:
        raise RuntimeError(f"the loaded {mk} panel {meta['sha256'][:12]} is not the protocol's {want[:12]}")


# ---------------------------------------------------------------------------------------- stage 0
def _same_fact(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return a == b if not isinstance(a, float) else abs(a - b) < 1e-12


def reproduce_status(want: dict, got: dict, fields: list[str], dev: dict) -> tuple[bool, str, str]:
    """(rule side identical, matched-baseline verdict, status): the rule-side `fields` must be identical;
    the matched baseline (dev['field']) may differ by at most dev['abs_tolerance'] (the accepted, recorded
    deviation); status REPRODUCED only then, else DEVIATES."""
    rule_side = all(_same_fact(want[k], got[k]) for k in fields)
    mw, mg = want[dev["field"]], got[dev["field"]]
    if _same_fact(mw, mg):
        matched = "IDENTICAL"
    elif mw is not None and mg is not None and abs(mw - mg) <= float(dev["abs_tolerance"]):
        matched = "DEVIATES_WITHIN_ACCEPTED_TOLERANCE"
    else:
        matched = "DEVIATES"
    return rule_side, matched, ("REPRODUCED" if rule_side and matched != "DEVIATES" else "DEVIATES")


def run_reproduce(df, meta, registry, out: Path, proto: dict, proto_sha: str, market: str, log=print) -> dict:
    """Precondition: the market's recorded run(s) re-run from their recorded config on the pinned panel.
    REPRODUCED when the rule-side statistics are identical and the matched baseline is identical or within
    the accepted tolerance (controls.py bcb89f0, on record); otherwise DEVIATES, both sides on record."""
    check_panel(proto, market, meta)
    s0 = get(proto, "stages.0_reproduce")
    fields = list(s0["rule_side_fields"])
    dev = s0["accepted_deviation"]
    out.mkdir(parents=True, exist_ok=False)
    H, x = int(get(proto, "labels.horizon")), float(get(proto, "labels.threshold"))
    results = []
    for run_dir in get(proto, f"markets.{market}.precondition_runs"):
        rec = recorded_run(run_dir)
        recorded = json.loads((PKG_ROOT / run_dir / "summary.json").read_text(encoding="utf-8"))
        cfg_fields = {k: v for k, v in recorded["config"].items() if k in RunConfig.__dataclass_fields__}
        cfg = RunConfig(**cfg_fields)
        assert_within_validation(proto, cfg.market, cfg.end)
        log(f"reproducing {run_dir}")
        output = run(cfg, df, meta, ca_registry=registry if cfg.ca_mode == "registry" else None)
        summary = output["summary"]

        def facts(s):
            return {"signals": s["signals"]["total"], "scored": s["rule_trades"]["scored"],
                    "avg_net_return": s["rule_trades"]["avg_net_return"],
                    "status_counts": s["rule_trades"]["status_counts"],
                    "matched_random_avg_net_return": (s["random_matched"]["avg_net_return"] or {}).get("random_mean")}

        want, got = facts(recorded), facts(summary)
        rule_side, matched, status = reproduce_status(want, got, fields, dev)
        m = Market.from_panel(df, price_limits=PROFILES[cfg.market].price_limits).window(summary["config"]["start"],
                                                                                        summary["config"]["end"])
        results.append({"run_dir": run_dir, "run_id": rec["run_id"], "config": cfg_fields, "recorded": want,
                        "reproduced": got, "rule_side_identical": bool(rule_side), "matched_baseline": matched,
                        "accepted_deviation": dev, "recorded_panel_sha256": recorded["panel"]["panel_sha256"],
                        "recorded_rule_sha256": recorded["rule"]["sha256"], "reproduced_rule_sha256": summary["rule"]["sha256"],
                        "lookahead": summary["lookahead_check"]["mode"],
                        "breakeven": breakeven_precision(output["trades"], u_lookup(m, H, x)), "status": status})
    result = {**_stamp(proto_sha, proto, market, "reproduce", meta, registry), "runs": results,
              "status": "REPRODUCED" if all(r["status"] == "REPRODUCED" for r in results) else "DEVIATES"}
    write_json(out / "result.json", result)
    return result


# ---------------------------------------------------------------------------------------- stage 1 + 2
def _check_precondition(out: Path, meta: dict, accept_deviation: bool) -> dict:
    repro_path = out.parent / "reproduce" / "result.json"
    if not repro_path.exists():
        raise RuntimeError(f"the precondition has not been run for this market (e5-reproduce): {_rel(repro_path)}")
    repro = json.loads(repro_path.read_text(encoding="utf-8"))
    if repro["panel_sha256"] != meta["sha256"]:
        raise RuntimeError("the precondition ran on different data than this discovery")
    if repro["status"] != "REPRODUCED" and not accept_deviation:
        raise RuntimeError("the recorded run did not reproduce on this data beyond the accepted deviation; see "
                           f"{_rel(repro_path)} and pass --accept-deviation to proceed with that on record")
    return repro


def run_discovery(df, meta, registry, out: Path, proto: dict, proto_sha: str, market: str, log=print,
                  accept_deviation: bool = False, protocol_path: Path | None = None) -> dict:
    check_panel(proto, market, meta)
    repro = _check_precondition(out, meta, accept_deviation)
    if list(get(proto, "features.order")) != list(moonshot_e5.FEATURE_ORDER):
        raise RuntimeError("protocol features.order is not moonshot_e5.FEATURE_ORDER")
    out.mkdir(parents=True, exist_ok=False)
    mk = market
    years = [int(y) for y in get(proto, f"markets.{mk}.discovery_years")]
    learner = get(proto, "learner")
    det = get(proto, "matched_controls.detection_stage")
    log(f"{mk}: building the discovery study")
    study = build_study(proto, mk, df, meta, protocol_path)
    window = study.e5_window
    m, f = study.m, study.base_feats
    lab = labels(study, proto, mk)
    ev = evaluable_mask(study, proto, mk, "discovery", lab)
    const = constant_columns(f, ev)
    n_idx, d_idx = np.nonzero(ev)
    log(f"{mk}: {len(n_idx)} evaluable discovery ticker-days; fitting U")
    fit_u = fit_label(f, n_idx, d_idx, lab["U"][n_idx, d_idx], learner, "U")
    d_arr, d_info = d_label(lab, mk, ev, proto)
    log(f"{mk}: fitting D ({d_info['rule']})")
    fit_d = fit_label(f, n_idx, d_idx, d_arr[n_idx, d_idx], learner, "D")
    model = {"market": mk, "protocol_id": proto["protocol_id"], "protocol_sha256": proto_sha,
             "feature_order": list(moonshot_e5.FEATURE_ORDER),
             "coef_U": fit_u["coef"], "intercept_U": fit_u["intercept"], "coef_D": fit_d["coef"],
             "intercept_D": fit_d["intercept"], "fit_U": fit_u, "fit_D": fit_d, "D_label": d_info,
             "constant_columns": const, "constant_column_names": [k for k, v in const.items() if v["constant"]],
             "window": window, "evaluable_ticker_days": int(len(n_idx)),
             "study_options": study.study_options(), "panel_sha256": meta["sha256"]}
    scores = arm_scores(f, model)
    pct = float(learner["threshold_percentile"])
    thr = {arm: threshold(scores[arm], ev, pct) for arm in ARMS}
    model["threshold_A"], model["threshold_B"] = thr["A"], thr["B"]
    write_json(out / "model.json", model)
    literals_sha = sha256_file(out / "model.json")
    write_json(out / "thresholds.json", {"market": mk, "percentile": pct, "evaluable_ticker_days": int(len(n_idx)),
                                         "threshold_A": thr["A"], "threshold_B": thr["B"]})
    entry_price = PROFILES[mk].entry
    H = int(get(proto, "labels.horizon"))
    r_plan = plan_window_return(m, entry_price, H)
    r_plan = np.where(lab["censor_plan"], np.nan, r_plan)
    # v1.1 (audit finding A): the plan window of a flag at t exits at t+1+H; it counts, for the flag and for
    # its matched controls alike, only when that exit session is inside the period. Label eligibility
    # (t and t+H inside the period, evaluable_mask) stays what it was.
    last_idx = int(np.searchsorted(study.dates, np.datetime64(window["last_period_session"], "D"), side="right")) - 1
    plan_ok = (np.arange(m.shape[1]) + 1 + H) <= last_idx
    r_plan = np.where(plan_ok[None, :], r_plan, np.nan)
    eligibility = {"label": f"t and t+{H} inside the period (evaluable_mask)",
                   "plan_window": f"exit session t+1+{H} inside the period, flags and matched controls alike",
                   "label_eligible_ticker_days": int(len(n_idx)),
                   "plan_window_eligible_ticker_days": int((ev & plan_ok[None, :]).sum()),
                   "last_plan_eligible_session": str(study.dates[last_idx - 1 - H]) if last_idx - 1 - H >= 0 else None,
                   "study_last_session": str(study.dates[-1])}
    primaries = {tuple(v): k for k, v in get(proto, "stages.1_information.primaries").items()}
    stage1 = {"market": mk, "window": window, "evaluable_ticker_days": int(len(n_idx)),
              "base_rates": {"E30": float(np.nanmean(lab["U"][ev])), "D30": float(np.nanmean(d_arr[ev]))},
              "D_label": d_info, "unit_resets": lab["unit_resets"], "constant_columns": model["constant_column_names"],
              "entry_price": entry_price, "eligibility": eligibility, "arms": {}, "detectors": {}}
    flag_rows = []
    gates = {"market": mk, "stage1": {}, "a1": None, "stage2": {}, "selected_arm": None}
    for arm in ARMS:
        flags = arm_flags(scores[arm], thr[arm], m)
        fl_n, fl_d = flag_cells(flags & ev)
        log(f"{mk} arm {arm}: {len(fl_n)} flags on evaluable discovery ticker-days; drawing controls")
        draws, level = detection_draws(study, fl_n, fl_d, ev, int(det["draws"]), int(det["seed"]))
        block = flag_block(study, lab, d_arr, f, r_plan, fl_n, fl_d, draws, level, ev, years, proto, mk)
        block.update({"threshold": thr[arm], "auc_U": auc(scores[arm][ev], lab["U"][ev]),
                      "auc_D": auc(scores[arm][ev], d_arr[ev]),
                      "flags_in_period_total": int((flags & (np.arange(m.shape[1]) >= moonshot_e5.WARMUP)[None, :]
                                                    & (study.dates >= np.datetime64(window["period_start"], "D"))[None, :]
                                                    & (study.dates <= np.datetime64(window["period_end"], "D"))[None, :]).sum()),
                      "primary": primaries.get((mk, arm)), "gate": stage1_gate(block, proto, years)})
        if arm == "A":
            ci = block["E30"]["lift_vs_matched_ci95"]
            d_lift = block["D30"]["lift_vs_matched"]
            block["variance_detection_check"] = {
                "D30_lift_vs_matched": d_lift, "E30_lift_ci95": ci,
                "D30_lift_within_E30_lift_ci": bool(ci and d_lift is not None and ci[0] <= d_lift <= ci[1])}
        stage1["arms"][arm] = block
        gates["stage1"][arm] = block["gate"]
        rc = r_plan[draws, fl_d[None, :]]
        with np.errstate(invalid="ignore", divide="ignore"):
            rc_mean = np.where(np.isfinite(rc).sum(axis=0) > 0, np.nansum(rc, axis=0) / np.isfinite(rc).sum(axis=0), np.nan)
        for j, (n, d) in enumerate(zip(fl_n, fl_d)):
            flag_rows.append({"arm": arm, "ticker": str(m.tickers[n]), "date": str(study.dates[d]),
                              "score": float(scores[arm][n, d]), "U": lab["U"][n, d], "D": d_arr[n, d],
                              "ret1": float(f["ret1"][n, d]), "plan_return": r_plan[n, d], "matched_plan_mean": rc_mean[j],
                              "match_level": int(level[j])})
    for name, flags in detector_flags(f, m).items():
        fl_n, fl_d = flag_cells(flags & ev)
        log(f"{mk} {name}: {len(fl_n)} flags; drawing controls")
        draws, level = detection_draws(study, fl_n, fl_d, ev, int(det["draws"]), int(det["seed"]))
        block = flag_block(study, lab, d_arr, f, r_plan, fl_n, fl_d, draws, level, ev, years, proto, mk)
        block["gate"] = stage1_gate(block, proto, years)
        if name == "A1_CREEP_QUIET_NR":
            block["a1_gate"] = a1_gate(block, proto)
            gates["a1"] = block["a1_gate"]
        stage1["detectors"][name] = block
        for j, (n, d) in enumerate(zip(fl_n, fl_d)):
            flag_rows.append({"arm": name, "ticker": str(m.tickers[n]), "date": str(study.dates[d]), "score": None,
                              "U": lab["U"][n, d], "D": d_arr[n, d], "ret1": float(f["ret1"][n, d]),
                              "plan_return": r_plan[n, d], "matched_plan_mean": None, "match_level": int(level[j])})
    write_json(out / "stage1.json", stage1)
    cols = ["arm", "ticker", "date", "score", "U", "D", "ret1", "plan_return", "matched_plan_mean", "match_level"]
    write_csv(out / "flags.csv", pd.DataFrame(flag_rows, columns=cols))
    log(f"{mk}: univariate table")
    write_csv(out / "univariate.csv", univariate_table(study, lab, f, ev, proto))
    # ---- stage 2: the harness under the market plan for every arm that passed, plus A1 if gated
    to_run = [("arm", arm) for arm in ARMS if gates["stage1"][arm]["passed"]]
    if gates["a1"] and gates["a1"]["passed"]:
        to_run.append(("detector", "A1_CREEP_QUIET_NR"))
    rows, run_rows = [], {}
    cache: dict = {}
    volume = volume_series(df) if to_run else None
    u_of = u_lookup(m.window(window["start"], window["end"]), int(get(proto, "labels.horizon")),
                    float(get(proto, "labels.threshold"))) if to_run else None
    plan = {k: get(proto, f"plans.{mk}.primary")[k] for k in PLAN_KEYS}
    for kind, name in to_run:
        rule_id = moonshot_e5.candidate_rule_id(f"{mk}_{name}" if kind == "arm" else name)
        run_rows[name] = {}
        for spec in run_specs(proto, mk):
            cfg = harness_config(proto, mk, rule_id, window["start"], window["end"], spec["overrides"])
            log(f"{mk} {name} {spec['id']}: harness run ({cfg.market}, fill {cfg.fill_model}, controls {cfg.controls_version})")
            with literals_from(model, mk):
                output = run(cfg, df, meta, ca_registry=registry if cfg.ca_mode == "registry" else None, signal_cache=cache)
            row = harness_row(output["summary"], output["trades"], name, spec, plan, years, proto, volume, u_of,
                              literals_sha)
            rows.append(row)
            run_rows[name][spec["id"]] = row
            write_json(run_summary_path(out, cfg.market, name, spec["id"]), output["summary"])
        adm = admissibility_stage2(run_rows[name]["primary"],
                                   [r for k, r in run_rows[name].items() if k != "primary"], proto, years)
        gates["stage2"][name] = adm
    table = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["arm", "run", "judged"])  # empty: no arm passed
    write_csv(out / "plans.csv", table)
    adm_arms = {a: gates["stage2"][a] for a in ARMS if a in gates["stage2"]}
    gates["selected_arm"] = select_arm(adm_arms, {a: run_rows[a]["primary"] for a in adm_arms}, mk, proto)
    gates["freeze"] = ("run e5-freeze --market " + mk + " (copies discovery/model.json into moonshot_e5.py and sets "
                       "SELECTED), commit, then e5-validation" if gates["selected_arm"] else
                       "no admissible arm on " + mk + ": nothing to validate; the ranker may still be frozen for the "
                       "prospective sidecar (e5-freeze sets no SELECTED entry)")
    write_json(out / "gates.json", gates)
    summary = {**_stamp(proto_sha, proto, mk, "discovery", meta, registry),
               "precondition": {"status": repro["status"], "accepted_deviation": bool(accept_deviation)},
               "window": window, "study_options": study.study_options(), "evaluable_ticker_days": int(len(n_idx)),
               "fits": {"U": {k: fit_u[k] for k in ("n_rows_used", "n_positives", "n_negatives_sampled", "lambda", "deviance", "converged")},
                        "D": {k: fit_d[k] for k in ("n_rows_used", "n_positives", "n_negatives_sampled", "lambda", "deviance", "converged")}},
               "thresholds": thr, "constant_columns": model["constant_column_names"],
               "stage1_gates": gates["stage1"], "a1_gate": gates["a1"], "stage2_runs": len(rows),
               "stage2_admissibility": gates["stage2"], "selected_arm": gates["selected_arm"],
               "primaries": get(proto, "stages.1_information.primaries"), "freeze": gates["freeze"],
               "files": ["model.json", "thresholds.json", "stage1.json", "flags.csv", "univariate.csv", "plans.csv",
                         "gates.json", "runs/<RunConfig market>/<arm>_<run>.json"]}
    write_json(out / "summary.json", summary)
    return summary


# ---------------------------------------------------------------------------------------- stage 3
def run_freeze(out: Path, proto: dict, proto_sha: str, market: str, module_path: Path | None = None,
               discovery_dir: Path | None = None, log=print) -> dict:
    """Copy discovery/model.json into the module's literal tables and SELECTED (gates.json); refuses when
    the market's literals are already set. Writes <MARKET>/freeze/result.json; the caller commits both."""
    module_path = Path(module_path or MODULE_PATH)
    disc = discovery_dir or out.parent / "discovery"
    model = json.loads((disc / "model.json").read_text(encoding="utf-8"))
    gates = json.loads((disc / "gates.json").read_text(encoding="utf-8"))
    if model["market"] != market or gates["market"] != market:
        raise RuntimeError(f"{_rel(disc)} is not {market}'s discovery")
    selected = gates.get("selected_arm")
    source = module_path.read_text(encoding="utf-8")
    new = freeze_source(source, model, market, selected)
    frozen = load_module_from_text(new)
    problems = check_frozen(model, market, frozen)
    if problems:
        raise RuntimeError(f"the rewritten module does not carry model.json: {problems}")
    from .rules.audit import audit_module

    audit = audit_module(frozen)
    if audit:
        raise RuntimeError(f"the rewritten module fails the source audit: {audit}")
    out.mkdir(parents=True, exist_ok=False)
    module_path.write_text(new, encoding="utf-8")
    log(f"{market}: literals written to {module_path.name}; SELECTED {'+= ' + str((market, selected)) if selected else 'unchanged'}")
    result = {"protocol_id": proto["protocol_id"], "protocol_sha256": proto_sha, "market": market, "stage": "freeze",
              "computed_at": _now(), "model_sha256": sha256_file(disc / "model.json"), "selected_arm": selected,
              "module": _rel(module_path),
              "module_sha256_after": sha256_file(module_path), "code_before": code_state(),
              "thresholds": {"A": model["threshold_A"], "B": model["threshold_B"]},
              "next": "commit idxsig/rules/moonshot_e5.py and research/E5/" + market + "/freeze together, then "
                      "e5-validation --market " + market if selected else "no SELECTED entry: no validation run"}
    write_json(out / "result.json", result)
    return result


def load_module_from_text(source: str):
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="idxsig-e5-freeze-")) / "moonshot_e5_frozen.py"
    tmp.write_text(source, encoding="utf-8")
    return load_module_from(tmp)


# ---------------------------------------------------------------------------------------- stage 4
def validation_pass(row: dict, sensitivities: list[dict], detection: dict, proto: dict, market: str) -> dict:
    v = get(proto, "validation")
    reasons = []
    if row["scored"] < int(v["min_scored"][market]):
        reasons.append(f"scored {row['scored']} < {v['min_scored'][market]}")
    if row["avg_net_return"] is None or not row["avg_net_return"] > 0:
        reasons.append("average net return not positive")
    judged = True
    if (row.get("paired_net_n_clusters") or 0) < 2:
        judged = False
        reasons.append("not judged: fewer than 2 signal-session clusters")
    else:
        if not ((row.get("paired_net_mean_excess") or 0) > 0):
            reasons.append("paired net excess not positive")
        if row.get("paired_net_p_one_sided") is None or not row["paired_net_p_one_sided"] < float(v["alpha_paired_net"]):
            reasons.append(f"paired net p {row.get('paired_net_p_one_sided')} not below {v['alpha_paired_net']}")
    p = row.get("p_one_sided_vs_matched")
    if p is None or not p < float(v["max_p_one_sided_vs_matched"]):
        reasons.append(f"harness p vs matched {p} not below {v['max_p_one_sided_vs_matched']}")
    for s in sensitivities:
        if s.get("judged", True) and not ((s.get("rule_minus_matched") or 0) > 0):
            reasons.append(f"sensitivity {s.get('run')}: rule minus matched not positive")
    lo, base = detection.get("precision_lo95"), detection.get("base_rate")
    if lo is None or base is None or not lo > base:
        reasons.append(f"detection: E30 precision Wilson lower bound {lo} not above the base rate {base}")
    return {"judged": judged, "passed": bool(judged and not reasons), "reasons": reasons,
            "claim_level": v["claim_level"]}


def validation_targets(gates: dict, market: str) -> list[tuple[str, str]]:
    """What Stage 4 runs, as (name, rule id): every Stage-2-admissible arm (the selected one under
    MOONSHOT_E5_<MARKET>_D1, any other under its candidate id) and A1 when its Stage-2 row was admissible
    (under its candidate id, recorded only now, after the freeze, so its rule sha is the frozen one)."""
    selected = gates.get("selected_arm")
    out = []
    for arm in ARMS:
        if gates.get("stage2", {}).get(arm, {}).get("admissible"):
            out.append((arm, moonshot_e5.selected_rule_id(market) if arm == selected
                        else moonshot_e5.candidate_rule_id(f"{market}_{arm}")))
    a1 = "A1_CREEP_QUIET_NR"
    if gates.get("stage2", {}).get(a1, {}).get("admissible"):
        out.append((a1, moonshot_e5.candidate_rule_id(a1)))
    return out


def run_validation(df, meta, registry, out: Path, proto: dict, proto_sha: str, market: str, log=print,
                   protocol_path: Path | None = None) -> dict:
    check_panel(proto, market, meta)
    disc = out.parent / "discovery"
    model = json.loads((disc / "model.json").read_text(encoding="utf-8"))
    gates = json.loads((disc / "gates.json").read_text(encoding="utf-8"))
    problems = check_frozen(model, market)
    if problems:
        raise RuntimeError(f"moonshot_e5.py literals are not discovery/model.json: {problems} (run e5-freeze and commit)")
    selected = gates.get("selected_arm")
    targets = validation_targets(gates, market)
    if not targets:
        raise RuntimeError(f"no Stage-2-admissible arm on {market}: nothing to validate")
    if selected is not None and (moonshot_e5.SELECTED is None
                                 or (market, selected) not in [tuple(x) for x in moonshot_e5.SELECTED]):
        raise RuntimeError(f"moonshot_e5.SELECTED {moonshot_e5.SELECTED} does not name ({market}, {selected})")
    out.mkdir(parents=True, exist_ok=False)
    mk = market
    literals_sha = sha256_file(disc / "model.json")  # equal to the module literals (checked above)
    log(f"{mk}: validation study (detection)")
    study = build_study(proto, mk, df, meta, protocol_path, period="validation")
    window = study.e5_window
    m, f = study.m, study.base_feats
    lab = labels(study, proto, mk)
    ev = evaluable_mask(study, proto, mk, "validation", lab)
    scores = arm_scores(f, model)
    det_flags = detector_flags(f, m)
    base = float(np.nanmean(lab["U"][ev])) if ev.any() else float("nan")
    detection = {}
    for name, _ in targets:
        flags = arm_flags(scores[name], model[f"threshold_{name}"], m) if name in ARMS else det_flags[name]
        fl_n, fl_d = flag_cells(flags & ev)
        hit = lab["U"][fl_n, fl_d]
        k, n = int(np.nansum(hit)), int(len(hit))
        lo, hi = wilson(k, n)
        detection[name] = {"flags": n, "hits": k, "precision": k / n if n else None,
                           "precision_lo95": float(lo) if n else None, "precision_hi95": float(hi) if n else None,
                           "base_rate": base, "evaluable_ticker_days": int(ev.sum())}
    years = [int(window["period_start"][:4])]
    plan = {k: get(proto, f"plans.{mk}.primary")[k] for k in PLAN_KEYS}
    volume = volume_series(df)
    u_of = u_lookup(Market.from_panel(df, price_limits=PROFILES[mk].price_limits).window(window["start"], window["end"]),
                    int(get(proto, "labels.horizon")), float(get(proto, "labels.threshold")))
    cache: dict = {}
    results, rows = {}, []
    for name, rule_id in targets:
        run_rows = {}
        for spec in run_specs(proto, mk):
            cfg = harness_config(proto, mk, rule_id, window["start"], window["end"], spec["overrides"])
            log(f"{mk} {name} {spec['id']}: recorded harness run ({rule_id}, {cfg.market}, fill {cfg.fill_model})")
            output = run(cfg, df, meta, ca_registry=registry if cfg.ca_mode == "registry" else None, signal_cache=cache)
            run_dir = write_run(output)  # the trading run on record, committed
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            row = harness_row(summary, output["trades"], name, spec, plan, years, proto, volume, u_of, literals_sha)
            row.update({"run_id": summary["run_id"], "run_dir": rel(run_dir), "rule_id": rule_id})
            rows.append(row)
            run_rows[spec["id"]] = row
        verdict = validation_pass(run_rows["primary"], [r for k, r in run_rows.items() if k != "primary"],
                                  detection[name], proto, mk)
        results[name] = {"rule_id": rule_id, "runs": run_rows, "detection": detection[name], **verdict}
    write_csv(out / "plans.csv", pd.DataFrame(rows))
    selected_passed = results[selected]["passed"] if selected in results else None
    result = {**_stamp(proto_sha, proto, mk, "validation", meta, registry), "window": window, "selected_arm": selected,
              "selected": list(moonshot_e5.SELECTED) if moonshot_e5.SELECTED is not None else None,
              "study_options": study.study_options(), "arms": results,
              "passed": {name: results[name]["passed"] for name, _ in targets},
              "claim_level": get(proto, "validation.claim_level"),
              "consequence": ("PROVISIONAL pass: a new paper policy version may wire MOONSHOT_E5_" + mk + "_D1 "
                              "through paper._detector; no paper BUY until >= 100 prospective scored E5 decisions "
                              "show paired excess > 0; the holdout stays sealed"
                              if selected_passed else
                              ("the selected arm did not pass 2023: the family is closed on " + mk + " (no second "
                               "design pass); the prospective sidecar is the only remaining path for this ranker")
                              if selected is not None else
                              "no selected arm on " + mk + ": only the gated A1 row was validated (reported)")}
    write_json(out / "result.json", result)
    return result
