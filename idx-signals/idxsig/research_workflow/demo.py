"""Small, deterministic synthetic demonstration; never a market strategy trial."""

from datetime import datetime, timedelta, timezone

from ..runtime.storage import digest
from .spec import (
    DATASET_VERSION,
    EVALUATOR_VERSION,
    FEATURE_VERSION,
    PROPOSAL_VERSION,
    PROTOCOL_VERSION,
)
from .worker import run_batch


def fixture():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    times = [(start + timedelta(hours=i)).isoformat().replace("+00:00", "Z") for i in range(120)]
    observations = [
        {
            "observed_at": at,
            "event_at": at,
            "symbol": "SYNTHETIC",
            "close": str(100 + i / 10 + ((i % 9) - 4) / 5),
        }
        for i, at in enumerate(times)
    ]
    dataset = {
        "schema_version": DATASET_VERSION,
        "id": "synthetic-development-v1",
        "kind": "synthetic",
        "source_hashes": [],
        "observations": observations,
    }
    protocol = {
        "schema_version": PROTOCOL_VERSION,
        "id": "synthetic-workflow-v1",
        "dataset_sha256": digest(dataset),
        "feature_version": FEATURE_VERSION,
        "evaluator": EVALUATOR_VERSION,
        "folds": [
            {
                "id": "development-1",
                "train_start": times[0],
                "train_end": times[29],
                "validation_start": times[35],
                "validation_end": times[59],
                "evaluation_start": times[65],
                "evaluation_end": times[114],
            }
        ],
        "horizon_observations": 3,
        "costs": {
            "id": "synthetic-cost-v1",
            "fee_rate": "0.001",
            "spread_bps": "4",
            "slippage_bps": "2",
            "price_basis": "MID",
        },
        "comparator": {
            "id": "SMA_CROSS_SHADOW_V1",
            "version": "1",
            "parameters": {"fast": 4, "slow": 12},
        },
        "max_attempts": 2,
        "max_rows": 200,
        "warmup_lengths": [40, 80],
        "seed": 0,
        "as_of": times[-1],
        "reserved_holdout_start": (start + timedelta(hours=120)).isoformat().replace("+00:00", "Z"),
    }
    proposal = {
        "schema_version": PROPOSAL_VERSION,
        "id": "synthetic-return-proposal",
        "hypothesis": "Demonstrate a fixed return-threshold comparison on invented prices.",
        "author": "human",
        "strategy": {
            "id": "RETURN_THRESHOLD_SHADOW_V1",
            "version": "1",
            "parameters": {"lookback": 3, "threshold": 0.002},
        },
    }
    return protocol, dataset, [proposal]


def demo(root):
    protocol, dataset, proposals = fixture()
    return run_batch(root, protocol, dataset, proposals)
