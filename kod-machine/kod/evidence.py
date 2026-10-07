"""Evidence objects v2 (KOD-EVIDENCE-v2): what was knowable, with how we know it.

An evidence object describes one document offered as proof of what was public at an
as-of cutoff. It records separately:

  existence  - that the document existed (was public) at or before the cutoff
  content    - that the bytes held here are what was available then

A timestamp proving a filing existed does not prove that the copy retrieved today has
the contents it had then, so the two are verified by different methods and never
inferred from each other. Publication time is the source's own time; retrieval time is
when we fetched a copy. One is never filled in from the other.

The grade is not the operator's opinion. Each object has a ceiling computed from its
fields, and a declared grade stronger than the ceiling is refused:

  A  contemporaneous PRIMARY source, existence AND content verified, published by the cutoff
  B  PRIMARY or SECONDARY source, existence verified by a contemporaneous method,
     published by the cutoff; content not verified
  C  PRIMARY or SECONDARY source dated by the cutoff, but neither existence nor content
     verified (a currently accessible page with a historical date)
  D  retrospective: a later account, an unknown publication time, or published after the cutoff

Objects are immutable. A better-verified copy is a new object with a new id; a card that
cited the weaker object keeps citing it.
"""

from __future__ import annotations

from datetime import datetime

from .hashing import fmt_ts, parse_ts, sha256_obj

EVIDENCE_HASH_VERSION = "KOD-EVIDENCE-v2"
SOURCE_TYPES = ("PRIMARY", "SECONDARY", "RETROSPECTIVE")
GRADES = {
    "A": "contemporaneous primary evidence with verified existence and contents",
    "B": "strongly corroborated contemporaneous evidence: existence verified, contents not",
    "C": "currently accessible, historically dated page whose original contents are unverified",
    "D": "retrospective source",
}
EXISTENCE_METHODS = {
    "PRIMARY_SOURCE_TIMESTAMP": "the primary source's own system records the publication time",
    "CONTEMPORANEOUS_ARCHIVE": "an independent archive captured the document at or before the cutoff",
    "EXTERNAL_TIMESTAMP_RECEIPT": "the bytes were captured and RFC 3161-timestamped at or before the cutoff",
    "CORROBORATED_CONTEMPORANEOUS": "two or more independent evidence objects published by the cutoff report it",
    "NONE": "not verified",
}
CONTENT_METHODS = {
    "CONTEMPORANEOUS_ARCHIVE_HASH_MATCH": "the copy held here is an archive capture from at or before the cutoff",
    "EXTERNAL_TIMESTAMP_RECEIPT": "content_sha256 was RFC 3161-timestamped at or before the cutoff",
    "NONE": "not verified",
}
# A true value of these facts asserts that a primary document existed. In strict records it
# must cite a PRIMARY evidence object whose existence is verified.
PRIMARY_CLAIM_FACTS = ("primary_document_public", "mechanism_in_primary_docs")
STRICT = "STRICT-v3"
PARTIAL = "PARTIAL"
INTEGRITY_LEVELS = (STRICT, PARTIAL)
RETRIEVAL_WORDS = ("retriev", "download", "access time", "accessed", "fetched", "crawl")


class EvidenceError(ValueError):
    pass


def _ts(value, name: str, required: bool = False) -> datetime | None:
    if value in (None, ""):
        if required:
            raise EvidenceError(f"{name} is required")
        return None
    try:
        return parse_ts(value)
    except ValueError as exc:
        raise EvidenceError(f"{name}: {exc}") from exc


def grade_ceiling(source_type: str, publication: datetime | None, cutoff: datetime,
                  existence_verified: bool, content_verified: bool) -> str:
    dated = publication is not None and publication <= cutoff
    if source_type == "RETROSPECTIVE" or not dated:
        return "D"
    if source_type == "PRIMARY" and existence_verified and content_verified:
        return "A"
    if existence_verified:
        return "B"
    return "C"


