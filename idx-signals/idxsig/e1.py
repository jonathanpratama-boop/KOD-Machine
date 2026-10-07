"""Experiment E1 (research/E1/protocol.json, KOD-IDX-E1-v1).

What distinguishes IDX names that reprice +30% / +50% / +100% within five sessions from
similar names on the same session, using only what was known at that session's close?

Stages, each writing a new directory under research/E1/ (frozen by the commit guard):

  discovery   base rates, episodes, the first 100 events with matched controls, weak-signal
              statistics, and the pre-registered detector selection (2021-01-22..2022-12-30)
  validation  the frozen detector on 2023 only: precision and lift against the base rate and
              against matched random controls, recall and lead time, executability

The holdout (2024-01-02 onward) is cut off before anything is computed: the study's market
ends at the last validation session, so no holdout label can be formed by this code.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import controls
from .execution import Market
from .provenance import PKG_ROOT, sha256_file
from .results import code_state
from .rules import moonshot_e1 as family

E1_DIR = PKG_ROOT / "research" / "E1"
PROTOCOL = E1_DIR / "protocol.json"
HORIZON = 5
THRESHOLDS = (0.30, 0.50, 1.00)
MIN_HISTORY = 20
N_FIRST = 100
N_CONTROLS = 5
SEED = 20261008
N_BOOT = 1000
N_RANDOM = 200
BAND_NAMES = ("<=Rp200", "<=Rp5000", ">Rp5000")
CONTINUOUS = ("ret1", "rel1", "ret5", "ret20", "volr", "valr", "freqr", "rngr", "cpos", "vol20", "dd60", "turn",
              "up5", "zero20", "age", "logval20", "logmcap")
BINARY = ("ara", "brk60", "ign")


def protocol() -> tuple[dict, str]:
    return json.loads(PROTOCOL.read_text(encoding="utf-8")), sha256_file(PROTOCOL)


def label(x: float) -> str:
    return f"E{int(round(x * 100))}"


def _lead(a: np.ndarray, k: int) -> np.ndarray:
    """a[:, t + k] at column t (NaN past the end)."""
    out = np.full(a.shape, np.nan)
    out[:, : a.shape[1] - k] = a[:, k:]
    return out


def _lagb(a: np.ndarray, k: int) -> np.ndarray:
    out = np.zeros(a.shape, dtype=bool)
    out[:, k:] = a[:, :-k]
    return out


def _roll(a, window, min_periods, how, shift=0):
    frame = pd.DataFrame(a.T).rolling(window, min_periods=min_periods)
    out = getattr(frame, how)().to_numpy().T
    if shift:
        out = np.concatenate([np.full((out.shape[0], shift), np.nan), out[:, :-shift]], axis=1)
    return out


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


class Study:
    def __init__(self, panel_df: pd.DataFrame, panel_meta: dict):
        proto, self.protocol_sha = protocol()
        self.periods = {k: tuple(v) for k, v in proto["periods"].items()}
        if panel_meta.get("format") != "panel-v2":
            raise ValueError("E1 needs the panel-v2 (share counts)")
        self.panel_sha = panel_meta["sha256"]
        full = Market.from_panel(panel_df)
        # Seal the holdout: nothing after the last validation session exists for this study.
        _, hi = full.bounds(None, self.periods["validation"][1])
        m = full.slice(0, hi)
        self.m = m
        freq = panel_df.pivot_table(index="ticker", columns="date", values="frequency", aggfunc="first")
        freq = freq.reindex(index=m.tickers, columns=pd.DatetimeIndex(m.dates.astype("datetime64[ns]")))
        self.freq = freq.to_numpy(dtype=float)
        self.dates = m.dates
        n, s = m.shape
        present, tradeable = m.present, m.tradeable
        with np.errstate(divide="ignore", invalid="ignore"):
            logret = np.where(present & (m.prev > 0) & (m.close > 0), np.log(m.close / m.prev), 0.0)
        self.level = np.where(present, np.exp(np.cumsum(logret, axis=1)), np.nan)
        L = self.level
        ahead = np.stack([_lead(L, k) for k in range(1, HORIZON + 1)])  # (5, n, s)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratios = ahead / L[None] - 1
        has_fwd = np.isfinite(ratios).any(axis=0)
        self.r5max = np.where(has_fwd, np.nanmax(np.where(np.isfinite(ratios), ratios, -np.inf), axis=0), np.nan)
        self.peak_k = np.where(has_fwd, np.argmax(np.where(np.isfinite(ratios), ratios, -np.inf), axis=0) + 1, 0)
        self.r5 = ratios[HORIZON - 1]
        nxt_trade = np.zeros((n, s), dtype=bool)
        nxt_trade[:, :-1] = tradeable[:, 1:] & ~m.lock_up[:, 1:]
        self.executable = nxt_trade
        with np.errstate(divide="ignore", invalid="ignore"):
            cap = np.stack([_lead(L, k) for k in range(2, HORIZON + 1)]) / _lead(L, 1)[None] - 1
        self.capturable = np.where(nxt_trade & np.isfinite(cap).any(axis=0),
                                   np.nanmax(np.where(np.isfinite(cap), cap, -np.inf), axis=0), np.nan)
        history = np.cumsum(present, axis=1) - present
        base = tradeable & (m.prev > 0) & (history >= MIN_HISTORY) & has_fwd
        self.period_of = np.full(s, "", dtype=object)
        self.elig = {}
        for name in ("discovery", "validation"):
            lo, hi_ = m.bounds(*self.periods[name])
            mask = np.zeros(s, dtype=bool)
            mask[lo: max(lo, hi_ - HORIZON)] = True  # t + 5 stays inside the period
            self.period_of[lo:hi_] = name
            self.elig[name] = base & mask[None, :]
        self.qraw = {x: present & (np.nan_to_num(self.r5max, nan=-1) >= x) for x in THRESHOLDS}
        self.start = {}
        for x, q in self.qraw.items():
            before = np.zeros(q.shape, dtype=bool)
            for k in range(1, HORIZON + 1):
                before |= _lagb(q, k)
            self.start[x] = q & ~before
        self._signals()
        b = controls.features(m, "v2")
        self.buckets = {k: b[k] for k in ("price_band", "liquidity", "market_cap")}
        self.flags = family.family_flags(self.base_feats)

    # ------------------------------------------------------------------ signals
    def _signals(self):
        m = self.m
        f = family.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.lock_up)
        self.base_feats = f
        tr = m.tradeable
        with np.errstate(divide="ignore", invalid="ignore"):
            val = np.where(tr, m.value, np.nan)
            med_val = _roll(val, 20, 10, "median", 1)
            fq = np.where(tr, self.freq, np.nan)
            med_fq = _roll(fq, 20, 10, "median", 1)
            rng = np.where(tr & (m.prev > 0), (m.high - m.low) / m.prev, np.nan)
            med_rng = _roll(rng, 20, 10, "median", 1)
            logret = np.where(tr & (m.prev > 0), np.log(m.close / m.prev), np.where(m.present, 0.0, np.nan))
            first = np.where(m.present.any(axis=1), m.present.argmax(axis=1), m.shape[1])
            untraded = (m.present & ~tr).astype(float)
            sig = {
                **{k: f[k] for k in ("ret1", "rel1", "ret5", "ret20", "volr", "cpos", "dd60")},
                "valr": np.where(med_val > 0, val / med_val, np.nan),
                "freqr": np.where(med_fq > 0, fq / med_fq, np.nan),
                "rngr": np.where(med_rng > 0, rng / med_rng, np.nan),
                "vol20": _roll(logret, 20, 15, "std"),
                "turn": np.where(tr & (m.listed_shares > 0), m.volume / m.listed_shares, np.nan),
                "up5": _roll(np.where(m.present, (np.nan_to_num(f["ret1"]) > 0).astype(float), np.nan), 5, 5, "sum"),
                "zero20": _roll(untraded, 20, 20, "sum", 1),
                "age": (np.arange(m.shape[1])[None, :] - first[:, None]).astype(float),
                "logval20": np.log10(_roll(val, 20, 10, "median")),
                "logmcap": np.log10(m.close * m.listed_shares),
                "ara": f["ara"].astype(float),
                "brk60": f["brk60"].astype(float),
            }
        sig["ign"] = family.family_flags(f)["F2_IGNITION_D"].astype(float)
        self.sig = sig

    # ------------------------------------------------------------------ helpers
    def cells(self, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return np.nonzero(mask)

    def row(self, n: int, d: int) -> dict:
        m = self.m
        out = {
            "ticker": str(m.tickers[n]), "date": str(self.dates[d]), "period": self.period_of[d],
            "close": float(m.close[n, d]), "price_band": BAND_NAMES[int(self.buckets["price_band"][n, d])]
            if self.buckets["price_band"][n, d] >= 0 else "",
            "liquidity_q": int(self.buckets["liquidity"][n, d]) + 1, "market_cap_q": int(self.buckets["market_cap"][n, d]) + 1,
            "r5max": float(self.r5max[n, d]), "peak_k": int(self.peak_k[n, d]),
            "peak_date": str(self.dates[d + self.peak_k[n, d]]) if self.peak_k[n, d] else "",
            "r5": float(self.r5[n, d]), "executable_entry": bool(self.executable[n, d]),
            "capturable": float(self.capturable[n, d]),
        }
        for x in THRESHOLDS:
            out[label(x)] = bool(self.r5max[n, d] >= x)
        for k in CONTINUOUS + BINARY:
            out[k] = float(self.sig[k][n, d])
        return out

    def _pool(self, n: int, d: int, eligible: np.ndarray, extra: np.ndarray | None = None) -> tuple[np.ndarray, int]:
        cand = np.flatnonzero(eligible[:, d])
        cand = cand[cand != n]
        if extra is not None:
            cand = cand[extra[cand, d]]
        keys = ("price_band", "liquidity", "market_cap")
        for level in range(3, -1, -1):
            pool = cand
            for k in keys[:level]:
                pool = pool[self.buckets[k][pool, d] == self.buckets[k][n, d]]
            if len(pool) >= N_CONTROLS or level == 0:
                return pool, 3 - level
        return cand, 3

    # ------------------------------------------------------------------ discovery
    def base_rates(self, period: str) -> pd.DataFrame:
        e = self.elig[period]
        rows = []
        years = self.dates.astype("datetime64[Y]").astype(int) + 1970
        band = self.buckets["price_band"]
        groups = [("all", "all", np.ones(e.shape, dtype=bool))]
        groups += [("price_band", BAND_NAMES[b], band == b) for b in range(3)]
        groups += [("year", str(y), np.broadcast_to((years == y)[None, :], e.shape)) for y in sorted(set(years[e.any(axis=0)]))]
        for kind, value, g in groups:
            sel = e & g
            nsel = int(sel.sum())
            row = {"period": period, "group": kind, "value": value, "eligible_ticker_days": nsel,
                   "sessions": int(sel.any(axis=0).sum())}
            for x in THRESHOLDS:
                k = int((sel & self.qraw[x]).sum())
                lo, hi = wilson(k, nsel)
                row.update({f"{label(x)}_ticker_days": k, f"{label(x)}_rate": k / nsel if nsel else float("nan"),
                            f"{label(x)}_rate_lo95": lo, f"{label(x)}_rate_hi95": hi,
                            f"{label(x)}_episodes": int((sel & self.start[x]).sum())})
            rows.append(row)
        return pd.DataFrame(rows)

    def episodes(self, period: str, x: float) -> pd.DataFrame:
        n_idx, d_idx = self.cells(self.elig[period] & self.start[x])
        order = np.lexsort((self.m.tickers[n_idx], d_idx))
        return pd.DataFrame([self.row(n_idx[i], d_idx[i]) for i in order])

    def matched_controls(self, events: pd.DataFrame, period: str) -> pd.DataFrame:
        tick = pd.Index(self.m.tickers)
        day = pd.Index(self.dates.astype(str))
        non_event = ~self.qraw[0.30]
        rows = []
        for i, ev in enumerate(events.itertuples(index=False)):
            n, d = tick.get_loc(ev.ticker), day.get_loc(ev.date)
            pool, level = self._pool(n, d, self.elig[period], non_event)
            rng = np.random.default_rng(SEED + i)
            chosen = rng.choice(pool, size=min(N_CONTROLS, len(pool)), replace=False)
            for c in sorted(chosen, key=lambda c: str(self.m.tickers[c])):
                rows.append({"event_index": i, "event_ticker": ev.ticker, "match_relaxed_steps": level,
                             "pool_size": len(pool), **self.row(c, d)})
        return pd.DataFrame(rows)

    def signal_stats(self, events: pd.DataFrame, ctrls: pd.DataFrame, label_: str) -> pd.DataFrame:
        rng = np.random.default_rng(SEED)
        out = []
        for k in CONTINUOUS + BINARY:
            ev = events[k].to_numpy(float)
            scores = np.zeros(len(events))
            counts = np.zeros(len(events))
            for i, grp in ctrls.groupby("event_index"):
                xs = grp[k].to_numpy(float)
                xs = xs[np.isfinite(xs)]
                if not np.isfinite(ev[i]) or not len(xs):
                    continue
                scores[i] = (ev[i] > xs).sum() + 0.5 * (ev[i] == xs).sum()
                counts[i] = len(xs)
            used = counts > 0
            auc = scores[used].sum() / counts[used].sum() if used.any() else float("nan")
            idx = np.flatnonzero(used)
            boots = []
            for _ in range(N_BOOT):
                b = rng.choice(idx, size=len(idx), replace=True) if len(idx) else idx
                boots.append(scores[b].sum() / counts[b].sum() if len(b) else np.nan)
            cv = ctrls[k].to_numpy(float)
            out.append({
                "sample": label_, "signal": k, "kind": "binary" if k in BINARY else "continuous",
                "events_with_value": int(np.isfinite(ev).sum()), "controls_with_value": int(np.isfinite(cv).sum()),
                "event_median": float(np.nanmedian(ev)) if np.isfinite(ev).any() else None,
                "control_median": float(np.nanmedian(cv)) if np.isfinite(cv).any() else None,
                "event_mean": float(np.nanmean(ev)) if np.isfinite(ev).any() else None,
                "control_mean": float(np.nanmean(cv)) if np.isfinite(cv).any() else None,
                "auc": float(auc), "auc_lo95": float(np.nanpercentile(boots, 2.5)),
                "auc_hi95": float(np.nanpercentile(boots, 97.5)),
            })
        return pd.DataFrame(out)

    def detector_table(self, period: str) -> pd.DataFrame:
        e = self.elig[period]
        n_all = int(e.sum())
        base = {x: (e & self.qraw[x]).sum() / n_all for x in THRESHOLDS}
        rows = []
        for name, desc in family.FAMILY:
            sel = e & self.flags[name]
            n = int(sel.sum())
            row = {"period": period, "rule": name, "description": desc, "flags": n,
                   "flags_per_session": n / max(1, int(e.any(axis=0).sum()))}
            for x in THRESHOLDS:
                k = int((sel & self.qraw[x]).sum())
                lo, hi = wilson(k, n)
                row.update({f"{label(x)}_hits": k, f"{label(x)}_precision": k / n if n else float("nan"),
                            f"{label(x)}_precision_lo95": lo, f"{label(x)}_base": base[x],
                            f"{label(x)}_lift": (k / n) / base[x] if n and base[x] else float("nan")})
            row["admissible"] = bool(n >= 200 and row["E30_precision_lo95"] > base[0.30])
            rows.append(row)
        return pd.DataFrame(rows)

    @staticmethod
    def select(table: pd.DataFrame) -> str | None:
        adm = table[table["admissible"]]
        if adm.empty:
            return None
        return str(adm.sort_values(["E30_lift", "flags"], ascending=[False, False]).iloc[0]["rule"])

    # ------------------------------------------------------------------ validation
    def evaluate(self, rule: str, period: str) -> dict:
        e = self.elig[period]
        flag = e & self.flags[rule]
        n_idx, d_idx = np.nonzero(flag)
        n_all = int(e.sum())
        out = {"rule": rule, "period": period, "eligible_ticker_days": n_all, "flags": int(len(n_idx)),
               "sessions": int(e.any(axis=0).sum()), "sessions_with_flag": int(flag.any(axis=0).sum())}
        # matched random controls: same session, same bucket, 200 draws per flag
        draws = np.empty((N_RANDOM, len(n_idx)), dtype=np.int64)
        relaxed = np.zeros(len(n_idx), dtype=np.int64)
        rng = np.random.default_rng(SEED)
        for j, (n, d) in enumerate(zip(n_idx, d_idx)):
            pool, level = self._pool(n, d, e)
            relaxed[j] = level
            draws[:, j] = rng.choice(pool, size=N_RANDOM, replace=True)
        for x in THRESHOLDS:
            hit = self.qraw[x][n_idx, d_idx]
            k = int(hit.sum())
            lo, hi = wilson(k, len(n_idx))
            base = (e & self.qraw[x]).sum() / n_all
            rand = self.qraw[x][draws, d_idx[None, :]].mean(axis=1) if len(n_idx) else np.array([np.nan])
            out[label(x)] = {
                "hits": k, "precision": k / len(n_idx) if len(n_idx) else None, "precision_lo95": lo,
                "precision_hi95": hi, "base_rate": float(base), "lift_vs_base": (k / len(n_idx)) / base if len(n_idx) else None,
                "matched_random_mean": float(np.mean(rand)), "matched_random_p2_5": float(np.percentile(rand, 2.5)),
                "matched_random_p97_5": float(np.percentile(rand, 97.5)),
                "lift_vs_matched_random": (k / len(n_idx)) / float(np.mean(rand)) if len(n_idx) and np.mean(rand) else None,
                "p_one_sided_vs_matched": float((1 + (rand >= k / max(1, len(n_idx))).sum()) / (1 + len(rand))),
                "recall": self._recall(flag, x, period),
            }
        out["matched_random_relaxed_steps"] = {int(v): int((relaxed == v).sum()) for v in np.unique(relaxed)}
        out["false_alerts_no_E30"] = int(len(n_idx) - self.qraw[0.30][n_idx, d_idx].sum())
        ex = self.executable[n_idx, d_idx]
        out["executable_share"] = float(ex.mean()) if len(ex) else None
        cap = self.capturable[n_idx, d_idx]
        rand_cap = self.capturable[draws, d_idx[None, :]]
        out["capturable_median"] = float(np.nanmedian(cap)) if np.isfinite(cap).any() else None
        out["capturable_ge_30_share_of_executable"] = float((cap[np.isfinite(cap)] >= 0.30).mean()) if np.isfinite(cap).any() else None
        out["matched_random_capturable_median"] = float(np.nanmedian(rand_cap)) if np.isfinite(rand_cap).any() else None
        out["r5_median"] = float(np.nanmedian(self.r5[n_idx, d_idx])) if len(n_idx) else None
        out["matched_random_r5_median"] = float(np.nanmedian(self.r5[draws, d_idx[None, :]])) if len(n_idx) else None
        self.last_flags = pd.DataFrame([self.row(n, d) for n, d in zip(n_idx, d_idx)])
        return out

    def _recall(self, flag: np.ndarray, x: float, period: str) -> dict:
        n_idx, d_idx = np.nonzero(self.elig[period] & self.start[x])
        caught, leads, on_start = 0, [], 0
        for n, d in zip(n_idx, d_idx):
            peak = d + int(self.peak_k[n, d])
            u = d
            first = None
            while u < peak and u < flag.shape[1]:
                if flag[n, u] and self.qraw[x][n, u]:
                    first = u
                    break
                u += 1
            if first is not None:
                caught += 1
                leads.append(peak - first)
                on_start += first == d
        total = len(n_idx)
        return {"episodes": int(total), "caught_before_repricing": int(caught),
                "recall": caught / total if total else None, "flagged_on_episode_start": int(on_start),
                "median_lead_sessions_to_peak": float(np.median(leads)) if leads else None}


def write_json(path: Path, obj) -> None:
    with path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=2, sort_keys=True, default=float) + "\n")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    with path.open("x", encoding="utf-8", newline="") as fh:
        df.to_csv(fh, index=False, float_format="%.6g", lineterminator="\n")


def run_discovery(study: Study, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    rates = study.base_rates("discovery")
    write_csv(out / "base_rates.csv", rates)
    episodes = {x: study.episodes("discovery", x) for x in THRESHOLDS}
    for x, df in episodes.items():
        write_csv(out / f"episodes_{label(x)}.csv", df)
    first = episodes[0.30].head(N_FIRST).reset_index(drop=True)
    write_csv(out / "first100_events.csv", first)
    first_ctrl = study.matched_controls(first, "discovery")
    write_csv(out / "first100_controls.csv", first_ctrl)
    all_ctrl = study.matched_controls(episodes[0.30], "discovery")
    write_csv(out / "all_E30_controls.csv", all_ctrl)
    stats = pd.concat([study.signal_stats(first, first_ctrl, "first100"),
                       study.signal_stats(episodes[0.30], all_ctrl, "all_discovery_E30")], ignore_index=True)
    write_csv(out / "signal_stats.csv", stats)
    table = study.detector_table("discovery")
    write_csv(out / "detector_selection.csv", table)
    chosen = study.select(table)
    summary = {
        "protocol_id": "KOD-IDX-E1-v1", "protocol_sha256": study.protocol_sha, "panel_sha256": study.panel_sha,
        "stage": "discovery", "computed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "eligible_ticker_days": int(study.elig["discovery"].sum()),
        "episodes": {label(x): int(len(df)) for x, df in episodes.items()},
        "first100_span": [first["date"].iloc[0], first["date"].iloc[-1]] if len(first) else None,
        "selected_detector": chosen,
        "code": code_state(),
        "holdout": "sealed: the study market ends at the last validation session",
    }
    write_json(out / "summary.json", summary)
    return summary


def run_validation(study: Study, rule: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    rates = study.base_rates("validation")
    write_csv(out / "base_rates.csv", rates)
    for x in THRESHOLDS:
        write_csv(out / f"episodes_{label(x)}.csv", study.episodes("validation", x))
    result = study.evaluate(rule, "validation")
    write_csv(out / "flags.csv", study.last_flags)
    result.update({"protocol_sha256": study.protocol_sha, "panel_sha256": study.panel_sha, "stage": "validation",
                   "code": code_state(),
                   "detector_module_sha256": sha256_file(Path(family.__file__)),
                   "computed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})
    write_json(out / "result.json", result)
    return result
