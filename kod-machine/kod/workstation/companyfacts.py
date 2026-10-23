"""SEC companyfacts as immutable financial observations, with filing lineage and explicit coverage.

What companyfacts is: facts tagged with standard taxonomies (us-gaap, dei, ...) for the whole entity, as each filing reported them, with the filing's accession,
form and filed date. What it is not: segment data, custom company KPIs, or proof that the same API payload existed at an earlier date.

Rules kept here:
- Only reviewed concepts are mapped (CONCEPTS); everything else is left out and the coverage report says which catalog metrics are absent.
- Each value keeps its original tag, unit array, raw number, accession, form, filed date and the exact JSON pointer into the preserved response.
- A value is never chosen by fy/fp or by its position in an array. fy/fp describe the filing, not the fact; periods come from the fact's own start/end dates.
- A later filing's comparative value is a separate observation. Nothing is overwritten; the as-reported and latest-known views are selected at read time
  (financials.resolve) after the cutoff policy has been applied.
- Availability is the accession's filing date (date precision). The submissions feed's acceptanceDateTime is kept as raw metadata only; an exact acceptance time
  is used only when the filing's own header was preserved and matched (not done in bulk).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import re

from ..earnings import _decimal_string
from .domain import canonical, identity
from .financials import duration_kind, period
from .identity import METRIC_VERSION

PROVIDER = "sec_companyfacts"
MAPPING_VERSION = "KOD-COMPANYFACTS-MAP-v1"
PARSER_VERSION = "KOD-COMPANYFACTS-READER-v2"  # v2: JSON pointers escaped per RFC 6901 (unit keys such as USD/shares)

# (taxonomy, tag) -> canonical metric. Reviewed one by one; alternatives that mean something different are deliberately absent (for example LongTermDebt,
# which includes the current portion, is not mapped to long_term_debt, which is the noncurrent amount).
CONCEPTS = {
    ("us-gaap", "Revenues"): "revenue",
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"): "revenue",
    ("us-gaap", "SalesRevenueNet"): "revenue",
    ("us-gaap", "OperatingExpenses"): "operating_expenses",
    ("us-gaap", "OperatingIncomeLoss"): "operating_income",
    ("us-gaap", "NetIncomeLoss"): "net_income",
    ("us-gaap", "EarningsPerShareDiluted"): "eps_diluted",
    ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"): "diluted_shares",
    ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"): "operating_cash_flow",
    ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"): "capex",
    ("us-gaap", "DepreciationDepletionAndAmortization"): "depreciation_amortization",
    ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"): "cash_and_equivalents",
    ("us-gaap", "Assets"): "total_assets",
    ("us-gaap", "Liabilities"): "total_liabilities",
    ("us-gaap", "StockholdersEquity"): "stockholders_equity",
    ("us-gaap", "LongTermDebtNoncurrent"): "long_term_debt",
    ("dei", "EntityCommonStockSharesOutstanding"): "shares_outstanding",
}
# When one filing period carries several concepts mapped to one metric, they are different line items (Costco reported net sales as SalesRevenueNet and
# total revenue including membership fees as Revenues). Only the first concept present for that period, in this order, is used; the others are not
# compared with it as if they were revisions.
CONCEPT_PRECEDENCE = {"revenue": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet")}
CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")

# Business types the first operating-company model does not support (SEC SIC codes): banks and credit institutions, insurance, real-estate investment trusts.
FINANCIAL_SIC = ((6000, 6199, "bank or credit institution"), (6300, 6411, "insurance"), (6798, 6798, "real estate investment trust"))


def json_pointer(*tokens) -> str:
    """An RFC 6901 JSON pointer: '~' is written '~0' and '/' is written '~1' inside each token (a unit key such as 'USD/shares' contains a slash)."""
    return "".join("/" + str(t).replace("~", "~0").replace("/", "~1") for t in tokens)


def resolve_pointer(document, pointer: str):
    """The value an RFC 6901 pointer designates in a parsed JSON document; KeyError/IndexError when it designates nothing."""
    node = document
    if pointer == "":
        return node
    if not pointer.startswith("/"):
        raise KeyError(pointer)
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            if not token.isdigit():
                raise KeyError(token)
            node = node[int(token)]
        else:
            node = node[token]
    return node


class CompanyFactsError(ValueError):
    """The response is not a companyfacts document KOD can read."""


def parse(raw: bytes) -> dict:
    """Decimal-exact JSON: numbers are read from their text, never through binary floats."""
    def refuse(name):
        raise CompanyFactsError(f"companyfacts response contains the non-JSON number {name}")
    try:
        data = json.loads(raw, parse_float=Decimal, parse_int=Decimal, parse_constant=refuse)
    except (ValueError, UnicodeDecodeError, ArithmeticError) as exc:
        raise CompanyFactsError("companyfacts response is not valid JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("facts"), dict) or "cik" not in data:
        raise CompanyFactsError("companyfacts response has no 'cik' and 'facts'")
    return data


def business_type(submissions: dict | None) -> dict:
    """{'supported': bool, 'sic', 'description', 'reason'} from the submissions feed's SIC code; unknown when no submissions were preserved."""
    if not submissions or not str(submissions.get("sic") or "").isdigit():
        return {"supported": None, "sic": None, "description": None, "reason": "SIC code unknown; business type not established"}
    sic = int(submissions["sic"])
    for low, high, kind in FINANCIAL_SIC:
        if low <= sic <= high:
            return {"supported": False, "sic": sic, "description": submissions.get("sicDescription"), "reason": f"SIC {sic} is a {kind}; the operating-company model does not apply"}
    return {"supported": True, "sic": sic, "description": submissions.get("sicDescription"), "reason": None}


