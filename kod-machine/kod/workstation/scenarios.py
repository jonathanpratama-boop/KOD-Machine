"""Scenarios: versioned assumption sets, their model results as recorded calculations, dated prices, and the market context a price gives a scenario.

- An assumption set (company, model, bear/base/bull, name) has immutable versions; saving changes creates version n+1 that supersedes n. Every version is
  validated in full before it is stored (model.validate), with author, time and rationale.
- Running a version records a calculation (formula KOD-FCFF-v1) whose inputs are the assumption version and any observations it cites. A newer version
  makes earlier results stale (calculations.stale_reasons); the old results stay as they were for anything saved from them.
- Prices are immutable dated observations with their conventions; the price used at a cutoff is chosen only among prices eligible at that cutoff.
- Market context (price x selected share count) is computed only from a raw (unadjusted) price, in the scenario's currency; adjusted prices are never
  multiplied by unadjusted share counts.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json

from . import calculations, companyfacts, model, prices
from .domain import canonical, identity, timestamp
from .policy import AsOfPolicy, DAY_END, eligibility

SCENARIOS = ("bear", "base", "bull")
# The revision order of price observations: a per-table sequence assigned in the recording transaction (SQLite serialises writers), so two
# corrections recorded within the same second are still ordered by which was recorded later, never by their hash ids.
NEXT_SEQ = "(SELECT COALESCE(MAX(seq),0)+1 FROM price_observations)"


def _now(service):
    return timestamp(service.clock())


def save_assumptions(service, security_id: str, scenario: str, raw: dict, rationale: str, name: str = "default", author: str = "local_user") -> dict:
    """Validate and store a new version of an assumption set. Returns the stored version (with its id, version number and validated assumptions)."""
    service.store.get_security(security_id)
    if scenario not in SCENARIOS:
        raise ValueError("scenario must be bear, base or bull (labels only; no probabilities are attached)")
    name = str(name or "default").strip()
    rationale = str(rationale or "").strip()
    if not name or len(name) > 80:
        raise ValueError("the assumption set needs a name of at most 80 characters")
    if not rationale or len(rationale) > 4000:
        raise ValueError("record why these assumptions are reasonable (a rationale of 1 to 4,000 characters)")
    model.validate(raw)                                   # raises AssumptionError listing every problem; nothing invalid is stored
    stored = canonical(raw)
    now = _now(service)
    with service.store._connection() as db:
        set_id = identity("aset", security_id, model.MODEL, scenario, name)
        db.execute("INSERT OR IGNORE INTO assumption_sets VALUES (?,?,?,?,?,?,?)", (set_id, security_id, model.MODEL, scenario, name, now, author))
        last = db.execute("SELECT id, version, assumptions FROM assumption_versions WHERE assumption_id=? ORDER BY version DESC LIMIT 1", (set_id,)).fetchone()
        if last is not None and last["assumptions"] == stored:
            raise ValueError("these assumptions are identical to the current version; nothing was saved")
        version = (last["version"] + 1) if last else 1
        vid = identity("asmv", set_id, version, stored)
        db.execute("INSERT INTO assumption_versions VALUES (?,?,?,?,?,?,?,?)", (vid, set_id, version, stored, rationale, author, now, last["id"] if last else None))
    return assumption_version(service, vid)


def assumption_version(service, version_id: str) -> dict:
    with service.store._connection() as db:
        row = db.execute("""SELECT v.*, s.security_id, s.model, s.scenario, s.name FROM assumption_versions v JOIN assumption_sets s ON s.id=v.assumption_id
                            WHERE v.id=?""", (version_id,)).fetchone()
        if row is None:
            raise ValueError("assumption version not found")
        latest = db.execute("SELECT MAX(version) FROM assumption_versions WHERE assumption_id=?", (row["assumption_id"],)).fetchone()[0]
    out = dict(row)
    out["assumptions"] = json.loads(out["assumptions"])
    out["latest_version"] = latest
    out["is_latest"] = latest == row["version"]
    return out


def assumption_sets(service, security_id: str) -> list:
    """Each set with its latest version and how many versions exist."""
    with service.store._connection() as db:
        rows = db.execute("""SELECT s.*, v.id AS latest_id, v.version AS latest_version, v.created_at AS latest_at, v.rationale AS latest_rationale
                             FROM assumption_sets s JOIN assumption_versions v ON v.assumption_id=s.id
                             WHERE s.security_id=? AND v.version=(SELECT MAX(version) FROM assumption_versions WHERE assumption_id=s.id)
                             ORDER BY CASE s.scenario WHEN 'bear' THEN 0 WHEN 'base' THEN 1 ELSE 2 END, s.name""", (security_id,)).fetchall()
    return [dict(r) for r in rows]


def history(service, set_id: str) -> list:
    with service.store._connection() as db:
        rows = db.execute("SELECT id, version, rationale, author, created_at, supersedes, assumptions FROM assumption_versions WHERE assumption_id=? ORDER BY version DESC",
                          (set_id,)).fetchall()
    return [{**dict(r), "assumptions": json.loads(r["assumptions"])} for r in rows]


def changed_fields(old: dict, new: dict) -> list:
    """Which assumptions differ between two versions (for the review trace): [(name, old, new)]."""
    names = sorted(set(old) | set(new))
    out = []
    for n in names:
        if old.get(n) != new.get(n):
            if isinstance(old.get(n), dict) and isinstance(new.get(n), dict):
                out += [(f"{n}.{k}", a, b) for k, a, b in changed_fields(old[n], new[n])]
            else:
                out.append((n, old.get(n), new.get(n)))
    return out


def business_type(service, security_id: str, policy: AsOfPolicy) -> dict:
    """The business classification (SIC) as the policy allows it to be known: the dossier's selector (ResearchService.submissions_at), so a
    snapshot imported later never changes the explanation of an earlier valuation."""
    return companyfacts.business_type(service.submissions_at(security_id, policy)[0])


@dataclass(frozen=True)
class ScenarioResult:
    version: dict
    valuation: model.Valuation
    calculation_id: str
    calculation: calculations.CalculationResult


def _cited_observations(raw: dict) -> list:
    ids = []
    for cite in (raw.get("sources") or {}).values():
        if isinstance(cite, dict):
            ids += [i for i in cite.get("observation_ids", []) if isinstance(i, str)]
    return sorted(set(ids))


def run_version(service, version_id: str, record: bool = True, *, policy: AsOfPolicy | None = None, context: dict | None = None, legacy: bool = False) -> ScenarioResult:
    """Run the model for one assumption version and (by default) record the result as a calculation whose inputs are that version and the observations it
    cites. Direct calls default to the assumption time; dossier/review callers pass their selected policy explicitly."""
    version = assumption_version(service, version_id)
    policy = policy or AsOfPolicy.parse(version["created_at"], "observed", DAY_END)
    context = context or service.submissions_context(version["security_id"], policy, legacy=legacy)
    if context["source"]["policy"] != policy.as_dict():
        raise ValueError("classification context does not match calculation policy")
    a = model.validate(version["assumptions"])
    business = companyfacts.business_type(context["data"])
    valuation = model.run(a, business)
    status = {"ok": "ok", "ev_only": "ok", "invalid": "invalid", "not_applicable": "not_applicable"}[valuation.status]
    value = valuation.per_share if valuation.status == "ok" else valuation.enterprise_value
    inputs = (("assumptions", "assumption", version_id),) + tuple(("cited", "observation", oid) for oid in _cited_observations(version["assumptions"]))
    result = calculations.CalculationResult(model.MODEL, model.MODEL, status, value if status == "ok" else None,
                                            "currency/share" if valuation.status == "ok" else "currency", inputs, (),
                                            tuple(valuation.warnings) + tuple(valuation.limitations),
                                            {"measure": "per_share" if valuation.status == "ok" else "enterprise_value", "valuation": valuation.as_dict(),
                                             "currency": a.currency, "scenario": version["scenario"], "assumption_version": version["version"],
                                             **({} if legacy else {"context_version": "KOD-SCENARIO-CONTEXT-v2", "source_context": context["source"]})})
    cid = calculations.calculation_id(result, policy)
    if record:
        with service.store._connection() as db:
            cid = calculations.record(db, result, "security", version["security_id"], policy, version["created_at"] if legacy else _now(service))
            if version["supersedes"]:
                for (old,) in db.execute("SELECT c.id FROM calculations c JOIN calculation_inputs i ON i.calculation_id=c.id WHERE i.input_kind='assumption' AND i.input_id=?",
                                         (version["supersedes"],)).fetchall():
                    calculations.supersede(db, old, cid, f"assumptions revised to version {version['version']}", version["created_at"])
    return ScenarioResult(version, valuation, cid, result)


def scenario_results(service, security_id: str) -> list:
    """The latest version of every set, run (and recorded idempotently)."""
    return [run_version(service, s["latest_id"]) for s in assumption_sets(service, security_id)]


# ---- prices ----

def record_prices(service, security_id: str, parsed: dict, source_kind: str, document_id: str | None = None) -> dict:
    now = _now(service)
    import_id = identity("pimp", security_id, source_kind, document_id, canonical(parsed["meta"]), [r["date"] for r in parsed["rows"]],
                         [str(r["close"]) for r in parsed["rows"]])
    rows = prices.rows_for_store(parsed, security_id, source_kind, now, now, import_id)
    cols = ("id", "security_id", "observed_on", "session", "timezone", "currency", "open", "high", "low", "close", "volume", "adjustment", "source",
            "source_kind", "feed_coverage", "published_at", "publication_basis", "observed_at", "recorded_at", "import_id")
    insert = f"INSERT OR IGNORE INTO price_observations({','.join(cols)},seq) VALUES ({','.join('?' * len(cols))},{NEXT_SEQ})"
    with service.store._connection() as db:
        db.execute("INSERT OR IGNORE INTO price_imports VALUES (?,?,?,?,?,?,?,?)", (import_id, security_id, document_id, source_kind, canonical(parsed["meta"]),
                                                                               canonical(parsed["coverage"]), len(rows), now))
        before = db.total_changes
        for r in rows:
            latest = db.execute("SELECT * FROM price_observations WHERE security_id=? AND observed_on=? AND session=? AND source=? AND adjustment=? "
                                "ORDER BY seq DESC LIMIT 1", (security_id, r["observed_on"], r["session"], r["source"], r["adjustment"])).fetchone()
            # Payload equality, not ID equality: retries of a re-recorded value are idempotent too.
            payload = tuple(c for c in cols if c not in ("id", "observed_at", "recorded_at", "import_id"))
            if latest is not None and all(latest[c] == r[c] for c in payload):
                continue
            seq = db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM price_observations").fetchone()[0]
            if db.execute("SELECT 1 FROM price_observations WHERE id=?", (r["id"],)).fetchone():
                r = {**r, "id": identity("price", r["id"], "revision-sequence-v1", seq)}
            db.execute(insert, tuple(r[c] for c in cols))
        added = db.total_changes - before
    return {"import_id": import_id, "rows": len(rows), "added": added, "coverage": parsed["coverage"], "meta": parsed["meta"]}


def import_price_csv(service, security_id: str, raw: bytes, filename: str, meta: dict) -> dict:
    """Validate the whole file first (prices.parse_csv); only then preserve its bytes and record the prices."""
    service.store.get_security(security_id)
    parsed = prices.parse_csv(raw, meta)
    doc = service.store.save_document(security_id, raw, filename, "https://example.invalid/local-price-file/" + hashlib.sha256(raw).hexdigest()[:16],
                                      published_at=None, published_basis="local price file supplied by the user; each row carries its own date",
                                      observed_at=_now(service), role="other", association="user_asserted", provider="local_price_csv",
                                      extraction_status="prices", metadata={"kind": "price CSV", **parsed["meta"], "coverage": parsed["coverage"]})
    return record_prices(service, security_id, parsed, "csv", doc["id"])


def add_manual_price(service, security_id: str, day: str, close, meta: dict, at: str | None = None) -> dict:
    service.store.get_security(security_id)
    return record_prices(service, security_id, prices.manual(meta, day, close, at), "manual")


def price_list(service, security_id: str, limit: int = 500) -> list:
    with service.store._connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM price_observations WHERE security_id=? ORDER BY observed_on DESC, seq DESC LIMIT ?", (security_id, limit))]


def price(service, price_id: str) -> dict:
    with service.store._connection() as db:
        row = db.execute("SELECT * FROM price_observations WHERE id=?", (price_id,)).fetchone()
    if row is None:
        raise ValueError("price observation not found")
    return dict(row)


def price_at(service, security_id: str, policy: AsOfPolicy, adjustment: str = "raw") -> dict | None:
    """The most recent price of the given convention that is eligible at the cutoff (published by it; in observed mode also recorded by it). For one
    trading day: within one series (session and source) the most recently recorded price is used, since a correction is a new import; across series
    (a close and an earlier intraday quote) the one published latest is used."""
    with service.store._connection() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM price_observations WHERE security_id=? AND adjustment=? ORDER BY observed_on DESC",
                                            (security_id, adjustment))]
    eligible = [r for r in rows if eligibility({"published_at": r["published_at"], "observed_at": r["observed_at"]}, policy)[0]]
    if not eligible:
        return None
    day = [r for r in eligible if r["observed_on"] == eligible[0]["observed_on"]]
    latest_per_series = {}
    for r in sorted(day, key=lambda r: r["seq"], reverse=True):
        latest_per_series.setdefault((r["session"], r["source"]), r)
    return max(latest_per_series.values(), key=lambda r: (r["published_at"], r["seq"]))


def market_context(version: dict, a: model.Assumptions, valuation: model.Valuation, price_row: dict | None) -> dict:
    """Price, implied market capitalisation and the scenario's value per share side by side, with every reason a comparison is not made."""
    if price_row is None:
        return {"status": "no_price", "reasons": ["no eligible price at this cutoff; record one manually or import a CSV"]}
    reasons = []
    if price_row["adjustment"] != "raw":
        reasons.append(f"the price is {price_row['adjustment'].replace('_', '-')}; market value needs an unadjusted (raw) price with the share count of the same date")
    if price_row["currency"] != a.currency:
        reasons.append(f"the price is in {price_row['currency']} but the scenario is in {a.currency}; no conversion is made")
    if a.share_count is None:
        reasons.append("the scenario has no selected share count")
    out = {"price_id": price_row["id"], "price": price_row["close"], "price_date": price_row["observed_on"], "currency": price_row["currency"],
           "adjustment": price_row["adjustment"], "source": price_row["source"], "session": price_row["session"]}
    if reasons:
        return {**out, "status": "not_comparable", "reasons": reasons}
    close = Decimal(price_row["close"])
    notes = []
    if a.share_count_date and a.share_count_date != price_row["observed_on"]:
        notes.append(f"share count dated {a.share_count_date}, price dated {price_row['observed_on']}")
    out.update({"status": "ok", "market_value": str(close * a.share_count), "share_count": str(a.share_count), "share_count_date": a.share_count_date,
                "notes": notes})
    if valuation.per_share is not None:
        out["value_per_share"] = str(valuation.per_share)
        out["value_to_price"] = str((valuation.per_share / close - 1) * 100)
    return out
