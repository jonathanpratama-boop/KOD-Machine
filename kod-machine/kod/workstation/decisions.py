"""Thesis versions, recorded reviews and decision packets.

- A thesis (company, title) has immutable versions: a statement, structured conditions (thesis.py) and a rationale.
- A review evaluates the thesis version that was current at the cutoff against the dossier at that cutoff. For a condition that depends on a scenario,
  the trace continues to the assumption version, the version it replaced and exactly which assumptions changed, so an assumption change can be followed
  from the changed number to the scenario result to the condition that now needs review.
- A decision packet freezes everything the decision rested on (the dossier read model at its cutoff, thesis version and evaluations, scenario assumption
  versions in full, calculations, evidence ids, open conflicts) together with the analyst's choice, rationale, review date/condition and an optional
  resolution rule. It is stored once with its SHA-256 and never changed. Reopening shows the stored packet; 'reproduce' rebuilds it from the workspace
  and lists any difference.
"""
from __future__ import annotations

import hashlib
import json

from . import dossier as dossier_model
from . import scenarios, thesis
from .domain import canonical, identity, timestamp
from .policy import AsOfPolicy, eligibility

PACKET_SCHEMA = "KOD-DECISION-PACKET-v2"
LEGACY_PACKET_SCHEMA = "KOD-DECISION-PACKET-v1"
EXPORT_NOTE = ("Contains preserved SEC data (public) and any user-supplied sources and prices; redistribution rights of user-supplied material are not "
               "established by this export. For private research use.")


def _now(service):
    return timestamp(service.clock())


def save_thesis(service, security_id: str, title: str, statement: str, conditions: list, rationale: str, author: str = "local_user") -> dict:
    service.store.get_security(security_id)
    title, statement, rationale = (str(x or "").strip() for x in (title, statement, rationale))
    if not title or len(title) > 120:
        raise ValueError("a thesis needs a title of 1 to 120 characters")
    if not statement or len(statement) > 4000:
        raise ValueError("state the thesis in 1 to 4,000 characters")
    if not rationale or len(rationale) > 4000:
        raise ValueError("record why this version (1 to 4,000 characters)")
    checked = thesis.validate_conditions(conditions)
    stored = canonical(checked)
    now = _now(service)
    with service.store._connection() as db:
        tid = identity("thesis", security_id, title)
        db.execute("INSERT OR IGNORE INTO theses VALUES (?,?,?,?,?)", (tid, security_id, title, now, author))
        last = db.execute("SELECT id, version, statement, conditions FROM thesis_versions WHERE thesis_id=? ORDER BY version DESC LIMIT 1", (tid,)).fetchone()
        if last is not None and last["statement"] == statement and last["conditions"] == stored:
            raise ValueError("the statement and conditions are identical to the current version; nothing was saved")
        version = (last["version"] + 1) if last else 1
        vid = identity("thv", tid, version, statement, stored)
        db.execute("INSERT INTO thesis_versions VALUES (?,?,?,?,?,?,?,?,?)", (vid, tid, version, statement, stored, rationale, author, now, last["id"] if last else None))
    return thesis_version(service, vid)


def thesis_version(service, version_id: str) -> dict:
    with service.store._connection() as db:
        row = db.execute("SELECT v.*, t.security_id, t.title FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id WHERE v.id=?", (version_id,)).fetchone()
    if row is None:
        raise ValueError("thesis version not found")
    return {**dict(row), "conditions": json.loads(row["conditions"])}


def theses(service, security_id: str) -> list:
    with service.store._connection() as db:
        rows = db.execute("SELECT * FROM theses WHERE security_id=? ORDER BY created_at, title", (security_id,)).fetchall()
        out = []
        for t in rows:
            versions = db.execute("SELECT id, version, created_at FROM thesis_versions WHERE thesis_id=? ORDER BY version DESC", (t["id"],)).fetchall()
            out.append({**dict(t), "versions": [dict(v) for v in versions]})
    return out


def version_at(service, thesis_id: str, cutoff: str) -> dict | None:
    """The thesis version that was current at the cutoff (the latest saved at or before it); a version written later is hindsight and is not used."""
    with service.store._connection() as db:
        row = db.execute("SELECT id FROM thesis_versions WHERE thesis_id=? AND created_at<=? ORDER BY version DESC LIMIT 1", (thesis_id, cutoff)).fetchone()
    return thesis_version(service, row["id"]) if row else None


