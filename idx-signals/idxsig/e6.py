"""Experiment E6-PRESSURE-RESPONSE (research/E6/protocol.json, KOD-CRYPTO-E6-v1): Stage 1 information gate.

Every choice the frozen protocol leaves open is fixed in research/E6/IMPLEMENTATION_NOTES.md (numbered
notes cited below). Discovery reads no bar after DISCOVERY_LAST_HOUR; no 2023 bar and no 2024+ file is read.
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PKG_ROOT = Path(__file__).resolve().parents[1]
E6_DIR = PKG_ROOT / "research" / "E6"
PROTOCOL = E6_DIR / "protocol.json"
GRID_START = pd.Timestamp("2020-04-01 00:00", tz="UTC")
DISCOVERY_LAST_HOUR = pd.Timestamp("2022-12-31 23:00", tz="UTC")
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote", "count", "tb_base",
        "tb_quote", "ignore"]
H = 120          # outcome bars
RECENT, BASE = 168, 720
ARMS = ("P1_pressure", "P2_pressure_then_breakout", "B0_breakout", "PL_placebo")
PRIMARIES = ("P1_pressure", "P2_pressure_then_breakout")


class HoldoutError(RuntimeError):
    pass


# ----------------------------------------------------------------------------------------------- data
@dataclass
class Hourly:
    symbols: list
    start: pd.Timestamp           # timestamp of hour index 0 (00:00 UTC of day index 0)
    present: np.ndarray           # (coins, hours) bool
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    quote: np.ndarray
    tb: np.ndarray                # taker-buy quote volume

    @property
    def n_days(self):
        return self.present.shape[1] // 24

    def day_dates(self):
        return pd.date_range(self.start, periods=self.n_days, freq="1D")


def _read_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw), header=None, names=COLS)
    if not str(df.iloc[0, 0]).isdigit():
        df = pd.read_csv(io.BytesIO(raw), header=0, names=COLS)
    return df


def build_hourly(frames: dict, last_hour: pd.Timestamp, start: pd.Timestamp = GRID_START) -> Hourly:
    """frames: symbol -> DataFrame with columns t (UTC hour), open, high, low, close, quote, tb. Bars after
    last_hour are dropped here, before anything else sees them (note 4)."""
    if last_hour >= pd.Timestamp("2024-01-01", tz="UTC"):
        raise HoldoutError("E6 never reads 2024 or later")
    n_hours = ((int((last_hour - start) / pd.Timedelta("1h")) + 1) // 24) * 24  # whole days only
    symbols = sorted(frames)
    shape = (len(symbols), n_hours)
    arr = {k: np.full(shape, np.nan) for k in ("open", "high", "low", "close", "quote", "tb")}
    present = np.zeros(shape, dtype=bool)
    for i, s in enumerate(symbols):
        df = frames[s]
        df = df[(df["t"] >= start) & (df["t"] <= last_hour)]
        idx = ((df["t"] - start) / pd.Timedelta("1h")).astype(int).to_numpy()
        ok = (idx >= 0) & (idx < n_hours)
        idx = idx[ok]
        present[i, idx] = True
        for k in arr:
            arr[k][i, idx] = df[k].to_numpy(float)[ok]
    return Hourly(symbols, start, present, **arr)


def load_manifest(manifest: Path, last_hour: pd.Timestamp = DISCOVERY_LAST_HOUR) -> tuple[Hourly, dict]:
    lines = [json.loads(x) for x in Path(manifest).read_text().splitlines()]
    head, recs = lines[0], lines[1:]
    by = {}
    for r in recs:
        if r["month"] > last_hour.strftime("%Y-%m"):
            continue  # note 4: later months are never opened
        by.setdefault(r["symbol"], []).append(r)
    frames = {}
    for sym, rs in by.items():
        parts = [_read_zip(PKG_ROOT / "data" / "raw" / r["file"]) for r in sorted(rs, key=lambda r: r["month"])]
        df = pd.concat(parts, ignore_index=True)
        unit = "us" if df["open_time"].max() > 1e14 else "ms"
        df["t"] = pd.to_datetime(df["open_time"], unit=unit, utc=True)
        df = df.drop_duplicates("t").rename(columns={"tb_quote": "tb"})
        frames[sym] = df[["t", "open", "high", "low", "close", "quote", "tb"]]
    all_syms = sorted({r["symbol"] for r in recs})  # note 11: index over the manifest's full symbol list
    hourly = build_hourly(frames, last_hour)
    return hourly, {"manifest": Path(manifest).name, "symbols_in_manifest": len(all_syms), "symbols_loaded": len(frames),
                    "symbol_index": {s: all_syms.index(s) for s in hourly.symbols}, "last_hour": str(last_hour)}


# ------------------------------------------------------------------------------------------- features
def _csum(x):
    c = np.zeros((x.shape[0], x.shape[1] + 1))
    np.cumsum(np.nan_to_num(x), axis=1, out=c[:, 1:])
    return c


def _win(c, end_idx, length):
    """Sum over hours end-length+1..end (inclusive) for each end in end_idx (array of hour indices)."""
    lo = end_idx - length + 1
    out = np.full((c.shape[0], len(end_idx)), np.nan)
    ok = lo >= 0
    out[:, ok] = c[:, end_idx[ok] + 1] - c[:, lo[ok]]
    return out


def hourly_returns(h: Hourly) -> tuple[np.ndarray, np.ndarray]:
    """r_h and its validity (note 5)."""
    prev = np.concatenate([np.full((h.close.shape[0], 1), np.nan), h.close[:, :-1]], axis=1)
    prevp = np.concatenate([np.zeros((h.close.shape[0], 1), dtype=bool), h.present[:, :-1]], axis=1)
    valid = h.present & prevp & (h.quote > 0) & (h.close > 0) & (prev > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(valid, np.log(h.close / prev), 0.0)
    return r, valid


def absorption(net: np.ndarray, r: np.ndarray, valid: np.ndarray, n_days: int) -> np.ndarray:
    """A_d per (coin, day) from net flow B-S (note 6); NaN where undefined."""
    pos, neg = valid & (net > 0), valid & (net < 0)
    end = np.arange(n_days) * 24 + 23
    out = {}
    for tag, m in (("p", pos), ("n", neg)):
        cr, cf, cn = _csum(np.where(m, r, 0)), _csum(np.where(m, net, 0)), _csum(m.astype(float))
        for w, length, shift in (("r", RECENT, 0), ("b", BASE, RECENT)):
            e = end - shift
            out[tag + w] = (_win(cr, e, length), _win(cf, e, length), _win(cn, e, length))
    with np.errstate(divide="ignore", invalid="ignore"):
        lam = {k: v[0] / v[1] for k, v in out.items()}
        ok = ((out["pr"][2] >= 40) & (out["nr"][2] >= 40) & (out["pb"][2] >= 150) & (out["nb"][2] >= 150)
              & (lam["pr"] > 0) & (lam["nr"] > 0) & (lam["pb"] > 0) & (lam["nb"] > 0))
        A = np.log(lam["pr"]) - np.log(lam["nr"]) - np.log(lam["pb"]) + np.log(lam["nb"])
    return np.where(ok, A, np.nan)


def placebo_net(h: Hourly, net: np.ndarray, symbol_index: dict) -> np.ndarray:
    """|f_h| x seeded random sign per coin (note 11)."""
    out = np.empty_like(net)
    for i, s in enumerate(h.symbols):
        sign = np.random.default_rng(20261015 + symbol_index[s]).choice([-1.0, 1.0], size=net.shape[1])
        out[i] = np.abs(net[i]) * sign
    return out


def daily(h: Hourly) -> dict:
    n, D = len(h.symbols), h.n_days
    rs = lambda a: a.reshape(n, D, 24)
    pres = rs(h.present)
    complete = pres.all(axis=2)
    qd = np.nansum(rs(np.where(h.present, h.quote, 0.0)), axis=2)
    high_d = np.nanmax(np.where(pres, rs(h.high), -np.inf), axis=2)
    high_d = np.where(np.isfinite(high_d), high_d, np.nan)
    cl = rs(np.where(h.present, h.close, np.nan))
    last = np.where(pres.any(axis=2), 23 - np.argmax(pres[:, :, ::-1], axis=2), 0)
    close_d = np.take_along_axis(cl, last[..., None], axis=2)[..., 0]
    close_d = np.where(pres.any(axis=2), close_d, np.nan)
    bad_h = h.present & ((h.tb > h.quote * (1 + 1e-9)) | (h.close <= 0))
    bad_d = rs(bad_h).any(axis=2)
    return {"complete": complete, "qd": qd, "high": high_d, "close": close_d, "bad": bad_d}


def features(h: Hourly, symbol_index: dict) -> dict:
    n, D = len(h.symbols), h.n_days
    r, valid = hourly_returns(h)
    net = 2 * np.nan_to_num(h.tb) - np.nan_to_num(h.quote)  # B - S
    A = absorption(net, r, valid, D)
    A_pl = absorption(placebo_net(h, net, symbol_index), r, valid, D)
    d = daily(h)
    T = lambda a: pd.DataFrame(a.T)  # days x coins
    hist = T(d["complete"].astype(float)).cumsum().shift(1).fillna(0).to_numpy().T
    liq = T(d["qd"]).rolling(30, min_periods=30).median().to_numpy().T
    base_med = T(d["qd"]).rolling(30, min_periods=30).median().shift(7).to_numpy().T
    rec_mean = T(d["qd"]).rolling(7, min_periods=7).mean().to_numpy().T
    with np.errstate(divide="ignore", invalid="ignore"):
        P = np.where(base_med > 0, rec_mean / base_med, np.nan)
    hi30 = T(d["high"]).rolling(30, min_periods=1).max().shift(1).to_numpy().T
    close7 = T(d["close"]).shift(7).to_numpy().T
    with np.errstate(divide="ignore", invalid="ignore"):
        ret7 = d["close"] / close7 - 1
    bad37 = T(d["bad"].astype(float)).rolling(37, min_periods=1).max().to_numpy().T > 0
    # vol30: std of valid hourly returns over the 720 hours of d-29..d
    end = np.arange(D) * 24 + 23
    c1, c2, cn = _csum(np.where(valid, r, 0)), _csum(np.where(valid, r * r, 0)), _csum(valid.astype(float))
    s1, s2, sn = _win(c1, end, 720), _win(c2, end, 720), _win(cn, end, 720)
    with np.errstate(divide="ignore", invalid="ignore"):
        vol30 = np.sqrt(np.maximum(s2 / sn - (s1 / sn) ** 2, 0))
    return {"A": A, "A_pl": A_pl, "P": P, "liq": liq, "hist": hist, "hi30": hi30, "ret7": ret7, "vol30": vol30,
            "bad37": bad37, **d}


# -------------------------------------------------------------------------------------------- outcomes
def outcomes(h: Hourly) -> dict:
    """Per (coin, decision day d): entry = open of bar 01:00 d+1, 120 bars (note 3, 16)."""
    n, D = len(h.symbols), h.n_days
    R = np.full((n, D), np.nan); E30 = np.zeros((n, D), dtype=bool); has = np.zeros((n, D), dtype=bool)
    missing_end = np.zeros((n, D), dtype=bool)
    barrier = np.full((n, D), "", dtype=object)
    for k in range(D):
        e0 = 24 * (k + 1) + 1
        e1 = e0 + H - 1
        if e1 >= h.present.shape[1]:
            break  # window would end after the last loaded bar: no outcome in this period (note 4)
        entry_ok = h.present[:, e0] & (h.open[:, e0] > 0)
        if not entry_ok.any():
            continue
        ent = h.open[:, e0]
        pw = h.present[:, e0:e1 + 1]
        hi, lo, cl = h.high[:, e0:e1 + 1], h.low[:, e0:e1 + 1], h.close[:, e0:e1 + 1]
        lastp = np.where(pw.any(axis=1), H - 1 - np.argmax(pw[:, ::-1], axis=1), 0)
        endc = cl[np.arange(n), lastp]
        with np.errstate(divide="ignore", invalid="ignore"):
            R[:, k] = np.where(entry_ok, endc / ent - 1, np.nan)
            up = pw & (hi >= 1.30 * ent[:, None])
            dn = pw & (lo <= 0.95 * ent[:, None])
        E30[:, k] = entry_ok & up.any(axis=1)
        has[:, k] = entry_ok
        missing_end[:, k] = entry_ok & ~pw[:, -1]
        for i in np.flatnonzero(entry_ok):
            u, d_ = np.flatnonzero(up[i]), np.flatnonzero(dn[i])
            fu, fd = (u[0] if len(u) else H), (d_[0] if len(d_) else H)
            barrier[i, k] = ("TIMEOUT" if fu == fd == H else "UNRESOLVED" if fu == fd else
                             "WIN" if fu < fd else "LOSS")
    return {"R120": R, "E30": E30, "has_entry": has, "missing_end": missing_end, "barrier": barrier}


# ------------------------------------------------------------------------------------------------ arms
def decision_days(h: Hourly, period: tuple) -> np.ndarray:
    dates = h.day_dates()
    return (dates >= pd.Timestamp(period[0], tz="UTC")) & (dates <= pd.Timestamp(period[1], tz="UTC"))


def debounce(raw: np.ndarray, gap: int = 5) -> np.ndarray:
    out = np.zeros_like(raw)
    for i in range(raw.shape[0]):
        last = -10 ** 9
        for k in np.flatnonzero(raw[i]):
            if k - last > gap:
                out[i, k] = True
                last = k
    return out


def _top5(A, elig):
    keep = np.zeros_like(elig)
    for k in range(A.shape[1]):
        m = elig[:, k] & np.isfinite(A[:, k])
        if m.sum() == 0:
            continue
        q = np.percentile(A[m, k], 95)  # note 8
        keep[:, k] = m & (A[:, k] >= q)
    return keep


def arms(f: dict, day_ok: np.ndarray) -> tuple[dict, np.ndarray, dict]:
    elig = (f["hist"] >= 60) & f["complete"] & (f["liq"] >= 200_000) & ~f["bad37"] & day_ok[None, :]
    excl = {"coin_days_failing_sanity_otherwise_eligible": int(((f["hist"] >= 60) & f["complete"] & (f["liq"] >= 200_000)
                                                                 & f["bad37"] & day_ok[None, :]).sum())}
    med7 = np.array([np.nanmedian(f["ret7"][elig[:, k], k]) if np.isfinite(f["ret7"][elig[:, k], k]).any() else np.nan
                     for k in range(elig.shape[1])])
    with np.errstate(invalid="ignore"):
        strength = (f["ret7"] - med7[None, :]) >= 0
        in_range = (f["close"] <= f["hi30"]) & (f["ret7"] >= -0.10) & (f["ret7"] <= 0.15)
        breakout = f["close"] > f["hi30"]
        part = f["P"] >= 1.5
    common = part & in_range & strength
    p1 = debounce(_top5(f["A"], elig) & common)
    pl = debounce(_top5(f["A_pl"], elig) & common)
    b0 = debounce(elig & breakout & part)
    recent_p1 = pd.DataFrame(p1.T.astype(float)).rolling(10, min_periods=1).max().shift(1).fillna(0).to_numpy().T > 0
    p2 = debounce(elig & breakout & part & recent_p1)
    return {"P1_pressure": p1, "P2_pressure_then_breakout": p2, "B0_breakout": b0, "PL_placebo": pl}, elig, excl


# ------------------------------------------------------------------------------------------ statistics
def _quintile(x):
    out = np.full(len(x), -1)
    ok = np.isfinite(x)
    if ok.sum() >= 5:
        out[ok] = np.minimum((pd.Series(x[ok]).rank(method="first").to_numpy() - 1) * 5 // ok.sum(), 4).astype(int)
    return out


def matched(flags: np.ndarray, elig: np.ndarray, f: dict, o: dict, draws: int = 200, seed: int = 20261008) -> pd.DataFrame:
    """Per flag with an entry: outcome and the mean outcome of 200 matched draws (notes 17-18)."""
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(flags.shape[1]):
        fl = np.flatnonzero(flags[:, k])
        if not len(fl):
            continue
        pool = np.flatnonzero(elig[:, k] & o["has_entry"][:, k])
        lq, vq = np.full(flags.shape[0], -1), np.full(flags.shape[0], -1)
        lq[pool], vq[pool] = _quintile(f["liq"][pool, k]), _quintile(f["vol30"][pool, k])
        for i in fl:
            if not o["has_entry"][i, k]:
                rows.append({"coin": i, "day": k, "status": "NO_ENTRY"})
                continue
            cand = pool[(pool != i) & (lq[pool] == lq[i]) & (vq[pool] == vq[i])]
            level = "liquidity+volatility"
            if len(cand) < 5:
                cand, level = pool[(pool != i) & (lq[pool] == lq[i])], "liquidity"
            if len(cand) < 5:
                cand, level = pool[pool != i], "day"
            if not len(cand):
                rows.append({"coin": i, "day": k, "status": "NO_CONTROLS"})
                continue
            dr = rng.choice(cand, size=draws, replace=True)
            rows.append({"coin": i, "day": k, "status": "SCORED", "R120": o["R120"][i, k], "E30": bool(o["E30"][i, k]),
                         "barrier": o["barrier"][i, k], "missing_end": bool(o["missing_end"][i, k]),
                         "ctrl_R120": float(np.mean(o["R120"][dr, k])), "ctrl_E30": float(np.mean(o["E30"][dr, k])),
                         "match_level": level, "A": f["A"][i, k], "A_pl": f["A_pl"][i, k], "P": f["P"][i, k]})
    return pd.DataFrame(rows)


def _weeks(dates):
    iso = pd.DatetimeIndex(dates).isocalendar()
    return (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()


def week_bootstrap(frames: dict, weights: dict, resamples: int = 10_000, seed: int = 20261015) -> dict:
    """Mean of sum_j w_j * mean_excess_j over arms j, week-cluster bootstrap (note 19)."""
    if any(len(df) == 0 for df in frames.values()):
        return {"estimate": None, "ci95": None, "p_one_sided": None, "weeks": 0, "resamples": 0,
                "note": "not computable: an arm has no scored flags"}
    weeks = sorted(set().union(*[set(df["week"]) for df in frames.values()]))
    widx = {w: i for i, w in enumerate(weeks)}
    sums, cnts = {}, {}
    for j, df in frames.items():
        s, c = np.zeros(len(weeks)), np.zeros(len(weeks))
        np.add.at(s, df["week"].map(widx).to_numpy(), df["excess"].to_numpy())
        np.add.at(c, df["week"].map(widx).to_numpy(), 1)
        sums[j], cnts[j] = s, c
    point = sum(w * sums[j].sum() / cnts[j].sum() for j, w in weights.items())
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(weeks), size=(resamples, len(weeks)))
    stat = np.zeros(resamples)
    for j, w in weights.items():
        with np.errstate(invalid="ignore", divide="ignore"):
            stat += w * sums[j][pick].sum(axis=1) / cnts[j][pick].sum(axis=1)
    stat = stat[np.isfinite(stat)]
    return {"estimate": float(point), "ci95": [float(np.percentile(stat, 2.5)), float(np.percentile(stat, 97.5))],
            "p_one_sided": float((1 + (stat <= 0).sum()) / (1 + len(stat))), "weeks": len(weeks), "resamples": int(len(stat))}


def arm_report(df: pd.DataFrame, years=(2021, 2022)) -> dict:
    sc = df[df["status"] == "SCORED"]
    out = {"flags": int(len(df)), "scored": int(len(sc)), "no_entry": int((df["status"] == "NO_ENTRY").sum()),
           "no_controls": int((df["status"] == "NO_CONTROLS").sum()), "missing_end": int(sc["missing_end"].sum()) if len(sc) else 0,
           "distinct_coins": int(sc["symbol"].nunique()) if len(sc) else 0}
    if not len(sc):
        return out
    out.update({"mean_R120": float(sc["R120"].mean()), "median_R120": float(sc["R120"].median()),
                "mean_ctrl_R120": float(sc["ctrl_R120"].mean()), "mean_excess": float(sc["excess"].mean()),
                "E30_rate": float(sc["E30"].mean()), "E30_ctrl_rate": float(sc["ctrl_E30"].mean()),
                "E30_lift": float(sc["E30"].mean() / sc["ctrl_E30"].mean()) if sc["ctrl_E30"].mean() > 0 else None,
                "barrier_shares": {k: float(v) for k, v in sc["barrier"].value_counts(normalize=True).items()},
                "match_levels": {k: int(v) for k, v in sc["match_level"].value_counts().items()},
                "by_year": {str(y): {"scored": int((sc["year"] == y).sum()),
                                     "mean_excess": float(sc.loc[sc["year"] == y, "excess"].mean()) if (sc["year"] == y).any() else None}
                            for y in sorted(sc["year"].unique())},
                "vs_matched": week_bootstrap({"a": sc}, {"a": 1.0})})
    return out


def stage1_gate(rep: dict, vs_placebo: dict, alpha=0.025, alpha_pl=0.05, years=(2021, 2022), min_flags=200) -> dict:
    reasons = []
    if rep["flags"] < min_flags:
        reasons.append(f"flags {rep['flags']} < {min_flags}")
    vm = rep.get("vs_matched")
    if not vm or vm["estimate"] is None or not (vm["estimate"] > 0 and vm["p_one_sided"] < alpha):
        reasons.append(f"excess vs matched {vm and round(vm['estimate'], 5)} with p {vm and round(vm['p_one_sided'], 4)} (needs > 0, p < {alpha})")
    for y in years:
        e = (rep.get("by_year") or {}).get(str(y), {}).get("mean_excess")
        if not (e is not None and e > 0):
            reasons.append(f"mean excess in {y} = {e} (needs > 0)")
    est, p = vs_placebo["estimate"], vs_placebo["p_one_sided"]
    if est is None or not (est > 0 and p < alpha_pl):
        reasons.append(f"minus placebo {est if est is None else round(est, 5)} with p {p if p is None else round(p, 4)} "
                       f"(needs > 0, p < {alpha_pl})")
    return {"passed": not reasons, "reasons": reasons}


def run_stage1(h: Hourly, meta: dict, period=("2020-07-01", "2022-12-31")) -> tuple[dict, pd.DataFrame]:
    f = features(h, meta["symbol_index"])
    o = outcomes(h)
    n_hours = h.present.shape[1]
    fits = np.arange(h.n_days) * 24 + 24 + 1 + H - 1 < n_hours  # whole outcome window loaded (note 4)
    day_ok = decision_days(h, period) & fits
    flags, elig, excl = arms(f, day_ok)
    dates = h.day_dates()
    tables = {}
    for arm in ARMS:
        df = matched(flags[arm], elig, f, o)
        if not len(df):
            df = pd.DataFrame(columns=["coin", "day", "status", "R120", "E30", "barrier", "missing_end", "ctrl_R120",
                                       "ctrl_E30", "match_level", "A", "A_pl", "P", "symbol", "date", "year", "week", "excess"])
        else:
            df["symbol"] = [h.symbols[i] for i in df["coin"]]
            df["date"] = dates[df["day"].to_numpy()].strftime("%Y-%m-%d")
            df["year"] = dates[df["day"].to_numpy()].year
            df["week"] = _weeks(dates[df["day"].to_numpy()])
            if "R120" in df:
                df["excess"] = df["R120"] - df["ctrl_R120"]
        df["arm"] = arm
        tables[arm] = df
    sc = {a: t[t["status"] == "SCORED"] for a, t in tables.items()}
    reports = {a: arm_report(t) for a, t in tables.items()}
    comps, gates = {}, {}
    for a in ("P1_pressure", "P2_pressure_then_breakout"):
        comps[f"{a} minus PL_placebo"] = week_bootstrap({"a": sc[a], "b": sc["PL_placebo"]}, {"a": 1.0, "b": -1.0})
        comps[f"{a} minus B0_breakout"] = week_bootstrap({"a": sc[a], "b": sc["B0_breakout"]}, {"a": 1.0, "b": -1.0})
        gates[a] = stage1_gate(reports[a], comps[f"{a} minus PL_placebo"])
    last = dates[day_ok]
    summary = {"stage": "discovery / Stage 1", "period": list(period),
               "decision_days": [str(last.min().date()), str(last.max().date())] if len(last) else None,
               "eligible_coin_days": int(elig.sum()), "eligible_coins_per_day_median": float(np.median(elig.sum(axis=0)[day_ok])),
               "exclusions": excl, "arms": reports, "comparisons": comps, "gates": gates,
               "stage2": "runs only for an arm whose gate passed"}
    return summary, pd.concat(tables.values(), ignore_index=True)
