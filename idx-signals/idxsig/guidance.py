"""E10 guidance revision (research/E10): full-year revenue guidance in an earnings release, and its revision.

Pure functions, no network and no prices. research/E10/collect.py fetches the filings; research/E10/FEASIBILITY_SPEC.md
states the rule these functions implement:

  a guidance sentence names revenue or sales, carries a forward cue, names one explicit fiscal year and is not about
  a quarter alone; its amount is a dollar figure or range (millions or billions), or a growth rate or range. Per
  release and fiscal year: the largest dollar midpoint, or the first growth figure. A revision compares a release with
  the same issuer's latest earlier release (at most 200 days earlier) that stated the same kind for the same fiscal
  year: RAISE if the level change is at least +1%, CUT if at most -1%, MAINTAIN otherwise.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass

RAISE_AT = 0.01
CUT_AT = -0.01
MAX_GAP_DAYS = 200

REVENUE = re.compile(r"\b(revenues?|net sales|total sales|sales)\b", re.I)
FORWARD = re.compile(r"\b(expects?|expected|expecting|outlook|guidance|anticipates?|anticipated|forecasts?|"
                     r"projects?|projected|now sees|sees|targets?)\b", re.I)
QUARTER = re.compile(r"\b(quarter|quarterly|Q[1-4])\b", re.I)
FULL_YEAR = re.compile(r"\b(full[- ]year|fiscal[- ]year|for the year|annual|full fiscal|whole year|calendar year)\b",
                       re.I)
FISCAL_YEAR = re.compile(r"\b(?:fiscal(?:\s+year)?|full[- ]year|FY)\s*'?((?:20)?[12]\d)\b", re.I)
YEAR = re.compile(r"\b(20[12]\d)\b")
NUM = r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
UNIT = r"\s*(billion|million|bn|mm)\b"
DOLLAR_RANGE = re.compile(r"\$\s?" + NUM + r"(?:" + UNIT + r")?\s*(?:to|-|–|—|and)\s*\$?\s?" + NUM + UNIT,
                          re.I)
DOLLAR_ONE = re.compile(r"\$\s?" + NUM + UNIT, re.I)
GROWTH_RANGE = re.compile(r"\b(grow\w*|growth|increase\w*|up|decline\w*|decrease\w*|down)\b[^.%$]{0,40}?" + NUM +
                          r"\s*%\s*(?:to|-|–|—|and)\s*" + NUM + r"\s*%", re.I)
GROWTH_ONE = re.compile(r"\b(grow\w*|growth|increase\w*|decline\w*|decrease\w*)\b[^.%$]{0,40}?" + NUM + r"\s*%", re.I)
NEGATIVE = re.compile(r"^(decline|decrease|down)", re.I)
DOC = re.compile(rb"<DOCUMENT>(.*?)</DOCUMENT>", re.S)
DOC_TYPE = re.compile(rb"<TYPE>([^\r\n<]+)")
DOC_TEXT = re.compile(rb"<TEXT>(.*?)</TEXT>", re.S)
ACCEPTANCE = re.compile(rb"<ACCEPTANCE-DATETIME>\s*(\d{14})")
BREAKS = re.compile(r"</?(p|div|br|tr|li|h[1-6]|table)\b[^>]*>", re.I)
TAGS = re.compile(r"<[^>]+>")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"“])")
MAX_SENTENCE = 700


@dataclass(frozen=True)
class Guidance:
    fiscal_year: int
    kind: str          # "dollar" (millions of USD) or "growth" (fraction)
    low: float
    high: float
    sentence: str

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2


def acceptance(raw: bytes) -> str | None:
    """SEC header acceptance time (YYYYMMDDHHMMSS, New York time) of a full submission text."""
    m = ACCEPTANCE.search(raw[:20000])
    return m.group(1).decode() if m else None


def exhibit_texts(raw: bytes) -> list[str]:
    """Plain text of every EX-99 document in a full submission text."""
    out = []
    for doc in DOC.finditer(raw):
        body = doc.group(1)
        t = DOC_TYPE.search(body)
        if not t or not t.group(1).strip().upper().startswith(b"EX-99"):
            continue
        m = DOC_TEXT.search(body)
        if m:
            out.append(plain_text(m.group(1).decode("utf-8", errors="replace")))
    return out


def plain_text(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    text = BREAKS.sub("\n", text)
    text = html.unescape(TAGS.sub(" ", text)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def sentences(text: str) -> list[str]:
    out = []
    for line in text.split("\n"):
        out.extend(s.strip() for s in SENTENCE_END.split(line) if s.strip())
    return out


def _year(token: str) -> int:
    y = int(token)
    return y + 2000 if y < 100 else y


COMPARISON = re.compile(r"\b(?:compared (?:to|with)|versus|vs\.?|over|from|relative to|than)\s+(?:the\s+)?"
                        r"(?:prior\s+|previous\s+)?(?:full[- ]year\s+|fiscal(?:\s+year)?\s+|FY\s*)?'?(?:20)?[12]\d\b",
                        re.I)


def fiscal_year(sentence: str) -> int | None:
    """The one fiscal year a sentence names, or None (no year, or several without a fiscal marker). A year named
    only as the comparison base ("compared to 2020") does not count."""
    sentence = COMPARISON.sub(" ", sentence)
    marked = {_year(m.group(1)) for m in FISCAL_YEAR.finditer(sentence)}
    marked = {y for y in marked if 2015 <= y <= 2030}
    if len(marked) == 1:
        return marked.pop()
    if marked:
        return None
    years = {int(y) for y in YEAR.findall(sentence)}
    return years.pop() if len(years) == 1 else None


def _millions(value: str, unit: str) -> float:
    v = float(value.replace(",", ""))
    return v * 1000 if unit.lower() in ("billion", "bn") else v


def amounts(sentence: str) -> tuple[str, float, float] | None:
    """(kind, low, high) of the first revenue amount in a sentence: dollars in millions, growth as a fraction."""
    m = DOLLAR_RANGE.search(sentence)
    if m:
        a, unit_a, b, unit_b = m.group(1), m.group(2) or m.group(4), m.group(3), m.group(4)
        lo, hi = _millions(a, unit_a), _millions(b, unit_b)
        return ("dollar", min(lo, hi), max(lo, hi)) if lo >= 1 and hi >= 1 else None
    m = DOLLAR_ONE.search(sentence)
    if m:
        v = _millions(m.group(1), m.group(2))
        return ("dollar", v, v) if v >= 1 else None
    m = GROWTH_RANGE.search(sentence)
    if m:
        sign = -1.0 if NEGATIVE.match(m.group(1)) else 1.0
        lo, hi = sign * float(m.group(2)) / 100, sign * float(m.group(3)) / 100
        return "growth", min(lo, hi), max(lo, hi)
    m = GROWTH_ONE.search(sentence)
    if m:
        v = (-1.0 if NEGATIVE.match(m.group(1)) else 1.0) * float(m.group(2)) / 100
        return "growth", v, v
    return None


def guidance_sentence(sentence: str) -> Guidance | None:
    if len(sentence) > MAX_SENTENCE or not REVENUE.search(sentence) or not FORWARD.search(sentence):
        return None
    if QUARTER.search(sentence) and not FULL_YEAR.search(sentence):
        return None
    fy = fiscal_year(sentence)
    if fy is None:
        return None
    a = amounts(sentence)
    if a is None:
        return None
    return Guidance(fy, a[0], a[1], a[2], sentence)


def release_guidance(texts: list[str]) -> dict[tuple[int, str], Guidance]:
    """Per (fiscal year, kind): the largest dollar midpoint, or the first growth figure, in a release."""
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


def level_change(new: Guidance, old: Guidance) -> float | None:
    if new.kind == "dollar":
        return new.mid / old.mid - 1 if old.mid > 0 else None
    return (1 + new.mid) / (1 + old.mid) - 1 if old.mid > -1 else None


def label(change: float) -> str:
    if change >= RAISE_AT:
        return "RAISE"
    if change <= CUT_AT:
        return "CUT"
    return "MAINTAIN"
