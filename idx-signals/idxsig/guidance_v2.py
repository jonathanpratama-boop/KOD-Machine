"""E10 guidance extraction, v2 (research/E10/FEASIBILITY_AMENDMENT_1.md). v1 (idxsig/guidance.py) is unchanged.

Text only, no prices. v1 took the first amount anywhere in a sentence that named revenue, so an acquired business's
sales, a loan balance or a segment figure could stand in for the company's revenue guidance. v2 keeps v1's sentence
filter (revenue term, forward cue, one fiscal year, not a quarter alone) and changes three things:

  1. the amount is anchored to a revenue term: it is the first amount within 80 characters after the term, with no
     other measure word or revenue term in between ("revenue of $1.88 billion to $2.00 billion", "revenue growth of
     12% to 14%"), or a dollar amount directly before it ("$2.80 to $2.81 billion in revenue");
  2. the revenue term is unqualified: stepping back over time words ("full year 2021"), the word before it is a
     function word or a total / net / consolidated marker, not a segment or measure name ("Software Platform
     revenue", "BPaaS full year revenue", "organic sales");
  3. a sentence about an acquired business, a trailing, year-to-date or pro forma period, a run rate or a
     contribution is skipped.

The revision step (research/E10/feasibility_a1.py) also drops a level change beyond +-50% as a measure mismatch, and
counts it.
"""
from __future__ import annotations

import re

from idxsig import guidance as v1
from idxsig.guidance import Guidance, label, level_change, sentences  # noqa: F401  (used by the E10 scripts)

MAX_CHANGE = 0.50
WINDOW_AFTER = 80
WINDOW_BEFORE = 80

REV_TERM = re.compile(r"\b(?:total\s+)?(?:net\s+)?(?:revenues?|sales)\b", re.I)
_VERBS = ("raise", "increase", "update", "reaffirm", "reiterate", "maintain", "narrow", "lower", "reduce", "expect",
          "project", "anticipate", "forecast", "guide", "target", "estimate", "deliver", "generate", "achieve",
          "provide", "issue", "initiate", "confirm", "introduce", "establish", "revise", "tighten")


def _forms(verb: str) -> set[str]:
    stem = verb[:-1] if verb.endswith("e") else verb
    return {verb, verb + "s", stem + "ed", stem + "ing"}


ALLOWED_BEFORE = {
    "total", "net", "consolidated", "company", "company's", "our", "its", "the", "of", "in", "for", "and", "gaap",
    "reported", "overall", "guidance", "outlook", "to", "that", "with", "on", "at", "sees", "see", "seeing", "now",
    "a", "an", "by", "is", "are", "be", "will", "including", "includes", "range", "where", "which", "as", "while",
    "both", "record", "sets", "set", "setting", "also", "currently", "still",
} | set().union(*(_forms(v) for v in _VERBS))
MEASURE_GAP = re.compile(r"\b(EBITDA|EBIT|EPS|earnings|income|margins?|cash|loans?|deposits?|bookings|backlog|ARR|"
                         r"expenses?|capex|capital|assets|balances?|shares?|profit|operating|tax|interest|dividends?|"
                         r"debt|NOI|FFO|AFFO|units|volumes?|segment|organic|comparable)\b", re.I)
SUBJECT_SKIP = re.compile(r"\b(acquired|acquisitions?|acquire|acquiring|merger|combined company|pro forma|"
                          r"twelve months end\w*|trailing|last twelve months|LTM|run[- ]rate|annualized|contribut\w*|"
                          r"divest\w*|year[- ]to[- ]date|YTD|through (?:January|February|March|April|May|June|July|"
                          r"August|September|October|November|December)|(?:first|initial) (?:half|six months|"
                          r"nine months|three quarters))\b", re.I)
