#!/usr/bin/env python3
"""T2 (funding carry / signal), T3 (cross-sectional momentum on perps), T4 (hourly mean reversion). Rules per PROTOCOL.md."""
import json
import sys

import numpy as np
import pandas as pd

import lib

PERP_SIDE = 0.0010      # 0.05% fee + 0.05% slippage per side
SPOT_SIDE = 0.0015
MAJORS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT"]
DEV = ("2019-09-01", "2022-12-31")
VAL = ("2023-01-01", "2026-10-31")


def in_period(idx, p):
    return (idx >= pd.Timestamp(p[0], tz="UTC")) & (idx <= pd.Timestamp(p[1], tz="UTC"))


# ------------------------------------------------------------------ T2 ----
def t2():
    out = {}
    for sym in ["BTCUSDT", "ETHUSDT"]:
        f = lib.load_funding(sym)
        if f is None:
            out[sym] = "no funding data"
            continue
        yearly = {}
        for y, g in f.groupby(f.index.year):
            n_per_year = 365 * 3  # 8h funding
            ann = g.mean() * n_per_year
            yearly[str(y)] = {"ann_funding": round(float(ann), 4), "share_negative": round(float((g < 0).mean()), 3),
                              "n": int(len(g)), "carry_net_of_one_roundtrip_each_leg": round(float(ann - 0.0030 - 0.0020), 4)}
        res = {"by_year": yearly}
        for name, p in [("dev", DEV), ("val", VAL)]:
            g = f[in_period(f.index, p)]
            ann = g.mean() * 365 * 3
            res[name] = {"ann_funding": round(float(ann), 4), "share_negative": round(float((g < 0).mean()), 3),
                         "carry_net": round(float(ann - 0.005), 4), "PASS": bool(ann - 0.005 > 0.08)}
        out[sym] = res
    # contrarian signal on BTC: 30-day mean funding turns negative
    f = lib.load_funding("BTCUSDT")
    px = lib.load_klines("futures", "BTCUSDT", "1d")["close"]
    if f is not None and px is not None:
        daily_f = f.resample("1D").sum()
        m30 = daily_f.rolling(30).mean()
        turns = m30[(m30 < 0) & (m30.shift(1) >= 0)].index
        fwd90 = px.shift(-90) / px - 1
        events = []
        for t in turns:
            d = t.normalize()
            if d in fwd90.index and not np.isnan(fwd90.loc[d]):
                events.append({"date": str(d.date()), "fwd90": round(float(fwd90.loc[d]), 4)})
        uncond = fwd90.dropna()
        out["BTC_funding_turns_negative"] = {"events": events,
                                             "unconditional_fwd90_mean": round(float(uncond.mean()), 4),
                                             "unconditional_fwd90_median": round(float(uncond.median()), 4),
                                             "unconditional_share_positive": round(float((uncond > 0).mean()), 3)}
    return out


