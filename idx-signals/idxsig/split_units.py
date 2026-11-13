"""SPLIT_UNITS_V1: is a recorded one-session move real, or only a change of price units across a share split?

The rule is check C01 of the KODCHECK audit of 2026-11-12, steps 1 to 5, with its addendum 1; the text is in
research/SPLIT_REVISIONS_v1/CONTRACT.md, part A. It differs from SPLIT_ARTIFACT_V11 in one way that matters: it asks
which session supplied the previous close. A split counts only when it falls between the previous bar and the signal
bar, and a later pull of the closes is used to see whether the recorded previous close was in pre-split units.

Pure functions, standard library only. Nothing here reads or writes a ledger.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
RULE_ID = "SPLIT_UNITS_V1"
THRESHOLD = 0.30
LOOKBACK_DAYS = 10
EXTREME_RATIO = 4.0
MAX_PREV_GAP_DAYS = 5
UNCHANGED_TOL = 0.01
REBASED_TOL = 0.03
MIN_SPLIT_FACTOR = 1.05
REFERENCE_LOOKBACK_DAYS = 30
_EPS = 1e-9  # floating-point noise only, not a tolerance on data

GROUP = {
    "ARTIFACT_CONFIRMED": "ARTIFACT",
    "ARTIFACT_PROBABLE": "ARTIFACT",
    "REAL_MOVE_UNITS_CONTAMINATED": "CONTAMINATED",
    "REAL_MOVE_AFTER_SPLIT": "REAL",
    "NO_ACTION_FOUND": "REAL",
    "NOT_ASSESSABLE": "UNRESOLVED",
    "UNITS_INCONSISTENT": "UNRESOLVED",
    "SPLIT_IN_WINDOW_UNRESOLVED": "UNRESOLVED",
    "REAL_MOVE_UNITS_UNVERIFIED": "UNRESOLVED",
    "UNEXPLAINED_EXTREME_MOVE": "UNRESOLVED",
    "STALE_PREVIOUS": "UNRESOLVED",
}
CLASSES = tuple(GROUP)


def _pos(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def _day(x):
    if not isinstance(x, str):
        return None
    try:
        return date.fromisoformat(x) if len(x) == 10 else None
    except ValueError:
        return None


def _lt(a, b) -> bool:
    return a < b - _EPS


def _gt(a, b) -> bool:
    return a > b + _EPS


def _answer(cls, previous_session=None, source=None, units="UNKNOWN", event=None, adjusted=None, later=None) -> dict:
    return {
        "class": cls,
        "group": GROUP[cls],
        "previous_session": previous_session,
        "previous_session_source": source,
        "units": units,
        "event": event,
        "adjusted_ret1": None if adjusted is None else round(adjusted, 4),
        "later_factor": later,
    }


def classify(close, previous, signal_session, events, bars, previous_session=None, retrieved_on=None) -> dict:
    """The class of one recorded pair of closes. See CONTRACT.md part A for the rule and part B1 for the result."""
    S = _day(signal_session)
    if not (_pos(close) and _pos(previous)) or S is None:
        return _answer("NOT_ASSESSABLE")
    s_iso = S.isoformat()
    r = close / previous
    ln_r = math.log(r)

    events = events if isinstance(events, (list, tuple)) else []
    bars = bars if isinstance(bars, (list, tuple)) else []
    valid = []
    for e in events:
        if not isinstance(e, dict):
            continue
        n, d, eff = e.get("numerator"), e.get("denominator"), e.get("effective_session")
        if _pos(n) and _pos(d) and _day(eff) is not None:
            valid.append({"effective_session": eff, "numerator": n, "denominator": d, "k": d / n})

    # Step 1: reference bars inside the lookback, strictly before the signal session.
    ref_lo = (S - timedelta(days=REFERENCE_LOOKBACK_DAYS)).isoformat()
    ref = {}
    for item in bars:
        try:
            session, px = item
        except (TypeError, ValueError):
            continue
        if _day(session) is not None and _pos(px) and ref_lo <= session < s_iso:
            ref[session] = float(px)
    sessions = sorted(ref)

    # Step 2: candidate events.
    lo = (S - timedelta(days=LOOKBACK_DAYS)).isoformat()
    min_ln = math.log(MIN_SPLIT_FACTOR)
    E = [e for e in valid if _gt(abs(math.log(e["k"])), min_ln) and lo < e["effective_session"] <= s_iso]
    E.sort(key=lambda e: e["effective_session"], reverse=True)

    # Addendum 1: a pull made after a later split may show every earlier close multiplied by its factor.
    upto = retrieved_on if _day(retrieved_on) is not None else None
    later = 1.0
    for e in valid:
        if e["effective_session"] > s_iso and (upto is None or e["effective_session"] <= upto):
            later *= e["k"]
    factors = [1.0] + ([later] if _gt(abs(math.log(later)), min_ln) else [])

    # Step 3: the previous bar and its units.
    tol_u, tol_r = math.log(1 + UNCHANGED_TOL), math.log(1 + REBASED_TOL)

    def near(q, target, tol) -> bool:
        return abs(math.log(q / target)) <= tol + _EPS

    P, source, units, units_event, used = None, None, "UNKNOWN", None, 1.0
    if _day(previous_session) is not None:
        P, source = previous_session, "recorded"
        q = ref.get(P)
        if q is not None:
            units = "INCONSISTENT"
            for f in factors:
                if near(q, previous * f, tol_u):
                    units, used = "UNCHANGED", f
                    break
            if units == "INCONSISTENT":
                for e in E:
                    hit = next(
                        (f for f in factors if P < e["effective_session"] and near(q, previous * e["k"] * f, tol_r)),
                        None,
                    )
                    if hit is not None:
                        units, units_event, used = "PRE_SPLIT_CONFIRMED", e, hit
                        break
    elif sessions:
        units = "INCONSISTENT"
        for f in factors:
            same = [x for x in sessions if near(ref[x], previous * f, tol_u)]
            if same:
                P, source, units, used = same[-1], "matched", "UNCHANGED", f
                break
        if units == "INCONSISTENT":
            for e in E:
                found = None
                for f in factors:
                    rebased = [
                        x for x in sessions if x < e["effective_session"] and near(ref[x], previous * e["k"] * f, tol_r)
                    ]
                    if rebased:
                        found = (rebased[-1], f)
                        break
                if found:
                    P, source, units, units_event, used = found[0], "rebased_match", "PRE_SPLIT_CONFIRMED", e, found[1]
                    break
    later_used = used if used != 1.0 else None

    # Step 4: straddle.
    def straddle(e) -> str:
        if P is None:
            return "UNKNOWN"
        return "YES" if P < e["effective_session"] else "NO"

    def closer(e) -> bool:
        return _lt(abs(math.log(r / e["k"])), abs(ln_r))

    def explains(e) -> bool:
        return _lt(r / e["k"] - 1, THRESHOLD) and closer(e)

    def out(cls, event=None, adjusted=None) -> dict:
        return _answer(cls, P, source, units, event, adjusted, later_used)

    # Step 5: the first matching rule decides.
    if units == "INCONSISTENT":
        return out("UNITS_INCONSISTENT")
    if units == "PRE_SPLIT_CONFIRMED":
        a = r / units_event["k"]
        cls = "ARTIFACT_CONFIRMED" if _lt(a - 1, THRESHOLD) else "REAL_MOVE_UNITS_CONTAMINATED"
        return out(cls, units_event, a - 1)
    C = [e for e in E if straddle(e) != "NO"]
    X = [e for e in C if explains(e)]
    if X:
        e = X[0]
        a = r / e["k"]
        if straddle(e) == "YES" or not _lt(r, EXTREME_RATIO):
            return out("ARTIFACT_PROBABLE", e, a - 1)
        return out("SPLIT_IN_WINDOW_UNRESOLVED", e, a - 1)
    if any(closer(e) for e in C):
        return out("REAL_MOVE_UNITS_UNVERIFIED")
    if not _lt(r, EXTREME_RATIO):
        return out("UNEXPLAINED_EXTREME_MOVE")
    if P is not None and (S - date.fromisoformat(P)).days > MAX_PREV_GAP_DAYS:
        return out("STALE_PREVIOUS")
    if E:
        return out("REAL_MOVE_AFTER_SPLIT")
    return out("NO_ACTION_FOUND")


def payload_bars(payload) -> list:
    """(New York session, close) pairs of a provider chart payload; [] for anything missing or malformed."""
    try:
        result = payload["chart"]["result"][0]
        stamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        out = []
        for unix, px in zip(stamps, closes):
            session = datetime.fromtimestamp(int(unix), timezone.utc).astimezone(NY).date().isoformat()
            out.append((session, px))
        return out
    except (TypeError, KeyError, IndexError, AttributeError, ValueError, OverflowError, OSError):
        return []
