"""Independent check of results_stage<N>/ with its own code (no import of idxsig, run.py or ib_*): the input hashes; the event table rebuilt from the Form 4 extract and the CIK map
(own implementation of the protocol's rules); for every scored trade of every hold the entry session (the first session strictly after the filing date), the entry open, the exit session
(the first tradeable session at or after entry + hold) and close, and the net return from the two prices, the as-traded cost tiers and the sale fee; then the mean excess, an analytic
week-cluster t against the bootstrap t, the winsorised mean and the gates. The matched-control means come from the harness (idxsig.controls, tested separately); the draws themselves
are not recomputed.
Usage (from idx-signals/): python3 research/US_INSIDER_BUY/verify.py --stage 1     (exit 1 if anything differs)
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FEE_SELL = 0.0000278
TIERS = [(1.0, 0.015), (5.0, 0.005), (20.0, 0.0015), (float("inf"), 0.0005)]
END = "2023-12-29"
HOLDS = (20, 60, 120)
STAGES = {1: ("2021-01-04", "2022-12-30"), 2: ("2023-01-03", "2023-09-29")}
MIN_VALUE, CHAIN_DAYS, CHAIN_START = 50_000.0, 90, "2020-07-01"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tier_exact(price: float) -> float:
    bounds = np.array([b for b, _ in TIERS])
    return TIERS[int(np.searchsorted(bounds, price, side="right").clip(0, len(TIERS) - 1))][1]


def rebuild(extract: pd.DataFrame, cikmap: dict) -> pd.DataFrame:
    """Events from the Form 4 purchase lines: per filing the total value and the owner flags; officer or director, no 10b5-1 flag, total >= 50,000, an issuer with a ticker, then the
    90-day chain per issuer in filing-date order; staged by filing date."""
    x = extract.copy()
    x["flag"] = x["aff10b5one"].fillna("").astype(str).str.strip().str.upper().isin({"1", "TRUE", "Y", "YES"})
    g = x.groupby("accession").agg(filing_date=("filing_date", "first"), cik=("issuer_cik", "first"), total=("value", "sum"), off=("officer", "max"), dr=("director", "max"),
                                   flag=("flag", "max")).reset_index()
    g = g[(g.off | g.dr) & ~g.flag & (g.total >= MIN_VALUE) & (g.filing_date >= CHAIN_START) & g.cik.isin(set(cikmap))]
    g = g.sort_values(["filing_date", "cik", "accession"])
    last, rows = {}, []
    for acc, d, cik in zip(g.accession, g.filing_date, g.cik):
        dd = date.fromisoformat(d)
        if cik not in last or (dd - last[cik]).days >= CHAIN_DAYS:
            last[cik] = dd
            stage = next((k for k, (a, b) in STAGES.items() if a <= d <= b), 0)
            if stage:
                rows.append({"accession": acc, "ticker": cikmap[cik], "public_date": d, "stage": stage})
    return pd.DataFrame(rows)


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
        net = (c / o) * (1 - FEE_SELL - tx) / (1 + te) - 1
        worst = max(worst, abs(net - r.net_return))
        if abs(net - r.net_return) > 1e-9:
            bad.append(f"net return {r.ticker} {r.public_date}: {net:.6f} vs {r.net_return:.6f}")
        n_checked += 1
    return n_checked, worst, bad


def week(entry: pd.Series) -> np.ndarray:
    iso = pd.to_datetime(entry).dt.isocalendar()
    return (iso.year.astype(int) * 100 + iso.week.astype(int)).to_numpy()


def analytic_t(x: np.ndarray, w: np.ndarray) -> float:
    """t of a mean with week-cluster robust standard error."""
    mu, n = x.mean(), len(x)
    by = {}
    for v, k in zip(x - mu, w):
        by[k] = by.get(k, 0.0) + v
    return float(mu / (np.sqrt(sum(c * c for c in by.values())) / n))


def scored(ev: pd.DataFrame) -> pd.DataFrame:
    return ev[ev.net_return.notna() & ev.control_mean.notna()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2))
    stage = ap.parse_args().stage
    bad = []
    d = HERE / f"results_stage{stage}"
    res = json.loads((d / "RESULT.json").read_text())
    pins = json.loads((HERE / "PINS.json").read_text())
    for name, p in (("events_csv", HERE / "events.csv"), ("form4_csv", HERE / "form4_purchases.csv.gz"), ("filings_csv", HERE.parent / "SLOW_10K" / "filings.csv.gz")):
        if sha(p) != pins[name] or res["inputs"][name] != pins[name]:
            bad.append(f"{p.name} hash")
    pm = json.loads((ROOT / "data/manifests/panel_us_repair-20261008T114805Z.json").read_text())
    pfile = ROOT / pm["panel"]
    if sha(pfile) != pm["sha256"] or pm["sha256"] != res["inputs"]["panel"]:
        bad.append("panel hash")

    # 1. the events from the extract
    ext = pd.read_csv(HERE / "form4_purchases.csv.gz", dtype={"accession": str, "aff10b5one": str, "symbol": str}, keep_default_na=False, na_values=[""])
    fl = pd.read_csv(HERE.parent / "SLOW_10K" / "filings.csv.gz", usecols=["cik", "ticker"], dtype={"ticker": str}, keep_default_na=False).drop_duplicates("cik")
    mine = rebuild(ext, dict(zip(fl.cik.astype(int), fl.ticker)))
    inp = pd.read_csv(HERE / "events.csv", dtype={"accession": str})
    a, b = mine.set_index("accession").sort_index(), inp.set_index("accession").sort_index()
    if list(a.index) != list(b.index) or (a.ticker != b.ticker).any() or (a.public_date != b.public_date).any() or (a.stage != b.stage).any():
        bad.append(f"events differ: {len(a)} rebuilt vs {len(b)} in events.csv")
    inp = inp[inp.stage == stage]

    # 2. trades from the panel, every hold
    n_checked, worst, per_hold = {}, 0.0, {}
    for h in HOLDS:
        ev = pd.read_csv(d / f"events_hold{h}.csv", dtype={"accession": str})
        if not set(ev.accession) <= set(inp.accession):
            bad.append(f"hold {h}: events not in the input table")
        n, w, tb = check_trades(ev, pfile, h)
        n_checked[h], worst = n, max(worst, w)
        bad += [f"hold {h}: {m}" for m in tb]
        f = scored(ev)
        if (abs(f.excess - (f.net_return - f.control_mean)) > 1e-12).any():
            bad.append(f"hold {h}: excess != net - control mean")
        ex = ev[(ev.status == "EXITED") & (ev.control_n > 0)]
        if len(f) != len(ex) or ex.control_mean.isna().any():
            bad.append(f"hold {h}: scored count != EXITED with a scored control")
        per_hold[h] = f

    # 3. statistics and gates
    f = per_hold[60]
    x, w = f.excess.to_numpy(), week(f.entry_date)
    mean, t_an = float(x.mean()), analytic_t(x, w)
    lo, hi = np.percentile(x, [1, 99])
    wins = float(np.clip(x, lo, hi).mean())
    s = res["excess"]
    for k, (u, v) in {"mean": (mean, s["mean"]), "n": (len(f), s["n"]), "winsorised": (wins, res["winsorised_mean_excess"])}.items():
        if abs(u - v) > 1e-9:
            bad.append(f"{k} {u} vs {v}")
    for h in HOLDS:
        if abs(per_hold[h].excess.mean() - res["holds"][str(h)]["excess"]["mean"]) > 1e-9:
            bad.append(f"hold {h} mean excess")
    if abs(t_an - s["t"]) > 0.2 * abs(s["t"]) + 0.15:
        bad.append(f"bootstrap t {s['t']:.3f} vs analytic {t_an:.3f}")
    if stage == 1:
        yrs = {y: (int((f.entry_date.str[:4] == y).sum()), float(f[f.entry_date.str[:4] == y].excess.mean()) if (f.entry_date.str[:4] == y).any() else None) for y in ("2021", "2022")}
        gates = {"G1_excess_t_ge_3": bool(mean > 0 and s["t"] >= 3.0), "G2_excess_ge_2pct_and_winsorised_ge_1pct": bool(mean >= 0.02 and wins >= 0.01),
                 "G3_excess_gt_0_in_2021_and_2022": bool(all(n >= 300 and m is not None and m > 0 for n, m in yrs.values())),
                 "G4_excess_gt_0_at_holds_20_and_120": bool(per_hold[20].excess.mean() > 0 and per_hold[120].excess.mean() > 0)}
    else:
        gates = {"G1p_excess_t_ge_1.65": bool(mean > 0 and s["t"] >= 1.65), "G2p_excess_ge_1pct": bool(mean >= 0.01)}
    bad += [k for k, v in gates.items() if v != res["gates"][k]]
    verdict = "PASS" if all(gates.values()) else "FAIL"
    if verdict != res["verdict"]:
        bad.append("verdict")
    print(json.dumps({"stage": stage, "events_rebuilt": int(len(mine)), "trades_recomputed_from_the_panel": n_checked, "max_abs_net_return_difference": worst, "scored": int(len(f)),
                      "mean_excess": mean, "winsorised": wins, "analytic_t": t_an, "bootstrap_t": s["t"], "gates": gates, "mismatches": bad, "verdict": verdict}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