GAP_BEFORE = re.compile(r"\s*(?:in|of)\s+", re.I)
TOKENS = re.compile(r"[A-Za-z0-9][\w&'’-]*")
TIME_WORD = re.compile(r"^(?:full|year|full-year|fiscal|annual|calendar|(?:fy)?'?(?:20)?[12]\d|fy)$", re.I)
GROWTH_RANGE_PCT = re.compile(r"\b(grow\w*|growth|increase\w*|up|decline\w*|decrease\w*|down)\b[^.%$]{0,40}?" +
                              v1.NUM + r"\s*(?:to|-|–|—)\s*" + v1.NUM + r"\s*%", re.I)    # "grow 11-14%"
AFTER_PATTERNS = (v1.DOLLAR_RANGE, v1.DOLLAR_ONE, v1.GROWTH_RANGE, GROWTH_RANGE_PCT, v1.GROWTH_ONE)
LIST_BREAK = re.compile(r"[•●▪◦;|]")


def parse(match: re.Match) -> tuple[str, float, float] | None:
    """(kind, low, high) of one amount match; None if it runs across a list break."""
    if LIST_BREAK.search(match.group(0)):
        return None
    if match.re is GROWTH_RANGE_PCT:
        sign = -1.0 if v1.NEGATIVE.match(match.group(1)) else 1.0
        lo, hi = sign * float(match.group(2)) / 100, sign * float(match.group(3)) / 100
        return "growth", min(lo, hi), max(lo, hi)
    return v1.amounts(match.group(0))


def qualified(sentence: str, start: int) -> bool:
    """True if the word before the revenue term at `start`, past any time words ("full year 2021"), names a
    segment or another measure."""
    words = TOKENS.findall(sentence[max(0, start - 60):start])
    while words and TIME_WORD.match(words[-1]):
        words.pop()
    return bool(words) and words[-1].lower().replace("’", "'") not in ALLOWED_BEFORE


def anchored_amount(sentence: str) -> tuple[str, float, float] | None:
    """(kind, low, high) of the first amount anchored to an unqualified revenue term, or None."""
    for term in REV_TERM.finditer(sentence):
        if qualified(sentence, term.start()):
            continue
        tail = sentence[term.end():term.end() + WINDOW_AFTER]
        first = None
        for pat in AFTER_PATTERNS:
            m = pat.search(tail)
            if m and (first is None or m.start() < first.start()):
                first = m
        if first is not None:
            gap = tail[:first.start()]
            if not MEASURE_GAP.search(gap) and not REV_TERM.search(gap) and not LIST_BREAK.search(gap):
                got = parse(first)
                if got is not None:
                    return got
        head = sentence[max(0, term.start() - WINDOW_BEFORE):term.start()]
        for pat in (v1.DOLLAR_RANGE, v1.DOLLAR_ONE):
            ms = list(pat.finditer(head))
            if ms and GAP_BEFORE.fullmatch(head[ms[-1].end():]):
                got = parse(ms[-1])
                if got is not None:
                    return got
    return None


def guidance_sentence(sentence: str) -> Guidance | None:
    if len(sentence) > v1.MAX_SENTENCE or not v1.REVENUE.search(sentence) or not v1.FORWARD.search(sentence):
        return None
    if v1.QUARTER.search(sentence) and not v1.FULL_YEAR.search(sentence):
        return None
    if SUBJECT_SKIP.search(sentence):
        return None
    fy = v1.fiscal_year(sentence)
    if fy is None:
        return None
    a = anchored_amount(sentence)
    if a is None:
        return None
    return Guidance(fy, a[0], a[1], a[2], sentence)


def release_guidance(texts: list[str]) -> dict[tuple[int, str], Guidance]:
    """Per (fiscal year, kind): the largest dollar midpoint, or the first growth figure (as v1)."""
    found: dict[tuple[int, str], Guidance] = {}
    for text in texts:
        for s in sentences(text):
            g = guidance_sentence(s)
            if g is None:
                continue
            key = (g.fiscal_year, g.kind)
            old = found.get(key)
            if old is None or (g.kind == "dollar" and g.mid > old.mid):
                found[key] = g
    return found
