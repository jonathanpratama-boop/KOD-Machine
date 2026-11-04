"""AVOID_TILT_v1 runner (see PROTOCOL.md). Run once: python3 research/AVOID_TILT_v1/run.py (from idx-signals/)."""
import glob, hashlib, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "results"
if (OUT / "RESULT.json").exists():
    sys.exit("error: results exist; this study runs once")
HP = ROOT / "data/raw/yahoo_us_history/20261030T095328Z"
COST, SEED, B = 0.002, 20261102, 5000
DISC, HOLD = ("2020-07-01", "2023-12-31"), ("2024-01-01", "2026-10-31")

# ---------- prices -> wide matrices (date x ticker)
adj, close, vol = {}, {}, {}
for f in sorted(glob.glob(str(HP / "*.json"))):
    t = os.path.basename(f).split(".")[0]
    try:
        d = json.load(open(f))["chart"]["result"][0]
        ts = d.get("timestamp") or []
        q = d["indicators"]["quote"][0]
        a = (d["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    except Exception:
        continue
    if not ts or not a:
        continue
    idx = pd.to_datetime(np.array(ts), unit="s").normalize()
    s_adj = pd.Series(np.array(a, float), index=idx)
    s_cl = pd.Series(np.array(q["close"], float), index=idx)
    s_v = pd.Series(np.array(q["volume"], float), index=idx)
    keep = ~s_adj.index.duplicated(keep="last")
    adj[t], close[t], vol[t] = s_adj[keep], s_cl[keep], s_v[keep]
ADJ = pd.DataFrame(adj).sort_index(); CL = pd.DataFrame(close).reindex(ADJ.index); VO = pd.DataFrame(vol).reindex(ADJ.index)
ADJ = ADJ.where(ADJ > 0)
RET = ADJ.pct_change(fill_method=None)
DV = (CL * VO)
print("tickers", ADJ.shape[1], "days", ADJ.shape[0], ADJ.index.min().date(), ADJ.index.max().date())

# ---------- dilution flags (8-K item 3.02 filing dates)
fil = pd.read_csv(ROOT / "research/US_8K_ITEMS/filings8k.csv.gz", dtype={"ticker": str, "items": str},
                  keep_default_na=False, na_values=[""])
fil = fil[fil["items"].fillna("").str.contains(r"\b3\.02\b")]
fil["filing_date"] = pd.to_datetime(fil["filing_date"])
dil = fil.groupby("ticker")["filing_date"].apply(lambda s: np.sort(s.values)).to_dict()

# ---------- monthly rebalance
days = ADJ.index
months = pd.Series(days).groupby(pd.Series(days).dt.to_period("M")).first()
rebal = [d for d in months.values if days.get_loc(d) >= 60]
rows, prevw = [], {"A": pd.Series(dtype=float), "B": pd.Series(dtype=float)}
for k in range(len(rebal) - 1):
    d0, d1 = pd.Timestamp(rebal[k]), pd.Timestamp(rebal[k + 1])
    i0 = days.get_loc(d0)
    prev = days[i0 - 1]
    hist = ADJ.iloc[:i0].notna().sum()
    medv = DV.iloc[i0 - 20:i0].median()
    elig = (CL.loc[prev] >= 5) & (medv >= 1e6) & (hist >= 60) & ADJ.loc[prev].notna()
    names = elig[elig].index
    spike = (RET.iloc[i0 - 20:i0][names] >= 0.30).any()
    dflag = pd.Series(False, index=names)
    for t in names:
        arr = dil.get(t)
        if arr is not None:
            lo = np.datetime64(d0 - pd.Timedelta(days=90)); hi = np.datetime64(d0)
            dflag[t] = bool(((arr >= lo) & (arr < hi)).any())
    excl = spike | dflag
    # holding-period return: buy at prev close-equivalent (rebalance uses adj close of prev day) to the day before d1
    j1 = days.get_loc(d1) - 1
    r = ADJ.iloc[j1][names] / ADJ.loc[prev][names] - 1
    r = r.fillna(0.0)  # name stops trading inside the month: counted flat (survivor data rarely has these)
    res = {"start": d0.date().isoformat(), "n_A": len(names), "n_excl": int(excl.sum()),
           "n_spike": int(spike.sum()), "n_dil": int(dflag.sum())}
    for arm, sel in (("A", names), ("B", names[~excl.values])):
        w = pd.Series(1.0 / len(sel), index=sel) if len(sel) else pd.Series(dtype=float)
        turn = (w.reindex(w.index.union(prevw[arm].index), fill_value=0)
                - prevw[arm].reindex(w.index.union(prevw[arm].index), fill_value=0)).abs().sum()
        gross = float((w * r.reindex(sel)).sum())
        res[f"{arm}_gross"], res[f"{arm}_turn"], res[f"{arm}_net"] = gross, float(turn), gross - COST * float(turn)
        # drift weights to end of month for next turnover calc
        grown = w * (1 + r.reindex(sel))
        prevw[arm] = grown / grown.sum() if grown.sum() else w
    res["excl_ret"] = float(r[excl.values].mean()) if excl.any() else None
    res["kept_ret"] = float(r[~excl.values].mean())
    rows.append(res)
M = pd.DataFrame(rows); M["start"] = pd.to_datetime(M["start"]); M["diff"] = M.B_net - M.A_net

def stats(x):
    x = np.asarray(x, float); ann = (1 + x).prod() ** (12 / len(x)) - 1
    v = x.std(ddof=1) * np.sqrt(12); eq = np.cumprod(1 + x); dd = float((1 - eq / np.maximum.accumulate(eq)).max())
    return {"months": len(x), "ann_return": float(ann), "ann_vol": float(v), "sharpe": float(x.mean() * 12 / v) if v else None,
            "max_drawdown": dd}

def boot_lb(x):
    rng = np.random.default_rng(SEED); x = np.asarray(x, float)
    return float(np.percentile([rng.choice(x, len(x)).mean() for _ in range(B)], 5))

out = {"study": "AVOID_TILT_v1", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "periods": {}}
for name, (a, b) in (("discovery", DISC), ("holdout", HOLD)):
    P = M[(M.start >= a) & (M.start <= b)]
    out["periods"][name] = {
        "A": stats(P.A_net), "B": stats(P.B_net),
        "diff_mean_monthly": float(P["diff"].mean()), "diff_lb95": boot_lb(P["diff"]),
        "share_months_B_beats_A": float((P["diff"] > 0).mean()),
        "avg_names_A": float(P.n_A.mean()), "avg_excluded": float(P.n_excl.mean()),
        "avg_spike_excl": float(P.n_spike.mean()), "avg_dil_excl": float(P.n_dil.mean()),
        "excluded_next_month_mean": float(P.excl_ret.dropna().mean()), "kept_next_month_mean": float(P.kept_ret.mean()),
        "by_year_diff": {str(y): float(g["diff"].sum()) for y, g in P.groupby(P.start.dt.year)},
    }
h = out["periods"]["holdout"]
out["verdict"] = ("PASS: excluding KOD-flagged names beat the market portfolio in the holdout, net of costs"
                  if h["diff_mean_monthly"] > 0 and h["diff_lb95"] > 0 and h["B"]["ann_return"] > 0
                  else "FAIL: the exclusion tilt did not clear the frozen bar in the holdout")
OUT.mkdir(exist_ok=True)
M.to_csv(OUT / "monthly.csv", index=False)
(OUT / "RESULT.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))
