"""Synthetic markets for tests. No network, no real data."""

from __future__ import annotations

import numpy as np
import pandas as pd

from idxsig.execution import Market


def flat_market(n_tickers=3, n_sessions=20, price=1000.0, volume=1_000_000.0, start="2024-01-02"):
    """Every name trades every session at one price. Mutate the arrays, then call rebuild()."""
    dates = np.busday_offset(np.datetime64(start, "D"), np.arange(n_sessions), roll="forward")
    shape = (n_tickers, n_sessions)
    arrays = {
        "close": np.full(shape, price),
        "prev": np.full(shape, price),
        "high": np.full(shape, price * 1.01),
        "low": np.full(shape, price * 0.99),
        "volume": np.full(shape, volume),
        "value": np.full(shape, price * volume),
        "present": np.ones(shape, dtype=bool),
    }
    tickers = np.array([f"T{i:03d}" for i in range(n_tickers)])
    return tickers, dates, arrays


def rebuild(tickers, dates, arrays) -> Market:
    a = arrays
    return Market.build(tickers, dates, a["close"], a["prev"], a["high"], a["low"], a["volume"], a["value"], a["present"])


def random_walk_panel(n_tickers=40, n_sessions=160, seed=7, start="2023-01-02",
                      drift: dict | None = None, delist: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Panel DataFrame + manifest-like meta. drift: {ticker_index: daily drift}; delist: {ticker_index: last session}."""
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime(np.busday_offset(np.datetime64(start, "D"), np.arange(n_sessions), roll="forward"))
    rows = []
    for i in range(n_tickers):
        price = float(rng.choice([150, 480, 1500, 4000, 9000]))
        mu = (drift or {}).get(i, 0.0)
        last = (delist or {}).get(i, n_sessions - 1)
        for d in range(last + 1):
            prev = price
            step = np.clip(rng.normal(mu, 0.02), -0.06, 0.06)
            from idxsig.market import floor_tick

            price = float(max(floor_tick(np.array([prev * (1 + step)]))[0], 50.0))
            vol = int(rng.integers(50_000, 5_000_000))
            rows.append({
                "date": dates[d], "ticker": f"S{i:03d}", "source": "synthetic", "previous": int(prev), "open": pd.NA,
                "high": int(max(prev, price)), "low": int(min(prev, price)), "close": int(price),
                "volume": vol, "value": int(vol * price), "frequency": 100,
            })
    df = pd.DataFrame(rows)
    for col in ("previous", "open", "high", "low", "close", "volume", "value", "frequency"):
        df[col] = df[col].astype("Int64")
    meta = {"sha256": "synthetic", "panel": "synthetic", "source_boundary": str(dates[-1].date())}
    return df, meta
