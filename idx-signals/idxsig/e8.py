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
    checks = {"files": len(recs), "symbols": len(by), "unit": {}, "bars_read": 0, "duplicate_bars": 0,
              "nonmonotonic_files": 0, "off_hour_bars": 0, "bad_symbol_names": []}
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
    hist = np.cumsum(complete, axis=1) - complete                       # complete days before day d
    liq = _prior_days(np.where(complete, qd, np.nan), 30, "median", 20)  # note 2
    bad_prior = _prior_days(bad.astype(float), BAD_DAYS, "max", 1) > 0
    absent = ~h.present.reshape(n, -1, 24).any(axis=2)
    run = np.zeros_like(absent, dtype=float)                            # consecutive absent days ending at d
    for k in range(absent.shape[1]):
        run[:, k] = np.where(absent[:, k], (run[:, k - 1] if k else 0) + 1, 0)
    gap_prior = _prior_days(run, GAP_LOOK, "max", 1) > GAP_DAYS         # note 4
    r, valid = e6.hourly_returns(h)
    full24 = pd.DataFrame(h.present.T.astype(float)).rolling(24, min_periods=24).sum().to_numpy().T == 24
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
    vol24 = pd.DataFrame(np.where(h.present, h.quote, 0.0).T).rolling(24, min_periods=24).sum().to_numpy().T
    liq_h = _days_to_hours(liq, T)
    vsd = np.sqrt(pd.DataFrame(np.where(valid, r, np.nan).T).rolling(720, min_periods=600).var().to_numpy().T)
    return {"elig": elig, "r24": r24, "res24": r24 - med24[None, :], "med24": med24, "res": res,
            "ret": np.where(valid, r, np.nan), "mkt": med_r,
            "vol24": vol24, "liq": liq_h, "vol30h": vsd, "valid": valid}


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
        return (f["elig"] & (f["r24"] >= LEAD_R24) & (f["res24"] >= LEAD_RES)
                & (f["vol24"] >= LEAD_VOLX * f["liq"]))


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
        return (k * s12 - s1 * s2) / np.sqrt((k * s11 - s1 ** 2) * (k * s22 - s2 ** 2))


def links(ret: np.ndarray, mkt: np.ndarray, lead: int, t: int, cand: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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
        c = (rab - rac * rbc) / np.sqrt((1 - rac ** 2) * (1 - rbc ** 2))
    ok = cand & (k >= LINK_MIN_BARS) & np.isfinite(c)
    out[ok] = c[ok]
    nb[:] = k
    return out, nb


def peer_events(h: e6.Hourly, f: dict, period=PERIOD, hold: int = HOLD) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leader triggers and peer events in the decision period (decision hours whose holding window
    t+1..t+hold ends by the last loaded hour). Returns (leaders table, peer events table)."""
    n, T = h.present.shape
    start = h.start
    t_lo = int((pd.Timestamp(period[0], tz="UTC") - start) / pd.Timedelta("1h"))
    t_hi = min(int((pd.Timestamp(period[1], tz="UTC") - start) / pd.Timedelta("1h")), T - 1 - hold)
    lead, raw = leaders(f)
    busy = _recent(raw, QUIET, include_now=True)  # coins that were leaders recently are not candidates
    L_rows, P_rows = [], []
    last_event = np.full(n, -10 ** 9)
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
            L_rows.append({"t": t, "leader": int(L), "r24": float(f["r24"][L, t]), "res24": float(f["res24"][L, t]),
                           "volx": float(f["vol24"][L, t] / f["liq"][L, t]), "candidates": int(c.sum()),
                           "linked_candidates": int(np.isfinite(lk).sum()), "peers": len(top),
                           "best_link": float(np.nanmax(lk)) if np.isfinite(lk).any() else None})
            for i in top:
                picked.setdefault(int(i), []).append((int(L), float(lk[i])))
        for i, lst in sorted(picked.items()):
            if t - last_event[i] <= hold:
                continue  # note 6: one open peer event per coin
            last_event[i] = t
            best = max(lst, key=lambda x: x[1])
            P_rows.append({"t": t, "peer": i, "leader": best[0], "link": best[1], "leaders": len(lst),
                           "res24": float(f["res24"][i, t]), "liq": float(f["liq"][i, t]),
                           "vol30h": float(f["vol30h"][i, t])})
    stamp = lambda df: df.assign(time=start + pd.to_timedelta(df["t"], unit="h")) if len(df) else df
    return stamp(pd.DataFrame(L_rows)), stamp(pd.DataFrame(P_rows))
