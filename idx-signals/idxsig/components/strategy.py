"""Allowlisted strategy contracts for reproducible, research-only evaluations.

Signal, allocation, risk and execution remain separate responsibilities. New
templates never become admitted paper strategies by appearing in this registry.
The incumbent trend adapter delegates its calculations to the pinned account.
"""

from __future__ import annotations

import math
import statistics
from decimal import Decimal

from ..runtime.data import parse_time, utc_text
from ..runtime.storage import digest
from .costs import decimal

VERSION = "KOD_STRATEGY_EVALUATION_V1"
SMA = "SMA_CROSS_SHADOW_V1"
RETURN = "RETURN_THRESHOLD_SHADOW_V1"


def registry():
    """Describe evaluators; this is not the trading-admission registry."""
    return [
        {
            "id": SMA,
            "version": "1",
            "scope": "RESEARCH_ONLY",
            "description": "Completed-observation fast/slow moving-average comparison",
            "parameters": {"fast": 10, "slow": 40},
            "entry_enabled": False,
            "live_enabled": False,
        },
        {
            "id": RETURN,
            "version": "1",
            "scope": "RESEARCH_ONLY",
            "description": "Completed-observation return threshold; an unvalidated hypothesis",
            "parameters": {"lookback": 3, "threshold": 0.10},
            "entry_enabled": False,
            "live_enabled": False,
        },
    ]


