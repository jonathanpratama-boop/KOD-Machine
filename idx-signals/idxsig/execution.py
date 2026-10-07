"""Execution model on daily closing prices.

Why closes: the IDX summary only carries an opening price for names with a pre-opening
auction (about 7% of rows), so an open-based model would silently drop most of the
universe. The close is the official closing-auction price for every name.

A signal computed from data through the close of session s is acted on at the close of
session s + entry_lag (default 1, a full session later). The position is sold at the
close of session entry + holding_days, or the first later session where a sale is
possible. Per trade:

  - Entry needs a trade that session and the close not locked at the upper limit (ARA).
  - Shares are whole 100-share lots: floor(notional / (price * 100)) * 100. No lot -> skip.
  - Shares may not exceed `max_participation` of that session's volume. Too big -> skip.
  - Exit needs a trade and the close not locked at the lower limit (ARB); otherwise the
    sale rolls to the next session where it is possible.
  - Splits and other reference-price resets scale the shares held, so value is preserved.
    Cash dividends are not added back (returns are price returns, slightly conservative).
  - A name that stops trading before the exit (delisting, or the data ends) is sold at its
    last traded close, status EXIT_DATA_END, or at zero with data_end_exit="zero".
  - Buy fee and sell fee are charged on traded value.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import market
from .market import LOT_SIZE, Fees

STATUS = (
    "EXITED",               # scored
    "EXIT_DATA_END",        # scored: name stopped trading before the exit
    "INCOMPLETE",           # not scored: holding period runs past the data
    "SKIP_NO_ENTRY_SESSION",
    "SKIP_NOT_TRADED",
    "SKIP_ARA_LOCK",
    "SKIP_LOT",
    "SKIP_LIQUIDITY",
)
SCORED = (0, 1)
BIG = np.iinfo(np.int64).max // 4


@dataclass(frozen=True)
class ExecConfig:
    holding_days: int
    entry_lag: int = 1
    notional: float = 10_000_000.0
    max_participation: float = 0.10
    fees: Fees = field(default_factory=Fees)
    data_end_exit: str = "last_close"  # or "zero"


def _snap_ratio(r: np.ndarray) -> np.ndarray:
    """Snap a reference reset to a simple n/m split ratio when it is within 1% of one."""
    cands = np.array(sorted({n / m for n in range(1, 21) for m in range(1, 21)}))
    out = r.copy()
    finite = np.isfinite(r) & (r > 0)
    pos = np.searchsorted(cands, r[finite]).clip(1, len(cands) - 1)
    lo, hi = cands[pos - 1], cands[pos]
    best = np.where(np.abs(r[finite] / lo - 1) < np.abs(r[finite] / hi - 1), lo, hi)
    out[finite] = np.where(np.abs(r[finite] / best - 1) < 0.01, best, r[finite])
    return out


class Market:
    """Dense (ticker x session) arrays. Column d only depends on data up to session d."""

    FIELDS = ("close", "prev", "high", "low", "volume", "value", "present", "tradeable",
              "lock_up", "lock_down", "ca_ratio", "share_factor")

    def __init__(self, tickers, dates, **arrays):
        self.tickers = np.asarray(tickers)
        self.dates = np.asarray(dates, dtype="datetime64[D]")
        for name in self.FIELDS:
            setattr(self, name, arrays[name])

    @property
    def shape(self):
        return self.close.shape

    @classmethod
    def from_panel(cls, df: pd.DataFrame) -> "Market":
        tickers = np.array(sorted(df["ticker"].unique()))
        dates = np.array(sorted(df["date"].unique()), dtype="datetime64[D]")
        ti = pd.Index(tickers).get_indexer(df["ticker"])
        di = pd.Index(dates).get_indexer(df["date"].to_numpy().astype("datetime64[D]"))
        shape = (len(tickers), len(dates))

        def dense(col):
            out = np.full(shape, np.nan)
            out[ti, di] = df[col].to_numpy(dtype=float, na_value=np.nan)
            return out

        close, prev, high, low = dense("close"), dense("previous"), dense("high"), dense("low")
        volume, value = dense("volume"), dense("value")
        present = np.zeros(shape, dtype=bool)
        present[ti, di] = True
        return cls.build(tickers, dates, close, prev, high, low, volume, value, present)

    @classmethod
    def build(cls, tickers, dates, close, prev, high, low, volume, value, present) -> "Market":
        tradeable = present & (np.nan_to_num(volume) > 0) & (np.nan_to_num(close) > 0)
        day_grid = np.broadcast_to(np.asarray(dates, dtype="datetime64[D]"), close.shape)
        ref = np.where(np.isfinite(prev) & (prev > 0), prev, np.nan)
        safe_ref = np.nan_to_num(ref, nan=1.0)
        ara, arb = market.limits(safe_ref, day_grid)
        sp_ara, sp_arb = market.special_limits(safe_ref)
        one_price = (high == low) & (low == close)
        sub50 = ((close < 50) | (ref < 50)) & (day_grid < np.datetime64("2026-09-28"))
        thin = one_price | sub50
        has_ref = np.isfinite(ref)
        lock_up = tradeable & has_ref & ((close >= ara) | (thin & (close >= sp_ara)))
        lock_down = tradeable & has_ref & (close < ref) & ((close <= arb) | (thin & (close <= sp_arb)))
        # Reference resets (splits, rights): previous close vs today's reference price.
        last_close = pd.DataFrame(np.where(present, close, np.nan)).ffill(axis=1).shift(1, axis=1).to_numpy()
        raw = last_close / ref
        reset = present & np.isfinite(raw) & (np.abs(1 / raw - 1) > 0.005)
        ca_ratio = np.where(reset, _snap_ratio(np.where(reset, raw, 1.0)), 1.0)
        share_factor = np.cumprod(ca_ratio, axis=1)
        return cls(tickers, dates, close=close, prev=prev, high=high, low=low, volume=volume, value=value,
                   present=present, tradeable=tradeable, lock_up=lock_up, lock_down=lock_down,
                   ca_ratio=ca_ratio, share_factor=share_factor)

    def window(self, start=None, end=None) -> "Market":
        lo = 0 if start is None else int(np.searchsorted(self.dates, np.datetime64(start, "D"), side="left"))
        hi = len(self.dates) if end is None else int(np.searchsorted(self.dates, np.datetime64(end, "D"), side="right"))
        return self.slice(lo, hi)

    def slice(self, lo: int, hi: int) -> "Market":
        arrays = {name: getattr(self, name)[:, lo:hi] for name in self.FIELDS}
        if lo:
            arrays["share_factor"] = np.cumprod(arrays["ca_ratio"], axis=1)
        return Market(self.tickers, self.dates[lo:hi], **arrays)

    def truncate(self, last: int) -> "Market":
        """Sessions 0..last only. Used to prove a rule never reads ahead."""
        return self.slice(0, last + 1)


def execute(m: Market, tick_idx: np.ndarray, sig_idx: np.ndarray, cfg: ExecConfig) -> dict:
    """Simulate one trade per (ticker index, signal session index). Vectorized."""
    tick_idx = np.asarray(tick_idx, dtype=np.int64)
    sig_idx = np.asarray(sig_idx, dtype=np.int64)
    n_trades = len(tick_idx)
    n_sessions = m.shape[1]
    status = np.full(n_trades, -1, dtype=np.int64)
    entry = sig_idx + cfg.entry_lag
    status[entry >= n_sessions] = STATUS.index("SKIP_NO_ENTRY_SESSION")
    e = np.minimum(entry, n_sessions - 1)
    open_ = status < 0

    traded = m.tradeable[tick_idx, e]
    status[open_ & ~traded] = STATUS.index("SKIP_NOT_TRADED")
    open_ = status < 0
    status[open_ & m.lock_up[tick_idx, e]] = STATUS.index("SKIP_ARA_LOCK")
    open_ = status < 0

    entry_price = np.nan_to_num(m.close[tick_idx, e])
    with np.errstate(divide="ignore", invalid="ignore"):
        lots = np.floor(cfg.notional / (entry_price * LOT_SIZE))
    lots = np.where(np.isfinite(lots), lots, 0)
    shares = lots * LOT_SIZE
    status[open_ & (shares <= 0)] = STATUS.index("SKIP_LOT")
    open_ = status < 0
    too_big = shares > cfg.max_participation * np.nan_to_num(m.volume[tick_idx, e])
    status[open_ & too_big] = STATUS.index("SKIP_LIQUIDITY")
    open_ = status < 0

    # Exit search.
    sellable = m.tradeable & ~m.lock_down
    idx = np.where(sellable, np.arange(n_sessions)[None, :], BIG)
    next_sellable = np.minimum.accumulate(idx[:, ::-1], axis=1)[:, ::-1]
    present_idx = np.where(m.present, np.arange(n_sessions)[None, :], -1)
    last_present = present_idx.max(axis=1)
    traded_idx = np.where(m.tradeable, np.arange(n_sessions)[None, :], -1)
    last_traded = traded_idx.max(axis=1)

    target = e + cfg.holding_days
    within = target < n_sessions
    found = np.where(within, next_sellable[tick_idx, np.minimum(target, n_sessions - 1)], BIG)
    gone = last_present[tick_idx] < n_sessions - 1  # the name left the data before its end
    exit_idx = np.where(found < BIG, found, -1)
    data_end = open_ & (found >= BIG) & gone & (last_traded[tick_idx] >= e)
    exit_idx = np.where(data_end, last_traded[tick_idx], exit_idx)
    incomplete = open_ & (found >= BIG) & ~data_end
    status[incomplete] = STATUS.index("INCOMPLETE")
    status[data_end] = STATUS.index("EXIT_DATA_END")
    status[open_ & ~incomplete & ~data_end] = STATUS.index("EXITED")

    scored = np.isin(status, SCORED)
    x = np.where(scored, exit_idx, e)
    exit_price = np.where(scored, np.nan_to_num(m.close[tick_idx, x]), np.nan)
    if cfg.data_end_exit == "zero":
        exit_price = np.where(status == STATUS.index("EXIT_DATA_END"), 0.0, exit_price)
    factor = m.share_factor[tick_idx, x] / m.share_factor[tick_idx, e]
    exit_shares = shares * factor
    buy_value = shares * entry_price
    cost = buy_value * (1 + cfg.fees.buy)
    proceeds = exit_shares * exit_price * (1 - cfg.fees.sell)
    with np.errstate(divide="ignore", invalid="ignore"):
        net = np.where(scored, proceeds / cost - 1, np.nan)
        gross = np.where(scored, exit_shares * exit_price / buy_value - 1, np.nan)
    return {
        "ticker_idx": tick_idx,
        "signal_idx": sig_idx,
        "entry_idx": np.where(status >= 3, -1, e),
        "exit_idx": np.where(scored, x, -1),
        "status": status,
        "entry_price": np.where(status >= 3, np.nan, entry_price),
        "shares": np.where(status >= 3, 0, shares),
        "exit_price": exit_price,
        "share_factor": np.where(scored, factor, np.nan),
        "rolled_sessions": np.where(scored & (status == 0), x - target, 0),
        "gross_return": gross,
        "net_return": net,
    }
