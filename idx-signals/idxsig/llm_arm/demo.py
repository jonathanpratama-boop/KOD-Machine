"""Invented one-candidate lifecycle; deliberately retains a loss and a retry."""

from .contracts import STATEMENTS, VERSION
from .workbench import initialize, prepare, record_response, resolve, status, watch


def fixture():
    source = {
        "type": "SPECULATION_SET",
        "set_id": "SYNTHETIC-LLM-1",
        "record_hash": "synthetic-set",
        "market": "SYNTHETIC",
        "ticker": "EXAMPLE",
        "signal_session": "2030-01-01",
        "protocol": {"id": "SYNTHETIC-NOT-A-STUDY", "sha256": "synthetic"},
        "sealed_at": "2030-01-01T00:00:00Z",
        "entry_cutoff": "2030-01-01T01:00:00Z",
        "plan": "BASE5",
        "windows": ["BASE5"],
        "cone": [{"id": s, "prior": 0.5, "resolves_with": "BASE5"} for s in STATEMENTS],
    }
    spec = {
        "schema_version": VERSION,
        "cohort": "SYNTHETIC-DEVELOPMENT-DEMO",
        "model": {"provider": "synthetic", "id": "fixture-no-model-called"},
        "latency_budget_seconds": 60,
        "candidates": [
            {"set": source, "resolution_due_at": "2030-01-08T00:00:00Z", "learner": None}
        ],
    }
    context = {
        "as_of": "2030-01-01T00:00:01Z",
        "observations": "Invented test candidate.",
        "sources": [
            {
                "id": "fixture",
                "url": "https://example.invalid/invented",
                "retrieved_at": "2030-01-01T00:00:01Z",
                "content": "Invented evidence.",
            }
        ],
    }
    outcome = {
        "type": "RESOLUTION",
        "set_id": source["set_id"],
        "window": "BASE5",
        "status": "RESOLVED",
        "resolved_at": "2030-01-07T00:00:00Z",
        **{k: source[k] for k in ("market", "ticker", "signal_session", "protocol")},
        "cone": [{"id": s, "outcome": s == "FADE10_5"} for s in STATEMENTS],
        "candidate": {"trade": {"net_return": -0.12}},
    }
    return spec, context, outcome


def response_for(packet):
    return {
        "packet_sha256": packet["packet_sha256"],
        "model": packet["model"],
        "call": "ABSTAIN",
        "p": {s: 0.5 for s in STATEMENTS},
        "facts": [{"claim": "This is an invented example.", "source_ids": ["fixture"]}],
        "inferences": ["No real market conclusion follows."],
        "counterargument": "The fixture cannot demonstrate a trading edge.",
        "uncertainties": ["No real model inference or market fill."],
        "timing_assessment": "Simulated wall clock only.",
        "proposal": None,
    }


def demo(root):
    spec, context, outcome = fixture()
    identifier = spec["candidates"][0]["set"]["set_id"]
    initialize(root, spec, clock=lambda: "2030-01-01T00:00:01Z")
    packet = prepare(root, identifier, context, clock=lambda: "2030-01-01T00:00:02Z")
    before = status(root, clock=lambda: "2030-01-01T00:00:03Z")
    if before["cases"][0]["attempts"] == 0:
        record_response(
            root, identifier, response_for(packet), clock=lambda: "2030-01-01T00:00:03Z"
        )
        record_response(
            root, identifier, response_for(packet), clock=lambda: "2030-01-01T00:00:04Z"
        )
    resolve(root, [spec["candidates"][0]["set"], outcome], clock=lambda: "2030-01-07T00:00:01Z")
    watch(root, clock=lambda: "2030-01-07T00:00:02Z")
    return status(root, clock=lambda: "2030-01-07T00:00:03Z")
