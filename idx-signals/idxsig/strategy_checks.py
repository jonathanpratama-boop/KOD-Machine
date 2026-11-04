"""Finite black-box checks for research signals, without promoting a strategy.

The callback accepts observations and returns one JSON row per observation.
These checks complement the rule sandbox: they inspect only the supplied cases,
and cannot prove that unexercised branches or external data are free of leakage.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Sequence

from .runtime.storage import canonical, digest

VERSION = "KOD_STRATEGY_CHECKS_V1"
MAX_OBSERVATIONS = 2000


def _same(left, right, atol, rtol):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(left, right, abs_tol=atol, rel_tol=rtol)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            (
                left[key] == right[key]
                if key in {"signal", "status", "observed_at", "symbol"}
                else _same(left[key], right[key], atol, rtol)
            )
            for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_same(a, b, atol, rtol) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def _evaluate(evaluate, observations):
    supplied = copy.deepcopy(observations)
    before = digest(supplied)
    result = evaluate(supplied)
    if digest(supplied) != before:
        raise ValueError("evaluator mutated its input observations")
    if not isinstance(result, list) or len(result) != len(observations):
        raise ValueError("evaluator must return one row per observation")
    if not all(isinstance(row, dict) for row in result):
        raise ValueError("evaluator rows must be JSON objects")
    canonical(result)  # Reject NaN, infinity, and non-serializable outputs.
    return copy.deepcopy(result)


def run_strategy_checks(
    evaluate: Callable,
    observations: Sequence[dict],
    *,
    warmup_lengths=(),
    atol=1e-9,
    rtol=1e-7,
):
    """Check repeatability, every prefix, and declared warm-up windows.

    Warm-up comparison is UNKNOWN if no windows are requested or any requested
    window cannot produce a READY final signal. Numeric indicator differences
    use explicit tolerances; signal/status/identity differences remain failures.
    A PASS covers these supplied observations only and grants no entry permission.
    """
    rows = copy.deepcopy(list(observations))
    if not 1 <= len(rows) <= MAX_OBSERVATIONS:
        raise ValueError(f"supply 1 to {MAX_OBSERVATIONS} observations")
    for tolerance in (atol, rtol):
        if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
            raise ValueError("tolerances must be finite nonnegative numbers")
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError("tolerances must be finite nonnegative numbers")
    lengths = list(warmup_lengths)
    if len(lengths) != len(set(lengths)) or any(
        isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= len(rows) for n in lengths
    ):
        raise ValueError("warm-up lengths must be distinct valid history sizes")
    report = {
        "schema_version": VERSION,
        "status": "UNKNOWN",
        "observation_sha256": digest(rows),
        "observations": len(rows),
        "tolerances": {"absolute": atol, "relative": rtol},
        "checks": {},
        "entry_permission": False,
        "scope": "Supplied observations and exercised evaluator branches only",
    }
    try:
        full = _evaluate(evaluate, rows)
        repeated = _evaluate(evaluate, rows)
        deterministic = canonical(full) == canonical(repeated)
        report["checks"]["repeatability"] = {
            "status": "PASS" if deterministic else "FAIL",
            "output_sha256": digest(full),
        }
        mismatches = []
        for count in range(1, len(rows) + 1):
            prefix = _evaluate(evaluate, rows[:count])
            if not _same(full[:count], prefix, atol, rtol):
                mismatches.append(count)
        report["checks"]["prefix_invariance"] = {
            "status": "FAIL" if mismatches else "PASS",
            "prefixes_checked": len(rows),
            "mismatching_prefix_lengths": mismatches,
        }
        windows = []
        for count in lengths:
            result = _evaluate(evaluate, rows[-count:])[-1]
            ready = count < len(rows) and result.get("status") == full[-1].get("status") == "READY"
            outcome = (
                "UNKNOWN"
                if not ready
                else ("PASS" if _same(full[-1], result, atol, rtol) else "FAIL")
            )
            windows.append({"history_length": count, "status": outcome, "final": result})
        warmup = "UNKNOWN"
        if windows:
            warmup = (
                "FAIL"
                if any(w["status"] == "FAIL" for w in windows)
                else ("PASS" if all(w["status"] == "PASS" for w in windows) else "UNKNOWN")
            )
        report["checks"]["warmup_stability"] = {
            "status": warmup,
            "windows": windows,
            "reference_history_length": len(rows),
            "reference_final": full[-1],
            "reason": "No warm-up windows requested" if not windows else None,
        }
    except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
        report["checks"]["evaluator_contract"] = {
            "status": "FAIL",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }
    statuses = [item["status"] for item in report["checks"].values()]
    report["status"] = (
        "FAIL" if "FAIL" in statuses else ("UNKNOWN" if "UNKNOWN" in statuses else "PASS")
    )
    return report
