"""MOVERS_NOW_v1: what did names look like before a 30%+ rise, in the current market (2025-2026)? Pure functions on wide (date x ticker) frames.
Decision at the close of day t using only data up to t. Labels look at closes t+1 .. t+20."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PANELS = {"IDX": "panel-20261007T225823Z", "US": "panel_us-20261008T004105Z", "CRYPTO": "panel_crypto-20261008T003354Z"}
MIN_VALUE = {"IDX": 1e9, "US": 1e6, "CRYPTO": 1e6}           # 20-day median traded value: IDR 1bn, USD 1m, USDT 1m
H, UP = 20, 1.30


def etoro_symbols() -> dict:
    data = json.loads((ROOT / "data/raw/etoro/20261016T190421Z/instruments.json").read_bytes())["InstrumentDisplayDatas"]
    us = {str(x["SymbolFull"]).upper().replace(".", "-") for x in data if x["InstrumentTypeID"] == 5 and x["ExchangeID"] in (4, 5) and not x.get("IsInternalInstrument")}
    cr = {str(x["SymbolFull"]).upper() for x in data if x["InstrumentTypeID"] == 10 and not x.get("IsInternalInstrument")}
    return {"US": us, "CRYPTO": cr}


def load(market: str, start: str = "2024-06-01") -> dict:
    df = pd.read_csv(ROOT / "data/panel" / f"{PANELS[market]}.csv.gz", usecols=["date", "ticker", "close", "value", "volume"], parse_dates=["date"])
    df = df[df.date >= start]
    if market == "US":
        df["value"] = df["value"].fillna(df.close * df.volume)
    C = df.pivot(index="date", columns="ticker", values="close").astype(float)
    V = df.pivot(index="date", columns="ticker", values="value").astype(float).reindex_like(C)
    r1, r2 = C / C.shift(1), C.shift(-1) / C
    spike = ((r1 > 1.8) & (r2 < 1 / 1.8)) | ((r1 < 1 / 1.8) & (r2 > 1.8))       # one-day bad print that snaps back
    C = C.mask(spike)
    brk = pd.DataFrame(False, index=C.index, columns=C.columns)
    if market == "IDX":                                                          # beyond any IDX daily limit: corporate action, not trading
        r = C / C.ffill().shift(1)
        brk = (r > 1.36) | (r < 0.64)
    return {"C": C, "V": V, "brk": brk}


def features(P: dict) -> dict:
    C, V, brk = P["C"], P["V"], P["brk"]
    Cf = C.ffill(limit=3)
    lr = np.log(Cf / Cf.shift(1))
    f = {
        "ret1": Cf / Cf.shift(1) - 1,
        "ret5": Cf / Cf.shift(5) - 1,
        "ret20": Cf / Cf.shift(20) - 1,
        "volr1": V / V.shift(1).rolling(20, min_periods=15).median(),
        "volr5": V.rolling(5, min_periods=4).mean() / V.shift(5).rolling(20, min_periods=15).median(),
        "hi60": Cf / Cf.rolling(60, min_periods=40).max(),
        "lo60": Cf / Cf.rolling(60, min_periods=40).min(),
        "squeeze": lr.rolling(10, min_periods=8).std() / lr.rolling(60, min_periods=40).std(),
        "liq": V.rolling(20, min_periods=15).median(),
        "price": Cf,
    }
    bad_hist = brk.rolling(61, min_periods=1).max().astype(bool)
    f = {k: v.mask(bad_hist) for k, v in f.items()}
    # market mood, same for every name on a day
    breadth = (f["ret20"] > 0).where(f["ret20"].notna()).mean(axis=1)
    mkt20 = f["ret20"].median(axis=1)
    f["breadth"] = pd.DataFrame(np.repeat(breadth.to_numpy()[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    f["mkt20"] = pd.DataFrame(np.repeat(mkt20.to_numpy()[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    return f


def labels(P: dict) -> dict:
    C, brk = P["C"], P["brk"]
    fut_max = pd.concat([C.shift(-k) for k in range(1, H + 1)]).groupby(level=0).max().reindex(C.index)
    fut_min = pd.concat([C.shift(-k) for k in range(1, H + 1)]).groupby(level=0).min().reindex(C.index)
    fut_brk = pd.concat([brk.shift(-k) for k in range(1, H + 1)]).groupby(level=0).max().reindex(C.index).astype(bool)
    end = C.shift(-H)
    ok = C.notna() & end.notna() & ~fut_brk
    return {"up30": (fut_max / C >= UP).where(ok), "dn30": (fut_min / C <= 1 / UP).where(ok), "fwd20": (end / C - 1).where(ok),
            "ok": ok}


def long_table(market: str, f: dict, y: dict, tradable: set | None) -> pd.DataFrame:
    keep = y["ok"] & (f["liq"] >= MIN_VALUE[market])
    if market == "US":
        keep &= f["price"] >= 1.0
    if tradable is not None:
        cols = [c for c in keep.columns if (c.replace("USDT", "") if market == "CRYPTO" else c) in tradable]
        keep = keep[cols]
    st = keep.stack()
    idx = st[st].index
    out = pd.DataFrame(index=idx)
    for k, v in {**f, **{k: y[k] for k in ("up30", "dn30", "fwd20")}}.items():
        out[k] = v.reindex(columns=keep.columns).stack().reindex(idx)
    return out.reset_index().rename(columns={"level_0": "date", "level_1": "ticker"})
