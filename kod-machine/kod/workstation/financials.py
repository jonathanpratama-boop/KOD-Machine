"""Immutable financial observations and the one cutoff-aware way to read them.

An observation is one reported value as one provider interpreted it from one preserved source: the original concept and raw text, the canonical value in base
units, the period, basis, currency and context, the filing lineage where known, an exact evidence locator, and the source's availability. Observations are never
updated; a corrected mapping or a new parser version records a new observation and leaves the old one (and anything saved from it) intact.

Reads go through FinancialRepository.observations(..., policy): eligibility at the cutoff is applied first, then the caller selects an as-reported or latest-known
view. Missing, unsupported, conflicted and incompatible are reported as such; nothing is filled in.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json

from .. import earnings
from .domain import canonical, identity
from .identity import METRIC_VERSION
from .policy import AsOfPolicy, available_from, eligibility

RELEASE_PROVIDER = "issuer_release_table"
RELEASE_MAPPING = "KOD-RELEASE-MAP-v1"
SCALES = {"thousands": 10**3, "millions": 10**6, "billions": 10**9}
UNIT_OF = {"per_share": "currency/share", "percent": "percent"}


@dataclass(frozen=True, slots=True)
class Period:
    id: str
    kind: str
    start_date: str | None
    end_date: str | None
    instant_date: str | None
    fiscal_label: str | None
    duration_days: int | None

    @property
    def label(self) -> str:
        if self.instant_date:
            return f"as of {self.instant_date}"
        if self.end_date:
            return f"{self.kind} ended {self.end_date}" + (f" ({self.fiscal_label})" if self.fiscal_label else "")
        return self.fiscal_label or self.kind


def period(kind: str, start=None, end=None, instant=None, fiscal_label=None) -> Period:
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 if start and end else None
    pid = identity("per", kind, start, end, instant, fiscal_label)
    return Period(pid, kind, start, end, instant, fiscal_label, days)


def duration_kind(start: str, end: str) -> str:
    """Classify a reported duration. 52/53-week fiscal periods vary by a few days; anything else is named by its length."""
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    for kind, low, high in (("quarter", 84, 98), ("6 months", 175, 189), ("9 months", 266, 280), ("12 months", 357, 372)):
        if low <= days <= high:
            return kind
    return f"{days} days"


@dataclass(frozen=True, slots=True)
class FinancialObservation:
    id: str
    provider: str
    issuer_id: str | None
    security_id: str | None
    concept: str
    taxonomy: str
    metric: str | None
    metric_version: int | None
    raw_value: str
    value: Decimal
    unit: str
    scale: int | None
    currency: str | None
    currency_basis: str | None
    period: Period
    basis: str
    context: str
    accession: str | None
    form: str | None
    filed: str | None
    amendment: bool | None
    source_document_id: str | None
    source_sha256: str
    evidence: dict
    published_at: str | None
    publication_date: str | None
    publication_precision: str
    publication_basis: str
    observed_at: str
    recorded_at: str
    parser_version: str
    mapping_version: str
    flags: tuple

    def availability(self) -> dict:
        return {"published_at": self.published_at, "publication_date": self.publication_date, "observed_at": self.observed_at}

    def comparable_key(self) -> tuple:
        """Two observations may stand for the same figure only if all of these agree."""
        return (self.metric, self.period.id, self.basis, self.unit, self.scale, self.currency, self.context)


def release_rows(document: dict, security_id: str, issuer_id: str | None, facts: list, resolution: dict, now: str) -> tuple[list, list]:
    """Periods and observations for the figures a release table yields (pure). The reported quarter's end date is attached to its label only when the
    release itself states it (resolution basis RELEASE_STATEMENT)."""
    periods, rows = {}, []
    stated_end = resolution.get("end") if resolution.get("basis") == "RELEASE_STATEMENT" else None
    accession = (document.get("metadata", {}).get("header_link") or {}).get("accession") if (document.get("metadata", {}).get("header_link") or {}).get("status") == "matched" else None
    for f in facts:
        info = f["period_info"]
        if info["end"]:
            p = period(info["kind"], end=info["end"].isoformat())
        elif f["period"] == resolution.get("period") and stated_end:
            p = period(info["kind"], end=stated_end, fiscal_label=f["period"])
        else:
            p = period(info["kind"], fiscal_label=f["period"])
        periods[p.id] = p
        printed = Decimal(f["value"])
        scale = 1 if f["unit"] == "per_share" else SCALES.get(f["unit"])
        value = printed * scale if scale else printed
        unit = UNIT_OF.get(f["unit"], "currency" if f["currency"] or f["unit"] in SCALES or f["unit"] == "unscaled" else "pure")
        if f["metric"] == "gross_margin":
            unit, scale = "percent", None
        evidence = {k: f["evidence"].get(k) for k in ("table", "row", "label", "quote", "alignment", "label_cells", "value_cells", "header_cells", "currency_quote")}
        evidence["document_id"] = document["id"]
        if p.end_date and not info["end"]:
            evidence["period_end_basis"] = "release statement: " + "; ".join(str(e) for e in resolution.get("evidence", []))
        flags = list(f["flags"]) + (["UNIT_SCALE_UNKNOWN"] if f["unit"] == "unscaled" and "UNIT_SCALE_UNKNOWN" not in f["flags"] else [])
        oid = identity("fob", RELEASE_PROVIDER, document["id"], document["sha256"], f["evidence"].get("table"), f["evidence"].get("row"),
                       f["evidence"].get("value_cells"), f["evidence"]["label"], f["metric"], METRIC_VERSION, earnings._decimal_string(value), unit, scale,
                       f["currency"], p.id, f["basis"], earnings.PARSER_VERSION, RELEASE_MAPPING)
        rows.append({"id": oid, "provider": RELEASE_PROVIDER, "issuer_id": issuer_id, "security_id": security_id, "concept": f["evidence"]["label"],
                     "taxonomy": "issuer-release-table", "metric": f["metric"], "metric_version": METRIC_VERSION, "raw_value": f["value"],
                     "value": earnings._decimal_string(value), "unit": unit, "scale": scale, "currency": f["currency"],
                     "currency_basis": f["evidence"].get("currency_basis"), "period_id": p.id, "basis": f["basis"], "context": "consolidated (release table)",
                     "dimensions_available": 0, "accession": accession, "form": None, "filed": None, "amendment": None, "source_document_id": document["id"],
                     "source_sha256": document["sha256"], "evidence": canonical(evidence), "published_at": document["published_at"],
                     "publication_date": document.get("metadata", {}).get("publication_date"),
                     "publication_precision": document.get("metadata", {}).get("publication_precision", "unknown"), "publication_basis": document["published_basis"],
                     "observed_at": document["observed_at"], "recorded_at": now, "parser_version": earnings.PARSER_VERSION, "mapping_version": RELEASE_MAPPING,
                     "flags": canonical(sorted(set(flags)))})
    return list(periods.values()), rows


COLUMNS = ("id", "provider", "issuer_id", "security_id", "concept", "taxonomy", "metric", "metric_version", "raw_value", "value", "unit", "scale", "currency",
           "currency_basis", "period_id", "basis", "context", "dimensions_available", "accession", "form", "filed", "amendment", "source_document_id", "source_sha256",
           "evidence", "published_at", "publication_date", "publication_precision", "publication_basis", "observed_at", "recorded_at", "parser_version",
           "mapping_version", "flags")


def insert(db, periods, rows) -> int:
    """Record periods and observations; an existing identical observation (same source, interpretation and versions) is not duplicated."""
    for p in periods:
        db.execute("INSERT OR IGNORE INTO periods VALUES (?,?,?,?,?,?,?)", (p.id, p.kind, p.start_date, p.end_date, p.instant_date, p.fiscal_label, p.duration_days))
    before = db.total_changes
    for row in rows:
        db.execute(f"INSERT OR IGNORE INTO financial_observations({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})", tuple(row[c] for c in COLUMNS))
    return db.total_changes - before


def _from_row(r) -> FinancialObservation:
    p = Period(r["period_id"], r["kind"], r["start_date"], r["end_date"], r["instant_date"], r["fiscal_label"], r["duration_days"])
    return FinancialObservation(
        r["id"], r["provider"], r["issuer_id"], r["security_id"], r["concept"], r["taxonomy"], r["metric"], r["metric_version"], r["raw_value"], Decimal(r["value"]),
        r["unit"], r["scale"], r["currency"], r["currency_basis"], p, r["basis"], r["context"], r["accession"], r["form"], r["filed"],
        None if r["amendment"] is None else bool(r["amendment"]), r["source_document_id"], r["source_sha256"], json.loads(r["evidence"]), r["published_at"],
        r["publication_date"], r["publication_precision"], r["publication_basis"], r["observed_at"], r["recorded_at"], r["parser_version"], r["mapping_version"],
        tuple(json.loads(r["flags"])))


class FinancialRepository:
    """Cutoff-aware reads over the store's observation tables."""

    def __init__(self, store):
        self.store = store

    def _query(self, where, args):
        with self.store._connection() as db:
            rows = db.execute(f"""SELECT o.*, p.kind, p.start_date, p.end_date, p.instant_date, p.fiscal_label, p.duration_days
                                  FROM financial_observations o JOIN periods p ON p.id=o.period_id WHERE {where}
                                  ORDER BY o.metric, p.end_date, p.instant_date, o.recorded_at, o.id""", args).fetchall()
        return [_from_row(r) for r in rows]

    def all_for(self, security_id: str, metric: str | None = None) -> list:
        """Every recorded observation, eligible or not: for provenance views and tests only. Analysis must use observations()."""
        issuer = self.issuer_of(security_id)
        where = "(o.security_id=? OR (o.issuer_id IS NOT NULL AND o.issuer_id=?))" + (" AND o.metric=?" if metric else "")
        return self._query(where, (security_id, issuer, metric) if metric else (security_id, issuer))

    def issuer_of(self, security_id: str):
        from . import identity as identity_model
        with self.store._connection() as db:
            found = identity_model.current(db, security_id)
        return found["issuer_id"] if found else None

    def observations(self, security_id: str, metric: str | None, policy: AsOfPolicy) -> list:
        """The observations eligible at the policy's cutoff, for the security's listing and its issuer (company-level filings)."""
        return [o for o in self.all_for(security_id, metric) if eligibility(o.availability(), policy)[0]]


