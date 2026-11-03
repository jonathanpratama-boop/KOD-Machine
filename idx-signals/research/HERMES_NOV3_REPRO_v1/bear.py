"""Study 5 BEAR (PROTOCOL.md). Daily bars 2018-01..2026-10. Proxy (all shortable, 0.03%/day borrow) and perp (shorts
only where a USD-M funding file exists that month; short receives the summed funding) versions."""
import json
import numpy as np, pandas as pd
import lib

COST, BORROW = lib.COST, 0.0003
daily = lib.load_daily(None)
dates = pd.date_range("2017-08-01", "2026-10-31", freq="D", tz="UTC")
syms = sorted(daily); S, T = len(syms), len(dates)
Cm, Hm, Qm = (np.full((S, T), np.nan) for _ in range(3))
for k, s in enumerate(syms):
    dd, _, h, _, c, q = daily[s]; pos = dates.get_indexer(pd.DatetimeIndex(dd).tz_localize("UTC") if pd.DatetimeIndex(dd).tz is None else pd.DatetimeIndex(dd))
    ok = pos >= 0; Cm[k, pos[ok]], Hm[k, pos[ok]], Qm[k, pos[ok]] = c[ok], h[ok], q[ok]
Cf = pd.DataFrame(Cm.T).ffill(limit=7).values.T          # delisting / gaps: carry the last close up to 7 days
b = syms.index("BTCUSDT"); alt = np.array([s != "BTCUSDT" for s in syms])
roll = lambda a, n: pd.DataFrame(a.T).rolling(n, min_periods=n).mean().values.T
SMA = {n: roll(Cm, n) for n in (20, 50, 100, 200)}
SMA6 = {n: roll(Cm, n) for n in (11, 21, 50, 100, 200, 500)}
hist = np.cumsum(np.isfinite(Cm), axis=1)
qv20 = np.full_like(Qm, np.nan); qv20[:, 1:] = roll(Qm, 20)[:, :-1]            # prior 20 days
elig = alt[:, None] & (hist >= 200) & (qv20 >= 5e5)
hi200 = np.full_like(Hm, np.nan); hi200[:, 1:] = pd.DataFrame(Hm.T).rolling(200, min_periods=200).max().values.T[:, :-1]
above50 = (Cm > SMA[50]) & elig
breadth = above50.sum(0) / np.maximum(elig.sum(0), 1)
bear = np.zeros(T, bool); altbear = np.zeros(T, bool)
bear[1:] = Cm[b, :-1] < SMA[200][b, :-1]                                        # known from the previous close
altbear[1:] = breadth[:-1] < 0.35
fng_v, _ = lib.load_fng(); fng = fng_v.reindex(dates).values.astype(float)
F = lib.load_funding(); F["date"] = F.ts.dt.normalize()
fd = F.groupby(["sym", "date"]).rate.sum().unstack().reindex(columns=dates)
fund = np.full((S, T), np.nan); has_perp_month = np.zeros((S, T), bool)
for k, s in enumerate(syms):
    if s in fd.index:
        v = fd.loc[s].values; fund[k] = v
        m = pd.Series(np.isfinite(v), index=dates).groupby(dates.to_period("M")).transform("any").values
        has_perp_month[k] = m
fund0 = np.nan_to_num(fund)
up30 = np.full_like(Cm, False, dtype=bool); up30[:, 1:] = Cm[:, 1:] / Cm[:, :-1] - 1 >= 0.30
lead = (Cm > SMA[50]) & (Cm > SMA[200]) & elig
weak = elig & (Cm < SMA[20]) & (Cm < SMA[50]) & (Cm < SMA[100]) & (Cm < SMA[200]) & (Cm <= 0.6 * hi200)
ret7 = np.full_like(Cm, np.nan); ret7[:, 7:] = Cm[:, 7:] / Cm[:, :-7] - 1
weak &= ret7 < 0
spiker20 = pd.DataFrame(up30.T).rolling(20, min_periods=1).max().values.T.astype(bool) & elig
d_idx = np.arange(T); per = lambda d: "2018-20" if dates[d].year <= 2020 else ("2021-23" if dates[d].year <= 2023 else "2024-26")
start = dates.get_loc(pd.Timestamp("2018-01-01", tz="UTC"))


