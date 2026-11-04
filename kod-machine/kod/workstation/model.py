"""One transparent annual driver model for ordinary operating companies (KOD-FCFF-v1), its sensitivity grid and a conditional reverse valuation.

Every number comes from an explicit, versioned assumption set the analyst reviewed; history may suggest starting values (suggest_from_history) but never
fills a forecast silently. The formulation, in the order it is computed:

    Revenue[t]   = Revenue[t-1] * (1 + growth[t])                       t = 1..N, Revenue[0] = base revenue (a stated fiscal year)
    EBIT[t]      = Revenue[t] * operating_margin[t]
    Taxes[t]     = max(EBIT[t], 0) * cash_tax_rate[t]                   (losses earn no tax credit in this model; declared, not hidden)
    NOPAT[t]     = EBIT[t] - Taxes[t]
    D&A[t]       = Revenue[t] * depreciation_rate[t]
    Capex[t]     = Revenue[t] * capex_rate[t]                           (a nonnegative investment amount)
    dNWC[t]      = (Revenue[t] - Revenue[t-1]) * nwc_rate[t]            (positive consumes cash)
    FCFF[t]      = NOPAT[t] + D&A[t] - Capex[t] - dNWC[t]
    DF[t]        = 1 / (1 + discount_rate) ** t                         (end-of-year discounting)
    TV[N]        = NOPAT[N] * (1 + g) * (1 - g / terminal_roic) / (discount_rate - g)
                   (value-driver perpetuity: reinvestment g / terminal_roic of NOPAT; needs discount_rate > g and terminal_roic > 0)
    EV           = sum(FCFF[t] * DF[t]) + TV[N] * DF[N]
    Equity       = EV + cash - debt - other_senior_claims + other_adjustments
    Per share    = Equity / share_count                                 (only with a complete, dated, same-currency bridge and an analyst-selected count)

Banks, insurers and REITs are outside this model (model-not-applicable). Unsupported complexity (leases, stock compensation, convertibles, minority
interests, tax losses) must be given a declared treatment; 'not modelled' is allowed and stays visible as a limitation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, localcontext
import re

MODEL = "KOD-FCFF-v1"
PRECISION = 34
VECTOR = (
    "revenue_growth",
    "operating_margin",
    "cash_tax_rate",
    "depreciation_rate",
    "capex_rate",
    "nwc_rate",
)
SCALAR = ("discount_rate", "terminal_growth", "terminal_roic")
BRIDGE = ("cash", "debt", "other_senior_claims", "other_adjustments")
TREATMENTS = {
    "stock_compensation": ("expensed_in_margin", "dilution_in_share_count", "not_modelled"),
    "leases": ("operating_cost_in_margin", "included_in_debt", "not_modelled"),
    "convertibles": (
        "none_outstanding",
        "included_in_debt",
        "dilution_in_share_count",
        "not_modelled",
    ),
    "noncontrolling_interests": ("none", "in_other_senior_claims", "not_modelled"),
    "tax_losses": ("none_material", "no_credit_assumed", "not_modelled"),
}
LIMITS = {  # (low, high) inclusive bounds on each rate, as fractions; outside them the input is refused, not clipped
    "revenue_growth": (Decimal("-0.95"), Decimal("5")),
    "operating_margin": (Decimal("-2"), Decimal("1")),
    "cash_tax_rate": (Decimal("0"), Decimal("1")),
    "depreciation_rate": (Decimal("0"), Decimal("1")),
    "capex_rate": (Decimal("0"), Decimal("2")),
    "nwc_rate": (Decimal("-2"), Decimal("2")),
    "discount_rate": (Decimal("0.001"), Decimal("1")),
    "terminal_growth": (Decimal("-0.5"), Decimal("0.2")),
    "terminal_roic": (Decimal("0.001"), Decimal("10")),
}
LABELS = {
    "revenue_growth": "Revenue growth",
    "operating_margin": "Operating margin",
    "cash_tax_rate": "Cash tax rate",
    "depreciation_rate": "D&A / revenue",
    "capex_rate": "Capex / revenue",
    "nwc_rate": "Working capital / revenue change",
    "discount_rate": "Discount rate (WACC)",
    "terminal_growth": "Terminal growth",
    "terminal_roic": "Return on new invested capital (terminal)",
}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CURRENCY = re.compile(r"^[A-Z]{3}$")


class AssumptionError(ValueError):
    """An assumption set that cannot be run, with every problem listed."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def _dec(value, name, problems):
    if isinstance(value, bool) or value is None or value == "":
        problems.append(f"{name} is required")
        return None
    if isinstance(value, float):
        problems.append(f"{name} must be given as text or an integer, not a binary float")
        return None
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        problems.append(f"{name} is not a number: {value!r}")
        return None
    if not d.is_finite():
        problems.append(f"{name} must be finite")
        return None
    return d


