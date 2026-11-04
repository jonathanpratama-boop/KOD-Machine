"""Post-run robustness for AVOID_TILT_v1 (NOT part of the frozen verdict). Same engine as run.py, with variants:
 V0 frozen rules (sanity: must match RESULT.json); V1 drop names whose spike day was >= +100% (likely data errors) from
 the exclusion test; V2 large/liquid only (median $vol >= $20m); V3 only the 500 most liquid names; plus excluded-group
 median and top-5 dependence, and benchmarks SPY / RSP / IWM over the same months."""
import glob, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path("/home/user/KOD-Machine/idx-signals")
HP = ROOT / "data/raw/yahoo_us_history/20261030T095328Z"
BENCH = Path(__file__).resolve().parent
COST = 0.002
adj, close, vol = {}, {}, {}
for f in sorted(glob.glob(str(HP / "*.json"))):
    t = os.path.basename(f).split(".")[0]
    try:
        d = json.load(open(f))["chart"]["result"][0]; ts = d.get("timestamp") or []; q = d["indicators"]["quote"][0]
        a = (d["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    except Exception:
        continue
    if not ts or not a:
        continue
    idx = pd.to_datetime(np.array(ts), unit="s").normalize()
    k = ~pd.Index(idx).duplicated(keep="last")
    adj[t] = pd.Series(np.array(a, float), index=idx)[k]; close[t] = pd.Series(np.array(q["close"], float), index=idx)[k]
    vol[t] = pd.Series(np.array(q["volume"], float), index=idx)[k]
ADJ = pd.DataFrame(adj).sort_index(); CL = pd.DataFrame(close).reindex(ADJ.index); VO = pd.DataFrame(vol).reindex(ADJ.index)
ADJ = ADJ.where(ADJ > 0); RET = ADJ.pct_change(fill_method=None); DV = CL * VO
fil = pd.read_csv(ROOT / "research/US_8K_ITEMS/filings8k.csv.gz", dtype={"ticker": str, "items": str}, keep_default_na=False, na_values=[""])
fil = fil[fil["items"].fillna("").str.contains(r"\b3\.02\b")]; fil["filing_date"] = pd.to_datetime(fil["filing_date"])
dil = fil.groupby("ticker")["filing_date"].apply(lambda s: np.sort(s.values)).to_dict()
days = ADJ.index
months = pd.Series(days).groupby(pd.Series(days).dt.to_period("M")).first()
rebal = [d for d in months.values if days.get_loc(d) >= 60]

def bench_month(t, d0, d1):
    d = json.load(open(BENCH / f"{t}.json"))["chart"]["result"][0]
    s = pd.Series(d["indicators"]["adjclose"][0]["adjclose"], index=pd.to_datetime(d["timestamp"], unit="s").normalize())
    return s

BS = {t: bench_month(t, None, None) for t in ("SPY", "RSP", "IWM")}

def run(variant):
    rows, prevw = [], {"A": pd.Series(dtype=float), "B": pd.Series(dtype=float)}
    for k in range(len(rebal) - 1):
        d0, d1 = pd.Timestamp(rebal[k]), pd.Timestamp(rebal[k + 1]); i0 = days.get_loc(d0); prev = days[i0 - 1]
        hist = ADJ.iloc[:i0].notna().sum(); medv = DV.iloc[i0 - 20:i0].median()
        minv = 2e7 if variant == "V2" else 1e6
        elig = (CL.loc[prev] >= 5) & (medv >= minv) & (hist >= 60) & ADJ.loc[prev].notna()
        names = elig[elig].index
        if variant == "V3":
            names = medv[names].sort_values(ascending=False).index[:500]
        win = RET.iloc[i0 - 20:i0][names]
        spike = (win >= 0.30).any()
        if variant == "V1":
            bad = (win >= 1.00).any()
            names = names[~bad.values]; spike = spike[~bad.values]
        dflag = pd.Series(False, index=names)
        for t in names:
            arr = dil.get(t)
            if arr is not None:
                lo, hi = np.datetime64(d0 - pd.Timedelta(days=90)), np.datetime64(d0)
                dflag[t] = bool(((arr >= lo) & (arr < hi)).any())
        excl = spike.reindex(names).fillna(False) | dflag
        j1 = days.get_loc(d1) - 1
        r = (ADJ.iloc[j1][names] / ADJ.loc[prev][names] - 1).fillna(0.0)
        res = {"start": d0, "n_A": len(names), "n_excl": int(excl.sum())}
        for arm, sel in (("A", names), ("B", names[~excl.values])):
            w = pd.Series(1.0 / len(sel), index=sel)
            u = w.index.union(prevw[arm].index)
            turn = (w.reindex(u, fill_value=0) - prevw[arm].reindex(u, fill_value=0)).abs().sum()
            res[f"{arm}_net"] = float((w * r.reindex(sel)).sum()) - COST * float(turn)
            g = w * (1 + r.reindex(sel)); prevw[arm] = g / g.sum()
        ex = r[excl.values]
        res["excl_mean"] = float(ex.mean()) if len(ex) else np.nan
        res["excl_median"] = float(ex.median()) if len(ex) else np.nan
        res["excl_sum_wo_top5_worst"] = float(ex.sort_values().iloc[5:].mean()) if len(ex) > 5 else np.nan
        for b, s in BS.items():
            a0 = s.asof(prev); a1 = s.asof(days[j1])
            res[b] = float(a1 / a0 - 1)
        rows.append(res)
    M = pd.DataFrame(rows); M["diff"] = M.B_net - M.A_net
    return M

def ann(x):
    x = np.asarray(x, float); return float((1 + x).prod() ** (12 / len(x)) - 1)

out = {}
for v in ("V0", "V1", "V2", "V3"):
    M = run(v)
    for name, (a, b) in (("discovery", ("2020-07-01", "2023-12-31")), ("holdout", ("2024-01-01", "2026-10-31"))):
        P = M[(M.start >= a) & (M.start <= b)]
        rng = np.random.default_rng(1); bs = [rng.choice(P["diff"].values, len(P)).mean() for _ in range(5000)]
        out[f"{v}_{name}"] = {"A_ann": ann(P.A_net), "B_ann": ann(P.B_net), "diff_monthly": float(P["diff"].mean()),
                              "diff_lb95": float(np.percentile(bs, 5)), "months_B_wins": float((P["diff"] > 0).mean()),
                              "avg_names": float(P.n_A.mean()), "avg_excl": float(P.n_excl.mean()),
                              "excl_mean": float(P.excl_mean.mean()), "excl_median": float(P.excl_median.mean()),
                              "excl_mean_wo_5_worst": float(P.excl_sum_wo_top5_worst.mean()),
                              "SPY_ann": ann(P.SPY), "RSP_ann": ann(P.RSP), "IWM_ann": ann(P.IWM)}
print(json.dumps(out, indent=1))
json.dump(out, open(BENCH / "robust_result.json", "w"), indent=1)
