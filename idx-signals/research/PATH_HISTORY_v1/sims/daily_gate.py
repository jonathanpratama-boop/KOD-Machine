"""Speedrun check 3: next-session statements scored in daily blocks (one observation per market day; a 1-session
window shares no market day with another day's), through v2.2's own confidence sequence and hysteresis, with the
minimum number of observations t_min varied. Null: the learner moves its forecasts on noise. Each day shares a market
shock (sd 0.3 logit). Rare (p0 0.15, like RUN30) and common (p0 0.40, like FADE10) statements."""
import math, sys
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from idxsig.learner2 import confidence_lowers, long_run_sd

def sig(x): return 1 / (1 + np.exp(-x))

def days(per_day, s, n_days, seed, p0, null=False, n0=400, s_move=0.6):
    rng = np.random.default_rng(seed); a0 = math.log(p0/(1-p0)); d, n = [], 0
    for _ in range(n_days):
        k = max(1, rng.poisson(per_day))
        z = rng.standard_normal(k); p = sig(a0 + 0.3*rng.standard_normal() + s*z)
        y = (rng.random(k) < p).astype(float); share = n/(n+n0)
        dev = share*s_move*rng.standard_normal(k) if null else share*s*z
        f = sig(a0 + dev); a = sig(a0)
        d.append(float(np.mean((a-y)**2 - (f-y)**2))); n += k
    return np.array(d)

def open_day(d, t_min, t_star=252, n_recent=252, z_open=1.645, z_stay=0.842, lag=0):
    lowers = confidence_lowers(d, lag, t_star=t_star)
    best, opened = -math.inf, False
    for t in range(t_min - 1, len(d)):
        best = max(best, float(lowers[t]))
        rec = d[max(0, t + 1 - n_recent): t + 1]
        se = long_run_sd(rec, lag) / math.sqrt(len(rec))
        opened = best > 0 and float(rec.mean() - (z_stay if opened else z_open) * se) > 0
        if opened: return t + 1
    return None

N = 504  # two years of sessions
for p0 in (0.15, 0.40):
    print(f"p0 {p0}: null false-open share over 2 years (200 runs), by t_min")
    for pd_ in (10, 30):
        ds = [days(pd_, 0.0, N, 9000+k, p0, null=True) for k in range(200)]
        print(f"   {pd_}/day  " + "  ".join(f"t_min {tm}: {sum(open_day(d, tm) is not None for d in ds)/200:5.1%}" for tm in (30, 20, 12)))
    print(f"p0 {p0}: real skill, median sessions to open (40 runs), t_min 30 / 20")
    for s, auc in ((0.4, .61), (0.6, .66), (0.9, .72)):
        row = []
        for pd_ in (10, 30):
            ds = [days(pd_, s, N, k, p0) for k in range(40)]
            meds = []
            for tm in (30, 20):
                got = sorted(x for x in (open_day(d, tm) for d in ds) if x)
                meds.append(str(got[len(got)//2]) if len(got) >= 20 else ">504")
            row.append(f"{pd_}/day {meds[0]:>4} / {meds[1]:>4}")
        print(f"   AUC {auc:.2f}  " + " | ".join(row))
