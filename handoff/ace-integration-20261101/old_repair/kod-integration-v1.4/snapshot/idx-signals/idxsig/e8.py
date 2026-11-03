"""Experiment E8-PEER-SPILLOVER: when one coin reprices on its own, do its closely linked coins that have
not moved yet follow? Signal side (research/E8/FEASIBILITY_SPEC.md; implementation choices in
research/E8/IMPLEMENTATION_NOTES.md, cited as "note n").

Reuses E6's checksum-verified hourly loader layout (idxsig.e6.Hourly / build_hourly). Nothing after
LAST_HOUR is read; the signal functions only look at bars up to the decision hour.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from idxsig import e6
from idxsig.global_panel import LEVERAGED, STABLE

PKG_ROOT = e6.PKG_ROOT
E8_DIR = PKG_ROOT / "research" / "E8"
LAST_HOUR = pd.Timestamp("2022-12-31 23:00", tz="UTC")
PERIOD = ("2020-07-01 00:00", "2022-12-31 23:00")

# signal constants, fixed in FEASIBILITY_SPEC.md before any E8 data was read
LEAD_R24, LEAD_RES, LEAD_VOLX = 0.25, 0.20, 3.0
PEER_RES_MAX, LINK_MIN, TOP_K = 0.05, 0.20, 3
LINK_BARS, LINK_MIN_BARS, LINK_LAG = 720, 600, 24
QUIET, HOLD = 72, 72
MIN_DAYS, LIQ_MIN, BAD_DAYS, GAP_DAYS, GAP_LOOK = 60, 1_000_000.0, 37, 7, 60
MIN_XS = 20  # coins needed for a cross-sectional median (note 3)
ASSET_BACKED = {"PAXG", "BKRW"}  # never eligible (amendment 1): gold token, KRW stablecoin


# ----------------------------------------------------------------------------------------------- data
def load(manifest: Path, last_hour: pd.Timestamp = LAST_HOUR) -> tuple[e6.Hourly, dict]:
    """Like e6.load_manifest, but records timestamp and identity checks before de-duplication (note 1)."""
    if last_hour >= pd.Timestamp("2023-01-01", tz="UTC"):
        raise e6.HoldoutError("E8 discovery never reads 2023 or later")
    lines = [json.loads(x) for x in Path(manifest).read_text().splitlines()]
    recs = [r for r in lines[1:] if r["month"] <= last_hour.strftime("%Y-%m")]
    by: dict = {}
    for r in recs:
        by.setdefault(r["symbol"], []).append(r)
    checks = {
        "files": len(recs),
        "symbols": len(by),
        "unit": {},
        "bars_read": 0,
        "duplicate_bars": 0,
        "nonmonotonic_files": 0,
        "off_hour_bars": 0,
        "bad_symbol_names": [],
    }
    frames = {}
    for sym, rs in sorted(by.items()):
        base = sym[:-4]
        if not sym.endswith("USDT") or base in STABLE or LEVERAGED.search(base):
            checks["bad_symbol_names"].append(sym)
            continue
        if base in ASSET_BACKED:
            checks.setdefault("asset_backed_excluded", []).append(sym)
            continue
        parts = []
        for r in sorted(rs, key=lambda r: r["month"]):
            df = e6._read_zip(PKG_ROOT / "data" / "raw" / r["file"])
            unit = "us" if df["open_time"].max() > 1e14 else "ms"
            checks["unit"][unit] = checks["unit"].get(unit, 0) + 1
            ts = pd.to_datetime(df["open_time"], unit=unit, utc=True)
            checks["nonmonotonic_files"] += int(not ts.is_monotonic_increasing)
            checks["off_hour_bars"] += int(((ts.dt.minute != 0) | (ts.dt.second != 0)).sum())
            df["t"] = ts
            parts.append(df)
        df = pd.concat(parts, ignore_index=True)
        checks["bars_read"] += len(df)
        checks["duplicate_bars"] += int(df["t"].duplicated().sum())
        df = df.drop_duplicates("t").sort_values("t").rename(columns={"tb_quote": "tb"})
        frames[sym] = df[["t", "open", "high", "low", "close", "quote", "tb"]]
    h = e6.build_hourly(frames, last_hour)
    return h, {"manifest": Path(manifest).name, "last_hour": str(last_hour), "checks": checks}


# ------------------------------------------------------------------------------------------- features
def _days_to_hours(a: np.ndarray, n_hours: int) -> np.ndarray:
    return np.repeat(a, 24, axis=1)[:, :n_hours]


def _prior_days(x: np.ndarray, window: int, how: str, min_periods: int) -> np.ndarray:
    """Rolling statistic over days d-window..d-1 (strictly before day d), per coin."""
    df = pd.DataFrame(x.T)
    r = df.rolling(window, min_periods=min_periods)
    out = getattr(r, how)().shift(1)
    return out.to_numpy().T


def features(h: e6.Hourly) -> dict:
    """Per (coin, hour) quantities known at the close of that hour (notes 2-5)."""
    n, T = h.present.shape
    d = e6.daily(h)
    complete, qd, bad = d["complete"], d["qd"], d["bad"]
    hist = np.cumsum(complete, axis=1) - complete  # complete days before day d
    liq = _prior_days(np.where(complete, qd, np.nan), 30, "median", 20)  # note 2
    bad_prior = _prior_days(bad.astype(float), BAD_DAYS, "max", 1) > 0
    absent = ~h.present.reshape(n, -1, 24).any(axis=2)
    run = np.zeros_like(absent, dtype=float)  # consecutive absent days ending at d
    for k in range(absent.shape[1]):
        run[:, k] = np.where(absent[:, k], (run[:, k - 1] if k else 0) + 1, 0)
    gap_prior = _prior_days(run, GAP_LOOK, "max", 1) > GAP_DAYS  # note 4
    r, valid = e6.hourly_returns(h)
    full24 = (
        pd.DataFrame(h.present.T.astype(float)).rolling(24, min_periods=24).sum().to_numpy().T == 24
    )
    with np.errstate(invalid="ignore"):
        day_ok = (hist >= MIN_DAYS) & (liq >= LIQ_MIN) & ~bad_prior & ~gap_prior
    elig = _days_to_hours(day_ok, T) & full24
    close24 = np.concatenate([np.full((n, 24), np.nan), h.close[:, :-24]], axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        r24 = np.where(full24 & (close24 > 0) & (h.close > 0), h.close / close24 - 1, np.nan)
    med24 = _xs_median(r24, elig)
    rmask = elig & valid
    med_r = _xs_median(np.where(rmask, r, np.nan), rmask)
    res = np.where(valid & np.isfinite(med_r)[None, :], r - med_r[None, :], np.nan)  # note 3
    vol24 = (
        pd.DataFrame(np.where(h.present, h.quote, 0.0).T)
        .rolling(24, min_periods=24)
        .sum()
        .to_numpy()
        .T
    )
    liq_h = _days_to_hours(liq, T)
    vsd = np.sqrt(
        pd.DataFrame(np.where(valid, r, np.nan).T).rolling(720, min_periods=600).var().to_numpy().T
    )
    return {
        "elig": elig,
        "r24": r24,
        "res24": r24 - med24[None, :],
        "med24": med24,
        "res": res,
        "ret": np.where(valid, r, np.nan),
        "mkt": med_r,
        "vol24": vol24,
        "liq": liq_h,
        "vol30h": vsd,
        "valid": valid,
    }


def _xs_median(x: np.ndarray, mask: np.ndarray) -> np.ndarray:
    v = np.where(mask, x, np.nan)
    cnt = np.isfinite(v).sum(axis=0)
    with np.errstate(all="ignore"):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            m = np.nanmedian(v, axis=0)
    return np.where(cnt >= MIN_XS, m, np.nan)


def leader_raw(f: dict) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return (
            f["elig"]
            & (f["r24"] >= LEAD_R24)
            & (f["res24"] >= LEAD_RES)
            & (f["vol24"] >= LEAD_VOLX * f["liq"])
        )


def _recent(raw: np.ndarray, back: int, include_now: bool) -> np.ndarray:
    """True where raw held in any of the previous `back` hours (and in the current hour if include_now)."""
    c = np.concatenate([np.zeros((raw.shape[0], 1)), np.cumsum(raw, axis=1)], axis=1)
    T = raw.shape[1]
    idx = np.arange(T)
    hi = idx + (1 if include_now else 0)
    lo = np.maximum(idx - back, 0)
    return (c[:, hi] - c[:, lo]) > 0


def leaders(f: dict) -> tuple[np.ndarray, np.ndarray]:
    """Leader trigger (first crossing: no raw leader condition in the previous QUIET hours, note 5)."""
    raw = leader_raw(f)
    return raw & ~_recent(raw, QUIET, include_now=False), raw


def _corr(k, s1, s2, s11, s22, s12):
    with np.errstate(invalid="ignore", divide="ignore"):
        return (k * s12 - s1 * s2) / np.sqrt((k * s11 - s1**2) * (k * s22 - s2**2))


def links(
    ret: np.ndarray, mkt: np.ndarray, lead: int, t: int, cand: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Partial correlation, given the market return, between `lead` and every candidate's hourly log
    returns over bars t-743..t-24 (amendment 1). ret: NaN where invalid; mkt: per-bar market median."""
    hi = t - LINK_LAG + 1
    lo = hi - LINK_BARS
    n = ret.shape[0]
    out, nb = np.full(n, np.nan), np.zeros(n, dtype=int)
    if lo < 0:
        return out, nb
    X, mk = ret[:, lo:hi], mkt[lo:hi]
    M = np.isfinite(X) & np.isfinite(mk)[None, :]
    msk = M & M[lead][None, :] & cand[:, None]
    A = np.where(msk, X[lead][None, :], 0.0)
    B = np.where(msk, X, 0.0)
    C = np.where(msk, np.nan_to_num(mk)[None, :], 0.0)
    k = msk.sum(axis=1).astype(float)
    sa, sb, sc = A.sum(1), B.sum(1), C.sum(1)
    saa, sbb, scc = (A * A).sum(1), (B * B).sum(1), (C * C).sum(1)
    rab = _corr(k, sa, sb, saa, sbb, (A * B).sum(1))
    rac = _corr(k, sa, sc, saa, scc, (A * C).sum(1))
    rbc = _corr(k, sb, sc, sbb, scc, (B * C).sum(1))
    with np.errstate(invalid="ignore", divide="ignore"):
        c = (rab - rac * rbc) / np.sqrt((1 - rac**2) * (1 - rbc**2))
    ok = cand & (k >= LINK_MIN_BARS) & np.isfinite(c)
    out[ok] = c[ok]
    nb[:] = k
    return out, nb


