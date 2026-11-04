"""LIQ_REBOUND_v1: buy BTC/ETH spot after a forced-deleveraging cascade, hold 72 hours, cash otherwise.

Hypothesis (PROTOCOL.md): when a sharp spot fall coincides with an extreme fall in perpetual-futures open interest
(coin units, i.e. leveraged positions forcibly closed), the forced sellers pay a price concession that partly reverses;
a patient, unleveraged spot buyer who supplies liquidity is paid for it.

    python3 research/LIQ_REBOUND_v1/rebound.py --feasibility   # event counts only, no forward price is read
    python3 research/LIQ_REBOUND_v1/rebound.py --freeze        # writes protocol.json (refuses if it exists)
    python3 research/LIQ_REBOUND_v1/rebound.py --run           # the one run (refuses if run/ exists)

Timing (all UTC). Bar t is the Binance spot 1h kline opening at t; it closes at T = t + 1h. The signal at T uses
spot closes up to T and open-interest rows stamped <= T - 5 min (a publication-lag allowance). The order is a market
buy at the open of the bar starting T + entry_lag (1h base): never at the signal price. The exit is a market sell at
the open of the bar 72 bars after the entry bar. A catastrophic stop at -20% exits at the LOW of the first bar whose
low reaches it (the worst price in that hour; a touched level is never assumed to be the fill).
"""

from __future__ import annotations

import argparse
import io
import itertools
import json
import math
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import sha256_file, utc_stamp

RAW = ROOT / "data/raw"
METRICS_MANIFEST = ROOT / "data/manifests/liq_rebound-20261031T223330Z.jsonl"
SPOT_MANIFEST = ROOT / "data/manifests/binance_1h-20261015T182940Z.jsonl"
PROTO, RUN, FEAS = HERE / "protocol.json", HERE / "run", HERE / "FEASIBILITY.json"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
DATA_FIRST, DATA_LAST = (
    pd.Timestamp("2020-04-01 00:00"),
    pd.Timestamp("2023-12-31 23:00"),
)  # bar opens
DISCOVERY = (pd.Timestamp("2020-09-01 00:00"), pd.Timestamp("2022-12-31 23:00"))  # signal-bar opens
SCREEN = (pd.Timestamp("2023-01-01 00:00"), pd.Timestamp("2023-12-31 23:00"))
K_CANDIDATES = (
    3.0,
    2.5,
    2.0,
)  # feasibility only: the largest k with >= 30 signals and >= 8 episodes is frozen


@dataclass(frozen=True)
class Config:
    window_h: int = 24  # price and OI change window
    sigma_k: float = 3.0  # price leg: 24h log return <= -k * trailing sigma (set from FEASIBILITY.json at freeze)
    sigma_bars: int = 720  # 30 days of hourly 24h-returns, ending 24h before the signal
    sigma_min: int = 576
    oi_lag_min: int = 5
    oi_tol_min: int = 15
    oi_q: float = 0.05  # OI leg: 24h coin-unit OI change <= trailing 5th percentile
    oi_bars: int = 4320  # 180 days, ending 24h before the signal
    oi_min: int = 2160  # at least 90 days of history
    entry_lag_h: int = 1
    hold_h: int = 72
    stop: float = 0.20
    size: float = 0.5  # of equity at the decision, capped by free cash; one position per coin, so <= 100% invested
    start_cash: float = 10_000.0
    min_order: float = 10.0
    episode_gap_days: int = 7


COSTS = {  # (buy, sell) per side, fraction of notional: fee + spread/slippage + tax (PROTOCOL.md section 6)
    "A1": (0.0016, 0.0037),  # licensed Indonesian IDR exchange, maker orders
    "A2": (0.0031, 0.0052),  # same venues, market orders: the base case
    "A3": (0.0115, 0.0215),  # eToro real crypto, Bronze-Gold, foreign-platform tax: reported only
    "S2": (0.0041, 0.0062),  # A2 with doubled spread/slippage: stress
}
BOOT = {"draws": 2000, "seed": 20261031}
PLACEBO = {"draws": 2000, "seed": 20261101}
MISSED = {"draws": 500, "seed": 20261102, "p_fail": 0.3}


# ------------------------------------------------------------------------------------------------------------ data
def load_spot(sym: str) -> pd.DataFrame:
    rows = []
    for line in SPOT_MANIFEST.read_text().splitlines()[1:]:
        r = json.loads(line)
        if r.get("symbol") != sym:
            continue
        if r["month"] > "2023-12":
            raise RuntimeError("a spot file after the development window")
        p = RAW / r["file"]
        if sha256_file(p) != r["sha256"]:
            raise RuntimeError(f"{p} differs from its manifest")
        with zipfile.ZipFile(p) as z:
            raw = z.read(z.namelist()[0])
        rows.append(pd.read_csv(io.BytesIO(raw), header=None, usecols=[0, 1, 2, 3, 4, 5, 8]))
    k = pd.concat(rows, ignore_index=True)
    k.columns = ["open_time", "open", "high", "low", "close", "volume", "trades"]
    k["t"] = pd.to_datetime(k.open_time, unit="ms")
    k = k.drop_duplicates("t", keep="last").set_index("t").sort_index()
    if k.index.max() > DATA_LAST:
        raise RuntimeError("a bar after the development window")
    k = halted_to_nan(k)
    full = pd.date_range(DATA_FIRST, DATA_LAST, freq="h")
    return k.reindex(full)[["open", "high", "low", "close", "volume"]].astype(float)


