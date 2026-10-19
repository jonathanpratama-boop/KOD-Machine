"""The single recorded test of PROTOCOL.md. Reads data/raw/yahoo_us_2005/*.json.gz, writes results/{RESULT.json,monthly.csv}.
Refuses a second run. Usage (from idx-signals/): python3 research/US_LOWVOL_MOM_2005_2019/run.py
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = ROOT / "data" / "raw" / "yahoo_us_2005"
OUT = HERE / "results"
MIN_DOLLAR_VOL, MIN_HISTORY, MIN_STOCKS = 2e6, 252, 300
CLIP = (-0.9, 2.0)
COST = 0.003
T_BAR, YEARS_BAR = 2.4, 10


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    adj, cl, vol = {}, {}, {}
    for f in sorted(RAW.glob("*.json.gz")):
        t = f.name[:-8]
        res = (json.loads(gzip.decompress(f.read_bytes()))["chart"]["result"] or [None])[0]
        if not res or not res.get("timestamp"):
            continue
        idx = pd.to_datetime(res["timestamp"], unit="s").normalize()
        q, a = res["indicators"]["quote"][0], res["indicators"].get("adjclose", [{}])[0].get("adjclose")
        if a is None:
            continue
        keep = ~idx.duplicated()
        adj[t] = pd.Series(a, index=idx)[keep]
        cl[t] = pd.Series(q["close"], index=idx)[keep]
        vol[t] = pd.Series(q["volume"], index=idx)[keep]
    frame = lambda d: pd.DataFrame(d).sort_index().loc[:"2019-12-31"]  # noqa: E731
    return frame(adj), frame(cl), frame(vol)


def monthly(adj: pd.DataFrame, cl: pd.DataFrame, vol: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """One row per month-end formation: quintile mean forward returns for volatility and momentum rankings."""
    dates = adj.index
    A, C, V = adj.to_numpy(float), cl.to_numpy(float), vol.to_numpy(float)
    lr = np.diff(np.log(A), axis=0, prepend=np.nan)
    dv = C * V
    month_end = [i for i in range(len(dates) - 1) if dates[i].month != dates[i + 1].month]
    rows, skipped = [], 0
    for k, t in enumerate(month_end[:-1]):
        if t < MIN_HISTORY or dates[t] < pd.Timestamp("2005-01-01"):
            continue
        t_next, entry = month_end[k + 1], t + 1
        mom = A[t - 21] / A[t - 252] - 1
        sd = np.nanstd(lr[t - 59:t + 1], axis=0)
        med = np.nanmedian(dv[t - 59:t + 1], axis=0)
        hist = np.isfinite(A[t - 252:t + 1]).sum(axis=0)
        fwd = np.clip(A[t_next] / A[entry] - 1, *CLIP)
        ok = np.isfinite(mom) & np.isfinite(sd) & (sd > 0) & np.isfinite(fwd) & (med >= MIN_DOLLAR_VOL) & (hist >= MIN_HISTORY)
        idx = np.flatnonzero(ok)
        if len(idx) < MIN_STOCKS:
            skipped += 1
            continue
        row = {"formed": dates[t].strftime("%Y-%m-%d"), "n": len(idx), "universe": fwd[idx].mean()}
        for name, x in (("lowvol", -sd), ("mom", mom)):
            order = idx[np.argsort(x[idx], kind="stable")]
            k5 = len(order) // 5
            for q in range(5):
                row[f"{name}{q + 1}"] = fwd[order[q * k5:(q + 1) * k5 if q < 4 else len(order)]].mean()
        rows.append(row)
    return pd.DataFrame(rows), skipped


def verdicts(m: pd.DataFrame) -> dict:
    m = m.copy()
    m["year"] = m.formed.str[:4]
    series = {"H1_lowvol_Q5_minus_Q1": m.lowvol5 - m.lowvol1, "H2_momentum_Q5_minus_Q1": m.mom5 - m.mom1,
              "H3_universe_minus_wildest_Q1": m.universe - m.lowvol1}
    out = {}
    for name, s in series.items():
        t = float(s.mean() / (s.std(ddof=1) / np.sqrt(len(s))))
        by_year = s.groupby(m.year).mean()
        pos = int((by_year > 0).sum())
        out[name] = {"months": int(len(s)), "mean_monthly": float(s.mean()), "t": t, "years_positive": pos,
                     "years": int(len(by_year)), "pass": bool(s.mean() > 0 and t >= T_BAR and pos >= YEARS_BAR)}
    long_only = (m.lowvol5 - m.universe - COST)
    out["descriptive"] = {"calm_Q5_minus_universe_gross_monthly": float((m.lowvol5 - m.universe).mean()),
                          "calm_Q5_minus_universe_net_of_30bp_monthly": float(long_only.mean()),
                          "mean_monthly_by_quintile_lowvol": [float(m[f"lowvol{q}"].mean()) for q in range(1, 6)],
                          "mean_monthly_by_quintile_mom": [float(m[f"mom{q}"].mean()) for q in range(1, 6)],
                          "universe_mean_monthly": float(m.universe.mean()), "mean_eligible_stocks": float(m.n.mean()),
                          "by_period": {p: {"H1": float((s := (m.lowvol5 - m.lowvol1)[m.year.between(*p.split('-'))]).mean()),
                                            "H2": float((m.mom5 - m.mom1)[m.year.between(*p.split('-'))].mean())}
                                        for p in ("2005-2009", "2010-2019")}}
    return out


def main() -> int:
    if (OUT / "RESULT.json").exists():
        sys.exit("refused: the recorded run already exists")
    adj, cl, vol = load()
    m, skipped = monthly(adj, cl, vol)
    OUT.mkdir(exist_ok=True)
    m.to_csv(OUT / "monthly.csv", index=False)
    res = {"experiment": "US low-vol and momentum 2005-2019 (PROTOCOL.md), run once", "tickers_with_data": int(adj.shape[1]),
           "months": int(len(m)), "months_skipped_too_few_stocks": skipped, "verdicts": verdicts(m),
           "limits": ["survivor-only universe (today's listings)", "no as-traded price floor", "one era, 2005-2019",
                      "gross returns for the gates; long-only net reading is descriptive"]}
    res["all_pass"] = all(res["verdicts"][h]["pass"] for h in ("H1_lowvol_Q5_minus_Q1", "H2_momentum_Q5_minus_Q1",
                                                                  "H3_universe_minus_wildest_Q1"))
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
