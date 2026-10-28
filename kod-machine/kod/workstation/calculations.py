"""Derived values with their lineage: formula and version, input observation / calculation / assumption IDs, the cutoff policy, status, unit and reasons.

Formulas are pure functions over resolved figures. They check metric semantics, not only matching units: a margin needs a profit flow over revenue for the same
period, basis family and currency; growth needs the same metric over a genuinely earlier comparable period; a non-positive base is not divided by. Percentage-point
changes are kept apart from percentage growth. Calculations are recorded immutably and form a small DAG (a calculation may consume other calculations);
cycles are refused. When an input gains a newer version, dependents are reported as stale and an explicit recompute records a new calculation that supersedes
the old one, which stays available to anything saved from it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, localcontext
import json

from .. import earnings
from ..earnings import _decimal_string
from .domain import canonical, identity
from .financials import ResolvedFigure
from .policy import AsOfPolicy

STATUSES = ("ok", "missing", "conflicted", "incompatible", "not_applicable", "invalid")
PRECISION = 28


@dataclass(frozen=True, slots=True)
class CalculationResult:
    formula: str
    formula_version: str
    status: str
    value: Decimal | None
    unit: str
    inputs: tuple            # ((role, kind, id), ...)
    evidence_ids: tuple
    reasons: tuple
    detail: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError("unknown calculation status " + repr(self.status))
        if (self.status == "ok") != (self.value is not None):
            raise ValueError("a value is present exactly when the status is ok")
        if self.value is not None and not self.value.is_finite():
            raise ValueError("calculation values must be finite")

    @property
    def input_ids(self) -> tuple:
        return tuple(i for _, _, i in self.inputs)


def _inputs(**figures):
    return tuple((role, "observation", oid) for role, f in figures.items() if f is not None for oid in f.observation_ids)


def _blocked(formula, version, unit, figures, extra=(), names=None):
    """The status for missing or conflicted inputs, or None when every input is usable. `names` gives the metric each role stands for, for the message."""
    missing = [role for role, f in figures.items() if f is None]
    if missing:
        return CalculationResult(formula, version, "missing", None, unit, _inputs(**figures), (),
                                 tuple(f"no eligible {(names or {}).get(r, r)} figure" for r in missing) + tuple(extra))
    conflicted = [role for role, f in figures.items() if f.status != "ok"]
    if conflicted:
        return CalculationResult(formula, version, "conflicted", None, unit, _inputs(**figures), (),
                                 tuple(f"the {(names or {}).get(r, r)} figure is {figures[r].status}: {'; '.join(figures[r].reasons)}" for r in conflicted))
    return None


def _money_compatible(a: ResolvedFigure, b: ResolvedFigure) -> list:
    reasons = []
    if a.unit != b.unit or a.unit not in ("currency", "currency/share"):
        reasons.append(f"units differ or are not monetary ({a.unit} vs {b.unit})")
    if a.scale is None or b.scale is None:
        reasons.append("a figure's scale (thousands/millions) is unknown")
    if a.currency is None or b.currency is None or a.currency != b.currency:
        reasons.append(f"currencies differ or are unknown ({a.currency} vs {b.currency})")
    if a.context != b.context and not (a.context.startswith("consolidated") and b.context.startswith("consolidated")):
        reasons.append("contexts differ (consolidated vs dimensional)")
    return reasons


def _basis_compatible(a: ResolvedFigure, b: ResolvedFigure) -> list:
    """GAAP with GAAP, non-GAAP with non-GAAP; an unstated basis only with another unstated or GAAP statement figure is not assumed: kept apart."""
    return [] if a.basis == b.basis else [f"accounting bases differ ({a.basis} vs {b.basis})"]


def _same_period(a: ResolvedFigure, b: ResolvedFigure) -> list:
    return [] if a.period.id == b.period.id else [f"periods differ ({a.period.label} vs {b.period.label})"]


def _kind(period) -> str:
    """A week-based fiscal quarter of 15-18 weeks (Costco's fourth quarter) compares as a quarter; its length difference is noted by the caller."""
    days = period.duration_days
    if period.kind != "quarter" and days is not None and days % 7 == 0 and 105 <= days <= 126:
        return "quarter"
    return period.kind


def _earlier_comparable(cur: ResolvedFigure, prior: ResolvedFigure) -> list:
    pc, pp = cur.period, prior.period
    if _kind(pc) != _kind(pp):
        return [f"duration kinds differ ({pc.kind} vs {pp.kind})"]
    if pc.end_date and pp.end_date:
        return [] if pp.end_date < pc.end_date else ["the comparison period is not earlier"]
    qc, qp = (earnings.qn_period(p.fiscal_label or "") for p in (pc, pp))
    if qc and qp:
        order = earnings.earlier(qp, qc)
        return [] if order is True else ["the comparison period is not earlier" if order is False else "fiscal and calendar quarter labels cannot be ordered"]
    return ["the periods cannot be ordered (no end dates or comparable quarter labels)"]


def growth(current: ResolvedFigure | None, prior: ResolvedFigure | None, version="growth-v1") -> CalculationResult:
    """Percentage change of one additive flow or per-share figure between a period and a genuinely earlier comparable one: 100 * (current - prior) / prior,
    only for a positive prior. Margins and other ratios change in percentage points (see point_change), not percent."""
    unit = "percent"
    blocked = _blocked("growth", version, unit, {"current": current, "prior": prior})
    if blocked:
        return blocked
    reasons = []
    if current.metric != prior.metric:
        reasons.append("different metrics")
    if current.unit == "percent":
        reasons.append("a percentage changes in percentage points; use point_change")
    reasons += _money_compatible(current, prior) + _basis_compatible(current, prior) + _earlier_comparable(current, prior)
    inputs = _inputs(current=current, prior=prior)
    if reasons:
        return CalculationResult("growth", version, "incompatible", None, unit, inputs, (), tuple(reasons))
    if prior.value <= 0:
        return CalculationResult("growth", version, "not_applicable", None, unit, inputs, (), ("the earlier value is zero or negative; percentage growth is not meaningful",))
    with localcontext() as ctx:
        ctx.prec = PRECISION
        value = (current.value - prior.value) * 100 / prior.value
    return CalculationResult("growth", version, "ok", value, unit, inputs, (), (), {"current": str(current.value), "prior": str(prior.value)})


def ratio(numerator: ResolvedFigure | None, denominator: ResolvedFigure | None, formula: str, numerator_metrics: tuple, denominator_metric: str,
          version: str, nonpositive_base: str) -> CalculationResult:
    unit = "percent"
    names = {"numerator": "/".join(m.replace("_", " ") for m in numerator_metrics), "denominator": denominator_metric.replace("_", " ")}
    blocked = _blocked(formula, version, unit, {"numerator": numerator, "denominator": denominator}, names=names)
    if blocked:
        return blocked
    reasons = []
    if numerator.metric not in numerator_metrics or denominator.metric != denominator_metric:
        reasons.append(f"{formula} needs {'/'.join(numerator_metrics)} over {denominator_metric}, not {numerator.metric} over {denominator.metric}")
    reasons += _money_compatible(numerator, denominator) + _basis_compatible(numerator, denominator) + _same_period(numerator, denominator)
    inputs = _inputs(numerator=numerator, denominator=denominator)
    if reasons:
        return CalculationResult(formula, version, "incompatible", None, unit, inputs, (), tuple(reasons))
    if denominator.value <= 0:
        return CalculationResult(formula, version, "not_applicable", None, unit, inputs, (), (nonpositive_base,))
    with localcontext() as ctx:
        ctx.prec = PRECISION
        value = numerator.value * 100 / denominator.value
    return CalculationResult(formula, version, "ok", value, unit, inputs, (), ())


def operating_margin(operating_income, revenue):
    return ratio(operating_income, revenue, "operating_margin", ("operating_income",), "revenue", "operating-margin-v1", "revenue is zero or negative")


def cash_conversion(operating_cash_flow, net_income):
    """Cash from operations as a percentage of net income; not meaningful when net income is zero or negative (a loss), which is reported, not computed."""
    return ratio(operating_cash_flow, net_income, "cash_conversion", ("operating_cash_flow",), "net_income", "cash-conversion-v1",
                 "net income is zero or negative; cash conversion is not meaningful")


def capex_intensity(capex, revenue):
    return ratio(capex, revenue, "capex_intensity", ("capex",), "revenue", "capex-intensity-v1", "revenue is zero or negative")


def cfo_minus_capex(operating_cash_flow: ResolvedFigure | None, capex: ResolvedFigure | None, version="cfo-minus-capex-v1") -> CalculationResult:
    """Cash from operations minus capital expenditures (capex as a nonnegative investment), same period, currency and scale. Named for what it is: not 'free cash
    flow' as any company defines it."""
    blocked = _blocked("cfo_minus_capex", version, "currency", {"operating_cash_flow": operating_cash_flow, "capex": capex})
    if blocked:
        return blocked
    reasons = _money_compatible(operating_cash_flow, capex) + _same_period(operating_cash_flow, capex)
    if operating_cash_flow.metric != "operating_cash_flow" or capex.metric != "capex":
        reasons.append("needs operating cash flow and capital expenditures")
    if capex.value < 0:
        reasons.append("capital expenditures must be recorded as a nonnegative investment amount")
    inputs = _inputs(operating_cash_flow=operating_cash_flow, capex=capex)
    if reasons:
        return CalculationResult("cfo_minus_capex", version, "incompatible", None, "currency", inputs, (), tuple(reasons))
    return CalculationResult("cfo_minus_capex", version, "ok", operating_cash_flow.value - capex.value, "currency", inputs, (), (),
                             {"currency": capex.currency})


def share_change(current: ResolvedFigure | None, prior: ResolvedFigure | None, version="share-change-v1") -> CalculationResult:
    """Percentage change of one share-count measure between a period and a genuinely earlier comparable one. Weighted-average diluted shares are compared
    only with weighted-average diluted shares of the same duration; they are never mixed with period-end shares outstanding."""
    unit = "percent"
    blocked = _blocked("share_change", version, unit, {"current": current, "prior": prior})
    if blocked:
        return blocked
    reasons = []
    if current.metric != prior.metric or current.metric not in ("diluted_shares", "shares_outstanding"):
        reasons.append("needs the same share-count measure on both sides (weighted-average diluted shares or shares outstanding, never mixed)")
    if current.unit != "shares" or prior.unit != "shares":
        reasons.append(f"units are not share counts ({current.unit} vs {prior.unit})")
    reasons += _earlier_comparable(current, prior)
    inputs = _inputs(current=current, prior=prior)
    if reasons:
        return CalculationResult("share_change", version, "incompatible", None, unit, inputs, (), tuple(reasons))
    if prior.value <= 0:
        return CalculationResult("share_change", version, "not_applicable", None, unit, inputs, (), ("the earlier share count is zero or negative",))
    with localcontext() as ctx:
        ctx.prec = PRECISION
        value = (current.value - prior.value) * 100 / prior.value
    return CalculationResult("share_change", version, "ok", value, unit, inputs, (), (), {"current": str(current.value), "prior": str(prior.value)})


def point_change(current: CalculationResult | None, prior: CalculationResult | None, formula="point_change", version="point-change-v1",
                 policy: AsOfPolicy | None = None) -> CalculationResult:
    """The change of a percentage between two calculations, in percentage points (never percent growth). Pass the cutoff policy the inputs are recorded
    under, so the input IDs are the IDs they are recorded with."""
    unit = "percentage points"
    if current is None or prior is None:
        return CalculationResult(formula, version, "missing", None, unit, (), (), ("an input calculation is missing",))
    inputs = (("current", "calculation", calculation_id(current, policy)), ("prior", "calculation", calculation_id(prior, policy)))
    if current.status != "ok" or prior.status != "ok":
        return CalculationResult(formula, version, current.status if current.status != "ok" else prior.status, None, unit, inputs, (),
                                 ("an input calculation is not available: " + "; ".join(current.reasons + prior.reasons),))
    if current.unit != "percent" or prior.unit != "percent" or current.formula != prior.formula:
        return CalculationResult(formula, version, "incompatible", None, unit, inputs, (), ("both inputs must be the same percentage measure",))
    return CalculationResult(formula, version, "ok", current.value - prior.value, unit, inputs, (), ())


def calculation_id(result: CalculationResult, policy: AsOfPolicy | None = None) -> str:
    return identity("calc", result.formula, result.formula_version, sorted(result.inputs), policy.as_dict() if policy else None, result.status,
                    None if result.value is None else _decimal_string(result.value), result.unit, list(result.reasons))


class CycleError(ValueError):
    """A calculation would (indirectly) consume itself."""


def _ancestors(db, calc_id, path=(), seen=None):
    """Every calculation `calc_id` depends on. A dependency loop already present in the database (which content addressing cannot create) raises CycleError."""
    seen = set() if seen is None else seen
    for (child,) in db.execute("SELECT input_id FROM calculation_inputs WHERE calculation_id=? AND input_kind='calculation'", (calc_id,)).fetchall():
        if child in path or child == calc_id:
            raise CycleError(f"the recorded calculations contain a dependency loop through {child}")
        if child not in seen:
            seen.add(child)
            _ancestors(db, child, path + (calc_id,), seen)
    return seen


def record(db, result: CalculationResult, subject_kind: str, subject_id: str, policy: AsOfPolicy, now: str) -> str:
    """Record a calculation and its inputs (idempotently). Every input must exist; a calculation input must not depend on this calculation."""
    cid = calculation_id(result, policy)
    for role, kind, iid in result.inputs:
        table = {"observation": "financial_observations", "calculation": "calculations", "assumption": "assumption_versions"}[kind]
        exists = db.execute(f"SELECT 1 FROM {table} WHERE id=?", (iid,)).fetchone() if kind != "assumption" or _has_table(db, table) else None
        if exists is None:
            raise ValueError(f"calculation input {kind} {iid} is not recorded")
        if kind == "calculation" and (iid == cid or cid in _ancestors(db, iid)):
            raise CycleError(f"calculation {cid} would depend on itself through {iid}")
    db.execute("INSERT OR IGNORE INTO calculations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
               (cid, result.formula, result.formula_version, subject_kind, subject_id, canonical(policy.as_dict()), result.status,
                None if result.value is None else _decimal_string(result.value), result.unit, canonical(list(result.reasons)),
                canonical({"evidence_ids": list(result.evidence_ids), "detail": result.detail}), now))
    for role, kind, iid in result.inputs:
        db.execute("INSERT OR IGNORE INTO calculation_inputs VALUES (?,?,?,?)", (cid, role, kind, iid))
    return cid


def _has_table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def supersede(db, old_id: str, new_id: str, reason: str, now: str):
    if old_id == new_id:
        return
    db.execute("INSERT OR IGNORE INTO calculation_supersessions VALUES (?,?,?,?)", (old_id, new_id, reason, now))


def stale_reasons(db, calc_id: str) -> list:
    """Why a recorded calculation no longer reflects its inputs' latest versions (empty when current). It is never changed; recompute records a new one."""
    reasons = []
    for role, kind, iid in db.execute("SELECT role,input_kind,input_id FROM calculation_inputs WHERE calculation_id=?", (calc_id,)).fetchall():
        if kind == "observation":
            row = db.execute("SELECT source_document_id,concept,period_id,basis,parser_version,mapping_version,recorded_at FROM financial_observations WHERE id=?", (iid,)).fetchone()
            newer = db.execute("""SELECT id,parser_version,mapping_version FROM financial_observations WHERE source_document_id IS ? AND concept=? AND period_id=? AND basis=?
                                  AND id<>? AND (parser_version<>? OR mapping_version<>?) AND recorded_at>=?""",
                               (row["source_document_id"], row["concept"], row["period_id"], row["basis"], iid, row["parser_version"], row["mapping_version"],
                                row["recorded_at"])).fetchall()
            for n in newer:
                reasons.append(f"input {role} has a newer interpretation ({n['parser_version']}, {n['mapping_version']}): {n['id']}")
        elif kind == "calculation":
            for (new,) in db.execute("SELECT new_id FROM calculation_supersessions WHERE old_id=?", (iid,)):
                reasons.append(f"input {role} was recomputed as {new}")
            if stale_reasons(db, iid):
                reasons.append(f"input {role} ({iid}) is itself stale")
        elif kind == "assumption" and _has_table(db, "assumption_versions"):
            row = db.execute("SELECT assumption_id, version FROM assumption_versions WHERE id=?", (iid,)).fetchone()
            latest = db.execute("SELECT id, version FROM assumption_versions WHERE assumption_id=? ORDER BY version DESC LIMIT 1", (row["assumption_id"],)).fetchone()
            if latest and latest["id"] != iid:
                reasons.append(f"assumption {role} has a newer version {latest['version']} ({latest['id']})")
    return reasons


def lineage(db, calc_id: str) -> dict:
    """The calculation and everything it was derived from, recursively (observations with their evidence)."""
    row = db.execute("SELECT * FROM calculations WHERE id=?", (calc_id,)).fetchone()
    if row is None:
        raise ValueError("calculation was not found")
    out = dict(row, reasons=json.loads(row["reasons"]), evidence=json.loads(row["evidence"]), policy=json.loads(row["policy"]), inputs=[])
    for role, kind, iid in db.execute("SELECT role,input_kind,input_id FROM calculation_inputs WHERE calculation_id=? ORDER BY role,input_id", (calc_id,)).fetchall():
        if kind == "calculation":
            node = lineage(db, iid)
        elif kind == "observation":
            o = db.execute("SELECT o.*, p.kind, p.end_date, p.fiscal_label FROM financial_observations o JOIN periods p ON p.id=o.period_id WHERE o.id=?", (iid,)).fetchone()
            node = dict(o, evidence=json.loads(o["evidence"]), flags=json.loads(o["flags"]))
        else:
            a = db.execute("SELECT * FROM assumption_versions WHERE id=?", (iid,)).fetchone() if _has_table(db, "assumption_versions") else None
            node = dict(a) if a else {"id": iid, "missing": True}
        out["inputs"].append({"role": role, "kind": kind, "id": iid, "node": node})
    out["stale"] = stale_reasons(db, calc_id)
    return out