def halted_to_nan(k: pd.DataFrame) -> pd.DataFrame:
    """Exchange-halt placeholder klines (no trades or no volume) are not tradable: treated as missing bars."""
    k = k.copy()
    halted = (k.trades <= 0) | (k.volume <= 0)
    k.loc[halted, ["open", "high", "low", "close"]] = np.nan
    return k


def load_oi(sym: str) -> pd.Series:
    frames = []
    for line in METRICS_MANIFEST.read_text().splitlines()[1:]:
        r = json.loads(line)
        if r["symbol"] != sym or r["status"] != "ok":
            continue
        if r["day"] > "2023-12-31":
            raise RuntimeError("an OI file after the development window")
        p = RAW / r["file"]
        if sha256_file(p) != r["sha256"]:
            raise RuntimeError(f"{p} differs from its manifest")
        with zipfile.ZipFile(p) as z:
            frames.append(
                pd.read_csv(
                    io.BytesIO(z.read(z.namelist()[0])),
                    usecols=["create_time", "sum_open_interest"],
                )
            )
    m = pd.concat(frames, ignore_index=True)
    m["create_time"] = pd.to_datetime(m.create_time)
    m = m.dropna().drop_duplicates("create_time", keep="last").sort_values("create_time")
    if len(m) and m.create_time.max() >= pd.Timestamp("2024-01-01"):
        raise RuntimeError("an OI row after the development window")
    return clean_oi(m.set_index("create_time").sum_open_interest.astype(float))


def clean_oi(s: pd.Series) -> pd.Series:
    """Archive hygiene: 0 marks missing data, and a feed repeating one value for 3+ consecutive rows is frozen
    (only the first row of such a run is kept). Removed rows become gaps, so the 15-minute tolerance gives no signal."""
    s = s[s > 0]
    same = s.diff().eq(0)
    run = s.groupby((~same).cumsum()).transform("size")
    return s[~(same & (run >= 3))]


def legs(spot: pd.DataFrame, oi: pd.Series, cfg: Config) -> pd.DataFrame:
    """Signal legs at each bar's close, using only information available at that close."""
    w = cfg.window_h
    out = pd.DataFrame(index=spot.index)
    out["T"] = spot.index + pd.Timedelta(hours=1)
    out["lr"] = np.log(spot.close / spot.close.shift(w))
    out["sigma"] = out.lr.shift(w).rolling(cfg.sigma_bars, min_periods=cfg.sigma_min).std()
    o = pd.DataFrame(
        {"ct": pd.DatetimeIndex(oi.index).astype("datetime64[ns]"), "oi": oi.to_numpy(float)}
    )
    tol = pd.Timedelta(minutes=cfg.oi_tol_min)
    for col, back in (("oi_now", pd.Timedelta(0)), ("oi_prev", pd.Timedelta(hours=w))):
        at = (out["T"] - pd.Timedelta(minutes=cfg.oi_lag_min) - back).astype("datetime64[ns]")
        q = pd.DataFrame({"at": at}).reset_index()
        q = q.sort_values("at")
        j = pd.merge_asof(q, o, left_on="at", right_on="ct", direction="backward", tolerance=tol)
        out[col] = j.set_index("index").oi.reindex(out.index)
    out["doi"] = (out.oi_now / out.oi_prev - 1).where(lambda x: np.isfinite(x))
    out["q"] = out.doi.shift(w).rolling(cfg.oi_bars, min_periods=cfg.oi_min).quantile(cfg.oi_q)
    ok_p = out.lr.notna() & out.sigma.notna()
    ok_o = out.doi.notna() & out.q.notna()
    out["valid"] = ok_p & ok_o
    out["price_leg"] = ok_p & (out.lr <= -cfg.sigma_k * out.sigma)
    out["cascade"] = out.valid & out.price_leg & (out.doi <= out.q)
    out["droponly"] = out.valid & out.price_leg & (out.doi > out.q)
    # the G3 control, causal: drop-only hours with no cascade hour on the same coin in the preceding
    # 1 + entry lag + hold bars (so a cascade's own aftermath is never counted as a "drop without an OI collapse").
    # Earlier hours of a crash, before OI reaches its tail, stay in: that is what a buyer without the OI leg would buy.
    # Drop size is not matched; both sets meet the same price leg.
    span = 1 + cfg.entry_lag_h + cfg.hold_h
    near = out.cascade.astype(float).rolling(span + 1, min_periods=1).max().astype(bool)
    out["control"] = out.droponly & ~near
    return out


