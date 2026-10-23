"""The company dossier: one cutoff-aware read model for the screen, the JSON/Markdown export and (later) decision packets.

It answers, for one company at one information cutoff: what is covered, what changed in compatible periods, where each number comes from, what is conflicted
or unavailable, and which questions the evidence raises. It never fills a gap, never ranks by an undisclosed score and never states a cause.

Rules kept here:
- Eligibility first. Only observations eligible under the AsOfPolicy enter; figures are selected (as-reported or latest-known) afterwards. Nothing about
  ineligible records is reported, not even how many there are: adding a later filing leaves an earlier cutoff's dossier byte-for-byte unchanged.
- Filing history (SEC companyfacts) and release tables are kept apart. A release figure is shown beside the filing history with its reconciliation status;
  it is not spliced into the filed series.
- One unit/currency group per series. A metric reported in more than one currency or unit is shown in its main group and the others are listed, not mixed.
- Changes come from a fixed, published catalog (CHANGES) in a fixed order; "supported changes" are simply the first ones whose inputs allow a result.
- Derived quarters (a year-to-date difference) are labelled and carry both inputs; per-share amounts and share counts are never derived.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import json
import re

from . import calculations as calc
from . import companyfacts, financials, quarters
from .financials import ResolvedFigure, period as make_period
from .identity import METRIC_CATALOG_V1
from .policy import AsOfPolicy, eligibility

SCHEMA = "KOD-DOSSIER-v1"
FILINGS = companyfacts.PROVIDER
RELEASES = financials.RELEASE_PROVIDER
LABELS = {m: label for m, label, *_ in METRIC_CATALOG_V1}
KINDS = {m: kind for m, _, kind, *_ in METRIC_CATALOG_V1}
UNIT_FAMILY = {"flow": "currency", "per_share": "currency/share", "count": "shares", "ratio": "percent"}
HISTORY_METRICS = ("revenue", "operating_income", "net_income", "eps_diluted", "diluted_shares", "operating_cash_flow", "capex", "depreciation_amortization",
                   "cash_and_equivalents", "total_assets", "total_liabilities", "stockholders_equity", "long_term_debt", "shares_outstanding")
QUARTERS_SHOWN, YEARS_SHOWN, INSTANTS_SHOWN = 8, 5, 6
SUPPORTED_SHOWN = 5
POLICY_NOTES = {
    "KOD-ASOF-v1-strict": "Strict policy: only exact availability times count, so filed history with filing dates only (all SEC companyfacts) is never eligible.",
    "KOD-ASOF-v1-day-end": "Day-end policy: a filing dated D counts from midnight New York time after D; exact times count from that time.",
}
SCOPE_NOTE = ("Filed history is SEC companyfacts: whole-entity standard-taxonomy facts as filed, with filing dates as availability (date precision). No segment "
              "data, custom KPIs, prices or estimates. Release figures come from preserved earnings releases and are shown separately.")


def _unit_family(metric):
    kind = KINDS.get(metric)
    if kind == "instant":
        return "shares" if metric == "shares_outstanding" else "currency"
    return UNIT_FAMILY.get(kind, "currency")


def _period_dict(p) -> dict:
    return {"kind": p.kind, "start": p.start_date, "end": p.end_date, "instant": p.instant_date, "label": p.label, "id": p.id}


def _end(p):
    return p.end_date or p.instant_date or ""


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


class _Index:
    """Observation lookup and the provenance summary shown in drill-downs."""

    def __init__(self, observations):
        self.by_id = {o.id: o for o in observations}
        self.used = {}

    def brief(self, oid):
        o = self.by_id[oid]
        self.used[oid] = {
            "id": o.id, "provider": o.provider, "metric": o.metric, "concept": f"{o.taxonomy}:{o.concept}", "value": str(o.value), "raw_value": o.raw_value,
            "unit": o.unit, "scale": o.scale, "currency": o.currency, "basis": o.basis, "period": _period_dict(o.period), "accession": o.accession, "form": o.form,
            "filed": o.filed, "published_at": o.published_at, "publication_date": o.publication_date, "publication_basis": o.publication_basis,
            "observed_at": o.observed_at, "source_document_id": o.source_document_id,
            # 'frame' is assigned by the SEC from the latest filing in the snapshot, i.e. possibly after the cutoff; it is not cutoff-safe and is left out.
            "evidence": {k: v for k, v in o.evidence.items() if k != "frame"}, "flags": list(o.flags),
            "parser_version": o.parser_version, "mapping_version": o.mapping_version}
        return self.used[oid]

    def accessions(self, ids) -> list:
        return sorted({self.by_id[i].accession for i in ids if i in self.by_id and self.by_id[i].accession},
                      key=lambda a: (min(self.by_id[i].filed or "" for i in ids if i in self.by_id and self.by_id[i].accession == a), a))

    def revisions(self, figure: ResolvedFigure) -> tuple[list, int]:
        """(other eligible disclosures whose value differs from the selected one beyond rounding, oldest first; how many differ only within rounding)."""
        out, rounding = [], 0
        for oid in figure.other_ids:
            o = self.by_id[oid]
            if figure.value is not None and o.value == figure.value:
                continue
            if figure.value is not None and financials.same_within_rounding(o.value, figure.value, o.unit):
                rounding += 1
                continue
            self.brief(oid)
            out.append({"observation_id": oid, "value": str(o.value), "form": o.form, "filed": o.filed, "accession": o.accession, "published_at": o.published_at})
        return sorted(out, key=lambda r: (r["filed"] or r["published_at"] or "", r["observation_id"])), rounding

    def differs_from_first(self, figure: ResolvedFigure) -> bool:
        """The selected value differs beyond rounding from the earliest eligible disclosure of the same figure (a restated or corrected value)."""
        group = [self.by_id[i] for i in figure.observation_ids + figure.other_ids]
        first = min(group, key=lambda o: (o.filed or o.published_at or "", o.observed_at))
        return figure.value is not None and not financials.same_within_rounding(first.value, figure.value, first.unit)

    def first_disclosure(self, ids):
        group = [self.by_id[i] for i in ids if i in self.by_id]
        return min(group, key=lambda o: (o.filed or o.published_at or "", o.observed_at)) if group else None

    def flags(self, ids) -> list:
        return sorted({fl for i in ids if i in self.by_id for fl in self.by_id[i].flags})


def _main_group(figures: list, family: str) -> tuple[list, list, tuple | None]:
    """(figures of the main unit/currency/basis group, descriptions of other groups, the main group key). The main group is the one with the most figures."""
    groups = {}
    for f in figures:
        groups.setdefault((f.unit, f.currency, f.basis, f.context), []).append(f)
    usable = {k: v for k, v in groups.items() if k[0] == family}
    if not usable:
        return [], [f"{len(v)} figure(s) in {k[0]} {k[1] or ''} {k[2]}".strip() for k, v in groups.items()], None
    main = max(usable, key=lambda k: (len(usable[k]), k[2] == "GAAP", str(k)))
    others = [f"{len(v)} figure(s) in {k[0]} {k[1] or ''} ({k[2]}) not combined with the main series" for k, v in groups.items() if k != main]
    return usable[main], others, main


def _figure_from_quarter(q: quarters.Quarter, template: ResolvedFigure, view: str) -> ResolvedFigure | None:
    """A derived quarter as a figure for further calculations: its lineage is the derivation's input observations."""
    if q is None:
        return None
    if q.figure is not None:
        return q.figure
    if q.status != "derived":
        return None
    return ResolvedFigure(template.metric, make_period("quarter", start=q.start, end=q.end), template.basis, template.unit, template.scale, template.currency,
                          template.context, "ok", q.value, q.calculation.input_ids, (), view, ("derived: " + q.calculation.detail.get("formula", ""),))


