"""EXIT-ATR-v1 step 3b: coverage and daily-versus-hourly reconciliation for the shared entry list.

Reads the shared entry list (entries/), E2's daily panel (rebuilt with E2 code a155cf0, argument 1) and the
restored hourly archive (data/raw/binance_1h, E6 manifest). It computes NO return and reads no exit price.
For every entered signal and control trade it reports:
- whether the hourly archive has the pair (ticker + USDT);
- hourly bars present over [entry day 00:00, planned exit day 23:00]; the planned exit is the original 5-session
  exit, or for trades the original model never exited (INCOMPLETE) entry + 5 days capped at 2022-12-31;
- whether the entry day's 00:00 bar exists;
- ATR warm-up: 15 consecutive daily panel bars s-14..s with high >= low > 0 and close > 0.
It also compares daily open/high/low/close/volume with the hourly aggregates for every coin-day in a window.
Usage (from idx-signals/): ../.venv/bin/python research/EXIT_ATR_v1/coverage.py <panel .csv.gz>
"""
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[2]
ENT = HERE / "research" / "EXIT_ATR_v1" / "entries"
OUT = HERE / "research" / "EXIT_ATR_v1" / "data_check"
MAN = HERE / "data" / "manifests" / "binance_1h-20261015T182940Z.jsonl"
FIRST, LAST = "2020-07", "2022-12"
END = pd.Timestamp("2022-12-31")
ENTERED = ("EXITED", "EXIT_DATA_END", "INCOMPLETE")