def load_all(cfg: Config) -> dict:
    data = {}
    for s in SYMBOLS:
        spot = load_spot(s)
        data[s] = {"spot": spot, "legs": legs(spot, load_oi(s), cfg)}
    return data


# ---------------------------------------------------------------------------------------------------------- trades
def simulate_trade(
    spot: pd.DataFrame, i: int, cost: tuple[float, float], cfg: Config
) -> dict | None:
    """One position from the signal bar index i (bar i closes at the signal time). None if the entry bar is missing
    or the scheduled exit falls outside the loaded data."""
    o, lo = spot.open.to_numpy(), spot.low.to_numpy()
    e = i + 1 + cfg.entry_lag_h
    target = e + cfg.hold_h
    if target >= len(o) or not np.isfinite(o[e]):
        return None
    px = o[e]
    stop_px = px * (1 - cfg.stop)
    j, exit_px, kind = e, None, None
    while j < len(o):
        if j >= target and np.isfinite(o[j]):
            exit_px, kind = o[j], ("TIME" if j == target else "TIME_ROLLED")
            break
        if np.isfinite(lo[j]) and lo[j] <= stop_px:
            exit_px, kind = lo[j], "STOP_AT_LOW"
            break
        j += 1
    if exit_px is None:
        return None
    cb, cs = cost
    return {
        "entry_i": e,
        "exit_i": j,
        "entry_px": float(px),
        "exit_px": float(exit_px),
        "exit_type": kind,
        "gross": float(exit_px / px - 1),
        "net": float((1 - cb) * (1 - cs) * exit_px / px - 1),
    }


def debounced(
    spot: pd.DataFrame, flags: np.ndarray, idx: np.ndarray, cost, cfg: Config
) -> list[dict]:
    """Trade-level list for a signal series (no account): one position at a time per coin, chronological."""
    out, busy_until = [], -1
    o = spot.open.to_numpy()
    for i in idx:
        if not flags[i] or i <= busy_until:
            continue
        e = i + 1 + cfg.entry_lag_h
        if e + cfg.hold_h >= len(o):
            continue
        if not np.isfinite(o[e]):  # as in the account: the order waits for its bar, then lapses
            busy_until = e - 1
            continue
        tr = simulate_trade(spot, int(i), cost, cfg)
        if tr is None:
            continue
        tr["signal_i"] = int(i)
        out.append(tr)
        busy_until = tr["exit_i"] - 1  # a new signal may form at the exit bar's close
    return out


def window_idx(spot: pd.DataFrame, window) -> np.ndarray:
    ix = spot.index
    return np.where((ix >= window[0]) & (ix <= window[1]))[0]


# --------------------------------------------------------------------------------------------------------- account
def run_account(
    data: dict,
    window,
    cost,
    cfg: Config,
    flag: str = "cascade",
    fail_rng=None,
    forced: dict | None = None,
) -> dict:
    """Shared-cash, long-only, unleveraged account over the decision window. Positions may run past the window's end
    (to their scheduled exit inside the loaded data). `forced` replaces the signal flags (placebo)."""
    syms = list(data)
    ix = data[syms[0]]["spot"].index
    O = {s: data[s]["spot"].open.to_numpy() for s in syms}
    L = {s: data[s]["spot"].low.to_numpy() for s in syms}
    C = {s: data[s]["spot"].close.to_numpy() for s in syms}
    F = {s: (forced[s] if forced else data[s]["legs"][flag].to_numpy()) for s in syms}
    first = int(np.searchsorted(ix, window[0]))
    last_dec = int(np.searchsorted(ix, window[1], side="right")) - 1
    cb, cs = cost
    cash, reserved = cfg.start_cash, 0.0
    pending, pos, trades, daily, events, blocked = {}, {}, [], [], [], {}
    last_close = {s: np.nan for s in syms}
    h = first
    end = len(ix) - 1
    while h <= end:
        for s in syms:
            if np.isfinite(C[s][h]):
                last_close[s] = C[s][h]
        # 1. fills at this bar's open
        for s in list(pending):
            p = pending[s]
            if p["entry_i"] != h:
                continue
            del pending[s]
            reserved -= p["N"]
            if fail_rng is not None and fail_rng.random() < MISSED["p_fail"]:
                # a missed fill is a missed trade: the coin stays out until the trade's scheduled exit
                events.append({"type": "MISSED_FILL", "symbol": s, "bar": str(ix[h])})
                blocked[s] = h + cfg.hold_h
                continue
            px = O[s][h]
            if not np.isfinite(px):
                events.append({"type": "ENTRY_BAR_MISSING", "symbol": s, "bar": str(ix[h])})
                continue
            cash -= p["N"]
            units = p["N"] * (1 - cb) / px
            pos[s] = {
                "units": units,
                "entry_i": h,
                "entry_px": px,
                "N": p["N"],
                "signal_i": p["signal_i"],
                "target": h + cfg.hold_h,
                "stop_px": px * (1 - cfg.stop),
            }
        # 2. time exits at this bar's open, then 3. the catastrophic stop inside this bar
        for s in list(pos):
            q = pos[s]
            px, kind = None, None
            if h >= q["target"] and np.isfinite(O[s][h]):
                px, kind = O[s][h], ("TIME" if h == q["target"] else "TIME_ROLLED")
            elif np.isfinite(L[s][h]) and L[s][h] <= q["stop_px"]:
                px, kind = L[s][h], "STOP_AT_LOW"
            if px is None:
                continue
            proceeds = q["units"] * px * (1 - cs)
            cash += proceeds
            trades.append(
                {
                    "symbol": s,
                    "signal_time": str(ix[q["signal_i"]] + pd.Timedelta(hours=1)),
                    "entry_time": str(ix[q["entry_i"]]),
                    "entry_px": q["entry_px"],
                    "notional": q["N"],
                    "units": q["units"],
                    "exit_time": str(ix[h]),
                    "exit_px": float(px),
                    "exit_type": kind,
                    "gross": float(px / q["entry_px"] - 1),
                    "net": float(proceeds / q["N"] - 1),
                    "pnl": float(proceeds - q["N"]),
                    "signal_i": q["signal_i"],
                }
            )
            del pos[s]
        # 4. mark at the close
        value = sum(q["units"] * last_close[s] for s, q in pos.items())
        equity = cash + value
        daily.append((ix[h], equity, value, cash))
        # 5. decisions at this bar's close
        if h <= last_dec:
            for s in syms:
                if not F[s][h] or s in pos or s in pending or h < blocked.get(s, -1):
                    continue
                e = h + 1 + cfg.entry_lag_h
                if e + cfg.hold_h > end:
                    events.append({"type": "NO_ROOM_FOR_EXIT", "symbol": s, "bar": str(ix[h])})
                    continue
                n = min(cfg.size * equity, cash - reserved)
                if n < cfg.min_order:
                    events.append({"type": "NO_CASH", "symbol": s, "bar": str(ix[h])})
                    continue
                pending[s] = {"N": n, "entry_i": e, "signal_i": h}
                reserved += n
        if h > last_dec and not pos and not pending:
            break
        h += 1
    for s, q in pos.items():  # cannot happen when every exit fits in the data; kept as a guard
        events.append({"type": "UNRESOLVED", "symbol": s, "value": q["units"] * last_close[s]})
    eq = pd.DataFrame(daily, columns=["t", "equity", "invested", "cash"]).set_index("t")
    return {"trades": trades, "equity": eq, "events": events, "cash": cash}


