"""Per-intent timing sidecar; original paper economics and labels stay intact.

Actual processing observations are upper bounds, not exchange timestamps or real
fills. Replayed economic timestamps are retained as links only. Newness comes
from the coordinator's before/after account comparison, never a timestamp guess.
"""

from __future__ import annotations

import copy
import json

from ..timing_capture import append_attempt, make_attempt, read_attempts, validate_attempt
from .data import parse_time, utc_text
from .storage import canonical, digest, locked

DETECTOR = "PAPER_INTENT_TIMING_V1"


def _ids(trace, key):
    encoded = trace.get("links", {}).get(key)
    values = json.loads(encoded) if encoded is not None else []
    if (not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values)
            or len(values) != len(set(values))):
        raise ValueError("invalid new paper identity list: " + key)
    return set(values)


def _identity(profile, profile_hash, order):
    for key in ("id", "symbol", "side", "made_at", "expires_at", "status"):
        if not isinstance(order.get(key), str) or not order[key]:
            raise ValueError("paper intent requires " + key)
    if order["side"] not in {"BUY", "SELL"}:
        raise ValueError("unsupported paper side")
    if parse_time(order["expires_at"]) <= parse_time(order["made_at"]):
        raise ValueError("paper intent expiry must follow creation")
    return "paper_intent_" + digest({"profile": profile, "profile_sha256": profile_hash,
                                     "intent_id": order["id"]})


def _filled(row, item, *, is_new, process_quote_at, processed_at, run_id):
    links = row["links"]
    fill_links = {
        "fill_id": item["id"], "logical_fill_recorded_at": item["fill_recorded_at"],
        "original_quote_observed_at": item["observed_at"],
        "original_quote_received_at": item["received_at"],
        "fill_observation_id": item["observation_id"],
        "fill_source_evidence_id": item.get("source_evidence_id"),
        "fill_record_sha256": digest(item),
    }
    for key, value in fill_links.items():
        if key in links and links[key] != value:
            raise ValueError("paper fill identity changed: " + key)
    if "fill_id" in links:
        return
    links.update(fill_links, fill_first_observed_run_id=run_id, paper_observed_fill_status="FILLED")
    if is_new:
        row["status"] = "FILLED"
        row["fill_at"] = processed_at
        links["fill_clock_basis"] = "ACTUAL_PROCESSING_COMPLETION_UPPER_BOUND_SIMULATED_ONLY"
        if process_quote_at is not None:
            quote_at = utc_text(parse_time(process_quote_at))
            if row["decision_at"] is None or parse_time(quote_at) > parse_time(row["decision_at"]):
                row["executable_at"] = quote_at
                links["executable_clock_basis"] = "ACTUAL_INPUT_PROCESSING_OBSERVATION_NOT_EXCHANGE_TIME"
            else:
                links["executable_clock_basis"] = "UNKNOWN_PROCESSING_QUOTE_NOT_AFTER_ACTUAL_DECISION"
    else:
        links["fill_clock_basis"] = "UNKNOWN_ORIGINAL_PROCESSING_TIME_RETAINED_ECONOMIC_LABEL_ONLY"


