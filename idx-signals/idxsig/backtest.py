"""Run a rule over the whole universe and compare it with random entries.

Universe: every ticker in the panel window, including names that later delisted, on
every session where the rule is evaluable. Not a list of past winners.

Random baseline: for every signal that is attempted, `random_draws` replacement entries
are drawn on the same session from the names on which the rule was evaluable that
session, and run through the identical execution model and holding period. Each draw is
a portfolio of the same size and dates as the rule's. The rule's average return and hit
rate are placed in the distribution of the draws.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from . import rules as rule_registry
from .execution import SCORED, STATUS, ExecConfig, Market, execute
from .market import Fees


class LookaheadError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunConfig:
    rule_id: str
    start: str | None = None
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
    lookahead_checks: int = 3


def _equal_with_nan(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(np.nan_to_num(a), np.nan_to_num(b)))


def lookahead_check(rule, m: Market, full: np.ndarray, k: int) -> list[dict]:
    n_sessions = m.shape[1]
    checks = []
    for frac in np.linspace(0.3, 0.9, k) if k else []:
        cut = int(frac * (n_sessions - 1))
        part = rule_registry.signal_array(rule, m.truncate(cut))
        ok = _equal_with_nan(full[:, : cut + 1], part)
        checks.append({"truncated_after": str(m.dates[cut]), "identical": ok})
        if not ok:
            raise LookaheadError(f"{rule.rule_id} changes past signals when future sessions are removed "
                                 f"(truncated after {m.dates[cut]}): it reads ahead")
    return checks


def _summary_stats(net: np.ndarray, status: np.ndarray) -> dict:
    scored = np.isin(status, SCORED)
    vals = net[scored]
    entered = status <= 2
    out = {
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
    return out


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
    )
    end = cfg.end or panel_meta["source_boundary"]
    m = Market.from_panel(panel_df).window(cfg.start, end)
    sig = rule_registry.signal_array(rule, m)
    checks = lookahead_check(rule, m, sig, cfg.lookahead_checks)
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
            if st in SCORED:
                held_until[n] = trades["exit_idx"][i]
            elif st == STATUS.index("INCOMPLETE"):
                held_until[n] = np.iinfo(np.int64).max
    attempt = ~overlap_skipped
    a_tick, a_sig = tick_idx[attempt], sig_idx[attempt]

    rng = np.random.default_rng(cfg.seed)
    draws = cfg.random_draws
    r_tick = np.empty((draws, len(a_sig)), dtype=np.int64)
    for s in np.unique(a_sig):
        cols = np.flatnonzero(a_sig == s)
        pool = np.flatnonzero(evaluable[:, s])
        r_tick[:, cols] = rng.choice(pool, size=(draws, len(cols)), replace=True)
    r_sig = np.broadcast_to(a_sig, (draws, len(a_sig)))
    rand = execute(m, r_tick.ravel(), r_sig.ravel(), exec_cfg) if len(a_sig) else None

    rule_stats = _summary_stats(trades["net_return"][attempt], trades["status"][attempt])
    draw_rows = []
    if rand is not None:
        net = rand["net_return"].reshape(draws, -1)
        status = rand["status"].reshape(draws, -1)
        for d in range(draws):
            st = _summary_stats(net[d], status[d])
            draw_rows.append({"draw": d, "scored": st["scored"], "fill_rate": st["fill_rate"],
                              "hit_rate": st["hit_rate"], "avg_net_return": st["avg_net_return"],
                              "median_net_return": st["median_net_return"]})
        pooled = _summary_stats(rand["net_return"], rand["status"])
    else:
        pooled = _summary_stats(np.array([]), np.array([], dtype=np.int64))
    draws_df = pd.DataFrame(draw_rows)

    def dist(col: str, observed):
        if draws_df.empty or observed is None:
            return None
        v = draws_df[col].dropna().to_numpy()
        if not len(v):
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

    by_year = []
    years = m.dates.astype("datetime64[Y]").astype(int) + 1970
    sig_year = years[a_sig]
    r_year = years[np.broadcast_to(a_sig, (draws, len(a_sig))).ravel()] if rand is not None else None
    for y in sorted(set(sig_year.tolist())):
        sel = sig_year == y
        rs = _summary_stats(trades["net_return"][attempt][sel], trades["status"][attempt][sel])
        row = {"year": int(y), "attempts": rs["attempts"], "scored": rs["scored"], "hit_rate": rs["hit_rate"],
               "avg_net_return": rs["avg_net_return"]}
        if rand is not None:
            rsel = r_year == y
            rr = _summary_stats(rand["net_return"][rsel], rand["status"][rsel])
            row.update({"random_hit_rate": rr["hit_rate"], "random_avg_net_return": rr["avg_net_return"]})
        by_year.append(row)

    warnings = []
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
        "config": {**asdict(cfg), "end": end, "holding_days": holding},
        "execution": {
            "price": "official close; signal at close of s, entry at close of s + entry_lag",
            "lot_size": 100,
            "fees": {"buy": cfg.fee_buy, "sell": cfg.fee_sell},
            "auto_rejection": "entry refused when the entry close is locked at ARA; exit rolls while locked at ARB "
                              "or untraded; regular-board schedule by date, plus 10% special-board limits on "
                              "one-price or sub-Rp50 bars",
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
        "random": {
            "draws": draws,
            "method": "same session, uniform over names where the rule was evaluable, same execution",
            "pooled": pooled,
            "avg_net_return": dist("avg_net_return", rule_stats["avg_net_return"]),
            "hit_rate": dist("hit_rate", rule_stats["hit_rate"]),
        },
        "by_year": by_year,
        "lookahead_checks": checks,
        "warnings": warnings,
    }
    return {"summary": summary, "trades": trades_df, "draws": draws_df}
