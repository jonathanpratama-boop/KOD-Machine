"""Loaders and a minimal, causal backtest engine for FRESH_EYES_v1.

Design rules (see PROTOCOL.md):
- A signal computed on bar t may only affect positions from the OPEN of bar t+1.
- Costs are charged per side on every change in position, as a fraction of notional traded.
- Funding on perpetual positions is charged at the daily funding sum (sign convention: a long pays positive funding).
"""
import glob
import io
import os
import zipfile

import numpy as np
import pandas as pd

RAW = os.environ.get("BINANCE_RAW", "/home/claude/data/binance")
KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
         "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def _read_zip_csv(path, names):
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        raw = z.read(name)
    first = raw.split(b"\n", 1)[0]
    header = 0 if first[:1].isalpha() else None
    df = pd.read_csv(io.BytesIO(raw), header=header)
    if header is None:
        df.columns = names[: df.shape[1]]
    else:
        df.columns = [c.strip() for c in df.columns]
    return df


def _to_dt(x):
    x = x.astype("int64")
    # Binance switched to microseconds for 2025+ files; normalise per row to milliseconds.
    x = x.where(x < 10**14, x // 1000)
    return pd.to_datetime(x, unit="ms", utc=True)


def load_klines(market, symbol, interval):
    m = "spot" if market == "spot" else "futures/um"
    files = sorted(glob.glob(f"{RAW}/data/{m}/monthly/klines/{symbol}/{interval}/*.zip"))
    if not files:
        return None
    parts = []
    for f in files:
        try:
            parts.append(_read_zip_csv(f, KCOLS))
        except zipfile.BadZipFile:
            continue
    df = pd.concat(parts, ignore_index=True)
    df["time"] = _to_dt(df["open_time"])
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    out = df[["open", "high", "low", "close", "volume", "quote_volume"]].astype(float)
    return out


def load_funding(symbol):
    files = sorted(glob.glob(f"{RAW}/data/futures/um/monthly/fundingRate/{symbol}/*.zip"))
    if not files:
        return None
    parts = []
    for f in files:
        try:
            d = _read_zip_csv(f, ["calc_time", "funding_interval_hours", "last_funding_rate"])
        except zipfile.BadZipFile:
            continue
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    df["time"] = _to_dt(df["calc_time"])
    s = df.set_index("time")["last_funding_rate"].astype(float).sort_index()
    return s[~s.index.duplicated(keep="last")]


def list_symbols(market, interval):
    m = "spot" if market == "spot" else "futures/um"
    base = f"{RAW}/data/{m}/monthly/klines"
    return sorted(s for s in os.listdir(base) if os.path.isdir(f"{base}/{s}/{interval}"))


# ---------------------------------------------------------------- engine ----

def run_positions(df, target_pos, fee_side, funding_daily=None, start=None, end=None):
    """Daily (or hourly) bar engine.

    target_pos: Series aligned to df.index, the DESIRED position (fraction of equity, +long/-short)
                decided at the close of each bar. It is applied at the next bar's open.
    Returns a DataFrame with equity, position held during each bar, cost, funding.
    Bar return for a position p held from open(t) to open(t+1) is p * (open(t+1)/open(t) - 1).
    """
    pos = target_pos.shift(1).fillna(0.0)                      # held from this bar's open
    op = df["open"]
    ret_open_to_open = op.shift(-1) / op - 1.0                 # realised over the bar
    gross = pos * ret_open_to_open
    traded = (pos - pos.shift(1).fillna(0.0)).abs()            # notional change at this bar's open
    cost = traded * fee_side
    fund = pd.Series(0.0, index=df.index)
    if funding_daily is not None:
        fund = pos * funding_daily.reindex(df.index).fillna(0.0)   # long pays positive funding
    net = gross - cost - fund
    out = pd.DataFrame({"pos": pos, "gross": gross, "cost": cost, "funding": fund, "net": net})
    if start is not None:
        out = out[out.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        out = out[out.index <= pd.Timestamp(end, tz="UTC")]
    out = out.iloc[:-1] if np.isnan(out["net"].iloc[-1]) else out
    out["equity"] = (1 + out["net"]).cumprod()
    return out


def stats(net, periods_per_year=365, pos=None):
    net = net.dropna()
    if len(net) == 0:
        return {}
    eq = (1 + net).cumprod()
    years = len(net) / periods_per_year
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    vol = net.std() * np.sqrt(periods_per_year)
    sharpe = net.mean() / net.std() * np.sqrt(periods_per_year) if net.std() > 0 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    out = {"CAGR": round(cagr, 4), "vol": round(vol, 4), "Sharpe": round(sharpe, 3), "MaxDD": round(dd, 4),
           "total": round(eq.iloc[-1] - 1, 4), "periods": int(len(net))}
    if pos is not None:
        p = pos.reindex(net.index).fillna(0)
        trades = ((p - p.shift(1).fillna(0)).abs() > 1e-12).sum()
        out["trades_per_year"] = round(trades / years, 1)
        out["time_in_market"] = round((p.abs() > 1e-12).mean(), 3)
    return out


def by_year(net):
    return {str(y): round(float((1 + g).prod() - 1), 4) for y, g in net.groupby(net.index.year)}