def observe_paper_timing(root, *, payload, trace_record, process_quote_at, processed_at):
    """Append linked observations for new paper decisions/fills; retry is inert.

    ``trace_record.links.paper_new_intents_json`` and ``paper_new_fills_json`` are
    JSON-encoded ID lists captured by the coordinator before/after mutation.
    Missing lists mean no new event is proven. Old snapshots cannot erase a
    previously observed fill. Every mutation remains inside the timing sidecar.
    """
    processed_at = utc_text(parse_time(processed_at))
    account, run = payload["account"], payload["run"]
    if account.get("simulation_only") is not True:
        raise ValueError("paper timing accepts simulation accounts only")
    profile, profile_hash = account["profile"], run["profile_sha256"]
    if not isinstance(profile, str) or not profile or not isinstance(profile_hash, str):
        raise ValueError("paper profile identity required")
    new_intents = _ids(trace_record, "paper_new_intents_json")
    new_fills = _ids(trace_record, "paper_new_fills_json")
    orders, fills = account.get("orders", []), account.get("fills", [])
    if not isinstance(orders, list) or not isinstance(fills, list):
        raise ValueError("paper orders and fills must be lists")
    by_order = {}
    for order in orders:
        identity = _identity(profile, profile_hash, order)
        if order["id"] in by_order:
            raise ValueError("duplicate paper intent")
        by_order[order["id"]] = (identity, order)
    by_fill, fill_ids = {}, set()
    for item in fills:
        if (not isinstance(item, dict) or item.get("simulation_only") is not True
                or item.get("intent_id") not in by_order):
            raise ValueError("paper fill lacks a retained simulated intent")
        if item["id"] in fill_ids or item["intent_id"] in by_fill:
            raise ValueError("duplicate paper fill identity")
        order = by_order[item["intent_id"]][1]
        if item["symbol"] != order["symbol"] or item["side"] != order["side"]:
            raise ValueError("paper fill differs from intent identity")
        by_fill[item["intent_id"]] = item
        fill_ids.add(item["id"])
    if not new_intents <= by_order.keys() or not new_fills <= fill_ids:
        raise ValueError("new paper identities absent from supplied account")
    prepared, retained = [], []
    with locked(root):
        prior = {row["id"]: row for row in read_attempts(root) if row["detector_version"] == DETECTOR}
        for intent_id, (identity, order) in by_order.items():
            previous = prior.get(identity)
            common = {"profile_id": profile, "profile_sha256": profile_hash,
                      "intent_id": intent_id, "intent_symbol": order["symbol"],
                      "intent_side": order["side"], "logical_intent_made_at": order["made_at"],
                      "logical_intent_expires_at": order["expires_at"]}
            if previous:
                if any(previous["links"].get(key) != value for key, value in common.items()):
                    raise ValueError("paper intent identity changed")
                new_event = (intent_id in new_intents
                             or by_fill.get(intent_id, {}).get("id") in new_fills)
                if new_event and previous["evidence_kind"] != trace_record["evidence_kind"]:
                    raise ValueError("paper timing evidence kind cannot change")
                row = copy.deepcopy(previous)
            else:
                row = make_attempt(identity, detector_version=DETECTOR,
                    universe_snapshot_id=trace_record["universe_snapshot_id"], evidence_id=identity,
                    evidence_kind=trace_record["evidence_kind"], recorded_at=processed_at,
                    status="UNKNOWN", source="KOD_PAPER_ACCOUNT",
                    links={**common, "parent_attempt_id": trace_record["id"],
                           "first_observed_run_id": run["id"],
                           "first_processing_attempt_id": trace_record["id"]},
                    reason="Processing observations for simulated paper events; economic labels preserved separately.")
            # A later fill can reach this observer first. An independently
            # measured original decision may then fill an UNKNOWN clock without
            # relabelling a terminal fill or borrowing a later cycle's decision.
            # Liquidations have no strategy-decision clock here.
            if (row["decision_at"] is None and intent_id in new_intents
                    and intent_id.startswith("decision:") and order["made_at"] == run["as_of"]
                    and trace_record.get("decision_at")):
                row["decision_at"] = utc_text(parse_time(trace_record["decision_at"]))
                if row["status"] == "UNKNOWN":
                    row["status"] = "DECIDED"
                row["links"].update(decision_clock_basis="ACTUAL_DECISION_PROCESSING_COMPLETION_UPPER_BOUND",
                                    decision_processing_attempt_id=trace_record["id"])
            item = by_fill.get(intent_id)
            if item:
                _filled(row, item, is_new=item["id"] in new_fills,
                        process_quote_at=process_quote_at, processed_at=processed_at, run_id=run["id"])
            elif ("fill_id" not in row["links"] and "paper_terminal_status" not in row["links"]
                    and order["status"] not in {"PENDING", "IOC_COMPLETE"}):
                # Expiry/cancellation times are not inferred from an old label.
                row["status"] = "EXPIRED" if order["status"] == "EXPIRED" else "REJECTED"
                row["links"].setdefault("paper_terminal_status", order["status"])
            if previous and canonical(row) == canonical(previous):
                retained.append(identity)
                continue
            row["recorded_at"] = processed_at
            prepared.append(validate_attempt(row))
        # Validate each projection before writing. The core journal additionally
        # enforces prior-stage preservation on every append.
        for row in prepared:
            append_attempt(root, row, _locked=True)
            retained.append(row["id"])
    return {"intent_attempt_ids": retained, "new_observations": len(prepared), "entry_permission": False}
