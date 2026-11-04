"""Weeks until the real v2.2 gate opens, for a learner with a given true edge (AUC) at a given weekly volume.
Idealised learner: it captures a share n/(n+n0) of the true signal after n resolved pairs (it must learn it live).
Each week shares a market shock (sd 0.3 logit) that the anchor cannot know. Pairs within a set are not modelled
as correlated; volumes are per gate, after the once-per-event dedupe."""
import math, sys
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from idxsig.learner2 import gate_path

def sig(x): return 1 / (1 + np.exp(-x))

def run(per_week, s, p0=0.3, weeks=160, n0=400, seed=0, lag=1):
    rng = np.random.default_rng(seed)
    a0 = math.log(p0 / (1 - p0))
    d, n = [], 0
    for w in range(weeks):
        z = rng.standard_normal(per_week)
        shock = 0.3 * rng.standard_normal()
        p = sig(a0 + shock + s * z)
        y = rng.random(per_week) < p
        share = n / (n + n0)
        f = sig(a0 + share * s * z)
        a = np.full(per_week, sig(a0))
        d.append(float(np.mean((a - y) ** 2 - (f - y) ** 2)))
        n += per_week
    path = gate_path(np.array(d), 1, lag)
    for i, (best, opened, _) in enumerate(path):
        if opened:
            return 29 + i + 1
    return None

def auc(s, p0=0.3, m=200000, seed=1):
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(m); y = rng.random(m) < sig(math.log(p0/(1-p0)) + s*z)
    r = np.argsort(np.argsort(z)) + 1
    n1 = y.sum(); return (r[y].sum() - n1*(n1+1)/2) / (n1*(m-n1))

print("signal_sd  AUC   | per_week: median weeks to open (share opened by week 52 / 104)")
for s in (0.0, 0.25, 0.4, 0.6, 0.9):
    row = [f"{s:4.2f}  {auc(s):.3f}"]
    for pw in (20, 50, 150):
        ws = [run(pw, s, seed=k) for k in range(40)]
        got = sorted(w for w in ws if w is not None)
        med = got[len(got)//2] if len(got) >= 20 else None
        row.append(f"{pw:>3}/wk: {str(med) if med else '>160':>4} ({sum(1 for w in ws if w and w<=52)/40:.0%}/{sum(1 for w in ws if w and w<=104)/40:.0%})")
    print(" | ".join(row))