@dataclass(frozen=True, slots=True)
class ResolvedFigure:
    metric: str
    period: Period
    basis: str
    unit: str
    scale: int | None
    currency: str | None
    context: str
    status: str                      # ok | conflicted
    value: Decimal | None
    observation_ids: tuple           # the selected tier: agreeing observations, or every conflicting one
    other_ids: tuple                 # eligible observations outside the selected tier (earlier/later disclosures)
    view: str
    reasons: tuple
    warnings: tuple = ()


def _disagreements(group) -> tuple:
    """Warnings when disclosures of one figure (any time) disagree in sign or by a factor of 100 or more: a likely sign or scale error in some filing."""
    values = [o.value for o in group if o.value]
    out = []
    if any(v > 0 for v in values) and any(v < 0 for v in values):
        out.append("disclosures of this figure disagree in sign: " + ", ".join(f"{o.value} ({o.form or o.provider} {o.filed or o.published_at or ''})".strip() for o in group))
    magnitudes = [abs(v) for v in values]
    if magnitudes and min(magnitudes) and max(magnitudes) / min(magnitudes) >= 100:
        out.append("disclosures of this figure differ by a factor of 100 or more (a scale error in one filing?): "
                   + ", ".join(f"{o.value} ({o.form or o.provider} {o.filed or ''})".strip() for o in group))
    return tuple(out)