def peer_events(
    h: e6.Hourly, f: dict, period=PERIOD, hold: int = HOLD
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leader triggers and peer events in the decision period (decision hours whose holding window
    t+1..t+hold ends by the last loaded hour). Returns (leaders table, peer events table)."""
    n, T = h.present.shape
    start = h.start
    t_lo = int((pd.Timestamp(period[0], tz="UTC") - start) / pd.Timedelta("1h"))
    t_hi = min(int((pd.Timestamp(period[1], tz="UTC") - start) / pd.Timedelta("1h")), T - 1 - hold)
    lead, raw = leaders(f)
    busy = _recent(
        raw, QUIET, include_now=True
    )  # coins that were leaders recently are not candidates
    L_rows, P_rows = [], []
    last_event = np.full(n, -(10**9))
    for t in range(t_lo, t_hi + 1):
        ls = np.flatnonzero(lead[:, t])
        if not len(ls):
            continue
        with np.errstate(invalid="ignore"):
            cand = f["elig"][:, t] & ~busy[:, t] & (f["res24"][:, t] <= PEER_RES_MAX)
        picked: dict = {}
        for L in ls:
            c = cand.copy()
            c[L] = False
            lk, nb = links(f["ret"], f["mkt"], L, t, c)
            order = np.argsort(-np.nan_to_num(lk, nan=-9))
            top = [i for i in order[:TOP_K] if np.isfinite(lk[i]) and lk[i] >= LINK_MIN]
            L_rows.append(
                {
                    "t": t,
                    "leader": int(L),
                    "r24": float(f["r24"][L, t]),
                    "res24": float(f["res24"][L, t]),
                    "volx": float(f["vol24"][L, t] / f["liq"][L, t]),
                    "candidates": int(c.sum()),
                    "linked_candidates": int(np.isfinite(lk).sum()),
                    "peers": len(top),
                    "best_link": float(np.nanmax(lk)) if np.isfinite(lk).any() else None,
                }
            )
            for i in top:
                picked.setdefault(int(i), []).append((int(L), float(lk[i])))
        for i, lst in sorted(picked.items()):
            if t - last_event[i] <= hold:
                continue  # note 6: one open peer event per coin
            last_event[i] = t
            best = max(lst, key=lambda x: x[1])
            P_rows.append(
                {
                    "t": t,
                    "peer": i,
                    "leader": best[0],
                    "link": best[1],
                    "leaders": len(lst),
                    "res24": float(f["res24"][i, t]),
                    "liq": float(f["liq"][i, t]),
                    "vol30h": float(f["vol30h"][i, t]),
                }
            )
    stamp = lambda df: df.assign(time=start + pd.to_timedelta(df["t"], unit="h")) if len(df) else df
    return stamp(pd.DataFrame(L_rows)), stamp(pd.DataFrame(P_rows))


# ============================================================================================ outcomes
# research/E8/protocol.json (KOD-CRYPTO-E8-v1, frozen at 8ec2265); details in IMPLEMENTATION_NOTES_OUTCOMES.md
TP, SL, FEE = 0.20, -0.10, 0.001
SLIP_LIQUID, SLIP_THIN, LIQUID = 0.001, 0.002, 10_000_000.0
CTRL_LINK_MAX, DRAWS, SEED = 0.10, 200, 20261016
PER_TRADE = 0.05


def slippage(liq: np.ndarray) -> np.ndarray:
    return np.where(np.asarray(liq) >= LIQUID, SLIP_LIQUID, SLIP_THIN)


def window(
    h: e6.Hourly, coins: np.ndarray, t: int, liq: np.ndarray, entry_off: int = 1, hold: int = HOLD
) -> dict:
    """Outcomes for `coins` decided at the close of hour t: entry at the open of bar t+entry_off, bars
    t+entry_off..t+entry_off+hold-1 (note O1-O4). Only those bars are read."""
    coins = np.asarray(coins, dtype=int)
    k = len(coins)
    e0 = t + entry_off
    e1 = e0 + hold - 1
    out = {
        "has_entry": np.zeros(k, dtype=bool),
        "R72": np.full(k, np.nan),
        "U20": np.zeros(k, dtype=bool),
        "U30": np.zeros(k, dtype=bool),
        "missing_end": np.zeros(k, dtype=bool),
        "net": np.full(k, np.nan),
        "reason": np.full(k, "", dtype=object),
        "bars": np.zeros(k, dtype=int),
    }
    if e1 >= h.present.shape[1] or k == 0:
        return out
    ent = h.open[coins, e0]
    has = h.present[coins, e0] & (ent > 0)
    out["has_entry"] = has
    pw = h.present[coins, e0 : e1 + 1]
    hi, lo, op, cl = (a[coins, e0 : e1 + 1] for a in (h.high, h.low, h.open, h.close))
    tp, sl = ent * (1 + TP), ent * (1 + SL)
    active = has.copy()
    exit_px = np.full(k, np.nan)
    last_close = np.full(k, np.nan)
    for b in range(hold):
        p = pw[:, b] & active
        gap = p & (op[:, b] <= sl)
        stop = p & ~gap & (lo[:, b] <= sl)
        take = p & ~gap & ~stop & (hi[:, b] >= tp)
        exit_px = np.where(gap, op[:, b], np.where(stop, sl, np.where(take, tp, exit_px)))
        out["reason"][gap] = "STOP_GAP"
        out["reason"][stop] = "STOP"
        out["reason"][take] = "TAKE_PROFIT"
        out["bars"][gap | stop | take] = b + 1
        active &= ~(gap | stop | take)
        last_close = np.where(pw[:, b], cl[:, b], last_close)
    timeout = active & np.isfinite(last_close)
    exit_px = np.where(timeout, last_close, exit_px)
    out["reason"][timeout] = "TIMEOUT"
    out["bars"][timeout] = hold
    out["missing_end"] = has & ~pw[:, -1]
    with np.errstate(invalid="ignore", divide="ignore"):
        out["R72"] = np.where(has & np.isfinite(last_close), last_close / ent - 1, np.nan)
        hmax = np.nanmax(np.where(pw, hi, -np.inf), axis=1)
        out["U20"] = has & (hmax >= ent * 1.20)
        out["U30"] = has & (hmax >= ent * 1.30)
        s = slippage(liq)
        out["net"] = np.where(
            has & np.isfinite(exit_px), exit_px * (1 - FEE - s) / (ent * (1 + FEE + s)) - 1, np.nan
        )
    out["reason"][~has] = "NO_ENTRY"
    return out


def _quintile_by(pool_vals: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Quintile of x by the cut points of pool_vals (note O5); -1 when either side is undefined."""
    ok = np.isfinite(pool_vals)
    q = np.full(len(x), -1)
    if ok.sum() < 5:
        return q
    edges = np.percentile(pool_vals[ok], [20, 40, 60, 80])
    fx = np.isfinite(x)
    q[fx] = np.searchsorted(edges, x[fx], side="right")
    return q


def score(h: e6.Hourly, f: dict, P: pd.DataFrame) -> pd.DataFrame:
    """Per peer event: its outcomes and the mean outcomes of 200 matched non-linked draws (E8-MATCH-v1)."""
    n = len(h.symbols)
    lead_raw = leader_raw(f)
    busy = _recent(lead_raw, QUIET, include_now=True)
    rng = np.random.default_rng(SEED)
    rows = []
    for ev in P.sort_values(["t", "peer"]).itertuples(index=False):
        t, i, L = int(ev.t), int(ev.peer), int(ev.leader)
        with np.errstate(invalid="ignore"):
            cand = f["elig"][:, t] & ~busy[:, t] & (f["res24"][:, t] <= PEER_RES_MAX)
        cand[i] = False
        cand[L] = False
        lk, _ = links(f["ret"], f["mkt"], L, t, cand)
        pool = np.flatnonzero(cand & np.isfinite(lk) & (lk < CTRL_LINK_MAX))
        everyone = np.concatenate([[i], pool])
        liq = f["liq"][everyone, t]
        w = window(h, everyone, t, liq)
        wl = window(h, everyone, t, liq, entry_off=2)
        row = {
            "t": t,
            "peer": i,
            "leader": L,
            "link": float(ev.link),
            "liq": float(liq[0]),
            "vol30h": float(f["vol30h"][i, t]),
        }
        if not w["has_entry"][0]:
            rows.append({**row, "status": "NO_ENTRY"})
            continue
        ok = w["has_entry"][1:]
        pool, pidx = pool[ok], np.flatnonzero(ok) + 1
        lq_pool, vq_pool = f["liq"][pool, t], f["vol30h"][pool, t]
        lq = _quintile_by(lq_pool, np.concatenate([[f["liq"][i, t]], lq_pool]))
        vq = _quintile_by(vq_pool, np.concatenate([[f["vol30h"][i, t]], vq_pool]))
        sel = np.flatnonzero((lq[1:] == lq[0]) & (vq[1:] == vq[0]) & (lq[0] >= 0) & (vq[0] >= 0))
        level = "liquidity+volatility"
        if len(sel) < 5:
            sel, level = np.flatnonzero((lq[1:] == lq[0]) & (lq[0] >= 0)), "liquidity"
        if len(sel) < 5:
            sel, level = np.arange(len(pool)), "pool"
        if not len(sel):
            rows.append({**row, "status": "NO_CONTROLS"})
            continue
        dr = pidx[rng.choice(sel, size=DRAWS, replace=True)]
        m = lambda a: float(np.nanmean(np.asarray(a, float)[dr]))
        rows.append(
            {
                **row,
                "status": "SCORED",
                "match_level": level,
                "pool": int(len(pool)),
                "R72": float(w["R72"][0]),
                "U20": bool(w["U20"][0]),
                "U30": bool(w["U30"][0]),
                "net": float(w["net"][0]),
                "reason": w["reason"][0],
                "bars": int(w["bars"][0]),
                "missing_end": bool(w["missing_end"][0]),
                "ctrl_R72": m(w["R72"]),
                "ctrl_U20": m(w["U20"]),
                "ctrl_U30": m(w["U30"]),
                "ctrl_net": m(w["net"]),
                "lat_R72": float(wl["R72"][0]) if wl["has_entry"][0] else np.nan,
                "lat_ctrl_R72": float(
                    np.nanmean(np.where(wl["has_entry"][dr], wl["R72"][dr], np.nan))
                )
                if wl["has_entry"][dr].any()
                else np.nan,
            }
        )
    df = pd.DataFrame(rows)
    if len(df):
        df["time"] = h.start + pd.to_timedelta(df["t"], unit="h")
        df["week"] = e6._weeks(df["time"].dt.tz_convert(None))
        df["year"] = df["time"].dt.year
    return df


# ------------------------------------------------------------------------------------------ statistics
def wilson(k: int, n: int, z: float = 1.959964) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - hw), float(c + hw)]


