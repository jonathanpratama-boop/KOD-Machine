"""(v2: events are keyed by cik and accession, because a joint filing has one accession and several issuers; the first version reported two false "missing" events) Independent check of results_stage<N>/ with its own code (no import of idxsig, run.py or tenk_*): the input hashes, the buckets recomputed from similarity.csv.gz, and for every scored
trade of the primary hold the entry session (the first session strictly after the filing date), the entry open, the exit session (the first tradeable session at or after entry + hold) and
close, and the net return from the two prices, the as-traded cost tiers and the sale fee; then the Q5 and Q1 means, the spread, an analytic week-cluster t against the bootstrap t, and the gates.
The matched-control means come from the harness (idxsig.controls, tested separately); the draws themselves are not recomputed.
Usage (from idx-signals/): python3 research/SLOW_10K/verify.py --stage 1     (exit 1 if anything differs)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FEE_BUY, FEE_SELL = 0.0, 0.0000278
TIERS = [(1.0, 0.015), (5.0, 0.005), (20.0, 0.0015), (float("inf"), 0.0005)]
END = "2023-12-29"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tier(price: float) -> float:
    for bound, cost in TIERS:
        if price < bound:                       # searchsorted(bounds, price, side="right"): a price equal to a bound falls in the next tier
            return cost
    return TIERS[-1][1]


def tier_exact(price: float) -> float:
    bounds = np.array([b for b, _ in TIERS])
    return TIERS[int(np.searchsorted(bounds, price, side="right").clip(0, len(TIERS) - 1))][1]


def buckets(sim: pd.DataFrame) -> pd.Series:
    d = pd.to_datetime(sim["filing_date"]).to_numpy("datetime64[D]")
    c = sim["cosine"].to_numpy(float)
    ok = np.isfinite(c)
    out = np.full(len(sim), "", dtype=object)
    for i in np.flatnonzero(ok):
        w = ok & (d < d[i]) & (d >= d[i] - np.timedelta64(365, "D"))
        if w.sum() >= 200:
            lo, hi = np.percentile(c[w], [20, 80])
            out[i] = "Q1" if c[i] <= lo else "Q5" if c[i] >= hi else "MID"
    return pd.Series(out, index=sim.index)


def check_trades(ev: pd.DataFrame, pfile: Path, hold: int) -> tuple[int, float, list]:
    """Recompute every EXITED trade of `ev` from the panel file: entry session, entry open, exit session and close, and the net return."""
    bad = []
    px = pd.read_csv(pfile, usecols=["date", "ticker", "open", "close", "volume", "unit_factor"], parse_dates=["date"], dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    px = px[px.date <= END]
    dates = np.array(sorted(px.date.unique()), dtype="datetime64[D]")
    by_ticker = {t: g.set_index(g.date.to_numpy().astype("datetime64[D]")) for t, g in px[px.ticker.isin(set(ev.ticker))].groupby("ticker")}
    n_checked, worst = 0, 0.0
    for r in ev[ev.status == "EXITED"].itertuples():
        g = by_ticker[r.ticker]
        e = int(np.searchsorted(dates, np.datetime64(r.public_date, "D"), side="right"))
        if str(dates[e]) != r.entry_date:
            bad.append(f"entry session {r.ticker} {r.public_date}")
            continue
        x = e + hold
        while x < len(dates):
            row = g.loc[dates[x]] if dates[x] in g.index else None
            if row is not None and row.volume > 0 and row.close > 0:
                break
            x += 1
        if x >= len(dates) or str(dates[x]) != r.exit_date:
            bad.append(f"exit session {r.ticker} {r.public_date}")
            continue
        o, c = float(g.loc[dates[e]].open), float(g.loc[dates[x]].close)
        if abs(o - r.entry_price) > 1e-9 * max(o, 1) or abs(c - r.exit_price) > 1e-9 * max(c, 1):
            bad.append(f"prices {r.ticker} {r.public_date}")
            continue
        te, tx = tier_exact(o * float(g.loc[dates[e]].unit_factor)), tier_exact(c * float(g.loc[dates[x]].unit_factor))
        net = (c / o) * (1 - FEE_SELL - tx) / (1 + FEE_BUY + te) - 1
        worst = max(worst, abs(net - r.net_return))
        if abs(net - r.net_return) > 1e-9:
            bad.append(f"net return {r.ticker} {r.public_date}: {net:.6f} vs {r.net_return:.6f}")
        n_checked += 1
    return n_checked, worst, bad


def week(entry: pd.Series) -> np.ndarray:
    iso = pd.to_datetime(entry).dt.isocalendar()
    return (iso.year.astype(int) * 100 + iso.week.astype(int)).to_numpy()


def spread_t(q5: pd.DataFrame, q1: pd.DataFrame) -> tuple[float, float]:
    """Spread of mean excess and its cluster-robust t (clusters = entry weeks)."""
    x5, x1 = q5.excess.to_numpy(), q1.excess.to_numpy()
    n5, n1 = len(x5), len(x1)
    mu5, mu1 = x5.mean(), x1.mean()
    contrib = {}
    for w, v in zip(week(q5.entry_date), x5 - mu5):
        contrib[w] = contrib.get(w, 0.0) + v / n5
    for w, v in zip(week(q1.entry_date), x1 - mu1):
        contrib[w] = contrib.get(w, 0.0) - v / n1
    se = float(np.sqrt(sum(c * c for c in contrib.values())))
    return float(mu5 - mu1), float((mu5 - mu1) / se)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2))
    stage = ap.parse_args().stage
    bad = []
    d = HERE / f"results_stage{stage}"
    res = json.loads((d / "RESULT.json").read_text())
    ev = pd.read_csv(d / "events.csv", dtype={"accession": str})
    pins = json.loads((HERE / "PINS.json").read_text())
    for name, p in (("events_csv", "events.csv"), ("similarity_csv", "similarity.csv.gz"), ("filings_csv", "filings.csv.gz")):
        if sha(HERE / p) != pins[name] or res["inputs"][name] != pins[name]:
            bad.append(f"{p} hash")
    pm = json.loads((ROOT / "data/manifests/panel_us_repair-20261008T114805Z.json").read_text())
    pfile = ROOT / pm["panel"]
    if sha(pfile) != pm["sha256"] or pm["sha256"] != res["inputs"]["panel"]:
        bad.append("panel hash")

    # 1. buckets from the similarities
    sim = pd.read_csv(HERE / "similarity.csv.gz", dtype={"accession": str})
    sim = sim[(sim.http_status == 200) & sim.cosine.notna()].sort_values(["filing_date", "cik", "accession"]).reset_index(drop=True)
    sim["bucket"] = buckets(sim)
    inp = pd.read_csv(HERE / "events.csv", dtype={"accession": str})
    inp = inp[inp.stage == stage]
    sim["key"] = sim.cik.astype(str) + "|" + sim.accession                 # a joint filing has one accession and several issuers
    inp = inp.assign(key=inp.cik.astype(str) + "|" + inp.accession)
    mine = sim[sim.bucket != ""].set_index("key").bucket
    got = inp.set_index("key").bucket
    both = got.index.intersection(mine.index)
    if (got.loc[both] != mine.loc[both]).any() or len(both) != len(got):
        bad.append(f"buckets differ: {(got.loc[both] != mine.loc[both]).sum()} of {len(both)}, {len(got) - len(both)} missing")
    if not set(ev.accession) <= set(inp.accession):
        bad.append("results contain events not in the input table")

    # 2. trades from the panel
    n_checked, worst, trade_bad = check_trades(ev, pfile, res["primary_hold"])
    bad += trade_bad

    # 3. statistics and gates
    f = ev[ev.net_return.notna() & ev.control_mean.notna()]
    if (abs(f.excess - (f.net_return - f.control_mean)) > 1e-12).any():
        bad.append("excess != net - control mean")
    exited_with_control = ev[(ev.status == "EXITED") & (ev.control_n > 0)]
    if len(f) != len(exited_with_control) or exited_with_control.control_mean.isna().any():
        bad.append("scored count != EXITED with a scored control")
    q5, q1 = f[f.bucket == "Q5"], f[f.bucket == "Q1"]
    sp, t_an = spread_t(q5, q1)
    s = res["spread"]
    for k, (a, b) in {"spread": (sp, s["spread"]), "n5": (len(q5), s["n5"]), "n1": (len(q1), s["n1"])}.items():
        if abs(a - b) > 1e-9:
            bad.append(f"{k} {a} vs {b}")
    if abs(t_an - s["t"]) > 0.2 * abs(s["t"]) + 0.15:
        bad.append(f"bootstrap t {s['t']:.3f} vs analytic {t_an:.3f}")
    if stage == 1:
        yrs = {}
        for y in ("2021", "2022"):
            a, b = q5[q5.entry_date.str[:4] == y], q1[q1.entry_date.str[:4] == y]
            yrs[y] = len(a) >= 200 and len(b) >= 200 and a.excess.mean() - b.excess.mean() > 0
        gates = {"G1_spread_t_ge_3": bool(sp > 0 and s["t"] >= 3.0), "G2_spread_ge_3pct": bool(sp >= 0.03), "G3_spread_gt_0_in_2021_and_2022": bool(all(yrs.values())),
                 "G4_shuffled_labels_all_abs_t_lt_3": bool(max(abs(t) for t in res["shuffled_label_t"]) < 3.0)}
    else:
        gates = {"G1p_spread_t_ge_1.65": bool(sp > 0 and s["t"] >= 1.65), "G2p_spread_ge_1.5pct": bool(sp >= 0.015)}
    bad += [k for k, v in gates.items() if v != res["gates"][k]]
    verdict = "PASS" if all(gates.values()) else "FAIL"
    if verdict != res["verdict"]:
        bad.append("verdict")
    print(json.dumps({"stage": stage, "trades_recomputed_from_the_panel": n_checked, "max_abs_net_return_difference": worst, "scored": int(len(f)), "q5": len(q5), "q1": len(q1),
                      "spread": sp, "analytic_t": t_an, "bootstrap_t": s["t"], "gates": gates, "mismatches": bad, "verdict": verdict}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