# ------------------------------------------------------------------ T3 ----
def t3():
    syms = lib.list_symbols("futures", "1d")
    closes, opens, dvol, fund = {}, {}, {}, {}
    for s in syms:
        d = lib.load_klines("futures", s, "1d")
        if d is None or len(d) < 100:
            continue
        closes[s], opens[s], dvol[s] = d["close"], d["open"], d["quote_volume"]
        f = lib.load_funding(s)
        fund[s] = f.resample("1D").sum() if f is not None else None
    C = pd.DataFrame(closes).sort_index()
    O = pd.DataFrame(opens).reindex(C.index)
    V = pd.DataFrame(dvol).reindex(C.index)
    F = pd.DataFrame({s: v for s, v in fund.items() if v is not None}).reindex(C.index).fillna(0.0)
    F = F.reindex(columns=C.columns).fillna(0.0)
    print(f"T3 panel: {C.shape[1]} symbols, {C.index[0].date()} .. {C.index[-1].date()}", file=sys.stderr)
    # eligibility at date t (computed on data up to t): >= 90 prior bars, median 30d dollar volume >= 5m
    hist = C.notna().cumsum()
    elig = (hist >= 90) & (V.rolling(30).median() >= 5e6) & C.notna()
    mom = C / C.shift(14) - 1
    mondays = [d for d in C.index if d.weekday() == 0]
    # weekly portfolio returns: hold from Monday open to next Monday open; signals at Sunday close (= index position of Monday minus 1)
    recs = []
    prev_w_long, prev_w_short = pd.Series(dtype=float), pd.Series(dtype=float)
    idx = C.index
    for i, m in enumerate(mondays[:-1]):
        pos_m = idx.get_loc(m)
        if pos_m == 0:
            continue
        sig_day = idx[pos_m - 1]
        e = elig.loc[sig_day]
        cand = mom.loc[sig_day][e].dropna()
        if len(cand) < 20:
            continue
        n = max(1, len(cand) // 10)
        ranked = cand.sort_values()
        longs, shorts = ranked.index[-n:], ranked.index[:n]
        nxt = mondays[i + 1]
        # realised open-to-open return over the week per symbol; a symbol that stops trading is closed at its last close
        def hold_ret(sym):
            o0 = O.loc[m, sym]
            o1 = O.loc[nxt, sym]
            if np.isnan(o1):
                last = C.loc[m:nxt, sym].dropna()
                o1 = last.iloc[-1] if len(last) else o0
            fsum = F.loc[m:nxt, sym].iloc[:-1].sum() if sym in F.columns else 0.0
            return o1 / o0 - 1.0, fsum
        wl = pd.Series(1.0 / n, index=longs)
        ws = pd.Series(1.0 / n, index=shorts)
        rl = sum(wl[s] * hold_ret(s)[0] for s in longs)
        rs = sum(ws[s] * hold_ret(s)[0] for s in shorts)
        fl = sum(wl[s] * hold_ret(s)[1] for s in longs)      # longs pay funding
        fs = sum(ws[s] * hold_ret(s)[1] for s in shorts)     # shorts receive funding
        turn_l = (wl.subtract(prev_w_long, fill_value=0.0)).abs().sum()
        turn_s = (ws.subtract(prev_w_short, fill_value=0.0)).abs().sum()
        prev_w_long, prev_w_short = wl, ws
        univ = cand.index
        ru = np.mean([hold_ret(s)[0] for s in univ])
        recs.append({"week": m, "n": n, "long": rl, "short": rs, "fund_long": fl, "fund_short": fs,
                     "cost_ls": (turn_l + turn_s) * PERP_SIDE, "cost_lo": turn_l * PERP_SIDE, "univ": ru, "n_univ": len(univ)})
    R = pd.DataFrame(recs).set_index("week")
    R["T3a_ls_net"] = R["long"] - R["short"] - R["fund_long"] + R["fund_short"] - R["cost_ls"]
    R["T3b_lo_net"] = R["long"] - R["fund_long"] - R["cost_lo"]
    R["univ_net"] = R["univ"] - R["univ"].abs() * 0  # equal-weight universe, gross (benchmark)
    out = {"n_weeks": int(len(R)), "mean_n_univ": round(float(R["n_univ"].mean()), 1)}
    for name, p in [("dev", DEV), ("val", VAL)]:
        sub = R[in_period(R.index, p)]
        res = {}
        for col in ["T3a_ls_net", "T3b_lo_net", "univ_net"]:
            st = lib.stats(sub[col], 52)
            st["by_year"] = lib.by_year(sub[col])
            res[col] = st
        out[name] = res
    years_pos = {}
    for col in ["T3a_ls_net", "T3b_lo_net"]:
        by = lib.by_year(R[col])
        years_pos[col] = round(sum(v > 0 for v in by.values()) / len(by), 3)
    out["share_years_positive"] = years_pos
    out["verdict"] = {col: ("PASS" if (out["dev"][col]["Sharpe"] > 1 and out["val"][col]["Sharpe"] > 1 and years_pos[col] >= 0.7) else "FAIL")
                      for col in ["T3a_ls_net", "T3b_lo_net"]}
    R.to_csv("t3_weekly.csv")
    return out


# ------------------------------------------------------------------ T4 ----
def t4():
    trades = []
    for sym in MAJORS:
        d = lib.load_klines("futures", sym, "1h")
        if d is None:
            continue
        f = lib.load_funding(sym)
        lr = np.log(d["close"]).diff()
        r4 = np.log(d["close"] / d["close"].shift(4))
        # trailing 30-day std of non-overlapping 4h returns ending at each hour's phase
        sd = pd.Series(np.nan, index=d.index)
        for phase in range(4):
            sel = r4.iloc[phase::4]
            sd.iloc[phase::4] = sel.rolling(180, min_periods=120).std().shift(1).values   # 30 days x 6 windows/day
        z = r4 / sd
        o = d["open"].values
        zz = z.values
        i, n = 0, len(d)
        while i < n - 6:
            if np.isnan(zz[i]):
                i += 1
                continue
            side = 0
            if zz[i] <= -2:
                side = 1
            elif zz[i] >= 2:
                side = -1
            if side == 0:
                i += 1
                continue
            entry, exit_ = o[i + 1], o[i + 5]
            gross = side * (exit_ / entry - 1.0)
            fnd = 0.0
            if f is not None:
                ff = f[(f.index > d.index[i + 1]) & (f.index <= d.index[i + 5])]
                fnd = side * ff.sum()
            trades.append({"sym": sym, "time": d.index[i], "z": zz[i], "side": side, "gross": gross,
                           "net": gross - 2 * PERP_SIDE - fnd, "abs_z_ge3": abs(zz[i]) >= 3})
            i += 5   # no overlapping positions in the same symbol
    T = pd.DataFrame(trades)
    T.to_csv("t4_trades.csv", index=False)
    out = {}
    for name, p in [("dev", DEV), ("val", VAL)]:
        sub = T[in_period(pd.DatetimeIndex(T["time"]), p)]
        res = {}
        for lab, mask in [("T4a_z3", sub["abs_z_ge3"]), ("T4b_z2", sub["abs_z_ge3"] | ~sub["abs_z_ge3"])]:
            s = sub[mask]
            for side_lab, sm in [("all", s), ("long_after_drop", s[s["side"] == 1]), ("short_after_spike", s[s["side"] == -1])]:
                if len(sm) < 5:
                    continue
                mu, se = sm["net"].mean(), sm["net"].std(ddof=1) / np.sqrt(len(sm))
                res[f"{lab}|{side_lab}"] = {"n": int(len(sm)), "mean_net": round(float(mu), 5), "t": round(float(mu / se), 2),
                                             "win_rate": round(float((sm["net"] > 0).mean()), 3),
                                             "mean_gross": round(float(sm["gross"].mean()), 5)}
        out[name] = res
    verdict = {}
    for lab in ["T4a_z3", "T4b_z2"]:
        for side_lab in ["long_after_drop", "short_after_spike"]:
            k = f"{lab}|{side_lab}"
            ok = all((k in out[p]) and out[p][k]["mean_net"] > 0 and out[p][k]["t"] >= 3 for p in ["dev", "val"])
            verdict[k] = "PASS" if ok else "FAIL"
    out["verdict"] = verdict
    return out


if __name__ == "__main__":
    which = sys.argv[1:] or ["t2", "t3", "t4"]
    res = {}
    if "t2" in which:
        res["T2"] = t2()
    if "t3" in which:
        res["T3"] = t3()
    if "t4" in which:
        res["T4"] = t4()
    json.dump(res, open("results_" + "_".join(which) + ".json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