def check_account(acct: dict, cfg: Config) -> list[str]:
    """Accounting identities and limits."""
    problems = []
    eq = acct["equity"]
    if (eq.cash < -1e-6).any():
        problems.append("negative cash")
    if (eq.invested > eq.equity * 1.0 + 1e-6).any():
        problems.append("invested above equity (leverage)")
    if any(e["type"] == "UNRESOLVED" for e in acct["events"]):
        problems.append("unresolved position at the end of the data")
    realized = sum(t["pnl"] for t in acct["trades"])
    if not acct["events"] or all(e["type"] != "UNRESOLVED" for e in acct["events"]):
        if abs(cfg.start_cash + realized - acct["cash"]) > 1e-6 * cfg.start_cash:
            problems.append("cash != start + realized P&L")
        if abs(eq.equity.iloc[-1] - acct["cash"]) > 1e-6 * cfg.start_cash:
            problems.append("final equity != final cash with no open position")
    by = {}
    for t in acct["trades"]:
        by.setdefault(t["symbol"], []).append((t["entry_time"], t["exit_time"]))
    for s, spans in by.items():
        spans.sort()
        for a, b in itertools.pairwise(spans):
            if b[0] < a[1]:
                problems.append(f"{s}: overlapping positions")
    return problems


# ------------------------------------------------------------------------------------------------------ statistics
def episodes(signal_times: list[str], gap_days: int) -> list[int]:
    order = np.argsort(pd.to_datetime(pd.Series(signal_times)).to_numpy())
    ids, ep, last = [0] * len(signal_times), -1, None
    for k in order:
        t = pd.Timestamp(signal_times[k])
        if last is None or t - last > pd.Timedelta(days=gap_days):
            ep += 1
        ids[k] = ep
        last = t
    return ids


def cluster_bootstrap(x: np.ndarray, groups: list[int]) -> dict:
    x = np.asarray(x, float)
    g = np.asarray(groups)
    uniq = np.unique(g)
    if len(uniq) < 2:
        return {
            "mean": float(x.mean()) if len(x) else None,
            "lower_one_sided_95": None,
            "lower95": None,
            "upper95": None,
            "episodes": len(uniq),
            **BOOT,
        }
    rng = np.random.default_rng(BOOT["seed"])
    members = [x[g == u] for u in uniq]
    draws = []
    for _ in range(BOOT["draws"]):
        pick = rng.integers(0, len(uniq), len(uniq))
        draws.append(np.concatenate([members[k] for k in pick]).mean())
    d = np.array(draws)
    return {
        "mean": float(x.mean()),
        "lower_one_sided_95": float(np.quantile(d, 0.05)),
        "lower95": float(np.quantile(d, 0.025)),
        "upper95": float(np.quantile(d, 0.975)),
        "episodes": len(uniq),
        **BOOT,
    }