def build_object(meta: dict, now: datetime, content_sha256: str | None, archived_copy: str | None,
                 stamps: list[dict], other_objects: dict) -> dict:
    """Validate an evidence declaration and return the frozen object (without its id).

    `stamps` are verified external timestamps on content_sha256: [{"authority", "time"}].
    `other_objects` maps existing v2 evidence ids to their frozen objects (for corroboration).
    Raises EvidenceError on anything inconsistent; never downgrades silently."""
    for key in ("source_url", "source_type", "publisher", "document_type", "evidence_grade",
                "existence_method", "content_method", "provenance"):
        if not str(meta.get(key) or "").strip():
            raise EvidenceError(f"{key} is required")
    source_type = meta["source_type"].upper()
    if source_type not in SOURCE_TYPES:
        raise EvidenceError(f"source_type must be one of {SOURCE_TYPES}")
    grade = str(meta["evidence_grade"]).upper()
    if grade not in GRADES:
        raise EvidenceError(f"evidence_grade must be one of {sorted(GRADES)}")
    existence_method = meta["existence_method"].upper()
    content_method = meta["content_method"].upper()
    if existence_method not in EXISTENCE_METHODS:
        raise EvidenceError(f"existence_method must be one of {sorted(EXISTENCE_METHODS)}")
    if content_method not in CONTENT_METHODS:
        raise EvidenceError(f"content_method must be one of {sorted(CONTENT_METHODS)}")

    cutoff = _ts(meta.get("as_of_cutoff"), "as_of_cutoff", required=True)
    retrieval = _ts(meta.get("retrieval_time"), "retrieval_time", required=True)
    publication = _ts(meta.get("publication_time"), "publication_time")
    event = _ts(meta.get("event_time"), "event_time")
    archive_time = _ts(meta.get("archive_time"), "archive_time")
    archive_url = meta.get("archive_url") or None
    basis = str(meta.get("publication_time_basis") or "").strip()

    if retrieval > now:
        raise EvidenceError("retrieval_time is in the future")
    if archive_time and archive_time > now:
        raise EvidenceError("archive_time is in the future")
    if archive_time and not archive_url:
        raise EvidenceError("archive_time needs the archive_url it came from")
    if publication is not None:
        if not basis:
            raise EvidenceError("publication_time needs publication_time_basis: where that time comes from")
        if any(word in basis.lower() for word in RETRIEVAL_WORDS):
            raise EvidenceError("publication_time_basis describes a retrieval; retrieval time is not a publication time")
        if publication > retrieval:
            raise EvidenceError("publication_time is after retrieval_time")
        if publication > cutoff and not (source_type == "RETROSPECTIVE" and grade == "D"):
            raise EvidenceError(
                f"publication_time {fmt_ts(publication)} is after as_of_cutoff {fmt_ts(cutoff)}: the document was not "
                f"public at the cutoff (only a RETROSPECTIVE grade D account may postdate it)"
            )
    claimed_existence = meta.get("existence_verified")
    claimed_content = meta.get("content_verified")

    # Existence: each method has to be shown, not asserted.
    corroborated_by = list(meta.get("corroborated_by") or [])
    stamp_ok = [s for s in stamps if parse_ts(s["time"]) <= cutoff]
    if existence_method == "PRIMARY_SOURCE_TIMESTAMP":
        if source_type != "PRIMARY" or publication is None or publication > cutoff:
            raise EvidenceError("PRIMARY_SOURCE_TIMESTAMP needs a PRIMARY source with a publication_time by the cutoff")
    elif existence_method == "CONTEMPORANEOUS_ARCHIVE":
        if not archive_url or archive_time is None or archive_time > cutoff:
            raise EvidenceError("CONTEMPORANEOUS_ARCHIVE needs archive_url and an archive_time at or before the cutoff")
    elif existence_method == "EXTERNAL_TIMESTAMP_RECEIPT":
        if not content_sha256 or not stamp_ok:
            raise EvidenceError("EXTERNAL_TIMESTAMP_RECEIPT needs the bytes and an external timestamp at or before the cutoff")
    elif existence_method == "CORROBORATED_CONTEMPORANEOUS":
        others = [other_objects.get(i) for i in corroborated_by]
        if len(corroborated_by) < 2 or any(o is None for o in others):
            raise EvidenceError("CORROBORATED_CONTEMPORANEOUS needs corroborated_by: two or more recorded evidence ids")
        if len({o["publisher"] for o in others}) < 2:
            raise EvidenceError("corroborating evidence must come from at least two different publishers")
        for o in others:
            if o["publication_time"] is None or parse_ts(o["publication_time"]) > cutoff or o["evidence_grade"] == "D":
                raise EvidenceError("each corroborating object must be dated at or before the cutoff and not grade D")
    existence_verified = existence_method != "NONE"

    if content_method == "CONTEMPORANEOUS_ARCHIVE_HASH_MATCH":
        if not content_sha256 or not archive_url or archive_time is None or archive_time > cutoff:
            raise EvidenceError("CONTEMPORANEOUS_ARCHIVE_HASH_MATCH needs the archived bytes, archive_url and an "
                                "archive_time at or before the cutoff")
    elif content_method == "EXTERNAL_TIMESTAMP_RECEIPT":
        if not content_sha256 or not stamp_ok:
            raise EvidenceError("content EXTERNAL_TIMESTAMP_RECEIPT needs the bytes timestamped at or before the cutoff")
    content_verified = content_method != "NONE"

    if claimed_existence is not None and bool(claimed_existence) != existence_verified:
        raise EvidenceError(f"existence_verified={claimed_existence} disagrees with existence_method {existence_method}")
    if claimed_content is not None and bool(claimed_content) != content_verified:
        raise EvidenceError(f"content_verified={claimed_content} disagrees with content_method {content_method}")

    ceiling = grade_ceiling(source_type, publication, cutoff, existence_verified, content_verified)
    if grade < ceiling:  # 'A' < 'B' < 'C' < 'D'
        raise EvidenceError(
            f"grade {grade} claimed, but the verification recorded supports at most grade {ceiling}"
        )
    return {
        "evidence_hash_version": EVIDENCE_HASH_VERSION,
        "source_url": meta["source_url"],
        "source_type": source_type,
        "publisher": meta["publisher"],
        "document_type": meta["document_type"],
        "title": meta.get("title", ""),
        "event_time": fmt_ts(event) if event else None,
        "publication_time": fmt_ts(publication) if publication else None,
        "publication_time_basis": basis or None,
        "retrieval_time": fmt_ts(retrieval),
        "archive_url": archive_url,
        "archive_time": fmt_ts(archive_time) if archive_time else None,
        "as_of_cutoff": fmt_ts(cutoff),
        "content_sha256": content_sha256,
        "archived_copy": archived_copy or archive_url,
        "evidence_grade": grade,
        "grade_ceiling": ceiling,
        "existence_verified": existence_verified,
        "content_verified": content_verified,
        "verification_method": {"existence": existence_method, "content": content_method},
        "verification_notes": meta.get("verification_notes", ""),
        "corroborated_by": sorted(corroborated_by),
        "content_timestamps": sorted(stamps, key=lambda s: s["authority"]),
        "provenance": meta["provenance"],
    }


