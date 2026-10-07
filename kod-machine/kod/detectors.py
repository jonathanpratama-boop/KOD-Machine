"""Weak-signal detectors. Hypotheses only. Missing inputs stay INSUFFICIENT_DATA.

Rule version KOD-DET-v0 is frozen. Threshold edits require KOD-DET-v1 and a new cohort.
These are not ASTRA COMPRESSION / IGNITION / EQ_GAP and do not enter that cohort.
"""

from __future__ import annotations

RULE_VERSION = "KOD-DET-v0"

DETECTORS = (
    "DATED_CATALYST_KNOWN",
    "PRIMARY_DOC_BEFORE_PRICE",
    "VOLUME_CREEP_PRICE_QUIET",
    "NARRATIVE_WITHOUT_MECHANISM",
    "COVERAGE_INCOMPLETE",
)

# What counts as a hit when the scorer computes hit rates and lift. Fixed before any
# prospective outcome exists. NARRATIVE_WITHOUT_MECHANISM is the failure detector, so
# its hit is a down repricing. Changing a hit label is a rule change: new RULE_VERSION.
HIT_LABEL = {name: "REPRICED_UP" for name in DETECTORS}
HIT_LABEL["NARRATIVE_WITHOUT_MECHANISM"] = "REPRICED_DOWN"


def evaluate(information_sets: dict) -> list[dict]:
    """Evaluate detectors on the T-24H set. Earlier horizons are context, not a second vote."""
    latest = information_sets.get("T-24H") or {}
    facts = latest.get("facts") or {}
    results = []
    results.append(_dated_catalyst(facts))
    results.append(_primary_doc(facts))
    results.append(_volume_creep(facts))
    results.append(_narrative(facts))
    results.append(_coverage(latest))
    return results


def _row(name: str, status: str, features: dict) -> dict:
    return {
        "detector": name,
        "rule_version": RULE_VERSION,
        "status": status,
        "features": features,
    }


def _dated_catalyst(facts: dict) -> dict:
    known = facts.get("dated_catalyst_known")
    if known is None:
        return _row("DATED_CATALYST_KNOWN", "INSUFFICIENT_DATA", {"dated_catalyst_known": None})
    return _row(
        "DATED_CATALYST_KNOWN",
        "SIGNAL" if known is True else "NO_SIGNAL",
        {"dated_catalyst_known": known, "catalyst": facts.get("catalyst")},
    )


def _primary_doc(facts: dict) -> dict:
    public = facts.get("primary_document_public")
    repriced = facts.get("price_already_repriced")
    if public is None or repriced is None:
        return _row(
            "PRIMARY_DOC_BEFORE_PRICE",
            "INSUFFICIENT_DATA",
            {"primary_document_public": public, "price_already_repriced": repriced},
        )
    status = "SIGNAL" if public is True and repriced is False else "NO_SIGNAL"
    return _row("PRIMARY_DOC_BEFORE_PRICE", status, {"primary_document_public": public, "price_already_repriced": repriced})


def _volume_creep(facts: dict) -> dict:
    creep = facts.get("volume_creep_before_story")
    quiet = facts.get("price_quiet_vs_own_range")
    if creep is None or quiet is None:
        return _row(
            "VOLUME_CREEP_PRICE_QUIET",
            "INSUFFICIENT_DATA",
            {"volume_creep_before_story": creep, "price_quiet_vs_own_range": quiet},
        )
    status = "SIGNAL" if creep is True and quiet is True else "NO_SIGNAL"
    return _row(
        "VOLUME_CREEP_PRICE_QUIET",
        status,
        {"volume_creep_before_story": creep, "price_quiet_vs_own_range": quiet},
    )


def _narrative(facts: dict) -> dict:
    narrative = facts.get("narrative_only")
    mechanism = facts.get("mechanism_in_primary_docs")
    if narrative is None or mechanism is None:
        return _row(
            "NARRATIVE_WITHOUT_MECHANISM",
            "INSUFFICIENT_DATA",
            {"narrative_only": narrative, "mechanism_in_primary_docs": mechanism},
        )
    status = "SIGNAL" if narrative is True and mechanism is False else "NO_SIGNAL"
    return _row(
        "NARRATIVE_WITHOUT_MECHANISM",
        status,
        {"narrative_only": narrative, "mechanism_in_primary_docs": mechanism},
    )


def _coverage(latest: dict) -> dict:
    status = latest.get("reconstruction_status")
    if status in (None, "", "UNKNOWN"):
        return _row("COVERAGE_INCOMPLETE", "INSUFFICIENT_DATA", {"reconstruction_status": status})
    incomplete = status != "COMPLETE_PUBLIC_ARCHIVE"
    return _row(
        "COVERAGE_INCOMPLETE",
        "SIGNAL" if incomplete else "NO_SIGNAL",
        {"reconstruction_status": status},
    )
