"""Grade a pasted chart idea (a TradingView call, a tip) against luck, honestly.

An idea is translated by hand into a small declarative spec (never code: no user string is evaluated), for example
    {"name": "BBCA RSI dip", "market": "IDX", "ticker": "BBCA", "side": "long",
     "entry": {"type": "rsi_below", "n": 14, "level": 30}, "exit": {"tp": 0.10, "sl": 0.05, "max_hold": 20}}
and graded three ways on KOD's own daily panels, sealed holdouts never loaded:

1. Against random entries: the same exit rule from as many random days, 2,000 times (does the signal beat the geometry?).
2. Against the search: the idea and its neighbours (every entry type and parameter on a frozen grid, three holds) as a
   family, Hansen's test of superior predictive ability (SPA, consistent version) with a stationary bootstrap: is the
   best of the family better than staying flat after accounting for how many rules a chartist could have tried?
3. Out of sample: the idea itself on a later segment it was not chosen on.

Verdicts: SURVIVES (SPA p <= 0.05 and the later segment's mean trade > 0 with random-entry p <= 0.10), IN-SAMPLE ONLY
(the first but not the second), NOT DISTINGUISHABLE FROM LUCK (otherwise). Paper only; a verdict is not a trade.
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .provenance import MANIFESTS

PANELS = {
    "IDX": "panel-20261007T225823Z.json",
    "US": "panel_us_repair-20261008T114805Z.json",
    "CRYPTO": "panel_crypto-20261008T003354Z.json",
}
SEALED = {
    "IDX": ("2024-01-02", "2025-02-21"),
    "US": ("2024-01-01", "2099-12-31"),
    "CRYPTO": ("2024-01-01", "2099-12-31"),
}
COST = {"IDX": 0.004, "US": 0.002, "CRYPTO": 0.004}  # round trip, as a fraction of the entry price
TYPES = {
    "rsi_below": [
        {"n": n, "level": lv} for n, lv in itertools.product((7, 14, 21), (20, 25, 30, 35, 40))
    ],
    "stoch_below": [
        {"n": n, "level": lv} for n, lv in itertools.product((9, 14, 21), (10, 20, 30))
    ],
    "bb_below": [{"n": n, "k": k} for n, k in itertools.product((10, 20, 50), (1.5, 2.0, 2.5))],
    "ma_cross_up": [
        {"fast": f, "slow": s}
        for f, s in itertools.product((5, 10, 20, 50), (20, 50, 100, 200))
        if f < s
    ],
    "breakout": [{"n": n} for n in (10, 20, 50, 100)],
    "macd_cross_up": [
        {"a": a, "b": b, "c": c} for a, b, c in ((12, 26, 9), (5, 35, 5), (8, 17, 9))
    ],
}
HOLDS = (5, 10, 20)
B, BLOCK, SEED = 1000, 10, 20261029


@dataclass
class Series:
    dates: np.ndarray
    level: np.ndarray  # the reference chain: cumulative close over the exchange's previous close


def load(market: str, ticker: str) -> Series:
    from . import global_panel, panel

    path = MANIFESTS / PANELS[market]
    df = panel.load(path)[0] if market == "IDX" else global_panel.load(path)[0]
    s = df[df["ticker"] == ticker].sort_values("date")
    if s.empty:
        raise ValueError(f"{ticker} is not in the {market} panel")
    d = pd.to_datetime(s["date"]).dt.strftime("%Y-%m-%d").to_numpy()
    lo, hi = SEALED[market]
    keep = (d < lo) | (d > hi)
    c, p = s["close"].to_numpy(float), s["previous"].to_numpy(float)
    r = np.where((p > 0) & (c > 0), np.log(np.where(p > 0, c / p, 1.0)), 0.0)
    return Series(d[keep], np.exp(np.cumsum(r[keep])))


def _rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up, dn = (
        d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(),
        (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(),
    )
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def signals(level: np.ndarray, entry: dict) -> np.ndarray:
    """Boolean array: the entry condition first becomes true at this close."""
    c, t = pd.Series(level), entry["type"]
    if t == "rsi_below":
        x = _rsi(c, entry["n"])
        cond = x < entry["level"]
    elif t == "stoch_below":
        lo, hi = c.rolling(entry["n"]).min(), c.rolling(entry["n"]).max()
        x = 100 * (c - lo) / (hi - lo).replace(0, np.nan)
        cond = x < entry["level"]
    elif t == "bb_below":
        ma, sd = c.rolling(entry["n"]).mean(), c.rolling(entry["n"]).std()
        cond = c < ma - entry["k"] * sd
    elif t == "ma_cross_up":
        cond = c.rolling(entry["fast"]).mean() > c.rolling(entry["slow"]).mean()
    elif t == "breakout":
        cond = c > c.shift(1).rolling(entry["n"]).max()
    elif t == "macd_cross_up":
        m = (
            c.ewm(span=entry["a"], adjust=False).mean()
            - c.ewm(span=entry["b"], adjust=False).mean()
        )
        cond = m > m.ewm(span=entry["c"], adjust=False).mean()
    else:
        raise ValueError(f"unknown entry type {t!r}; known: {sorted(TYPES)}")
    cond = cond.fillna(False).to_numpy(bool)
    return cond & ~np.r_[False, cond[:-1]]


def exit_index(level: np.ndarray, i: int, ex: dict) -> int | None:
    """Close at which a trade entered at close i is closed; None when the data end first."""
    if "hold" in ex:
        j = i + int(ex["hold"])
        return j if j < len(level) else None
    end = min(len(level) - 1, i + int(ex.get("max_hold", 20)))
    for j in range(i + 1, end + 1):
        r = level[j] / level[i] - 1
        if r >= ex["tp"] or r <= -ex["sl"]:
            return j
    return end if i + int(ex.get("max_hold", 20)) < len(level) else None


def trades(level: np.ndarray, sig: np.ndarray, ex: dict, side: int) -> list[tuple[int, int]]:
    out, i = [], 0
    idx = np.flatnonzero(sig)
    for s in idx:
        e = s + 1  # signal at a close, entry at the next close
        if e <= i or e >= len(level):
            continue
        j = exit_index(level, e, ex)
        if j is None:
            break
        out.append((e, j))
        i = j
    return out


def trade_returns(level, tr, side, cost):
    return np.array([side * (level[j] / level[e] - 1) - cost for e, j in tr])


def daily(level: np.ndarray, tr: list[tuple[int, int]], side: int, cost: float) -> np.ndarray:
    lr = np.r_[0.0, np.diff(np.log(level))]
    pos = np.zeros(len(level))
    out = np.zeros(len(level))
    for e, j in tr:
        pos[e + 1 : j + 1] = side
        out[e] -= cost / 2
        out[j] -= cost / 2
    return out + pos * lr


def stationary_indices(n: int, rng: np.random.Generator) -> np.ndarray:
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(n)
    for t in range(1, n):
        idx[t] = rng.integers(n) if rng.random() < 1 / BLOCK else (idx[t - 1] + 1) % n
    return idx


def spa(d: np.ndarray, seed: int = SEED) -> dict:
    """Hansen (2005) SPA test, consistent version, against a zero benchmark; d is T x K daily excess returns."""
    n, k = d.shape
    rng = np.random.default_rng(seed)
    mean = d.mean(0)
    boots = np.array([d[stationary_indices(n, rng)].mean(0) for _ in range(B)])
    omega = np.sqrt(n * boots.var(0))
    omega = np.where(omega > 0, omega, np.inf)
    t = np.sqrt(n) * mean / omega
    stat = max(float(t.max()), 0.0)
    mu = np.where(t >= -math.sqrt(2 * math.log(math.log(n))), mean, 0.0)
    tb = np.maximum((np.sqrt(n) * (boots - mu) / omega).max(1), 0.0)
    return {"stat": stat, "p": float((tb >= stat).mean()), "best": int(np.argmax(t)), "members": k}


def family(spec: dict) -> list[dict]:
    fam = [{"entry": spec["entry"], "exit": spec["exit"]}]
    for t, grid in TYPES.items():
        for g in grid:
            for h in HOLDS:
                fam.append({"entry": {"type": t, **g}, "exit": {"hold": h}})
    return fam


def placebo(level, n_trades, ex, side, cost, lo, hi, rng, draws=2000):
    """Mean trade return of n random entries inside [lo, hi), the same exit rule, non-overlap not imposed."""
    if n_trades == 0:
        return np.array([])
    starts = np.arange(lo, hi)
    out = np.empty(draws)
    for b in range(draws):
        rs = []
        for e in rng.choice(starts, n_trades, replace=True):
            j = exit_index(level, int(e), ex)
            if j is not None:
                rs.append(side * (level[j] / level[e] - 1) - cost)
        out[b] = np.mean(rs) if rs else np.nan
    return out


def grade(spec: dict, series: Series | None = None) -> dict:
    market, side = spec["market"].upper(), (1 if spec.get("side", "long") == "long" else -1)
    s = series or load(market, spec["ticker"])
    cost = COST[market]
    if market == "IDX":
        cut = int(
            np.searchsorted(s.dates, SEALED["IDX"][0])
        )  # in sample: before the sealed window; later: after it
    else:
        cut = int(len(s.dates) * 0.7)
    lv_in, lv_out = s.level[:cut], s.level[cut:]
    rng = np.random.default_rng(SEED)
    fam = family(spec)
    d = np.column_stack(
        [
            daily(lv_in, trades(lv_in, signals(lv_in, f["entry"]), f["exit"], side), side, cost)
            for f in fam
        ]
    )
    test = (
        spa(d[1:])
        if len(d) > 50
        else {"p": float("nan"), "stat": float("nan"), "best": 0, "members": len(fam)}
    )
    out = {
        "spec": spec,
        "dates": {
            "in_sample": [s.dates[0], s.dates[cut - 1]],
            "later": ([s.dates[cut], s.dates[-1]] if cut < len(s.dates) else None),
        },
        "family_size": len(fam),
        "spa": test,
        "best_of_family": fam[test["best"]],
    }
    for name, lv in (("in_sample", lv_in), ("later", lv_out)):
        if len(lv) < 60:
            out[name] = None
            continue
        tr = trades(lv, signals(lv, spec["entry"]), spec["exit"], side)
        rr = trade_returns(lv, tr, side, cost)
        pl = placebo(lv, len(tr), spec["exit"], side, cost, 30, len(lv) - 1, rng)
        out[name] = {
            "trades": len(tr),
            "win_rate": (float((rr > 0).mean()) if len(rr) else None),
            "mean": (float(rr.mean()) if len(rr) else None),
            "median": (float(np.median(rr)) if len(rr) else None),
            "random_mean": (float(np.nanmean(pl)) if len(pl) else None),
            "p_vs_random": (
                float((np.sum(pl >= rr.mean()) + 1) / (len(pl) + 1)) if len(rr) else None
            ),
        }
    later = out.get("later")
    ok_later = bool(
        later and later["trades"] and later["mean"] > 0 and later["p_vs_random"] <= 0.10
    )
    out["verdict"] = (
        "SURVIVES"
        if test["p"] <= 0.05 and ok_later
        else "IN-SAMPLE ONLY"
        if test["p"] <= 0.05
        else "NOT DISTINGUISHABLE FROM LUCK"
    )
    return out


def words(g: dict) -> str:
    sp, a, b = g["spec"], g.get("in_sample"), g.get("later")

    def seg(x, label):
        if not x or not x["trades"]:
            return f"- {label}: no trades."
        return (
            f"- {label}: {x['trades']} trades, won {x['win_rate']:.0%}, mean {x['mean']:+.2%} after costs "
            f"(random entries with the same exit: {x['random_mean']:+.2%}; p {x['p_vs_random']:.3f})."
        )

    return "\n".join(
        [
            f"**{sp.get('name', sp['ticker'])}** ({sp['market']} {sp['ticker']}, {sp.get('side', 'long')}): **{g['verdict']}**",
            seg(a, f"Chosen-on period {g['dates']['in_sample'][0]}..{g['dates']['in_sample'][1]}"),
            seg(
                b,
                "Later period"
                + (
                    f" {g['dates']['later'][0]}..{g['dates']['later'][1]}"
                    if g["dates"]["later"]
                    else ""
                ),
            ),
            f"- Against the search: {g['family_size']} near-identical rules; the best is "
            f"{json.dumps(g['best_of_family'])}; SPA p {g['spa']['p']:.3f} (above 0.05 = the best looks like what searching "
            "that many rules produces from noise).",
            "- Paper only. Sealed holdouts were not loaded.",
        ]
    )


def grade_file(path: Path) -> str:
    spec = json.loads(Path(path).read_text())
    specs = spec if isinstance(spec, list) else [spec]
    return "\n\n".join(words(grade(s)) for s in specs)
