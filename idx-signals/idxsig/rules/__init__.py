"""Rule registry and the causal interface rules compute through.

A rule is frozen code plus the rule text it implements, verbatim. `compute(view)` gets a
RuleView and returns a float array shaped view.shape (names x sessions): 1.0 = signal at
that session's close, 0.0 = evaluated, no signal, NaN = not evaluable. The rule hash covers
the text and the module source, so editing a rule after a run produces a new rule hash and
a new run, never a changed one.

Causal by construction (causal_signals): a run calls compute once per session d, on a view
holding only sessions 0..d and only the names listed by d, and records column d of that
call as the signal at d. So every recorded signal is exactly what the rule computed from
data available at that close; nothing later was in its input. Three further layers stop a
rule from fetching the future some other way:

  1. audit.py refuses rule source that imports I/O modules, reads files, walks frames,
     keeps state between calls or holds data loaded at import time.
  2. sandbox.py blocks file, network, process, frame and heap access while compute runs.
  3. One extra call on the whole window is compared with the prefix-built signals; any
     difference (a rule that behaves differently when it sees more data) is a
     LookaheadError, not a silent fix.

A RuleView has exchange data only. The corporate-action registry and share factors are
built from later sources (Yahoo downloads, primary documents) and never reach a rule.
"""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass
from types import ModuleType
from typing import Callable

import numpy as np


class RuleNotProvided(RuntimeError):
    pass


@dataclass(frozen=True)
class Rule:
    rule_id: str
    version: str
    text: str
    holding_days: int
    compute: Callable
    module: ModuleType
    kind: str = "DETECTOR"  # or "PLACEBO" (harness self-check, not a trading rule)

    @property
    def sha256(self) -> str:
        body = self.text + "\n---\n" + inspect.getsource(self.module)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()


def registry() -> dict:
    from . import placebo, user_rule

    out = {}
    for module in (user_rule, placebo):
        rule = module.rule()
        if rule is not None:
            out[rule.rule_id] = rule
    return out


def pending() -> list[str]:
    from . import user_rule

    return [] if user_rule.rule() is not None else [user_rule.RULE_ID]


def get(rule_id: str) -> Rule:
    from . import user_rule

    if rule_id == user_rule.RULE_ID and user_rule.rule() is None:
        raise RuleNotProvided(user_rule.MISSING)
    rules = registry()
    if rule_id not in rules:
        raise KeyError(f"unknown rule {rule_id}; known: {sorted(rules)}")
    return rules[rule_id]


RULE_FIELDS = ("close", "prev", "high", "low", "volume", "value", "present", "tradeable", "lock_up", "lock_down",
               "listed_shares")
CAUSAL_MODE = "prefix-first-v1"


class LookaheadError(RuntimeError):
    pass


class RuleView:
    """Read-only exchange data for sessions 0..last and the first `rows` names in listing order.

    Every field is copied when the view is built, so nothing reachable from a view, by any
    route, extends past session `last` or covers a name not yet listed."""

    __slots__ = ("tickers", "dates", "shape", *RULE_FIELDS)

    def __init__(self, src: dict, tickers: np.ndarray, dates: np.ndarray, rows: int, last: int):
        self.tickers = _frozen(tickers[:rows])
        self.dates = _frozen(dates[: last + 1])
        self.shape = (rows, last + 1)
        for name in RULE_FIELDS:
            setattr(self, name, _frozen(src[name][:rows, : last + 1]))

    def __getattr__(self, name):
        raise AttributeError(f"RuleView has no {name!r}; a rule sees only {', '.join(RULE_FIELDS)}, tickers, dates")


def _frozen(a: np.ndarray) -> np.ndarray:
    out = np.array(a, copy=True, order="C")
    out.flags.writeable = False
    return out


class CausalSource:
    """A market's rule-visible fields with names ordered by first listed session, so the names
    listed by session d are the first rows_at(d) rows."""

    def __init__(self, market):
        n_sessions = market.shape[1]
        listed = market.present.any(axis=1)
        first = np.where(listed, market.present.argmax(axis=1), n_sessions)
        self.order = np.lexsort((np.arange(len(first)), first))
        self.first = first[self.order]
        self.n_sessions = n_sessions
        self.fields = {f: getattr(market, f)[self.order] for f in RULE_FIELDS}
        self.tickers = market.tickers[self.order]
        self.dates = market.dates

    def rows_at(self, d: int) -> int:
        return int(np.searchsorted(self.first, d, side="right"))

    def view(self, d: int) -> RuleView:
        return RuleView(self.fields, self.tickers, self.dates, self.rows_at(d), d)

    def unorder(self, ordered: np.ndarray) -> np.ndarray:
        out = np.empty_like(ordered)
        out[self.order] = ordered
        return out


def _call(rule: Rule, view: RuleView) -> np.ndarray:
    from . import sandbox

    try:
        with sandbox.guarded() as violations:
            raw = rule.compute(view)
    except sandbox.SandboxViolation as exc:
        raise LookaheadError(f"{rule.rule_id}: {exc}") from None
    if violations:
        raise LookaheadError(f"{rule.rule_id}: blocked while computing (and swallowed): {violations[0]}")
    return signal_array(rule, view, raw)


def signal_array(rule: Rule, view, raw=None) -> np.ndarray:
    out = np.asarray(rule.compute(view) if raw is None else raw, dtype=float)
    if out.shape != view.shape:
        raise ValueError(f"{rule.rule_id} returned shape {out.shape}, expected {view.shape}")
    bad = np.isfinite(out) & (out != 0) & (out != 1)
    if bad.any():
        raise ValueError(f"{rule.rule_id} returned values other than 0, 1, NaN")
    return out


def causal_signals(rule: Rule, market, audit: bool = True) -> tuple[np.ndarray, dict]:
    """Signals assembled from one call per session on data through that session only."""
    from .audit import require_clean

    if audit:
        require_clean(rule)
    src = CausalSource(market)
    n_rows, n_sessions = market.shape
    built = np.full((n_rows, n_sessions), np.nan)
    calls = 0
    for d in range(n_sessions):
        k = src.rows_at(d)
        if k:
            built[:k, d] = _call(rule, src.view(d))[:, d]
            calls += 1
    full = np.full((n_rows, n_sessions), np.nan)
    k_end = src.rows_at(n_sessions - 1)
    full[:k_end] = _call(rule, src.view(n_sessions - 1))
    listed = np.arange(n_rows)[:, None] < np.array([src.rows_at(d) for d in range(n_sessions)])[None, :]
    differs = listed & ~((np.isnan(full) & np.isnan(built)) | (full == built))
    if differs.any():
        i, d = np.argwhere(differs)[0]
        raise LookaheadError(
            f"{rule.rule_id}: given the whole window it signals {full[i, d]} for {src.tickers[i]} on "
            f"{market.dates[d]}, but given data only through that close it signals {built[i, d]}: it reads "
            f"data from after the close, depends on names not yet listed, or keeps state between calls "
            f"({int(differs.sum())} ticker-sessions differ)")
    return src.unorder(built), {"mode": CAUSAL_MODE, "sessions": n_sessions, "prefix_calls": calls,
                                "full_window_mismatches": 0, "source_audit": "passed" if audit else "skipped",
                                "sandbox": "file, network, process, frame and heap access blocked during compute"}