def load_hourly(symbols):
    recs = [json.loads(x) for x in MAN.read_text().splitlines()[1:]]
    files = {}
    for r in recs:
        if FIRST <= r["month"] <= LAST and r["symbol"] in symbols:
            files.setdefault(r["symbol"], []).append(r["file"])
    out = {}
    for s, fs in files.items():
        parts = []
        for f in sorted(fs):
            with zipfile.ZipFile(HERE / "data" / "raw" / f) as z:
                raw = z.read(z.namelist()[0])
            df = pd.read_csv(io.BytesIO(raw), header=None, usecols=range(6),
                             names=["t", "open", "high", "low", "close", "volume"])
            if not str(df.iloc[0, 0]).isdigit():
                df = df.iloc[1:]
            parts.append(df.astype(float))
        h = pd.concat(parts, ignore_index=True)
        unit = 1000 if h["t"].max() < 1e14 else 1_000_000
        h["hour"] = (h["t"] // (3600 * unit)).astype(np.int64)
        out[s] = h.drop_duplicates("hour").sort_values("hour").reset_index(drop=True)
    return out


def hour_of(dates):
    return (pd.to_datetime(dates).values.astype("datetime64[h]").astype(np.int64))


def main(panel_path: Path) -> int:
    sig = pd.read_csv(ENT / "signals.csv")
    sig = sig[sig.j >= 0].assign(arm="signal", draw=-1)
    ctl = pd.read_csv(ENT / "controls.csv.gz").assign(arm="control")
    E = pd.concat([sig[["arm", "j", "draw", "ticker", "signal_date", "status", "entry_date", "exit_date_original"]],
                   ctl[["arm", "j", "draw", "ticker", "signal_date", "status", "entry_date", "exit_date_original"]]],
                  ignore_index=True)
    E = E[E.status.isin(ENTERED)].copy()
    E["entry_date"] = pd.to_datetime(E.entry_date)
    planned = pd.to_datetime(E.exit_date_original.where(E.exit_date_original.notna() & (E.exit_date_original != "")))
    E["planned_exit"] = planned.fillna(np.minimum(E.entry_date + pd.Timedelta(days=5), END))
    E["symbol"] = E.ticker + "USDT"

    # ATR warm-up from the daily panel
    P = pd.read_csv(panel_path, usecols=["date", "ticker", "open", "high", "low", "close", "volume"])
    P["date"] = pd.to_datetime(P.date)
    P = P[(P.date >= "2020-04-01") & (P.date <= END)]
    ok = ((P.high >= P.low) & (P.low > 0) & (P.close > 0)).astype(float)
    W = P.assign(ok=ok).pivot(index="date", columns="ticker", values="ok")
    W = W.reindex(pd.date_range(W.index.min(), END, freq="D")).fillna(0.0)
    warm = W.rolling(15, min_periods=15).sum() == 15
    sd = pd.to_datetime(E.signal_date)
    E["atr_valid"] = [bool(warm.at[d, t]) if (t in warm.columns and d in warm.index) else False
                      for d, t in zip(sd, E.ticker)]

    # Hourly coverage
    H = load_hourly(set(E.symbol))
    E["h0"] = hour_of(E.entry_date)
    E["h1"] = hour_of(E.planned_exit) + 23
    E["expected_hours"] = E.h1 - E.h0 + 1
    E["present_hours"] = 0
    E["entry_bar"] = False
    E["last_present_hour"] = -1
    E["has_symbol"] = E.symbol.isin(H.keys())
    for s, idx in E[E.has_symbol].groupby("symbol").groups.items():
        hrs = H[s]["hour"].to_numpy()
        h0, h1 = E.loc[idx, "h0"].to_numpy(), E.loc[idx, "h1"].to_numpy()
        l, r = np.searchsorted(hrs, h0, "left"), np.searchsorted(hrs, h1, "right")
        E.loc[idx, "present_hours"] = r - l
        E.loc[idx, "entry_bar"] = (l < len(hrs)) & (hrs[np.minimum(l, len(hrs) - 1)] == h0)
        E.loc[idx, "last_present_hour"] = np.where(r > l, hrs[np.maximum(r - 1, 0)], -1)
    cls = np.select([~E.has_symbol, E.present_hours == E.expected_hours, E.last_present_hour < E.h1],
                    ["NO_HOURLY_SYMBOL", "COMPLETE", "TRUNCATED"], "GAPS")
    E["coverage"] = cls

    # Daily vs hourly reconciliation on every coin-day inside a window
    days = set()
    for t, a, b in E[E.has_symbol][["ticker", "entry_date", "planned_exit"]].drop_duplicates().itertuples(index=False):
        for d in pd.date_range(a, b, freq="D"):
            days.add((t, d))
    agg = []
    for s, h in H.items():
        g = h.assign(day=pd.to_datetime(h.hour * 3600, unit="s").dt.floor("D")).groupby("day")
        a = g.agg(n=("hour", "size"), open=("open", "first"), high=("high", "max"), low=("low", "min"),
                  close=("close", "last"), volume=("volume", "sum")).reset_index()
        agg.append(a.assign(ticker=s[:-4]))
    A = pd.concat(agg, ignore_index=True)
    want = pd.DataFrame(sorted(days), columns=["ticker", "day"])
    J = want.merge(A, on=["ticker", "day"], how="left").merge(
        P.rename(columns={"date": "day"}), on=["ticker", "day"], how="left", suffixes=("_h", "_d"))
    full = J[(J.n == 24) & J.open_d.notna()]
    rec = {"coin_days_in_windows": int(len(J)), "with_24_hourly_bars_and_daily_row": int(len(full)),
           "missing_daily_row": int(J.open_d.isna().sum()), "fewer_than_24_hourly_bars": int((J.n.fillna(0) < 24).sum())}
    for c in ("open", "high", "low", "close", "volume"):
        rel = (full[f"{c}_h"] - full[f"{c}_d"]).abs() / full[f"{c}_d"].abs().replace(0, np.nan)
        rec[c] = {"exact_1e-9": int((rel <= 1e-9).sum()), "over_1e-9": int((rel > 1e-9).sum()),
                  "over_0.1pct": int((rel > 1e-3).sum()), "max_rel_diff": float(rel.max()) if len(rel) else None}
    worst = full.assign(rel_close=(full.close_h - full.close_d).abs() / full.close_d).nlargest(10, "rel_close")
    rec["worst_close_examples"] = worst[["ticker", "day", "close_h", "close_d", "rel_close"]].astype(str).to_dict("records")

    # Summary
    tab = E.groupby(["arm", "coverage"]).size().unstack(fill_value=0)
    atr = E.groupby(["arm", "atr_valid"]).size().unstack(fill_value=0)
    eligible = E.coverage.isin(["COMPLETE"]) & E.atr_valid
    summ = {"entered_trades": E.arm.value_counts().to_dict(), "coverage": tab.to_dict(orient="index"),
            "atr_warmup": atr.to_dict(orient="index"),
            "entry_bar_missing": E[~E.entry_bar].groupby("arm").size().to_dict(),
            "complete_and_atr_valid": E[eligible].groupby("arm").size().to_dict(),
            "signals_complete_and_atr_valid_distinct_coins": int(E[eligible & (E.arm == "signal")].ticker.nunique()),
            "symbols_without_hourly": sorted(set(E[~E.has_symbol].ticker)),
            "daily_vs_hourly": rec}
    OUT.mkdir(parents=True, exist_ok=True)
    E.drop(columns=["h0", "h1"]).to_csv(OUT / "coverage.csv.gz", index=False,
                                        compression={"method": "gzip", "mtime": 0})
    (OUT / "COVERAGE.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps({k: summ[k] for k in ("entered_trades", "coverage", "atr_warmup", "entry_bar_missing",
                                           "complete_and_atr_valid", "symbols_without_hourly")}, indent=1, default=str))
    print(json.dumps({k: v for k, v in rec.items() if k != "worst_close_examples"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
