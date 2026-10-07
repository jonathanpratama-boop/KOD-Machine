"""Run a rule over the whole universe and compare it with random entries.

Universe: every ticker in the panel window, including names that later delisted, on
every session where the rule is evaluable. Not a list of past winners.

Two random baselines, each run through the identical execution model and holding period.
For every attempted signal, `random_draws` replacement entries are drawn on the same
session from the names where the rule was evaluable:

  matched       from names in the same price band, liquidity, volatility and momentum
                buckets as the signalled name (controls.py), so exposure to illiquid or
                volatile names is not mistaken for a signal. This is the primary comparison.
  same-session  from all of them, uniformly. Controls for market timing only.

Each draw is a portfolio of the rule's size and dates. The rule's average return and hit
rate are placed in each distribution of draws.

No lookahead: by default the rule is recomputed on every prefix of the data (sessions
0..d for every d) and its signal at d must equal the full run's signal at d. That makes
every recorded signal exactly what the rule computes from data available at that close.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from . import controls
from . import rules as rule_registry
from .execution import FIRST_SKIP, SCORED, STATUS, ExecConfig, Market, execute
from .market import Fees
from .sources.idx_mirror import FIRST_SNAPSHOT


class LookaheadError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunConfig:
    rule_id: str
    start: str | None = None  # default: the mirror's first snapshot (survivorship-complete from there)
    end: str | None = None  # default: last session of the IDX mirror (the best-covered era)
    holding_days: int | None = None  # default: the rule's pre-registered holding period
    entry_lag: int = 1
    notional: float = 10_000_000.0
    max_participation: float = 0.10
    fee_buy: float = 0.0015
    fee_sell: float = 0.0025
    overlap: str = "skip"  # skip a signal while the same name is still held
    random_draws: int = 200
    seed: int = 20261007
    data_end_exit: str = "last_close"
    ca_mode: str = "exclude"
    lookahead_cuts: int | None = None  # None: every session (exhaustive); N: N sampled prefixes


def _equal_with_nan(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(np.nan_to_num(a), np.nan_to_num(b)))


def lookahead_check(rule, m: Market, full: np.ndarray, cuts: int | None) -> dict:
    n_sessions = m.shape[1]
    if cuts is None:
        for d in range(n_sessions):
            part = rule_registry.signal_array(rule, m.truncate(d))[:, d]
            if not _equal_with_nan(full[:, d], part):
                raise LookaheadError(f"{rule.rule_id}: the signal at {m.dates[d]} differs when later sessions are "
                                     f"removed, so it reads data from after that close")
        return {"mode": "exhaustive", "sessions_checked": n_sessions, "mismatches": 0}
    checked = []
    for frac in np.linspace(0.3, 0.9, cuts) if cuts else []:
        cut = int(frac * (n_sessions - 1))
        if not _equal_with_nan(full[:, : cut + 1], rule_registry.signal_array(rule, m.truncate(cut))):
            raise LookaheadError(f"{rule.rule_id} changes past signals when sessions after {m.dates[cut]} are "
                                 f"removed: it reads ahead")
        checked.append(str(m.dates[cut]))
    return {"mode": "sampled", "truncated_after": checked, "mismatches": 0}


def _summary_stats(net: np.ndarray, status: np.ndarray) -> dict:
    scored = np.isin(status, SCORED)
    vals = net[scored]
    entered = status < FIRST_SKIP
    return {
        "attempts": int(len(status)),
        "filled": int(entered.sum()),
        "fill_rate": float(entered.mean()) if len(status) else None,
        "scored": int(scored.sum()),
        "hit_rate": float((vals > 0).mean()) if len(vals) else None,
        "avg_net_return": float(vals.mean()) if len(vals) else None,
        "median_net_return": float(np.median(vals)) if len(vals) else None,
        "std_net_return": float(vals.std(ddof=1)) if len(vals) > 1 else None,
        "status_counts": {STATUS[i]: int((status == i).sum()) for i in range(len(STATUS)) if (status == i).any()},
    }


def _baseline(m: Market, r_tick: np.ndarray, a_sig: np.ndarray, exec_cfg: ExecConfig, rule_stats: dict,
              method: str) -> tuple[dict, pd.DataFrame, dict]:
    draws = r_tick.shape[0]
    r_sig = np.broadcast_to(a_sig, r_tick.shape)
    out = execute(m, r_tick.ravel(), r_sig.ravel(), exec_cfg)
    net = out["net_return"].reshape(draws, -1)
    status = out["status"].reshape(draws, -1)
    rows = []
    for d in range(draws):
        st = _summary_stats(net[d], status[d])
        rows.append({"draw": d, "scored": st["scored"], "fill_rate": st["fill_rate"], "hit_rate": st["hit_rate"],
                     "avg_net_return": st["avg_net_return"], "median_net_return": st["median_net_return"]})
    frame = pd.DataFrame(rows)

    def dist(col: str, observed):
        v = frame[col].dropna().to_numpy() if not frame.empty else np.array([])
        if observed is None or not len(v):
            return None
        return {
            "observed": observed,
            "random_mean": float(v.mean()),
            "random_p2_5": float(np.percentile(v, 2.5)),
            "random_p50": float(np.percentile(v, 50)),
            "random_p97_5": float(np.percentile(v, 97.5)),
            "difference": float(observed - v.mean()),
            "percentile_of_observed": float((v < observed).mean() * 100),
            "p_value_one_sided": float((1 + (v >= observed).sum()) / (1 + len(v))),
        }

    summary = {
        "draws": draws,
        "method": method,
        "pooled": _summary_stats(out["net_return"], out["status"]),
        "avg_net_return": dist("avg_net_return", rule_stats["avg_net_return"]),
        "hit_rate": dist("hit_rate", rule_stats["hit_rate"]),
    }
    return summary, frame, out


def run(cfg: RunConfig, panel_df: pd.DataFrame, panel_meta: dict) -> dict:
    rule = rule_registry.get(cfg.rule_id)
    holding = cfg.holding_days or rule.holding_days
    exec_cfg = ExecConfig(
        holding_days=holding,
        entry_lag=cfg.entry_lag,
        notional=cfg.notional,
        max_participation=cfg.max_participation,
        fees=Fees(cfg.fee_buy, cfg.fee_sell),
        data_end_exit=cfg.data_end_exit,
        ca_mode=cfg.ca_mode,
    )
    start = cfg.start or FIRST_SNAPSHOT
    end = cfg.end or panel_meta["source_boundary"]
    m = Market.from_panel(panel_df).window(start, end)
    sig = rule_registry.signal_array(rule, m)
    lookahead = lookahead_check(rule, m, sig, cfg.lookahead_cuts)
    evaluable = np.isfinite(sig)
    tick_idx, sig_idx = np.nonzero(sig == 1)  # row-major: by ticker, then session

    trades = execute(m, tick_idx, sig_idx, exec_cfg)
    overlap_skipped = np.zeros(len(tick_idx), dtype=bool)
    if cfg.overlap == "skip":
        held_until = {}
        for i, (n, s) in enumerate(zip(tick_idx, sig_idx)):
            if s + cfg.entry_lag <= held_until.get(n, -1):
                overlap_skipped[i] = True
                continue
            st = trades["status"][i]
            if trades["exit_idx"][i] >= 0:  # exited, exited at data end, or held across a corporate action
                held_until[n] = trades["exit_idx"][i]
            elif st == STATUS.index("INCOMPLETE"):
                held_until[n] = np.iinfo(np.int64).max
    attempt = ~overlap_skipped
    a_tick, a_sig = tick_idx[attempt], sig_idx[attempt]
    rule_stats = _summary_stats(trades["net_return"][attempt], trades["status"][attempt])

    draws = cfg.random_draws
    rng = np.random.default_rng(cfg.seed)
    same_tick = np.empty((draws, len(a_sig)), dtype=np.int64)
    for s in np.unique(a_sig):
        cols = np.flatnonzero(a_sig == s)
        same_tick[:, cols] = rng.choice(np.flatnonzero(evaluable[:, s]), size=(draws, len(cols)), replace=True)
    matched_tick, level_used = controls.matched_draws(
        evaluable, controls.features(m), a_tick, a_sig, draws, np.random.default_rng(cfg.seed + 1)
    )
    baselines, frames, raw = {}, [], {}
    for key, ticks, method in (
        ("random_matched", matched_tick, "same session, same price band / liquidity quintile / volatility tercile / "
                                         "momentum tercile as the signalled name (relaxed when fewer than "
                                         f"{controls.MIN_POOL} names match), same execution"),
        ("random", same_tick, "same session, uniform over names where the rule was evaluable, same execution"),
    ):
        if len(a_sig):
            baselines[key], frame, raw[key] = _baseline(m, ticks, a_sig, exec_cfg, rule_stats, method)
            frames.append(frame.assign(baseline=key))
        else:
            baselines[key] = {"draws": draws, "method": method, "pooled": _summary_stats(np.array([]), np.array([], dtype=np.int64)),
                              "avg_net_return": None, "hit_rate": None}
    names = controls.level_names()
    baselines["random_matched"]["match_level_used"] = {
        names[i]: int((level_used == i).sum()) for i in range(len(names)) if (level_used == i).any()
    }
    draws_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    by_year = []
    years = m.dates.astype("datetime64[Y]").astype(int) + 1970
    sig_year = years[a_sig]
    for y in sorted(set(sig_year.tolist())):
        sel = sig_year == y
        rs = _summary_stats(trades["net_return"][attempt][sel], trades["status"][attempt][sel])
        row = {"year": int(y), "attempts": rs["attempts"], "scored": rs["scored"], "hit_rate": rs["hit_rate"],
               "avg_net_return": rs["avg_net_return"]}
        for key, out in raw.items():
            rsel = np.broadcast_to(sel, (draws, len(a_sig))).ravel()
            rr = _summary_stats(out["net_return"][rsel], out["status"][rsel])
            row[f"{key}_hit_rate"] = rr["hit_rate"]
            row[f"{key}_avg_net_return"] = rr["avg_net_return"]
        by_year.append(row)

    warnings = []
    if np.datetime64(start, "D") < np.datetime64(FIRST_SNAPSHOT, "D"):
        warnings.append(
            f"window starts before {FIRST_SNAPSHOT}, the mirror's first snapshot: names that delisted before "
            f"then are missing, so the universe before {FIRST_SNAPSHOT} is survivor-biased"
        )
    if np.datetime64(end, "D") > np.datetime64(panel_meta["source_boundary"], "D"):
        warnings.append(
            f"window runs past {panel_meta['source_boundary']}: after that date the panel is survivor-only "
            f"(names delisted later stop at {panel_meta['source_boundary']} and exit as EXIT_DATA_END)"
        )
    if rule_stats["scored"] < 30:
        warnings.append(f"only {rule_stats['scored']} scored trades; any difference from random is mostly noise")
    data_end = rule_stats["status_counts"].get("EXIT_DATA_END", 0)
    if data_end:
        warnings.append(f"{data_end} trades exited at a last traded close because the name stopped trading "
                        f"(data_end_exit={cfg.data_end_exit})")
    excluded = rule_stats["status_counts"].get("EXCLUDED_CORP_ACTION", 0)
    if excluded:
        warnings.append(f"{excluded} trades were held across a rights issue or other non-split corporate action "
                        f"and are not scored (ca_mode={cfg.ca_mode}); the baselines apply the same rule")
    if lookahead["mode"] != "exhaustive":
        warnings.append("lookahead check was sampled, not exhaustive; the signals are not proven causal")
    if rule.kind == "PLACEBO":
        warnings.append("PLACEBO rule: harness self-check, not a trading rule; any lift here is a harness bias")

    tickers = m.tickers
    trades_df = pd.DataFrame({
        "ticker": tickers[tick_idx],
        "signal_date": m.dates[sig_idx].astype(str),
        "status": np.where(overlap_skipped, "SKIP_OVERLAP", np.array(STATUS)[trades["status"]]),
        "entry_date": np.where(trades["entry_idx"] >= 0, m.dates[np.maximum(trades["entry_idx"], 0)].astype(str), ""),
        "exit_date": np.where(trades["exit_idx"] >= 0, m.dates[np.maximum(trades["exit_idx"], 0)].astype(str), ""),
        "entry_price": trades["entry_price"],
        "shares": trades["shares"],
        "exit_price": trades["exit_price"],
        "share_factor": trades["share_factor"],
        "rolled_sessions": trades["rolled_sessions"],
        "gross_return": trades["gross_return"],
        "net_return": trades["net_return"],
    })
    summary = {
        "rule": {"rule_id": rule.rule_id, "version": rule.version, "kind": rule.kind, "text": rule.text,
                 "sha256": rule.sha256, "holding_days": holding},
        "config": {**asdict(cfg), "start": start, "end": end, "holding_days": holding},
        "execution": {
            "price": "official close; signal at close of s, entry at close of s + entry_lag",
            "lot_size": 100,
            "fees": {"buy": cfg.fee_buy, "sell": cfg.fee_sell},
            "auto_rejection": "entry refused when the entry close is locked at ARA; exit rolls while locked at ARB "
                              "or untraded; regular-board schedule by date, plus 10% special-board limits on "
                              "one-price or sub-Rp50 bars",
            "corporate_actions": "splits and reverse splits scale shares; a trade held across any other reference "
                                 "reset (rights issue, bonus, stock dividend) is "
                                 + ("excluded" if cfg.ca_mode == "exclude" else "valued as if rights were reinvested"),
        },
        "panel": {"manifest_sha256": panel_meta.get("_manifest_sha256"), "panel_sha256": panel_meta["sha256"],
                  "panel": panel_meta["panel"], "source_boundary": panel_meta["source_boundary"]},
        "universe": {
            "first_session": str(m.dates[0]),
            "last_session": str(m.dates[-1]),
            "sessions": int(m.shape[1]),
            "tickers_in_window": int(m.present.any(axis=1).sum()),
            "tickers_ending_inside_window": int((m.present.any(axis=1) & ~m.present[:, -1]).sum()),
            "evaluable_ticker_sessions": int(evaluable.sum()),
            "tickers_ever_evaluable": int(evaluable.any(axis=1).sum()),
        },
        "signals": {
            "total": int(len(tick_idx)),
            "signal_rate": float(len(tick_idx) / evaluable.sum()) if evaluable.sum() else None,
            "tickers_with_signals": int(len(np.unique(tick_idx))),
            "skipped_overlap": int(overlap_skipped.sum()),
            "attempted": int(attempt.sum()),
        },
        "rule_trades": rule_stats,
        **baselines,
        "by_year": by_year,
        "lookahead_check": lookahead,
        "warnings": warnings,
    }
    return {"summary": summary, "trades": trades_df, "draws": draws_df}