def _year_before(end_a: str, end_b: str) -> bool:
    """end_a is the same fiscal period one year before end_b (357-372 days: 52/53-week years included)."""
    return 357 <= _days(end_a, end_b) <= 372


class _Series:
    """One metric's main series at the cutoff: quarters (reported or derived), annual figures, instants, and the observations behind them so comparisons can
    use the prior period as presented in the same filing."""

    def __init__(self, metric, figures, eligible, index: _Index, policy, view):
        self.metric, self.view, self.index, self.policy = metric, view, index, policy
        self.family = _unit_family(metric)
        self.figures, self.other_groups, key = _main_group([f for f in figures if f.metric == metric], self.family)
        self.obs = [o for o in eligible if o.metric == metric and o.provider == FILINGS and (o.unit, o.currency, o.basis, o.context) == key] if key else []
        self.kind = KINDS.get(metric)
        self.figures = [self._screen(f) for f in self.figures]
        if self.kind == "instant":
            self.quarters = []
            self.instants = sorted((f for f in self.figures if f.period.kind == "instant"), key=lambda f: f.period.instant_date)
        else:
            self.quarters = self._quarters()
            self.instants = []
        self.annual = sorted((f for f in self.figures if f.period.kind == "12 months"), key=lambda f: f.period.end_date)
        self.template = self.figures[0] if self.figures else None

    @staticmethod
    def _screen(f: ResolvedFigure) -> ResolvedFigure:
        """A figure whose disclosures differ by a factor of 100 or more is a likely scale error in some filing: it is not used until resolved."""
        if f.status == "ok" and any("factor of 100" in w for w in f.warnings):
            return replace(f, status="suspect", value=None, reasons=f.reasons + ("disclosures differ by a factor of 100 or more (a likely scale error); not used",))
        return f

    def _quarters(self):
        """Quarters, with every reported quarter cross-checked against the year-to-date difference for the same period when both exist: a factor of 100
        or more marks the reported figure suspect, and the quarters are rebuilt without it."""
        for _ in range(3):
            alternatives = {}
            built = quarters.quarterly(self.figures, self.metric, self._derivation_check, alternatives)
            suspects = set()
            for q in built:
                alt = alternatives.get((q.start, q.end))
                if q.status == "reported" and alt and q.value:
                    ratio = abs(q.value / alt)
                    if ratio >= 100 or ratio <= Decimal("0.01"):
                        suspects.add(q.figure.period.id)
            if not suspects:
                return built
            self.figures = [replace(f, status="suspect", value=None, reasons=f.reasons + (
                "the reported quarter differs from the year-to-date difference for the same period by a factor of 100 or more (a likely scale error); not used",))
                            if f.period.id in suspects and f.status == "ok" else f for f in self.figures]
        return built

    def _derivation_check(self, shorter, longer) -> list:
        """Reasons two year-to-date figures must not be differenced: a capital-expenditure input tagged with a negative sign; a restated input paired with
        an unrestated one from another filing; or a longer figure whose own filing re-presents the shorter period at a different value (the difference
        would mix accounting vintages)."""
        reasons = []
        flagged = [i for f in (shorter, longer) for i in f.observation_ids if "CAPEX_NEGATIVE_AS_REPORTED" in self.index.by_id[i].flags]
        signs = {v > 0 for v in (shorter.value, longer.value) if v is not None and v != 0}
        if flagged or (self.metric == "capex" and len(signs) > 1):
            reasons.append("a year-to-date capital expenditure figure carries a negative sign in its filing; differencing would give a wrong quarter")
        if shorter.value is None or longer.value is None:
            return reasons
        restated = [f for f in (shorter, longer) if self.index.differs_from_first(f)]
        if restated and set(self.index.accessions(shorter.observation_ids)) != set(self.index.accessions(longer.observation_ids)):
            reasons.append("a year-to-date input was restated in a later filing and the other was not re-disclosed with it; the difference could mix accounting vintages")
        for a in self.index.accessions(longer.observation_ids):
            same = [o for o in self.obs if o.accession == a and o.period.id == shorter.period.id]
            changed = next((o for o in same if not financials.same_within_rounding(o.value, shorter.value, o.unit)), None)
            if changed is not None:
                reasons.append(f"the filing of the longer figure ({a}) re-presents the shorter period at {changed.value}, not {shorter.value}; the difference would "
                               "mix accounting vintages")
                break
        return reasons

    def quarter(self, end: str):
        return next((q for q in self.quarters if q.end == end), None)

    def figure(self, end: str):
        return _figure_from_quarter(self.quarter(end), self.template, self.view)

    def previous(self, start: str):
        return self.quarter((date.fromisoformat(start) - timedelta(days=1)).isoformat())

    def year_ago_quarter(self, end: str):
        return next((q for q in reversed(self.quarters) if _year_before(q.end, end)), None)

    def presented(self, accession: str, kind: str, end_before: str, start: str | None = None) -> ResolvedFigure | None:
        """The figure of `kind` ending one year before `end_before`, as presented in filing `accession` (its comparative column)."""
        found = [o for o in self.obs if o.accession == accession and o.period.kind == kind and o.period.end_date and _year_before(o.period.end_date, end_before)
                 and (start is None or o.period.start_date == start)]
        if not found:
            return None
        resolved = financials.resolve(found, self.policy, "as_reported")
        return resolved[0] if len(resolved) == 1 else None

    def comparable_pair(self, end: str):
        """(current figure, year-ago figure, how the year-ago figure was chosen). The year-ago figure is the one presented in the same filing as the current
        figure (or, for a derived quarter, in the same two filings), so stock splits and restatements apply to both sides alike. Without a same-filing
        comparative, flows fall back to the selected disclosure of the year-ago quarter, flagged; per-share amounts and share counts do not."""
        q = self.quarter(end)
        current = _figure_from_quarter(q, self.template, self.view) if q else None
        if current is None:
            return None, None, "no current quarter figure"
        if q.status == "reported":
            for a in self.index.accessions(current.observation_ids):
                prior = self.presented(a, "quarter", end)
                if prior is not None:
                    return current, prior, f"year-ago quarter as presented in the same filing ({a})"
        elif q.status == "derived":
            longer_ids = [i for r, _, i in q.calculation.inputs if r == "year_to_date_longer"]
            shorter_ids = [i for r, _, i in q.calculation.inputs if r == "year_to_date_shorter"]
            longer, shorter = self.index.by_id[longer_ids[0]], self.index.by_id[shorter_ids[0]]
            for a in self.index.accessions(longer_ids):
                for b in self.index.accessions(shorter_ids):
                    p_long = self.presented(a, longer.period.kind, longer.period.end_date)
                    p_short = self.presented(b, shorter.period.kind, shorter.period.end_date, p_long.period.start_date if p_long else None)
                    if p_long is not None and p_short is not None:
                        derived = quarters.quarterly([p_short, p_long], self.metric)
                        dq = next((d for d in derived if d.status == "derived"), None)
                        if dq is not None:
                            return current, _figure_from_quarter(dq, self.template, self.view), \
                                f"year-ago quarter derived from the comparatives presented in the same filings ({a}, {b})"
        if self.kind in ("per_share", "count"):
            return current, None, ("no year-ago comparative is presented in the same filing; per-share amounts and share counts are compared only within one "
                                   "filing's presentation (a stock split or restatement in between would make the comparison meaningless)")
        ago = self.year_ago_quarter(end)
        prior = _figure_from_quarter(ago, self.template, self.view) if ago else None
        return current, prior, ("year-ago quarter not presented in the current filing; compared with its " + self.view.replace("_", "-") + " disclosure"
                                if prior is not None else "no year-ago quarter in the filed history")

    def cell_for_figure(self, f: ResolvedFigure) -> dict:
        for oid in f.observation_ids:
            self.index.brief(oid)
        revisions, rounding = self.index.revisions(f)
        return {"period": _period_dict(f.period), "value": None if f.value is None else str(f.value), "status": "reported" if f.status == "ok" else f.status,
                "observation_ids": list(f.observation_ids), "calculation_id": None, "revisions": revisions, "rounding_differences": rounding,
                "warnings": list(f.warnings), "reasons": list(f.reasons), "flags": self.index.flags(f.observation_ids)}

    def cell_for_quarter(self, q: quarters.Quarter, policy) -> tuple[dict, dict | None]:
        if q.figure is not None:
            cell = self.cell_for_figure(q.figure)
            cell["status"] = q.status
            return cell, None
        record = _calc_dict(q.calculation, policy, self.index, f"{LABELS.get(self.metric, self.metric)}, quarter {q.start} to {q.end}")
        cell = {"period": _period_dict(make_period("quarter", start=q.start, end=q.end)), "value": None if q.value is None else str(q.value),
                "status": q.status, "observation_ids": list(q.input_ids), "calculation_id": record["id"], "revisions": [], "rounding_differences": 0,
                "warnings": [], "reasons": list(q.reasons), "flags": self.index.flags(q.input_ids)}
        return cell, record

    def split_notes(self) -> list:
        """Adjacent periods whose share-based values jump by 1.8x or more: a likely stock split or share restatement. Values on either side are not comparable."""
        if self.kind not in ("per_share", "count") and self.metric != "shares_outstanding":
            return []
        seq = [(q.end, q.value) for q in self.quarters if q.value] if self.quarters else [(f.period.instant_date, f.value) for f in self.instants if f.value]
        out = []
        for (e1, v1), (e2, v2) in zip(seq, seq[1:]):
            if v1 > 0 and v2 > 0 and (v2 / v1 >= Decimal("1.8") or v1 / v2 >= Decimal("1.8")):
                out.append(f"{LABELS[self.metric]} moves from {v1} ({e1}) to {v2} ({e2}): a stock split or share restatement is likely; values on either side "
                           "are not comparable as shown")
        return out


