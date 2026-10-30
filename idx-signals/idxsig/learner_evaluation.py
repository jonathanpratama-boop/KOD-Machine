"""Immutable planned evaluations, separate from continuously updated metrics.

This is an evaluation recipe, not a new trading or forecasting policy. The first
eligible *ledger prefix* is reconstructed deterministically; frozen_at records
when the decision was actually saved, independently of the eligibility cutoff.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import paper
from .provenance import exclusive_lock, utc_stamp

VERSION = "LEARNER-EVALUATION-v1"
TYPE = "LEARNER3_EVALUATION"
REVIEW = "LEARNER3_EVALUATION_REVIEW"
LEDGER = paper.PAPER / "learner_v3_evaluations.jsonl"


def digest(value):
    return hashlib.sha256(paper._canonical(value).encode()).hexdigest()


def _ordered(pairs, headline):
    return sorted((p for p in pairs if p["statement"] == headline),
                  key=lambda p: (p["resolved_at"], p["set_id"], p["statement"]))


def _namespace(record):
    return paper.resolution_key({**record, "set_id": ""})[:-2]


def _source_manifest(records):
    groups = {}
    for record in records:
        groups.setdefault(_namespace(record), []).append(record)
    return [{"namespace": list(ns), "count": len(rows), "sha256": digest(rows)} for ns, rows in groups.items()]


def _source_prefix(records, manifest):
    # New rows in the first register must not shift the recorded second prefix.
    out = []
    for entry in manifest:
        rows = [r for r in records if list(_namespace(r)) == entry["namespace"]][:entry["count"]]
        if len(rows) != entry["count"] or digest(rows) != entry["sha256"]:
            raise ValueError("evaluation source register prefix missing or changed")
        out.extend(rows)
    return out


def _eligible(records, forecasts, asof, proto, pair_fn, headline):
    """First row prefix satisfying count and sessions, in stable register order."""
    found = set()
    for i, record in enumerate(records):
        if record.get("type") != "RESOLUTION" or (record.get("resolved_at") or "9") >= asof:
            continue
        pairs = _ordered(pair_fn(records[:i + 1], forecasts, asof), headline)
        sessions = len({p["session"] for p in pairs})
        for k, threshold in enumerate(proto["claim"]["looks"]):
            if k in found or len(pairs) < threshold or sessions < proto["claim"]["min_sessions"][k]:
                continue
            found.add(k)
            yield k, i + 1, pairs
        if len(found) == len(proto["claim"]["looks"]):
            break


def _rule(proto, index):
    return {key: [proto["claim"][key][index]] for key in ("looks", "z_min", "min_sessions")}


def _result(pairs, proto, index, claim_fn, seed):
    result = claim_fn(pairs, _rule(proto, index), seed=seed)
    if index != len(proto["claim"]["looks"]) - 1:
        result["verdict"] = result["verdict"].replace(" (final)", "; continues")
    return result


def candidates(records, forecasts, asof, proto, proto_sha, pair_fn, claim_fn, headline):
    for k, count, pairs in _eligible(records, forecasts, asof, proto, pair_fn, headline):
        yield {"type": TYPE, "recipe": VERSION, "protocol": {"id": proto["protocol_id"], "sha256": proto_sha},
               "look": proto["claim"]["looks"][k], "look_index": k, "rule": _rule(proto, k), "seed": 20261029,
               "implementation": {"evaluation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                  "claim_sha256": hashlib.sha256(Path(claim_fn.__code__.co_filename).read_bytes()).hexdigest()},
               "source_prefix": {"count": count, "sha256": digest(records[:count]),
                                 "registers": _source_manifest(records[:count])},
               "forecasts": {"count": len(forecasts), "sha256": digest(forecasts)},
               "eligible_at": max(p["resolved_at"] for p in pairs),
               "pairs": pairs, "pairs_sha256": digest(pairs),
               "result": _result(pairs, proto, k, claim_fn, 20261029)}


def changes(event, current_pairs):
    current = {(p["set_id"], p["statement"]): p for p in current_pairs}
    out = []
    fields = ("y", "raw", "bench", "resolved_at", "resolution_record_hash", "forecast_record_hash")
    for old in event["pairs"]:
        new = current.get((old["set_id"], old["statement"]))
        if new is None or any(new.get(k) != old.get(k) for k in fields):
            out.append({"set_id": old["set_id"], "statement": old["statement"],
                        "original": {k: old.get(k) for k in fields},
                        "current": None if new is None else {k: new.get(k) for k in fields}})
    return out


def freeze(records, forecasts, asof, proto, proto_sha, pair_fn, claim_fn, headline, path=None):
    path = LEDGER if path is None else Path(path)
    # Distinct operation lock encloses the read/decide/append transaction. append
    # uses its own data-publication lock, so there is no recursive flock deadlock.
    with exclusive_lock(path.with_name(path.name + ".evaluation")):
        existing = paper.ledger_lines(path)
        problems = verify(path, claim_fn, proto=proto, proto_sha=proto_sha, records=records,
                          forecasts=forecasts, pair_fn=pair_fn, headline=headline)
        if problems:
            raise ValueError("invalid evaluation ledger: " + "; ".join(problems))
        current = pair_fn(records, forecasts, asof)  # validate the complete effective view before publishing
        done = {r["look"] for r in existing if r["type"] == TYPE and r["protocol"]["sha256"] == proto_sha}
        recorded_at = utc_stamp()
        pending = [{**r, "frozen_at": recorded_at, "cutoff": asof} for r in candidates(records, forecasts, asof, proto, proto_sha,
                    pair_fn, claim_fn, headline) if r["look"] not in done]
        written = paper.append(pending, path=path) if pending else []
        reviews = []
        seen = {(r.get("evaluation_hash"), r.get("changes_sha256")) for r in existing if r["type"] == REVIEW}
        for event in [*existing, *written]:
            if event["type"] != TYPE or event["protocol"]["sha256"] != proto_sha:
                continue
            changed = changes(event, current)
            key = (event["record_hash"], digest(changed))
            if changed and key not in seen:
                reviews.append({"type": REVIEW, "recipe": VERSION, "evaluation_hash": key[0],
                                "reviewed_at": recorded_at, "cutoff": asof, "changes": changed, "changes_sha256": key[1],
                                "status": "requires_review; original decision preserved"})
        if reviews:
            written += paper.append(reviews, path=path)
        return written


def official(current_pairs, proto_sha, asof, path=None, *, proto=None, claim_fn=None,
             records=None, forecasts=None, pair_fn=None, headline=None):
    path = LEDGER if path is None else Path(path)
    problems = verify(path, claim_fn, proto=proto, proto_sha=proto_sha, records=records,
                      forecasts=forecasts, pair_fn=pair_fn, headline=headline)
    if problems:
        raise ValueError("invalid evaluation ledger: " + "; ".join(problems))
    events = [r for r in paper.ledger_lines(path) if r.get("type") == TYPE
              and r["protocol"]["sha256"] == proto_sha and r["frozen_at"] <= asof]
    if not events:
        return {"n_pairs": 0, "n_sessions": 0, "auc": None, "auc_bench": None, "se": None,
                "z": None, "look": None, "verdict": "no planned evaluation frozen; descriptive metrics only"}
    last = max(events, key=lambda r: r["look_index"])
    changed = changes(last, current_pairs)
    result = {**last["result"], "evaluation_hash": last["record_hash"], "frozen_at": last["frozen_at"],
              "cohort_changes": changed, "original_verdict": last["result"]["verdict"]}
    if changed:
        result["verdict"] = "frozen evaluation requires correction review; original decision retained"
    return result


def verify(path=None, claim_fn=None, *, proto=None, proto_sha=None, records=None,
           forecasts=None, pair_fn=None, headline=None):
    path = LEDGER if path is None else Path(path)
    problems = list(paper.verify_chain(path))
    seen, known = set(), set()
    try:
        events = paper.ledger_lines(path)
    except (ValueError, UnicodeError):
        return problems
    for event in events:
        try:
            if event.get("type") == TYPE:
                key = (event["protocol"]["sha256"], event["look"])
                if key in seen:
                    problems.append("planned look recorded twice")
                seen.add(key)
                known.add(event["record_hash"])
                if event.get("recipe") != VERSION or digest(event["pairs"]) != event["pairs_sha256"]:
                    raise ValueError("evaluation recipe or pair hash invalid")
                if proto is None or claim_fn is None or proto_sha is None:
                    raise ValueError("pinned protocol and evaluator required to verify a planned decision")
                k = event["look_index"]
                if (type(k) is not int or not 0 <= k < len(proto["claim"]["looks"])
                        or event["protocol"] != {"id": proto["protocol_id"], "sha256": proto_sha}
                        or event["look"] != proto["claim"]["looks"][k]
                        or event["rule"] != _rule(proto, k) or event["seed"] != 20261029):
                    raise ValueError("evaluation rule differs from the pinned protocol")
                if _result(event["pairs"], proto, k, claim_fn, event["seed"]) != event["result"]:
                    raise ValueError("evaluation statistic or verdict does not reproduce")
                if records is not None and forecasts is not None and pair_fn is not None:
                    prefix = _source_prefix(records, event["source_prefix"]["registers"])
                    if (len(prefix) != event["source_prefix"]["count"]
                            or digest(prefix) != event["source_prefix"]["sha256"]):
                        raise ValueError("evaluation combined source prefix missing or changed")
                    fprefix = forecasts[:event["forecasts"]["count"]]
                    if digest(fprefix) != event["forecasts"]["sha256"]:
                        raise ValueError("evaluation forecast prefix missing or changed")
                    first = next(((count, pairs) for index, count, pairs in
                                  _eligible(prefix, fprefix, event["cutoff"], proto, pair_fn, headline)
                                  if index == k), None)
                    if first is None or first[0] != len(prefix) or digest(first[1]) != event["pairs_sha256"]:
                        raise ValueError("evaluation is not the first eligible source prefix")
            elif event.get("type") == REVIEW:
                if (event.get("evaluation_hash") not in known
                        or digest(event["changes"]) != event.get("changes_sha256")):
                    raise ValueError("invalid linked evaluation review")
            else:
                raise ValueError("unknown evaluation record type")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            problems.append(str(exc))
    return problems
