"""E10 step 5: recompute the decisive numbers of results/RESULT.json without run_test.py or run_full.py code: entry and
exit dates from the acceptance times, every trade's gross and net return from the panel (its own tier lookup), the
pre-entry move, class means, the RAISE week bootstrap, the RAISE - MAINTAIN contrast, account A, and gates G1-G6.

Usage (from idx-signals/): python3 research/E10/verify_result.py
Prints each check; exits non-zero if any differs by more than 1e-9 (1e-6 for account equity).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
E10 = ROOT / "research" / "E10"
PANEL = ROOT / "data" / "panel" / "panel_us_repair-20261008T114805Z.csv.gz"
TIERS = [(1.0, 0.015), (5.0, 0.005), (20.0, 0.0015), (float("inf"), 0.0005)]  # idxsig/profiles.py US, restated
SEC_FEE = 0.0000278
SEED, RESAMPLES, STRESS, HOLD = 20261017, 10_000, 0.005, 20


def tier(price: float) -> float:
    for upper, cost in TIERS:
        if price < upper:
            return cost
    return TIERS[-1][1]


def net(entry_adj, exit_adj, entry_traded, exit_traded, extra=0.0):
    return (exit_adj / entry_adj) * (1 - tier(entry_traded) - extra) * (1 - tier(exit_traded) - SEC_FEE - extra) - 1


def main() -> int:
    res = json.loads((E10 / "results" / "RESULT.json").read_text())
    T = pd.read_csv(E10 / "results" / "trades.csv.gz", dtype={"ticker": str, "shadow_ticker": str})
    bad = []

    def check(name, mine, theirs, tol=1e-9):
        if isinstance(mine, (bool, np.bool_, str)) or isinstance(theirs, (bool, str)):
            ok = mine == theirs
        else:
            ok = theirs is not None and abs(float(mine) - float(theirs)) <= tol
        print(f"{'ok ' if ok else 'BAD'} {name}: {mine} vs {theirs}")
        if not ok:
            bad.append(name)

    names = set(T.ticker) | set(T.shadow_ticker)
    p = pd.read_csv(PANEL, usecols=["date", "ticker", "open", "low", "close", "unit_factor"], dtype={"ticker": str},
                    keep_default_na=False, na_values=[""])
    p = p[(p.date <= "2022-12-30")]
    dates = np.array(sorted(p.date.unique()))
    p = p[p.ticker.isin(names)]
    wide = {c: p.pivot(index="date", columns="ticker", values=c).reindex(dates) for c in
            ("open", "low", "close", "unit_factor")}
    pos = {d: i for i, d in enumerate(dates)}

    # dates, gross, net, stress and pre-entry move per trade
    worst = {"entry": 0, "exit": 0, "gross": 0.0, "net": 0.0, "stress": 0.0, "pre": 0.0}
    for r in T.itertuples():
        t = pd.Timestamp(r.acceptance_ny)
        day = t.strftime("%Y-%m-%d")
        later = dates[dates > day]
        e = pos[day] if day in pos and (t.hour, t.minute) <= (9, 15) else pos[later[0]]
        x = e + HOLD - 1
        worst["entry"] += dates[e] != r.entry_date
        worst["exit"] += dates[x] != r.exit_date
        o, c, f = wide["open"][r.ticker], wide["close"][r.ticker], wide["unit_factor"][r.ticker]
        g = c.iloc[x] / o.iloc[e] - 1
        n = net(o.iloc[e], c.iloc[x], o.iloc[e] * f.iloc[e], c.iloc[x] * f.iloc[x])
        s = net(o.iloc[e], c.iloc[x], o.iloc[e] * f.iloc[e], c.iloc[x] * f.iloc[x], STRESS)
        before = dates[dates < day]
        s0 = pos[day] if day in pos and t.hour >= 16 else pos[before[-1]]
        pre = o.iloc[e] / c.iloc[s0] - 1
        worst["gross"] = max(worst["gross"], abs(g - r.gross))
        worst["net"] = max(worst["net"], abs(n - r.net))
        worst["stress"] = max(worst["stress"], abs(s - r.net_stress))
        if np.isfinite(r.pre_move):
            worst["pre"] = max(worst["pre"], abs(pre - r.pre_move))
    check("entry dates differing", worst["entry"], 0)
    check("exit dates differing", worst["exit"], 0)
    for k in ("gross", "net", "stress", "pre"):
        check(f"max |{k} recomputed - {k}|", worst[k], 0.0)
    check("max |excess - (net - control_net)|", float(np.max(np.abs(T.excess - (T.net - T.control_net)))), 0.0)

    # class statistics
    by = {c: T[T["class"] == c] for c in ("RAISE", "MAINTAIN", "CUT")}
    for c, d in by.items():
        out = res["classes"][c]
        check(f"n {c}", int(len(d)), out.get("n", 0))
        if len(d):
            check(f"{c} mean net", d.net.mean(), out["mean_net"])
            check(f"{c} mean excess", d.excess.mean(), out["excess"]["mean"])
            check(f"{c} mean pre-entry move", d.pre_move.mean(), out["pre_move"]["mean"])
    R = by["RAISE"]
    lo, hi = np.quantile(R.net, [0.01, 0.99])
    clipped = float(np.clip(R.net, lo, hi).mean())
    check("RAISE clipped mean net", clipped, res["classes"]["RAISE"]["clipped_mean_net"])
    check("RAISE stress mean net", R.net_stress.mean(), res["classes"]["RAISE"]["stress_mean_net"])
    years = {y: float(g.excess.mean()) for y, g in R.groupby(R.entry_date.str[:4])}
    for y, v in years.items():
        check(f"RAISE {y} mean excess", v, res["classes"]["RAISE"]["by_year"][y]["mean_excess"])

    # week bootstrap of the RAISE excess, rebuilt (RAISE is the first class: seed 20261017)
    weeks = sorted(R.week.unique())
    wpos = {w: i for i, w in enumerate(weeks)}
    sums, cnts = np.zeros(len(weeks)), np.zeros(len(weeks))
    for w, v in zip(R.week, R.excess):
        sums[wpos[w]] += v
        cnts[wpos[w]] += 1
    pick = np.random.default_rng(SEED).integers(0, len(weeks), size=(RESAMPLES, len(weeks)))
    means = sums[pick].sum(axis=1) / cnts[pick].sum(axis=1)
    ci_lo = float(np.quantile(means, 0.025))
    check("RAISE excess 95% lower bound", ci_lo, res["classes"]["RAISE"]["excess"]["ci95"][0])
    diff = R.excess.mean() - by["MAINTAIN"].excess.mean() if len(by["MAINTAIN"]) else -1.0
    check("RAISE - MAINTAIN excess", diff, res["contrasts"].get("RAISE_minus_MAINTAIN_excess", {}).get("diff", -1.0))

    # account A, rebuilt: 10% of the equity marked at the previous close, 10 slots, 20-session exit, USD 2 per order
    def account(key):
        cash, book, curve = 10_000.0, [], {}
        order = R.sort_values("acceptance_ny")
        start = {}
        for r in order.itertuples():
            start.setdefault(r.entry_date, []).append(getattr(r, key))
        first = pos[min(start)]
        for d in range(first, len(dates)):
            mark = cash + sum(b["sh"] * b["last"] for b in book)
            for t in start.get(dates[d], []):
                px = wide["open"][t].iloc[d]
                size = 0.10 * mark
                if len(book) >= 10 or size + 2 > cash or not np.isfinite(px):
                    continue
                cash -= size + 2
                book.append({"t": t, "sh": size * (1 - tier(px * wide["unit_factor"][t].iloc[d])) / px,
                             "x": d + HOLD - 1, "last": px})
            still = []
            for b in book:
                px = wide["close"][b["t"]].iloc[d]
                if b["x"] == d:
                    cash += b["sh"] * px * (1 - tier(px * wide["unit_factor"][b["t"]].iloc[d]) - SEC_FEE) - 2
                    continue
                if np.isfinite(px):
                    b["last"] = px
                still.append(b)
            book = still
            curve[d] = cash + sum(b["sh"] * b["last"] for b in book)
        return curve[len(dates) - 1]

    a_end, sh_end = account("ticker"), account("shadow_ticker")
    check("account A end equity", a_end, res["accounts"]["A"]["end_equity"], 1e-6)
    check("shadow A end equity", sh_end, res["accounts"]["A_shadow"]["end_equity"], 1e-6)

    gates = {
        "G1_raise_excess_ci_above_zero": ci_lo > 0,
        "G2_raise_mean_and_clipped_net_positive": bool(R.net.mean() > 0 and clipped > 0),
        "G3_raise_beats_maintain": bool(diff > 0),
        "G4_stress_net_positive": bool(R.net_stress.mean() > 0),
        "G5_excess_positive_every_year": all(v > 0 for v in years.values()),
        "G6_account_A_beats_start_and_shadow": bool(a_end > 10_000.0 and a_end > sh_end),
    }
    for k, v in gates.items():
        check(k, v, res["gates"][k])
    check("verdict", "PASS" if all(gates.values()) else "FAIL", res["verdict"])
    print("VERIFIED" if not bad else f"MISMATCH: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
