"""Speedrun check, v2: an exact betting gate with a range known before the outcomes.
Each pair's Brier gain g = (a-y)^2 - (f-y)^2 can take only two values, both known when the forecast is sealed, so a
week's bound B_w = sum max|g| is known in advance and x_w = sum g / B_w lies in [-1, 1] exactly. Two e-processes, on
odd and on even weeks (5-session windows of alternate weeks share no market days), each bets lam in [0, 0.9] chosen
from its own past (aGRAPA) and opens at wealth 40 (alpha 2.5% each, 5% together, Ville's inequality, any number of
looks, no minimum sample).
Null: the learner moves its forecasts as much as a skilled one, on noise unrelated to the outcome."""
import math, sys
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from idxsig.learner2 import gate_path

def sig(x): return 1 / (1 + np.exp(-x))

def weeks_data(per_week, s, weeks, seed, null=False, p0=0.3, n0=400, s_move=0.6):
    rng = np.random.default_rng(seed); a0 = math.log(p0/(1-p0)); out, n = [], 0
    for w in range(weeks):
        z = rng.standard_normal(per_week); p = sig(a0 + 0.3*rng.standard_normal() + s*z)
        y = (rng.random(per_week) < p).astype(float)
        share = n/(n+n0)
        dev = share*s_move*rng.standard_normal(per_week) if null else share*s*z
        f = sig(a0 + dev); a = np.full(per_week, sig(a0))
        g = (a-y)**2 - (f-y)**2
        gmax = np.maximum(np.abs((f-a)*(-a-f)), np.abs((f-a)*(2-a-f)))
        out.append((float(g.mean()), float(g.sum()), float(gmax.sum()))); n += per_week
    return out

def bet_open(data, thresh=40.0):
    best = None
    for parity in (0, 1):
        logk, xs = 0.0, []
        for t, (_, S, B) in enumerate(data):
            if t % 2 != parity or B <= 0: continue
            x = S / B
            if len(xs) >= 2:
                m, v = float(np.mean(xs)), float(np.var(xs)) + 1e-6
                lam = min(max(m / (v + m*m), 0.0), 0.9)
            else:
                lam = 0.0
            logk += math.log1p(lam * x); xs.append(x)
            if logk >= math.log(thresh):
                best = t + 1 if best is None else min(best, t + 1); break
    return best

def v22_open(data):
    d = np.array([o[0] for o in data])
    for i, (_, opened, _) in enumerate(gate_path(d, 1, 1)):
        if opened: return 30 + i
    return None

W = 160
print("Null (learner moves forecasts on noise), share of 200 runs that ever opened in 160 weeks:")
for pw in (20, 50, 150):
    ds = [weeks_data(pw, 0.0, W, 5000+k, null=True) for k in range(200)]
    print(f"  {pw:>3}/wk  v2.2 gate {sum(v22_open(d) is not None for d in ds)/200:5.1%}   betting gate {sum(bet_open(d) is not None for d in ds)/200:5.1%}")
print("Real skill, median weeks to open (40 runs; share open by week 26):")
for s, auc in ((0.25, .569), (0.4, .609), (0.6, .658), (0.9, .722)):
    row = []
    for pw in (20, 50, 150):
        ds = [weeks_data(pw, s, W, k) for k in range(40)]
        a = [v22_open(d) for d in ds]; b = [bet_open(d) for d in ds]
        def med(xs):
            got = sorted(x for x in xs if x)
            return got[len(got)//2] if len(got) >= 20 else ">160"
        row.append(f"{pw:>3}/wk {med(a)!s:>4} vs {med(b)!s:>4} ({sum(1 for x in b if x and x <= 26)/40:.0%})")
    print(f"  AUC {auc:.2f}  " + " | ".join(row))
