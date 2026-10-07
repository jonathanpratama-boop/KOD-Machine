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
  - Corporate actions (ca_mode="registry", what runs use): shares held are scaled only
    through resets the corporate-action registry (corporate_actions.py) verifies as a split,
    reverse split or stock dividend. A trade held across a verified rights issue is
    CORP_ACTION_RIGHTS_ISSUE, across any other reset CORP_ACTION_UNRESOLVED; neither is
    scored, for the rule and the random baselines alike. A rights holder gets rights, not
    free shares, and what they are worth depends on terms the bars lack.
    Earlier modes, kept so older runs stay reproducible: ca_mode="exclude" scales every
    integer reset as a split and excludes the rest (EXCLUDED_CORP_ACTION);
    ca_mode="value_preserving" scales shares by every reset.
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
    "EXCLUDED_CORP_ACTION",  # not scored (ca_mode="exclude"): held across a non-integer reset
    "CORP_ACTION_RIGHTS_ISSUE",  # not scored (ca_mode="registry"): held across a verified rights issue
    "CORP_ACTION_UNRESOLVED",    # not scored (ca_mode="registry"): held across a reset the registry cannot verify
    "SKIP_NO_ENTRY_SESSION",
    "SKIP_NOT_TRADED",
    "SKIP_ARA_LOCK",
    "SKIP_LOT",
    "SKIP_LIQUIDITY",
)
SCORED = (0, 1)
FIRST_SKIP = STATUS.index("SKIP_NO_ENTRY_SESSION")  # statuses from here on never entered
BIG = np.iinfo(np.int64).max // 4


@dataclass(frozen=True)
class ExecConfig:
    holding_days: int
    entry_lag: int = 1
    notional: float = 10_000_000.0
    max_participation: float = 0.10
    fees: Fees = field(default_factory=Fees)
    data_end_exit: str = "last_close"  # or "zero"
    ca_mode: str = "exclude"  # "registry" (needs Market.with_registry), "exclude", "value_preserving"


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
              "lock_up", "lock_down", "ca_ratio", "is_split", "share_factor", "split_factor", "other_ca_count",
              "listed_shares")
    # Set by with_registry(); built from information that postdates the session (later
    # downloads, primary documents), so never shown to a rule (see rules.RuleView).
    REGISTRY_FIELDS = ("reg_factor", "reg_rights", "reg_unresolved")

    def __init__(self, tickers, dates, **arrays):
        self.tickers = np.asarray(tickers)
        self.dates = np.asarray(dates, dtype="datetime64[D]")
        for name in self.FIELDS:
            setattr(self, name, arrays[name])
        for name in self.REGISTRY_FIELDS:
            setattr(self, name, arrays.get(name))
        self.registry_counts = arrays.get("registry_counts")

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
        listed = dense("listed_shares") if "listed_shares" in df else np.full(shape, np.nan)
        present = np.zeros(shape, dtype=bool)
        present[ti, di] = True
        return cls.build(tickers, dates, close, prev, high, low, volume, value, present, listed)

    @classmethod
    def build(cls, tickers, dates, close, prev, high, low, volume, value, present, listed_shares=None) -> "Market":
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
        whole = np.abs(ca_ratio - np.round(ca_ratio)) < 1e-6
        whole_inverse = np.abs(1 / ca_ratio - np.round(1 / ca_ratio)) < 1e-6
        is_split = reset & (((ca_ratio >= 2) & whole) | ((ca_ratio <= 0.5) & whole_inverse))
        return cls(tickers, dates, close=close, prev=prev, high=high, low=low, volume=volume, value=value,
                   present=present, tradeable=tradeable, lock_up=lock_up, lock_down=lock_down,
                   ca_ratio=ca_ratio, is_split=is_split,
                   share_factor=np.cumprod(ca_ratio, axis=1),
                   split_factor=np.cumprod(np.where(is_split, ca_ratio, 1.0), axis=1),
                   other_ca_count=np.cumsum(reset & ~is_split, axis=1),
                   listed_shares=np.full(close.shape, np.nan) if listed_shares is None else listed_shares)

    def with_registry(self, registry) -> "Market":
        """A copy with share scaling from a corporate-action registry (ca_mode="registry")."""
        from .corporate_actions import scaling_arrays

        factor, rights, unresolved, counts = scaling_arrays(self, registry)
        arrays = {name: getattr(self, name) for name in self.FIELDS}
        return Market(self.tickers, self.dates, **arrays, reg_factor=factor, reg_rights=rights,
                      reg_unresolved=unresolved, registry_counts=counts)

    def bounds(self, start=None, end=None) -> tuple[int, int]:
        lo = 0 if start is None else int(np.searchsorted(self.dates, np.datetime64(start, "D"), side="left"))
        hi = len(self.dates) if end is None else int(np.searchsorted(self.dates, np.datetime64(end, "D"), side="right"))
        return lo, hi

    def window(self, start=None, end=None) -> "Market":
        return self.slice(*self.bounds(start, end))

    def slice(self, lo: int, hi: int) -> "Market":
        # Cumulative fields are only ever used as ratios or differences, so a slice keeps them valid.
        arrays = {name: getattr(self, name)[:, lo:hi] for name in self.FIELDS}
        for name in self.REGISTRY_FIELDS:
            if getattr(self, name) is not None:
                arrays[name] = getattr(self, name)[:, lo:hi]
        return Market(self.tickers, self.dates[lo:hi], **arrays, registry_counts=self.registry_counts)

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

    held = np.isin(status, SCORED)
    x = np.where(held, exit_idx, e)
    if cfg.ca_mode == "registry":
        if m.reg_factor is None:
            raise ValueError("ca_mode='registry' needs a market with a corporate-action registry attached "
                             "(Market.with_registry)")
        unresolved = m.reg_unresolved[tick_idx, x] - m.reg_unresolved[tick_idx, e] > 0
        rights = m.reg_rights[tick_idx, x] - m.reg_rights[tick_idx, e] > 0
        status[held & unresolved] = STATUS.index("CORP_ACTION_UNRESOLVED")
        status[held & rights & ~unresolved] = STATUS.index("CORP_ACTION_RIGHTS_ISSUE")
        factor_array = m.reg_factor
    elif cfg.ca_mode == "exclude":
        crossed = m.other_ca_count[tick_idx, x] - m.other_ca_count[tick_idx, e] > 0
        status[held & crossed] = STATUS.index("EXCLUDED_CORP_ACTION")
        factor_array = m.split_factor
    elif cfg.ca_mode == "value_preserving":
        factor_array = m.share_factor
    else:
        raise ValueError(f"unknown ca_mode {cfg.ca_mode!r}")
    scored = np.isin(status, SCORED)
    exit_price = np.where(scored, np.nan_to_num(m.close[tick_idx, x]), np.nan)
    if cfg.data_end_exit == "zero":
        exit_price = np.where(status == STATUS.index("EXIT_DATA_END"), 0.0, exit_price)
    factor = factor_array[tick_idx, x] / factor_array[tick_idx, e]
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
        "entry_idx": np.where(status >= FIRST_SKIP, -1, e),
        "exit_idx": np.where(held, x, -1),  # excluded trades were still held until here
        "status": status,
        "entry_price": np.where(status >= FIRST_SKIP, np.nan, entry_price),
        "shares": np.where(status >= FIRST_SKIP, 0, shares),
        "exit_price": exit_price,
        "share_factor": np.where(scored, factor, np.nan),
        "rolled_sessions": np.where(scored & (status == 0), x - target, 0),
        "gross_return": gross,
        "net_return": net,
    }