def _assumption_trace(service, version_id: str, policy=None, context=None, legacy=False) -> dict:
    """The assumption version behind a scenario operand, what it replaced and what changed, and the recorded calculation for it."""
    v = scenarios.assumption_version(service, version_id)
    out = {"assumption_version_id": v["id"], "scenario": v["scenario"], "name": v["name"], "version": v["version"], "saved_at": v["created_at"],
           "rationale": v["rationale"], "previous_version_id": v["supersedes"], "changed": []}
    if v["supersedes"]:
        previous = scenarios.assumption_version(service, v["supersedes"])
        out["changed"] = [{"assumption": name, "from": old, "to": new} for name, old, new in scenarios.changed_fields(previous["assumptions"], v["assumptions"])]
    result = scenarios.run_version(service, v["id"], record=False, policy=None if legacy else policy,
                                   context=None if legacy else context, legacy=legacy)
    if not legacy:
        out["source_context"] = result.calculation.detail["source_context"]
    out["calculation_id"] = result.calculation_id
    out["result"] = {"status": result.valuation.status, "per_share": None if result.valuation.per_share is None else str(result.valuation.per_share),
                     "enterprise_value": None if result.valuation.enterprise_value is None else str(result.valuation.enterprise_value)}
    return out


def review(service, security_id: str, policy: AsOfPolicy, view: str = "as_reported", d: dict | None = None, *, legacy=False, source_membership=None) -> dict:
    """Evaluate every thesis of the company at the cutoff. Returns {'dossier', 'price', 'theses': [{thesis, version, evaluations}]}; nothing is recorded."""
    d = d or dossier_model.build(service, security_id, policy, view, legacy=legacy)
    source = d.get("classification_context")
    context = ({"source": source, "data": json.loads(service.store.raw(source["document_id"])) if source.get("document_id") else None}
               if source else service.submissions_context(security_id, policy, legacy=legacy))
    price = (scenarios.price_at(service, security_id, policy) if source_membership is None else
             scenarios.price(service, source_membership["price_id"]) if source_membership["price_id"] else None)
    if price:
        if price["security_id"] != security_id or not eligibility(price, policy)[0]:
            raise ValueError("frozen price does not belong to this company and cutoff")
        with service.store._connection() as db:
            imported = db.execute("SELECT document_id FROM price_imports WHERE id=?", (price["import_id"],)).fetchone()
        if imported and imported["document_id"]:
            service.store.raw(imported["document_id"])  # verify any preserved CSV source, including on replay
    cutoff = policy.as_dict()["cutoff"]
    out = []
    for t in theses(service, security_id):
        v = version_at(service, t["id"], cutoff)
        if v is None:
            continue
        evaluations = thesis.evaluate(v, d, {"price": price})
        for e in evaluations:
            for step in e["trace"]:
                for side in ("left", "right"):
                    src = step[side]["sources"]
                    if src.get("assumption_version_id"):
                        src["assumption_trace"] = _assumption_trace(service, src["assumption_version_id"], policy, context, legacy)
        out.append({"thesis": {k: t[k] for k in ("id", "title")}, "version": v, "evaluations": evaluations})
    return {"dossier": d, "price": price, "theses": out}


def record_review(service, security_id: str, policy: AsOfPolicy, view: str = "as_reported") -> list:
    """Evaluate and store the evaluations (immutable). Returns the stored rows."""
    result = review(service, security_id, policy, view)
    now = _now(service)
    rows = []
    with service.store._connection() as db:
        for t in result["theses"]:
            for e in t["evaluations"]:
                rid = identity("trev", e["thesis_version_id"], e["condition_id"], canonical(policy.as_dict()), view, e["status"], canonical(e["trace"]), now)
                db.execute("INSERT OR IGNORE INTO thesis_reviews VALUES (?,?,?,?,?,?,?,?)", (rid, e["thesis_version_id"], e["condition_id"], e["status"],
                                                                                         canonical(policy.as_dict()), view, canonical(e["trace"]), now))
                rows.append({**e, "id": rid, "created_at": now})
    return rows


def recorded_reviews(service, thesis_version_id: str) -> list:
    with service.store._connection() as db:
        return [{**dict(r), "trace": json.loads(r["trace"]), "policy": json.loads(r["policy"])}
                for r in db.execute("SELECT * FROM thesis_reviews WHERE thesis_version_id=? ORDER BY created_at DESC, id", (thesis_version_id,))]


# ---- decision packets ----