def _integer(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10000:
        raise ValueError(f"{field}: integer in 1..10000 required")
    return value


def specification(strategy, parameters=None):
    """Resolve one immutable evaluator version and validate its full parameters."""
    if isinstance(strategy, dict):
        if set(strategy) != {"id", "version", "parameters"} or parameters is not None:
            raise ValueError("strategy requires exactly id, version and parameters")
        if strategy["version"] != "1":
            raise ValueError("unsupported evaluator version")
        parameters, strategy = strategy["parameters"], strategy["id"]
    if not isinstance(strategy, str) or strategy not in {SMA, RETURN}:
        raise ValueError("unknown research evaluator; strategy admission is separate")
    defaults = next(row["parameters"] for row in registry() if row["id"] == strategy)
    if parameters is None:
        parameters = defaults
    if not isinstance(parameters, dict) or set(parameters) != set(defaults):
        raise ValueError("unknown or missing strategy parameter")
    if strategy == SMA:
        fast = _integer(parameters["fast"], "fast")
        slow = _integer(parameters["slow"], "slow")
        if fast >= slow:
            raise ValueError("fast must precede slow")
        params = {"fast": fast, "slow": slow}
    else:
        lookback = _integer(parameters["lookback"], "lookback")
        threshold = decimal(parameters["threshold"], "threshold")
        if threshold > 100:
            raise ValueError("unsupported return threshold")
        params = {"lookback": lookback, "threshold": float(threshold)}
    return {"id": strategy, "version": "1", "parameters": params}


def _observations(rows):
    if not isinstance(rows, list) or len(rows) > 100000:
        raise ValueError("a bounded list of at most 100000 observations is required")
    out, previous, symbol = [], None, None
    for row in rows:
        if not isinstance(row, dict) or not {"observed_at", "close"} <= set(row):
            raise ValueError("each observation requires observed_at and close")
        at = parse_time(row["observed_at"])
        if previous is not None and at <= previous:
            raise ValueError("observations require strictly increasing availability times")
        name = row.get("symbol", "UNSPECIFIED")
        if not isinstance(name, str) or not name.strip() or (symbol and symbol != name):
            raise ValueError("one explicit symbol per series required")
        # observed_at is availability, not the bar's hypothetical start time.
        if row.get("event_at") is not None and parse_time(row["event_at"]) > at:
            raise ValueError("event occurs after declared observation availability")
        value = float(decimal(row["close"], "close", positive=True))
        if not math.isfinite(value):
            raise ValueError("close exceeds evaluator numeric range")
        out.append((utc_text(at), name, value))
        previous, symbol = at, name
    return out


def evaluate_series(strategy, observations, parameters=None):
    """Return one signal per observation using only its available prefix.

    Input: [{observed_at, close, symbol?, event_at?}]. Output rows carry READY or
    WARMUP. Missing warm-up is unknown, not a zero-return prediction. This pure
    function neither reads outcomes nor modifies an account or the input rows.
    """
    spec = specification(strategy, parameters)
    rows = _observations(observations)
    params = spec["parameters"]
    closes, decisions = [], []
    for at, symbol, close in rows:
        closes.append(close)
        value = None
        if spec["id"] == SMA and len(closes) >= params["slow"]:
            fast = statistics.mean(closes[-params["fast"] :])
            slow = statistics.mean(closes[-params["slow"] :])
            value = fast / slow - 1
            signal = int(fast > slow)
        elif spec["id"] == RETURN and len(closes) > params["lookback"]:
            value = close / closes[-params["lookback"] - 1] - 1
            signal = int(value >= params["threshold"])
        else:
            signal = None
        if value is not None and not math.isfinite(value):
            raise ValueError("indicator exceeds evaluator numeric range")
        decisions.append(
            {
                "observed_at": at,
                "symbol": symbol,
                "status": "WARMUP" if value is None else "READY",
                "signal": signal,
                "value": value,
            }
        )
    return decisions


def evaluate_batch(request):
    """JSON-facing adapter used by the CLI and bounded research worker."""
    if not isinstance(request, dict) or not {"strategy", "observations"} <= set(request):
        raise ValueError("strategy and observations are required")
    if set(request) - {"strategy", "observations", "as_of"}:
        raise ValueError("unknown strategy evaluation request field")
    spec = specification(request["strategy"])
    decisions = evaluate_series(spec, request["observations"])
    if request.get("as_of") is not None:
        cutoff = parse_time(request["as_of"])
        if any(parse_time(row["observed_at"]) > cutoff for row in decisions):
            raise ValueError("observation available after evaluation cutoff")
    return {
        "schema_version": VERSION,
        "strategy": spec,
        "input_sha256": digest(request),
        "decisions": decisions,
        "scope": "RESEARCH_ONLY",
        "entry_enabled": False,
        "live_enabled": False,
    }


def portfolio_targets(signals, *, gross_weight="1", symbol_limit="1"):
    """Equal-weight active signals under declared limits, leaving unused cash."""
    gross = decimal(gross_weight, "gross_weight")
    limit = decimal(symbol_limit, "symbol_limit")
    if gross > 1 or limit > 1 or not isinstance(signals, dict):
        raise ValueError("long-only unlevered allocation required")
    if any(
        not isinstance(name, str)
        or not name
        or isinstance(value, bool)
        or not isinstance(value, int)
        or value not in (0, 1)
        for name, value in signals.items()
    ):
        raise ValueError("allocation requires known binary signals by symbol")
    active = sum(signals.values())
    weight = min(limit, gross / active) if active else Decimal(0)
    return {name: str(weight if value else Decimal(0)) for name, value in sorted(signals.items())}


def assess_risk(targets, *, admitted=False, fresh=False, max_gross="1", max_symbol="1"):
    """Independent fail-closed gate; no signal score grants execution permission."""
    if not isinstance(targets, dict) or not targets:
        raise ValueError("explicit portfolio targets required")
    if not isinstance(admitted, bool) or not isinstance(fresh, bool):
        raise ValueError("explicit boolean admission and freshness required")
    gross = decimal(max_gross, "max_gross")
    limit = decimal(max_symbol, "max_symbol")
    if gross > 1 or limit > 1:
        raise ValueError("risk limits must be unlevered")
    if any(not isinstance(name, str) or not name.strip() for name in targets):
        raise ValueError("explicit target symbols required")
    weights = {name: decimal(weight, "target") for name, weight in targets.items()}
    reasons = []
    if not admitted:
        reasons.append("STRATEGY_NOT_ADMITTED")
    if not fresh:
        reasons.append("DATA_NOT_FRESH")
    if sum(weights.values()) > gross:
        reasons.append("GROSS_LIMIT")
    if any(weight > limit for weight in weights.values()):
        reasons.append("SYMBOL_LIMIT")
    return {
        "allowed": not reasons,
        "reasons": reasons,
        "targets": {k: str(v) for k, v in weights.items()},
    }


def evaluate_trend(signal_evidence, signal_date, decision_at):
    """Expose existing signal/allocation stages without changing pinned economics."""
    from ..runtime.account import signals, wire

    raw, targets, metrics = signals(signal_evidence, signal_date, decision_at)
    return wire({"raw_weights": raw, "targets": targets, "metrics": metrics})
