"""PATH_HISTORY_v1 feasibility: count signal events per market and period. Reads no outcome: only the signal day's
own bars (detector flags), and each panel is cut to its allowed dates before the market is built."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from idxsig import panel as idx_panel, global_panel
from idxsig.execution import Market
from idxsig.rules import moonshot_e1, moonshot_g

SEGMENTS = {"IDX": [("2019-07-29", "2023-12-29"), ("2025-02-24", "2026-10-06")],
            "US": [("2020-01-02", "2023-12-29")], "CRYPTO": [("2020-01-01", "2023-12-31")]}

def load(market):
    if market == "IDX":
        df, meta, _ = idx_panel.load(Path_("data/manifests/panel-20261007T225823Z.json"))
    elif market == "US":
        df, meta = global_panel.load(Path_("data/manifests/panel_us_repair-20261008T114805Z.json"))
    else:
        df, meta = global_panel.load(Path_("data/manifests/panel_crypto-20261008T003354Z.json"))
    return df, meta

from pathlib import Path as Path_
for market in ("US", "CRYPTO", "IDX"):
    df, meta = load(market)
    for lo, hi in SEGMENTS[market]:
        seg = df[(df["date"] >= lo) & (df["date"] <= hi)]
        if market == "IDX":
            traded = seg[seg["volume"] > 0].groupby("date")["ticker"].nunique()
            seg = seg[seg["date"].isin(traded[traded >= 50].index)]
            m = Market.from_panel(seg)
            f = moonshot_e1.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.lock_up)
            flag = moonshot_e1.family_flags(f)["F1_ARA"] & (m.close >= 50)
        else:
            m = Market.from_panel(seg, price_limits=False)
            f = moonshot_g.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
            flag = moonshot_g.family_flags(f)["G2_RET30"]
        hist = np.cumsum(m.present, axis=1)
        flag = flag & m.tradeable & (hist > 20)
        flag[:, -21:] = False  # 20-session windows stay inside the segment
        years = pd.DatetimeIndex(m.dates.astype("datetime64[ns]")).year
        n_by_year = {int(y): int(flag[:, years == y].sum()) for y in sorted(set(years))}
        days_with = int((flag.sum(axis=0) > 0).sum())
        print(f"{market} {lo}..{hi}: {int(flag.sum())} events, {int((flag.sum(axis=1) > 0).sum())} tickers, "
              f"{days_with} of {m.shape[1]} sessions have one; by year {n_by_year}")
