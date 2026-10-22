"""SLOW_10K: the statistics, gates and reading rules of PROTOCOL.md as pure functions (tested in tests/test_slow_10k.py). Imported by run.py."""
import numpy as np
import pandas as pd

HURDLE_T, MIN_SPREAD, MIN_PER_YEAR, SHUFFLES, SHUFFLE_T = 3.0, 0.03, 200, 20, 3.0       # Stage 1
HURDLE_T2, MIN_SPREAD2 = 1.65, 0.015                                                       # Stage 2
GO_MIN_PER_BUCKET = 1000


class Boot:
    """Week-cluster bootstrap: one fixed set of resampled weeks serves every statistic, so a difference between buckets sees the same weeks."""

    def __init__(self, weeks, resamples: int = 10_000, seed: int = 20261201):
        self.weeks = np.array(sorted({int(w) for w in weeks}))
        self.pick = np.random.default_rng(seed).integers(0, len(self.weeks), size=(resamples, len(self.weeks)))

    def _means(self, v, w) -> np.ndarray:
        w = np.asarray(w, dtype=np.int64)
        i = np.searchsorted(self.weeks, w)
        if len(w) and not (self.weeks[np.minimum(i, len(self.weeks) - 1)] == w).all():
            raise ValueError("a week outside the bootstrap's week set")
        n = len(self.weeks)
        s, c = np.bincount(i, np.asarray(v, float), minlength=n), np.bincount(i, minlength=n).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            return s[self.pick].sum(1) / c[self.pick].sum(1)

    def mean(self, v, w) -> dict:
        v = np.asarray(v, float)
        st = self._means(v, w)
        st = st[np.isfinite(st)]
        se = float(st.std(ddof=1))
        return {"n": int(len(v)), "mean": float(v.mean()), "se": se, "t": float(v.mean() / se) if se > 0 else float("nan"),
                "lo95": float(np.percentile(st, 2.5)), "hi95": float(np.percentile(st, 97.5))}

    def spread(self, v5, w5, v1, w1) -> dict:
        v5, v1 = np.asarray(v5, float), np.asarray(v1, float)
        st = self._means(v5, w5) - self._means(v1, w1)
        st = st[np.isfinite(st)]
        sp, se = float(v5.mean() - v1.mean()), float(st.std(ddof=1))
        return {"n5": int(len(v5)), "n1": int(len(v1)), "spread": sp, "se": se, "t": sp / se if se > 0 else float("nan"),
                "lo95": float(np.percentile(st, 2.5)), "hi95": float(np.percentile(st, 97.5))}


def week_id(entry_date: pd.Series) -> np.ndarray:
    iso = pd.to_datetime(entry_date).dt.isocalendar()
    return (iso.year.astype(int) * 100 + iso.week.astype(int)).to_numpy()


def scored_sets(f: pd.DataFrame):
    """(Q5, Q1) rows of the scored events: net return, control and excess exist."""
    f = f[f.net_return.notna() & f.control_mean.notna()]
    return f[f.bucket == "Q5"], f[f.bucket == "Q1"]


def shuffle_check(f: pd.DataFrame, boot: Boot, k: int = SHUFFLES, seed: int = 20261202) -> list[float]:
    """t of the Q5 - Q1 spread when the Q1/Q5 labels are permuted within each filing month (counts per month kept): a method check."""
    q5, q1 = scored_sets(f)
    both = pd.concat([q5, q1]).reset_index(drop=True)
    month = both.public_date.str[:7].to_numpy()
    is5 = (both.bucket == "Q5").to_numpy()
    w, ex = week_id(both.entry_date), both.excess.to_numpy()
    out = []
    for j in range(k):
        rng = np.random.default_rng(seed + j)
        lab = is5.copy()
        for m in np.unique(month):
            idx = np.flatnonzero(month == m)
            lab[idx] = rng.permutation(is5[idx])
        out.append(boot.spread(ex[lab], w[lab], ex[~lab], w[~lab])["t"])
    return out


def stage1_gates(f: pd.DataFrame, spread: dict, shuffle_ts: list[float]) -> tuple[dict, dict]:
    q5, q1 = scored_sets(f)
    yr = {}
    for y in ("2021", "2022"):
        a, b = q5[q5.entry_date.str[:4] == y], q1[q1.entry_date.str[:4] == y]
        yr[y] = {"n5": int(len(a)), "n1": int(len(b)), "spread": float(a.excess.mean() - b.excess.mean()) if len(a) and len(b) else None}
    ok_years = all(v["n5"] >= MIN_PER_YEAR and v["n1"] >= MIN_PER_YEAR and v["spread"] is not None and v["spread"] > 0 for v in yr.values())
    gates = {"G1_spread_t_ge_3": bool(spread["spread"] > 0 and spread["t"] >= HURDLE_T), "G2_spread_ge_3pct": bool(spread["spread"] >= MIN_SPREAD),
             "G3_spread_gt_0_in_2021_and_2022": bool(ok_years), "G4_shuffled_labels_all_abs_t_lt_3": bool(max(abs(t) for t in shuffle_ts) < SHUFFLE_T)}
    return gates, yr


def stage1_reading(gates: dict, spread: dict) -> str:
    if all(gates.values()):
        return "STAGE1_PASS: run stage 2"
    if spread["spread"] > 0 and spread["t"] >= 1.5:
        return "LEAN_WITHOUT_SIZE: no stage 2"
    return "NO_LARGE_EFFECT: no stage 2"


def stage2_gates(spread: dict) -> dict:
    return {"G1p_spread_t_ge_1.65": bool(spread["spread"] > 0 and spread["t"] >= HURDLE_T2), "G2p_spread_ge_1.5pct": bool(spread["spread"] >= MIN_SPREAD2)}


def stage2_reading(gates: dict) -> str:
    return "LARGE_PERSISTENT_EFFECT" if all(gates.values()) else "DID_NOT_PERSIST"