def eligible_returns(data: dict, window, cost, cfg: Config) -> dict:
    """Net trade return for an entry at every eligible signal bar (legs valid, entry and exit inside the data)."""
    out = {}
    for s, d in data.items():
        idx = window_idx(d["spot"], window)
        valid = d["legs"].valid.to_numpy()
        rets = []
        for i in idx:
            if valid[i]:
                tr = simulate_trade(d["spot"], int(i), cost, cfg)
                if tr is not None:
                    rets.append(tr["net"])
        out[s] = np.array(rets)
    return out


def placebo(elig: dict, counts: dict) -> dict:
    rng = np.random.default_rng(PLACEBO["seed"])
    means = []
    for _ in range(PLACEBO["draws"]):
        pooled = [rng.choice(elig[s], size=counts[s], replace=False) for s in counts if counts[s]]
        means.append(np.concatenate(pooled).mean() if pooled else np.nan)
    m = np.array(means)
    n = sum(counts.values())
    unconditional = sum(counts[s] * elig[s].mean() for s in counts if counts[s]) / n if n else None
    return {
        "p90": float(np.nanquantile(m, 0.90)),
        "p50": float(np.nanquantile(m, 0.50)),
        "p10": float(np.nanquantile(m, 0.10)),
        "matched_unconditional_mean": unconditional,
        "eligible_hours": {s: len(v) for s, v in elig.items()},
        **PLACEBO,
        "means": m,
    }


def account_summary(acct: dict, cfg: Config) -> dict:
    eq = acct["equity"]
    tr = pd.DataFrame(acct["trades"])
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 86400)
    end = float(eq.equity.iloc[-1])
    peak = eq.equity.cummax()
    dd = float((eq.equity / peak - 1).min())
    expo = float((eq.invested / eq.equity).mean())
    out = {
        "start": cfg.start_cash,
        "end_equity": end,
        "net_return": end / cfg.start_cash - 1,
        "cagr": (end / cfg.start_cash) ** (1 / years) - 1 if years > 0 else None,
        "years": years,
        "max_drawdown": dd,
        "mean_exposure": expo,
        "trades": len(tr),
        "events": pd.Series([e["type"] for e in acct["events"]]).value_counts().to_dict(),
    }
    if len(tr):
        mean_eq = float(eq.equity.mean())
        traded = float(tr.notional.sum() + (tr.units * tr.exit_px).sum())
        wins = tr.pnl.sort_values(ascending=False)
        net = tr.net.sort_values()
        k = max(1, math.ceil(0.05 * len(net)))
        out.update(
            turnover_per_year=traded / mean_eq / years if years > 0 else None,
            win_rate=float((tr.net > 0).mean()),
            mean_net=float(tr.net.mean()),
            median_net=float(tr.net.median()),
            worst_net=float(tr.net.min()),
            best_net=float(tr.net.max()),
            cvar95_net=float(net.iloc[:k].mean()),
            realized_pnl=float(tr.pnl.sum()),
            pnl_without_top3=float(tr.pnl.sum() - wins.iloc[:3].clip(lower=0).sum()),
            exit_types=tr.exit_type.value_counts().to_dict(),
            by_symbol={
                s: {
                    "trades": len(g),
                    "mean_net": float(g.net.mean()),
                    "pnl": float(g.pnl.sum()),
                }
                for s, g in tr.groupby("symbol")
            },
            by_year={
                str(y): {
                    "trades": len(g),
                    "mean_net": float(g.net.mean()),
                    "pnl": float(g.pnl.sum()),
                }
                for y, g in tr.groupby(pd.to_datetime(tr.entry_time).dt.year)
            },
        )
    m = eq.equity.resample("ME").last()
    out["monthly_returns"] = {
        k.strftime("%Y-%m"): float(v)
        for k, v in (m / m.shift(1).fillna(cfg.start_cash) - 1).items()
    }
    return out


def buy_and_hold(data: dict, window, cost, cfg: Config) -> dict:
    """Equal-weight BTC/ETH bought at the first window bar's open, sold at the last window bar's close."""
    out, legs_ = {}, []
    for s, d in data.items():
        idx = window_idx(d["spot"], window)
        sp = d["spot"].iloc[idx]
        o, c = sp.open.dropna().iloc[0], sp.close.dropna().iloc[-1]
        path = sp.close.ffill() / o * (1 - cost[0])
        legs_.append(path)
        out[s] = float((1 - cost[0]) * (1 - cost[1]) * c / o - 1)
    curve = sum(legs_) / len(legs_)
    out["equal_weight"] = float(curve.iloc[-1] * (1 - cost[1]) - 1)
    out["equal_weight_max_drawdown"] = float((curve / curve.cummax() - 1).min())
    return out


