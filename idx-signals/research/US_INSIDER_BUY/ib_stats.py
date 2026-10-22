"""US_INSIDER_BUY: the statistics, gates and reading rules of PROTOCOL.md as pure functions (tested in tests/test_us_insider_buy.py). Imported by run.py."""
import numpy as np
import pandas as pd

HURDLE_T, MIN_EXCESS, MIN_EXCESS_WINS, MIN_PER_YEAR = 3.0, 0.02, 0.01, 300          # Stage 1
HURDLE_T2, MIN_EXCESS2 = 1.65, 0.01                                                   # Stage 2
GO_MIN, GO_MIN_PER_YEAR = 1500, 300


class Boot:
    """Week-cluster bootstrap: one fixed set of resampled weeks serves every statistic (same construction as SLOW_10K's)."""

    def __init__(self, weeks, resamples: int = 10_000, seed: int = 20261203):
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


def week_id(entry_date: pd.Series) -> np.ndarray:
    iso = pd.to_datetime(entry_date).dt.isocalendar()
    return (iso.year.astype(int) * 100 + iso.week.astype(int)).to_numpy()


def winsor_mean(x, lo: float = 1, hi: float = 99) -> float:
    a = np.asarray(x, float)
    l, h = np.percentile(a, [lo, hi])
    return float(np.clip(a, l, h).mean())


def scored(res: pd.DataFrame) -> pd.DataFrame:
    """The events with a net return, a control and an excess."""
    return res[res["net_return"].notna() & res["control_mean"].notna()]


def go_check(f: pd.DataFrame) -> tuple[bool, dict]:
    """The Stage 1 GO rule on the scored events of hold 60 (counts only)."""
    per_year = {y: int((f["entry_date"].str[:4] == y).sum()) for y in ("2021", "2022")}
    ok = len(f) >= GO_MIN and all(v >= GO_MIN_PER_YEAR for v in per_year.values())
    return bool(ok), {"scored": int(len(f)), "per_year": per_year, "need_total": GO_MIN, "need_per_year": GO_MIN_PER_YEAR}


def stage1_gates(f: pd.DataFrame, stats: dict, other_hold_means: dict) -> tuple[dict, dict]:
    """`f` the scored events of hold 60, `stats` their Boot.mean of the excess, `other_hold_means` the mean excess at holds 20 and 120."""
    yr = {}
    for y in ("2021", "2022"):
        g = f[f["entry_date"].str[:4] == y]
        yr[y] = {"n": int(len(g)), "mean_excess": float(g["excess"].mean()) if len(g) else None}
    ok_years = all(v["n"] >= MIN_PER_YEAR and v["mean_excess"] is not None and v["mean_excess"] > 0 for v in yr.values())
    gates = {"G1_excess_t_ge_3": bool(stats["mean"] > 0 and stats["t"] >= HURDLE_T),
             "G2_excess_ge_2pct_and_winsorised_ge_1pct": bool(stats["mean"] >= MIN_EXCESS and winsor_mean(f["excess"]) >= MIN_EXCESS_WINS),
             "G3_excess_gt_0_in_2021_and_2022": bool(ok_years),
             "G4_excess_gt_0_at_holds_20_and_120": bool(len(other_hold_means) == 2 and all(m is not None and m > 0 for m in other_hold_means.values()))}
    return gates, yr


def stage1_reading(gates: dict, stats: dict) -> str:
    if all(gates.values()):
        return "STAGE1_PASS: run stage 2"
    if gates["G1_excess_t_ge_3"]:
        return "REAL_BUT_SMALL_OR_UNSTABLE: no stage 2"
    if stats["mean"] > 0 and stats["t"] >= 1.5:
        return "LEAN_WITHOUT_SIZE: no stage 2"
    return "NO_LARGE_EFFECT: no stage 2"


def stage2_gates(stats: dict) -> dict:
    return {"G1p_excess_t_ge_1.65": bool(stats["mean"] > 0 and stats["t"] >= HURDLE_T2), "G2p_excess_ge_1pct": bool(stats["mean"] >= MIN_EXCESS2)}


def stage2_reading(gates: dict) -> str:
    return "LARGE_PERSISTENT_EFFECT" if all(gates.values()) else "DID_NOT_PERSIST"
