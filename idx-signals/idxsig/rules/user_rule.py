"""The detector rule under test. EMPTY until the rule text is supplied.

The request asked to "implement this rule exactly: [paste your detector rule]" and the
placeholder was never filled in, so there is no rule here. Nothing is guessed. To add it:

  1. Paste the rule, verbatim, into RULE_TEXT.
  2. Set VERSION (e.g. "v1") and HOLDING_DAYS (sessions, pre-registered).
  3. Implement compute(market) to match the text exactly, using only data <= each
     session (see rules/__init__.py for the contract and placebo.py for an example).
  4. Commit, then `python -m idxsig run --rule USER_RULE`.

Any later change to the text or the code is a new version and a new run.
"""

from __future__ import annotations

RULE_ID = "USER_RULE"
VERSION: str | None = None
RULE_TEXT: str | None = None
HOLDING_DAYS: int | None = None
MISSING = (
    "USER_RULE has no rule text. The request said '[paste your detector rule]' and the rule "
    "was never pasted. Put it in idx-signals/idxsig/rules/user_rule.py (RULE_TEXT, VERSION, "
    "HOLDING_DAYS, compute) before running."
)


def compute(market):  # pragma: no cover - replaced when the rule is supplied
    from . import RuleNotProvided

    raise RuleNotProvided(MISSING)


def rule():
    from . import Rule

    if not RULE_TEXT or not VERSION or not HOLDING_DAYS:
        return None
    import sys

    return Rule(RULE_ID, VERSION, RULE_TEXT, HOLDING_DAYS, compute, sys.modules[__name__])