@dataclass(frozen=True)
class Assumptions:
    """A validated assumption set. Rates are fractions (0.25 = 25%)."""

    horizon: int
    base_year_end: str
    base_revenue: Decimal
    currency: str
    valuation_date: str
    vectors: dict
    discount_rate: Decimal
    terminal_growth: Decimal
    terminal_roic: Decimal
    bridge: dict  # name -> Decimal or None (missing)
    bridge_date: str | None
    share_count: Decimal | None
    share_count_date: str | None
    share_count_basis: str | None
    treatments: dict
    sources: dict = field(default_factory=dict)

    def value(self, name):
        return self.vectors[name] if name in self.vectors else getattr(self, name)


def validate(raw: dict) -> Assumptions:
    """Check an assumption record completely; raise AssumptionError listing every problem. Nothing is defaulted except a scalar rate repeated over the
    horizon when a single value is given."""
    problems = []
    if not isinstance(raw, dict):
        raise AssumptionError(["the assumption set must be an object"])
    horizon = raw.get("horizon_years")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 30:
        problems.append("horizon_years must be an integer from 1 to 30")
        horizon = None
    base = raw.get("base") or {}
    base_revenue = _dec(base.get("revenue"), "base revenue", problems)
    if base_revenue is not None and base_revenue <= 0:
        problems.append("base revenue must be positive")
    base_end = str(base.get("fiscal_year_end") or "")
    if not DATE.match(base_end):
        problems.append("base fiscal_year_end must be a date (YYYY-MM-DD)")
    currency = str(raw.get("currency") or "")
    if not CURRENCY.match(currency):
        problems.append("currency must be a three-letter code")
    valuation_date = str(raw.get("valuation_date") or "")
    if not DATE.match(valuation_date):
        problems.append("valuation_date must be a date (YYYY-MM-DD)")
    vectors = {}
    for name in VECTOR:
        given = raw.get(name)
        values = given if isinstance(given, list) else [given] * (horizon or 1)
        if horizon and isinstance(given, list) and len(given) != horizon:
            problems.append(
                f"{name} needs {horizon} yearly values (or one value for every year), got {len(given)}"
            )
            continue
        out = []
        for i, v in enumerate(values):
            d = _dec(v, f"{name} year {i + 1}", problems)
            if d is not None:
                low, high = LIMITS[name]
                if not low <= d <= high:
                    problems.append(
                        f"{name} year {i + 1} = {d} is outside the accepted range {low} to {high}"
                    )
                out.append(d)
        vectors[name] = tuple(out)
    scalars = {}
    for name in SCALAR:
        d = _dec(raw.get(name), name, problems)
        if d is not None:
            low, high = LIMITS[name]
            if not low <= d <= high:
                problems.append(f"{name} = {d} is outside the accepted range {low} to {high}")
        scalars[name] = d
    if (
        scalars.get("discount_rate") is not None
        and scalars.get("terminal_growth") is not None
        and scalars["discount_rate"] <= scalars["terminal_growth"]
    ):
        problems.append("the discount rate must exceed terminal growth for a perpetuity value")
    bridge_raw = raw.get("bridge") or {}
    bridge = {}
    for name in BRIDGE:
        v = bridge_raw.get(name)
        if v is None or v == "":
            bridge[name] = None
            continue
        d = _dec(v, f"bridge {name}", problems)
        if d is not None and name in ("cash", "debt", "other_senior_claims") and d < 0:
            problems.append(
                f"bridge {name} is an amount and must not be negative (its sign is applied by the formula)"
            )
        bridge[name] = d
    bridge_date = bridge_raw.get("as_of")
    if bridge_date is not None and not DATE.match(str(bridge_date)):
        problems.append("bridge as_of must be a date")
    shares = raw.get("shares") or {}
    share_count = None
    if shares.get("count") not in (None, ""):
        share_count = _dec(shares.get("count"), "share count", problems)
        if share_count is not None and share_count <= 0:
            problems.append("share count must be positive")
        if not DATE.match(str(shares.get("as_of") or "")):
            problems.append("share count as_of must be a date")
        if not str(shares.get("basis") or "").strip():
            problems.append(
                "state the share-count basis (for example: diluted shares outstanding at the valuation date, analyst-reviewed)"
            )
    treatments = raw.get("treatments") or {}
    for name, allowed in TREATMENTS.items():
        if treatments.get(name) not in allowed:
            problems.append(f"declare a treatment for {name}: one of {', '.join(allowed)}")
    if problems:
        raise AssumptionError(problems)
    return Assumptions(
        horizon,
        base_end,
        base_revenue,
        currency,
        valuation_date,
        vectors,
        scalars["discount_rate"],
        scalars["terminal_growth"],
        scalars["terminal_roic"],
        bridge,
        str(bridge_date) if bridge_date else None,
        share_count,
        str(shares.get("as_of")) if share_count is not None else None,
        str(shares.get("basis") or "") or None,
        {k: treatments[k] for k in TREATMENTS},
        dict(raw.get("sources") or {}),
    )