def _calc_dict(result: calc.CalculationResult, policy: AsOfPolicy, index: _Index, label: str) -> dict:
    for _, kind, iid in result.inputs:
        if kind == "observation" and iid in index.by_id:
            index.brief(iid)
    return {"id": calc.calculation_id(result, policy), "label": label, "formula": result.formula, "formula_version": result.formula_version,
            "status": result.status, "value": None if result.value is None else str(result.value), "unit": result.unit,
            "inputs": [{"role": r, "kind": k, "id": i} for r, k, i in result.inputs], "reasons": list(result.reasons), "detail": result.detail,
            "policy": policy.as_dict()}


# The change catalog, in display order. Each entry names what is compared; the computation is in _changes.
CHANGES = (
    ("revenue_yoy", "Revenue, latest quarter vs year-ago quarter", "percent growth"),
    ("operating_margin_yoy", "Operating margin, latest quarter vs year-ago quarter", "percentage points"),
    ("net_income_yoy", "Net income, latest quarter vs year-ago quarter", "percent growth"),
    ("eps_diluted_yoy", "Diluted EPS, latest quarter vs year-ago quarter", "percent growth"),
    ("revenue_qoq", "Revenue, latest quarter vs previous quarter", "percent growth"),
    ("cash_conversion_fy", "Cash from operations / net income, latest fiscal year", "percent of"),
    ("capex_intensity_fy", "Capital expenditures / revenue, latest fiscal year", "percent of"),
    ("cfo_minus_capex_fy", "Cash from operations minus capital expenditures, latest fiscal year", "amount"),
    ("diluted_shares_yoy", "Weighted-average diluted shares, latest quarter vs year-ago quarter", "percent change"),
)
QUARTER_KEYS = ("revenue_yoy", "operating_margin_yoy", "net_income_yoy", "eps_diluted_yoy", "revenue_qoq", "diluted_shares_yoy")


