"""Shared code for HERMES_NOV3_REPRO_v1. Detector, controls, clues and X4 copied from Hermes's pushed scripts
(hermes/ignition-combo-holdout-v1 @ c7c84127: scan_v0.py, run_holdout_v1.py, fib_trend_v1.py, exposure_v1.py).
Additions (PROTOCOL.md): corrected past-only controls, generic hourly exit simulator, funding and Fear & Greed lookups."""
import glob, io, json, os, pickle, zipfile
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CACHE = RAW / "cache"; CACHE.mkdir(parents=True, exist_ok=True)
COST = 0.003
NS = [11, 21, 50, 100, 200, 500]
SEGMENTS = {
    "disc": dict(universe=("hermes_universe_2020_22.json", "usdt_universe"), start="2020-01-01", end="2022-12-31 23:00",
                 months=("2020-01", "2022-12"), first_event="2020-01-01"),
    "hold": dict(universe=("hermes_universe_2023_26.json", "universe"), start="2022-11-01", end=None,
                 months=("2022-11", "2026-10"), first_event="2023-01-01"),
}


def read_zip(fp, cols_idx):
    with zipfile.ZipFile(fp) as z:
        df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(df.iloc[0, 0]).isdigit():
        df = df.iloc[1:]
    df = df.iloc[:, cols_idx].astype(float)
    t = df.iloc[:, 0].values.astype("int64"); t = np.where(t > 1e14, t // 1000, t)  # microseconds -> ms (2025+)
    df.iloc[:, 0] = t
    return df


class Seg:
    """Hourly matrices for one segment, as Hermes built them."""

    def __init__(self, name):
        cfg = SEGMENTS[name]; self.name = name
        cp = CACHE / f"seg_{name}.pkl"
        if cp.exists():
            self.__dict__.update(pickle.load(open(cp, "rb"))); return
        f, key = cfg["universe"]; uni = set(json.load(open(HERE / f))[key])
        fr, nfiles = [], 0
        for fp in sorted(glob.glob(str(RAW / "k1h" / "*.zip"))):
            b = os.path.basename(fp); s = b.split("-1h-")[0]; ym = b[-11:-4]
            if s not in uni or not (cfg["months"][0] <= ym <= cfg["months"][1]):
                continue
            d = read_zip(fp, [0, 1, 2, 3, 4, 7]); d.columns = ["t", "open", "high", "low", "close", "qv"]; d["sym"] = s
            fr.append(d); nfiles += 1
        p = pd.concat(fr); p["ts"] = pd.to_datetime(p.t.astype("int64"), unit="ms", utc=True); del fr
        end = pd.Timestamp(cfg["end"], tz="UTC") if cfg["end"] else p.ts.max().floor("h")
        grid = pd.date_range(pd.Timestamp(cfg["start"], tz="UTC"), end, freq="h")
        p = p[(p.ts >= grid[0]) & (p.ts <= grid[-1])].drop_duplicates(["sym", "ts"])
        syms = sorted(p.sym.unique()); idx = {s: i for i, s in enumerate(syms)}; T = len(grid)
        mats = {}
        for col in ["open", "high", "low", "close", "qv"]:
            m = np.full((len(syms), T), np.nan)
            for s, g in p.groupby("sym"):
                m[idx[s], grid.get_indexer(g.ts)] = g[col].values
            mats[col] = m
        state = dict(grid=grid, syms=syms, idx=idx, T=T, O=mats["open"], H=mats["high"], L=mats["low"], C=mats["close"],
                     Q=mats["qv"], nfiles=nfiles, first_event=cfg["first_event"])
        pickle.dump(state, open(cp, "wb"), protocol=4)
        self.__dict__.update(state)


def shift(a, k):
    o = np.full_like(a, np.nan); o[:, k:] = a[:, :-k]; return o


def detect(sg, ret_h=3, ret_min=0.10):
    """Hermes's ignition detector (ret_h=3, +10%). ret_h=1, ret_min=0.05 gives the EARLY alarm (PROTOCOL Study 1)."""
    C, Q, T = sg.C, sg.Q, sg.T
    r = C / shift(C, ret_h) - 1
    qn = Q.copy()
    for k in range(1, ret_h):
        qn = qn + shift(Q, k)
    cs = np.concatenate([np.zeros((len(sg.syms), 1)), np.nancumsum(np.nan_to_num(Q), axis=1)], axis=1)
    cc = np.concatenate([np.zeros((len(sg.syms), 1)), np.cumsum(np.isfinite(Q).astype(float), axis=1)], axis=1)
    t = np.arange(T); lo = t - 170; hi = t - 2; valid = lo >= 0   # base window t-170..t-3, as Hermes (fixed to 3h)
    base = np.full_like(Q, np.nan); nobs = np.full_like(Q, np.nan)
    base[:, valid] = (cs[:, hi[valid]] - cs[:, lo[valid]]) / 168.0; nobs[:, valid] = cc[:, hi[valid]] - cc[:, lo[valid]]
    base = np.where(nobs >= 150, base, np.nan)
    vmult = qn / (ret_h * base); prior = shift(C, 3) / shift(C, 171) - 1; liquid = base >= 20000
    with np.errstate(invalid="ignore"):
        trig = (r >= ret_min) & (vmult >= 5) & (prior <= .30) & liquid
    trig &= (t[None, :] < T - 72 - 1)
    return dict(trig=trig, base=base, liquid=liquid, r=r, vmult=vmult, prior=prior)


def ok72(sg, i, e):
    if e >= sg.T:
        return False
    ent = sg.O[i, e]
    return bool(np.isfinite(ent) and ent > 0 and np.isfinite(sg.C[i, e:e + 72]).sum() >= 72 * .9)


def events_and_controls(sg, det, cooldown=72, n_ctrl=5):
    """Events with Hermes's cooldown; Hermes's controls (+/-72h exclusion, seed 7) and corrected past-only controls."""
    trig, liquid, T = det["trig"], det["liquid"], sg.T
    start_t = sg.grid.get_indexer([pd.Timestamp(sg.first_event, tz="UTC")])[0]
    rng = np.random.default_rng(7); rng2 = np.random.default_rng(7)
    last, ev, ct, ct2 = {}, [], [], []
    for e_t in range(T):
        for i in np.where(trig[:, e_t])[0]:
            if e_t - last.get(i, -10**9) < cooldown:
                continue
            last[i] = e_t
            if e_t < start_t:
                continue
            if not ok72(sg, i, e_t + 1):
                ev.append((i, e_t, "NO_OUTCOME_DATA")); continue
            ev.append((i, e_t, "OK"))
            recent = trig[:, max(0, e_t - 72):min(T, e_t + 73)].any(axis=1)
            pool = np.where(liquid[:, e_t] & ~recent)[0]
            if len(pool):
                for j in rng.choice(pool, size=min(n_ctrl, len(pool)), replace=False):
                    if ok72(sg, j, e_t + 1):
                        ct.append((j, e_t))
            past = trig[:, max(0, e_t - 72):e_t + 1].any(axis=1)
            pool2 = np.where(liquid[:, e_t] & ~past)[0]
            if len(pool2):
                for j in rng2.choice(pool2, size=min(n_ctrl, len(pool2)), replace=False):
                    if ok72(sg, j, e_t + 1):
                        ct2.append((j, e_t))
    return ev, ct, ct2


def load_daily(syms):
    cp = CACHE / "daily.pkl"
    if cp.exists():
        d = pickle.load(open(cp, "rb"))
    else:
        dr = []
        for fp in glob.glob(str(RAW / "k1d" / "*.zip")):
            s = os.path.basename(fp).split("-1d-")[0]
            x = read_zip(fp, [0, 1, 2, 3, 4, 7]); x.columns = ["t", "open", "high", "low", "close", "qv"]; x["sym"] = s; dr.append(x)
        D = pd.concat(dr); D["date"] = pd.to_datetime(D.t.astype("int64"), unit="ms", utc=True).dt.normalize()
        D = D.drop_duplicates(["sym", "date"]).sort_values(["sym", "date"])
        d = {s: (g.date.values, g.open.values, g.high.values, g.low.values, g.close.values, g.qv.values) for s, g in D.groupby("sym")}
        pickle.dump(d, open(cp, "wb"), protocol=4)
    return {s: v for s, v in d.items() if syms is None or s in syms}


LV = (.618, 1.0)


def _cross(px, start, h, l):
    if len(h) < 20:
        return np.nan
    Hh, Ll = np.nanmax(h), np.nanmin(l)
    if not (Hh > Ll > 0) or not np.isfinite(start):
        return np.nan
    a, b = (start - Ll) / (Hh - Ll), (px - Ll) / (Hh - Ll)
    return float(any(a < v <= b for v in LV))


def clues(sg, daily, i, tt):
    """As run_holdout_v1.py: daily bars strictly before the trigger day; price = trigger-hour close."""
    s = sg.syms[i]; px, start = sg.C[i, tt], sg.C[i, tt - 3]; day = sg.grid[tt].normalize()
    f = dict(above_count=np.nan, stack=np.nan, res200_dist=np.nan, sma100_dist=np.nan, fib200=np.nan, fib50=np.nan)
    if s not in daily:
        return f
    dd, _, dh, dl, dc, _ = daily[s]; k = np.searchsorted(dd, np.datetime64(day.tz_convert(None)), side="left")
    dh, dl, dc = dh[:k], dl[:k], dc[:k]
    sm = {n: (dc[-n:].mean() if len(dc) >= n else np.nan) for n in NS}
    if np.isfinite(sm[200]):
        f["above_count"] = float(sum(px > sm[n] for n in NS if np.isfinite(sm[n])))
        f["stack"] = float(sm[11] > sm[21] > sm[50] > sm[100] > sm[200])
    if np.isfinite(sm[100]):
        f["sma100_dist"] = px / sm[100] - 1
    if len(dh) >= 200:
        f["res200_dist"] = px / dh[-200:].max() - 1; f["fib200"] = _cross(px, start, dh[-200:], dl[-200:])
    f["fib50"] = _cross(px, start, dh[-50:], dl[-50:])
    return f


def score(f):
    return int((f["above_count"] >= 5) + (f["stack"] == 1) + (f["res200_dist"] >= -0.15) + (f["sma100_dist"] >= 0.5)
               + (f["fib200"] == 1) + (f["fib50"] == 1))


def trend(f):
    return bool((f["above_count"] >= 5) and (f["res200_dist"] >= -0.15))


def window(sg, i, e, n):
    """Hours e..e+n-1; None unless >= 90% of closes present. Returns highs, lows, forward-filled closes, opens."""
    if e + n > sg.T:
        return None
    c = sg.C[i, e:e + n]
    m = np.isfinite(c)
    if m.sum() < .9 * n:
        return None
    j = np.maximum.accumulate(np.where(m, np.arange(n), 0))   # forward fill (leading gap stays NaN, as pandas ffill)
    cf = c[j]; cf[: np.argmax(m)] = np.nan
    return sg.H[i, e:e + n], sg.L[i, e:e + n], cf, sg.O[i, e:e + n]


def _first(mask):
    return int(np.argmax(mask)) if mask.any() else 10**9


def x4(sg, i, e, ent):
    """Hermes's X4: +50% take-profit on hourly highs from hour e, else close of hour e+335. Net of 0.3% per side."""
    w = window(sg, i, e, 336)
    if w is None or not (np.isfinite(ent) and ent > 0):
        return None
    hh, _, cf, _ = w; entc = ent * (1 + COST)
    with np.errstate(invalid="ignore"):
        if (hh >= ent * 1.5).any():
            return ent * 1.5 * (1 - COST) / entc - 1
    return cf[335] * (1 - COST) / entc - 1


def sim_exit(sg, i, e, ent, tp, sl, maxh):
    """Long from price ent at the start of hour e. tp/sl as fractions (sl negative) or None. Stop checked first in a
    bar that touches both. Time exit at the close of hour e+maxh-1. Net of 0.3% per side. None without the window."""
    w = window(sg, i, e, maxh)
    if w is None or not (np.isfinite(ent) and ent > 0):
        return None
    hh, ll, cf, oo = w; entc = ent * (1 + COST); out = lambda x: x * (1 - COST) / entc - 1
    with np.errstate(invalid="ignore"):
        ks = _first(ll <= ent * (1 + sl)) if sl is not None else 10**9
        kt = _first(hh >= ent * (1 + tp)) if tp is not None else 10**9
    if ks <= kt and ks < maxh:
        px = ent * (1 + sl); o = oo[ks]
        return out(min(o, px) if np.isfinite(o) else px)
    if kt < maxh:
        return out(ent * (1 + tp))
    return out(cf[maxh - 1])


def load_fng():
    f = pd.DataFrame(json.load(open(HERE / "hermes_fng_alternative_me.json"))["data"])
    f["date"] = pd.to_datetime(f.timestamp.astype("int64"), unit="s", utc=True).dt.normalize()
    f = f.drop_duplicates("date").set_index("date").sort_index()
    return f["value"].astype(int), f["value_classification"]


def load_funding():
    cp = CACHE / "funding.pkl"
    if cp.exists():
        return pd.read_pickle(cp)
    fr = []
    for fp in glob.glob(str(RAW / "fund" / "*.zip")):
        s = os.path.basename(fp).split("-fundingRate-")[0]
        with zipfile.ZipFile(fp) as z:
            d = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
        if not len(d):
            continue
        tcol = [c for c in d.columns if "time" in c.lower()][0]; rcol = [c for c in d.columns if "rate" in c.lower()][0]
        t = d[tcol].astype("int64").values; t = np.where(t > 1e14, t // 1000, t)
        fr.append(pd.DataFrame({"sym": s, "ts": pd.to_datetime(t, unit="ms", utc=True), "rate": d[rcol].astype(float).values}))
    F = pd.concat(fr).drop_duplicates(["sym", "ts"]).sort_values(["sym", "ts"]).reset_index(drop=True)
    F.to_pickle(cp)
    return F
