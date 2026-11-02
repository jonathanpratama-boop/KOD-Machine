"""IGNITION_SCAN_v0 (exploratory, discovery window 2020-2022 only).
Question: when a coin starts an unusual move (big 3h gain on abnormal volume, not already pumped),
how often does it keep running to +30/+50/+100% after a realistic next-hour entry, vs matched controls?
Every event is written to out/events_v0.csv, including fades. Parameters are recorded in out/spec_v0.json."""
import json, os, hashlib
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "out")
SPEC = dict(
    version="IGNITION_SCAN_v0", window="2020-01-01..2022-12-31 (2023+ not on disk)",
    trigger_ret_3h=0.10, trigger_vol_mult=5.0, max_prior_run_7d=0.30,
    min_avg_hourly_quote_usd=20000, cooldown_h=72, horizon_h=72,
    entry="open of hour t+1 (first hour after the trigger hour closes)",
    cost_per_side=0.003, controls_per_event=5,
    controls="same entry hour, random other eligible coins (liquidity filter, not triggered within +/-72h), seed 7",
)
rng = np.random.default_rng(7)
# Safe: panel_1h.pkl is produced locally by build_panel.py from hash-logged Binance zips, never external.
p = pd.read_pickle(os.path.join(OUT, "panel_1h.pkl"))
grid = pd.date_range("2020-01-01", "2022-12-31 23:00", freq="h", tz="UTC")
syms = sorted(p["sym"].unique())
T = len(grid); idx = {s: i for i, s in enumerate(syms)}
def mat(col):
    m = np.full((len(syms), T), np.nan)
    for s, g in p.groupby("sym"):
        pos = grid.get_indexer(g["ts"]); m[idx[s], pos] = g[col].values
    return m
O, H, L, C, Q = (mat(c) for c in ["open", "high", "low", "close", "quote_vol"])
del p
def shift(a, k):  # value k hours earlier (k>0)
    out = np.full_like(a, np.nan); out[:, k:] = a[:, :-k]; return out
r3 = C / shift(C, 3) - 1
q3 = Q + shift(Q, 1) + shift(Q, 2)
# trailing mean hourly volume over the 168h ending before the 3h trigger window
cs = np.concatenate([np.zeros((len(syms), 1)), np.nancumsum(np.nan_to_num(Q), axis=1)], axis=1)  # cs[:,k]=sum Q[:, :k]
t = np.arange(T)
lo = t - 3 - 168 + 1; hi = t - 3 + 1  # hours t-170 .. t-3 inclusive
valid = lo >= 0
base = np.full_like(Q, np.nan)
base[:, valid] = (cs[:, hi[valid]] - cs[:, lo[valid]]) / 168.0  # mean hourly volume
cnt = np.isfinite(Q).astype(float); cc = np.concatenate([np.zeros((len(syms), 1)), np.cumsum(cnt, axis=1)], axis=1)
nobs = np.full_like(Q, np.nan); nobs[:, valid] = cc[:, hi[valid]] - cc[:, lo[valid]]
base = np.where(nobs >= 150, base, np.nan)  # need >=150 of 168 hours present
vmult = q3 / (3 * base)
prior = shift(C, 3) / shift(C, 171) - 1
liquid = base >= SPEC["min_avg_hourly_quote_usd"]
trig = (r3 >= SPEC["trigger_ret_3h"]) & (vmult >= SPEC["trigger_vol_mult"]) & (prior <= SPEC["max_prior_run_7d"]) & liquid
trig &= t[None, :] < T - SPEC["horizon_h"] - 1
cost = SPEC["cost_per_side"]; Hh = SPEC["horizon_h"]
def outcome(i, e):  # entry at open of hour e, for coin i
    ent = O[i, e]
    if not np.isfinite(ent) or ent <= 0: return None
    hh = H[i, e:e + Hh]; ll = L[i, e:e + Hh]; cl = C[i, e:e + Hh]
    if np.isfinite(cl).sum() < Hh * 0.9: return None
    entc = ent * (1 + cost)
    mfe = np.nanmax(hh) / entc - 1; mae = np.nanmin(ll) / entc - 1
    def ret_at(k):
        v = cl[k - 1]; return v * (1 - cost) / entc - 1 if np.isfinite(v) else np.nan
    first = lambda x: (int(np.argmax(hh / entc - 1 >= x)) if np.nanmax(hh / entc - 1) >= x else -1)
    return dict(entry=ent, mfe72=mfe, mae72=mae, net24=ret_at(24), net72=ret_at(Hh),
                hit30=mfe >= .3, hit50=mfe >= .5, hit100=mfe >= 1.0, h_to30=first(.3))
events, controls = [], []
last = {}
trig_any = trig.copy()
for e_t in range(T):
    col = np.where(trig[:, e_t])[0]
    if len(col) == 0: continue
    for i in col:
        if e_t - last.get(i, -10**9) < SPEC["cooldown_h"]: continue
        last[i] = e_t
        o = outcome(i, e_t + 1)
        rec = dict(sym=syms[i], trigger_hour=str(grid[e_t]), r3=r3[i, e_t], vol_mult=vmult[i, e_t], prior7d=prior[i, e_t],
                   avg_hourly_quote=base[i, e_t], start_px=C[i, e_t - 3], trig_close=C[i, e_t])
        if o is None:
            rec["status"] = "NO_OUTCOME_DATA"; events.append(rec); continue
        rec.update(o); rec["status"] = "OK"
        rec["already_moved_from_start"] = o["entry"] / C[i, e_t - 3] - 1
        events.append(rec)
        # controls: same entry hour, other liquid coins not triggered within +-72h
        lo_, hi_ = max(0, e_t - 72), min(T, e_t + 73)
        recent = trig_any[:, lo_:hi_].any(axis=1)
        pool = np.where(liquid[:, e_t] & ~recent)[0]
        if len(pool):
            for j in rng.choice(pool, size=min(SPEC["controls_per_event"], len(pool)), replace=False):
                oc = outcome(j, e_t + 1)
                if oc: controls.append(dict(event_sym=syms[i], trigger_hour=str(grid[e_t]), sym=syms[j], **oc))
ev = pd.DataFrame(events); ct = pd.DataFrame(controls)
ev.to_csv(os.path.join(OUT, "events_v0.csv"), index=False); ct.to_csv(os.path.join(OUT, "controls_v0.csv"), index=False)
SPEC["script_sha256"] = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
json.dump(SPEC, open(os.path.join(OUT, "spec_v0.json"), "w"), indent=1)
ok = ev[ev.status == "OK"]
def summ(d):
    return dict(n=len(d), hit30=d.hit30.mean(), hit50=d.hit50.mean(), hit100=d.hit100.mean(),
                net24_mean=d.net24.mean(), net24_median=d.net24.median(), net72_mean=d.net72.mean(),
                net72_median=d.net72.median(), win72=(d.net72 > 0).mean(), mae72_median=d.mae72.median())
res = dict(events_total=len(ev), events_no_data=int((ev.status != "OK").sum()), events=summ(ok), controls=summ(ct),
           already_moved_median=ok.already_moved_from_start.median(),
           by_year={y: summ(ok[ok.trigger_hour.str[:4] == y]) for y in ["2020", "2021", "2022"]},
           ctrl_by_year={y: summ(ct[ct.trigger_hour.str[:4] == y]) for y in ["2020", "2021", "2022"]})
json.dump(res, open(os.path.join(OUT, "summary_v0.json"), "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=lambda x: round(float(x), 4)))
