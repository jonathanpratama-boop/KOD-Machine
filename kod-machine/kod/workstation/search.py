"""Archive search over preserved sources, governed by the same information-time policy as everything else.

Passages are derived deterministically from each preserved document's bytes (PASSAGE_VERSION); the index can always be rebuilt from retained sources and
nothing is cached beyond the bytes' own hash. Ranking reuses the workbench's BM25 (kod.workbench.bm25).

Order of operations, so that nothing from after the cutoff can leak into results, snippets, ranking statistics or counts:
1. documents not eligible under the AsOfPolicy are set aside without trace (their text is never read and they are not counted);
2. eligible documents outside the company/source-type/period filters are set aside (counted by filter);
3. passages of the remaining documents form the corpus, each distinct passage text once, so copies do not inflate term statistics;
4. BM25 ranks the passages; a passage repeated in several documents is one result listing every document it appears in.
A score ranks reading order for this query. It is not importance, materiality or an expected return.
"""

from __future__ import annotations

from collections import Counter
import hashlib

from .. import earnings
from ..workbench import TOKEN, _tokens, bm25
from .policy import AsOfPolicy, eligibility

PASSAGE_VERSION = "KOD-PASSAGES-v2"  # v2: a short line always joins the next; line ranges end at the last line used
RANKING = "BM25 (k1 1.2, b 0.75) over distinct eligible passages; ranks reading order for this query, not importance or expected return"
SOURCE_TYPES = {"release": "Earnings releases and exhibits", "other_html": "Other preserved HTML"}
MERGE_BELOW, MERGE_UP_TO = 12, 60
SNIPPET = 320
MAX_QUERY = 200


def source_type(doc: dict) -> str | None:
    """The searchable type of a preserved document, or None for sources that are not text passages (JSON API responses, filing headers)."""
    if doc.get("role") in ("current", "comparison"):
        return "release"
    name = str(doc.get("filename", "")).lower()
    if doc.get("role") == "other" and name.endswith((".htm", ".html")):
        return "other_html"
    return None


def passages(raw: bytes, filename: str) -> list[dict]:
    """Deterministic passages: each text line of the document (paragraphs and table rows); a passage closes once it has MERGE_BELOW tokens, so a short
    line (a heading, a label) always stays with the line that follows it. line_start/line_end are the first and last lines whose text is in the passage."""
    try:
        lines = earnings.read_document(raw, filename)["lines"]
    except (earnings.EarningsError, ValueError):
        return []
    out, buffer, start, last, count = [], [], 0, 0, 0

    def flush():
        nonlocal buffer, count
        text = " ".join(buffer).strip()
        if text:
            out.append(
                {
                    "index": len(out),
                    "text": text,
                    "line_start": start,
                    "line_end": last,
                    "sha256": hashlib.sha256(
                        " ".join(text.split()).casefold().encode()
                    ).hexdigest(),
                }
            )
        buffer, count = [], 0

    for i, line in enumerate(lines):
        n = len(_tokens(line))
        if not n:
            continue
        if buffer and count >= MERGE_BELOW:
            flush()
        if not buffer:
            start = i
        buffer.append(line.strip())
        last = i
        count += n
    flush()
    return out


class ArchiveIndex:
    """Passages per document, keyed by the document's content hash and PASSAGE_VERSION (bytes are re-verified by the store on every read)."""

    def __init__(self, store):
        self.store = store
        self._cache = {}

    def of(self, doc: dict) -> list[dict]:
        key = (doc["sha256"], doc["filename"], PASSAGE_VERSION)
        if key not in self._cache:
            if len(self._cache) > 2000:
                self._cache.clear()
            self._cache[key] = passages(self.store.raw(doc["id"]), doc["filename"])
        return self._cache[key]


