"""FLOW_IDX_v1 (research/FLOW_IDX_v1/PROTOCOL.md): flow features from the archived IDX daily summaries.

Foreign buy and sell volume, the closing best-bid and best-offer queue volumes and negotiated-market value, none of
which the price panel keeps. Every feature at session u uses sessions up to u's close only. `load_raw` reads the
mirror's raw per-stock files named in a manifest (rows after `last` are never read) onto the study market's
(ticker x session) grid; `features` turns them into the eight protocol features; `hot_mask` is the cross-sectional
volatility key of the IDX_HOT family.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .provenance import PKG_ROOT, read_manifest

RAW_COLS = [
    "volume",
    "value",
    "foreign_buy",
    "foreign_sell",
    "bid_volume",
    "offer_volume",
    "non_regular_value",
]
NAMES = ("fnet5", "fnet20", "fpart20", "bidq1", "bidq5", "bidx1", "blk5", "blk20")


def load_raw(manifest, tickers, dates, last: str) -> dict[str, np.ndarray]:
    """{column: (tickers x sessions)}; NaN where the name has no row on that session of the grid."""
    _, records = read_manifest(manifest)
    idx = pd.DatetimeIndex(np.asarray(dates).astype("datetime64[ns]"))
    pos = {t: i for i, t in enumerate(tickers)}
    out = {c: np.full((len(tickers), len(idx)), np.nan) for c in RAW_COLS}
    for rec in records:
        if "ticker" not in rec or rec["ticker"] not in pos:
            continue
        df = pd.read_csv(PKG_ROOT / rec["path"], usecols=["date", *RAW_COLS])
        df["date"] = pd.to_datetime(df["date"].str[:10])
        df = (
            df[df["date"] <= pd.Timestamp(last)]
            .drop_duplicates("date", keep="last")
            .set_index("date")
            .reindex(idx)
        )
        for c in RAW_COLS:
            out[c][pos[rec["ticker"]]] = df[c].to_numpy(float)
    return out


def _roll(a: np.ndarray, window: int, minp: int, how: str) -> np.ndarray:
    return getattr(pd.DataFrame(a.T).rolling(window, min_periods=minp), how)().to_numpy().T


def _ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.isfinite(num) & np.isfinite(den) & (den > 0), num / den, np.nan)


def features(raw: dict[str, np.ndarray], tradeable: np.ndarray) -> dict[str, np.ndarray]:
    t = lambda k: np.where(tradeable, raw[k], np.nan)  # noqa: E731
    vol, val, fb, fs, bv, ov, nrv = (
        t(k)
        for k in (
            "volume",
            "value",
            "foreign_buy",
            "foreign_sell",
            "bid_volume",
            "offer_volume",
            "non_regular_value",
        )
    )
    f = {}
    for name, w, mn in (("fnet5", 5, 4), ("fnet20", 20, 15)):
        f[name] = _ratio(_roll(fb - fs, w, mn, "sum"), _roll(vol, w, mn, "sum"))
    f["fpart20"] = _ratio(_roll(fb + fs, 20, 15, "sum"), 2.0 * _roll(vol, 20, 15, "sum"))
    q = _ratio(bv, bv + ov)
    f["bidq1"] = q
    f["bidq5"] = _roll(q, 5, 3, "mean")
    med = _roll(vol, 20, 10, "median")
    prior = np.full(med.shape, np.nan)
    prior[:, 1:] = med[:, :-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        f["bidx1"] = np.where(
            np.isfinite(bv) & np.isfinite(prior), np.log10((bv + 1.0) / (prior + 1.0)), np.nan
        )
    for name, w, mn in (("blk5", 5, 4), ("blk20", 20, 15)):
        n = _roll(nrv, w, mn, "sum")
        f[name] = _ratio(n, _roll(val, w, mn, "sum") + n)
    return {k: f[k] for k in NAMES}


def hot_mask(vol20: np.ndarray, ok: np.ndarray, q: float, min_names: int = 20) -> np.ndarray:
    """True where vol20 is at or above the q-quantile of vol20 across the names `ok` at that session."""
    hot = np.zeros(vol20.shape, dtype=bool)
    for u in range(vol20.shape[1]):
        x = vol20[ok[:, u], u]
        x = x[np.isfinite(x)]
        if len(x) >= min_names:
            hot[:, u] = np.isfinite(vol20[:, u]) & (vol20[:, u] >= np.quantile(x, q))
    return hot