def _missing(formula, reason, unit="percent", figures=()):
    inputs = tuple(("current", "observation", i) for f in figures if f is not None for i in f.observation_ids)
    return calc.CalculationResult(formula, f"{formula}-v1", "missing", None, unit, inputs, (), (reason,))


def _duration_note(cur, prior):
    if cur is None or prior is None or not cur.period.duration_days or not prior.period.duration_days:
        return None
    if abs(cur.period.duration_days - prior.period.duration_days) > 3:
        return f"the periods differ in length ({cur.period.duration_days} vs {prior.period.duration_days} days); not like for like"
    return None


def _changes(series: dict, policy: AsOfPolicy, index: _Index, view: str, business: dict | None = None) -> tuple[list, dict, str | None]:
    """The change catalog at the latest quarter any core series (revenue, net income, diluted EPS) reaches. A series that stops earlier makes its own
    changes missing with that reason, rather than moving every change back to a stale quarter."""
    core = [q for m in ("revenue", "net_income", "eps_diluted") for q in series[m].quarters if q.value is not None]
    latest = max(core, key=lambda q: q.end) if core else None
    out, records = [], {}

    def add(key, result: calc.CalculationResult, periods: str, extra=None):
        label, measure = next((l, m) for k, l, m in CHANGES if k == key)
        record = _calc_dict(result, policy, index, label)
        records[record["id"]] = record
        out.append({"key": key, "label": label, "measure": measure, "periods": periods, "status": result.status,
                    "value": record["value"], "unit": result.unit, "calculation_id": record["id"], "reasons": list(result.reasons),
                    **{k: v for k, v in (extra or {}).items() if v}})

    def notes(*figures, basis=None, pair=None):
        derived = [r for f in figures if f is not None for r in f.reasons if r.startswith("derived")]
        return {"derived_inputs": derived, "comparison_basis": basis, "duration_note": _duration_note(*pair) if pair else None}

    def last_of(metric):
        usable = [q.end for q in series[metric].quarters if q.value is not None]
        return usable[-1] if usable else None

    def absent(metric, end):
        return f"no eligible {LABELS[metric].lower()} for the quarter ended {end}" + (f" (its latest quarter ends {last_of(metric)})" if last_of(metric) else "")

    def yoy(key, metric, end, fn, extra=None):
        s = series[metric]
        formula = "growth" if fn is calc.growth else "share_change"
        q = s.quarter(end)
        if q is None:
            reason = absent(metric, end) + ("; " + quarters.not_derivable_reason(metric) if quarters.not_derivable_reason(metric) else "")
            add(key, _missing(formula, reason), f"quarter ended {end} vs year-ago quarter", extra)
            return None, None, None
        cur, prior, how = s.comparable_pair(end)
        if cur is None:
            add(key, _missing(formula, f"the quarter ended {end} is {q.status.replace('_', ' ')}: " + "; ".join(q.reasons)), f"quarter ended {end} vs year-ago quarter",
                extra)
            return None, None, None
        result = fn(cur, prior) if prior is not None else _missing(formula, how, figures=(cur,))
        add(key, result, f"quarter ended {end} vs year-ago quarter", {**notes(cur, prior, basis=how, pair=(cur, prior)), **(extra or {})})
        return cur, prior, how

    if latest is None:
        for key in QUARTER_KEYS:
            add(key, _missing(key, "no eligible quarterly revenue, net income or diluted EPS in the filed history"), "")
    else:
        end = latest.end
        when = f"quarter ended {end} vs year-ago quarter"
        cur_rev, ago_rev, how = yoy("revenue_yoy", "revenue", end, calc.growth)
        # Operating margin: both sides from the same presentation as revenue.
        cur_op, ago_op, op_how = series["operating_income"].comparable_pair(end) if series["operating_income"].quarter(end) else (None, None, absent("operating_income", end))
        if cur_rev is None:
            m_now = m_then = _missing("operating_margin", absent("revenue", end))
        else:
            m_now = calc.operating_margin(cur_op, cur_rev) if cur_op is not None else _missing("operating_margin", op_how)
            m_then = calc.operating_margin(ago_op, ago_rev) if ago_op is not None and ago_rev is not None else \
                _missing("operating_margin", "no comparable year-ago operating income and revenue: " + (op_how if ago_op is None else how or "no year-ago revenue"))
        margin_ids = []
        for r_, lab in ((m_now, f"Operating margin, quarter ended {end}"), (m_then, "Operating margin, year-ago quarter")):
            rec = _calc_dict(r_, policy, index, lab)
            records[rec["id"]] = rec
            margin_ids.append(rec["id"])
        add("operating_margin_yoy", calc.point_change(m_now, m_then, policy=policy), when,
            {"current_margin": None if m_now.value is None else str(m_now.value), "prior_margin": None if m_then.value is None else str(m_then.value),
             "current_margin_calculation_id": margin_ids[0], "prior_margin_calculation_id": margin_ids[1],
             **notes(cur_op, ago_op, cur_rev, ago_rev, basis=op_how, pair=(cur_op, ago_op))})
        yoy("net_income_yoy", "net_income", end, calc.growth)
        yoy("eps_diluted_yoy", "eps_diluted", end, calc.growth)
        # Quarter over quarter: withheld when the current filing restates comparatives (a basis change between the two quarters).
        qoq_when = f"quarter ended {end} vs previous quarter"
        if cur_rev is None:
            add("revenue_qoq", _missing("growth", absent("revenue", end)), qoq_when)
        else:
            prev = series["revenue"].previous(series["revenue"].quarter(end).start)
            prev_fig = _figure_from_quarter(prev, series["revenue"].template, view) if prev else None
            restated = None
            if ago_rev is not None and how and "same filing" in how:
                first = index.first_disclosure([o.id for o in series["revenue"].obs if o.period.id == ago_rev.period.id])
                if first is not None and ago_rev.value is not None and not financials.same_within_rounding(first.value, ago_rev.value, first.unit):
                    restated = f"the current filing re-presents the year-ago quarter at {ago_rev.value} (first reported {first.value}): a basis change, so the " \
                               "previous quarter's own disclosure is on the earlier basis"
            if prev_fig is None:
                result = _missing("growth", "no previous contiguous revenue quarter", figures=(cur_rev,))
            elif restated:
                result = calc.CalculationResult("growth", "growth-v1", "incompatible", None, "percent", calc._inputs(current=cur_rev, prior=prev_fig), (), (restated,))
            else:
                result = calc.growth(cur_rev, prev_fig)
            add("revenue_qoq", result, qoq_when, notes(cur_rev, prev_fig, basis="previous quarter's " + view.replace("_", "-") + " disclosure",
                                                       pair=(cur_rev, prev_fig)))
        yoy("diluted_shares_yoy", "diluted_shares", end, calc.share_change,
            {"note": "weighted-average diluted shares for each quarter; not period-end shares outstanding"})
    years = [f.period.end_date for f in series["revenue"].annual if f.value is not None]
    fy = years[-1] if years else None

    def annual(metric):
        return next((f for f in series[metric].annual if f.period.end_date == fy), None) if fy else None

    fy_label = f"fiscal year ended {fy}" if fy else "no eligible fiscal year"
    for key, result in (("cash_conversion_fy", calc.cash_conversion(annual("operating_cash_flow"), annual("net_income"))),
                        ("capex_intensity_fy", calc.capex_intensity(annual("capex"), annual("revenue"))),
                        ("cfo_minus_capex_fy", calc.cfo_minus_capex(annual("operating_cash_flow"), annual("capex")))):
        if business and business.get("supported") is False:
            # A bank's or insurer's operating cash flow mixes lending, deposits and trading; these operating-company ratios would mislead.
            result = calc.CalculationResult(result.formula, result.formula_version, "not_applicable", None, result.unit, result.inputs, (),
                                            (business["reason"] + "; operating-company cash-flow ratios are not meaningful for it",))
        add(key, result, fy_label)
    order = {k: i for i, (k, *_) in enumerate(CHANGES)}
    out.sort(key=lambda c: order[c["key"]])
    return out, records, (latest.end if latest else None)