def event_paths(data: dict, trades_by: dict, hours: int = 168) -> pd.DataFrame:
    """Mean gross path (close / signal close - 1) for k = 0..hours after each signal: descriptive only."""
    rows = []
    for label, lst in trades_by.items():
        for s, tr in lst:
            c = data[s]["spot"].close.to_numpy()
            i = tr["signal_i"]
            if i + hours < len(c):
                rows.append((label, *(c[i : i + hours + 1] / c[i] - 1)))
    if not rows:
        return pd.DataFrame()
    f = pd.DataFrame(rows, columns=["label", *range(hours + 1)])
    return f.groupby("label").mean().T


# ------------------------------------------------------------------------------------------------------ modes
def feasibility() -> int:
    """Count debounced signals per k (time-based debounce, no forward price read). Writes FEASIBILITY.json."""
    if PROTO.exists():
        sys.exit("error: protocol.json exists; feasibility is a pre-freeze step")
    rows = {}
    for k in K_CANDIDATES:
        cfg = Config(sigma_k=k)
        data = load_all(cfg)
        res = {}
        for period, window in (("discovery", DISCOVERY), ("screen_2023", SCREEN)):
            times, per = [], {}
            for s, d in data.items():
                for flag in ("cascade", "droponly", "control"):
                    f = d["legs"][flag].to_numpy()
                    n, busy = 0, -1
                    for i in window_idx(d["spot"], window):
                        if f[i] and i > busy:
                            n += 1
                            busy = i + 1 + cfg.entry_lag_h + cfg.hold_h - 1
                            if flag == "cascade":
                                times.append(str(d["spot"].index[i]))
                    per[f"{s}_{flag}"] = n
                per[f"{s}_valid_hours"] = int(
                    d["legs"].valid.to_numpy()[window_idx(d["spot"], window)].sum()
                )
            res[period] = {
                **per,
                "cascade_total": len(times),
                "cascade_episodes": len(set(episodes(times, 7))) if times else 0,
            }
        rows[str(k)] = res
    rule = K_RULE
    chosen = choose_k(rows)
    out = {
        "study": "LIQ_REBOUND_v1",
        "computed_at": utc_stamp(),
        "what": "signal counts only; no return, no "
        "forward price, no outcome was computed (debounce assumes every position lasts entry_lag + 72h)",
        "rule": rule,
        "counts": rows,
        "chosen_sigma_k": chosen,
    }
    FEAS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


PINS = (
    "research/LIQ_REBOUND_v1/rebound.py",
    "research/LIQ_REBOUND_v1/collect.py",
    "research/LIQ_REBOUND_v1/PROTOCOL.md",
    "research/LIQ_REBOUND_v1/FEASIBILITY.json",
    "research/LIQ_REBOUND_v1/report.py",
    "idxsig/provenance.py",
    "tests/test_liq_rebound.py",
    "data/manifests/liq_rebound-20261031T223330Z.jsonl",
    "data/manifests/binance_1h-20261015T182940Z.jsonl",
)


K_RULE = (
    "freeze the largest k in K_CANDIDATES whose DISCOVERY cascade_total >= 30 and cascade_episodes >= 8; "
    "if none qualifies, freeze the smallest k (G0 then decides whether the sample suffices)"
)


def choose_k(counts: dict) -> float:
    return next(
        (
            float(k)
            for k in K_CANDIDATES
            if counts[str(k)]["discovery"]["cascade_total"] >= 30
            and counts[str(k)]["discovery"]["cascade_episodes"] >= 8
        ),
        min(K_CANDIDATES),
    )


def frozen_config() -> Config:
    f = json.loads(FEAS.read_text())
    k = choose_k(f["counts"])
    if k != f["chosen_sigma_k"] or f["rule"] != K_RULE:
        raise RuntimeError(
            "FEASIBILITY.json's chosen k does not follow from its counts and the rule"
        )
    return Config(sigma_k=float(k))


def versions() -> dict:
    return {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__}


def git_clean(paths: list[str]) -> None:
    """Refuse unless every path is tracked and unmodified, so the recorded commit really contains it."""
    for p in paths:
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", p], cwd=ROOT, capture_output=True, check=False
        )
        if r.returncode:
            sys.exit(f"error: {p} is not committed")
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if dirty:
        sys.exit(f"error: uncommitted changes in pinned files:\n{dirty}")


def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    git_clean(list(PINS))
    cfg = frozen_config()
    proto = {
        "study_id": "LIQ_REBOUND_v1",
        "frozen_at": utc_stamp(),
        "config": asdict(cfg),
        "costs": {k: {"buy": v[0], "sell": v[1]} for k, v in COSTS.items()},
        "windows": {
            "discovery_signal_bars": [str(x) for x in DISCOVERY],
            "screen_2023_signal_bars": [str(x) for x in SCREEN],
            "data_bars": [str(DATA_FIRST), str(DATA_LAST)],
            "not_read": "2024-01-01 onward",
        },
        "bootstrap": BOOT,
        "placebo": {k: v for k, v in PLACEBO.items()},
        "missed_fill_stress": MISSED,
        "gates": GATES,
        "versions": versions(),
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "config", "gates")}, indent=1))
    return 0


