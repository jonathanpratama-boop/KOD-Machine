"""E3-US-RETENTION-v1 decision policy core; not registered as a trading rule.

Consumes frozen E2 flags. No outcome, future bar, split-verification status,
entry fill, or result is an input to a decision. See PROTOCOL.md for the
historical runner, controls, unresolved fill assumptions and advancement gates.
"""

import math
import statistics

VERSION = "E3-US-RETENTION-v1"
NOTIONAL_USD = 5000.0
CAPACITY_FRACTION = 0.01
CAPACITY_SESSIONS = 20


def _positive(value):
    return value is not None and math.isfinite(value) and value > 0


def confirmation_at(flags, closes, present, decision_index):
    """At close d, retain the frozen flag at d-1 iff close d >= close d-1.

Arrays contain one ticker on the common session calendar, with no forward
filling. Only indices d-1 and d are accessed, even if later bars are supplied.
"""
    if decision_index < 1:
        return False
    if any(len(a) <= decision_index for a in (flags, closes, present)):
        raise ValueError("decision session is not observed")
    origin = decision_index - 1
    return bool(flags[origin] == 1 and present[origin] and present[decision_index]
                and _positive(closes[origin]) and _positive(closes[decision_index])
                and closes[decision_index] >= closes[origin])


def capacity_at(dollar_values, present, decision_index, notional=NOTIONAL_USD):
    """Known daily dollar-volume budget, not a claim of opening-auction capacity.

Value = adjusted close * consistently adjusted volume, so later split-unit
rescaling cancels. A present zero-trade session counts as zero. Missing/invalid
history refuses entry; it is reported separately rather than dropping the name.
"""
    if not math.isfinite(notional) or notional <= 0:
        raise ValueError("notional must be finite and positive")
    if decision_index < 0 or any(len(a) <= decision_index for a in (dollar_values, present)):
        raise ValueError("decision session is not observed")
    if decision_index + 1 < CAPACITY_SESSIONS:
        return {"eligible": False, "reason": "INSUFFICIENT_HISTORY", "budget_usd": None}
    history = []
    for i in range(decision_index - CAPACITY_SESSIONS + 1, decision_index + 1):
        value = dollar_values[i]
        if not present[i] or value is None or not math.isfinite(value) or value < 0:
            return {"eligible": False, "reason": "INVALID_HISTORY", "budget_usd": None}
        history.append(value)
    budget = CAPACITY_FRACTION * statistics.median(history)
    return {"eligible": notional <= budget, "reason": "ELIGIBLE" if notional <= budget else "CAPACITY",
            "budget_usd": budget}


def plan_at(flags, closes, dollar_values, present, decision_index):
    """One decision per observed close; dates are session indices, not civil days.

Five-session legacy offset is explicit: target close = entry index + 5.
No decision asserts that an order filled; the runner must keep rejected and
unresolved orders in the opportunity ledger described by the protocol.
"""
    if not confirmation_at(flags, closes, present, decision_index):
        return {"version": VERSION, "enter": False, "reason": "NO_RETENTION"}
    capacity = capacity_at(dollar_values, present, decision_index)
    if not capacity["eligible"]:
        return {"version": VERSION, "enter": False, **capacity}
    return {"version": VERSION, "enter": True, "reason": "PLAN_ONLY", "origin_index": decision_index - 1,
            "decision_index": decision_index, "entry_index": decision_index + 1,
            "target_exit_index": decision_index + 6, "notional_usd": NOTIONAL_USD,
            "budget_usd": capacity["budget_usd"]}