def _questions(changes: dict, revised: list, reconciliation: list, conflicts: list) -> list:
    """Neutral research questions raised by the computed changes, each citing its inputs. They state no cause and recommend nothing."""
    out = []
    rev, margin = changes.get("revenue_yoy"), changes.get("operating_margin_yoy")
    if rev and margin and rev["status"] == "ok" and margin["status"] == "ok":
        out.append({"text": f"Revenue changed {_pct(rev['value'])} year over year while operating margin changed {_pp(margin['value'])}. Which cost lines moved "
                            "faster or slower than revenue? Possible explanations include mix, pricing, one-off items and accounting changes; check the filing's "
                            "discussion before concluding.", "cites": [rev["calculation_id"], margin["calculation_id"]]})
    ni = changes.get("net_income_yoy")
    if rev and ni and rev["status"] == "ok" and ni["status"] == "ok" and (Decimal(ni["value"]) - Decimal(rev["value"])).copy_abs() >= 10:
        out.append({"text": f"Net income changed {_pct(ni['value'])} against revenue {_pct(rev['value'])}. Do below-the-line items (interest, tax, other income) "
                            "explain the gap?", "cites": [rev["calculation_id"], ni["calculation_id"]]})
    cc = changes.get("cash_conversion_fy")
    if cc and cc["status"] == "ok":
        out.append({"text": f"Cash from operations was {_pct(cc['value'], signed=False)} of net income in the latest fiscal year. Which working-capital, "
                            "non-cash and timing items explain the difference from 100%?", "cites": [cc["calculation_id"]]})
    elif cc and cc["status"] == "not_applicable" and any("zero or negative" in r for r in cc["reasons"]):
        out.append({"text": "Net income was zero or negative in the latest fiscal year, so cash conversion is not meaningful. How did operating cash flow behave?",
                    "cites": [cc["calculation_id"]]})
    sh = changes.get("diluted_shares_yoy")
    if sh and sh["status"] == "ok" and Decimal(sh["value"]).copy_abs() >= 1:
        out.append({"text": f"Weighted-average diluted shares changed {_pct(sh['value'])} year over year. Do buybacks, issuance, equity compensation or convertible "
                            "instruments explain it?", "cites": [sh["calculation_id"]]})
    for r in sorted(revised, key=lambda r: r["end"], reverse=True)[:3]:
        out.append({"text": f"{r['label']} for {r['period']} was first reported as {r['first']} and later disclosed as {r['later']} ({r['form']} filed "
                            f"{r['filed']}). What does the later filing say changed?", "cites": r["observation_ids"]})
    for r in reconciliation:
        if r["status"] == "differs":
            out.append({"text": f"The release's {LABELS.get(r['metric'], r['metric'])} for {r['period']} differs from the filed figure beyond printed rounding. "
                                "Which is restated or differently defined?", "cites": [r["release_observation"]] + r.get("filing_observations", [])})
    for c in conflicts[:3]:
        if c["kind"] == "conflicted_figure":
            out.append({"text": f"{c['label']} for {c['period']} has conflicting disclosures at the same time ({c['detail']}). Which tag or filing is right?",
                        "cites": c["observation_ids"]})
    return out


def _pct(value, signed=True):
    v = Decimal(value).quantize(Decimal("0.1"))
    return (f"{v:+}" if signed else f"{v}") + "%"


def _pp(value):
    return f"{Decimal(value).quantize(Decimal('0.1')):+} percentage points"


def _one_interpretation(observations: list) -> list:
    """Within one preserved source, use one interpretation: the parser/mapping version recorded last among those eligible. A source re-read by a newer
    parser does not corroborate or conflict with its own earlier reading."""
    groups = {}
    for o in observations:
        groups.setdefault(o.source_document_id, {}).setdefault((o.parser_version, o.mapping_version), []).append(o)
    keep = set()
    for versions in groups.values():
        chosen = max(versions.values(), key=lambda g: (min(o.recorded_at for o in g), min(o.id for o in g)))
        keep.update(o.id for o in chosen)
    return [o for o in observations if o.id in keep]


def _concept_precedence(observations: list) -> list:
    """For filed facts, keep per metric and period only the first concept present in companyfacts.CONCEPT_PRECEDENCE (different line items mapped to one
    metric are not treated as revisions or conflicts of each other)."""
    best = {}
    for o in observations:
        order = companyfacts.CONCEPT_PRECEDENCE.get(o.metric)
        if o.provider == FILINGS and order and o.concept in order:
            key = (o.metric, o.period.id)
            best[key] = min(best.get(key, len(order)), order.index(o.concept))
    out = []
    for o in observations:
        order = companyfacts.CONCEPT_PRECEDENCE.get(o.metric)
        if o.provider == FILINGS and order and o.concept in order and order.index(o.concept) != best[(o.metric, o.period.id)]:
            continue
        out.append(o)
    return out


