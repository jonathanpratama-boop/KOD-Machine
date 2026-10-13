"""Market profiles: the few things that differ between the markets the harness studies.

IDX is the original market and its numbers are unchanged. US and CRYPTO costs are explicit
assumptions (no commission data or quoted spreads are in the bars): a per-side cost by price
tier standing in for commission + half the spread + slippage, so cheap, illiquid names pay
more. They are labelled assumptions in every run.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Profile:
    market: str
    currency: str
    lot_size: int
    price_limits: bool          # IDX auto-rejection limits; none in US / crypto daily bars
    band_edges: tuple           # upper edges of the price bands used for matching
    band_names: tuple
    fee_buy: float
    fee_sell: float
    cost_tiers: tuple           # ((price upper bound, extra per-side cost), ...); applied on top of fees
    notional: float             # per-trade notional in the profile currency
    entry: str                  # "close": next session's close; "open": next session's open
    venue: str
    assumption_note: str = ""
    # Short side (research/E4): carry charged per session held, on the sold notional, as a fraction;
    # an assumption standing in for stock borrow (US) or perpetual-futures funding (crypto). None: no
    # short side is modelled for this market.
    short_carry_per_session: float | None = None
    short_note: str = ""

    def per_side_cost(self, price: np.ndarray) -> np.ndarray:
        price = np.asarray(price, dtype=float)
        out = np.zeros(price.shape)
        if not self.cost_tiers:
            return out
        bounds = np.array([b for b, _ in self.cost_tiers])
        costs = np.array([c for _, c in self.cost_tiers])
        idx = np.searchsorted(bounds, np.nan_to_num(price, nan=0.0), side="right").clip(0, len(costs) - 1)
        return costs[idx]

    def band(self, close: np.ndarray) -> np.ndarray:
        band = np.searchsorted(np.array(self.band_edges), close, side="left").astype(np.int8)
        return np.where(np.isfinite(close), band, -1).astype(np.int8)


IDX = Profile("IDX", "IDR", 100, True, (200, 5000), ("<=Rp200", "<=Rp5000", ">Rp5000"), 0.0015, 0.0025, (),
              10_000_000.0, "close", "IDX (Indonesia Stock Exchange)")
US = Profile("US", "USD", 1, False, (1, 5, 20), ("<$1", "$1-5", "$5-20", ">$20"), 0.0, 0.0000278,
             ((1, 0.015), (5, 0.005), (20, 0.0015), (float("inf"), 0.0005)), 5_000.0, "open",
             "US exchanges (Nasdaq / NYSE / NYSE American / Cboe)",
             "costs assumed: per side 1.5% under $1, 0.5% $1-5, 0.15% $5-20, 0.05% above, plus the SEC fee on sales",
             short_carry_per_session=0.003,
             short_note="short side assumed: borrow 0.3% per session (about 75% a year: a hard-to-borrow rate, "
                        "as names that just spiked usually are), locate assumed available; not point-in-time")
CRYPTO = Profile("CRYPTO", "USDT", 1, False, (0.01, 1, 100), ("<0.01", "0.01-1", "1-100", ">100"), 0.001, 0.001,
                 ((float("inf"), 0.001),), 5_000.0, "open", "Binance spot (reference prices; USDT pairs)",
                 "costs assumed: 0.1% taker fee + 0.1% slippage per side; sessions are UTC days",
                 short_carry_per_session=0.0005,
                 short_note="short side assumed: a perpetual-futures short at the spot reference price, funding "
                            "0.05% per UTC day paid by the short (a conservative stand-in: after a pump longs "
                            "usually pay), 0.1% fee + 0.1% slippage per side; perpetuals may not exist for "
                            "every pair, and liquidation risk is not modelled")
PROFILES = {p.market: p for p in (IDX, US, CRYPTO)}