def _boot(df: pd.DataFrame, col: str) -> dict:
    return e6.week_bootstrap({"a": df.assign(excess=df[col])}, {"a": 1.0})


def exposure(sc: pd.DataFrame) -> dict:
    if not len(sc):
        return {}
    start = sc["t"].to_numpy() + 1
    end = start + sc["bars"].to_numpy()  # position held in hours [start, end)
    ev = np.concatenate(
        [np.stack([start, np.ones(len(sc))], 1), np.stack([end, -np.ones(len(sc))], 1)]
    )
    ev = ev[np.lexsort((ev[:, 1], ev[:, 0]))]  # closes before opens at the same hour
    conc = np.cumsum(ev[:, 1])
    span = end.max() - start.min()
    covered = np.zeros(int(span) + 1, dtype=bool)
    for s, e in zip(start - start.min(), end - start.min()):
        covered[s:e] = True
    order = np.argsort(end, kind="stable")
    curve = np.cumsum(PER_TRADE * sc["net"].to_numpy()[order])
    dd = curve - np.maximum.accumulate(np.concatenate([[0.0], curve]))[1:]
    cap = sc["liq"].to_numpy() / 24 * 0.01
    return {
        "max_concurrent_positions": int(conc.max()),
        "mean_holding_hours": float(sc["bars"].mean()),
        "share_of_hours_with_a_position": float(covered.mean()),
        "per_trade_capital": PER_TRADE,
        "cumulative_net_at_5pct_per_trade": float(curve[-1]),
        "max_drawdown_at_5pct_per_trade": float(dd.min()),
        "capacity_usd_at_1pct_of_hourly_volume": {
            "median": float(np.median(cap)),
            "p10": float(np.percentile(cap, 10)),
        },
    }


