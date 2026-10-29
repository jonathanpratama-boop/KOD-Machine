"""gate_power2.py (2026-10-29): gate_power.py's reporting corrected after the independent review.

Same simulated learner and the real v2.2 gate code, but: (1) every quantile is over ALL runs, with a run that never
opened counted as infinite, so a median is ">160" unless at least half of the runs opened; (2) the no-skill null is
the fair one (the learner moves its forecasts as much as a skilled one, on noise unrelated to the outcome), 200 runs,
reported with the one-sided 95% upper bound on the false-open probability (Clopper-Pearson); (3) the full
stopping-time distribution is written to gate_power2.json. A design read; it reads no market data.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from idxsig.learner2 import gate_path  # noqa: E402


def sig(x):
    return 1 / (1 + np.exp(-x))


def weekly(per_week, s, weeks, seed, p0=0.3, n0=400, null=False, s_move=0.6):
    rng = np.random.default_rng(seed)
    a0 = math.log(p0 / (1 - p0))
    d, n = [], 0
    for _ in range(weeks):
        z = rng.standard_normal(per_week)
        p = sig(a0 + 0.3 * rng.standard_normal() + s * z)
        y = (rng.random(per_week) < p).astype(float)
        share = n / (n + n0)
        dev = share * s_move * rng.standard_normal(per_week) if null else share * s * z
        f = sig(a0 + dev)
        a = sig(a0)
        d.append(float(np.mean((a - y) ** 2 - (f - y) ** 2)))
        n += per_week
    return np.array(d)


def first_open(d):
    for i, (_, opened, _) in enumerate(gate_path(d, 1, 1)):
        if opened:
            return 30 + i
    return math.inf


def upper95(k, n):
    """One-sided 95% Clopper-Pearson upper bound on a proportion with k of n."""
    if k == n:
        return 1.0
    lo, hi = k / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        # P(X <= k | p = mid)
        cdf = sum(math.comb(n, j) * mid ** j * (1 - mid) ** (n - j) for j in range(k + 1))
        lo, hi = (lo, mid) if cdf < 0.05 else (mid, hi)
    return hi


W, R, NULL_R = 160, 40, 200
out = {"weeks": W, "runs_per_cell": R, "null_runs": NULL_R, "null": {}, "skill": {}}
print("Fair null (forecasts moved on noise), share of runs ever open in 160 weeks, with the 95% upper bound:")
for pw in (20, 50, 150):
    stops = [first_open(weekly(pw, 0.0, W, 5000 + k, null=True)) for k in range(NULL_R)]
    k = sum(1 for t in stops if t < math.inf)
    out["null"][pw] = {"opened": k, "upper95": upper95(k, NULL_R), "stops": [t if t < math.inf else None for t in stops]}
    print(f"  {pw:>3}/wk: {k}/{NULL_R} opened ({k / NULL_R:.1%}; upper bound {upper95(k, NULL_R):.1%})")
print("Real skill: share of ALL runs open by week 30 / 52 / 78 / 104 / 160, and the all-run median")
for s, auc in ((0.25, 0.569), (0.4, 0.609), (0.6, 0.658), (0.9, 0.722)):
    out["skill"][auc] = {}
    row = []
    for pw in (20, 50, 150):
        stops = sorted(first_open(weekly(pw, s, W, k)) for k in range(R))
        med = stops[R // 2]
        shares = [sum(1 for t in stops if t <= w) / R for w in (30, 52, 78, 104, 160)]
        out["skill"][auc][pw] = {"stops": [t if t < math.inf else None for t in stops], "median_all_runs": med if med < math.inf else None,
                                 "share_by_week": dict(zip((30, 52, 78, 104, 160), shares))}
        row.append(f"{pw:>3}/wk " + "/".join(f"{x:.0%}" for x in shares) + f" med {med if med < math.inf else '>160'}")
    print(f"  AUC {auc:.2f}  " + " | ".join(row))
(Path(__file__).resolve().parent / "gate_power2.json").write_text(json.dumps(out, indent=1) + "\n")
