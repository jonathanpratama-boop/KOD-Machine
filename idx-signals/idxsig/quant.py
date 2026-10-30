"""Quant-grade building blocks (research/QUANT_ENGINE_*): cross-sectional ranking, walk-forward signal combination,
autocorrelation-robust statistics, factor alpha and a market-impact cost model. Pure numpy, no I/O.

Conventions: a panel is an array of shape (months, stocks); NaN means not eligible or not observed. Month t's forward
return is realised by the formation date of month t+1, so a model scoring month t may train on months <= t - 1 - embargo.
"""

from __future__ import annotations

import numpy as np


def rank_normalize(x: np.ndarray) -> np.ndarray:
    """Cross-sectional ranks mapped to (-0.5, 0.5); non-finite entries stay NaN."""
    out = np.full(x.shape, np.nan)
    ok = np.isfinite(x)
    n = ok.sum()
    if n < 2:
        return out
    r = np.empty(n)
    r[np.argsort(x[ok], kind="stable")] = np.arange(n)
    out[ok] = (r + 0.5) / n - 0.5
    return out


def rank_ic(score: np.ndarray, fwd: np.ndarray, min_n: int = 30) -> float:
    """Spearman correlation of one month's score with the forward return (NaN if fewer than min_n pairs)."""
    ok = np.isfinite(score) & np.isfinite(fwd)
    if ok.sum() < min_n:
        return float("nan")
    a, b = (
        rank_normalize(np.where(ok, score, np.nan))[ok],
        rank_normalize(np.where(ok, fwd, np.nan))[ok],
    )
    return float(np.corrcoef(a, b)[0, 1])


def newey_west_se_mean(x: np.ndarray, lags: int) -> float:
    """Newey-West (Bartlett) standard error of the mean of a series."""
    x = np.asarray(x, float)
    n = len(x)
    e = x - x.mean()
    s = float(e @ e) / n
    for k in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - k / (lags + 1)) * float(e[k:] @ e[:-k]) / n
    return float(np.sqrt(max(s, 0.0) / n))


def series_stats(x: np.ndarray, lags: int = 6) -> dict:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    se = newey_west_se_mean(x, lags)
    return {
        "n": int(len(x)),
        "mean": float(x.mean()),
        "sd": float(x.std(ddof=1)),
        "t_nw": float(x.mean() / se) if se > 0 else float("nan"),
        "t_iid": float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))),
        "share_positive": float((x > 0).mean()),
    }


def quintile_means(score: np.ndarray, fwd: np.ndarray, q: int = 5) -> np.ndarray:
    ok = np.flatnonzero(np.isfinite(score) & np.isfinite(fwd))
    order = ok[np.argsort(score[ok], kind="stable")]
    k = len(order) // q
    return np.array(
        [fwd[order[i * k : (i + 1) * k if i < q - 1 else len(order)]].mean() for i in range(q)]
    )


def quintile_members(score: np.ndarray, q: int = 5) -> list[np.ndarray]:
    ok = np.flatnonzero(np.isfinite(score))
    order = ok[np.argsort(score[ok], kind="stable")]
    k = len(order) // q
    return [order[i * k : (i + 1) * k if i < q - 1 else len(order)] for i in range(q)]


def ridge_fit(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """Closed-form ridge without intercept (inputs are rank-normalised, so already centred)."""
    return np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)


def walk_forward_scores(
    features: list[np.ndarray],
    fwd: np.ndarray,
    first: int,
    lam: float,
    embargo: int = 1,
    min_train_months: int = 24,
) -> tuple[np.ndarray, np.ndarray]:
    """Expanding-window ridge. For month t >= first: train on months m <= t - 1 - embargo (their forward returns are
    realised by t), rank-normalise features and target within each month, score month t from its own features only.
    Returns (scores[t, stock], betas[t, feature]); rows before `first` are NaN."""
    T, N = fwd.shape
    F = len(features)
    Xn = [
        np.stack([rank_normalize(f[m]) for f in features], axis=-1) for m in range(T)
    ]  # (N, F) per month
    yn = [rank_normalize(fwd[m]) for m in range(T)]
    scores, betas = np.full((T, N), np.nan), np.full((T, F), np.nan)
    for t in range(first, T):
        rows = [m for m in range(t - embargo) if m >= 0]
        if len(rows) < min_train_months:
            continue
        X = np.concatenate(
            [Xn[m][np.isfinite(Xn[m]).all(axis=1) & np.isfinite(yn[m])] for m in rows]
        )
        y = np.concatenate(
            [yn[m][np.isfinite(Xn[m]).all(axis=1) & np.isfinite(yn[m])] for m in rows]
        )
        if len(y) < 1000:
            continue
        b = ridge_fit(X, y, lam)
        betas[t] = b
        ok = np.isfinite(Xn[t]).all(axis=1)
        scores[t, ok] = Xn[t][ok] @ b
    return scores, betas


def ols_hac(y: np.ndarray, X: np.ndarray, lags: int = 6) -> dict:
    """OLS of y on X (an intercept is added) with Newey-West standard errors. Returns alpha, betas, their t-stats."""
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    n, k = X.shape
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, min(lags, n - 1) + 1):
        w = 1 - L / (lags + 1)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(cov))
    return {
        "alpha": float(beta[0]),
        "alpha_t": float(beta[0] / se[0]),
        "betas": beta[1:].tolist(),
        "beta_t": (beta[1:] / se[1:]).tolist(),
        "r2": float(1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))),
        "n": int(n),
    }


def impact_cost_per_side(
    trade_value, adv_value, daily_vol, half_spread: float = 0.0005, c: float = 0.7
):
    """Fraction of traded value lost on one side: half the spread plus square-root market impact,
    c * daily_vol * sqrt(trade_value / average daily dollar volume). c ~ 0.5-1 in the literature; 0.7 assumed."""
    return half_spread + c * np.asarray(daily_vol) * np.sqrt(
        np.asarray(trade_value) / np.asarray(adv_value)
    )


def net_spread_at_aum(
    gross: np.ndarray,
    turnover_long: np.ndarray,
    turnover_short: np.ndarray,
    adv_long: np.ndarray,
    adv_short: np.ndarray,
    vol_long: np.ndarray,
    vol_short: np.ndarray,
    n_leg: np.ndarray,
    aum: float,
    half_spread: float = 0.0005,
    c: float = 0.7,
) -> np.ndarray:
    """Monthly long-short spread net of costs for a book of `aum` (half long, half short, equal weight in n_leg names).
    A replaced name is sold and its successor bought in full, so each side trades position = aum / (2 n_leg)."""
    pos = aum / (2 * n_leg)
    cl = impact_cost_per_side(pos, adv_long, vol_long, half_spread, c)
    cs = impact_cost_per_side(pos, adv_short, vol_short, half_spread, c)
    return gross - 2 * turnover_long * cl - 2 * turnover_short * cs


def breakeven_aum(net_mean_by_aum: dict[float, float]) -> float | None:
    """Smallest AUM on the grid (log-interpolated) at which mean net spread falls to zero; None if it never does,
    0.0 if it is already non-positive at the smallest AUM."""
    items = sorted(net_mean_by_aum.items())
    if items[0][1] <= 0:
        return 0.0
    for (a0, m0), (a1, m1) in zip(items, items[1:]):
        if m1 <= 0 < m0:
            return float(np.exp(np.log(a0) + (np.log(a1) - np.log(a0)) * m0 / (m0 - m1)))
    return None
