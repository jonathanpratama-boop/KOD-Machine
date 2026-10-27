"""MOVERS_NOW_v1: run an IDX rule's signals through the execution harness (idxsig.idx_events), with two baselines:
(A) the harness's matched random controls (price band, liquidity, volatility, momentum, drawdown, market cap, listing age);
(B) random tradable names of the same price band and liquidity quintile on the same session, executed by the same harness.
Signal = first session of a qualifying streak, then at most one per name per 20 sessions. Posted 16:00 WIB, so bought at the next session's close."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "IDX_DILUTION_v1"))
import common  # noqa: E402  (panel-20261007T225823Z, registry 20261007, the IDX_INSIDER_NEWS plan)
from idxsig import idx_events  # noqa: E402

GAP = 20


def signals(rows: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    r = rows.loc[mask, ["date", "ticker"]].sort_values(["ticker", "date"])
    dates = np.sort(rows.date.unique())
    pos = {d: i for i, d in enumerate(dates)}
    out, last = [], {}
    for tk, d in zip(r.ticker, r.date):
        i = pos[np.datetime64(d)]
        if tk in last and i - last[tk] < GAP:
            if i - last[tk] == 1 or True:
                pass
            continue
        last[tk] = i
        out.append({"ticker": tk, "date": pd.Timestamp(d).strftime("%Y-%m-%d"), "posted_wib": pd.Timestamp(d).strftime("%Y-%m-%d") + " 16:00"})
    return pd.DataFrame(out)


def run(ev: pd.DataFrame, hold: int = 20, k_baseline: int = 30, seed: int = 20261027, prep=None):
    df, reg, meta = common.load_inputs()
    prep = prep or idx_events.prepare(df, reg, "2024-06-03", "2026-10-06")
    cfg = common.config(hold)
    res = idx_events.run_events(prep, ev, cfg, draws=100, seed=seed)
    # baseline B
    m, feats = prep.m, prep.feats
    rng = np.random.default_rng(seed + 7)
    tick = pd.Index(m.tickers)
    base = []
    for i, r in enumerate(res.itertuples()):
        s, n = int(r.sig_idx), int(r.tick_idx)
        cand = np.flatnonzero(prep.evaluable[:, s] & (feats["price_band"][:, s] == feats["price_band"][n, s]) & (feats["liquidity"][:, s] == feats["liquidity"][n, s]))
        cand = cand[cand != n]
        if len(cand) == 0:
            continue
        for c in rng.choice(cand, size=min(k_baseline, len(cand)), replace=False):
            base.append({"ticker": tick[c], "posted_wib": r.posted_wib, "parent": i})
    b = idx_events.run_events(prep, pd.DataFrame(base), cfg, draws=1, seed=seed, overlap="keep")
    bm = b[b.net_return.notna()].groupby("parent").net_return.mean()
    res["base_b"] = bm.reindex(range(len(res))).to_numpy()
    res["excess_b"] = res.net_return - res.base_b
    return res, prep


def summary(res: pd.DataFrame) -> dict:
    f = res[res.net_return.notna()]
    d = lambda s: {"n": int(s.notna().sum()), "mean": float(s.mean()), "median": float(s.median()),  # noqa: E731
                   "t_naive": float(s.mean() / s.std() * np.sqrt(s.notna().sum())) if s.notna().sum() > 2 else float("nan")}
    return {"status": idx_events.status_counts(res), "net": d(f.net_return), "excess_vs_similar_A": d(f.excess), "excess_vs_any_B": d(f.excess_b),
            "share_gross_ge_30pct": float((f.gross_return >= 0.30).mean()), "share_net_le_-20pct": float((f.net_return <= -0.20).mean())}