@dataclass(frozen=True)
class Valuation:
    status: str  # ok | ev_only | invalid | not_applicable
    years: tuple  # per-year dicts of exact Decimals
    pv_explicit: Decimal | None
    terminal_value: Decimal | None
    pv_terminal: Decimal | None
    enterprise_value: Decimal | None
    equity_value: Decimal | None
    per_share: Decimal | None
    terminal_share: Decimal | None  # PV of terminal value / EV
    warnings: tuple
    limitations: tuple

    def as_dict(self) -> dict:
        s = lambda v: None if v is None else str(v)  # noqa: E731
        return {
            "model": MODEL,
            "status": self.status,
            "years": [
                {k: s(v) if isinstance(v, Decimal) else v for k, v in y.items()} for y in self.years
            ],
            "pv_explicit": s(self.pv_explicit),
            "terminal_value": s(self.terminal_value),
            "pv_terminal": s(self.pv_terminal),
            "enterprise_value": s(self.enterprise_value),
            "equity_value": s(self.equity_value),
            "per_share": s(self.per_share),
            "terminal_share": s(self.terminal_share),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


def run(a: Assumptions, business: dict | None = None) -> Valuation:
    """Run the model on a validated assumption set."""
    limitations = [
        f"{name.replace('_', ' ')}: not modelled"
        for name, how in a.treatments.items()
        if how == "not_modelled"
    ]
    if business and business.get("supported") is False:
        return Valuation(
            "not_applicable",
            (),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            (business.get("reason") or "business type not supported",),
            tuple(limitations),
        )
    warnings = []
    with localcontext() as ctx:
        ctx.prec = PRECISION
        years, previous, pv = [], a.base_revenue, Decimal(0)
        one = Decimal(1)
        for t in range(1, a.horizon + 1):
            v = {name: a.vectors[name][t - 1] for name in VECTOR}
            revenue = previous * (one + v["revenue_growth"])
            ebit = revenue * v["operating_margin"]
            taxes = max(ebit, Decimal(0)) * v["cash_tax_rate"]
            nopat = ebit - taxes
            da = revenue * v["depreciation_rate"]
            capex = revenue * v["capex_rate"]
            dnwc = (revenue - previous) * v["nwc_rate"]
            fcff = nopat + da - capex - dnwc
            df = one / (one + a.discount_rate) ** t
            pv += fcff * df
            years.append(
                {
                    "year": t,
                    "revenue": revenue,
                    "ebit": ebit,
                    "taxes": taxes,
                    "nopat": nopat,
                    "depreciation": da,
                    "capex": capex,
                    "change_in_nwc": dnwc,
                    "fcff": fcff,
                    "discount_factor": df,
                    "pv_fcff": fcff * df,
                }
            )
            if ebit < 0:
                warnings.append(f"year {t}: operating loss; no tax credit is assumed")
            previous = revenue
        last = years[-1]
        g = a.terminal_growth
        reinvestment = g / a.terminal_roic
        if reinvestment > one:
            return Valuation(
                "invalid",
                tuple(years),
                pv,
                None,
                None,
                None,
                None,
                None,
                None,
                (f"terminal reinvestment g / ROIC = {reinvestment} exceeds 100% of NOPAT",),
                tuple(limitations),
            )
        tv = last["nopat"] * (one + g) * (one - reinvestment) / (a.discount_rate - g)
        pv_tv = tv * last["discount_factor"]
        ev = pv + pv_tv
        if last["nopat"] <= 0:
            warnings.append(
                "final-year NOPAT is not positive, so the perpetuity value is not positive"
            )
        if ev != 0 and pv_tv / ev > Decimal("0.75"):
            warnings.append(
                f"the terminal value is {(pv_tv / ev * 100).quantize(Decimal('0.1'))}% of enterprise value; the result rests mostly on the perpetuity"
            )
        terminal_share = pv_tv / ev if ev != 0 else None
        missing = [
            name for name in ("cash", "debt", "other_senior_claims") if a.bridge.get(name) is None
        ]
        reasons = []
        if missing:
            reasons.append(
                "the bridge from enterprise value to equity is incomplete: "
                + ", ".join(missing)
                + " not supplied"
            )
        if a.bridge_date and a.bridge_date > a.valuation_date:
            reasons.append(
                f"the bridge is dated {a.bridge_date}, after the valuation date {a.valuation_date}"
            )
        if not a.bridge_date and not missing:
            reasons.append("the bridge amounts have no balance-sheet date")
        if a.share_count is None:
            reasons.append("no share count was selected")
        elif a.share_count_date and a.share_count_date > a.valuation_date:
            reasons.append(
                f"the share count is dated {a.share_count_date}, after the valuation date {a.valuation_date}"
            )
        if reasons:
            return Valuation(
                "ev_only",
                tuple(years),
                pv,
                tv,
                pv_tv,
                ev,
                None,
                None,
                terminal_share,
                tuple(warnings + reasons),
                tuple(limitations),
            )
        equity = (
            ev
            + a.bridge["cash"]
            - a.bridge["debt"]
            - a.bridge["other_senior_claims"]
            + (a.bridge.get("other_adjustments") or Decimal(0))
        )
        if equity <= 0:
            warnings.append("equity value is not positive under these assumptions")
        return Valuation(
            "ok",
            tuple(years),
            pv,
            tv,
            pv_tv,
            ev,
            equity,
            equity / a.share_count,
            terminal_share,
            tuple(warnings),
            tuple(limitations),
        )


def with_values(a: Assumptions, overrides: dict) -> Assumptions:
    """A copy with some assumptions replaced; a single value for a yearly assumption applies to every forecast year (a level, not a shift)."""
    vectors = dict(a.vectors)
    kwargs = {}
    for name, value in overrides.items():
        if name in VECTOR:
            vectors[name] = tuple([Decimal(value)] * a.horizon)
        elif name in SCALAR:
            kwargs[name] = Decimal(value)
        else:
            raise ValueError(f"{name} cannot be varied")
    from dataclasses import replace

    return replace(a, vectors=vectors, **kwargs)


GRID_PARAMETERS = VECTOR[:2] + ("discount_rate", "terminal_growth", "capex_rate")


def sensitivity(
    a: Assumptions,
    row: tuple,
    column: tuple,
    business: dict | None = None,
    measure: str = "per_share",
) -> dict:
    """A two-dimensional grid: `row` and `column` are (parameter, [values]). Every other assumption is held at its saved value and listed. Each cell is
    the model result with that pair; a cell whose pair is invalid (for example discount rate <= terminal growth) says so instead of a number."""
    (r_name, r_values), (c_name, c_values) = row, column
    for name, values in ((r_name, r_values), (c_name, c_values)):
        if name not in GRID_PARAMETERS:
            raise ValueError(f"{name} is not a grid parameter ({', '.join(GRID_PARAMETERS)})")
        if not 1 <= len(values) <= 9:
            raise ValueError("each grid axis takes 1 to 9 values")
    if r_name == c_name:
        raise ValueError("choose two different parameters")
    if measure not in ("per_share", "enterprise_value"):
        raise ValueError("measure must be per_share or enterprise_value")
    cells = []
    for rv in r_values:
        line = []
        for cv in c_values:
            overrides = {r_name: Decimal(str(rv)), c_name: Decimal(str(cv))}
            problems = _check_pair(a, overrides)
            if problems:
                line.append(
                    {
                        "row": str(rv),
                        "column": str(cv),
                        "status": "invalid",
                        "value": None,
                        "reasons": problems,
                    }
                )
                continue
            v = run(with_values(a, overrides), business)
            value = v.per_share if measure == "per_share" else v.enterprise_value
            line.append(
                {
                    "row": str(rv),
                    "column": str(cv),
                    "status": v.status
                    if value is not None
                    else (v.status if v.status != "ok" else "ev_only"),
                    "value": None if value is None else str(value),
                    "reasons": list(v.warnings[-1:]) if value is None else [],
                }
            )
        cells.append(line)
    held = {
        name: [str(x) for x in a.vectors[name]] for name in VECTOR if name not in (r_name, c_name)
    }
    held.update({name: str(getattr(a, name)) for name in SCALAR if name not in (r_name, c_name)})
    return {
        "model": MODEL,
        "measure": measure,
        "row": {"parameter": r_name, "values": [str(v) for v in r_values]},
        "column": {"parameter": c_name, "values": [str(v) for v in c_values]},
        "cells": cells,
        "held_fixed": held,
        "semantics": "a single grid value for a yearly assumption applies to every forecast year",
    }


def _check_pair(a, overrides):
    problems = []
    for name, value in overrides.items():
        low, high = LIMITS[name]
        if not low <= value <= high:
            problems.append(f"{name} = {value} is outside {low} to {high}")
    rate = overrides.get("discount_rate", a.discount_rate)
    g = overrides.get("terminal_growth", a.terminal_growth)
    if rate <= g:
        problems.append("discount rate must exceed terminal growth")
    return problems


REVERSE_BRACKETS = {
    "revenue_growth": (Decimal("-0.5"), Decimal("1.5")),
    "operating_margin": (Decimal("-0.5"), Decimal("0.8")),
    "discount_rate": (Decimal("0.02"), Decimal("0.40")),
    "terminal_growth": (Decimal("-0.05"), Decimal("0.08")),
}


def reverse(
    a: Assumptions,
    target_per_share: Decimal,
    parameter: str,
    bracket: tuple | None = None,
    business: dict | None = None,
    tolerance: Decimal = Decimal("0.0001"),
    samples: int = 41,
    max_iterations: int = 200,
) -> dict:
    """Solve ONE parameter (applied as a level to every forecast year where yearly) so that value per share equals a dated target, all else fixed.

    Bounded bisection on an explicit bracket. Before solving, the model is sampled across the bracket: it must be finite and strictly monotonic there,
    and the target must lie between the end values; otherwise the result says no unique solution exists in the bracket rather than inventing one. The
    answer is 'the level required under this model and these assumptions', not what the market believes."""
    if parameter not in REVERSE_BRACKETS:
        raise ValueError(f"{parameter} cannot be solved for ({', '.join(REVERSE_BRACKETS)})")
    target = Decimal(str(target_per_share))
    if not target.is_finite() or target <= 0:
        raise ValueError("the target value per share must be positive")
    low, high = (Decimal(str(x)) for x in (bracket or REVERSE_BRACKETS[parameter]))
    if not low < high:
        raise ValueError("the bracket's lower end must be below its upper end")
    base = {
        "parameter": parameter,
        "label": f"{LABELS[parameter]} required under this model and these assumptions",
        "target_per_share": str(target),
        "bracket": [str(low), str(high)],
        "model": MODEL,
    }

    def value_at(x):
        overrides = {parameter: x}
        if _check_pair(a, overrides):
            return None
        v = run(with_values(a, overrides), business)
        return v.per_share

    if run(a, business).status == "not_applicable":
        return {
            **base,
            "status": "not_applicable",
            "reasons": ["the operating-company model does not apply to this business type"],
        }
    if run(a, business).per_share is None:
        return {
            **base,
            "status": "ev_only",
            "reasons": [
                "value per share is not available: " + "; ".join(run(a, business).warnings[-1:])
            ],
        }
    step = (high - low) / (samples - 1)
    grid = [low + step * i for i in range(samples)]
    values = [value_at(x) for x in grid]
    if any(v is None for v in values):
        bad = [str(x) for x, v in zip(grid, values) if v is None][:3]
        return {
            **base,
            "status": "invalid_bracket",
            "reasons": [
                f"the model is undefined at {', '.join(bad)} within the bracket; narrow it"
            ],
        }
    diffs = [b - c for b, c in zip(values[1:], values)]
    if not (all(d > 0 for d in diffs) or all(d < 0 for d in diffs)):
        return {
            **base,
            "status": "not_monotonic",
            "reasons": [
                "value per share is not strictly monotonic in this parameter over the bracket, so a solution "
                "would not be unique"
            ],
            "samples": [[str(x), str(v)] for x, v in zip(grid, values)][::10],
        }
    f_low, f_high = values[0] - target, values[-1] - target
    if f_low == 0:
        return {**base, "status": "solved", "value": str(low), "residual": "0", "iterations": 0}
    if f_high == 0:
        return {**base, "status": "solved", "value": str(high), "residual": "0", "iterations": 0}
    if (f_low > 0) == (f_high > 0):
        return {
            **base,
            "status": "no_solution",
            "reasons": [
                f"the target lies outside the values the bracket produces ({values[0]} to {values[-1]} per share)"
            ],
            "range": [str(min(values[0], values[-1])), str(max(values[0], values[-1]))],
        }
    lo, hi, f_lo = low, high, f_low
    with localcontext() as ctx:
        ctx.prec = PRECISION
        for i in range(1, max_iterations + 1):
            mid = (lo + hi) / 2
            f_mid = value_at(mid) - target
            if abs(f_mid) <= tolerance:
                return {
                    **base,
                    "status": "solved",
                    "value": str(mid),
                    "residual": str(f_mid),
                    "iterations": i,
                    "tolerance": str(tolerance),
                    "check": str(value_at(mid)),
                }
            if (hi - lo) / 2 < Decimal("1e-12"):
                return {
                    **base,
                    "status": "not_converged",
                    "value": str(mid),
                    "residual": str(f_mid),
                    "iterations": i,
                    "reasons": [
                        f"the bracket narrowed to {hi - lo} without reaching the tolerance {tolerance} per share; the value is that steep here"
                    ],
                }
            if (f_mid > 0) == (f_lo > 0):
                lo, f_lo = mid, f_mid
            else:
                hi = mid
    return {
        **base,
        "status": "not_converged",
        "reasons": [f"no convergence within {max_iterations} iterations"],
    }


def suggest_from_history(dossier: dict) -> dict:
    """Reference values from the eligible filed history, shown beside the form with their provenance. They are suggestions for the analyst to accept or
    change, never forecasts: no growth path is extrapolated."""
    annual = dossier["history"]["annual"]

    def last(metric):
        cells = [c for c in annual.get(metric, []) if c["value"] is not None]
        return cells[-1] if cells else None

    rev, op, capex, da, ocf = (
        last(m)
        for m in (
            "revenue",
            "operating_income",
            "capex",
            "depreciation_amortization",
            "operating_cash_flow",
        )
    )
    out = {
        "note": "From the latest eligible fiscal year as filed; suggestions only, never applied without your review.",
        "values": {},
    }
    if rev:
        out["values"]["base_revenue"] = {
            "value": rev["value"],
            "fiscal_year_end": rev["period"]["end"],
            "observation_ids": rev["observation_ids"],
        }
        revenue = Decimal(rev["value"])
        for name, cell in (
            ("operating_margin", op),
            ("capex_rate", capex),
            ("depreciation_rate", da),
        ):
            if cell and cell["period"]["end"] == rev["period"]["end"] and revenue > 0:
                out["values"][name] = {
                    "value": str((Decimal(cell["value"]) / revenue).quantize(Decimal("0.0001"))),
                    "fiscal_year_end": cell["period"]["end"],
                    "observation_ids": cell["observation_ids"] + rev["observation_ids"],
                }
        cells = [c for c in annual.get("revenue", []) if c["value"]]
        if len(cells) >= 2 and Decimal(cells[-2]["value"]) > 0:
            out["values"]["last_year_growth"] = {
                "value": str(
                    (revenue / Decimal(cells[-2]["value"]) - 1).quantize(Decimal("0.0001"))
                ),
                "fiscal_year_end": rev["period"]["end"],
                "note": "the last reported year's growth; not a forecast",
                "observation_ids": rev["observation_ids"] + cells[-2]["observation_ids"],
            }
    if ocf:
        out["values"]["operating_cash_flow"] = {
            "value": ocf["value"],
            "fiscal_year_end": ocf["period"]["end"],
            "observation_ids": ocf["observation_ids"],
        }
    return out
