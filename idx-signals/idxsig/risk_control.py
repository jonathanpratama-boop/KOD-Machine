"""Certified calls: Learn then Test (Angelopoulos, Bates, Candes, Jordan, Lei, arXiv 2110.01052) for one calling rule.

The machine makes a call on an event when its score clears a threshold. On resolved calibration events this module finds
the thresholds whose losing rate (the share of wrong calls among the calls made) is at most alpha, with family-wise error
at most delta over every threshold tried: each threshold's null "losing rate > alpha" gets an exact binomial p-value, and
the thresholds are tested in a fixed order, strictest first, stopping at the first that fails (fixed-sequence testing,
valid whatever the shape of the losing rate across thresholds). Pure functions, stdlib only.

The guarantee assumes calibration and future calls are exchangeable; markets drift, so a certificate is checked against
the realised losing rate on later events, never taken on trust.
"""

from __future__ import annotations

from math import exp, lgamma, log


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(Bin(n, p) <= k), exactly (summed in log space)."""
    if k < 0:
        return 0.0
    if k >= n or p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    lp, lq, total = log(p), log(1.0 - p), 0.0
    for i in range(k + 1):
        total += exp(lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1) + i * lp + (n - i) * lq)
    return min(1.0, total)


def p_value(losses: int, calls: int, alpha: float) -> float:
    """Exact p-value for the null "losing rate > alpha" after `losses` wrong calls in `calls` calls."""
    return 1.0 if calls == 0 else binom_cdf(losses, calls, alpha)


def certify(
    scores: list[float],
    wrong: list[int],
    thresholds: list[float],
    alpha: float,
    delta: float,
    min_calls: int = 1,
) -> dict:
    """Fixed-sequence Learn then Test. `thresholds` are tried in the order given (strictest first); a call is made when
    score >= threshold; `wrong[i]` is 1 when the call on event i would have been wrong. Returns every tested threshold
    with its calls, losses and p-value, the certified ones, and the certified threshold that makes the most calls."""
    rows, certified = [], []
    for t in thresholds:
        sel = [w for s, w in zip(scores, wrong) if s >= t]
        n, k = len(sel), int(sum(sel))
        p = p_value(k, n, alpha) if n >= min_calls else 1.0
        rows.append({"threshold": t, "calls": n, "losses": k, "p": p})
        if p > delta:
            break
        certified.append(t)
    best = None
    if certified:
        best = max(certified, key=lambda t: (sum(1 for s in scores if s >= t), -t))
    return {"tested": rows, "certified": certified, "chosen": best}


def realised(scores: list[float], wrong: list[int], threshold: float | None, alpha: float) -> dict:
    """The certificate's check on later events: calls, losing rate, and the one-sided p-value that the true losing rate
    exceeds alpha (small = the certificate is broken)."""
    if threshold is None:
        return {"calls": 0, "losses": 0, "losing_rate": None, "p_exceeds_alpha": None}
    sel = [w for s, w in zip(scores, wrong) if s >= threshold]
    n, k = len(sel), int(sum(sel))
    p_exceeds = None if n == 0 else 1.0 - binom_cdf(k - 1, n, alpha)
    return {
        "calls": n,
        "losses": k,
        "losing_rate": (k / n if n else None),
        "p_exceeds_alpha": p_exceeds,
    }