def report(df: pd.DataFrame) -> dict:
    sc = df[df["status"] == "SCORED"].copy() if len(df) else df
    out = {
        "events": int(len(df)),
        "scored": int(len(sc)),
        "no_entry": int((df["status"] == "NO_ENTRY").sum()) if len(df) else 0,
        "no_controls": int((df["status"] == "NO_CONTROLS").sum()) if len(df) else 0,
    }
    if not len(sc):
        return out
    sc["excess"] = sc["R72"] - sc["ctrl_R72"]
    sc["dU20"] = sc["U20"].astype(float) - sc["ctrl_U20"]
    sc["dU30"] = sc["U30"].astype(float) - sc["ctrl_U30"]
    sc["dnet"] = sc["net"] - sc["ctrl_net"]
    wins = int((sc["net"] > 0).sum())
    loss = sc.loc[sc["net"] < 0, "net"]
    counts = sc["week"].value_counts()
    busiest = sorted(counts.index, key=lambda w: (-counts[w], w))[:2]
    rest = sc[~sc["week"].isin(busiest)]
    lat = sc.dropna(subset=["lat_R72", "lat_ctrl_R72"])
    out.update(
        {
            "distinct_weeks": int(sc["week"].nunique()),
            "distinct_coins": int(sc["peer"].nunique()),
            "missing_end": int(sc["missing_end"].sum()),
            "match_levels": {k: int(v) for k, v in sc["match_level"].value_counts().items()},
            "information": {
                "mean_R72": float(sc["R72"].mean()),
                "median_R72": float(sc["R72"].median()),
                "mean_ctrl_R72": float(sc["ctrl_R72"].mean()),
                "mean_excess": float(sc["excess"].mean()),
                "vs_controls": _boot(sc, "excess"),
            },
            "moonshot": {
                "U20_rate": float(sc["U20"].mean()),
                "U20_ctrl_rate": float(sc["ctrl_U20"].mean()),
                "U20_difference": _boot(sc, "dU20"),
                "U30_rate": float(sc["U30"].mean()),
                "U30_ctrl_rate": float(sc["ctrl_U30"].mean()),
                "U30_difference": _boot(sc, "dU30"),
            },
            "trading_plan": {
                "mean_net": float(sc["net"].mean()),
                "median_net": float(sc["net"].median()),
                "mean_net_vs_zero": _boot(sc, "net"),
                "mean_ctrl_net": float(sc["ctrl_net"].mean()),
                "mean_net_minus_ctrl": float(sc["dnet"].mean()),
                "win_rate": wins / len(sc),
                "win_rate_wilson95": wilson(wins, len(sc)),
                "mean_win": float(sc.loc[sc["net"] > 0, "net"].mean()) if wins else None,
                "mean_loss": float(loss.mean()) if len(loss) else None,
                "worst_1pct": float(np.percentile(sc["net"], 1)),
                "worst_trade": float(sc["net"].min()),
                "best_trade": float(sc["net"].max()),
                "exit_reasons": {k: int(v) for k, v in sc["reason"].value_counts().items()},
                "exposure": exposure(sc),
            },
            "by_year": {
                str(y): {
                    "scored": int((sc["year"] == y).sum()),
                    "mean_excess": float(sc.loc[sc["year"] == y, "excess"].mean()),
                    "mean_net": float(sc.loc[sc["year"] == y, "net"].mean()),
                }
                for y in sorted(sc["year"].unique())
            },
            "without_two_busiest_weeks": {
                "weeks_dropped": [int(w) for w in busiest],
                "scored": int(len(rest)),
                "mean_excess": float(rest["excess"].mean()) if len(rest) else None,
            },
            "latency_one_hour": {
                "scored": int(len(lat)),
                "mean_excess": float((lat["lat_R72"] - lat["lat_ctrl_R72"]).mean())
                if len(lat)
                else None,
            },
            "by_link_tercile": {
                str(k): float(v)
                for k, v in sc.groupby(
                    pd.qcut(sc["link"], 3, labels=["low", "mid", "high"]), observed=True
                )["excess"]
                .mean()
                .items()
            },
        }
    )
    return out


