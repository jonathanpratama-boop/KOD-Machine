"""Read-only readiness audit of frozen LLM_ARM v1 calls; never a performance look.

This module inspects supplied records, not their historical authenticity. It does
not verify RFC 3161 tokens, register hash chains, source contents or a learner
ledger. Missing evidence remains visible and cannot grant promotion permission.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from ..runtime.data import parse_time

STATEMENTS = ("RUN30_5", "FADE10_5", "BEATS_TWINS_5")
FIRST_LOOK = 60


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def load_jsonl(path) -> list:
    """Read every row strictly; malformed bytes never silently disappear."""
    path = Path(path)
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError(f"{path.name}: incomplete JSONL tail")
    rows = []
    for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{path.name}:{number}: blank JSONL row")
        try:
            row = json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
            if not isinstance(row, dict):
                raise ValueError("JSONL record must be an object")
            rows.append(row)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{path.name}:{number}: {exc}") from exc
    return rows


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _probability(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 1
        and math.isfinite(value)
    )


def _time(value):
    try:
        return parse_time(value) if isinstance(value, str) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def _cone(value):
    """Ambiguous statement IDs invalidate the whole cone, not just the last row."""
    if not isinstance(value, list):
        return None
    rows = {}
    for row in value:
        if not isinstance(row, dict) or not _text(row.get("id")) or row["id"] in rows:
            return None
        rows[row["id"]] = row
    return rows


def _call_errors(row):
    if not isinstance(row, dict):
        return ["call is not an object"]
    errors = []
    for field in ("call_id", "set", "ticker", "market", "signal_session"):
        if not _text(row.get(field)):
            errors.append(f"missing or invalid {field}")
    if row.get("call") not in ("BACK", "AVOID", "ABSTAIN"):
        errors.append("invalid call action")
    if _time(row.get("called_at")) is None:
        errors.append("invalid called_at")
    probabilities = row.get("p")
    if not isinstance(probabilities, dict) or any(
        not _probability(probabilities.get(name)) for name in STATEMENTS
    ):
        errors.append("missing or invalid statement probabilities")
    for field in ("reasons", "sources"):
        values = row.get(field)
        if not isinstance(values, list) or any(not _text(value) for value in values):
            errors.append(f"invalid {field}")
    if not isinstance(row.get("agrees_with_kod"), bool):
        errors.append("missing or invalid agrees_with_kod")
    return errors


def _set_errors(row, candidate):
    errors = []
    if any(row.get(key) != candidate.get(key) for key in ("ticker", "market", "signal_session")):
        errors.append("call and set identity differ")
    sealed, cutoff, called = (
        _time(candidate.get("sealed_at")),
        _time(candidate.get("entry_cutoff")),
        _time(row.get("called_at")),
    )
    if sealed is None or cutoff is None or called is None or not sealed <= called < cutoff:
        errors.append("declared call time is outside sealed set entry window")
    cone = _cone(candidate.get("cone"))
    if cone is None or any(
        name not in cone or cone[name].get("resolves_with") != "BASE5" for name in STATEMENTS
    ):
        errors.append("set lacks unambiguous BASE5 statements")
    return errors


def _resolution_ready(row, candidate, resolution):
    if resolution.get("status") != "RESOLVED":
        return False
    if any(
        resolution.get(key) != candidate.get(key) for key in ("ticker", "market", "signal_session")
    ):
        return False
    # A declared protocol mismatch is a blocking conflict; neither protocol is invented.
    if (
        not isinstance(candidate.get("protocol"), dict)
        or resolution.get("protocol") != candidate["protocol"]
    ):
        return False
    resolved, called, cutoff = (
        _time(resolution.get("resolved_at")),
        _time(row.get("called_at")),
        _time(candidate.get("entry_cutoff")),
    )
    if resolved is None or called is None or cutoff is None or resolved < max(called, cutoff):
        return False
    cone, original = _cone(resolution.get("cone")), _cone(candidate.get("cone"))
    return (
        cone is not None
        and original is not None
        and all(
            name in cone
            and isinstance(cone[name].get("outcome"), bool)
            and _probability(cone[name].get("prior"))
            and cone[name]["prior"] == original[name].get("prior")
            for name in STATEMENTS
        )
    )


def audit(calls: list, register: list) -> dict:
    """Count v1 coverage/readiness without exposing outcomes or scoring performance.

    Inputs may contain malformed rows: these remain counted and are reported.
    Duplicate call IDs or duplicate calls for one set are all excluded from the
    readiness count, preventing arbitrary first/last-response selection.
    """
    if not isinstance(calls, list) or not isinstance(register, list):
        raise ValueError("calls and register must be lists")
    sets, resolutions = defaultdict(list), defaultdict(list)
    malformed_register = 0
    for row in register:
        if not isinstance(row, dict) or not _text(row.get("set_id")):
            malformed_register += 1
            continue
        if row.get("type") == "SPECULATION_SET":
            sets[row["set_id"]].append(row)
        elif row.get("type") == "RESOLUTION":
            if row.get("window") == "BASE5":
                resolutions[row["set_id"]].append(row)
        else:
            malformed_register += 1
    ids = Counter(
        row["call_id"] for row in calls if isinstance(row, dict) and _text(row.get("call_id"))
    )
    call_sets = Counter(
        row["set"] for row in calls if isinstance(row, dict) and _text(row.get("set"))
    )
    counts = Counter(
        {
            name: 0
            for name in (
                "BACK",
                "AVOID",
                "ABSTAIN",
                "malformed_calls",
                "duplicate_call_rows",
                "duplicate_set_call_rows",
                "without_source_urls",
                "missing_numeric_context",
                "numeric_forecast_declared_unsealed",
                "call_prior_absent",
                "agrees_with_kod",
                "disagrees_with_kod",
                "valid_unique_linked_calls",
                "missing_register_priors",
                "complete_BASE5_outcomes",
                "pending_or_unusable_BASE5",
                "unlinked_calls",
            )
        }
    )
    details = []
    for number, row in enumerate(calls, 1):
        errors = _call_errors(row)
        if errors:
            counts["malformed_calls"] += 1
        if not isinstance(row, dict):
            counts["without_source_urls"] += 1
            counts["missing_numeric_context"] += 1
            counts["call_prior_absent"] += 1
            details.append({"row": number, "issues": errors})
            continue
        action = row.get("call")
        if isinstance(action, str) and action in ("BACK", "AVOID", "ABSTAIN"):
            counts[action] += 1
        sources = row.get("sources")
        if not isinstance(sources, list) or not any(_url(value) for value in sources):
            counts["without_source_urls"] += 1
        numeric = row.get("kod_numeric")
        if not _text(numeric):
            counts["missing_numeric_context"] += 1
        elif "not sealed" in numeric.lower() or "unsealed" in numeric.lower():
            counts["numeric_forecast_declared_unsealed"] += 1
        if not isinstance(row.get("prior"), dict):
            counts["call_prior_absent"] += 1
        if row.get("agrees_with_kod") is True:
            counts["agrees_with_kod"] += 1
        elif row.get("agrees_with_kod") is False:
            counts["disagrees_with_kod"] += 1
        cid, sid = row.get("call_id"), row.get("set")
        if _text(cid) and ids[cid] > 1:
            counts["duplicate_call_rows"] += 1
            errors.append("duplicate call_id")
        if _text(sid) and call_sets[sid] > 1:
            counts["duplicate_set_call_rows"] += 1
            errors.append("multiple calls for one set")
        candidates = sets.get(sid, []) if isinstance(sid, str) else []
        if len(candidates) != 1:
            counts["unlinked_calls"] += 1
            errors.append("missing or ambiguous speculation set")
        else:
            candidate = candidates[0]
            errors.extend(_set_errors(row, candidate))
            cone = _cone(candidate.get("cone"))
            if cone is None or any(
                name not in cone or not _probability(cone[name].get("prior")) for name in STATEMENTS
            ):
                counts["missing_register_priors"] += 1
                errors.append("missing sealed register prior")
        if not errors:
            counts["valid_unique_linked_calls"] += 1
            outcomes = resolutions.get(sid, [])
            ready = len(outcomes) == 1 and _resolution_ready(row, candidate, outcomes[0])
            counts["complete_BASE5_outcomes" if ready else "pending_or_unusable_BASE5"] += 1
        details.append(
            {"row": number, "call_id": cid if isinstance(cid, str) else None, "issues": errors}
        )
    complete = counts["complete_BASE5_outcomes"]
    return {
        "schema_version": "KOD_LLM_ARM_V1_READINESS_AUDIT_V1",
        "counts": {
            "all_call_rows": len(calls),
            "all_register_rows": len(register),
            "malformed_register_rows": malformed_register,
            **counts,
        },
        "first_look": {
            "required_scored_calls": FIRST_LOOK,
            "structurally_complete_calls": complete,
            "remaining": max(0, FIRST_LOOK - complete),
            "status": "BELOW_FIRST_LOOK"
            if complete < FIRST_LOOK
            else "REQUIRES_INDEPENDENT_EVALUATOR",
        },
        "learner_comparison": {
            "status": "NOT_VERIFIED",
            "verified_calls": 0,
            "calls_without_verified_comparator": len(calls),
            "reason": "This audit receives no sealed learner ledger; numeric prose is not comparator evidence.",
        },
        "back_and_avoid_labels_present": counts["BACK"] > 0 and counts["AVOID"] > 0,
        "performance_evaluated": False,
        "profitability_validated": False,
        "entry_permission": False,
        "promotion_permission": False,
        "timestamp_verification": "NOT_PERFORMED",
        "integrity_scope": "Supplied local record structure only; no hash-chain, source-content or independent timestamp verification.",
        "limitations": [
            "The supplied calls are not an independently frozen candidate roster; omitted calls cannot be detected here.",
            "Complete BASE5 records are readiness evidence, not verified scored calls or a performance claim.",
            "Empty source lists are a quality gap, not a retroactive v1 exclusion rule.",
            "No Brier scores, returns, wins or losses are exposed by this readiness audit.",
        ],
        "calls": details,
    }