def assemble(security: dict, identity: dict | None, observations: list, policy: AsOfPolicy, view: str = "as_reported", submissions: dict | None = None,
             submissions_observed_at: str | None = None, documents: list | None = None, question: str | None = None, scenarios: list | None = None) -> dict:
    """The dossier from every recorded observation of the company (pure). Eligibility is applied here first; nothing ineligible contributes a value."""
    if view not in ("as_reported", "latest"):
        raise ValueError("view must be as_reported or latest")
    eligible = _one_interpretation([o for o in observations if eligibility(o.availability(), policy)[0]])
    eligible = _concept_precedence(eligible)
    index = _Index(eligible)
    filings = financials.resolve([o for o in eligible if o.provider == FILINGS], policy, view)
    releases = financials.resolve([o for o in eligible if o.provider == RELEASES], policy, view)
    series = {m: _Series(m, filings, eligible, index, policy, view) for m in HISTORY_METRICS}
    business = companyfacts.business_type(submissions)
    changes, records, latest_end = _changes(series, policy, index, view, business)

    history = {"quarterly": {}, "annual": {}, "instant": {}, "ttm": {}, "other_groups": {}, "notes": {}}
    revised, conflicts = [], []
    for metric, s in series.items():
        if s.other_groups:
            history["other_groups"][metric] = s.other_groups
        if s.split_notes():
            history["notes"][metric] = s.split_notes()
        if s.quarters:
            cells = []
            for q in s.quarters[-QUARTERS_SHOWN:]:
                cell, record = s.cell_for_quarter(q, policy)
                if record:
                    records[record["id"]] = record
                cells.append(cell)
            history["quarterly"][metric] = cells
            t = quarters.ttm(s.quarters, s.quarters[-1].end, metric)
            if t.status != "not_applicable":
                r = _calc_dict(t, policy, index, f"{LABELS[metric]}, trailing four quarters to {s.quarters[-1].end}")
                records[r["id"]] = r
                history["ttm"][metric] = r["id"]
        if s.annual:
            history["annual"][metric] = [s.cell_for_figure(f) for f in s.annual[-YEARS_SHOWN:]]
        if s.instants:
            history["instant"][metric] = [s.cell_for_figure(f) for f in s.instants[-INSTANTS_SHOWN:]]
        for f in s.figures:
            if f.status == "conflicted":
                conflicts.append({"kind": "conflicted_figure", "metric": metric, "label": LABELS[metric], "period": f.period.label, "end": _end(f.period),
                                  "detail": "; ".join(f.reasons),
                                  "observation_ids": [index.brief(i)["id"] for i in f.observation_ids]})
            for w in f.warnings:
                conflicts.append({"kind": "disclosure_disagreement", "metric": metric, "label": LABELS[metric], "period": f.period.label, "end": _end(f.period),
                              "detail": w,
                                  "observation_ids": [index.brief(i)["id"] for i in f.observation_ids + f.other_ids]})
            changed, _ = index.revisions(f)
            if changed and f.value is not None:
                if view == "as_reported":
                    # The selected figure is the first disclosure; the revision is the latest differing one.
                    other = changed[-1]
                    first, later, source = str(f.value), other["value"], other
                else:
                    # The selected figure is the latest disclosure; name the filing that disclosed it, not the one that first reported the old value.
                    other = changed[0]
                    own = index.first_disclosure(f.observation_ids)
                    first, later, source = other["value"], str(f.value), {"form": own.form, "filed": own.filed, "observation_id": own.id}
                revised.append({"metric": metric, "label": LABELS[metric], "period": f.period.label, "end": _end(f.period), "first": first, "later": later,
                                "form": source["form"], "filed": source["filed"], "observation_ids": list(f.observation_ids) + [other["observation_id"]]})
    release_figs = [f for f in releases if f.period.kind == "quarter"]
    latest_release_end = max((f.period.end_date for f in release_figs if f.period.end_date), default=None)
    release_shown = [f for f in release_figs if f.period.end_date == latest_release_end] if latest_release_end else []
    release_obs = [index.by_id[i] for f in release_shown for i in f.observation_ids[:1]]
    reconciliation = financials.reconcile(release_obs, [o for o in eligible if o.provider == FILINGS]) if release_obs else []
    for r in reconciliation:
        index.brief(r["release_observation"])
        for i in r.get("filing_observations", []):
            index.brief(i)
    release = {"period_end": latest_release_end,
               "figures": [{"metric": f.metric, "label": LABELS.get(f.metric, f.metric), "basis": f.basis, "value": None if f.value is None else str(f.value),
                            "unit": f.unit, "currency": f.currency, "period": f.period.label, "status": f.status,
                            "observation_ids": [index.brief(i)["id"] for i in f.observation_ids]} for f in release_shown],
               "reconciliation": [{k: (str(v) if isinstance(v, Decimal) else v) for k, v in r.items()} for r in reconciliation]}
    for doc in documents or []:
        if doc.get("extraction_status") == "needs_review" and eligibility({"published_at": doc.get("published_at"),
                                                                            "publication_date": (doc.get("metadata") or {}).get("publication_date"),
                                                                            "observed_at": doc.get("observed_at")}, policy)[0]:
            conflicts.append({"kind": "release_needs_review", "metric": None, "label": doc["filename"], "period": "unresolved", "end": "9999-12-31",
                              "detail": (doc.get("metadata") or {}).get("review_reason", "reported period unresolved"), "observation_ids": []})
    by_key = {c["key"]: c for c in changes}
    metrics_cov = {}
    for metric in HISTORY_METRICS:
        own = [o for o in eligible if o.metric == metric]
        if own:
            ends = sorted(_end(o.period) for o in own)
            metrics_cov[metric] = {"label": LABELS[metric], "observations": len(own), "providers": sorted({o.provider for o in own}),
                                   "first_end": ends[0], "last_end": ends[-1], "quarters": len(series[metric].quarters), "annual": len(series[metric].annual),
                                   "instants": len(series[metric].instants)}
    if submissions is not None:
        business["source"] = f"current SEC submissions metadata observed {submissions_observed_at}; not a historical classification"
    eligible_docs = [d for d in documents or [] if d.get("role") in ("current", "comparison") and eligibility(
        {"published_at": d.get("published_at"), "publication_date": (d.get("metadata") or {}).get("publication_date"), "observed_at": d.get("observed_at")}, policy)[0]]
    return {
        "schema": SCHEMA, "question": question, "policy": policy.as_dict(), "view": view,
        "company": {"security_id": security["id"], "ticker": security["ticker"], "name": security["name"], "cik": security.get("cik"),
                    "venue": security.get("venue"), "listing_currency": security.get("currency"), "issuer_id": (identity or {}).get("issuer_id")},
        "coverage": {"eligible_observations": len(eligible), "by_provider": dict(Counter(o.provider for o in eligible)),
                     "policy_note": POLICY_NOTES[policy.policy_version], "metrics": metrics_cov,
                     "absent_metrics": [m for m in HISTORY_METRICS if m not in metrics_cov], "business_type": business,
                     "releases": {"eligible": len(eligible_docs)}, "scope_note": SCOPE_NOTE},
        "latest_quarter_end": latest_end,
        "changes": changes,
        "supported_changes": [c["key"] for c in changes if c["status"] == "ok"][:SUPPORTED_SHOWN],
        "history": history,
        "release": release,
        "revisions": revised,
        "conflicts": conflicts,
        "questions": _questions(by_key, revised, release["reconciliation"], conflicts),
        "chronology": companyfacts.filing_chronology([o for o in eligible if o.provider == FILINGS], submissions),
        "scenarios": scenarios or [],
        "calculations": records,
        "observations": index.used,
    }