def _snippet(text: str, terms: set) -> list[dict]:
    """Up to SNIPPET characters around the first matching word, as segments [{'text', 'match'}] for escaped rendering. Matches are whole words of the
    full passage, found with the same tokenizer and case folding as the ranking, and are highlighted only when they lie wholly inside the window."""
    spans = [(m.start(), m.end()) for m in TOKEN.finditer(text) if m.group().casefold() in terms]
    first = spans[0][0] if spans else 0
    begin = max(0, first - SNIPPET // 3)
    end = min(len(text), begin + SNIPPET)
    segments, pos = [], begin
    if begin:
        segments.append({"text": "…", "match": False})
    for a, b in spans:
        if a < begin or b > end:
            continue
        if a > pos:
            segments.append({"text": text[pos:a], "match": False})
        segments.append({"text": text[a:b], "match": True})
        pos = b
    if pos < end:
        segments.append({"text": text[pos:end], "match": False})
    if end < len(text):
        segments.append({"text": "…", "match": False})
    return segments


def _availability(doc):
    return {
        "published_at": doc.get("published_at"),
        "publication_date": (doc.get("metadata") or {}).get("publication_date"),
        "observed_at": doc.get("observed_at"),
    }


def search(
    store,
    index: ArchiveIndex,
    query: str,
    policy: AsOfPolicy,
    security_ids=None,
    period: str | None = None,
    source_types=None,
    limit: int = 20,
) -> dict:
    query = str(query or "").strip()
    if len(query) > MAX_QUERY:
        raise ValueError(f"the query exceeds {MAX_QUERY} characters")
    if source_types:
        unknown = set(source_types) - set(SOURCE_TYPES)
        if unknown:
            raise ValueError("unknown source type: " + ", ".join(sorted(unknown)))
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    securities = {s["id"]: s for s in store.securities()}
    wanted = set(security_ids or []) or None
    excluded = Counter()
    eligible = []
    for doc in store.documents():
        if not eligibility(_availability(doc), policy)[0]:
            continue
        kind = source_type(doc)
        if kind is None:
            continue
        if wanted and doc["security_id"] not in wanted:
            excluded["outside_company_filter"] += 1
            continue
        if source_types and kind not in source_types:
            excluded["outside_source_type_filter"] += 1
            continue
        if period:
            label = (doc.get("metadata") or {}).get("period")
            if not label:
                excluded["reported_period_unknown"] += 1
                continue
            if label.casefold() != period.strip().casefold():
                excluded["outside_period_filter"] += 1
                continue
        eligible.append((doc, kind))
    occurrences, corpus = {}, {}
    total = 0
    for doc, kind in eligible:
        for p in index.of(doc):
            total += 1
            corpus.setdefault(p["sha256"], _tokens(p["text"]))
            occurrences.setdefault(p["sha256"], []).append((doc, kind, p))
    scores = bm25(corpus, query) if query else {}
    terms = set(_tokens(query))
    hits = [key for key, score in scores.items() if score > 0]

    def first_available(key):
        doc = occurrences[key][0][0]
        return doc.get("published_at") or (doc.get("metadata") or {}).get("publication_date") or ""

    # Stable sorts: score first, then the newest source, then document and passage order.
    hits.sort(key=lambda k: (occurrences[k][0][0]["id"], occurrences[k][0][2]["index"]))
    hits.sort(key=first_available, reverse=True)
    hits.sort(key=lambda k: -scores[k])
    results = []
    for key in hits[:limit]:
        doc, kind, p = occurrences[key][0]
        sec = securities.get(doc["security_id"]) or store.get_security(doc["security_id"])
        others, seen = [], {doc["id"]}
        for d, _, q in occurrences[key][1:]:
            if d["id"] not in seen:
                seen.add(d["id"])
                others.append(
                    {"document_id": d["id"], "passage_index": q["index"], "filename": d["filename"]}
                )
        results.append(
            {
                "score": round(scores[key], 6),
                "text": p["text"],
                "snippet": _snippet(p["text"], terms),
                "passage_sha256": key,
                "document_id": doc["id"],
                "passage_index": p["index"],
                "filename": doc["filename"],
                "source_type": kind,
                "source_url": doc["source_url"],
                "document_sha256": doc["sha256"],
                "ticker": sec["ticker"],
                "security_id": doc["security_id"],
                "period": (doc.get("metadata") or {}).get("period"),
                "published_at": doc.get("published_at"),
                "publication_date": (doc.get("metadata") or {}).get("publication_date"),
                "observed_at": doc.get("observed_at"),
                "also_in": others,
                "repeated_at": [
                    q["index"] for d, _, q in occurrences[key][1:] if d["id"] == doc["id"]
                ],
            }
        )
    return {
        "query": query,
        "policy": policy.as_dict(),
        "index_version": PASSAGE_VERSION,
        "ranking": RANKING,
        "filters": {
            "security_ids": sorted(wanted) if wanted else [],
            "period": period or None,
            "source_types": sorted(source_types or []),
        },
        "coverage": {
            "documents_searched": len(eligible),
            "excluded": dict(excluded),
            "passages": total,
            "distinct_passages": len(corpus),
            "matches": len(hits),
        },
        "results": results,
    }


def passage_context(
    store,
    index: ArchiveIndex,
    document_id: str,
    passage_index: int,
    policy: AsOfPolicy | None = None,
    around: int = 2,
) -> dict:
    """One passage with its neighbours, for an exact source link. With a policy, a document not eligible at the cutoff is refused."""
    doc = store.document(document_id)
    if source_type(doc) is None:
        raise ValueError("this source has no text passages")
    if policy is not None and not eligibility(_availability(doc), policy)[0]:
        raise ValueError("this source is not eligible at the selected cutoff")
    items = index.of(doc)
    if not 0 <= passage_index < len(items):
        raise ValueError("passage not found")
    return {
        "document": doc,
        "passage": items[passage_index],
        "before": items[max(0, passage_index - around) : passage_index],
        "after": items[passage_index + 1 : passage_index + 1 + around],
        "count": len(items),
        "index_version": PASSAGE_VERSION,
    }
