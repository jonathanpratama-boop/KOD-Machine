"""Rule registry.

A rule is frozen code plus the rule text it implements, verbatim. `compute(market)`
returns a float array shaped (tickers, sessions): 1.0 = signal at that session's close,
0.0 = evaluated, no signal, NaN = not evaluable (not listed, no trade, not enough
history). Column d may only use data from sessions <= d; every run re-checks this by
recomputing on truncated data. The rule hash covers the text and the module source, so
editing a rule after a run produces a new rule hash and a new run, never a changed one.
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


def signal_array(rule: Rule, market) -> np.ndarray:
    out = np.asarray(rule.compute(market), dtype=float)
    if out.shape != market.shape:
        raise ValueError(f"{rule.rule_id} returned shape {out.shape}, expected {market.shape}")
    bad = np.isfinite(out) & (out != 0) & (out != 1)
    if bad.any():
        raise ValueError(f"{rule.rule_id} returned values other than 0, 1, NaN")
    return out
