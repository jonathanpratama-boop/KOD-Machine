"""Multiple-testing tools for the project's trial register (research/QUANT_GRADE).

Every number here answers one question: given how many things we have tried, how big must the next result be before
it is distinguishable from the best of many noise results? Pure functions, stdlib only.
"""
from __future__ import annotations

from statistics import NormalDist

N01 = NormalDist()


def p_one_sided(effect: float, se: float) -> float:
    """P(Z >= effect/se): the one-sided p-value for a claimed positive effect."""
    return 1.0 - N01.cdf(effect / se)


def se_from_ci95(low: float, high: float) -> float:
    """Standard error implied by a published 95% interval under a normal approximation."""
    return (high - low) / (2 * 1.959964)


def p_from_t(t: float) -> float:
    return 1.0 - N01.cdf(t)


def holm(pvals: list[float]) -> list[float]:
    """Holm step-down adjusted p-values (family-wise error control), in the input order."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj, running = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def benjamini_hochberg(pvals: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values (false-discovery-rate control), in the input order."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i], reverse=True)
    adj, running = [0.0] * m, 1.0
    for k, i in enumerate(order):
        rank = m - k
        running = min(running, pvals[i] * m / rank)
        adj[i] = min(1.0, running)
    return adj


def hurdle_z(n_tests: int, alpha: float = 0.05, method: str = "bonferroni") -> float:
    """One-sided z a single result must reach to hold family-wise error at `alpha` over `n_tests` tries."""
    if n_tests < 1:
        raise ValueError("n_tests must be >= 1")
    if method == "bonferroni":
        return N01.inv_cdf(1 - alpha / n_tests)
    if method == "sidak":
        return N01.inv_cdf((1 - alpha) ** (1 / n_tests))
    raise ValueError(method)


def expected_max_z(n_tests: int) -> float:
    """Approximate expected best z among n independent pure-noise tests (Blom's approximation)."""
    return N01.inv_cdf((n_tests - 0.375) / (n_tests + 0.25))


def project_hurdle(n_tests: int, floor: float = 3.0, alpha: float = 0.05) -> float:
    """The t-statistic a future primary result must clear: the larger of the Harvey-Liu-Zhu style floor (3.0) and the
    Bonferroni bar for the number of tests tried so far plus this one."""
    return max(floor, hurdle_z(n_tests + 1, alpha))