def gates(rep: dict) -> dict:
    g = {}
    unscorable = (rep["no_entry"] + rep["no_controls"]) / max(1, rep["events"])
    g["G0_sample"] = (
        rep["scored"] >= 300 and rep.get("distinct_weeks", 0) >= 50 and unscorable <= 0.05
    )
    if not rep["scored"]:
        return {"gates": g, "decision": "INCONCLUSIVE", "high_win_rate": False}
    vi, vm, tp = (
        rep["information"]["vs_controls"],
        rep["moonshot"]["U20_difference"],
        rep["trading_plan"],
    )
    pos = lambda b, a: b["estimate"] is not None and b["estimate"] > 0 and b["p_one_sided"] < a
    g["G1_information"] = pos(vi, 0.025)
    g["G2_moonshot"] = pos(vm, 0.025)
    g["G3_trading"] = pos(tp["mean_net_vs_zero"], 0.05) and tp["mean_net_minus_ctrl"] > 0
    g["G4_consistency"] = all(
        (rep["by_year"].get(y) or {}).get("mean_excess", -1) > 0 for y in ("2021", "2022")
    )
    wb = rep["without_two_busiest_weeks"]["mean_excess"]
    g["G5_robustness"] = wb is not None and wb > 0
    if not g["G0_sample"]:
        decision = "INCONCLUSIVE"
    else:
        decision = "PASS" if all(g.values()) else "FAIL"
    hwr = decision == "PASS" and (tp["win_rate_wilson95"][0] or 0) > 0.5
    return {
        "gates": g,
        "decision": decision,
        "high_win_rate": bool(hwr),
        "unscorable_share": unscorable,
    }