def resolve(observations: list, policy: AsOfPolicy, view: str = "as_reported") -> list:
    """Select one figure per comparable group from ALREADY ELIGIBLE observations. as_reported: the earliest-available disclosure; latest: the most recent one.
    Equal values in the selected tier corroborate; different values are a conflict, shown with every value, never averaged or ordered away."""
    if view not in ("as_reported", "latest"):
        raise ValueError("view must be as_reported or latest")
    groups = {}
    for o in observations:
        if o.metric:
            groups.setdefault(o.comparable_key(), []).append(o)
    out = []
    for key, group in groups.items():
        def moment(o):
            start = available_from(o.published_at, o.publication_date, policy)
            return (start.isoformat() if start else "", o.observed_at)
        ordered = sorted(group, key=moment)
        edge = moment(ordered[0] if view == "as_reported" else ordered[-1])[0]
        tier = [o for o in ordered if moment(o)[0] == edge]
        values = {o.value for o in tier}
        status = "ok" if len(values) == 1 else "conflicted"
        reasons = () if status == "ok" else (f"{len(values)} different values were disclosed at the same time: " + ", ".join(sorted(str(v) for v in values)),)
        first = tier[0]
        out.append(ResolvedFigure(first.metric, first.period, first.basis, first.unit, first.scale, first.currency, first.context, status,
                                  first.value if status == "ok" else None, tuple(o.id for o in tier), tuple(o.id for o in ordered if o not in tier), view, reasons,
                                  _disagreements(ordered)))
    return sorted(out, key=lambda r: (r.metric, r.period.end_date or r.period.instant_date or "", r.period.kind, r.basis))


