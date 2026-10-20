"""Independent check of results/RESULT.json from results/monthly.csv, with its own Newey-West and regression code (no
import of idxsig.quant): IC and spread statistics, factor alpha, net spread at each book size, break-even, gates.
Usage (from idx-signals/): python3 research/QUANT_ENGINE_2005_2019/verify.py   (exit 1 if anything differs by > 1e-9)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "results"


def nw_t_mean(x, lags=6):
    x = np.asarray(x, float)
    n, e = len(x), x - x.mean()
    gamma = np.correlate(e, e, "full")[n - 1:] / n                      # autocovariances at lags 0..n-1
    lrv = gamma[0] + 2 * sum((1 - k / (lags + 1)) * gamma[k] for k in range(1, lags + 1))
    return x.mean() / np.sqrt(lrv / n)


def hac_alpha(y, F, lags=6):
    n = len(y)
    X = np.column_stack([np.ones(n), F])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    Z = X * (y - X @ beta)[:, None]
    idx = np.arange(n)
    W = np.clip(1 - np.abs(idx[:, None] - idx[None, :]) / (lags + 1), 0, None)       # Bartlett weights, zero past `lags`
    S = Z.T @ W @ Z
    A = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(A @ S @ A))
    return beta[0], beta[0] / se[0]


def main() -> int:
    res = json.loads((R / "RESULT.json").read_text())
    m = pd.read_csv(R / "monthly.csv")
    bad = []

    def check(name, mine, theirs, tol=1e-9):
        ok = (mine == theirs) if isinstance(mine, (bool, str)) else abs(float(mine) - float(theirs)) <= tol
        print(f"{'ok ' if ok else 'BAD'} {name}: {mine} vs {theirs}")
        if not ok:
            bad.append(name)

    check("months", len(m), res["months"])
    check("mean IC", m.ic.mean(), res["ic_combined"]["mean"])
    check("IC t (NW6)", nw_t_mean(m.ic), res["ic_combined"]["t_nw"])
    yrs = m.groupby(m.formed.str[:4]).ic.mean()
    check("IC years positive", int((yrs > 0).sum()), res["ic_combined"]["years_positive"])
    check("large-half IC t (NW6)", nw_t_mean(m.ic_large), res["ic_large_half"]["t_nw"])
    check("mean spread", m.spread.mean(), res["spread_gross"]["mean"])
    check("spread = q5 - q1", float(np.abs(m.spread - (m.q5 - m.q1)).max()), 0.0)
    a, at = hac_alpha(m.spread.to_numpy(), m[["f_mkt-rf", "f_smb", "f_hml", "f_mom"]].to_numpy())
    check("factor alpha", a, res["factor_alpha_of_spread"]["alpha"])
    check("factor alpha t", at, res["factor_alpha_of_spread"]["alpha_t"])
    nets = {}
    for aum in (1e4, 1e5, 1e6, 1e7, 1e8):
        pos = aum / (2 * m.n_leg)
        cl = 0.0005 + 0.7 * m.vol_long * np.sqrt(pos / m.adv_long)
        cs = 0.0005 + 0.7 * m.vol_short * np.sqrt(pos / m.adv_short)
        nets[aum] = float((m.spread - 2 * m.tau_long * cl - 2 * m.tau_short * cs).mean())
        check(f"net spread at {int(aum)}", nets[aum], res["net_spread_mean_monthly_by_aum"][str(int(aum))])
    g = {"G1_ic_t_ge_3_and_9_of_12_years": bool(m.ic.mean() > 0 and nw_t_mean(m.ic) >= 3.0 and (yrs > 0).sum() >= 9),
         "G2_net_spread_positive_at_100k": bool(nets[1e5] > 0),
         "G3_factor_alpha_t_ge_3": bool(a > 0 and at >= 3.0),
         "G4_large_cap_ic_t_ge_2": bool(m.ic_large.mean() > 0 and nw_t_mean(m.ic_large) >= 2.0)}
    for k, v in g.items():
        check(k, v, res["gates"][k])
    check("all_pass", all(g.values()), res["all_pass"])
    print("VERIFIED" if not bad else f"MISMATCH: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
