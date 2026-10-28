"""Read-only, cutoff-aware research views over an explicitly linked document bundle.

This is an inspectable workbench inspired by published information-retrieval ideas,
not Bloomberg's proprietary implementation. It opens no ledger, writes no files,
retrieves no external content and grants no trading permission. Bundle timestamps,
security mappings, quotations and source lineage are supplied assertions, not verified
proof of historical public availability or independent sourcing.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import html
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlsplit

from .hashing import parse_ts, sha256_obj, sha256_text

SCHEMA = "KOD-WORKBENCH-v1"
REPORT_SCHEMA = "KOD-WORKBENCH-REPORT-v1"
ROLES = {"ACTUAL", "CONSENSUS", "PRIOR"}
TOKEN = re.compile(r"\w+", re.UNICODE)


def _string(value, field, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{field}: expected {'a string' if allow_empty else 'a nonempty string'}")
    return value


def _optional_string(value, field):
    return None if value is None else _string(value, field)


def _timestamp(value, field):
    if value is None:
        return None
    try:
        return parse_ts(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{field}: timezone-aware ISO timestamp required") from exc


def _iso(moment):
    return moment.isoformat().replace("+00:00", "Z") if moment is not None else None


def _decimal(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{field}: finite decimal string required (maximum 128 characters)")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field}: finite decimal string required") from exc
    if not result.is_finite() or (result and abs(result.adjusted()) > 1000):
        raise ValueError(f"{field}: nonfinite or excessively large/small decimal")
    return result


def _decimal_string(value):
    if not value:
        return "0"
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _scope(doc):
    return doc["event_id"], tuple(doc["security_ids"])


def _tokens(text):
    return TOKEN.findall(text.casefold())


def _validate(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema_version") != SCHEMA:
        raise ValueError(f"schema_version must be {SCHEMA}")
    if not isinstance(bundle.get("synthetic"), bool):
        raise ValueError("synthetic must be true or false")
    if not isinstance(bundle.get("securities"), list) or not isinstance(bundle.get("documents"), list):
        raise ValueError("securities and documents must be arrays")
    securities = {}
    for row in bundle["securities"]:
        if not isinstance(row, dict):
            raise ValueError("each security must be an object")
        sec = {k: _string(row.get(k), f"security.{k}")
               for k in ("security_id", "issuer_id", "ticker", "venue", "currency")}
        if sec["security_id"] in securities:
            raise ValueError("duplicate security_id: " + sec["security_id"])
        securities[sec["security_id"]] = sec
    documents = {}
    for row in bundle["documents"]:
        if not isinstance(row, dict):
            raise ValueError("each document must be an object")
        doc = {k: _string(row.get(k), f"document.{k}") for k in
               ("document_id", "event_id", "publisher", "source_url", "title", "text")}
        doc_id = doc["document_id"]
        if doc_id in documents:
            raise ValueError("duplicate document_id: " + doc_id)
        ids = row.get("security_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
            raise ValueError(f"{doc_id}: nonempty security_ids array required")
        if len(set(ids)) != len(ids) or any(i not in securities for i in ids):
            raise ValueError(f"{doc_id}: duplicate or unknown security reference")
        doc["security_ids"] = sorted(ids)
        if row.get("source_kind") not in ("PRIMARY", "SECONDARY"):
            raise ValueError(f"{doc_id}: source_kind must be PRIMARY or SECONDARY")
        doc["source_kind"] = row["source_kind"]
        try:
            parsed_url = urlsplit(doc["source_url"])
            if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
                raise ValueError("invalid URL")
        except ValueError as exc:
            raise ValueError(f"{doc_id}: source_url must be an http(s) URL") from exc
        for field in ("source_family", "replaces_document_id"):
            doc[field] = _optional_string(row.get(field), f"{doc_id}.{field}")
        for field in ("published_at", "observed_at"):
            doc[field] = _timestamp(row.get(field), f"{doc_id}.{field}")
        if (doc["published_at"] is not None and doc["observed_at"] is not None
                and doc["observed_at"] < doc["published_at"]):
            raise ValueError(f"{doc_id}: observed_at precedes published_at")
        observations = row.get("observations", [])
        if not isinstance(observations, list):
            raise ValueError(f"{doc_id}: observations must be an array")
        doc["observations"] = []
        for observation in observations:
            if not isinstance(observation, dict):
                raise ValueError(f"{doc_id}: each observation must be an object")
            obs = {k: _string(observation.get(k), f"{doc_id}.observation.{k}")
                   for k in ("metric", "unit", "period", "source_quote")}
            if not isinstance(observation.get("role"), str) or observation["role"] not in ROLES:
                raise ValueError(f"{doc_id}: observation role must be ACTUAL, CONSENSUS or PRIOR")
            obs["role"] = observation["role"]
            obs["value"] = _decimal(observation.get("value"), f"{doc_id}.observation.value")
            obs["currency"] = _optional_string(observation.get("currency"), f"{doc_id}.observation.currency")
            if obs["source_quote"] not in doc["text"]:
                raise ValueError(f"{doc_id}: source_quote must occur verbatim in the supplied text")
            doc["observations"].append(obs)
        doc["content_sha256"] = sha256_obj({"title": doc["title"], "text": doc["text"]})
        doc["normalized_sha256"] = sha256_text(" ".join((doc["title"] + "\n" + doc["text"]).casefold().split()))
        documents[doc_id] = doc
    for doc_id, doc in documents.items():
        predecessor = doc["replaces_document_id"]
        if predecessor is None:
            continue
        if predecessor not in documents:
            raise ValueError(f"{doc_id}: unknown replaces_document_id")
        parent = documents[predecessor]
        if _scope(doc) != _scope(parent):
            raise ValueError(f"{doc_id}: corrections must keep the same event and securities")
        if doc["published_at"] is not None and parent["published_at"] is not None and doc["published_at"] < parent["published_at"]:
            raise ValueError(f"{doc_id}: correction publication predates its predecessor")
        seen = {doc_id}
        while predecessor is not None:
            if predecessor in seen:
                raise ValueError(f"{doc_id}: correction cycle")
            seen.add(predecessor)
            predecessor = documents[predecessor]["replaces_document_id"]
    return securities, documents


def bm25(corpus, query):
    """BM25 (k1=1.2, b=0.75) of each corpus entry for the query. `corpus` maps a key (one per unique text) to its tokens; callers that hold repeated copies
    of one text pass it once, so copies do not alter corpus statistics. Returns key -> score; an empty query scores 0."""
    if not corpus or not query.strip():
        return {key: 0.0 for key in corpus}
    terms = set(_tokens(query))
    counters = {key: Counter(value) for key, value in corpus.items()}
    average = sum(map(len, corpus.values())) / len(corpus)
    frequency = {term: sum(term in c for c in counters.values()) for term in terms}
    output = {}
    for key, tokens in corpus.items():
        counter, length, score = counters[key], len(tokens), 0.0
        for term in sorted(terms):
            tf = counter[term]
            if not tf:
                continue
            idf = math.log(1 + (len(corpus) - frequency[term] + .5) / (frequency[term] + .5))
            score += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / (average or 1)))
        output[key] = score
    return output


def _scores(documents, query):
    """BM25 over unique supplied content; repeated copies do not alter corpus statistics."""
    corpus = {d["normalized_sha256"]: _tokens(d["title"] + " " + d["text"])
              for d in documents}
    scores = bm25(corpus, query)
    return {d["document_id"]: scores[d["normalized_sha256"]] for d in documents}


def _comparisons(documents):
    groups = defaultdict(list)
    publication_times = {doc["document_id"]: doc["published_at"] for doc in documents}
    for doc in documents:
        for obs in doc["observations"]:
            key = obs["metric"], obs["unit"], obs["currency"], obs["period"]
            groups[key].append((doc["document_id"], obs))
    result = []
    for key, records in sorted(groups.items(), key=lambda pair: tuple("" if x is None else x for x in pair[0])):
        roles = {role: {obs["value"] for _, obs in records if obs["role"] == role}
                 for role in ROLES}
        row = dict(zip(("metric", "unit", "currency", "period"), key))
        row.update(status="INSUFFICIENT_DATA", actual=None, consensus=None, difference=None,
                   difference_pct=None, percent_basis="100*(actual-consensus)/abs(consensus)",
                   difference_pct_decimal_places=12, reason=None,
                   evidence=[{"document_id": doc_id, "role": obs["role"],
                              "value": _decimal_string(obs["value"]), "source_quote": obs["source_quote"],
                              "published_at": _iso(publication_times[doc_id])}
                             for doc_id, obs in records])
        if any(len(roles[role]) > 1 for role in ("ACTUAL", "CONSENSUS")):
            row.update(status="DATA_CONFLICT", reason="Conflicting current ACTUAL or CONSENSUS values; comparison withheld.")
        elif not roles["ACTUAL"] or not roles["CONSENSUS"]:
            row["reason"] = "Matching ACTUAL and CONSENSUS observations are required; units, currency and period are not converted."
        elif not any(publication_times[doc_id] < min(publication_times[actual_id]
                         for actual_id, actual_obs in records if actual_obs["role"] == "ACTUAL")
                     for doc_id, obs in records if obs["role"] == "CONSENSUS"):
            row["reason"] = "pre-release consensus is required: a matching consensus document must be published strictly before the earliest current actual document. Supplied timestamps are not independently verified."
        else:
            actual, consensus = next(iter(roles["ACTUAL"])), next(iter(roles["CONSENSUS"]))
            with localcontext() as context:
                context.prec = 4096
                context.rounding = ROUND_HALF_EVEN
                difference = actual - consensus
                percent = (100 * difference / abs(consensus)).quantize(Decimal("0.000000000001")) if consensus else None
            row.update(status="OK", actual=_decimal_string(actual), consensus=_decimal_string(consensus),
                       difference=_decimal_string(difference),
                       difference_pct=_decimal_string(percent) if percent is not None else None,
                       reason="Zero consensus denominator; percentage is undefined." if consensus == 0 else None)
        result.append(row)
    return result


def _card(scope, documents, securities, scores):
    replaced = {d["replaces_document_id"] for d in documents if d["replaces_document_id"] is not None}
    current = [d for d in documents if d["document_id"] not in replaced]
    # A visible correction can replace a predecessor absent at this cutoff; only visible
    # documents contribute to this derived view. Branching corrections remain conflicts.
    current.sort(key=lambda d: (d["source_kind"] != "PRIMARY", -scores[d["document_id"]],
                                -d["published_at"].timestamp(), d["document_id"]))
    representative = current[0]
    citations = []
    for doc in sorted(documents, key=lambda d: (d["published_at"], d["document_id"])):
        citations.append({k: doc[k] for k in ("document_id", "source_url", "publisher", "source_kind",
                                             "source_family", "content_sha256", "normalized_sha256", "replaces_document_id")})
        citations[-1].update(published_at=_iso(doc["published_at"]), observed_at=_iso(doc["observed_at"]),
                             current=doc["document_id"] not in replaced,
                             content_hash_basis="SUPPLIED_TITLE_AND_TEXT")
    event_id, security_ids = scope
    unique = len({d["normalized_sha256"] for d in documents})
    return {"card_id": "WB-" + sha256_obj({"event_id": event_id, "security_ids": security_ids})[:20],
            "event_id": event_id, "security_ids": list(security_ids),
            "securities": [securities[s] for s in security_ids],
            "title": representative["title"], "preview": representative["text"][:280],
            "preview_type": "EXTRACTIVE_PREVIEW", "relevance_score": max(scores[d["document_id"]] for d in current),
            "latest_publication_at": _iso(max(d["published_at"] for d in documents)),
            "document_count": len(documents), "unique_content_count": unique,
            "duplicate_count": len(documents) - unique,
            "declared_source_families": sorted({d["source_family"] for d in documents if d["source_family"] is not None}),
            "source_lineage_unknown_count": sum(d["source_family"] is None for d in documents),
            "citations": citations, "current_document_ids": sorted(d["document_id"] for d in current),
            "superseded_document_ids": sorted(d["document_id"] for d in documents if d["document_id"] in replaced),
            "corrections": [{"document_id": d["document_id"], "replaces_document_id": d["replaces_document_id"]}
                            for d in sorted(documents, key=lambda d: d["document_id"]) if d["replaces_document_id"] is not None],
            "comparisons": _comparisons(current)}


def build_report(bundle, as_of, query="", security_id=None, limit=10, mode="observed"):
    """Build a deterministic research report; no external IO or mutation is performed.

    ``observed`` enforces both supplied publication and observation cutoffs.
    ``public`` is a historical timestamp-only reconstruction, never proof of what
    this system knew then. Unknown dates are never replaced with retrieval dates.
    """
    if mode not in ("observed", "public"):
        raise ValueError("mode must be observed or public")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    _string(query, "query", allow_empty=True)
    cutoff = _timestamp(as_of, "as_of")
    if cutoff is None:
        raise ValueError("as_of is required")
    securities, all_documents = _validate(bundle)
    if security_id is not None and (not isinstance(security_id, str) or security_id not in securities):
        raise ValueError("unknown security_id")
    eligible, excluded = [], []
    for doc in sorted(all_documents.values(), key=lambda d: d["document_id"]):
        reasons = []
        if doc["published_at"] is None:
            reasons.append("publication_time_unknown")
        elif doc["published_at"] > cutoff:
            reasons.append("published_after_cutoff")
        if mode == "observed":
            if doc["observed_at"] is None:
                reasons.append("observation_time_unknown")
            elif doc["observed_at"] > cutoff:
                reasons.append("observed_after_cutoff")
        if security_id is not None and security_id not in doc["security_ids"]:
            reasons.append("outside_security_filter")
        if reasons:
            excluded.append({"document_id": doc["document_id"], "reasons": reasons})
        else:
            eligible.append(doc)
    groups = defaultdict(list)
    for doc in eligible:
        groups[_scope(doc)].append(doc)
    # Exclude superseded text from search statistics as well as numeric comparisons.
    replaced = {d["replaces_document_id"] for d in eligible if d["replaces_document_id"] is not None}
    scores = _scores([d for d in eligible if d["document_id"] not in replaced], query)
    scores.update({d["document_id"]: 0.0 for d in eligible if d["document_id"] in replaced})
    cards = [_card(scope, rows, securities, scores) for scope, rows in groups.items()]
    search = [card for card in cards if not query.strip() or card["relevance_score"] > 0]
    search.sort(key=lambda c: (-c["relevance_score"], -parse_ts(c["latest_publication_at"]).timestamp(), c["card_id"]))
    primary = [card for card in cards if any(c["source_kind"] == "PRIMARY" for c in card["citations"])]
    primary.sort(key=lambda c: (-parse_ts(c["latest_publication_at"]).timestamp(), c["card_id"]))
    warnings = ["INPUT_BUNDLE_ONLY: counts describe the supplied bundle, not completed market/source coverage.",
                "Mappings, timestamps, quotations and source families are supplied assertions; no source or historical-content verification is performed.",
                "Declared source families and publisher diversity do not prove independent corroboration.",
                "Relevance scores rank research attention, not expected returns or entry eligibility."]
    if mode == "public":
        warnings.insert(0, "HISTORICAL_RECONSTRUCTION: observation cutoff is not enforced; this report does not show what the system knew then.")
    if bundle["synthetic"]:
        warnings.insert(0, "SYNTHETIC DEMONSTRATION: invented inputs, not investment or productivity results.")
    return {"schema_version": REPORT_SCHEMA, "research_only": True, "entry_permission": False,
            "input_bundle_sha256": sha256_obj(bundle),
            "synthetic": bundle["synthetic"], "mode": mode,
            "availability_basis": "SUPPLIED_PUBLICATION_AND_OBSERVATION_TIMES" if mode == "observed" else "HISTORICAL_RECONSTRUCTION_PUBLICATION_ONLY",
            "as_of": _iso(cutoff), "query": query, "security_id": security_id,
            "coverage": {"scope": "INPUT_BUNDLE_ONLY", "securities_input": len(securities),
                         "documents_input": len(all_documents), "documents_eligible": len(eligible),
                         "documents_excluded": len(excluded), "eligible_events": len(cards),
                         "search_events_total": len(search), "primary_events_total": len(primary)},
            "excluded_documents": excluded, "search_results": search[:limit],
            "primary_disclosures": primary[:limit], "warnings": warnings}


def _md(value):
    text = html.escape(str(value), quote=True).replace("\n", " ").replace("\r", " ")
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text)


def render_markdown(report):
    """Escape supplied text and safely link the validated http(s) source URLs."""
    lines = ["# KOD research workbench", "", "Research only. No entry permission.", "",
             f"As of: {_md(report['as_of'])}; mode: {_md(report['mode'])}", ""]
    for warning in report["warnings"]:
        lines.extend(["> " + _md(warning), ""])
    counts = report["coverage"]
    lines.extend([f"Bundle documents: {counts['documents_input']}; eligible: {counts['documents_eligible']}; excluded: {counts['documents_excluded']}.", ""])
    for key, heading in (("search_results", "Search results"), ("primary_disclosures", "Primary disclosures")):
        lines.extend(["## " + heading, ""])
        if not report[key]:
            lines.extend(["No matching event in eligible supplied documents.", ""])
        for card in report[key]:
            lines.extend(["### " + _md(card["title"]), "",
                          f"Event: {_md(card['event_id'])}; securities: {_md(', '.join(card['security_ids']))}", "",
                          "Extractive preview: " + _md(card["preview"]), "",
                          f"Documents: {card['document_count']}; unique content: {card['unique_content_count']}; duplicate copies: {card['duplicate_count']}.", ""])
            for citation in card["citations"]:
                status = "current" if citation["current"] else "superseded"
                safe_url = quote(citation["source_url"], safe=":/?#[]@!$&'()*+,;=%")
                lines.append(f"- {_md(citation['document_id'])} ({status}, {_md(citation['source_kind'])}): [{_md(citation['publisher'])}](<{safe_url}>)")
            lines.append("")
            for comp in card["comparisons"]:
                values = f"actual={comp['actual']}, consensus={comp['consensus']}, difference={comp['difference']}, percentage={comp['difference_pct']}"
                lines.extend([f"- {_md(comp['metric'])} / {_md(comp['period'])} / {_md(comp['unit'])} / {_md(comp['currency'])}: {_md(comp['status'])}; {_md(values)}.", ""])
                if comp["reason"]:
                    lines.extend(["  " + _md(comp["reason"]), ""])
    lines.extend(["## Excluded documents", ""])
    lines.extend([f"- {_md(row['document_id'])}: {_md(', '.join(row['reasons']))}" for row in report["excluded_documents"]])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="local KOD-WORKBENCH-v1 JSON bundle")
    parser.add_argument("--as-of", required=True, help="timezone-aware ISO information cutoff")
    parser.add_argument("--query", default="")
    parser.add_argument("--security-id")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--mode", choices=("observed", "public"), default="observed")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        with Path(args.input).open(encoding="utf-8") as stream:
            bundle = json.load(stream)
        report = build_report(bundle, args.as_of, args.query, args.security_id, args.limit, args.mode)
        print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) if args.format == "json" else render_markdown(report), end="\n" if args.format == "json" else "")
    except (OSError, UnicodeError, ValueError, InvalidOperation) as exc:
        print(f"workbench input error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
