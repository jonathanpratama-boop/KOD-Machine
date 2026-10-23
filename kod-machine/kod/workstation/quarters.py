"""Quarterly and trailing-twelve-month series with accounting semantics.

- A quarter reported as a three-month figure is used as reported.
- A missing quarter may be derived as the difference of two year-to-date figures with the same start date (6M - 3M, 9M - 6M, 12M - 9M) only for an additive
  flow (catalog `additive`), with the same basis, unit, scale, currency and context, and only when both inputs are usable. The derivation is a calculation with
  both inputs recorded and is labelled as derived.
- Per-share amounts, share counts and ratios are never derived by subtraction (Q4 diluted EPS is not annual EPS minus nine-month EPS), and instants are never
  summed.
- TTM is the sum of four contiguous, non-overlapping quarters of an additive flow; a gap or overlap leaves it unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .calculations import CalculationResult
from .financials import ResolvedFigure, duration_kind
from .identity import METRIC_CATALOG_V1

ADDITIVE = {m for m, _, kind, additive, *_ in METRIC_CATALOG_V1 if kind == "flow" and additive}
KIND = {m: kind for m, _, kind, *_ in METRIC_CATALOG_V1}


@dataclass(frozen=True, slots=True)
class Quarter:
    start: str
    end: str
    value: Decimal | None
    status: str                  # reported | derived | conflicted | not_derivable
    figure: ResolvedFigure | None
    calculation: CalculationResult | None
    reasons: tuple

    @property
    def input_ids(self):
        if self.calculation:
            return self.calculation.input_ids
        return self.figure.observation_ids if self.figure else ()


def _day(text):
    return date.fromisoformat(text)


def _compatible(a: ResolvedFigure, b: ResolvedFigure) -> list:
    reasons = []
    for field in ("metric", "basis", "unit", "scale", "currency", "context"):
        if getattr(a, field) != getattr(b, field):
            reasons.append(f"{field} differs ({getattr(a, field)} vs {getattr(b, field)})")
    return reasons


def quarterly(figures: list, metric: str, check=None) -> list:
    """Discrete quarters for one metric from resolved duration figures (one basis/unit/currency group per call is the caller's choice; mixed groups are
    never combined). Returns Quarter records sorted by end date. `check(shorter, longer)` may return reasons the two year-to-date figures must not be
    differenced (for example, one was restated and the other was not: different accounting vintages)."""
    own = [f for f in figures if f.metric == metric and f.period.start_date and f.period.end_date]
    quarters = {}
    for f in own:
        if f.period.kind == "quarter":
            key = (f.period.start_date, f.period.end_date)
            quarters[key] = Quarter(*key, f.value, "reported" if f.status == "ok" else "conflicted", f, None, f.reasons)
    if metric not in ADDITIVE:
        return sorted(quarters.values(), key=lambda q: q.end)
    by_start = {}
    for f in own:
        if f.period.kind in ("quarter", "6 months", "9 months", "12 months"):
            by_start.setdefault(f.period.start_date, []).append(f)
    for start, group in by_start.items():
        group.sort(key=lambda f: f.period.end_date)
        for shorter, longer in zip(group, group[1:]):
            q_start = (_day(shorter.period.end_date) + timedelta(days=1)).isoformat()
            q_end = longer.period.end_date
            if duration_kind(q_start, q_end) != "quarter" or (q_start, q_end) in quarters:
                continue
            reasons = _compatible(shorter, longer) + (list(check(shorter, longer)) if check else [])
            inputs = tuple(("year_to_date_" + role, "observation", oid) for role, f in (("longer", longer), ("shorter", shorter)) for oid in f.observation_ids)
            if shorter.status != "ok" or longer.status != "ok":
                calc = CalculationResult("quarter_from_ytd_difference", "ytd-difference-v1", "conflicted", None, longer.unit, inputs, (),
                                         ("a year-to-date input is conflicted",))
                quarters[(q_start, q_end)] = Quarter(q_start, q_end, None, "conflicted", None, calc, calc.reasons)
                continue
            if reasons:
                calc = CalculationResult("quarter_from_ytd_difference", "ytd-difference-v1", "incompatible", None, longer.unit, inputs, (), tuple(reasons))
                quarters[(q_start, q_end)] = Quarter(q_start, q_end, None, "not_derivable", None, calc, calc.reasons)
                continue
            calc = CalculationResult("quarter_from_ytd_difference", "ytd-difference-v1", "ok", longer.value - shorter.value, longer.unit, inputs, (), (),
                                     {"longer": f"{longer.period.kind} ended {longer.period.end_date}", "shorter": f"{shorter.period.kind} ended {shorter.period.end_date}",
                                      "formula": f"{longer.period.kind} minus {shorter.period.kind}, same start {start}"})
            quarters[(q_start, q_end)] = Quarter(q_start, q_end, calc.value, "derived", None, calc, ())
    return sorted(quarters.values(), key=lambda q: q.end)


def not_derivable_reason(metric: str):
    kind = KIND.get(metric)
    if metric in ADDITIVE:
        return None
    if kind == "per_share":
        return "per-share amounts are not additive: a quarter is never derived by subtracting year-to-date figures"
    if kind == "count":
        return "share counts (weighted averages) are not additive"
    if kind == "instant":
        return "balances at a date are not flows and are never summed or differenced into quarters"
    return "this measure is not an additive flow"


def ttm(quarters: list, end: str, metric: str) -> CalculationResult:
    """Sum of the four contiguous quarters ending on `end` for an additive flow."""
    unit = quarters[0].figure.unit if quarters and quarters[0].figure else "currency"
    reason = not_derivable_reason(metric)
    if reason:
        return CalculationResult("ttm", "ttm-v1", "not_applicable", None, unit, (), (), (reason,))
    chain, cursor = [], end
    by_end = {q.end: q for q in quarters}
    for _ in range(4):
        q = by_end.get(cursor)
        if q is None:
            return CalculationResult("ttm", "ttm-v1", "missing", None, unit, tuple(_ttm_inputs(chain)), (), (f"no quarter ending {cursor}",))
        if q.value is None:
            return CalculationResult("ttm", "ttm-v1", "conflicted" if q.status == "conflicted" else "missing", None, unit, tuple(_ttm_inputs(chain + [q])), (),
                                     (f"the quarter ending {cursor} is {q.status}",))
        chain.append(q)
        cursor = (_day(q.start) - timedelta(days=1)).isoformat()
    starts = [q.start for q in chain]
    if len(set(starts)) != 4:
        return CalculationResult("ttm", "ttm-v1", "invalid", None, unit, tuple(_ttm_inputs(chain)), (), ("the quarters overlap",))
    total = sum((q.value for q in chain), Decimal(0))
    return CalculationResult("ttm", "ttm-v1", "ok", total, unit, tuple(_ttm_inputs(chain)), (), (),
                             {"quarters": [f"{q.start}..{q.end} ({q.status})" for q in reversed(chain)]})


def _ttm_inputs(chain):
    for i, q in enumerate(chain):
        if q.calculation is not None:
            for role, kind, iid in q.calculation.inputs:
                yield (f"q{i + 1}_{role}", kind, iid)
        elif q.figure is not None:
            for oid in q.figure.observation_ids:
                yield (f"q{i + 1}", "observation", oid)