def build(service, security_id: str, policy: AsOfPolicy, view: str = "as_reported", question: str | None = None) -> dict:
    """Read the store and assemble the dossier (the imperative shell around assemble)."""
    store = service.store
    security = store.get_security(security_id)
    repo = financials.FinancialRepository(store)
    docs = store.documents(security_id)
    cutoff = policy.as_dict()["cutoff"]
    # The submissions response (business classification, raw acceptance times) and the issuer mapping are chosen so that nothing recorded later changes
    # an earlier view: in observed mode the latest held by the cutoff; in public mode the earliest preserved (labelled current metadata at that time).
    subs = sorted((d for d in docs if d["metadata"].get("kind") == "SEC submissions response"), key=lambda d: (d["observed_at"], d["id"]))
    if policy.mode == "observed":
        subs = [d for d in subs if d["observed_at"] <= cutoff][-1:]
    subs_doc = subs[0] if subs else None
    submissions = json.loads(store.raw(subs_doc["id"])) if subs_doc else None
    identity_as_of = cutoff if policy.mode == "observed" else None
    from . import identity as identity_model
    with store._connection() as db:
        ident = identity_model.current(db, security_id, identity_as_of)
    shown_security = {**security, "cik": (ident or {}).get("cik") if policy.mode == "observed" else security.get("cik")}
    return assemble(shown_security, ident, repo.all_for(security_id, identity_as_of=identity_as_of), policy, view, submissions,
                    subs_doc["observed_at"] if subs_doc else None, docs, question, scenario_summaries(service, security_id, policy, submissions))


def scenario_summaries(service, security_id: str, policy: AsOfPolicy, submissions: dict | None) -> list:
    """For each assumption set, the latest version saved at or before the cutoff (a scenario written later is hindsight, so it is absent), run without
    recording: status, value, and what is missing for a per-share value."""
    from . import model, scenarios
    cutoff = policy.as_dict()["cutoff"]
    business = companyfacts.business_type(submissions)
    out = []
    for s in scenarios.assumption_sets(service, security_id):
        versions = [v for v in scenarios.history(service, s["id"]) if v["created_at"] <= cutoff]
        if not versions:
            continue
        v = versions[0]
        valuation = model.run(model.validate(v["assumptions"]), business)
        out.append({"set_id": s["id"], "version_id": v["id"], "scenario": s["scenario"], "name": s["name"], "version": v["version"], "saved_at": v["created_at"],
                    "status": valuation.status, "per_share": None if valuation.per_share is None else str(valuation.per_share),
                    "enterprise_value": None if valuation.enterprise_value is None else str(valuation.enterprise_value),
                    "currency": v["assumptions"].get("currency"), "warnings": list(valuation.warnings), "limitations": list(valuation.limitations),
                    "rationale": v["rationale"]})
    return out


# ---- presentation helpers shared by the page and the Markdown export ----

def display(value, unit, currency=None) -> str:
    """Readable value; currency amounts in millions, shares in millions, per-share to two decimals. The exact value stays in the JSON."""
    if value is None:
        return "—"
    v = Decimal(value)
    if unit in ("percent",):
        return f"{v.quantize(Decimal('0.1'))}%"
    if unit == "percentage points":
        return f"{v.quantize(Decimal('0.1')):+} pp"
    if unit == "currency/share":
        return f"{currency + ' ' if currency else ''}{v.quantize(Decimal('0.01')):,}"
    if unit in ("currency", "shares"):
        m = (v / Decimal(10**6)).quantize(Decimal("0.1"))
        return f"{currency + ' ' if currency and unit == 'currency' else ''}{m:,}m"
    return str(v)


def series_unit(dossier: dict, metric: str) -> tuple[str, str | None]:
    for group in ("quarterly", "annual", "instant"):
        for cell in dossier["history"][group].get(metric, []):
            for oid in cell["observation_ids"]:
                o = dossier["observations"].get(oid)
                if o:
                    return o["unit"], o["currency"]
    return _unit_family(metric), None


def md_text(text, single_line=True) -> str:
    """Free text (a question, a name, a rationale) as inert Markdown: inline control characters and raw HTML are escaped everywhere, block markers
    (headings, list items, quotes) at the start of a line, and single-line fields have their line breaks collapsed. The text cannot create headings,
    list items, links or raw HTML in an export."""
    text = str(text or "")
    lines = [" ".join(text.split())] if single_line else [" ".join(line.split()) for line in text.splitlines()]
    out = []
    for line in lines:
        line = re.sub(r"([\\`*_{}\[\]<>|~!])", r"\\\1", line)
        line = re.sub(r"^([#+\-=])", r"\\\1", line)
        out.append(re.sub(r"^(\d+)([.)])", r"\1\\\2", line))
    return "\n".join(out)


