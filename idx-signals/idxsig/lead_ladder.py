"""LEAD_LADDER_v1 (research/LEAD_LADDER_v1/PROTOCOL.md): lift of pre-event features against lead.

Anchors on the episode, not the flag. For each episode start t of a kind (FAST_UP, FAST_DOWN, SLOW_UP, SLOW_DOWN)
and each lead k, the features are read at u = t - k and compared with a matched pool of names at u that did not
start the same kind of move in u..t. The void rule (idxsig.void) removes events and pool names that are already
extended at u. Everything is computed from arrays; `Ladder` takes them from an `idxsig.e1.Study` so features,
buckets and the sealed study market are E1's and E2's own.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import void


@dataclass(frozen=True)
class Kind:
    name: str
    horizon: int
    direction: str  # "up" / "down"
    threshold: float = 1.30
    max_day: float | None = None  # largest allowed one-session ratio (up) or its inverse (down)


def kinds_from_protocol(proto: dict) -> dict[str, Kind]:
    return {
        k: Kind(k, v["horizon"], v["direction"], v["threshold"], v["max_day"])
        for k, v in proto["kinds"].items()
    }


def qualifying(level: np.ndarray, kind: Kind) -> np.ndarray:
    """True at t when the level path over t+1..t+H meets the kind's threshold (and its one-session limit)."""
    n, s = level.shape
    H = kind.horizon
    best = np.full((n, s), np.nan)
    ok_day = np.ones((n, s), dtype=bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        for j in range(1, H + 1):
            ahead = np.full((n, s), np.nan)
            ahead[:, : s - j] = level[:, j:] / level[:, : s - j]
            if kind.direction == "up":
                best = np.fmax(best, ahead)
            else:
                best = np.fmin(best, ahead)
            if kind.max_day is not None:
                step = np.full((n, s), np.nan)
                step[:, : s - j] = (
                    level[:, j:] / level[:, j - 1 : s - 1]
                )  # session t+j against t+j-1
                if kind.direction == "up":
                    ok_day &= ~(step > kind.max_day)
                else:
                    ok_day &= ~(step < 1.0 / kind.max_day)
        if kind.direction == "up":
            hit = best >= kind.threshold
        else:
            hit = best <= 1.0 / kind.threshold
    return np.isfinite(best) & hit & ok_day


def first_in(q: np.ndarray, separation: int) -> np.ndarray:
    """q at t with no q in t-separation..t-1."""
    c = np.cumsum(q, axis=1)
    # count of q in t-sep..t-1 = c[t-1] - c[t-sep-1]
    s = q.shape[1]
    cm1 = np.zeros(q.shape, dtype=np.int64)
    cm1[:, 1:] = c[:, :-1]
    csep = np.zeros(q.shape, dtype=np.int64)
    if separation + 1 < s:
        csep[:, separation + 1 :] = c[:, : s - separation - 1]
    before = cm1 - csep
    return q & (before == 0)


def eligible(
    present: np.ndarray, tradeable: np.ndarray, prev: np.ndarray, min_history: int
) -> np.ndarray:
    history = np.cumsum(present, axis=1) - present
    return tradeable & present & (prev > 0) & (history >= min_history)


def tail_stats(v: float, xs: np.ndarray, binary: bool, top_q: float, bot_q: float) -> tuple:
    """(I_top, E_top, I_bot, E_bot, auc) for one event value against its pool values (finite, >= 1)."""
    auc = ((v > xs).sum() + 0.5 * (v == xs).sum()) / len(xs)
    if binary:
        return (float(v == 1), float((xs == 1).mean()), np.nan, np.nan, auc)
    hi = np.quantile(xs, top_q)
    lo = np.quantile(xs, bot_q)
    return (float(v > hi), float((xs > hi).mean()), float(v < lo), float((xs < lo).mean()), auc)


class Ladder:
    """Per-event table for one market. Arrays are (names x sessions) over the sealed study market."""

    def __init__(
        self,
        level,
        present,
        tradeable,
        prev,
        buckets: dict,
        features: dict,
        binary: tuple,
        dates: np.ndarray,
        window: tuple[int, int],
        proto: dict,
    ):
        self.level, self.dates, self.proto = level, dates, proto
        self.features, self.binary = features, set(binary)
        self.feature_names = list(features)
        self.buckets = [buckets[k] for k in proto["pool"]["buckets"]]
        self.elig = eligible(present, tradeable, prev, proto["min_history"])
        vd = proto["void"]
        self.ext = void.extended(level, vd["threshold"], vd["window"], vd["min_periods"])
        self.kinds = kinds_from_protocol(proto)
        self.q = {k: qualifying(level, kd) for k, kd in self.kinds.items()}
        self.cq = {k: np.cumsum(q, axis=1) for k, q in self.q.items()}
        self.lo, self.hi = window  # discovery sessions [lo, hi)
        sep = proto["separation_sessions"]
        self.starts = {}
        for k, kd in self.kinds.items():
            st = first_in(self.q[k], sep) & self.elig
            mask = np.zeros(level.shape[1], dtype=bool)
            a, b = self.lo + sep, self.hi - kd.horizon  # t - sep and t + H inside the window
            if b > a:
                mask[a:b] = True
            self.starts[k] = st & mask[None, :]

    def events(self, kind: str) -> tuple[np.ndarray, np.ndarray]:
        n, t = np.nonzero(self.starts[kind])
        order = np.lexsort((n, t))
        return n[order], t[order]

    def _q_between(self, kind: str, u: int, t: int) -> np.ndarray:
        """Per name: any same-kind qualifying session in u..t."""
        c = self.cq[kind]
        return (c[:, t] - (c[:, u - 1] if u > 0 else 0)) > 0

    def pool(self, n: int, u: int, t: int, kind: str, voided: bool) -> tuple[np.ndarray, int]:
        ok = self.elig[:, u] & ~self._q_between(kind, u, t)
        if voided:
            ok &= ~self.ext[:, u]
        ok[n] = False
        cand = np.flatnonzero(ok)
        mins = self.proto["pool"]["min_size"]
        nb = len(self.buckets)
        for level in range(nb, -1, -1):
            pool = cand
            for b in self.buckets[:level]:
                pool = pool[b[pool, u] == b[n, u]]
            if len(pool) >= mins or level == 0:
                return pool, nb - level
        return cand, nb

    def table(self, kind: str, events: tuple[np.ndarray, np.ndarray] | None = None) -> pd.DataFrame:
        """One row per (event, lead, analysis) with tail counts per feature."""
        ev_n, ev_t = events if events is not None else self.events(kind)
        tq, bq = self.proto["tails"]["top_quantile"], self.proto["tails"]["bottom_quantile"]
        mins = self.proto["pool"]["min_size"]
        rows = []
        for i, (n, t) in enumerate(zip(ev_n, ev_t)):
            for k in self.proto["leads"]:
                u = t - k
                if u < 0 or not self.elig[n, u]:
                    continue
                for analysis in ("void", "all"):
                    voided = analysis == "void"
                    if voided and self.ext[n, u]:
                        continue
                    pool, relaxed = self.pool(n, u, t, kind, voided)
                    row = {
                        "kind": kind,
                        "event": i,
                        "name_idx": int(n),
                        "t": int(t),
                        "lead": k,
                        "u": int(u),
                        "analysis": analysis,
                        "pool_size": len(pool),
                        "relaxed": relaxed,
                    }
                    for f in self.feature_names:
                        arr = self.features[f]
                        v = arr[n, u]
                        xs = arr[pool, u]
                        xs = xs[np.isfinite(xs)]
                        if not np.isfinite(v) or len(xs) < mins:
                            continue
                        it, et, ib, eb, auc = tail_stats(v, xs, f in self.binary, tq, bq)
                        row[f"{f}|top|I"], row[f"{f}|top|E"] = it, et
                        if f not in self.binary:
                            row[f"{f}|bottom|I"], row[f"{f}|bottom|E"] = ib, eb
                        row[f"{f}|auc"] = auc
                    rows.append(row)
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------- aggregation
def _boot_log_se(I: np.ndarray, E: np.ndarray, week: np.ndarray, reps: int, rng) -> float:
    weeks, inv = np.unique(week, return_inverse=True)
    Iw = np.bincount(inv, weights=I, minlength=len(weeks))
    Ew = np.bincount(inv, weights=E, minlength=len(weeks))
    counts = rng.multinomial(len(weeks), np.full(len(weeks), 1.0 / len(weeks)), size=reps)
    num, den = counts @ Iw, counts @ Ew
    with np.errstate(divide="ignore", invalid="ignore"):
        lifts = num / den
    good = np.isfinite(lifts) & (lifts > 0)
    if good.sum() < reps // 2:
        return float("inf")
    return float(np.std(np.log(lifts[good]), ddof=1))


def aggregate(
    tab: pd.DataFrame,
    dates: np.ndarray,
    feature_names: list[str],
    binary: set,
    proto: dict,
    market: str,
) -> pd.DataFrame:
    """Lift per (kind, analysis, lead, feature, tail) with week-bootstrap lower bound and per-year lifts."""
    z = proto["z_one_sided"]
    reps = proto["bootstrap"]["resamples"]
    out = []
    if tab.empty:
        return pd.DataFrame(out)
    tdates = pd.DatetimeIndex(dates.astype("datetime64[ns]"))
    iso = tdates.isocalendar()
    week_of = iso["year"].to_numpy() * 100 + iso["week"].to_numpy()
    year_of = tdates.year.to_numpy()
    for (kind, analysis, lead), g in tab.groupby(["kind", "analysis", "lead"], sort=True):
        week = week_of[g["t"].to_numpy()]
        year = year_of[g["t"].to_numpy()]
        for f in feature_names:
            for tail in ("top",) if f in binary else ("top", "bottom"):
                ci, ce = f"{f}|{tail}|I", f"{f}|{tail}|E"
                if ci not in g:
                    continue
                sel = g[ci].notna().to_numpy()
                I, E = g[ci].to_numpy(float)[sel], g[ce].to_numpy(float)[sel]
                n = int(sel.sum())
                sI, sE = float(I.sum()), float(E.sum())
                lift = sI / sE if sE > 0 else float("nan")
                seed = (
                    proto["bootstrap"]["seed"]
                    + zlib.crc32(f"{market}|{kind}|{analysis}|{int(lead)}|{f}|{tail}".encode())
                    % 10**6
                )
                se = (
                    _boot_log_se(I, E, week[sel], reps, np.random.default_rng(seed))
                    if n and sE > 0
                    else float("inf")
                )
                lower = (
                    float(np.exp(np.log(lift) - z * se)) if lift > 0 and np.isfinite(se) else 0.0
                )
                years = {}
                for y in np.unique(year[sel]):
                    ys = year[sel] == y
                    yE = E[ys].sum()
                    years[str(int(y))] = {
                        "events": int(ys.sum()),
                        "lift": float(I[ys].sum() / yE) if yE > 0 else None,
                    }
                auc = g[f"{f}|auc"].to_numpy(float)
                out.append(
                    {
                        "market": market,
                        "kind": kind,
                        "analysis": analysis,
                        "lead": int(lead),
                        "feature": f,
                        "tail": tail,
                        "events": n,
                        "observed": sI,
                        "expected": sE,
                        "lift": lift,
                        "log_se": se,
                        "lower_bound": lower,
                        "auc_mean": float(np.nanmean(auc)) if np.isfinite(auc).any() else None,
                        "years": years,
                    }
                )
    return pd.DataFrame(out)


def gate(agg: pd.DataFrame, proto: dict) -> pd.DataFrame:
    """Apply G1-G5 to the primary (void) analysis, up kinds, gated leads."""
    gs = proto["gates"]
    rows = []
    prim = agg[agg["analysis"] == "void"]
    key = prim.set_index(["market", "kind", "lead", "feature", "tail"])
    for up, down in proto["pairs"].items():
        cells = prim[(prim["kind"] == up) & (prim["lead"].isin(proto["gated_leads"]))]
        for r in cells.itertuples(index=False):
            try:
                dl = key.loc[(r.market, down, r.lead, r.feature, r.tail), "lift"]
            except KeyError:
                dl = float("nan")
            yrs = [
                v["lift"] for v in r.years.values() if v["events"] >= gs["G4_min_events_per_year"]
            ]
            g1 = bool(r.lift >= gs["G1_min_lift"])
            g2 = bool(r.lower_bound > gs["G2_lower_bound_above"])
            g3 = bool(np.isfinite(dl) and r.lift >= gs["G3_min_ratio_to_down"] * dl)
            g4 = bool(
                len(yrs) > 0
                and all(y is not None and y >= gs["G4_min_lift_each_year"] for y in yrs)
            )
            g5 = bool(r.events >= gs["G5_min_events"] and r.expected >= gs["G5_min_expected"])
            rows.append(
                {
                    "market": r.market,
                    "kind": r.kind,
                    "lead": r.lead,
                    "feature": r.feature,
                    "tail": r.tail,
                    "events": r.events,
                    "expected": r.expected,
                    "lift": r.lift,
                    "lower_bound": r.lower_bound,
                    "down_lift": dl,
                    "G1": g1,
                    "G2": g2,
                    "G3": g3,
                    "G4": g4,
                    "G5": g5,
                    "passes": g1 and g2 and g3 and g4 and g5,
                    "movement_only": g1 and g2 and g4 and g5 and not g3,
                }
            )
    return pd.DataFrame(rows)


def verdict(gates: pd.DataFrame, proto: dict) -> dict:
    confirming = [m for m, v in proto["markets"].items() if v["can_confirm"]]
    passing = gates[gates["passes"]] if len(gates) else gates
    horizon = {}
    for (m, k, f, t), g in (
        passing.groupby(["market", "kind", "feature", "tail"]) if len(passing) else []
    ):
        horizon[f"{m}|{k}|{f}|{t}"] = int(g["lead"].max())
    if len(passing) and passing["market"].isin(confirming).any():
        v = "LEAD_FOUND"
    elif len(passing):
        v = "LEAD_US_ONLY"
    else:
        v = "NO_DAYS_AHEAD_LEAD"
    best = None
    if len(passing):
        p = passing[passing["market"].isin(confirming)] if v == "LEAD_FOUND" else passing
        p = p.sort_values(["lead", "lift"], ascending=[False, False])
        best = p.iloc[0][
            ["market", "kind", "lead", "feature", "tail", "lift", "lower_bound"]
        ].to_dict()
    mo = gates[gates["movement_only"]] if len(gates) else gates
    return {
        "verdict": v,
        "cells_gated": int(len(gates)),
        "cells_passing": int(len(passing)),
        "horizons": horizon,
        "best_cell": best,
        "movement_only_cells": int(len(mo)),
        "movement_only": mo[
            ["market", "kind", "lead", "feature", "tail", "lift", "down_lift"]
        ].to_dict("records")
        if len(mo)
        else [],
    }
