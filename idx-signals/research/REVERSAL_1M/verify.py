"""Independent check of results/RESULT.json from results/monthly.csv, with its own Newey-West and regression code (no
import of idxsig.quant). Exit 1 if anything differs by more than 1e-9 or a gate disagrees.
Usage (from idx-signals/): python3 research/REVERSAL_1M/verify.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / "results"
COLS = ["Mkt-RF", "SMB", "HML", "MOM"]


def nw_t_mean(x, lags=6):
    x = np.asarray(x, float)
    n, e = len(x), x - x.mean()
    gamma = np.correlate(e, e, "full")[n - 1:] / n
    lrv = gamma[0] + 2 * sum((1 - k / (lags + 1)) * gamma[k] for k in range(1, lags + 1))
    return x.mean() / np.sqrt(lrv / n)


def hac_alpha(y, F, lags=6):
    n = len(y)
    X = np.column_stack([np.ones(n), F])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    Z = X * (y - X @ beta)[:, None]
    idx = np.arange(n)
    W = np.clip(1 - np.abs(idx[:, None] - idx[None, :]) / (lags + 1), 0, None)
    A = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(A @ (Z.T @ W @ Z) @ A))
    return beta[0], beta[0] / se[0]


def main() -> int:
    res = json.loads((R / "RESULT.json").read_text())
    m = pd.read_csv(R / "monthly.csv", dtype={"month": str}).set_index("month")
    if (m.index >= "2024-01").any():
        print("FAIL: sealed months present"); return 1
    w = m[(m.index >= "2005-01") & (m.index <= "2019-12")]
    o = m[(m.index >= "2020-01") & (m.index <= "2023-12")]
    mean, t = w["ST_Rev"].mean(), nw_t_mean(w["ST_Rev"])
    a, at = hac_alpha(w["ST_Rev"].to_numpy(), w[COLS].to_numpy())
    checks = {"n": (len(w), res["main_2005_2019"]["n"]), "mean": (mean, res["main_2005_2019"]["mean"]),
              "t_nw": (t, res["main_2005_2019"]["t_nw"]), "alpha": (a, res["alpha_2005_2019"]["alpha"]),
              "alpha_t": (at, res["alpha_2005_2019"]["alpha_t"]), "oos_mean": (o["ST_Rev"].mean(), res["oos_2020_2023"]["mean"])}
    gates = {"G1_mean_t_nw_ge_3": mean > 0 and t >= 3.0, "G2_alpha_t_nw_ge_3": a > 0 and at >= 3.0,
             "G3_mean_minus_0.80pct_gt_0": mean - 0.008 > 0, "G4_oos_2020_2023_mean_gt_0": o["ST_Rev"].mean() > 0}
    bad = [k for k, (x, y) in checks.items() if abs(x - y) > 1e-9]
    bad += [k for k, v in gates.items() if bool(v) != res["gates"][k]]
    verdict = "PASS" if all(gates.values()) else "FAIL"
    if verdict != res["verdict"]:
        bad.append("verdict")
    print(json.dumps({"checked": list(checks) + list(gates), "mismatches": bad, "verdict": verdict}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