def trend_daily(k, d):
    sm = [SMA6[n][k, d - 1] for n in (11, 21, 50, 100, 200, 500)]
    if not np.isfinite(sm[4]) or not np.isfinite(hi200[k, d]):
        return False
    return sum(Cm[k, d] > x for x in sm if np.isfinite(x)) >= 5 and Cm[k, d] / hi200[k, d] - 1 >= -0.15


# ---------------- weekly arms
mondays = [d for d in range(start + 1, T) if dates[d].weekday() == 0]
ARMS = ["HOLD_BTC", "HOLD_ALTS", "SHORT_ALTS", "LEAD", "WEAK_SHORT", "LS", "SPIKER_SHORT"]


def weights(arm, a, version):
    s0 = a - 1                                       # decide at the close before Monday
    shortable = elig[:, s0] & (has_perp_month[:, s0] if version == "perp" else True)
    w = np.zeros(S)
    def ew(mask, sign, tot):
        n = mask.sum()
        if n: w[mask] += sign * tot / n
    if arm == "HOLD_BTC": w[b] = 1
    elif arm == "HOLD_ALTS": ew(elig[:, s0], 1, 1)
    elif arm == "SHORT_ALTS": ew(shortable, -1, 1)
    elif arm == "LEAD": ew(lead[:, s0], 1, 1)
    elif arm == "WEAK_SHORT": ew(weak[:, s0] & shortable, -1, 1)
    elif arm == "LS":
        if lead[:, s0].any() and (weak[:, s0] & shortable).any(): ew(lead[:, s0], 1, .5); ew(weak[:, s0] & shortable, -1, .5)
    elif arm == "SPIKER_SHORT": ew(spiker20[:, s0] & shortable, -1, 1)
    return w


weekly = {}
for version in ("proxy", "perp"):
    for rname, reg in (("BEAR", bear), ("ALT_BEAR", altbear)):
        for arm in ARMS:
            prev = np.zeros(S); eq, peak, mdd, recs = 1.0, 1.0, 0.0, []
            for a, nb in zip(mondays[:-1], mondays[1:]):
                if not reg[a]:
                    prev = np.zeros(S); continue
                w = weights(arm, a, version)
                r = np.nan_to_num(Cf[:, nb - 1] / Cf[:, a - 1] - 1)
                turn = np.abs(w - prev).sum()
                R = float((w * r).sum()) - COST * turn
                sw = np.clip(-w, 0, None)
                if version == "proxy": R -= BORROW * 7 * sw.sum()
                else: R += float((sw * fund0[:, a:nb].sum(1)).sum())
                dr = w * (1 + r); prev = dr / np.abs(dr).sum() * np.abs(w).sum() if np.abs(dr).sum() > 0 else w
                eq = max(0.0, eq * (1 + R)); peak = max(peak, eq); mdd = min(mdd, eq / peak - 1 if peak > 0 else -1)
                recs.append((per(a), R))
            pp = {}
            for p in ("2018-20", "2021-23", "2024-26"):
                x = [r for q, r in recs if q == p]; pp[p] = dict(weeks=len(x), total=float(np.prod([max(0, 1 + r) for r in x]) - 1) if x else None)
            weekly[f"{version}|{rname}|{arm}"] = dict(weeks=len(recs), total=eq - 1, max_drawdown=mdd, by_period=pp)

# ---------------- event arms (entries on BEAR days)
def short_ret(k, d, version, entry_px):
    ex, dd = None, None
    for j in range(d + 1, min(T, d + 11)):
        if np.isfinite(Cm[k, j]) and Cm[k, j] >= 1.3 * entry_px: ex, dd = Cm[k, j], j; break
    if ex is None:
        dd = min(T - 1, d + 10); ex = Cf[k, dd]
    if not np.isfinite(ex): return None, None
    r = (entry_px * (1 - COST) - ex * (1 + COST)) / entry_px
    r += -BORROW * (dd - d) if version == "proxy" else float(fund0[k, d + 1:dd + 1].sum())
    return r, dd


