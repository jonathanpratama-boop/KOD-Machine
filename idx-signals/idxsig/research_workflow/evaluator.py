"""Fixed, causal close-price proxy evaluator; never reports portfolio performance."""

from __future__ import annotations

from statistics import mean

from ..components.costs import CostModel
from ..components.strategy import evaluate_series
from ..runtime.data import parse_time
from ..strategy_checks import run_strategy_checks
from .spec import EVALUATOR_VERSION


class EvaluationBlocked(ValueError):
    def __init__(self, checks):
        super().__init__("candidate or comparator did not pass the declared strategy checks")
        self.checks = checks


def _metrics(rows):
    known = [row["net_return_proxy"] for row in rows if row["net_return_proxy"] is not None]
    triggered = [row for row in rows if row["signal"] == 1]
    observed = [row["net_return_proxy"] for row in triggered if row["status"] == "OBSERVED_PROXY"]
    return {
        "opportunities": len(rows),
        "triggered": len(triggered),
        "warmup": sum(row["status"] == "WARMUP" for row in rows),
        "censored": sum(row["status"] == "CENSORED" for row in rows),
        "known_opportunities": len(known),
        "observed_triggered": len(observed),
        "mean_net_return_per_trigger_proxy": mean(observed) if observed else None,
        "mean_unit_notional_return_per_opportunity_proxy": mean(known) if known else None,
    }


def _arm(rows, decisions, selected, fold_end, horizon, costs):
    result = []
    for index in selected:
        decision, observation = decisions[index], rows[index]
        item = {
            "index": index,
            "observed_at": observation["observed_at"],
            "signal": decision["signal"],
            "status": "NO_TRIGGER",
            "entry_at": None,
            "exit_at": None,
            "net_return_proxy": 0.0,
        }
        if decision["status"] == "WARMUP":
            item.update(status="WARMUP", net_return_proxy=None)
        elif decision["signal"] == 1:
            entry, exit_ = index + 1, index + 1 + horizon
            if exit_ >= len(rows) or parse_time(rows[exit_]["observed_at"]) > fold_end:
                item.update(status="CENSORED", net_return_proxy=None)
            else:
                value = costs.round_trip_return(rows[entry]["close"], rows[exit_]["close"])
                item.update(
                    status="OBSERVED_PROXY",
                    entry_at=rows[entry]["observed_at"],
                    exit_at=rows[exit_]["observed_at"],
                    net_return_proxy=float(value),
                )
        result.append(item)
    return result


def evaluate(protocol, dataset, proposal):
    """Score frozen signals with later observations and an aligned fixed comparator.

    The strategy sees only normalized observations, never outcome columns. Full-series
    output is checked against every causal prefix and declared warm-up windows. No fitting or
    optimization happens here; train/validation intervals establish declared chronology.
    """
    rows = dataset["observations"]
    strategy, comparator = proposal["strategy"], protocol["comparator"]
    checks = {
        name: run_strategy_checks(
            lambda observations, template=template: evaluate_series(template, observations),
            rows,
            warmup_lengths=protocol["warmup_lengths"],
        )
        for name, template in (("candidate", strategy), ("comparator", comparator))
    }
    if any(result["status"] != "PASS" for result in checks.values()):
        raise EvaluationBlocked(checks)
    decisions = evaluate_series(strategy, rows)
    benchmark = evaluate_series(comparator, rows)
    costs = CostModel.from_dict(protocol["costs"])
    horizon = protocol["horizon_observations"]
    folds = []
    for fold in protocol["folds"]:
        start, end = parse_time(fold["evaluation_start"]), parse_time(fold["evaluation_end"])
        selected = [
            i for i, row in enumerate(rows) if start <= parse_time(row["observed_at"]) <= end
        ]
        candidate_rows = _arm(rows, decisions, selected, end, horizon, costs)
        comparator_rows = _arm(rows, benchmark, selected, end, horizon, costs)
        paired = [
            a["net_return_proxy"] - b["net_return_proxy"]
            for a, b in zip(candidate_rows, comparator_rows, strict=True)
            if a["net_return_proxy"] is not None and b["net_return_proxy"] is not None
        ]
        folds.append(
            {
                "id": fold["id"],
                "candidate": {"metrics": _metrics(candidate_rows), "observations": candidate_rows},
                "comparator": {
                    "metrics": _metrics(comparator_rows),
                    "observations": comparator_rows,
                },
                "cash_net_return": 0.0,
                "paired_known_opportunities": len(paired),
                "paired_unknown_opportunities": len(selected) - len(paired),
                "mean_paired_excess_return_proxy": mean(paired) if paired else None,
            }
        )
    return {
        "evaluator": EVALUATOR_VERSION,
        "evidence_kind": dataset["kind"],
        "purpose": "DEVELOPMENT_ONLY",
        "model_fitted": False,
        "strategy_checks": checks,
        "folds": folds,
        "live_eligible": False,
        "entry_permission": False,
        "profitability_validated": False,
        "limitations": [
            "Close prices are proxies, not observed executable quotes or fills.",
            "Source hashes are declarations; normalized prices are not reconciled to raw sources here.",
            "Overlapping opportunities are correlated and are not a portfolio equity curve.",
            "Fixed strategy templates do not fit or optimize a model on the training interval.",
            "Evaluation uses development data only; the reserved holdout is not read.",
        ],
    }
