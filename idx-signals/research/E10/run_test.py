"""E10 step 4: the single recorded discovery test (research/E10/PROTOCOL.md; protocol.json is frozen first).

Event: an earnings release (8-K Item 2.02) that revises the issuer's full-year revenue guidance
(feasibility/events.csv.gz, frozen before any return). No price condition of any kind.
Entry: the open of the first session the release could be traded on (accepted by 09:15 New York time on a session
day: that session; otherwise the next session). Exit: the close of the 20th session (entry session = session 1).
Costs: the US profile's per-side tiers on as-traded prices plus the SEC fee on sales.
Controls: for each event, 200 draws (with replacement) from names on the same entry session in the same cost tier,
liquidity quintile, 20-session momentum tercile and 20-session volatility tercile, without their own Item 2.02 release
from 5 sessions before entry to the exit; the least important bucket is dropped while fewer than 5 names match.
Statistics: week-cluster bootstrap (ISO week of entry), 10,000 resamples, seed 20261017.

Usage (from idx-signals/): python3 research/E10/run_test.py
Writes research/E10/results/{RESULT.json, trades.csv.gz}. Refuses a changed input or an existing output.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import profiles  # noqa: E402

E10 = ROOT / "research" / "E10"
OUT = E10 / "results"
PANEL = ROOT / "data" / "panel" / "panel_us_repair-20261008T114805Z.csv.gz"
LAST_SESSION = "2022-12-30"           # discovery ends; 2023 is the used validation year; 2024+ is sealed
HOLD = 20
SHORT_HOLD = 5
STOP = 0.05
MIN_PRICE = 2.0                        # as-traded entry open
MIN_VALUE = 500_000.0                  # median traded value, 20 sessions before entry
LOOKBACK = 20
DRAWS = 200
MIN_POOL = 5
EXCLUDE_BEFORE = 5
SEED = 20261017
RESAMPLES = 10_000
STRESS = 0.005
NOTIONAL = 5_000.0
US = profiles.US


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_panel():
    cols = ["date", "ticker", "open", "high", "low", "close", "value", "unit_factor"]
    p = pd.read_csv(PANEL, usecols=cols, dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    p = p[p.date <= LAST_SESSION]
    dates = np.array(sorted(p.date.unique()))
    tickers = np.array(sorted(p.ticker.unique()))
    di = {d: i for i, d in enumerate(dates)}
    ti = {t: i for i, t in enumerate(tickers)}
    r, c = p.date.map(di).to_numpy(), p.ticker.map(ti).to_numpy()
    mats = {}
    for col in ("open", "high", "low", "close", "value", "unit_factor"):
        m = np.full((len(dates), len(tickers)), np.nan)
        m[r, c] = p[col].to_numpy(dtype=float)
        mats[col] = m
    return dates, tickers, ti, mats


def entry_session(accept_ny: str, dates: np.ndarray) -> int | None:
    t = pd.Timestamp(accept_ny)
    day = t.strftime("%Y-%m-%d")
    i = int(np.searchsorted(dates, day, side="left"))
    if i < len(dates) and dates[i] == day and (t.hour, t.minute) <= (9, 15):
        return i
    j = int(np.searchsorted(dates, day, side="right"))
    return j if j < len(dates) else None


def net_returns(entry_px, exit_px, entry_traded, exit_traded, extra=0.0):
    c_in = US.per_side_cost(entry_traded) + US.fee_buy + extra
    c_out = US.per_side_cost(exit_traded) + US.fee_sell + extra
    return (exit_px / entry_px) * (1 - c_in) * (1 - c_out) - 1


def trade(m, e, j, hold, stop=None):
    """(entry adjusted, exit adjusted, entry as-traded, exit as-traded, exit index) for name j entered at e."""
    o, lo, cl, f = m["open"], m["low"], m["close"], m["unit_factor"]
    x = e + hold - 1
    px_in = o[e, j]
    if stop is not None:
        level = px_in * (1 - stop)
        for k in range(e, x + 1):
            if k > e and o[k, j] <= level:
                return px_in, o[k, j], px_in * f[e, j], o[k, j] * f[k, j], k
            if lo[k, j] <= level:
                return px_in, level, px_in * f[e, j], level * f[k, j], k
    return px_in, cl[x, j], px_in * f[e, j], cl[x, j] * f[x, j], x


def features(m, e):
    cl, val = m["close"], m["value"]
    win = slice(max(0, e - LOOKBACK), e)
    med_val = np.nanmedian(val[win], axis=0)
    mom = cl[e - 1] / cl[e - 1 - LOOKBACK] - 1 if e - 1 - LOOKBACK >= 0 else np.full(cl.shape[1], np.nan)
    lr = np.diff(np.log(cl[max(0, e - LOOKBACK - 1):e]), axis=0)
    vol = np.nanstd(lr, axis=0) if len(lr) > 1 else np.full(cl.shape[1], np.nan)
    return med_val, mom, vol


def quantile_bucket(x: np.ndarray, pool: np.ndarray, q: int) -> np.ndarray:
    edges = np.nanquantile(x[pool], np.linspace(0, 1, q + 1)[1:-1]) if pool.any() else np.array([])
    return np.where(np.isfinite(x), np.searchsorted(edges, x, side="right"), -1)


def wilson(k: int, n: int) -> list:
    if n == 0:
        return [None, None]
    z, p = 1.959964, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def boot(values: np.ndarray, weeks: np.ndarray, rng_seed: int) -> dict:
    """Mean with a week-cluster bootstrap: 95% interval and one-sided p (share of resampled means <= 0)."""
    if len(values) == 0:
        return {"n": 0}
    uw, inv = np.unique(weeks, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=len(uw))
    cnts = np.bincount(inv, minlength=len(uw)).astype(float)
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, len(uw), size=(RESAMPLES, len(uw)))
    means = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    return {"n": int(len(values)), "mean": float(values.mean()), "ci95": [float(np.quantile(means, 0.025)),
            float(np.quantile(means, 0.975))], "p_one_sided": float((means <= 0).mean()), "weeks": int(len(uw))}


def boot_diff(a, wa, b, wb, rng_seed):
    """Difference of means (a - b), resampling the union of weeks once for both samples."""
    weeks = np.unique(np.concatenate([wa, wb]))
    wi = {w: i for i, w in enumerate(weeks)}
    ia, ib = np.array([wi[w] for w in wa]), np.array([wi[w] for w in wb])
    sa, ca = np.bincount(ia, a, len(weeks)), np.bincount(ia, minlength=len(weeks)).astype(float)
    sb, cb = np.bincount(ib, b, len(weeks)), np.bincount(ib, minlength=len(weeks)).astype(float)
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, len(weeks), size=(RESAMPLES, len(weeks)))
    with np.errstate(invalid="ignore", divide="ignore"):
        d = sa[idx].sum(1) / ca[idx].sum(1) - sb[idx].sum(1) / cb[idx].sum(1)
    d = d[np.isfinite(d)]
    return {"diff": float(a.mean() - b.mean()), "ci95": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))],
            "p_one_sided": float((d <= 0).mean())}


def clipped_mean(x: np.ndarray) -> float:
    lo, hi = np.quantile(x, [0.01, 0.99])
    return float(np.clip(x, lo, hi).mean())


def summary(df: pd.DataFrame, seed: int) -> dict:
    if len(df) == 0:
        return {"n": 0}
    net, exc = df.net.to_numpy(), df.excess.to_numpy()
    wins = int((net > 0).sum())
    return {"n": int(len(df)), "mean_net": float(net.mean()), "median_net": float(np.median(net)),
            "clipped_mean_net": clipped_mean(net), "win_rate": wins / len(df), "win_rate_ci95": wilson(wins, len(df)),
            "mean_control_net": float(df.control_net.mean()), "excess": boot(exc, df.week.to_numpy(), seed),
            "clipped_mean_excess": clipped_mean(exc), "net_boot": boot(net, df.week.to_numpy(), seed + 1),
            "stress_mean_net": float(df.net_stress.mean()), "net_5": float(df.net_5.mean()),
            "excess_5": float(df.excess_5.mean()), "net_stop": float(df.net_stop.mean()),
            "excess_stop": float(df.excess_stop.mean()),
            "by_year": {y: {"n": int(len(g)), "mean_net": float(g.net.mean()), "mean_excess": float(g.excess.mean())}
                        for y, g in df.groupby(df.entry_date.str[:4])}}


def account(df: pd.DataFrame, dates: np.ndarray, m, ti) -> dict:
    """Every trade at NOTIONAL dollars, positions valued at each close (no capital cap): capital deployed and a
    marked-to-market equity curve."""
    if len(df) == 0:
        return {}
    pnl = np.zeros(len(dates))
    open_n = np.zeros(len(dates), dtype=int)
    for r in df.itertuples():
        j, e, x = ti[r.ticker], r.e, r.x
        path = m["close"][e:x + 1, j] / m["open"][e, j]
        val = NOTIONAL * path
        val[-1] = NOTIONAL * (1 + r.net)
        daily = np.diff(np.concatenate([[NOTIONAL], val]))
        pnl[e:x + 1] += daily
        open_n[e:x + 1] += 1
    eq = np.cumsum(pnl)
    dd = eq - np.maximum.accumulate(np.maximum(eq, 0))
    return {"notional_per_trade": NOTIONAL, "trades": int(len(df)), "total_pnl": float(eq[-1]),
            "max_positions": int(open_n.max()), "max_capital_deployed": float(open_n.max() * NOTIONAL),
            "mean_positions": float(open_n[open_n > 0].mean()), "max_drawdown_marked": float(dd.min()),
            "note": "positions valued at every close; no capital limit: compare drawdown with max_capital_deployed"}


def main() -> int:
    proto = json.loads((E10 / "protocol.json").read_text())
    for rel, h in proto["hashes"].items():
        if sha(ROOT / rel) != h:
            sys.exit(f"refused: {rel} changed since the freeze")
    if (OUT / "RESULT.json").exists():
        sys.exit("refused: results already exist (one recorded run)")
    started = datetime.now(timezone.utc).isoformat()
    dates, tickers, ti, m = load_panel()
    ev = pd.read_csv(E10 / "feasibility" / "events.csv.gz", dtype={"ticker": str})
    releases = pd.read_csv(E10 / "feasibility" / "releases.csv.gz", dtype={"ticker": str})
    releases = releases[releases.status == "OK"].dropna(subset=["acceptance_ny"])

    # sessions in which each name had its own earnings release (for control exclusion)
    own = np.zeros((len(dates), len(tickers)), dtype=bool)
    for r in releases.itertuples():
        if r.ticker in ti:
            e = entry_session(r.acceptance_ny, dates)
            if e is not None:
                own[e, ti[r.ticker]] = True
    own_cum = np.vstack([np.zeros((1, len(tickers)), dtype=int), np.cumsum(own, axis=0)])

    rows, skipped = [], {}
    held_until = {}
    ev = ev.sort_values("acceptance_ny").reset_index(drop=True)
    feat_cache = {}
    for k, r in enumerate(ev.to_dict("records")):
        def skip(reason):
            skipped[reason] = skipped.get(reason, 0) + 1
        if r["ticker"] not in ti:
            skip("not in panel")
            continue
        j = ti[r["ticker"]]
        e = entry_session(r["acceptance_ny"], dates)
        if e is None or e + HOLD - 1 >= len(dates):
            skip("exit beyond discovery")
            continue
        x = e + HOLD - 1
        if not (np.isfinite(m["open"][e, j]) and np.isfinite(m["close"][x, j])):
            skip("no price at entry or exit")
            continue
        if held_until.get(j, -1) >= e:
            skip("overlap")
            continue
        if e not in feat_cache:
            feat_cache[e] = features(m, e)
        med_val, mom, vol = feat_cache[e]
        traded_in = m["open"][e] * m["unit_factor"][e]
        if traded_in[j] < MIN_PRICE or not med_val[j] >= MIN_VALUE:
            skip("below price or liquidity floor")
            continue
        # controls
        valid = (np.isfinite(m["open"][e]) & np.isfinite(m["close"][x]) & (traded_in >= MIN_PRICE) &
                 (med_val >= MIN_VALUE))
        lo_s = max(0, e - EXCLUDE_BEFORE)
        busy = (own_cum[x + 1] - own_cum[lo_s]) > 0
        pool = valid & ~busy
        pool[j] = False
        tier = np.searchsorted(np.array([1, 5, 20]), traded_in, side="right")
        liq = quantile_bucket(med_val, pool, 5)
        mq = quantile_bucket(mom, pool, 3)
        vq = quantile_bucket(vol, pool, 3)
        keys = [tier == tier[j], liq == liq[j], mq == mq[j], vq == vq[j]]
        level = 4
        cand = pool & keys[0] & keys[1] & keys[2] & keys[3]
        while cand.sum() < MIN_POOL and level > 1:
            level -= 1
            cand = pool.copy()
            for kk in keys[:level]:
                cand &= kk
        idx = np.flatnonzero(cand)
        if len(idx) < MIN_POOL:
            skip("no control pool")
            continue
        rng = np.random.default_rng(SEED + k)
        draw = rng.choice(idx, size=DRAWS, replace=True)

        def nets(jj, hold, stop=None, extra=0.0):
            a, b, ta, tb, _ = trade(m, e, jj, hold, stop)
            return float(net_returns(a, b, ta, tb, extra))

        net = nets(j, HOLD)
        ctrl = np.array([nets(c, HOLD) for c in draw])
        ctrl5 = np.array([nets(c, SHORT_HOLD) for c in draw])
        ctrls = np.array([nets(c, HOLD, STOP) for c in draw])
        rows.append({"accession": r["accession"], "ticker": r["ticker"], "class": r["class"], "kind": r["kind"],
                     "level_change": r["level_change"], "acceptance_ny": r["acceptance_ny"], "e": e, "x": x, "entry_date": dates[e], "exit_date": dates[x],
                     "week": pd.Timestamp(dates[e]).strftime("%G-%V"), "entry_traded": float(traded_in[j]),
                     "net": net, "control_net": float(ctrl.mean()), "excess": net - float(ctrl.mean()),
                     "net_stress": nets(j, HOLD, extra=STRESS), "net_5": nets(j, SHORT_HOLD),
                     "excess_5": nets(j, SHORT_HOLD) - float(ctrl5.mean()), "net_stop": nets(j, HOLD, STOP),
                     "excess_stop": nets(j, HOLD, STOP) - float(ctrls.mean()), "match_level": level,
                     "pool": int(len(idx))})
        held_until[j] = x
    tr = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    tr.drop(columns=["e", "x"]).to_csv(OUT / "trades.csv.gz", index=False)

    by = {c: tr[tr["class"] == c] for c in ("RAISE", "MAINTAIN", "CUT")}
    res = {c: summary(d, SEED + i * 10) for i, (c, d) in enumerate(by.items())}
    contrasts = {}
    for a, b in (("RAISE", "MAINTAIN"), ("RAISE", "CUT")):
        if len(by[a]) and len(by[b]):
            contrasts[f"{a}_minus_{b}_excess"] = boot_diff(by[a].excess.to_numpy(), by[a].week.to_numpy(),
                                                           by[b].excess.to_numpy(), by[b].week.to_numpy(), SEED + 99)
    raise_ = res["RAISE"]
    gates = {}
    if raise_.get("n", 0):
        years = raise_["by_year"]
        gates = {
            "G1_raise_excess_ci_above_zero": raise_["excess"]["ci95"][0] > 0,
            "G2_raise_mean_and_clipped_net_positive": raise_["mean_net"] > 0 and raise_["clipped_mean_net"] > 0,
            "G3_raise_beats_maintain": contrasts.get("RAISE_minus_MAINTAIN_excess", {}).get("diff", -1) > 0,
            "G4_stress_net_positive": raise_["stress_mean_net"] > 0,
            "G5_excess_positive_every_year": all(v["mean_excess"] > 0 for v in years.values()),
        }
    verdict = "PASS" if gates and all(gates.values()) else "FAIL"
    etoro_path = ROOT / "data" / "raw" / "etoro" / "20261016T190421Z" / "instruments.json"
    etoro = {str(x["SymbolFull"]).upper().replace(".", "-")
             for x in json.loads(etoro_path.read_bytes())["InstrumentDisplayDatas"]
             if x["InstrumentTypeID"] == 5 and x["ExchangeID"] in (4, 5) and not x.get("IsInternalInstrument")}
    on_etoro = tr[tr.ticker.str.upper().str.replace(".", "-", regex=False).isin(etoro)]
    result = {
        "experiment": "E10 guidance revision (US), discovery 2020-07..2022-11, run once",
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "code": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
        "protocol_sha256": sha(E10 / "protocol.json"),
        "events_in": int(len(ev)), "skipped": skipped, "trades": int(len(tr)),
        "classes": res, "contrasts": contrasts, "gates": gates, "verdict": verdict,
        "raise_on_etoro": summary(on_etoro[on_etoro["class"] == "RAISE"], SEED + 77),
        "account_raise": account(by["RAISE"], dates, m, ti),
        "limits": ["US universe is today's listings only (survivor bias, likely flattering)",
                   "costs are assumed price tiers, not measured spreads; daily bars cannot prove an opening fill",
                   "guidance extraction is a frozen text rule with an audited error rate, not a reading of every filing",
                   "discovery only: 2023 is already used and 2024+ is sealed; a PASS licenses forward paper testing only"],
    }
    (OUT / "RESULT.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(json.dumps({k: result[k] for k in ("trades", "skipped", "gates", "verdict")}, indent=2))
    print(json.dumps({c: {kk: v for kk, v in res[c].items() if kk in ("n", "mean_net", "win_rate", "excess")}
                      for c in res}, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