def _packet_body(service, security_id: str, policy: AsOfPolicy, view: str, question: str, schema=PACKET_SCHEMA, source_membership=None) -> dict:
    """Everything the decision rests on, from the shared read model."""
    legacy = schema == LEGACY_PACKET_SCHEMA
    if schema not in (LEGACY_PACKET_SCHEMA, PACKET_SCHEMA):
        raise ValueError("unsupported decision packet schema")
    context = (service.submissions_context(security_id, policy, source_membership["classification"])
               if source_membership is not None else None)
    d = dossier_model.build(service, security_id, policy, view, question, legacy=legacy, context=context)
    r = review(service, security_id, policy, view, d, legacy=legacy, source_membership=source_membership)
    assumption_versions = {}
    for sc in d["scenarios"]:
        v = scenarios.assumption_version(service, sc["version_id"])
        assumption_versions[v["id"]] = {k: v[k] for k in ("id", "scenario", "name", "version", "assumptions", "rationale", "author", "created_at", "supersedes")}
    evidence = sorted(d["observations"])
    body = {"schema": schema, "question": question, "policy": d["policy"], "view": view, "dossier": d,
            "theses": [{"thesis": t["thesis"], "version": t["version"], "evaluations": t["evaluations"]} for t in r["theses"]],
            "price": r["price"], "assumption_versions": assumption_versions, "evidence_ids": evidence,
            "calculation_ids": sorted(d["calculations"]), "unresolved": d["conflicts"], "export_note": EXPORT_NOTE}
    if not legacy:
        body["source_membership"] = {"classification": d["classification_context"], "price_id": r["price"]["id"] if r["price"] else None}
    return body


def save_packet(service, security_id: str, policy: AsOfPolicy, view: str, question: str, choice: str, rationale: str, thesis_version_id: str | None = None,
                review_date: str | None = None, review_condition: str | None = None, resolution_rule: str | None = None, author: str = "local_user") -> dict:
    service.store.get_security(security_id)
    question, choice, rationale = (str(x or "").strip() for x in (question, choice, rationale))
    if not question or len(question) > 400:
        raise ValueError("state the question in 1 to 400 characters")
    if not choice or len(choice) > 200:
        raise ValueError("record your choice in 1 to 200 characters")
    if not rationale or len(rationale) > 8000:
        raise ValueError("record the rationale in 1 to 8,000 characters")
    for name, value, limit in (("review condition", review_condition, 1000), ("resolution rule", resolution_rule, 2000)):
        if value and len(value) > limit:
            raise ValueError(f"the {name} is longer than {limit} characters")
    if review_date and not (len(review_date) == 10 and review_date[4] == "-" and review_date[7] == "-"):
        raise ValueError("the review date must be YYYY-MM-DD")
    body = _packet_body(service, security_id, policy, view, question)
    if thesis_version_id and thesis_version_id not in {t["version"]["id"] for t in body["theses"]}:
        raise ValueError("that thesis version was not current at this cutoff for this company")
    now = _now(service)
    body["decision"] = {"choice": choice, "rationale": rationale, "thesis_version_id": thesis_version_id, "review_date": review_date or None,
                        "review_condition": review_condition or None, "resolution_rule": resolution_rule or None, "author": author, "recorded_at": now,
                        "hindsight_note": ("the decision was recorded after its information cutoff; it is a reconstruction, not a contemporaneous decision"
                                           if now > policy.as_dict()["cutoff"] else None)}
    text = canonical(body)
    digest = hashlib.sha256(text.encode()).hexdigest()
    pid = identity("pkt", security_id, digest)
    with service.store._connection() as db:
        db.execute("INSERT INTO decision_packets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (pid, security_id, question, canonical(policy.as_dict()), view, thesis_version_id, choice, rationale, review_date or None, review_condition or None,
                    resolution_rule or None, text, digest, author, now))
    return packet(service, pid)


def packet(service, packet_id: str) -> dict:
    with service.store._connection() as db:
        row = db.execute("SELECT * FROM decision_packets WHERE id=?", (packet_id,)).fetchone()
    if row is None:
        raise ValueError("decision packet not found")
    if hashlib.sha256(row["packet"].encode()).hexdigest() != row["packet_sha256"]:
        raise ValueError("the stored decision packet does not match its recorded SHA-256")
    return {**dict(row), "packet": json.loads(row["packet"]), "policy": json.loads(row["policy"])}


def packets(service, security_id: str) -> list:
    with service.store._connection() as db:
        return [dict(r) for r in db.execute("SELECT id, question, choice, created_at, view, policy, packet_sha256 FROM decision_packets WHERE security_id=? "
                                            "ORDER BY created_at DESC", (security_id,))]