def _unit(unit: str):
    """(unit, currency, scale) for a companyfacts units key, or None when KOD does not interpret it."""
    if unit == "shares":
        return "shares", None, 1
    if "/" in unit:
        num, den = unit.split("/", 1)
        return ("currency/share", num, 1) if CURRENCY_CODE.match(num) and den == "shares" else None
    return ("currency", unit, 1) if CURRENCY_CODE.match(unit) else None


def acceptance_times(submissions: dict | None) -> dict:
    recent = ((submissions or {}).get("filings") or {}).get("recent") or {}
    return dict(zip(recent.get("accessionNumber", []), recent.get("acceptanceDateTime", [])))


def observation_rows(data: dict, document: dict, security_id: str, issuer_id: str | None, now: str, submissions: dict | None = None) -> tuple[list, list, dict]:
    """(periods, observation rows, coverage) from a parsed companyfacts response preserved as `document` (pure). Exact repeats of one fact inside the response
    (the same value, period, accession and form listed under several frames) become one observation with every pointer kept."""
    accepted = acceptance_times(submissions)
    periods, rows, seen = {}, {}, {}
    coverage = {"provider": PROVIDER, "scope": "whole-entity standard-taxonomy facts as filed; no segments or custom KPIs", "metrics": {}, "unmapped_units": [],
                "absent_metrics": [], "concepts_present": []}
    for (taxonomy, tag), metric in sorted(CONCEPTS.items()):
        concept = (data["facts"].get(taxonomy) or {}).get(tag)
        if not concept:
            continue
        coverage["concepts_present"].append(f"{taxonomy}:{tag}")
        for unit_key, entries in sorted((concept.get("units") or {}).items()):
            interpreted = _unit(unit_key)
            if interpreted is None:
                coverage["unmapped_units"].append(f"{taxonomy}:{tag} [{unit_key}]")
                continue
            unit, currency, scale = interpreted
            for index, e in enumerate(entries):
                pointer = json_pointer("facts", taxonomy, tag, "units", unit_key, index)
                try:
                    end, start, val, accn, form, filed = e["end"], e.get("start"), e["val"], e["accn"], e["form"], e["filed"]
                    if not isinstance(val, Decimal) or not val.is_finite() or abs(val) >= Decimal(10) ** 18:
                        raise TypeError("value is not a finite number of a plausible magnitude")
                    if not all(isinstance(x, str) for x in (end, accn, form, filed)) or (start is not None and not isinstance(start, str)):
                        raise TypeError("dates and filing fields must be text")
                    duration_kind(start, end) if start else date.fromisoformat(end)
                    date.fromisoformat(filed)
                except (KeyError, TypeError, ValueError):
                    coverage.setdefault("malformed_entries", []).append(pointer)
                    continue
                if start:
                    p = period(duration_kind(start, end), start=start, end=end)
                else:
                    p = period("instant", instant=end)
                periods[p.id] = p
                value = Decimal(val)
                key = (taxonomy, tag, unit_key, start, end, value, accn, form, filed)
                if key in seen:
                    rows[seen[key]]["_also_at"].append(pointer)
                    continue
                flags = []
                if metric == "capex" and value < 0:
                    flags.append("CAPEX_NEGATIVE_AS_REPORTED")
                oid = identity("fob", PROVIDER, document["id"], pointer, tag, metric, METRIC_VERSION, _decimal_string(value), unit, currency, p.id, accn, MAPPING_VERSION)
                seen[key] = oid
                rows[oid] = {
                    "id": oid, "provider": PROVIDER, "issuer_id": issuer_id, "security_id": security_id, "concept": tag, "taxonomy": taxonomy, "metric": metric,
                    "metric_version": METRIC_VERSION, "raw_value": str(val), "value": _decimal_string(value), "unit": unit, "scale": scale, "currency": currency,
                    "currency_basis": "UNIT_OF_MEASURE" if currency else None, "period_id": p.id, "basis": "GAAP" if taxonomy == "us-gaap" else "UNSTATED",
                    "context": "consolidated (companyfacts whole entity)", "dimensions_available": 0, "accession": accn, "form": form, "filed": filed,
                    "amendment": 1 if form.endswith("/A") else 0, "source_document_id": document["id"], "source_sha256": document["sha256"],
                    "_pointer": pointer, "_also_at": [], "_frame": e.get("frame"), "_fy": e.get("fy"), "_fp": e.get("fp"), "_accepted_raw": accepted.get(accn),
                    "published_at": None, "publication_date": filed, "publication_precision": "date",
                    "publication_basis": f"SEC filing date of accession {accn} (companyfacts 'filed'); exact acceptance time not established",
                    "observed_at": document["observed_at"], "recorded_at": now, "parser_version": PARSER_VERSION, "mapping_version": MAPPING_VERSION,
                    "flags": canonical(sorted(flags))}
                m = coverage["metrics"].setdefault(metric, {"observations": 0, "kinds": {}, "first_end": None, "last_end": None, "concepts": set(), "forms": set()})
                m["observations"] += 1
                m["kinds"][p.kind if p.kind in ("quarter", "6 months", "9 months", "12 months", "instant") else "other"] = \
                    m["kinds"].get(p.kind if p.kind in ("quarter", "6 months", "9 months", "12 months", "instant") else "other", 0) + 1
                m["first_end"] = min(filter(None, (m["first_end"], end)))
                m["last_end"] = max(filter(None, (m["last_end"], end)))
                m["concepts"].add(tag)
                m["forms"].add(form)
    out = []
    for row in rows.values():
        evidence = {"json_pointer": row.pop("_pointer"), "also_at": row.pop("_also_at"), "frame": row.pop("_frame"), "filing_fy": row.pop("_fy"),
                    "filing_fp": row.pop("_fp"), "submissions_acceptance_raw": row.pop("_accepted_raw"), "document_id": document["id"],
                    "note": "fy/fp describe the filing, not this fact; the period is the fact's own start/end"}
        row["evidence"] = canonical(evidence)
        out.append(row)
    from .identity import METRIC_CATALOG_V1
    coverage["absent_metrics"] = sorted(m for m, *_ in METRIC_CATALOG_V1 if m not in coverage["metrics"] and m not in ("gross_margin",))
    for m in coverage["metrics"].values():
        m["concepts"], m["forms"] = sorted(m["concepts"]), sorted(m["forms"])
    coverage["observations"] = len(out)
    return list(periods.values()), out, coverage


def filing_chronology(observations, submissions: dict | None = None) -> list:
    """The filings the observations come from, in filing-date order: accession, form, filed date, amendment, how many observations, and the submissions feed's raw
    acceptanceDateTime (shown as metadata; not used as the availability time)."""
    accepted = acceptance_times(submissions)
    filings = {}
    for o in observations:
        if not o.accession:
            continue
        f = filings.setdefault(o.accession, {"accession": o.accession, "form": o.form, "filed": o.filed, "amendment": bool(o.amendment), "observations": 0,
                                             "submissions_acceptance_raw": accepted.get(o.accession)})
        f["observations"] += 1
    return sorted(filings.values(), key=lambda f: (f["filed"] or "", f["accession"]))