trades = []
for version in ("proxy", "perp"):
    last = {}
    for d in range(start, T - 11):
        if not bear[d]: continue
        for k in np.where(up30[:, d] & elig[:, d])[0]:
            if version == "perp" and not has_perp_month[k, d]: continue
            if d - last.get(("S", k), -99) >= 10:
                r, dd = short_ret(k, d, version, Cm[k, d])
                if r is not None: last[("S", k)] = d; trades.append(dict(arm="SHORT_SPIKE", version=version, sym=syms[k], date=str(dates[d].date()), period=per(d), ret=r, fund_entry=fund[k, d]))
            if Cm[k, d + 1] < Cm[k, d] and not trend_daily(k, d) and d + 1 - last.get(("F", k), -99) >= 10:
                r, dd = short_ret(k, d + 1, version, Cm[k, d + 1])
                if r is not None: last[("F", k)] = d + 1; trades.append(dict(arm="SHORT_FAILED", version=version, sym=syms[k], date=str(dates[d + 1].date()), period=per(d + 1), ret=r, fund_entry=fund[k, d + 1]))
for d in range(start, T - 11):
    if not bear[d]: continue
    for k in np.where(lead[:, d - 3] & elig[:, d] & (Cm[:, d] / Cm[:, d - 3] - 1 <= -0.20))[0]:
        if d - last.get(("L", k), -99) >= 10 and np.isfinite(Cf[k, d + 10]):
            last[("L", k)] = d
            trades.append(dict(arm="LEADER_DIP", version="spot", sym=syms[k], date=str(dates[d].date()), period=per(d), ret=Cf[k, d + 10] * (1 - COST) / (Cm[k, d] * (1 + COST)) - 1))
for h in (10, 20):
    busy = -1
    for d in range(start, T - h):
        if bear[d] and d > busy and np.isfinite(fng[d - 1]) and fng[d - 1] <= 15:
            trades.append(dict(arm=f"FNG_BTC_{h}", version="spot", sym="BTCUSDT", date=str(dates[d].date()), period=per(d), ret=Cm[b, d + h] * (1 - COST) / (Cm[b, d] * (1 + COST)) - 1)); busy = d + h
busy = -1
for d in range(start, T - 10):
    if bear[d] and d > busy and breadth[d] <= 0.10:
        m = elig[:, d] & np.isfinite(Cm[:, d]) & np.isfinite(Cf[:, d + 10])
        if m.any():
            trades.append(dict(arm="CAPITULATION", version="spot", sym="ALL", date=str(dates[d].date()), period=per(d), ret=float(np.mean(Cf[m, d + 10] * (1 - COST) / (Cm[m, d] * (1 + COST)) - 1)))); busy = d + 10
TR = pd.DataFrame(trades)
ev = {}
for (arm, v), g in TR.groupby(["arm", "version"]):
    ev[f"{v}|{arm}"] = dict(n=int(len(g)), mean=float(g.ret.mean()), median=float(g.ret.median()), win=float((g.ret > 0).mean()),
                            worst=float(g.ret.min()), best=float(g.ret.max()),
                            by_period={p: dict(n=int(len(x)), mean=float(x.ret.mean())) for p, x in g.groupby("period")})
res = dict(bear_weeks=int(sum(bear[a] for a in mondays[:-1])), altbear_weeks=int(sum(altbear[a] for a in mondays[:-1])),
           bear_days=int(bear[start:].sum()), symbols=S, weekly=weekly, events=ev,
           note="futures symbols whose name differs from spot (e.g. 1000SHIBUSDT) are treated as no perp")
TR.to_csv(lib.HERE / "out" / "bear_trades.csv.gz", index=False, compression="gzip")
(lib.HERE / "out" / "RESULT_bear.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
print("bear weeks", res["bear_weeks"], "alt-bear weeks", res["altbear_weeks"])
for k, v in weekly.items(): print(f"{k:32s} weeks {v['weeks']:4d} total {v['total']:+.3f} mdd {v['max_drawdown']:+.3f}", {p: (x['weeks'], None if x['total'] is None else round(x['total'], 3)) for p, x in v['by_period'].items()})
for k, v in ev.items(): print(f"{k:24s} n {v['n']:5d} mean {v['mean']:+.4f} med {v['median']:+.4f} win {v['win']:.2f} worst {v['worst']:+.3f}", {p: (x['n'], round(x['mean'], 4)) for p, x in v['by_period'].items()})