def reproduce(service, packet_id: str) -> dict:
    """Rebuild the packet's evidence from the workspace at its stored cutoff, policy and view and compare it with what was stored."""
    stored = packet(service, packet_id)
    body = stored["packet"]
    p = body["policy"]
    rebuilt = _packet_body(service, stored["security_id"], AsOfPolicy.parse(p["cutoff"], p["mode"], p["policy_version"]), body["view"], body["question"],
                           schema=body["schema"], source_membership=body.get("source_membership"))
    differences = []
    for key in ("dossier", "theses", "price", "assumption_versions", "evidence_ids", "calculation_ids", "unresolved"):
        if canonical(rebuilt[key]) != canonical(body[key]):
            differences.append(key)
    detail = []
    if "dossier" in differences:
        for key in sorted(set(body["dossier"]) | set(rebuilt["dossier"])):
            if canonical(body["dossier"].get(key)) != canonical(rebuilt["dossier"].get(key)):
                detail.append(f"dossier.{key}")
    return {"packet_id": packet_id, "reproduced": not differences, "differences": differences, "detail": detail,
            "note": "identical: the workspace reproduces the stored evidence using this packet's cutoff and source-selection rules" if not differences else
            "the workspace now yields different evidence at this cutoff (for example a new parser version or a changed record); the stored packet is unchanged"}


def render_markdown(stored: dict) -> str:
    """The packet as text, from the stored JSON only."""
    body = stored["packet"]
    dec = body["decision"]
    md = dossier_model.md_text
    lines = [f"# Decision packet: {md(body['dossier']['company']['ticker'])}", "",
             f"Recorded {dec['recorded_at']} by {md(dec['author'])} · cutoff {body['policy']['cutoff']} ({body['policy']['mode']}, {body['policy']['policy_version']}) · "
             f"{body['view'].replace('_', ' ')} view · {body['schema']} · SHA-256 {stored['packet_sha256']}", "",
             f"**Question:** {md(body['question'])}", "", f"**Choice:** {md(dec['choice'])}", "", "**Rationale:**", "", md(dec["rationale"], single_line=False), ""]
    if dec.get("hindsight_note"):
        lines += [f"> Note: {dec['hindsight_note']}.", ""]
    if dec.get("review_date") or dec.get("review_condition"):
        lines += [f"**Review:** {md(dec.get('review_date') or 'no date')} · {md(dec.get('review_condition') or 'no condition')}", ""]
    if dec.get("resolution_rule"):
        lines += [f"**Resolution rule:** {md(dec['resolution_rule'])}", ""]
    lines += ["## Thesis conditions at the cutoff", ""]
    for t in body["theses"]:
        lines.append(f"### {md(t['thesis']['title'])} (version {t['version']['version']})")
        lines.append("")
        lines.append(md(t["version"]["statement"], single_line=False))
        lines.append("")
        for e in t["evaluations"]:
            condition = next(c for c in t["version"]["conditions"] if c["id"] == e["condition_id"])
            lines.append(f"- **{e['status'].replace('_', ' ')}** — {md(e['label'])} [{md(thesis.describe(condition['expression']))}]")
            for step in e["trace"]:
                lines.append(f"  - {step['left']['label']} = {thesis.shown(step['left'])} {step['op']} {step['right']['label']} = {thesis.shown(step['right'])}"
                             f" → {step['result'].replace('_', ' ')}" + (f" ({step['reason']})" if step.get("reason") else "")
                             + "".join(f" [{step[side]['note']}]" for side in ("left", "right") if step[side].get("note")))
                for side in ("left", "right"):
                    at = step[side]["sources"].get("assumption_trace")
                    if at:
                        changed = "; ".join(f"{c['assumption']} {c['from']} → {c['to']}" for c in at["changed"]) or "first version"
                        lines.append(f"    - from {at['scenario']} assumptions v{at['version']} ({changed}); calculation {at['calculation_id']}")
        lines.append("")
    if not body["theses"]:
        lines += ["- No thesis was current at this cutoff.", ""]
    lines += ["## Scenario assumption versions", ""]
    for v in body["assumption_versions"].values():
        lines.append(f"- {v['scenario']} '{md(v['name'])}' v{v['version']} saved {v['created_at']}: {md(v['rationale'])}")
    if not body["assumption_versions"]:
        lines.append("- None saved by this cutoff.")
    lines += ["", f"Evidence: {len(body['evidence_ids'])} observations; {len(body['calculation_ids'])} calculations; {len(body['unresolved'])} open conflicts.", "",
              "---", "", dossier_model.render_markdown(body["dossier"]), "", body["export_note"], ""]
    return "\n".join(lines)

