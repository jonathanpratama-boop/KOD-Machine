"""Event studies on the IDX execution harness.

A new kind of IDX event (an insider purchase reported by a news site, a filing, anything with a ticker and a time) costs a
table and a protocol, not a new backtester: this module turns the table into harness signals, lets the harness execute them
exactly as it executes a detector's signals (lots, auto-rejection locks, decision-time capacity, fees, registry-verified
corporate actions) and draws each event's control from the harness's own matched random baseline (controls.py): the same
session, the same price band / liquidity / market-cap / volatility / momentum / drawdown / age buckets, the same plan.

Timing. Closes are the only prices every name has (execution.py), so an event is acted on at a close. `signal_session` maps
the publication time (WIB) to the harness's signal session s, and the harness buys at the close of s + 1:
  - published on a session day at or before CUTOFF (14:30, an hour before the closing auction): bought at that day's close;
  - published later that day, or on a non-session day: bought at the close of the next session.
Nothing here reads a price to decide which events count.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from . import controls
from .execution import SCORED, STATUS, ExecConfig, Market, execute

CUTOFF = (14, 30)            # a session-day publication at or before this WIB time can be bought at that day's close
MIN_HISTORY = 60             # sessions of history a name needs to be an eligible control


def signal_session(dates: np.ndarray, posted: pd.Timestamp) -> int | None:
    """Index of the harness signal session for an event published at `posted` (a tz-aware or naive WIB timestamp), or None if
    there is no earlier session to act from."""
    day = np.datetime64(posted.date(), "D")
    k = int(np.searchsorted(dates, day, side="left"))           # first session on or after the publication day
    is_session = k < len(dates) and dates[k] == day
    in_time = (posted.hour, posted.minute) <= CUTOFF
    s = k if (is_session and not in_time) else k - 1
    return s if s >= 0 else None


def build_signals(m: Market, events: pd.DataFrame) -> pd.DataFrame:
    """events: columns `ticker` and `posted_wib` (ISO string or Timestamp). Returns the events with `tick_idx`, `sig_idx` and
    `mapped` (False with a `reason` when the ticker is not in the market or no session precedes the event)."""
    out = events.copy().reset_index(drop=True)
    posted = pd.to_datetime(out["posted_wib"])
    tick = pd.Index(m.tickers).get_indexer(out["ticker"].str.upper())
    sig = np.array([-1 if (s := signal_session(m.dates, p)) is None else s for p in posted])
    out["tick_idx"], out["sig_idx"] = tick, sig
    out["mapped"] = (tick >= 0) & (sig >= 0)
    out["reason"] = np.where(tick < 0, "NO_TICKER", np.where(sig < 0, "NO_SESSION", ""))
    return out


def evaluable_matrix(m: Market, min_history: int = MIN_HISTORY) -> np.ndarray:
    """Names that can be a control at a session: traded that session and with at least `min_history` sessions of history."""
    return m.tradeable & (np.cumsum(m.present, axis=1) >= min_history)


@dataclass(frozen=True)
class Prepared:
    m: Market                    # the window, with the corporate-action registry when one is given
    feats: dict                  # matching features for the window (computed on the whole panel, then windowed)
    evaluable: np.ndarray        # who can be a control at each session of the window (history counted on the whole panel)
    lo: int
    hi: int


def prepare(df: pd.DataFrame, registry: pd.DataFrame | None, start: str, end: str, controls_version: str = "v2",
            band_edges: tuple = (200, 5000), price_limits: bool = True) -> Prepared:
    df = df[df["date"] <= pd.Timestamp(end)]                     # nothing after the window is ever loaded into the market
    full = Market.from_panel(df, price_limits=price_limits)
    if registry is not None:
        full = full.with_registry(registry)
    lo, hi = full.bounds(start, end)
    feats = {k: v[:, lo:hi] for k, v in controls.features(full, controls_version, band_edges).items()}
    return Prepared(full.slice(lo, hi), feats, evaluable_matrix(full)[:, lo:hi], lo, hi)


def run_events(prep: Prepared, events: pd.DataFrame, cfg: ExecConfig, draws: int = 200, seed: int = 20261007,
               controls_version: str = "v2", overlap: str = "skip") -> pd.DataFrame:
    """One row per mapped event: its execution, the mean of its matched controls under the same plan, and the excess.
    `status` is the harness status ("SKIP_OVERLAP" for an event while the same name is still held). Controls are `draws`
    replacement draws per event from the names that could have been bought that session in the same buckets."""
    m = prep.m
    ev = build_signals(m, events)
    ev = ev[ev["mapped"]].reset_index(drop=True)
    tick_idx, sig_idx = ev["tick_idx"].to_numpy(np.int64), ev["sig_idx"].to_numpy(np.int64)
    trades = execute(m, tick_idx, sig_idx, cfg)
    skipped = np.zeros(len(ev), dtype=bool)
    if overlap == "skip":                                        # as backtest.run: a signal while the name is still held
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
    drawable = keep.copy()                                       # an event needs at least one other name that could be bought
    drawable[keep] = prep.evaluable[:, a_sig].sum(axis=0) >= 2
    if drawable.any():
        d_tick, d_sig = tick_idx[drawable], sig_idx[drawable]
        matched, lvl = controls.matched_draws(prep.evaluable, prep.feats, d_tick, d_sig, draws,
                                              np.random.default_rng(seed + 1), controls_version)
        out = execute(m, matched.ravel(), np.broadcast_to(d_sig, matched.shape).ravel(), cfg)
        net = out["net_return"].reshape(draws, -1)
        scored = np.isin(out["status"], SCORED).reshape(draws, -1)
        with np.errstate(invalid="ignore"):
            control_mean[drawable] = np.where(scored, net, np.nan).sum(0) / np.where(scored.sum(0) > 0, scored.sum(0), np.nan)
        control_n[drawable] = scored.sum(0)
        level[drawable] = lvl
    day = lambda idx: np.where(idx >= 0, m.dates[np.maximum(idx, 0)].astype(str), "")  # noqa: E731
    status = np.where(skipped, "SKIP_OVERLAP", np.array(STATUS)[trades["status"]])
    scored_ev = np.isin(trades["status"], SCORED) & ~skipped
    ev = ev.assign(signal_date=m.dates[sig_idx].astype(str), entry_date=day(trades["entry_idx"]), exit_date=day(trades["exit_idx"]),
                   status=status, entry_price=trades["entry_price"], exit_price=trades["exit_price"],
                   gross_return=np.where(scored_ev, trades["gross_return"], np.nan),
                   net_return=np.where(scored_ev, trades["net_return"], np.nan),
                   control_mean=control_mean, control_n=control_n, match_level=level)
    ev["excess"] = ev["net_return"] - ev["control_mean"]
    return ev


def status_counts(ev: pd.DataFrame) -> dict:
    return {k: int(v) for k, v in ev["status"].value_counts().items()}


def filled(ev: pd.DataFrame) -> pd.DataFrame:
    """Events that were entered and scored, with a control mean from at least one scored draw."""
    return ev[ev["net_return"].notna() & ev["control_mean"].notna()]
