"""Strict specifications for bounded, development-only quantitative experiments."""

from __future__ import annotations

import copy
import re
from decimal import Decimal, InvalidOperation

from ..runtime.data import parse_time
from ..runtime.storage import canonical, digest

PROTOCOL_VERSION = "KOD_RESEARCH_PROTOCOL_V1"
DATASET_VERSION = "KOD_RESEARCH_DATASET_V1"
PROPOSAL_VERSION = "KOD_RESEARCH_PROPOSAL_V1"
EVALUATOR_VERSION = "NEXT_OBSERVATION_FIXED_HORIZON_V1"
FEATURE_VERSION = "CLOSE_AVAILABILITY_V1"


def fields(value, required, optional=(), *, name):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional):
        raise ValueError(f"{name}: object with supported fields required")
    missing = set(required) - set(value)
    if missing:
        raise ValueError(f"{name}: missing fields {', '.join(sorted(missing))}")


def identifier(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", value):
        raise ValueError(f"{name}: simple nonempty identifier required")
    return value


def integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{name}: integer in {low}..{high} required")
    return value


def hash_text(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{name}: SHA-256 required")


def strategy_spec(value):
    fields(value, ("id", "version", "parameters"), name="strategy")
    identifier(value["id"], "strategy.id")
    if value["version"] != "1" or not isinstance(value["parameters"], dict):
        raise ValueError("strategy version 1 and parameter object required")
    canonical(value)
    return copy.deepcopy(value)


def validate_protocol(protocol):
    fields(
        protocol,
        (
            "schema_version",
            "id",
            "dataset_sha256",
            "feature_version",
            "evaluator",
            "folds",
            "horizon_observations",
            "costs",
            "comparator",
            "max_attempts",
            "max_rows",
            "warmup_lengths",
            "seed",
            "as_of",
            "reserved_holdout_start",
        ),
        name="protocol",
    )
    if protocol["schema_version"] != PROTOCOL_VERSION:
        raise ValueError("unsupported research protocol")
    identifier(protocol["id"], "protocol.id")
    hash_text(protocol["dataset_sha256"], "dataset_sha256")
    if protocol["feature_version"] != FEATURE_VERSION or protocol["evaluator"] != EVALUATOR_VERSION:
        raise ValueError("unsupported feature or evaluator version")
    integer(protocol["horizon_observations"], "horizon_observations", 1, 1000)
    integer(protocol["max_attempts"], "max_attempts", 1, 100)
    integer(protocol["max_rows"], "max_rows", 2, 2000)
    lengths = protocol["warmup_lengths"]
    if not isinstance(lengths, list) or not 1 <= len(lengths) <= 10:
        raise ValueError("one to ten warm-up history sizes required")
    for length in lengths:
        integer(length, "warmup length", 1, protocol["max_rows"])
    if len(set(lengths)) != len(lengths):
        raise ValueError("duplicate warmup length")
    integer(protocol["seed"], "seed", 0, 2**32 - 1)
    cutoff = parse_time(protocol["as_of"])
    holdout = parse_time(protocol["reserved_holdout_start"])
    if cutoff >= holdout:
        raise ValueError("as_of must precede the reserved holdout")
    from ..components.strategy import specification

    specification(strategy_spec(protocol["comparator"]))
    from ..components.costs import CostModel

    cost = CostModel.from_dict(protocol["costs"])
    if cost.price_basis != "MID":
        raise ValueError("close-price proxy evaluation requires declared MID costs")
    folds = protocol["folds"]
    if not isinstance(folds, list) or not 1 <= len(folds) <= 20:
        raise ValueError("one to twenty chronological folds required")
    ids, last_evaluation_end = set(), None
    names = (
        "train_start",
        "train_end",
        "validation_start",
        "validation_end",
        "evaluation_start",
        "evaluation_end",
    )
    for fold in folds:
        fields(fold, ("id", *names), name="fold")
        identifier(fold["id"], "fold.id")
        if fold["id"] in ids:
            raise ValueError("duplicate fold id")
        ids.add(fold["id"])
        ts = [parse_time(fold[name]) for name in names]
        if not (ts[0] <= ts[1] < ts[2] <= ts[3] < ts[4] <= ts[5] <= cutoff):
            raise ValueError("fold train/validation/evaluation ranges overlap or exceed cutoff")
        if last_evaluation_end is not None and ts[4] <= last_evaluation_end:
            raise ValueError("evaluation folds must be ordered and disjoint")
        last_evaluation_end = ts[5]
    canonical(protocol)
    return copy.deepcopy(protocol)


def validate_dataset(dataset, protocol):
    fields(
        dataset, ("schema_version", "id", "kind", "source_hashes", "observations"), name="dataset"
    )
    if dataset["schema_version"] != DATASET_VERSION or dataset["kind"] not in {
        "synthetic",
        "recorded",
    }:
        raise ValueError("unsupported dataset schema or evidence kind")
    identifier(dataset["id"], "dataset.id")
    if not isinstance(dataset["source_hashes"], list):
        raise ValueError("source_hashes must be a list of declared source hashes")
    for source_hash in dataset["source_hashes"]:
        hash_text(source_hash, "source hash")
    if dataset["kind"] == "recorded" and not dataset["source_hashes"]:
        raise ValueError("recorded datasets require declared source hashes")
    rows = dataset["observations"]
    if not isinstance(rows, list) or not 2 <= len(rows) <= protocol["max_rows"]:
        raise ValueError("dataset size outside the frozen row budget")
    if any(length >= len(rows) for length in protocol["warmup_lengths"]):
        raise ValueError("warmup windows must be shorter than the dataset")
    previous, symbol = None, None
    cutoff = parse_time(protocol["as_of"])
    holdout = parse_time(protocol["reserved_holdout_start"])
    for row in rows:
        fields(row, ("observed_at", "close", "symbol"), ("event_at",), name="observation")
        timestamp = parse_time(row["observed_at"])
        if (
            timestamp > cutoff
            or timestamp >= holdout
            or previous is not None
            and timestamp <= previous
        ):
            raise ValueError(
                "observations must be ordered, available by cutoff, and outside holdout"
            )
        if "event_at" in row and parse_time(row["event_at"]) > timestamp:
            raise ValueError("source clock follows observation availability")
        if isinstance(row["close"], bool):
            raise ValueError("positive finite close required")
        try:
            close = Decimal(str(row["close"]))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError("positive finite close required") from exc
        if not close.is_finite() or close <= 0:
            raise ValueError("positive finite close required")
        identifier(row["symbol"], "symbol")
        if symbol is not None and symbol != row["symbol"]:
            raise ValueError("one instrument per research dataset required")
        symbol, previous = row["symbol"], timestamp
    if digest(dataset) != protocol["dataset_sha256"]:
        raise ValueError("dataset differs from the frozen content hash")
    # Purge labels around the split boundaries, even though these templates do not fit a model.
    times = [parse_time(row["observed_at"]) for row in rows]
    horizon = protocol["horizon_observations"] + 1
    for fold in protocol["folds"]:
        for start_name, end_name, following in (
            ("train_start", "train_end", "validation_start"),
            ("validation_start", "validation_end", "evaluation_start"),
        ):
            indices = [
                i
                for i, t in enumerate(times)
                if parse_time(fold[start_name]) <= t <= parse_time(fold[end_name])
            ]
            if not indices:
                raise ValueError("fold has an empty training or validation interval")
            maturity = indices[-1] + horizon
            if maturity >= len(times) or times[maturity] >= parse_time(fold[following]):
                raise ValueError("fold boundary lacks the frozen label-maturity embargo")
        if not any(
            parse_time(fold["evaluation_start"]) <= t <= parse_time(fold["evaluation_end"])
            for t in times
        ):
            raise ValueError("fold has no evaluation observations")
    return copy.deepcopy(dataset)


def validate_proposal(proposal):
    fields(proposal, ("schema_version", "id", "hypothesis", "author", "strategy"), name="proposal")
    if proposal["schema_version"] != PROPOSAL_VERSION:
        raise ValueError("unsupported proposal schema")
    identifier(proposal["id"], "proposal.id")
    if (
        not isinstance(proposal["hypothesis"], str)
        or not 1 <= len(proposal["hypothesis"].strip()) <= 2000
    ):
        raise ValueError("a concise hypothesis is required")
    if proposal["author"] not in {"human", "ai"}:
        raise ValueError("proposal author must be human or ai")
    strategy_spec(proposal["strategy"])
    return copy.deepcopy(proposal)


def hypothesis_hash(proposal):
    """Renaming a valid, equivalent strategy does not buy another trial."""
    from ..components.strategy import specification

    try:
        validated = validate_proposal(proposal)
        strategy = specification(validated["strategy"])
    except (ValueError, TypeError, KeyError):
        return digest({"invalid_proposal": proposal})
    return digest({"strategy": strategy})