def _printed_tolerance(observation) -> Decimal:
    """Half a unit of the last printed digit, in base units: '35082' in millions -> 500,000; '0.78' per share -> 0.005."""
    raw = observation.raw_value.replace(",", "")
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    return Decimal(5) * (observation.scale or 1) / (Decimal(10) ** (decimals + 1))


def reconcile(release: list, filings: list) -> list:
    """A release's figures against filing (companyfacts) figures for the same metric, quarter end date, unit and currency. Management-adjusted (non-GAAP)
    figures are not compared with GAAP tags; a release figure without a stated end date cannot be matched. Differences beyond the release's printed rounding
    are reported with both values; nothing is adjusted."""
    rows = []
    by_key = {}
    for f in filings:
        if f.provider == "sec_companyfacts" and f.period.end_date and f.period.kind == "quarter":
            by_key.setdefault((f.metric, f.period.end_date, f.unit, f.currency), []).append(f)
    for r in release:
        row = {"metric": r.metric, "basis": r.basis, "period": r.period.label, "release_value": r.value, "release_observation": r.id}
        if r.basis == "NON-GAAP":
            rows.append({**row, "status": "not_compared", "reason": "management-adjusted (non-GAAP) figure; filings tag GAAP amounts"})
            continue
        if not r.period.end_date or r.period.kind != "quarter":
            rows.append({**row, "status": "not_compared", "reason": "the release figure has no stated quarter end date to match"})
            continue
        matches = by_key.get((r.metric, r.period.end_date, r.unit, r.currency), [])
        if not matches:
            rows.append({**row, "status": "no_filing_figure", "reason": "no filing figure for this metric, quarter end, unit and currency"})
            continue
        tolerance = _printed_tolerance(r)
        values = sorted({m.value for m in matches})
        agrees = all(abs(v - r.value) <= tolerance for v in values)
        rows.append({**row, "status": "agrees" if agrees else "differs", "filing_values": [str(v) for v in values], "tolerance": str(tolerance),
                     "filing_observations": [m.id for m in matches], "accessions": sorted({m.accession for m in matches if m.accession}),
                     "reason": None if agrees else "the filing value differs from the release beyond its printed rounding",
                     "basis_note": "release basis not stated; the filing value is GAAP" if r.basis == "UNSTATED" else None})
    return rows
