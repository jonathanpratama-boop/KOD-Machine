"""Event studies on the execution harness for the US panel (entries at the open).

A table of events with a ticker and the calendar date an item became public (a 10-K's EDGAR filing date, say) turns into harness signals; the harness executes them exactly
as it executes a detector's signals (as-traded units, decision-time capacity, the US profile's cost tiers) and each event's control comes from the harness's own matched random
baseline (controls.py): the same session, the same price band / liquidity / volatility / momentum / drawdown / age buckets, the same plan. idx_events.py is the IDX
counterpart (close entries, WIB clock) and is not touched.

Timing. The first obtainable entry is the open of the first session strictly after the item's date, whatever time of day it was made public (`entry_signal_session`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import backtest, controls
from .execution import SCORED, STATUS, ExecConfig, Market, execute
from .idx_events import Prepared, evaluable_matrix, filled, mean_over_scored, status_counts  # noqa: F401  (re-exported)
from .market import Fees
from .profiles import US


def entry_signal_session(dates: np.ndarray, public_date) -> int | None:
    """Index s of the harness signal session for an item public on `public_date`: the harness buys at the open of s + 1, which is the first session strictly after the date.
    None if no session precedes that entry. If the date is on or after the last session, s + 1 is past the window and the harness reports SKIP_NO_ENTRY_SESSION."""
    day = np.datetime64(pd.Timestamp(public_date).date(), "D")
    e = int(np.searchsorted(dates, day, side="right"))
    return e - 1 if e >= 1 else None


def prepare_us(df: pd.DataFrame, start: str, end: str, controls_version: str = "v2") -> Prepared:
    """The market over the window with as-traded units, plus the matching features and the controls' eligibility, all computed on the whole panel and then windowed
    (history before the window is available at its first session). Nothing after `end` is loaded."""
    df = df[df["date"] <= pd.Timestamp(end)]
    full = Market.from_panel(df, price_limits=US.price_limits)
    full = full.with_units(backtest._dense(full, df, "unit_factor", 1.0))
    lo, hi = full.bounds(start, end)
    feats = {k: v[:, lo:hi] for k, v in controls.features(full, controls_version, US.band_edges, as_traded=True).items()}
    return Prepared(full.slice(lo, hi), feats, evaluable_matrix(full)[:, lo:hi], lo, hi)


def us_config(hold: int, notional: float | None = None, entry_lag: int = 1, max_participation: float = 0.10) -> ExecConfig:
    """The US profile's execution plan, as backtest.run builds it for market 'US' (E9's configuration), with a given holding period."""
    return ExecConfig(lot_size=US.lot_size, entry_price=US.entry, cost_tiers=US.cost_tiers, holding_days=hold, entry_lag=entry_lag,
                      notional=US.notional if notional is None else notional, max_participation=max_participation, fees=Fees(US.fee_buy, US.fee_sell),
                      data_end_exit="last_close", ca_mode="adjusted", units="as_traded", fill_model="B")


def run_events(prep: Prepared, events: pd.DataFrame, cfg: ExecConfig, draws: int = 200, seed: int = 20261007, controls_version: str = "v2",
               overlap: str = "skip") -> pd.DataFrame:
    """One row per event whose ticker is in the market: its execution, the mean of its matched controls under the same plan, and the excess. `events` needs `ticker` and
    `public_date` (any other columns are carried along). `status` is the harness status ("SKIP_OVERLAP" for an event while the same name is still held)."""
    m = prep.m
    ev = events.copy().reset_index(drop=True)
    tick = pd.Index(m.tickers).get_indexer(ev["ticker"].astype(str))
    sig = np.array([-1 if (s := entry_signal_session(m.dates, d)) is None else s for d in ev["public_date"]])
    ev["tick_idx"], ev["sig_idx"] = tick, sig
    ev = ev[(tick >= 0) & (sig >= 0)].reset_index(drop=True)
    tick_idx, sig_idx = ev["tick_idx"].to_numpy(np.int64), ev["sig_idx"].to_numpy(np.int64)
    trades = execute(m, tick_idx, sig_idx, cfg)
    skipped = np.zeros(len(ev), dtype=bool)
    if overlap == "skip":
        held_until = {}
        for i, (n, s) in enumerate(zip(tick_idx, sig_idx)):
            if s + cfg.entry_lag <= held_until.get(n, -1):
                skipped[i] = True
                continue
            if trades["exit_idx"][i] >= 0:
                held_until[n] = trades["exit_idx"][i]
            elif trades["status"][i] == STATUS.index("INCOMPLETE"):
                held_until[n] = np.iinfo(np.int64).max
    keep = ~skipped
    a_tick, a_sig = tick_idx[keep], sig_idx[keep]
    control_mean = np.full(len(ev), np.nan)
    control_n = np.zeros(len(ev), dtype=int)
    level = np.full(len(ev), -1)
    drawable = keep.copy()
    drawable[keep] = prep.evaluable[:, a_sig].sum(axis=0) >= 2
    if drawable.any():
        d_tick, d_sig = tick_idx[drawable], sig_idx[drawable]
        matched, lvl = controls.matched_draws(prep.evaluable, prep.feats, d_tick, d_sig, draws, np.random.default_rng(seed + 1), controls_version)
        out = execute(m, matched.ravel(), np.broadcast_to(d_sig, matched.shape).ravel(), cfg)
        net = out["net_return"].reshape(draws, -1)
        scored = np.isin(out["status"], SCORED).reshape(draws, -1) & np.isfinite(net)
        control_mean[drawable] = mean_over_scored(net, scored)
        control_n[drawable] = scored.sum(0)
        level[drawable] = lvl
    day = lambda idx: np.where(idx >= 0, m.dates[np.maximum(idx, 0)].astype(str), "")  # noqa: E731
    status = np.where(skipped, "SKIP_OVERLAP", np.array(STATUS)[trades["status"]])
    scored_ev = np.isin(trades["status"], SCORED) & ~skipped
    ev = ev.assign(signal_date=m.dates[sig_idx].astype(str), entry_date=day(trades["entry_idx"]), exit_date=day(trades["exit_idx"]), status=status,
                   entry_price=trades["entry_price"], exit_price=trades["exit_price"], gross_return=np.where(scored_ev, trades["gross_return"], np.nan),
                   net_return=np.where(scored_ev, trades["net_return"], np.nan), control_mean=control_mean, control_n=control_n, match_level=level)
    ev["excess"] = ev["net_return"] - ev["control_mean"]
    return ev

