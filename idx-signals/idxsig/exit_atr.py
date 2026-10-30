"""EXIT-ATR-v1: one volatility trailing exit (research/EXIT_ATR_v1/cloud/PROTOCOL.md).

Pure numpy, no other idxsig imports, so the comparison can run it next to E2's original harness code
(commit 21345b1) without mixing package versions.

- ATR: arithmetic mean of 14 true ranges from the completed daily bars s-13..s (s = signal day, decided at
  its close); the first true range uses the close of bar s-14. True range = max(high - low,
  |high - previous close|, |low - previous close|).
- Initial stop = entry price - 3 x ATR, active from the entry bar. After each completed hourly bar the
  highest observed price since entry is updated (it starts at the entry price) and the stop becomes
  max(previous stop, highest - 3 x ATR), active from the NEXT bar. The stop never moves down. No take-profit.
- Fills within a bar use only the stop set before that bar: an open at or below the stop fills at the open
  (STOP_GAP); otherwise a low at or below the stop fills at the stop (STOP). Missing bars offer no fill and
  do not move the stop. Conservative variant: on the first bar after a missing hour, a stop trigger fills at
  that bar's low (STOP_GAP_WORST).
- A position the stop never closes is NOT_STOPPED; the caller exits it exactly as the original model does.
"""

from __future__ import annotations

import numpy as np

MULT = 3.0
ATR_BARS = 14


def true_ranges(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """True ranges of bars 1..n-1 of consecutive daily bars (bar 0 supplies only its close)."""
    high, low, close = (np.asarray(a, dtype=float) for a in (high, low, close))
    prev = close[:-1]
    return np.maximum.reduce([high[1:] - low[1:], np.abs(high[1:] - prev), np.abs(low[1:] - prev)])


def atr_at_signal(high, low, close, consecutive: bool) -> float | None:
    """ATR from exactly 15 consecutive daily bars s-14..s, oldest first. None when the warm-up is invalid:
    not 15 bars, not consecutive days, a non-finite value, high < low, low <= 0, close <= 0, or ATR <= 0."""
    high, low, close = (np.asarray(a, dtype=float) for a in (high, low, close))
    if (
        not consecutive
        or len(high) != ATR_BARS + 1
        or len(low) != ATR_BARS + 1
        or len(close) != ATR_BARS + 1
    ):
        return None
    if not (np.isfinite(high).all() and np.isfinite(low).all() and np.isfinite(close).all()):
        return None
    if (high < low).any() or (low <= 0).any() or (close <= 0).any():
        return None
    atr = float(true_ranges(high, low, close).mean())
    return atr if atr > 0 else None


def trail(
    open_,
    high,
    low,
    present,
    entry_price: float,
    atr: float,
    mult: float = MULT,
    conservative_gaps: bool = False,
) -> dict:
    """Walk the hourly bars of one trade window (index 0 = the entry bar, whose open is the entry; the last
    index = the last bar the original model holds). Arrays may contain NaN where `present` is False."""
    open_, high, low = (np.asarray(a, dtype=float) for a in (open_, high, low))
    present = np.asarray(present, dtype=bool)
    stop = entry_price - mult * atr
    out = {
        "initial_stop": stop,
        "reason": "NOT_STOPPED",
        "exit_price": None,
        "exit_bar": None,
        "raises": 0,
        "final_stop": stop,
        "highest": entry_price,
        "bars_seen": 0,
        "last_present_bar": None,
    }
    highest = entry_price
    gap_before = False
    for b in range(len(present)):
        if not present[b]:
            gap_before = out["bars_seen"] > 0  # a missing hour after the position was opened
            continue
        out["bars_seen"] += 1
        out["last_present_bar"] = b
        o, h, l = open_[b], high[b], low[b]
        if conservative_gaps and gap_before and l <= stop:
            out.update(reason="STOP_GAP_WORST", exit_price=float(l), exit_bar=b)
            break
        if o <= stop:
            out.update(reason="STOP_GAP", exit_price=float(o), exit_bar=b)
            break
        if l <= stop:
            out.update(reason="STOP", exit_price=float(stop), exit_bar=b)
            break
        gap_before = False
        highest = max(highest, h)
        new = max(stop, highest - mult * atr)
        if new > stop:
            out["raises"] += 1
        stop = new
        out["final_stop"], out["highest"] = stop, highest
    return out


def trailing_exit(
    open_,
    high,
    low,
    present,
    entry_price: float,
    atr: float,
    original_exit_price: float,
    conservative_gaps: bool = False,
) -> dict:
    """Arm B for one trade: the trailing stop over the original model's holding window; a position the stop
    never closes leaves exactly as the original model leaves (same session, same price), so its return is
    identical in both arms. held_bars counts hourly bars from the entry bar through the exit bar."""
    r = trail(open_, high, low, present, entry_price, atr, conservative_gaps=conservative_gaps)
    if r["exit_bar"] is None:
        r.update(exit_price=float(original_exit_price), held_bars=len(present))
    else:
        r["held_bars"] = r["exit_bar"] + 1
    return r


def net_return(entry_price, exit_price, per_side: float):
    """Net return with a symmetric per-side cost (fee plus slippage), as E2's harness charges it:
    exit x (1 - cost) / (entry x (1 + cost)) - 1."""
    entry_price, exit_price = (
        np.asarray(entry_price, dtype=float),
        np.asarray(exit_price, dtype=float),
    )
    return exit_price * (1 - per_side) / (entry_price * (1 + per_side)) - 1