GATES = {
    "G0_sample": "discovery cascade trades (A2 account) >= 20 and episodes (7-day gap) >= 8; else INCONCLUSIVE",
    "G1_net_edge": "discovery mean net trade return (A2) > 0 and its episode-cluster bootstrap one-sided 95% lower "
    "bound > 0",
    "G2_timing": "discovery mean net trade return (A2) > the 90th percentile of the random-entry placebo (same coins, "
    "same counts, same rules and costs, eligible signal hours of the discovery window)",
    "G3_mechanism": "discovery mean GROSS return of cascade trades > that of control trades (control: drop-only "
    "hours - same price leg, OI change above its 5% tail - with no cascade hour on the same coin in the preceding "
    "1 + entry lag + hold bars; trade-level, debounced; drop size not matched); NOT_EVALUABLE if fewer than 5 "
    "control trades",
    "G4_account": "discovery A2 account: end equity > start, max drawdown >= -25%, realized P&L without the 3 "
    "largest winners > 0",
    "G5_stress": "discovery accounts S1 (A2, entry 4h after the signal) and S2 (doubled slippage) both end above "
    "start",
    "G6_screen_2023": "if the 2023 A2 account has >= 3 trades its mean net trade return must be >= 0; with fewer "
    "than 3 trades the screen is uninformative (flagged) and does not block",
    "verdict": "PROMISING (a candidate for validation, never proof) only if G0-G6 all PASS; INCONCLUSIVE if G0 fails "
    "or G3 is NOT_EVALUABLE; otherwise FAIL",
}


def gates(res: dict) -> dict:
    d = res["discovery"]
    g = {}
    a2 = d["accounts"]["A2"]
    g["G0_sample"] = "PASS" if a2["trades"] >= 20 and d["episodes"] >= 8 else "FAIL"
    b = d["bootstrap_A2"]
    g["G1_net_edge"] = (
        "PASS" if (b["mean"] or 0) > 0 and (b["lower_one_sided_95"] or -1) > 0 else "FAIL"
    )
    g["G2_timing"] = "PASS" if (b["mean"] or -1) > d["placebo_A2"]["p90"] else "FAIL"
    m = d["mechanism"]
    if m["control_trades"] < 5:
        g["G3_mechanism"] = "NOT_EVALUABLE"
    else:
        g["G3_mechanism"] = "PASS" if m["cascade_gross_mean"] > m["control_gross_mean"] else "FAIL"
    g["G4_account"] = (
        "PASS"
        if (
            a2["end_equity"] > a2["start"]
            and a2["max_drawdown"] >= -0.25
            and a2.get("pnl_without_top3", -1) > 0
        )
        else "FAIL"
    )
    s1, s2 = d["accounts"]["S1_delay4h"], d["accounts"]["S2"]
    g["G5_stress"] = (
        "PASS" if s1["end_equity"] > s1["start"] and s2["end_equity"] > s2["start"] else "FAIL"
    )
    sc = res["screen_2023"]["accounts"]["A2"]
    if sc["trades"] < 3:
        g["G6_screen_2023"] = "PASS (uninformative: fewer than 3 trades)"
    else:
        g["G6_screen_2023"] = "PASS" if sc["mean_net"] >= 0 else "FAIL"
    if g["G0_sample"] == "FAIL" or g["G3_mechanism"] == "NOT_EVALUABLE":
        verdict = "INCONCLUSIVE"
    elif all(v.startswith("PASS") for v in g.values()):
        verdict = "PROMISING"
    else:
        verdict = "FAIL"
    return {"gates": g, "verdict": verdict}