def render_markdown(d: dict) -> str:
    """The same read model as text. Every value is followed by its provenance identifiers in the JSON export."""
    c, p = d["company"], d["policy"]
    lines = [f"# Company dossier: {md_text(c['ticker'])} ({md_text(c['name'])})", "",
             f"Information cutoff {p['cutoff']} · {p['mode']} mode · policy {p['policy_version']} · {d['view'].replace('_', ' ')} view · {d['schema']}", ""]
    if d.get("question"):
        lines += [f"**Question:** {md_text(d['question'])}", ""]
    cov = d["coverage"]
    lines += ["## Coverage", "", cov["scope_note"], "",
              f"- Eligible observations: {cov['eligible_observations']} ({', '.join(f'{k}: {v}' for k, v in sorted(cov['by_provider'].items())) or 'none'})",
              f"- Availability: {cov['policy_note']}",
              f"- Eligible releases: {cov['releases']['eligible']}",
              f"- Absent metrics: {', '.join(LABELS[m] for m in cov['absent_metrics']) or 'none'}",
              f"- Business type: {'supported' if cov['business_type']['supported'] else 'not supported: ' + str(cov['business_type']['reason']) if cov['business_type']['supported'] is False else 'unknown'}",
              ""]
    lines += ["## Supported changes", ""]
    shown = [ch for ch in d["changes"] if ch["key"] in d["supported_changes"]]
    for ch in shown:
        lines.append(f"- **{ch['label']}**: {display(ch['value'], ch['unit'], None) if ch['unit'] != 'currency' else display(ch['value'], 'currency')} "
                     f"({ch['periods']}; calculation `{ch['calculation_id']}`)" + (" — uses a derived quarter" if ch.get("derived_inputs") else ""))
    if not shown:
        lines.append("- None: the eligible evidence supports no change in the catalog.")
    unavailable = [ch for ch in d["changes"] if ch["status"] != "ok"]
    if unavailable:
        lines += ["", "Not available:", ""]
        lines += [f"- {ch['label']}: {ch['status'].replace('_', ' ')} — {'; '.join(ch['reasons'])}" for ch in unavailable]
    lines += ["", "## Scenarios saved by this cutoff", ""]
    for sc in d.get("scenarios", []):
        value = display(sc["per_share"], "currency/share", sc["currency"]) + " per share" if sc["per_share"] else (
            display(sc["enterprise_value"], "currency", sc["currency"]) + " enterprise value" if sc["enterprise_value"] else sc["status"].replace("_", " "))
        lines.append(f"- {sc['scenario']} · {md_text(sc['name'])} v{sc['version']} (saved {sc['saved_at']}): {value}" + (f"; {'; '.join(sc['warnings'][-1:])}" if sc["warnings"] else ""))
    if not d.get("scenarios"):
        lines.append("- None saved by this cutoff.")
    lines += ["", "## Filed history (quarters)", ""]
    for metric, cells in d["history"]["quarterly"].items():
        unit, cur = series_unit(d, metric)
        row = " | ".join(f"{cell['period']['end']}: {display(cell['value'], unit, cur)}{' (derived)' if cell['status'] == 'derived' else ''}"
                         f"{' (conflicted)' if cell['status'] == 'conflicted' else ''}" for cell in cells)
        lines.append(f"- {LABELS[metric]}: {row}")
    lines += ["", "## Filed history (fiscal years)", ""]
    for metric, cells in d["history"]["annual"].items():
        unit, cur = series_unit(d, metric)
        lines.append(f"- {LABELS[metric]}: " + " | ".join(f"{cell['period']['end']}: {display(cell['value'], unit, cur)}" for cell in cells))
    if d["history"]["instant"]:
        lines += ["", "## Balances", ""]
        for metric, cells in d["history"]["instant"].items():
            unit, cur = series_unit(d, metric)
            lines.append(f"- {LABELS[metric]}: " + " | ".join(f"{cell['period']['instant']}: {display(cell['value'], unit, cur)}" for cell in cells))
    rel = d["release"]
    lines += ["", "## Latest release figures and reconciliation", ""]
    if rel["figures"]:
        for f in rel["figures"]:
            lines.append(f"- {f['label']} ({f['basis']}, {f['period']}): {display(f['value'], f['unit'], f['currency'])}")
        for r in rel["reconciliation"]:
            lines.append(f"  - reconciliation {LABELS.get(r['metric'], r['metric'])} {r['basis']}: {r['status'].replace('_', ' ')}" + (f" — {r['reason']}" if r.get("reason") else ""))
    else:
        lines.append("- No eligible release figures.")
    lines += ["", "## Conflicts, revisions and limitations", ""]
    for r in d["revisions"]:
        lines.append(f"- {r['label']} {r['period']}: first {r['first']}, later {r['later']} ({r['form']} filed {r['filed']})")
    for cf in d["conflicts"]:
        lines.append(f"- {cf['label']} {cf['period']}: {cf['detail']}")
    if not d["revisions"] and not d["conflicts"]:
        lines.append("- None recorded at this cutoff.")
    lines += ["", "## Research questions", ""]
    lines += [f"- {q['text']}" for q in d["questions"]] or ["- None raised by the computed changes."]
    lines += ["", "## Filing chronology", ""]
    lines += [f"- {f['filed']} {f['form']} {f['accession']} ({f['observations']} observations)" for f in d["chronology"][-12:]] or ["- No eligible filings."]
    lines += ["", "Interpretation, materiality and any decision are the analyst's. No price, valuation or recommendation is implied by this dossier.", ""]
    return "\n".join(lines)


TABLE_LIMITS = {"quarterly": QUARTERS_SHOWN, "annual": YEARS_SHOWN, "instant": INSTANTS_SHOWN}


def history_table(d: dict, group: str, limit: int | None = None) -> dict:
    """{'columns': [period ends, oldest first], 'rows': [{'metric', 'label', 'unit', 'currency', 'cells': {end: cell}}]} for one history group
    ('quarterly', 'annual' or 'instant'), for display."""
    key = "instant" if group == "instant" else "end"
    ends = sorted({cell["period"][key] for cells in d["history"][group].values() for cell in cells if cell["period"][key]})
    ends = ends[-(limit or TABLE_LIMITS[group]):]
    rows = []
    for metric, cells in d["history"][group].items():
        unit, currency = series_unit(d, metric)
        by_end = {cell["period"][key]: cell for cell in cells}
        if any(e in by_end for e in ends):
            rows.append({"metric": metric, "label": LABELS.get(metric, metric), "unit": unit, "currency": currency, "cells": by_end,
                         "ttm": d["history"]["ttm"].get(metric) if group == "quarterly" else None, "notes": d["history"]["notes"].get(metric, [])})
    return {"columns": ends, "rows": rows}
