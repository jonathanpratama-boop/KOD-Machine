"""Paired exploratory evaluation of one frozen Kronos continuation filter.

Returns are fractions; every usable event has the same opportunity weight. This
is an event study, not a capital-constrained portfolio simulation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import statistics

COST = 0.02
SEED = 20261108


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def utc_date(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("decision_time must include its UTC offset")
    return parsed.astimezone(timezone.utc).date().isoformat()


def stats(values):
    return {
        "n": len(values),
        "mean_net_return": statistics.fmean(values) if values else None,
        "median_net_return": statistics.median(values) if values else None,
        "profitable_fraction": sum(v > 0 for v in values) / len(values) if values else None,
    }


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def paired_delta(rows):
    return statistics.fmean(row["combined"] - row["baseline"] for row in rows) if rows else None


def cluster_interval(rows, resamples=2000):
    clusters = defaultdict(lambda: [0.0, 0])
    for row in rows:
        cluster = clusters[row["date"]]
        cluster[0] += row["combined"] - row["baseline"]
        cluster[1] += 1
    groups = [clusters[key] for key in sorted(clusters)]
    if len(groups) < 2:
        return None
    rng = random.Random(SEED)
    draws = []
    for _ in range(resamples):
        chosen = [groups[rng.randrange(len(groups))] for _ in groups]
        draws.append(sum(group[0] for group in chosen) / sum(group[1] for group in chosen))
    return [quantile(draws, 0.025), quantile(draws, 0.975)]


def classify(enough, coverage_ok, interval, winner_removed_delta):
    if not enough or not coverage_ok:
        return "INSUFFICIENT_EVIDENCE"
    if (interval is not None and interval[0] > 0
            and winner_removed_delta is not None and winner_removed_delta > 0):
        return "PROMISING_EXPLORATORY_ONLY"
    return "NO_DEMONSTRATED_IMPROVEMENT"


def evaluate(records, resamples=2000):
    if resamples < 2:
        raise ValueError("resamples must be at least 2")
    rows, ids, missing, invalid_forecasts = [], set(), [], []
    forecast_errors, flat_errors, runtimes = [], [], []
    for record in records:
        identifier = str(record["event_id"])
        if identifier in ids:
            raise ValueError(f"duplicate event_id: {identifier}")
        ids.add(identifier)
        predicted = finite(record.get("predicted_return"))
        forecast_ok = record.get("status") == "ok" and predicted is not None
        if not forecast_ok:
            invalid_forecasts.append(identifier)
        runtime = finite(record.get("inference_seconds"))
        if runtime is not None and runtime >= 0:
            runtimes.append(runtime)
        gross = finite(record.get("actual_gross_return"))
        if gross is None:
            missing.append(identifier)
            continue
        baseline = gross - COST
        # Failures retain baseline exposure, including all its losses.
        action = "fallback" if not forecast_ok else ("accept" if predicted > COST else "reject")
        rows.append({
            "event_id": identifier,
            "symbol": record.get("symbol"),
            "date": utc_date(record["decision_time"]),
            "baseline": baseline,
            "combined": 0.0 if action == "reject" else baseline,
            "action": action,
        })
        # The forecast starts at the last observed close, while the executable
        # return starts one hour later. Score each against its own denominator.
        target = finite(record.get("actual_forecast_target_return"))
        if forecast_ok and target is not None:
            forecast_errors.append(abs(predicted - target))
            flat_errors.append(abs(target))

    selected = [row for row in rows if row["action"] == "accept"]
    rejected = [row for row in rows if row["action"] == "reject"]
    fallback = [row for row in rows if row["action"] == "fallback"]
    interval = cluster_interval(rows, resamples)
    delta = paired_delta(rows)
    dates = len({row["date"] for row in rows})
    fallback_fraction = len(fallback) / len(rows) if rows else None
    best = max(selected, key=lambda row: row["baseline"]) if selected else None
    without_best = [row for row in rows if best is None or row["event_id"] != best["event_id"]]
    winner_removed_delta = paired_delta(without_best)
    enough = len(rows) >= 50 and len(selected) >= 10 and dates >= 10
    coverage_ok = not missing and fallback_fraction is not None and fallback_fraction <= 0.05
    verdict = classify(enough, coverage_ok, interval, winner_removed_delta)
    combined = stats([row["combined"] for row in rows])
    result = {
        "study_type": "exploratory_paired_event_study",
        "return_units": "fractions",
        "rule": "accept if status=ok and predicted_return > 0.02; rejected events hold cash; failed forecasts retain baseline",
        "round_trip_cost": COST,
        "counts": {
            "submitted": len(records), "usable_outcomes": len(rows),
            "missing_or_nonfinite_outcomes": len(missing),
            "invalid_or_failed_forecasts": len(invalid_forecasts),
            "selected": len(selected), "rejected": len(rejected), "fallback": len(fallback),
            "decision_utc_dates": dates,
        },
        "outcome_coverage": len(rows) / len(records) if records else None,
        "fallback_fraction_of_usable": fallback_fraction,
        "baseline": stats([row["baseline"] for row in rows]),
        "combined_on_same_opportunities": combined,
        "cash_baseline_mean_net_return": 0.0,
        "combined_beats_cash": combined["mean_net_return"] is not None and combined["mean_net_return"] > 0,
        "paired_mean_delta": delta,
        "paired_delta_95pct_date_cluster_bootstrap": interval,
        "bootstrap": {"seed": SEED, "resamples": resamples, "cluster": "decision UTC date", "interval": "percentile"},
        "selected": stats([row["baseline"] for row in selected]),
        "rejected_counterfactual": stats([row["baseline"] for row in rejected]),
        "fallback": stats([row["baseline"] for row in fallback]),
        "forecast_error_count": len(forecast_errors),
        "forecast_mae": statistics.fmean(forecast_errors) if forecast_errors else None,
        "flat_zero_return_mae": statistics.fmean(flat_errors) if flat_errors else None,
        "runtime_seconds": {"n": len(runtimes), "median": statistics.median(runtimes) if runtimes else None,
                            "max": max(runtimes) if runtimes else None},
        "largest_selected_winner_removed": {
            "removed_event_id": best["event_id"] if best else None,
            "baseline": stats([row["baseline"] for row in without_best]),
            "combined": stats([row["combined"] for row in without_best]),
            "paired_mean_delta": winner_removed_delta,
        },
        "missing_outcome_event_ids": missing,
        "invalid_forecast_event_ids": invalid_forecasts,
        "verdict": verdict,
        "promotion_authorized": False,
        "limitations": ["Historical screening is exploratory, not independent prospective validation.",
                        "Per-event equal opportunity weights do not model overlapping positions or constrained capital.",
                        "A better forecast error or exploratory interval does not establish a profitable strategy."],
    }
    # Guard the serialized contract against NaN/Infinity escaping into a report.
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.records.read_text().splitlines() if line.strip()]
    args.output.write_text(json.dumps(evaluate(records), indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
