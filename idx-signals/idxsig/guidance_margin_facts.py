"""Offline source-bound guidance facts. No model, market data, orders or scheduler.

FACTS_READY is conditional on trusted external review attestations. A text hash
and matching numeric token do not prove authenticity or semantic entailment.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
from pathlib import Path

from .guidance_revision import moment

SCHEMA = "guidance-margin-facts/v1"
STATUSES = ("INCOMPARABLE", "MISSING", "UNVERIFIED")


class _Review:
    def __init__(self):
        self.issues = {s: [] for s in STATUSES}

    def add(self, status, reason):
        if reason not in self.issues[status]:
            self.issues[status].append(reason)

    def required(self, obj, key, where):
        value = obj.get(key)
        if value is None or value == "":
            self.add("MISSING", f"{where}.{key} is missing")
            return None
        return value

    def text(self, obj, key, where):
        value = self.required(obj, key, where)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{where}.{key} must be nonempty text")
        return value

    def clock(self, obj, key, where):
        if key not in obj:
            self.add("MISSING", f"{where}.{key} is missing")
            return None
        if obj[key] is None:
            self.add("UNVERIFIED", f"{where}.{key} is unknown")
            return None
        if not isinstance(obj[key], str):
            raise ValueError(f"{where}.{key} must be a timestamp")
        try:
            return moment(obj[key])
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"{where}.{key}: invalid timestamp") from exc


def _object(value, where, review):
    if value is None:
        review.add("MISSING", f"{where} is missing")
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    return value


def _decimal(value, where):
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{where} must be a finite number, not bool")
    return Decimal(str(value))


_SCALE = re.compile(r"(?i)(billions?|bn|b|millions?|mm|mn|m)\b")
_SCALE_END = re.compile(r"(?i)(?<=\d)\s*(billions?|bn|b|millions?|mm|mn|m)$")


def _token_value(token):
    token = token.strip().replace(",", "")
    if token.endswith("%"):
        token = token[:-1].strip()
    if token.startswith("$"):
        token = token[1:].strip()
    negative = token.startswith("(") and token.endswith(")")
    if negative:
        token = token[1:-1].strip()
        if token.startswith("$"):
            token = token[1:].strip()
    token = _SCALE_END.sub("", token).strip()
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError("source span is not a numeric token") from exc
    if not value.is_finite() or (negative and value < 0):
        raise ValueError("source span has invalid numerical meaning")
    return -value if negative else value


def _number(obj, raw, where, review):
    obj = _object(obj, where, review)
    value = review.required(obj, "value", where)
    number = _decimal(value, where) if value is not None else None
    start = review.required(obj, "start", where)
    end = review.required(obj, "end", where)
    if start is None or end is None:
        return None
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        raise ValueError(f"{where}: invalid character span")
    if raw is not None:
        if end > len(raw):
            raise ValueError(f"{where}: character span outside source")
        if number is not None and _token_value(raw[start:end]) != number:
            raise ValueError(f"{where}: source token differs from supplied value")
    return number


def _explicit_scale(raw, span):
    """Find an attached or adjacent scale without using a different table cell."""
    if not isinstance(span, dict) or raw is None:
        return None
    start, end = span.get("start"), span.get("end")
    if type(start) is not int or type(end) is not int:
        return None
    token = raw[start:end].strip().rstrip(")")
    match = _SCALE_END.search(token) or _SCALE.match(raw[end:].lstrip(" \t\xa0"))
    if match:
        return "USD_BILLIONS" if match[1].lower().startswith("b") else "USD_MILLIONS"
    return None


def _metric(obj, raw, expected_unit, where, review):
    value = _metric_value(obj, raw, expected_unit, where, review)
    if value is None or not isinstance(obj, dict):
        return value
    slots = {"point": ("point",), "range": ("low", "high"), "center_spread": ("center", "spread")}
    spans = [obj.get(key) for key in slots.get(obj.get("form"), ())]
    scales = [_explicit_scale(raw, span) for span in spans]
    unit = obj.get("unit")
    if any(scale and scale != unit for scale in scales):
        review.add("INCOMPARABLE", f"{where}: source scale conflicts with supplied unit")
    if unit == "USD_BILLIONS":
        # In "$5 to $6 billion" the last scale applies to the whole range.
        if None in scales:
            shared = False
            if len(spans) == 2 and scales == [None, unit] and raw is not None:
                between = raw[spans[0]["end"]:spans[1]["start"]].strip()
                shared = between.lower() in ("to", "-", "–", "—", "±", "+/-")
            if not shared:
                review.add("UNVERIFIED", f"{where}: billion scale lacks direct source evidence")
        return value * 1000
    return value


def _metric_value(obj, raw, expected_unit, where, review):
    obj = _object(obj, where, review)
    form = review.required(obj, "form", where)
    unit = review.required(obj, "unit", where)
    qualifier = review.required(obj, "qualifier", where)
    if unit is not None and unit != expected_unit and not (
        unit == "USD_BILLIONS" and expected_unit == "USD_MILLIONS"
    ):
        review.add("INCOMPARABLE", f"{where}: unsupported unit {unit!r}")
    if qualifier == "ambiguous":
        review.add("INCOMPARABLE", f"{where}: ambiguous bounds")
    elif qualifier is not None and qualifier not in ("exact", "approximate"):
        raise ValueError(f"{where}: unknown qualifier")
    if form is None:
        return None
    if form == "point":
        return _number(obj.get("point"), raw, where + ".point", review)
    if form == "range":
        low = _number(obj.get("low"), raw, where + ".low", review)
        high = _number(obj.get("high"), raw, where + ".high", review)
        if low is None or high is None:
            return None
        if low > high:
            raise ValueError(f"{where}: reversed range")
        return (low + high) / 2
    if form == "center_spread":
        center = _number(obj.get("center"), raw, where + ".center", review)
        spread = _number(obj.get("spread"), raw, where + ".spread", review)
        if spread is not None and spread < 0:
            raise ValueError(f"{where}: negative spread")
        return center if spread is not None else None
    raise ValueError(f"{where}: unknown metric form")


def _document(value, where, review):
    doc = _object(value, where, review)
    identity = review.text(doc, "issuer_cik", where)
    if identity is not None and (
        not identity.isascii() or not identity.isdigit() or int(identity) <= 0
    ):
        raise ValueError(f"{where}: invalid issuer CIK")
    periods = []
    for key in ("period_start", "period_end"):
        item = review.text(doc, key, where)
        try:
            periods.append(date.fromisoformat(item) if item is not None else None)
        except ValueError as exc:
            raise ValueError(f"{where}.{key}: invalid date") from exc
    if all(p is not None for p in periods) and periods[0] >= periods[1]:
        raise ValueError(f"{where}: reversed fiscal period")
    kind = review.required(doc, "period_kind", where)
    if kind is not None and kind != "FULL_YEAR":
        review.add("INCOMPARABLE", f"{where}: not full-year guidance")
    basis = review.required(doc, "basis", where)
    if basis is not None and basis not in ("GAAP", "ADJUSTED"):
        raise ValueError(f"{where}: unknown accounting basis")
    definition = review.text(doc, "definition_id", where)
    perimeter = review.text(doc, "perimeter_id", where)
    source = _object(doc.get("source"), where + ".source", review)
    source_id = review.text(source, "id", where + ".source")
    for key in ("url", "locator"):
        review.text(source, key, where + ".source")
    raw = review.text(source, "raw_text", where + ".source")
    sha = review.text(source, "sha256", where + ".source")
    representation = review.required(source, "representation", where + ".source")
    if representation is not None and representation != "retained_excerpt":
        raise ValueError(f"{where}: unknown source representation")
    if sha is not None:
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError(f"{where}: invalid source SHA-256")
        if raw is not None and hashlib.sha256(raw.encode("utf-8")).hexdigest() != sha:
            raise ValueError(f"{where}: source SHA-256 mismatch")
    published = review.clock(source, "published_at", where + ".source")
    received = review.clock(source, "received_at", where + ".source")
    if published is not None and received is not None and published > received:
        raise ValueError(f"{where}: publication after receipt")
    revenue = _metric(doc.get("revenue"), raw, "USD_MILLIONS", where + ".revenue", review)
    profit = margin = None
    if "operating_profit" in doc and "operating_margin" in doc:
        raise ValueError(f"{where}: supply profit or margin, not both")
    if "operating_profit" in doc:
        profit = _metric(
            doc["operating_profit"], raw, "USD_MILLIONS", where + ".operating_profit", review
        )
    elif "operating_margin" in doc:
        margin = _metric(
            doc["operating_margin"], raw, "PERCENT", where + ".operating_margin", review
        )
    else:
        review.add("MISSING", f"{where}: operating profit or margin missing")
    for key in ("eps", "ebitda", "net_income", "gross_profit", "fcf", "segment_noi"):
        if key in doc and "operating_profit" not in doc and "operating_margin" not in doc:
            review.add("INCOMPARABLE", f"{where}: {key} is not operating profit")
    if revenue is not None and revenue <= 0:
        review.add("INCOMPARABLE", f"{where}: revenue midpoint is not positive")
    if margin is None and profit is not None and revenue is not None and revenue > 0:
        margin = 100 * profit / revenue
    return {
        "identity": int(identity) if identity is not None else None,
        "periods": tuple(periods),
        "basis": basis,
        "definition": definition,
        "perimeter": perimeter,
        "source_id": source_id,
        "published": published,
        "received": received,
        "revenue": revenue,
        "margin": margin,
    }


def qualify(pair):
    """Qualify offline facts conditional on external attestations; never a trade signal."""
    if not isinstance(pair, dict):
        raise ValueError("pair must be an object")
    try:
        json.dumps(pair, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ValueError("fact packet must contain finite JSON values") from exc
    review = _Review()
    schema = review.required(pair, "schema_version", "pair")
    if schema is not None and schema != SCHEMA:
        raise ValueError("unknown fact schema")
    purpose = review.required(pair, "purpose", "pair")
    if purpose is not None and purpose != "development":
        raise ValueError("this contract is development-only")
    review.text(pair, "event_id", "pair")
    current = _document(pair.get("current"), "current", review)
    prior = _document(pair.get("prior"), "prior", review)
    for key in ("identity", "basis", "definition", "perimeter"):
        if current[key] is not None and prior[key] is not None and current[key] != prior[key]:
            review.add("INCOMPARABLE", f"current/prior {key} differ")
    for i, key in enumerate(("period_start", "period_end")):
        a, b = current["periods"][i], prior["periods"][i]
        if a is not None and b is not None and a != b:
            review.add("INCOMPARABLE", f"current/prior {key} differ")
    external = _object(pair.get("external"), "external", review)
    for key in ("attestor", "evidence_notes"):
        review.text(external, key, "external")
    for key in (
        "source_authenticity",
        "metric_binding",
        "prior_completeness",
        "basis_comparable",
        "perimeter_comparable",
    ):
        value = review.required(external, key, "external")
        if value is not None and value not in ("VERIFIED", "UNKNOWN", "FAILED"):
            raise ValueError(f"external.{key}: unknown attestation status")
        if value in ("UNKNOWN", "FAILED"):
            status = (
                "INCOMPARABLE"
                if value == "FAILED" and key in ("basis_comparable", "perimeter_comparable")
                else "UNVERIFIED"
            )
            review.add(status, f"external.{key}: {value}")
    latest = review.text(external, "latest_prior_source_id", "external")
    if latest is not None and prior["source_id"] is not None and latest != prior["source_id"]:
        review.add("INCOMPARABLE", "supplied prior is not the externally identified latest prior")
    clocks = _object(pair.get("clocks"), "clocks", review)
    extracted = review.clock(clocks, "extracted_at", "clocks")
    decision = review.clock(clocks, "decision_at", "clocks")
    if (
        prior["published"] is not None
        and current["published"] is not None
        and prior["published"] >= current["published"]
    ):
        raise ValueError("prior publication must precede current publication")
    for name, doc in (("current", current), ("prior", prior)):
        if doc["received"] is not None and extracted is not None and doc["received"] > extracted:
            raise ValueError(f"{name}: source received after extraction")
    if extracted is not None and decision is not None and extracted > decision:
        raise ValueError("extraction completed after decision")
    reasons = [item for status in STATUSES for item in review.issues[status]]
    status = next((s for s in STATUSES if review.issues[s]), "FACTS_READY")
    derived = None
    if status == "FACTS_READY":
        if any(doc[k] is None for doc in (current, prior) for k in ("revenue", "margin")):
            raise ValueError("internal qualification inconsistency")
        derived = {
            "current_revenue_midpoint": float(current["revenue"]),
            "prior_revenue_midpoint": float(prior["revenue"]),
            "current_margin_midpoint_pct": float(current["margin"]),
            "prior_margin_midpoint_pct": float(prior["margin"]),
            "revenue_revision_pct": float(100 * (current["revenue"] / prior["revenue"] - 1)),
            "margin_revision_pp": float(current["margin"] - prior["margin"]),
        }
        if not all(math.isfinite(x) for x in derived.values()):
            raise ValueError("derived values exceed finite numeric range")
    return {"status": status, "reasons": reasons, "derived": derived}


def record_revision(record, path):
    """Append a validated observation using the existing paper-chain hash recipe.

    The existing atomic publication and exclusive lock cover validation AND write.
    Calling paper.append while holding its same lock would deadlock, so the small
    existing hash recipe is reused directly; no legacy module is changed.
    """
    from .paper import _canonical, _chain_problems
    from .provenance import exclusive_lock, publish_bytes

    path = Path(path)
    if path.is_symlink():
        raise ValueError("fact ledger cannot use a symbolic link")
    path = path.resolve()
    with exclusive_lock(path):
        if not isinstance(record, dict):
            raise ValueError("record must be an object")
        if any(k in record for k in ("qualification", "prev_hash", "record_hash")):
            raise ValueError("caller cannot supply derived or hash-chain fields")
        for key in ("id", "event_id", "recorded_at"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f"record.{key} is required")
        if "revision_of" not in record or (
            record["revision_of"] is not None and not isinstance(record["revision_of"], str)
        ):
            raise ValueError("record.revision_of is required")
        try:
            at = moment(record["recorded_at"])
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError("invalid record timestamp") from exc
        pair = record.get("fact_pair")
        if not isinstance(pair, dict) or pair.get("event_id") != record["event_id"]:
            raise ValueError("record and fact event IDs differ")
        result = qualify(pair)
        decision = (pair.get("clocks") or {}).get("decision_at")
        if decision is not None and at < moment(decision):
            raise ValueError("record time precedes fact decision")
        before = path.read_bytes() if path.exists() else b""
        try:
            rows = [
                json.loads(line) for line in before.decode("utf-8").splitlines() if line.strip()
            ]
            if _chain_problems(rows) or (before and not before.endswith(b"\n")):
                raise ValueError("fact ledger hash chain is corrupt")
        except (ValueError, TypeError, AttributeError, UnicodeError) as exc:
            raise ValueError("fact ledger is unreadable or corrupt") from exc
        if any(r.get("id") == record["id"] for r in rows):
            raise ValueError("record ID already exists")
        matching = [r for r in rows if r.get("event_id") == record["event_id"]]
        head = matching[-1] if matching else None
        if record["revision_of"] != (head["id"] if head else None):
            raise ValueError("revision must target the current head of this event")
        if head is not None and at <= moment(head["recorded_at"]):
            raise ValueError("correction-known time must advance")
        body = {
            **record,
            "qualification": result,
            "prev_hash": rows[-1]["record_hash"] if rows else None,
        }
        body["record_hash"] = hashlib.sha256(_canonical(body).encode()).hexdigest()
        serialized = (_canonical(body) + "\n").encode("utf-8")
        publish_bytes(path, before + serialized, replace=True)
        if path.read_bytes() != before + serialized:
            raise ValueError("fact ledger read-back differs")
        return body


def main(argv=None):
    """Rehearse retained development fixtures into a NEW artifact directory."""
    import argparse
    from .provenance import publish_bytes

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("output directory already exists; preserve it and choose a new one")
    raw = args.fixtures.read_bytes()
    fixtures = json.loads(raw)["fixtures"]
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("at least one development fixture is required")
    ids = [f["id"] for f in fixtures]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate fixture IDs")
    # Qualify every input before creating artifacts, including integrity failures.
    results = [(f, qualify(f["pair"])) for f in fixtures]
    args.out.mkdir(parents=True)
    stamp = datetime.now(timezone.utc).isoformat()
    rows = []
    for fixture, result in results:
        record = record_revision(
            {
                "id": fixture["id"],
                "event_id": fixture["pair"]["event_id"],
                "revision_of": None,
                "recorded_at": stamp,
                "fact_pair": fixture["pair"],
            },
            args.out / "facts.jsonl",
        )
        rows.append(
            {
                "id": fixture["id"],
                "kind": fixture["kind"],
                "qualification": result,
                "record_hash": record["record_hash"],
            }
        )
    report = {
        "schema": "GUIDANCE_MARGIN_FACTS_DEVELOPMENT_V1",
        "as_of": stamp,
        "purpose": "offline development; no model or trading result",
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "provider_calls": 0,
        "orders": 0,
        "rows": rows,
    }
    publish_bytes(
        args.out / "REPORT.json", (json.dumps(report, indent=2, allow_nan=False) + "\n").encode()
    )
    print(
        json.dumps(
            {
                "out": str(args.out),
                "observations": len(rows),
                "statuses": [r["qualification"]["status"] for r in rows],
                "provider_calls": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
