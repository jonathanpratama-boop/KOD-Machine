#!/usr/bin/env python3
"""T6: what USD 1,000 -> USD 10,000 within one year requires. Monte Carlo per PROTOCOL.md."""
import json

import numpy as np
import pandas as pd

import lib
from run_t1_t5 import sma_cross_positions, tsmom_positions

rng = np.random.default_rng(20261101)
N_PATHS, DAYS = 20000, 365


def simulate(daily_returns_matrix):
    """paths x days matrix of simple daily returns -> stats."""
    eq = np.cumprod(1 + daily_returns_matrix, axis=1)
    peak = np.maximum.accumulate(eq, axis=1)
    dd = eq / peak - 1
    hit10 = (eq >= 10).any(axis=1)
    ruin50 = (dd <= -0.5).any(axis=1)
    # which came first
    t_hit = np.where(hit10, np.argmax(eq >= 10, axis=1), DAYS + 1)
    t_ruin = np.where(ruin50, np.argmax(dd <= -0.5, axis=1), DAYS + 1)
    return {"P_10x_within_1y": round(float(hit10.mean()), 4),
            "P_50pct_drawdown_within_1y": round(float(ruin50.mean()), 4),
            "P_10x_before_50pct_dd": round(float((hit10 & (t_hit < t_ruin)).mean()), 4),
            "median_terminal": round(float(np.median(eq[:, -1])), 3),
            "p10_terminal": round(float(np.percentile(eq[:, -1], 10)), 3),
            "p90_terminal": round(float(np.percentile(eq[:, -1], 90)), 3),
            "P_lose_half_or_more_at_end": round(float((eq[:, -1] <= 0.5).mean()), 4)}


def parametric():
    out = {}
    vol = 0.20
    for sharpe in [0.5, 1.0, 1.5, 2.0, 3.0]:
        for lev in [1, 2, 3, 5, 10]:
            mu_d = sharpe * vol / 365.0
            sd_d = vol / np.sqrt(365)
            r = rng.normal(mu_d, sd_d, size=(N_PATHS, DAYS)) * lev
            r = np.maximum(r, -1.0)   # cannot lose more than everything in a day
            out[f"Sharpe{sharpe}|vol20%|lev{lev}x"] = simulate(r)
    return out


def bootstrap_eth():
    """Block bootstrap (20-day blocks) of the two ETH variants that PASSED T1, at leverage 1x..5x."""
    df = lib.load_klines("spot", "ETHUSDT", "1d")
    out = {}
    for name, pos in [("ETH_T1b_tsmom", tsmom_positions(df, 28, 5)), ("ETH_T1c_sma10_40", sma_cross_positions(df, 10, 40))]:
        net = lib.run_positions(df, pos, 0.0015, start="2017-08-17", end="2026-10-31")["net"].dropna().values
        nblocks = DAYS // 20 + 1
        starts = rng.integers(0, len(net) - 20, size=(N_PATHS, nblocks))
        paths = np.concatenate([net[s[:, None] + np.arange(20)] for s in starts.T], axis=1)[:, :DAYS]
        for lev in [1, 2, 3, 5]:
            r = np.maximum(paths * lev - (lev - 1) * 0.0 , -1.0)   # no borrow cost modelled (disclosed)
            out[f"{name}|lev{lev}x"] = simulate(r)
        out[f"{name}|realised_daily_vol"] = round(float(net.std() * np.sqrt(365)), 4)
        out[f"{name}|realised_sharpe_full"] = round(float(net.mean() / net.std() * np.sqrt(365)), 3)
    return out


if __name__ == "__main__":
    res = {"parametric": parametric(), "bootstrap": bootstrap_eth()}
    json.dump(res, open("results_t6.json", "w"), indent=1)
    rows = [(k, *v.values()) for k, v in res["parametric"].items()]
    cols = ["case", "P_10x", "P_dd50", "P_10x_first", "median", "p10", "p90", "P_end<=0.5"]
    pd.set_option("display.width", 200)
    print(pd.DataFrame(rows, columns=cols).to_string(index=False))
    rows = [(k, *v.values()) for k, v in res["bootstrap"].items() if isinstance(v, dict)]
    print(pd.DataFrame(rows, columns=cols).to_string(index=False))
    print({k: v for k, v in res["bootstrap"].items() if not isinstance(v, dict)})