def evaluate(data: dict, cfg: Config, window) -> tuple[dict, dict]:
    accts, files = {}, {}
    for name, cost in (
        ("A1", COSTS["A1"]),
        ("A2", COSTS["A2"]),
        ("A3", COSTS["A3"]),
        ("S2", COSTS["S2"]),
    ):
        accts[name] = run_account(data, window, cost, cfg)
    accts["S1_delay4h"] = run_account(data, window, COSTS["A2"], replace(cfg, entry_lag_h=4))
    out = {"accounts": {}}
    for name, a in accts.items():
        probs = check_account(a, cfg)
        if probs:
            raise RuntimeError(f"{name}: {probs}")
        out["accounts"][name] = account_summary(a, cfg)
        files[f"trades_{name}.csv"] = pd.DataFrame(a["trades"])
        files[f"equity_{name}.csv.gz"] = a["equity"]
    a2 = accts["A2"]
    times = [t["signal_time"] for t in a2["trades"]]
    eps = episodes(times, cfg.episode_gap_days) if times else []
    out["episodes"] = len(set(eps))
    out["bootstrap_A2"] = cluster_bootstrap(np.array([t["net"] for t in a2["trades"]]), eps)
    # missed-fill stress (reported)
    rng = np.random.default_rng(MISSED["seed"])
    ends = [
        account_summary(run_account(data, window, COSTS["A2"], cfg, fail_rng=rng), cfg)[
            "end_equity"
        ]
        for _ in range(MISSED["draws"])
    ]
    out["missed_fill_A2"] = {
        "median_end": float(np.median(ends)),
        "p05_end": float(np.quantile(ends, 0.05)),
        "share_above_start": float(np.mean(np.array(ends) > cfg.start_cash)),
        **MISSED,
    }
    # mechanism: cascade vs drop-only, trade-level
    casc, drop = [], []
    for s, d in data.items():
        idx = window_idx(d["spot"], window)
        casc += [
            (s, t)
            for t in debounced(d["spot"], d["legs"].cascade.to_numpy(), idx, COSTS["A2"], cfg)
        ]
        drop += [
            (s, t)
            for t in debounced(d["spot"], d["legs"].control.to_numpy(), idx, COSTS["A2"], cfg)
        ]
    out["mechanism"] = {
        "cascade_trades": len(casc),
        "control_trades": len(drop),
        "cascade_gross_mean": float(np.mean([t["gross"] for _, t in casc])) if casc else None,
        "control_gross_mean": float(np.mean([t["gross"] for _, t in drop])) if drop else None,
        "cascade_net_mean_A2": float(np.mean([t["net"] for _, t in casc])) if casc else None,
        "control_net_mean_A2": float(np.mean([t["net"] for _, t in drop])) if drop else None,
        "cascade_mean_signal_lr": float(
            np.mean([data[s]["legs"].lr.iloc[t["signal_i"]] for s, t in casc])
        )
        if casc
        else None,
        "control_mean_signal_lr": float(
            np.mean([data[s]["legs"].lr.iloc[t["signal_i"]] for s, t in drop])
        )
        if drop
        else None,
    }
    files["mechanism_trades.csv"] = pd.DataFrame(
        [
            {
                "set": lab,
                "symbol": s,
                "signal_time": str(data[s]["spot"].index[t["signal_i"]] + pd.Timedelta(hours=1)),
                **{k: t[k] for k in ("entry_px", "exit_px", "exit_type", "gross", "net")},
            }
            for lab, lst in (("cascade", casc), ("control", drop))
            for s, t in lst
        ]
    )
    paths = event_paths(data, {"cascade": casc, "control": drop})
    if len(paths):
        files["event_paths.csv"] = paths
    # placebo (random entries, same counts)
    counts = {s: sum(1 for t in a2["trades"] if t["symbol"] == s) for s in data}
    elig = eligible_returns(data, window, COSTS["A2"], cfg)
    pl = placebo(elig, counts)
    files["placebo_means.csv"] = pd.DataFrame({"mean_net": pl.pop("means")})
    out["placebo_A2"] = pl
    out["buy_and_hold_A2"] = buy_and_hold(data, window, COSTS["A2"], cfg)
    return out, files


def run() -> int:
    if RUN.exists():
        sys.exit("error: run/ exists; LIQ_REBOUND_v1 runs once")
    proto = json.loads(PROTO.read_text())
    git_clean([*PINS, "research/LIQ_REBOUND_v1/protocol.json"])
    if set(proto["pins"]) != set(PINS):
        sys.exit("error: protocol.json pins a different file set")
    for p, want in proto["pins"].items():
        if sha256_file(ROOT / p) != want:
            sys.exit(f"error: {p} changed since the freeze")
    cfg = Config(**proto["config"])
    expected = {
        "config": asdict(frozen_config()),
        "costs": {k: {"buy": v[0], "sell": v[1]} for k, v in COSTS.items()},
        "windows": {
            "discovery_signal_bars": [str(x) for x in DISCOVERY],
            "screen_2023_signal_bars": [str(x) for x in SCREEN],
            "data_bars": [str(DATA_FIRST), str(DATA_LAST)],
            "not_read": "2024-01-01 onward",
        },
        "bootstrap": BOOT,
        "placebo": PLACEBO,
        "missed_fill_stress": MISSED,
        "gates": GATES,
        "versions": versions(),
    }
    for key, want in expected.items():
        if proto[key] != want:
            sys.exit(f"error: protocol.json '{key}' differs from what this run would use")
    data = load_all(cfg)
    res = {
        "study": "LIQ_REBOUND_v1",
        "ran_at": utc_stamp(),
        "config": asdict(cfg),
        "protocol_sha256": sha256_file(PROTO),
        "versions": versions(),
    }
    files = {}
    for period, window in (("discovery", DISCOVERY), ("screen_2023", SCREEN)):
        out, f = evaluate(data, cfg, window)
        res[period] = out
        files.update({f"{period}/{k}": v for k, v in f.items()})
    res.update(gates(res))
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    RUN.mkdir()
    for name, frame in files.items():
        p = RUN / name
        p.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(
            p,
            index=name.startswith(
                ("discovery/equity", "screen_2023/equity", "discovery/event", "screen_2023/event")
            ),
        )
    (RUN / "RESULT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(res["verdict"], json.dumps(res["gates"], indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--feasibility", action="store_true")
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    return feasibility() if a.feasibility else freeze() if a.freeze else run()


if __name__ == "__main__":
    sys.exit(main())