def evidence_id(obj: dict) -> str:
    return sha256_obj(obj)


def citation_problems(horizons: dict, objects: dict, integrity: str, opened_at: datetime) -> list[str]:
    """Rules for a card's citations. `objects` maps v2 evidence ids to frozen objects plus
    their recorded_at. Strict cards: every known fact cites evidence that was public at the
    set's cutoff, none of it grade D, and primary claims cite verified primary documents."""
    strict = integrity == STRICT
    problems = []
    for horizon, payload in horizons.items():
        facts = payload.get("facts") or {}
        cited = payload.get("evidence") or {}
        claims = payload.get("fact_grades") or {}
        try:
            cutoff = parse_ts(payload.get("cutoff", ""))
        except ValueError:
            continue  # reported by the horizon check
        for fact in sorted(set(cited) - set(facts)):
            problems.append(f"{horizon}: evidence cites {fact!r}, which is not a fact in this set")
        for fact in sorted(set(claims) - set(facts)):
            problems.append(f"{horizon}: fact_grades names {fact!r}, which is not a fact in this set")
        for fact, value in facts.items():
            ids = cited.get(fact) or []
            if not isinstance(ids, list):
                problems.append(f"{horizon}: evidence for {fact!r} must be a list of evidence ids")
                continue
            if value is None:
                if ids:
                    problems.append(f"{horizon}: {fact!r} is UNKNOWN (null) but cites evidence")
                continue
            if strict and not ids:
                problems.append(f"{horizon}: fact {fact!r} = {value!r} cites no evidence")
            usable = []
            for eid in ids:
                obj = objects.get(eid)
                if obj is None:
                    problems.append(f"{horizon}: {fact!r} cites {eid[:16]}, which is not a recorded v2 evidence object")
                    continue
                if parse_ts(obj["recorded_at"]) > opened_at:
                    problems.append(f"{horizon}: {fact!r} cites evidence {eid[:12]} recorded after the open")
                    continue
                pub = obj["publication_time"]
                if obj["evidence_grade"] == "D":
                    if strict:
                        problems.append(f"{horizon}: {fact!r} cites grade D (retrospective) evidence {eid[:12]}; "
                                        f"a strict record needs evidence that was public at the cutoff")
                        continue
                elif pub is None or parse_ts(pub) > cutoff:
                    problems.append(f"{horizon}: {fact!r} cites evidence {eid[:12]} not published by the "
                                    f"{horizon} cutoff {fmt_ts(cutoff)}")
                    continue
                if strict and parse_ts(obj["as_of_cutoff"]) > cutoff:
                    problems.append(f"{horizon}: {fact!r} cites evidence {eid[:12]} graded as of "
                                    f"{obj['as_of_cutoff']}, after this set's cutoff")
                    continue
                usable.append(obj)
            if strict and value is True and fact in PRIMARY_CLAIM_FACTS and not any(
                o["source_type"] == "PRIMARY" and o["existence_verified"] for o in usable
            ):
                problems.append(f"{horizon}: {fact!r} = true claims a primary document but cites no PRIMARY "
                                f"evidence with verified existence")
            if fact in claims:
                claimed = str(claims[fact]).upper()
                best = min((o["evidence_grade"] for o in usable), default="E")
                if claimed not in GRADES or claimed < best:
                    problems.append(f"{horizon}: fact {fact!r} claims grade {claimed}, but its usable evidence "
                                    f"supports at most {best if best != 'E' else 'nothing'}")
    return problems
