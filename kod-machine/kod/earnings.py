"""Earnings-release research note: one supported document in, a source-linked Markdown note out.

First supported workflow: an official earnings press release in HTML (for example an SEC 8-K Exhibit 99.1) whose summary table has period-labelled columns such as
"Q3 FY25  Q2 FY25  Q3 FY24". The program extracts figures with the exact table row as evidence, reads the company's own outlook, builds a KOD-WORKBENCH-v1 bundle
(so the workbench's cutoff, citation and consensus rules apply), and writes a research note. It reads supplied files (or one public URL), writes only the files you ask for,
never opens the KOD database, ledger or registry, and grants no entry permission.

Three comparisons are kept apart and always labelled: ACTUAL vs PRIOR-PERIOD ACTUAL, ACTUAL vs EARLIER COMPANY GUIDANCE, ACTUAL vs CONSENSUS (unknown unless a dated
consensus document is supplied). Nothing is guessed: an unreadable or ambiguous field stays unknown and is listed.
"""

from __future__ import annotations

import argparse
import html
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlsplit
import urllib.request
from zoneinfo import ZoneInfo

from .hashing import fmt_ts, parse_ts, sha256_bytes, sha256_text, utc_now
from . import workbench
from .workbench import _decimal_string

SCHEMA = "KOD-EARNINGS-NOTE-v1"
PARSER_VERSION = "KOD-EARNINGS-PARSER-v4"
LOCAL_URL = "https://example.invalid/local-file/"
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4}
SCALES = {"thousands": 1000, "millions": 10**6, "billions": 10**9}


def _md(value):
    """Escape untrusted text for Markdown: HTML-significant characters become entities, Markdown syntax characters are backslash-escaped, newlines are flattened."""
    text = html.escape(str(value), quote=False).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_\[\]|])", r"\\\1", text)


class EarningsError(ValueError):
    """A problem the user can fix; the message says how."""


# ---------------------------------------------------------------- document reading

# Bounds on what one table may claim. A table beyond them is listed and not read; the rest of the document still is.
MAX_TABLES = 3000
MAX_TABLE_ROWS = 5000
MAX_ROW_CELLS = 500
MAX_SPAN = 200
MAX_GRID_COLUMNS = 500
MAX_GRID_SLOTS = 250_000
SPAN_RE = re.compile(r"\s*([1-9]\d{0,3})\s*")


class TableShapeError(ValueError):
    """A table whose cells cannot be placed on one grid (overlapping spans, or beyond the bounds)."""


class _Table:
    __slots__ = ("rows", "row", "cell", "problem", "span_problem", "caption", "in_caption")

    def __init__(self):
        # problem: a bound was exceeded, so the table's cells are discarded. span_problem: its text is kept but its cells are not placed on a grid.
        self.rows, self.row, self.cell, self.problem, self.span_problem = [], None, None, None, None
        self.caption, self.in_caption = [], False


class _Page(HTMLParser):
    """Text blocks and tables. A table keeps every original cell with its colspan/rowspan and its (row, cell) position in the source; a nested table is read as a table of its own.
    A cell or row left open is closed by the next one, as browsers do."""
    BLOCKS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip, self.buf, self.blocks = 0, [], []
        self.tables, self.stack, self.seen_tables = [], [], 0

    def _flush(self):
        text = " ".join("".join(self.buf).split())
        self.buf = []
        if text and not self.stack:
            self.blocks.append(("p", text))

    def _emit_cell_text(self, t):
        parts, attrs = t.cell
        text = " ".join("".join(parts).split())
        if text:
            self.blocks.append(("p", text))
        parts.clear()
        attrs["container"] = True

    def _end_cell(self, t):
        if t.cell is not None and t.row is not None:
            if t.cell[1].get("container"):
                self._emit_cell_text(t)  # the wrapper's text after its nested table, also in reading order
            parts, attrs = t.cell
            if t.problem is None:
                t.row.append({"text": " ".join("".join(parts).split()), "cell": len(t.row) + 1,
                              **{k: v for k, v in attrs.items() if k != "container"}})
        t.cell = None

    def _end_row(self, t):
        self._end_cell(t)
        if t.row is not None and t.problem is None:
            t.rows.append(t.row)
            if len(t.rows) > MAX_TABLE_ROWS:
                t.problem, t.rows = f"more than {MAX_TABLE_ROWS} rows", []
        t.row = None

    def _end_table(self):
        t = self.stack.pop()
        self._end_row(t)
        self.seen_tables += 1
        if self.seen_tables > MAX_TABLES:
            t.problem, t.rows = t.problem or f"the document has more than {MAX_TABLES} tables", []
        caption = " ".join("".join(t.caption).split())
        if caption:
            self.blocks.append(("p", caption))  # a <caption> is the table's own caption line, read just before its rows
        self.tables.append(t)
        self.blocks.append(("t", len(self.tables) - 1))

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
            return
        t = self.stack[-1] if self.stack else None
        if tag == "table":
            self._flush()
            if t is not None and t.cell is not None:
                # A cell that wraps a nested table (a layout wrapper): its text so far is narrative, kept in reading order before the inner table.
                self._emit_cell_text(t)
            self.stack.append(_Table())
        elif tag == "caption" and t is not None:
            t.in_caption = True
        elif tag == "tr" and t is not None:
            self._end_row(t)
            t.row = []
        elif tag in ("td", "th") and t is not None:
            self._end_cell(t)
            if t.row is None:
                t.row = []
            spans = {}
            for name, value in ((n, v) for n, v in attrs if n in ("colspan", "rowspan")):
                m = SPAN_RE.fullmatch(value or "")
                if m is None or int(m.group(1)) > MAX_SPAN:
                    t.span_problem = t.span_problem or f"unsupported {name}={value!r} (allowed: whole numbers 1 to {MAX_SPAN})"
                else:
                    spans[name] = int(m.group(1))
            if len(t.row) >= MAX_ROW_CELLS:
                t.problem, t.rows = t.problem or f"a row has more than {MAX_ROW_CELLS} cells", []
            t.cell = ([], {"colspan": spans.get("colspan", 1), "rowspan": spans.get("rowspan", 1), "tag": tag})
        elif tag in self.BLOCKS:
            if t is not None and t.cell is not None:
                t.cell[0].append(" ")
            elif not self.stack:
                self._flush()

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
            return
        t = self.stack[-1] if self.stack else None
        if tag == "caption" and t is not None:
            t.in_caption = False
        elif tag in ("td", "th") and t is not None:
            self._end_cell(t)
        elif tag == "tr" and t is not None:
            self._end_row(t)
        elif tag == "table" and t is not None:
            self._end_table()
        elif tag in self.BLOCKS:
            if t is not None and t.cell is not None:
                t.cell[0].append(" ")
            elif not self.stack:
                self._flush()

    def handle_data(self, data):
        if self.skip:
            return
        t = self.stack[-1] if self.stack else None
        if t is not None and t.in_caption:
            t.caption.append(data)
        elif t is not None and t.cell is not None:
            t.cell[0].append(data)
        elif not self.stack:
            self.buf.append(data)

    def finish(self):
        while self.stack:
            self._end_table()
        self._flush()


def layout(rows):
    """Place each original cell on a logical grid the way HTML tables are laid out: left to right, skipping slots an earlier row's rowspan already covers, each cell occupying
    rowspan x colspan slots (a rowspan past the last row stops there). Returns the placed cells {text, row, cell, tag, r0, r1, c0, c1} (r1/c1 exclusive; row/cell are the
    1-based source coordinates). Raises TableShapeError when two cells claim one slot or the grid exceeds the bounds."""
    covered, placed, n = {}, [], len(rows)
    for r, row in enumerate(rows):
        c = 0
        for cell in row:
            while (r, c) in covered:
                c += 1
            c1, r1 = c + cell["colspan"], min(n, r + cell["rowspan"])
            if c1 > MAX_GRID_COLUMNS:
                raise TableShapeError(f"row {r + 1} reaches column {c1}, beyond {MAX_GRID_COLUMNS}")
            for rr in range(r, r1):
                for cc in range(c, c1):
                    if (rr, cc) in covered:
                        other = covered[(rr, cc)]
                        raise TableShapeError(f"row {r + 1} cell {cell['cell']} overlaps row {other[0]} cell {other[1]}")
                    covered[(rr, cc)] = (r + 1, cell["cell"])
            if len(covered) > MAX_GRID_SLOTS:
                raise TableShapeError(f"more than {MAX_GRID_SLOTS} grid slots")
            placed.append({"text": cell["text"], "row": r + 1, "cell": cell["cell"], "tag": cell["tag"], "r0": r, "r1": r1, "c0": c, "c1": c1})
            c = c1
    return placed


# Symbols that name one currency. '$' is not one (it is assumed to be USD only as a flagged assumption when nothing is stated) and '¥' is not one either
# (yen and yuan both use it; it is never assumed).
CURRENCY_SYMBOLS = {"US$": "USD", "U.S.$": "USD", "C$": "CAD", "CA$": "CAD", "CAD$": "CAD", "CDN$": "CAD", "A$": "AUD", "AU$": "AUD", "NZ$": "NZD", "S$": "SGD",
                    "HK$": "HKD", "€": "EUR", "£": "GBP"}
AMBIGUOUS_SYMBOLS = {"$", "¥"}
LONE_SYMBOLS = AMBIGUOUS_SYMBOLS | set(CURRENCY_SYMBOLS)


def merge_cells(cells):
    """Drop empty cells; attach a lone currency symbol ('$', 'US$', 'C$', ...) to the next cell and a lone '%' or ')' to the previous one."""
    out, pending = [], ""
    for cell in cells:
        cell = cell.strip()
        if not cell:
            continue
        if cell in LONE_SYMBOLS:
            pending = cell
        elif cell in ("%", ")", "%)") and out:
            out[-1] += cell
        else:
            out.append(pending + cell)
            pending = ""
    return out


def read_document(raw: bytes, name: str = "document") -> dict:
    """Parse an HTML earnings release into plain text lines and table rows. The returned `text` is what the workbench bundle carries and where evidence quotes are found.
    Each table also keeps its placed cells (`placed`, see layout()) or, when its cells cannot be placed, `grid_problem` saying why (its rows stay in the text)."""
    if not isinstance(raw, (bytes, bytearray)) or not raw.strip():
        raise EarningsError(f"{name}: empty file; provide an official earnings press release in HTML")
    if raw[:5] == b"%PDF-":
        raise EarningsError(f"{name}: PDF is not supported yet; provide the HTML earnings release (for SEC filers, the 8-K Exhibit 99.1 .htm file)")
    html_text = bytes(raw).decode("utf-8", "replace")
    if not re.search(r"<(html|table|p|div|body)\b", html_text, re.I):
        raise EarningsError(f"{name}: not HTML; provide the official earnings release as an .htm/.html file")
    page = _Page()
    try:
        page.feed(html_text)
        page.close()
        page.finish()
    except Exception as exc:  # malformed markup from an untrusted source
        raise EarningsError(f"{name}: the HTML could not be read ({type(exc).__name__}); provide the official release file") from exc
    lines, tables, rejected = [], [], []
    for kind, item in page.blocks:
        if kind == "p":
            lines.append(item)
            continue
        t = page.tables[item]
        if t.problem:
            rejected.append({"source_table": item + 1, "reason": t.problem})
            continue
        try:
            if t.span_problem:
                raise TableShapeError(t.span_problem)
            placed, problem = layout(t.rows), None
        except TableShapeError as exc:
            placed, problem = [], str(exc)
        by_row = {}
        for cell in placed:
            by_row.setdefault(cell["row"], []).append(cell)
        rows = []
        for r, row in enumerate(t.rows):
            merged = merge_cells([c["text"] for c in row])
            if merged:
                rows.append({"row": r + 1, "cells": merged, "line": " | ".join(merged), "placed": by_row.get(r + 1, [])})
        if rows:
            tables.append({"table": len(tables) + 1, "first_line": len(lines), "rows": rows, "placed": placed, "grid_problem": problem,
                           "width": max((c["c1"] for c in placed), default=0)})
            lines.extend(row["line"] for row in rows)
    return {"name": name, "raw_sha256": sha256_bytes(bytes(raw)), "bytes": len(raw), "lines": lines, "text": "\n".join(lines), "tables": tables,
            "rejected_tables": rejected}


# ---------------------------------------------------------------- figures

PERIOD_RE = re.compile(r"^Q([1-4])\s*(FY|fy|Fiscal|fiscal|FISCAL)?\s*'?(\d{2}|\d{4})$")
# A change column: 'Y/Y', 'Y-O-Y Change', 'Organic Y-O-Y Change', '% Change', '% Chg', 'Change %', 'Growth', 'Increase (Decrease)', 'Variance'.
_CHANGE_WORD = r"(?:y/y|q/q|yoy|qoq|y-o-y|q-o-q|vpy)"
CHANGE_RE = re.compile(rf"^(?:(?:organic|reported|constant[- ]currency|as reported)\s+)?(?:{_CHANGE_WORD}(?:\s+(?:%\s*)?(?:change|chg\.?|growth))?"
                       r"|%\s*(?:change|chg\.?|growth|variance)|(?:change|chg\.?|growth|variance)(?:\s*%)?|increase\s*\(decrease\)|favorable\s*\(unfavorable\)"
                       r"|(?:bps|basis points?)\s+change)$", re.I)
SKIP_COLUMN_RE = re.compile(r"^(?:ytd|year[- ]to[- ]date)\b", re.I)  # a year-to-date column beside quarter columns: neither a quarter nor a change
DATE_RE = re.compile(r"^([A-Za-z]{3,9})\.?\s*(\d{1,2}),\s*(\d{4})$")
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
DURATIONS = {"three": "quarter", "six": "6 months", "nine": "9 months", "twelve": "12 months", "year": "12 months", "years": "12 months", "quarter": "quarter",
             "quarters": "quarter"}
DUR_RE = re.compile(r"\b(?:(three|six|nine|twelve)\s+months|(?:fiscal\s+)?(years?|quarters?)"
                    r"|(thirteen|twenty[- ]six|thirty[- ]nine|fifty[- ]two|fifty[- ]three|13|26|39|52|53)[- ]weeks?(?:\s+periods?)?)\s+ended\b", re.I)
# Week-based periods: only the four standard lengths. A 12-, 16- or 17-week quarter is not called a quarter here (its length differs from the year-ago one).
WEEKS = {"thirteen": "quarter", "13": "quarter", "twenty six": "6 months", "26": "6 months", "thirty nine": "9 months", "39": "9 months",
         "fifty two": "12 months", "fifty three": "12 months", "52": "12 months", "53": "12 months"}
BASIS_RE = re.compile(r"^(non-gaap|gaap)\b", re.I)


def _full_year(text: str) -> int:
    """The year of a 'Qn FYyy' / 'Qn yyyy' label as four digits. Two-digit years are read as 20yy: this reader is for releases from 2000 to 2099."""
    return int(text) if len(text) == 4 else 2000 + int(text)


def qn_period(text: str):
    m = PERIOD_RE.match(text.strip())
    if not m:
        return None
    year, fiscal = m.group(3), bool(m.group(2))
    label = f"Q{m.group(1)} FY{year[-2:]}" if fiscal else f"Q{m.group(1)} {_full_year(year)}"
    return {"label": label, "kind": "quarter", "q": int(m.group(1)), "yy": int(year[-2:]), "year": _full_year(year), "fiscal": fiscal, "end": None}


def normalize_period(label: str):
    """Kept for callers that only need (label, quarter, two-digit year) of a 'Qn FYyy' / 'Qn yyyy' label."""
    p = qn_period(label)
    return (p["label"], p["q"], p["yy"]) if p else None


def parse_date(text: str):
    m = DATE_RE.match(text.strip())
    month = MONTHS.get(m.group(1)[:3].lower()) if m else None
    if not m or month is None:
        return None
    try:
        return date(int(m.group(3)), month, int(m.group(2)))
    except ValueError:
        return None


def duration_of(text: str):
    m = DUR_RE.search(text or "")
    if not m:
        return None
    if m.group(3):
        return WEEKS[m.group(3).lower().replace("-", " ")]
    return DURATIONS[(m.group(1) or m.group(2)).lower()]


def dated_period(kind: str, end: date):
    return {"label": f"{kind} ended {end.isoformat()}", "kind": kind, "q": None, "yy": None, "year": None, "fiscal": None, "end": end}


def earlier(other: dict, cur: dict):
    """True when `other` is a genuinely earlier period than `cur` of the same duration kind and the same labelling (both dated, or both fiscal / both calendar quarter labels);
    False when it is the same or a later one; None when the two cannot be ordered."""
    if cur["kind"] != other["kind"]:
        return None
    if cur["end"] and other["end"]:
        return other["end"] < cur["end"]
    if cur["q"] and other["q"] and cur["fiscal"] == other["fiscal"]:
        return (other["year"], other["q"]) < (cur["year"], cur["q"])
    return None


def relation(cur: dict, other: dict):
    """How an earlier `other` relates to `cur`: YEAR_OVER_YEAR, SEQUENTIAL or OTHER. None unless `other` is a genuinely earlier, comparable period (see earlier()): a later
    column is never a prior period, and different duration kinds or label styles are never compared."""
    if earlier(other, cur) is not True:
        return None
    if cur["end"] and other["end"]:
        days = (cur["end"] - other["end"]).days
        if 350 <= days <= 380:
            return "YEAR_OVER_YEAR"
        return "SEQUENTIAL" if cur["kind"] == "quarter" and 75 <= days <= 105 else "OTHER"
    if other["q"] == cur["q"] and other["year"] == cur["year"] - 1:
        return "YEAR_OVER_YEAR"
    if (cur["q"] > 1 and other["q"] == cur["q"] - 1 and other["year"] == cur["year"]) or (cur["q"] == 1 and other["q"] == 4 and other["year"] == cur["year"] - 1):
        return "SEQUENTIAL"
    return "OTHER"


NUMBER_RE = re.compile(r"(?P<o1>\()?\s*(?P<sym>US\$|U\.S\.\$|CDN\$|CAD\$|CA\$|C\$|AU\$|A\$|NZ\$|HK\$|S\$|\$|€|£|¥)?\s*(?P<o2>\()?\s*"
                       r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<p1>%)?\s*(?P<c>\))?\s*(?P<p2>%)?")


def parse_number(cell: str):
    """(Decimal, currency symbol or None, 'percent' or None) from '$12,345', '(1,234)', '$(1,234)', '74.6%', 'C$1.20'; None if the cell is not one plain number.
    Parentheses mean a negative value and must balance; thousands separators must be regular."""
    m = NUMBER_RE.fullmatch(cell.strip())
    if m is None:
        return None
    opened = (m["o1"] is not None) + (m["o2"] is not None)
    if opened > 1 or opened != (m["c"] is not None) or (m["p1"] and m["p2"]):
        return None
    value = Decimal(m["num"].replace(",", ""))
    return (-value if opened and value else value), m["sym"], ("percent" if (m["p1"] or m["p2"]) else None)


_NI = r"net\s+(?:income|earnings|loss|income\s+\(loss\)|earnings\s+\(loss\)|\(loss\)\s+income|\(loss\)\s+earnings)"
_EARN = r"(?:net\s+)?(?:earnings|income|eps|loss|earnings\s+\(loss\)|\(loss\)\s+earnings|income\s+\(loss\)|\(loss\)\s+income)"
# 'attributable to <the company>': not to non-controlling or minority interests, and not to common or preferred holders (after preferred dividends).
_TO_COMPANY = (r"\s+attributable\s+to\s+(?!(?:the\s+)?(?:non-?controlling|noncontrolling|minority|redeemable|common|preferred|participating|class\b))"
               r"(?!.*\b(?:common|ordinary|preferred)\s+(?:share|stock)holders)(?!.*[-–—]\s*(?:basic|diluted)$).{2,80}?")
# Earnings per share is per common or ordinary share whoever it is 'attributable to' (classes, ordinary shareholders, the company), except non-controlling interests.
_TO_HOLDERS = r"(?:\s+attributable\s+to\s+(?!(?:the\s+)?(?:non-?controlling|noncontrolling|minority))[^:]{2,100}?)"
METRICS = (
    ("revenue", re.compile(r"^(total )?(net )?(operating )?(revenues?|sales)(, net)?$|^total net (revenues?|sales)$")),
    ("gross_margin", re.compile(r"^gross (profit )?margin$")),
    ("operating_expenses", re.compile(r"^(total )?operating expenses$")),
    ("operating_income", re.compile(r"^(income from operations|operating income)$")),
    ("net_income", re.compile(rf"^{_NI}$")),
    ("net_income_attributable", re.compile(rf"^{_NI}{_TO_COMPANY}$")),
    ("eps_diluted", re.compile(r"^(diluted (earnings|eps)( per (common )?share)?|(earnings|net income) per diluted share|diluted net income per share)$"
                               r"|^eps\s*[-–—]\s*diluted$"
                               rf"|^{_EARN}\s+per\s+diluted\s+(?:common\s+|ordinary\s+)?share$"
                               rf"|^{_EARN}\s+per\s+(?:common\s+|ordinary\s+)?share{_TO_HOLDERS}?\s*[-–—,]?\s*assuming\s+dilution$"
                               rf"|^{_EARN}\s+per\s+(?:common\s+|ordinary\s+)?share{_TO_HOLDERS}?\s*\(\s*(?:basic\s+and\s+)?diluted\s*\)$"
                               rf"|^(?:diluted|basic\s+and\s+diluted|basic\s*&\s*diluted)\s+{_EARN}\s+per\s+(?:common\s+)?share(?:\s+of\s+common\s+stock)?(?:{_TO_COMPANY})?$"
                               rf"|^{_EARN}\s+per\s+(?:common\s+|ordinary\s+)?share{_TO_HOLDERS}?,?\s*[-–—]?\s*(?:basic\s+and\s+)?diluted$")),
)
# A loss label prints its amount without a sign as often as with one; either way the amount is a loss.
LOSS_LABEL = re.compile(r"^(?:basic\s+and\s+diluted\s+|diluted\s+)?net\s+loss\b|^(?:basic\s+and\s+diluted|diluted)\s+loss\s+per\b|^loss\s+per\s+(?:common\s+)?share\b")
EXCLUDED_LABEL = re.compile(r"\b(?:continuing|discontinued|adjusted|pro\s+forma|excluding|before)\b")
COMPACT = {"revenue": "revenue", "operatingincome": "operating_income", "netincome": "net_income", "dilutedearningspershare": "eps_diluted"}
SCALE_WORDS = {"m": "millions", "million": "millions", "millions": "millions", "thousand": "thousands", "thousands": "thousands", "billion": "billions", "billions": "billions"}


def unit_scale(text: str):
    """'in millions', '($ in thousands)', '(Millions except per share amounts)', '(Dollars in millions)', '($M)'; None if the text states no scale."""
    text = text or ""
    m = (re.search(r"\bin\s+(thousands|millions|billions)\b", text, re.I) or re.search(r"\(\s*(?:\$\s*|U\.?S\.?\s*\$\s*)?(thousands|millions|billions)\b", text, re.I)
         or re.search(r"\(\s*\$\s*(m)\s*\)", text, re.I)
         # '$ millions (unless otherwise noted)', '$, millions except EPS', 'USD millions'
         or re.search(r"(?:^|[\s(])(?:\$|US\$|USD)\s*,?\s*(thousands|millions|billions)\b", text, re.I))
    if m:
        return SCALE_WORDS[m.group(1).lower()]
    if re.search(r"\(\s*(?:in\s+)?\$\s*000'?s?\s*\)|\bin\s+\$\s*000'?s\b", text, re.I):   # '($000s)', 'in $000s'
        return "thousands"
    return None


AS_REPORTED = re.compile(r"^(?:as\s+reported|reported|gaap)\s*(?:\((?:gaap|u\.s\.\s+gaap)\))?$|^(?:adjusted|non-gaap)\s*(?:\((?:non-gaap)\))?$", re.I)


def metric_for(label: str, section: str | None = None):
    """(metric, basis-from-label or None, scale-from-label or None), or None. Footnote marks, '(1)', '($M)' and a leading GAAP / Non-GAAP are read off the label first."""
    s = re.sub(r"[*†‡]+$", "", label.strip())
    s = re.sub(r"(?:\s*\(\d+\))+$", "", s)
    scale = None
    m = re.search(r"\(\s*\$?\s*(?:in\s+)?(m|millions?|thousands?|billions?)\s*\)", s, re.I)
    if m:
        scale = SCALE_WORDS[m.group(1).lower()]
        s = (s[:m.start()] + s[m.end():]).strip()
    basis = None
    m = BASIS_RE.match(s)
    if m:
        basis = "NON-GAAP" if m.group(1).lower().startswith("non") else "GAAP"
        s = s[m.end():].strip()
    m = re.search(r"\s*\((non-gaap|gaap)\)$", s, re.I) or re.search(r"\s+on\s+a\s+(non-gaap|gaap)\s+basis$", s, re.I)
    if m and basis is None:
        basis = "NON-GAAP" if m.group(1).lower().startswith("non") else "GAAP"   # 'Net income (GAAP)', 'Net loss on a GAAP basis'
        s = s[:m.start()].strip()
    s = re.sub(r"\s+", " ", s.lower()).strip()
    if section and AS_REPORTED.match(s):
        # 'Net Sales' over 'As Reported (GAAP) | $2,137' and 'Adjusted (Non-GAAP) | ...': the heading names the metric, the row its basis.
        heading = metric_for(section)
        if heading and heading[0] in ("revenue", "operating_income", "net_income", "net_income_attributable", "eps_diluted"):
            return heading[0], ("NON-GAAP" if re.match(r"adjusted|non-gaap", s) else "GAAP"), scale
        return None
    eps_section = bool(section and re.search(r"\bper\s+(?:common\s+|ordinary\s+)?share\b", section) and not re.search(r"shares\s+used|weighted|average", section))
    if s in ("diluted", "basic and diluted", "basic & diluted", "diluted eps") and eps_section:
        return "eps_diluted", basis, scale
    if eps_section and "diluted" in section and "basic" not in section and re.fullmatch(rf"{_NI}|total", s):
        return "eps_diluted", basis, scale     # 'Diluted earnings per share attributable to X:' over a 'Net earnings | $4.16' row
    if eps_section and re.fullmatch(rf"{_NI}|{_NI}{_TO_COMPANY}", s):
        return None                             # 'Net income' under a basic or per-share heading is a per-share amount, not net income
    if EXCLUDED_LABEL.search(s):
        return None
    for name, pattern in METRICS:
        if pattern.match(s):
            return name, basis, scale
    return None


def _basis_in(lines):
    for line in reversed(lines):
        m = BASIS_RE.match(line.strip())
        if m and len(line) < 80:
            return "NON-GAAP" if m.group(1).lower().startswith("non") else "GAAP"
    return None


def _month_day(text: str):
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s*$", text.strip())
    month = MONTHS.get(m.group(1)[:3].lower()) if m else None
    return (month, int(m.group(2))) if m else None


# ---------------------------------------------------------------- reporting currency

# A sentence ends at '.', ';', '!' or '?' followed by space, but not after an initial such as the 'S.' of 'U.S.'.
SENTENCE_BREAK = re.compile(r"(?<=[.;!?])(?<![A-Z]\.)\s+")

_NAME_CODES = (
    (r"(?:u\.\s?s\.|us|united\s+states|american)\s+dollars?", "USD"), (r"canadian\s+dollars?", "CAD"), (r"australian\s+dollars?", "AUD"),
    (r"new\s+zealand\s+dollars?", "NZD"), (r"singapore\s+dollars?", "SGD"), (r"hong\s+kong\s+dollars?", "HKD"), (r"euros?", "EUR"),
    (r"pounds?\s+sterling|british\s+pounds?|sterling", "GBP"), (r"(?:japanese\s+)?yen", "JPY"), (r"renminbi|chinese\s+yuan|yuan|rmb", "CNY"),
    (r"(?:indonesian\s+)?rupiah", "IDR"), (r"swiss\s+francs?", "CHF"),
)
_DESIGNATION = re.compile("|".join(rf"(?P<n{i}>\b(?:{rx})\b)" for i, (rx, _) in enumerate(_NAME_CODES)), re.I)
_CODE = re.compile(r"\b(USD|CAD|AUD|NZD|SGD|HKD|EUR|GBP|JPY|CNY|RMB|IDR|CHF)\b")
_SYMBOL = re.compile(r"(?<![A-Za-z])(U\.S\.\$|US\$|CDN\$|CAD\$|CA\$|C\$|AU\$|A\$|NZ\$|HK\$|S\$)|[€£]")
_SUBJECT = re.compile(r"\b(?:amounts|figures|numbers|values|results|financial\s+(?:statements|information|results|data|highlights))\b", re.I)
_DECLARING = re.compile(r"(?:\b(?:expressed|reported|presented|stated|shown|are|is|were|have\s+been)\s+in|\b(?:are|is|were)\s+denominated\s+in"
                        r"|\b(?:amounts|figures|numbers)(?:\s+[\w-]+){0,4}\s+in)"
                        r"\s+(?:(?:millions|thousands|billions)\s+of\s+)?$", re.I)
_UNLESS = re.compile(r"\bunless\s+otherwise\s+(?:noted|stated|indicated|specified)\b", re.I)
_NOT_A_STATEMENT = re.compile(r"\b(?:terms|exchange|constant\s+currency|equivalent|translated|translation|converted|conversion)\b", re.I)
_CAPTION_VERBS = re.compile(r"\b(?:grew|increased|decreased|rose|fell|declined|repaid|issued|paid|raised|denominated|terms|exchange|translation|compared)\b", re.I)


def _designations(text: str):
    """(ISO code, span start, quoted text) for every currency named in the text: names ('Canadian dollars', 'Renminbi'), ISO codes and one-currency symbols."""
    found = []
    for m in _DESIGNATION.finditer(text):
        index = int(next(k for k, v in m.groupdict().items() if v)[1:])
        found.append((_NAME_CODES[index][1], m.start(), m.group(0)))
    for m in _CODE.finditer(text):
        found.append(("CNY" if m.group(1) == "RMB" else m.group(1), m.start(), m.group(0)))
    for m in _SYMBOL.finditer(text):
        found.append((CURRENCY_SYMBOLS[m.group(0)], m.start(), m.group(0)))
    return found


def is_caption(text: str) -> bool:
    """A units caption such as '(millions of Canadian dollars, except per share amounts)' or '(C$ millions)': short, parenthesised or naming a scale,
    with no figures and no narrative verbs."""
    t = text.strip()
    if not t or len(t) > 160 or _CAPTION_VERBS.search(t) or re.search(r"\d", re.sub(r"\(\d\)", "", t)):
        return False
    return t.startswith("(") or re.search(r"\b(?:thousands|millions|billions)\b", t, re.I) is not None


def currency_statements(lines, captions_only=()) -> dict:
    """Explicit reporting-currency statements as {ISO code: first quote}. Two forms count: a units caption that names a currency ('(in millions of U.S.
    dollars)', '(C$ millions)', '(Renminbi in millions)'), and a sentence that declares the currency of the amounts ('All amounts are in Canadian dollars',
    'Financial results are reported in euros', 'All figures in Canadian dollars unless otherwise noted'). A currency merely mentioned in a sentence ('notes
    denominated in euros', 'sales grew 5% in Canadian dollars', 'in U.S. dollar terms', 'constant currency') is not a statement. '$' and '¥' alone never are."""
    found = {}
    for line in captions_only:
        if is_caption(line):
            for code, _, quote in _designations(line):
                found.setdefault(code, line.strip())
    for line in lines:
        if is_caption(line):
            for code, _, quote in _designations(line):
                found.setdefault(code, line.strip())
            continue
        for sentence in SENTENCE_BREAK.split(line):
            if _NOT_A_STATEMENT.search(sentence):
                continue
            for code, start, quote in _designations(sentence):
                before = sentence[max(0, start - 120):start]
                if (_SUBJECT.search(before) and _DECLARING.search(before)) or (_UNLESS.search(sentence) and re.search(r"\bin\s+(?:(?:millions|thousands|billions)\s+of\s+)?$", before, re.I)):
                    found.setdefault(code, sentence.strip()[:300])
    return found


ISO_4217 = frozenset("""AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD CAD CDF CHF CLP CNY COP CRC CUP CVE
CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD
KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF
SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND VUV WST XAF XCD XOF XPF YER ZAR ZMW
ZWL""".split())


def analyst_currency(value):
    """An analyst's reporting-currency decision, from an ISO code or {currency, recorded_by, recorded_at, rationale}; returned with its provenance, or None."""
    if value is None:
        return None
    if isinstance(value, str):
        value = {"currency": value}
    code = str(value.get("currency") or "").strip().upper()
    if code not in ISO_4217:
        raise EarningsError(f"the reporting-currency record {code or '(empty)'!r} is not an ISO 4217 currency code (for example CAD, USD, EUR)")
    return {"currency": code, "source": "analyst override", "recorded_by": value.get("recorded_by"), "recorded_at": value.get("recorded_at"), "rationale": value.get("rationale")}


def scope_currency(table_found: dict, doc_found: dict, override: dict | None, table_symbols: dict | None = None) -> dict:
    """The currency of '$' and symbol-less monetary figures in one table: the table's own caption statement or the one-currency symbol printed in its cells,
    else the document's statement, else the analyst's record. Several currencies in the deciding scope, symbols that contradict the caption, or a record that
    contradicts the evidence leave it unresolved ('conflict' says why). None when nothing is stated, printed or recorded."""
    table_symbols = table_symbols or {}
    if len(table_found) > 1:
        return _currency_conflict("the table caption states several currencies: " + "; ".join(f"'{q}'" for q in table_found.values()))
    if table_found and table_symbols and set(table_symbols) - set(table_found):
        return _currency_conflict(f"the table prints {', '.join(sorted(table_symbols.values()))} but its caption states '{next(iter(table_found.values()))}'")
    if not table_found and len(table_symbols) > 1:
        return _currency_conflict("the table prints several currency symbols: " + ", ".join(sorted(table_symbols.values())))
    for name, found in (("TABLE_STATEMENT", table_found), ("TABLE_SYMBOL", {} if table_found else table_symbols), ("DOCUMENT_STATEMENT", doc_found)):
        if not found:
            continue
        if len(found) > 1:
            return _currency_conflict("the release states several currencies: " + "; ".join(f"'{q}'" for q in found.values()))
        (code, quote), = found.items()
        if override and override["currency"] != code:
            return {**_currency_conflict(f"analyst override {override['currency']} contradicts '{quote}'"), "quote": quote}
        return {"currency": code, "basis": name + (" (analyst override agrees)" if override else ""), "quote": quote, "conflict": None}
    if override:
        return {"currency": override["currency"], "basis": "ANALYST_OVERRIDE", "quote": None, "conflict": None}
    return {"currency": None, "basis": None, "quote": None, "conflict": None}


def _currency_conflict(reason):
    return {"currency": None, "basis": None, "quote": None, "conflict": reason}


ASSUMED = "ASSUMED_FROM_$_SIGN"


def _fact_currency(metric, symbol, table_dollar, scope):
    """(currency, basis, quote, flags) of one figure. Margins have no currency. In a table whose currency is in conflict no monetary figure gets one. A
    one-currency symbol printed with the figure is its own evidence; otherwise the table's scope decides; with nothing stated, '$' is assumed to mean US dollars
    and flagged, and '¥' (yen or yuan) stays unresolved."""
    if metric == "gross_margin":
        return None, None, None, []
    if scope["conflict"]:
        return None, None, None, ["CURRENCY_UNRESOLVED"]
    if symbol in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[symbol], "CELL_SYMBOL", symbol, []
    if scope["currency"]:
        return scope["currency"], scope["basis"], scope["quote"], []
    if symbol == "¥":
        return None, None, None, ["CURRENCY_UNRESOLVED"]
    if symbol == "$" or (symbol is None and table_dollar and metric != "eps_diluted"):
        return "USD", ASSUMED, "$", ["CURRENCY_ASSUMED_USD_FROM_$_SIGN"]
    return None, None, None, []


GENERIC_DOLLAR = re.compile(r"(?<![A-Za-z.])\$")


def _layout_table(table) -> bool:
    """A table used for layout (a letterhead, a boxed paragraph): no period header and no row with two or more numbers."""
    for row in table["rows"]:
        if any(_header_kind(c) for c in row["cells"][1:]) or sum(parse_number(c) is not None for c in row["cells"]) >= 2:
            return False
    return True


def _document_lines(doc: dict) -> list:
    """The release's narrative: paragraphs and layout tables (not data tables)."""
    in_table = set()
    for t in doc["tables"]:
        if not _layout_table(t):
            in_table.update(range(t["first_line"], t["first_line"] + len(t["rows"])))
    return [line for i, line in enumerate(doc["lines"]) if i not in in_table]


def document_currency_statements(doc: dict) -> dict:
    """Statements in the narrative; a caption split over two lines by a <br> is also read joined (as a caption only, never as a sentence)."""
    lines = _document_lines(doc)
    return currency_statements(lines, [a + " " + b for a, b in zip(lines, lines[1:])])


# ---------------------------------------------------------------- table geometry

def _cell_ref(c):
    return {"row": c["row"], "cell": c["cell"], "columns": [c["c0"], c["c1"]]}


def _header_kind(text: str):
    """'change', 'qn', 'date' or 'year' for a header token, else None. A bare number is a year only between 1990 and 2100 (a store count of 1205 is not)."""
    if CHANGE_RE.match(text):
        return "change"
    if SKIP_COLUMN_RE.match(text):
        return "skip"
    if qn_period(text):
        return "qn"
    if parse_date(text):
        return "date"
    return "year" if re.fullmatch(r"\d{4}", text) and 1990 <= int(text) <= 2100 else None


def _merge_with_cells(cells):
    """merge_cells over placed cells, keeping the source cells of each merged token."""
    out, pending = [], None
    for cell in cells:
        text = cell["text"].strip()
        if not text:
            continue
        if text in LONE_SYMBOLS:
            pending = (text, cell)
        elif text in ("%", ")", "%)") and out:
            out[-1] = (out[-1][0] + text, out[-1][1] + [cell])
        elif pending:
            out.append((pending[0] + text, [pending[1], cell]))
            pending = None
        else:
            out.append((text, [cell]))
    return out


def _heading_for(headings: list, cell: dict):
    """The duration heading above a header cell: a table-wide heading (the only heading of its row, written without a colspan), else the one heading whose columns contain the
    cell's columns. Returns (heading or None, reason it is unknown)."""
    if not headings:
        return None, "no 'Three/Twelve Months Ended' heading above it"
    wide = [h for h in headings if h["wide"]]
    if wide:
        return wide[0], None
    inside = [h for h in headings if h["c0"] <= cell["c0"] and cell["c1"] <= h["c1"]]
    if len(inside) == 1:
        return inside[0], None
    if any(h["c0"] < cell["c1"] and cell["c0"] < h["c1"] for h in headings):
        return None, "it straddles two duration headings"
    return None, "no duration heading spans its columns"


DANGLING = LONE_SYMBOLS | {"%", ")", "%)"}
PARTIAL_HEADING_RE = re.compile(r"^(?:for\s+the\s+)?(?:three|six|nine|twelve|thirteen|twenty[- ]six|thirty[- ]nine|fifty[- ]two|\d+)?\s*(?:quarters?|months|weeks?|years?|fiscal\s+years?)"
                                r"(?:\s+periods?)?$", re.I)
PER_SHARE_TABLE = re.compile(r"^\(?\s*(?:amounts\s+)?per\s+(?:common\s+|ordinary\s+)?share(?:\s+(?:data|amounts|information))?\s*\)?$", re.I)
MONTH_DAY_RE = re.compile(r"^[A-Za-z]{3,9}\.?\s+\d{1,2},?$")
# A heading that opens a breakdown (segments, categories, regions): rows below it in the same table are parts of the company, not the company figure.
BREAKDOWN_RE = re.compile(r"\b(segments?|reportable|by\s+(?:category|product|region|geograph\w*|market|business|customer|end\s+market)|category\s+information)\b", re.I)


def _read_grid(row: dict, columns: list, covering: list):
    """A data row read by the table's geometry: (label, value text per column (None if blank), value cells per column), or None when its cells do not sit under the header
    columns. Every non-empty cell must lie left of the first column (the label) or wholly inside exactly one column; a column holds at most one value and never only a lone
    '$', '%' or ')'; the row must reach the last column (a short row may have lost a cell); no non-empty cell from an earlier row may span down into a column."""
    first, last = min(c["c0"] for c in columns), max(c["c1"] for c in columns)
    own = row["placed"]
    if not own or max(c["c1"] for c in own) < last:
        return None
    if any(c["text"] and c["c1"] > first for c in covering):
        return None
    ancestors = [c for c in covering if c["text"] and c["c1"] <= first]  # a rowspan label above (e.g. 'Non-GAAP') belongs to this row's label
    label_cells, inside = [], [[] for _ in columns]
    for cell in own:
        if not cell["text"]:
            continue
        if cell["c1"] <= first:
            label_cells.append(cell)
            continue
        hit = [i for i, col in enumerate(columns) if col["c0"] <= cell["c0"] and cell["c1"] <= col["c1"]]
        if not hit and cell["text"].strip() in (")", "%", ")%", "%)"):
            # A closing parenthesis or % sign printed in its own cell just right of a number column belongs to that number: the nearest column ending at or
            # before it, with no other column starting in between.
            left = [i for i, col in enumerate(columns) if col["c1"] <= cell["c0"]]
            nearest = max(left, key=lambda i: columns[i]["c1"]) if left else None
            if nearest is not None and not any(columns[nearest]["c1"] <= col["c0"] < cell["c1"] for col in columns):
                hit = [nearest]
        if len(hit) != 1:
            return None
        inside[hit[0]].append(cell)
    texts = []
    for cells in inside:
        merged = merge_cells([c["text"] for c in cells])
        if len(merged) > 1 or (cells and not merged) or (merged and merged[0] in DANGLING):
            return None
        texts.append(merged[0] if merged else None)
    return " ".join(merge_cells([c["text"] for c in label_cells])), texts, inside, ancestors + label_cells


def extract_table_facts(doc: dict, currency_override=None) -> tuple[list, list]:
    """Facts from tables whose columns are periods (a 'Qn FYyy' / 'Qn yyyy' label, or a date under a 'Three/Twelve Months Ended' heading, or a year under 'Three Months Ended <Month day>,')
    and from tables with the periods down the rows (metric names across the top). One value, one period, one basis per fact; the table row is the evidence.

    Column meaning comes from the table's geometry: each header cell's columns, and the duration heading whose columns contain them (see layout()). A value belongs to the column
    whose columns contain its cell. A table written without any colspan/rowspan whose rows do not line up with the header is read in printed cell order, and only when a
    row has exactly one value per header column. Anything else is skipped and listed. Returns (facts, issues)."""
    facts, issues = [], []
    lines = doc["lines"]
    override = analyst_currency(currency_override)
    doc_found = document_currency_statements(doc)
    for rejected in doc.get("rejected_tables", []):
        issues.append({"code": "TABLE_NOT_READ", "where": f"source table {rejected['source_table']}", "detail": rejected["reason"] + "; its contents are not read"})
    for table in doc["tables"]:
        where_t = f"table {table['table']}"
        ctx = lines[max(0, table["first_line"] - 4):table["first_line"]]
        if table["grid_problem"]:
            if any(metric_for(r["cells"][0]) or any(_header_kind(c) in ("qn", "date") for c in r["cells"]) for r in table["rows"]):
                issues.append({"code": "TABLE_LAYOUT_REJECTED", "where": where_t, "detail": f"its cells cannot be placed on one grid ({table['grid_problem']}); its figures are not read"})
            continue
        basis = _basis_in(ctx) or "UNSTATED"
        scale = unit_scale(" ".join(ctx[-3:]))
        # The table's own currency evidence: its caption cells (and a caption line directly above it), and the one-currency symbols printed in its cells.
        captions = [line for line in ctx[-2:] if is_caption(line)] + [r["cells"][0] for r in table["rows"] if r["cells"] and (len(r["cells"]) == 1 or is_caption(r["cells"][0]))]
        symbols = {}
        for r in table["rows"]:
            for c in r["cells"][1:]:
                num = parse_number(c)
                if num and num[1] in CURRENCY_SYMBOLS:
                    symbols.setdefault(CURRENCY_SYMBOLS[num[1]], num[1])
        scope = scope_currency(currency_statements(captions), doc_found, override, symbols)
        if scope["conflict"]:
            issues.append({"code": "CURRENCY_CONFLICT", "where": where_t, "detail": scope["conflict"] + "; its monetary figures have no currency"})
        simple = all(c["c1"] - c["c0"] == 1 and c["r1"] - c["r0"] == 1 for c in table["placed"])
        covering_by_row = {}
        for c in table["placed"]:
            for r in range(c["r0"] + 1, c["r1"]):  # bounded by the grid's slot count
                covering_by_row.setdefault(r, []).append(c)
        section, headings, columns, transposed, skipped, misaligned, by_order, basis_conflicts = None, [], None, None, 0, 0, 0, 0
        partial, month_days, per_share_table = None, [], False
        # A duration heading printed as a caption just above the table ('Three Months Ended June 30,'), used only for a header of bare years with no heading of its own.
        above = [line for line in ctx[-3:] if duration_of(line) and _month_day(line) and len(line) < 120]
        context_heading = ({"text": above[0], "c0": 0, "c1": 0, "wide": True, "ref": {"row": 0, "cell": None, "columns": [0, 0], "caption_line": above[0]}}
                           if len(above) == 1 else None)
        table_start, breakdown, breakdown_rows = len(facts), None, 0
        unknown = {}
        table_dollar = any(GENERIC_DOLLAR.search(c) for r in table["rows"] for c in r["cells"])
        for row in table["rows"]:
            cells = row["cells"]
            where = f"table {table['table']} row {row['row']}"
            own = [c for c in row["placed"] if c["text"]]
            covering = covering_by_row.get(row["row"] - 1, [])
            if len(cells) == 1:
                t = cells[0]
                if BREAKDOWN_RE.search(t):
                    breakdown = t
                if BASIS_RE.match(t) and len(t) < 40:
                    basis = "NON-GAAP" if t.lower().startswith("non") else "GAAP"
                elif duration_of(t) and own:
                    # The only cell of its row: it heads every column of the header row below it, whatever its colspan.
                    c = own[0]
                    headings = [{"text": t, "c0": c["c0"], "c1": c["c1"], "wide": True, "ref": _cell_ref(c)}]
                elif unit_scale(t) and not t.endswith(":"):
                    scale = unit_scale(t)
                elif PER_SHARE_TABLE.match(t.strip()):
                    per_share_table = True
                elif t.endswith(":"):
                    section = t.rstrip(":").strip().lower()
                elif re.search(r"\bper\s+(?:common\s+|ordinary\s+)?share\b", t, re.I) and len(t) < 160 and not re.search(r"\d", t):
                    section = t.strip().lower()   # 'Diluted Earnings (Loss) Per Share' over 'Basic' / 'Diluted' rows
                elif len(t) < 80 and not re.search(r"\d", t):
                    section = t.strip().lower()   # 'Net Sales' over 'As Reported (GAAP)' / 'Adjusted (Non-GAAP)' rows; any other heading ends that block
                elif unit_scale(t):
                    scale = unit_scale(t)
                continue
            if own and all(duration_of(c["text"]) for c in own):
                headings, partial = [{"text": c["text"], "c0": c["c0"], "c1": c["c1"], "wide": False, "ref": _cell_ref(c)} for c in own], None
                continue
            if len(own) >= 2 and not duration_of(own[0]["text"]) and all(duration_of(c["text"]) for c in own[1:]) and own[0]["c1"] <= min(c["c0"] for c in own[1:]):
                # '(Dollar amounts in millions) | For the Three Months Ended June 30,': a caption beside the duration headings.
                headings, partial = [{"text": c["text"], "c0": c["c0"], "c1": c["c1"], "wide": len(own) == 2, "ref": _cell_ref(c)} for c in own[1:]], None
                scale = unit_scale(own[0]["text"]) or scale
                continue
            if partial and own and all(c["text"].lower().startswith("ended") and len([p for p in partial if p["c0"] <= c["c0"] and c["c1"] <= p["c1"]]) == 1 for c in own):
                # A heading written over two rows ('For the quarter' / 'ended June 30,'): each part joins the part above it.
                joined = []
                for c in own:
                    top = next(p for p in partial if p["c0"] <= c["c0"] and c["c1"] <= p["c1"])
                    joined.append({"text": f"{top['text']} {c['text']}", "c0": top["c0"], "c1": top["c1"], "wide": False, "ref": top["ref"], "ref2": _cell_ref(c)})
                partial = None
                if all(duration_of(h["text"]) for h in joined):
                    headings = joined
                continue
            if own and all(PARTIAL_HEADING_RE.search(c["text"]) and not re.search(r"\d", c["text"]) and not duration_of(c["text"]) for c in own):
                partial = [{"text": c["text"], "c0": c["c0"], "c1": c["c1"], "ref": _cell_ref(c)} for c in own]
                continue
            partial = None
            md_cells = [c for c in own if MONTH_DAY_RE.match(c["text"].strip())]
            if len(md_cells) >= 2 and all(MONTH_DAY_RE.match(c["text"].strip()) for c in own[1:]):
                # Month and day on one row ('June 30, | March 31,'), the years on the next: each year takes the month and day above it.
                month_days = md_cells
                continue
            kinds = [_header_kind(c["text"]) for c in own]
            years = [c["text"] for c, k in zip(own, kinds) if k == "year"]
            if not headings and years and len(years) == len(set(years)) and context_heading:
                # Each year at most once: a row '2026 | 2025 | 2026 | 2025' holds two durations, and one caption cannot say which is which.
                headings = [context_heading]
            caption, tokens = (own[0], own[1:]) if kinds and kinds[0] is None else (None, own)
            token_kinds = kinds[1:] if caption is not None else kinds
            data_like = (caption is not None and columns is not None and all(k == "year" for k in token_kinds) and not duration_of(caption["text"])
                         and not is_caption(caption["text"]) and not BASIS_RE.match(caption["text"].strip()))
            if len(tokens) >= 2 and all(token_kinds) and not data_like and any(k in ("qn", "date", "year") for k in token_kinds):
                if caption is not None and duration_of(caption["text"]):
                    # 'Nine months ended September 30, | 2024 | 2023': the row's own caption is the duration of its columns.
                    headings = [{"text": caption["text"], "c0": caption["c0"], "c1": caption["c1"], "wide": True, "ref": _cell_ref(caption)}]
                if caption is not None:
                    scale = unit_scale(caption["text"]) or scale
                    per_share_table = per_share_table or bool(PER_SHARE_TABLE.match(caption["text"].strip()))
                    if BASIS_RE.match(caption["text"].strip()) or re.search(r"\bgaap\b", caption["text"], re.I):
                        basis = "NON-GAAP" if re.search(r"non-gaap", caption["text"], re.I) else "GAAP"
                columns = []
                for cell, kind in zip(tokens, token_kinds):
                    base = {"c0": cell["c0"], "c1": cell["c1"], "ref": _cell_ref(cell)}
                    heading, why = _heading_for(headings, cell)
                    base["heading_key"] = tuple(heading["ref"]["columns"]) + (heading["ref"]["row"],) if heading else None
                    if kind == "change":
                        columns.append({**base, "type": "change", "label": cell["text"].upper()})
                        continue
                    if kind == "skip":
                        columns.append({**base, "type": "skip", "label": cell["text"]})
                        continue
                    if kind == "qn":
                        columns.append({**base, "type": "period", "period": qn_period(cell["text"]), "ancestry": [base["ref"]]})
                        continue
                    d = parse_date(cell["text"])
                    above = [m for m in month_days if m["c0"] <= cell["c0"] and cell["c1"] <= m["c1"]] if kind == "year" else []
                    if len(above) == 1 and heading:
                        month, day = _month_day(above[0]["text"].strip().rstrip(",") + ",")
                        try:
                            d = date(int(cell["text"]), month, day)
                        except (ValueError, TypeError):
                            d, why = None, "its year and the month and day above it are not a date"
                        base["ancestry_md"] = _cell_ref(above[0])
                    elif kind == "year" and heading and _month_day(heading["text"]):
                        month, day = _month_day(heading["text"])
                        try:
                            d = date(int(cell["text"]), month, day)
                        except ValueError:
                            d, why = None, "its year and the heading's month and day are not a date"
                    elif kind == "year" and heading:
                        why = "its heading gives no month and day for the year"
                    dur = duration_of(heading["text"]) if heading else None
                    if d is not None and dur:
                        columns.append({**base, "type": "period", "period": dated_period(dur, d), "ancestry": [heading["ref"], base["ref"]]})
                    else:
                        columns.append({**base, "type": "unknown", "label": cell["text"]})
                        unknown.setdefault(why or "its duration is not stated", []).append(cell["text"])
                transposed = None
                headings, month_days = [], []  # a heading describes the header block below it only; a later block needs its own
                continue
            names = [COMPACT.get(re.sub(r"\W", "", c["text"].lower())) for c in own[1:]]
            if sum(m is not None for m in names) >= 2 and headings:
                under = {id(h) if h else None for h in (_heading_for(headings, c)[0] for c in own[1:])}
                heading = _heading_for(headings, own[1])[0]
                if len(under) == 1 and heading and _month_day(heading["text"]) and duration_of(heading["text"]):
                    transposed = {"heading": heading, "columns": [{"c0": c["c0"], "c1": c["c1"], "metric": m, "ref": _cell_ref(c)} for c, m in zip(own[1:], names)]}
                    scale = unit_scale(own[0]["text"]) or scale
                    columns = None
                    continue
            if breakdown and columns is not None and metric_for(cells[0], section):
                breakdown_rows += 1
                continue
            if transposed:
                grid = _read_grid(row, transposed["columns"], covering)
                label = grid[0] if grid else cells[0]
                m = re.fullmatch(r"(\d{4}) As (?:Reported|Adjusted) \((Non-)?GAAP\)", label.strip())
                if not m:
                    continue
                if grid is None:
                    # A missing or extra cell must never move the following values under different metrics: read in printed order only when nothing is spanned and the
                    # count matches exactly; otherwise refuse the whole row.
                    if not simple or len(cells) - 1 != len(transposed["columns"]):
                        skipped += 1
                        continue
                    tokens = _merge_with_cells(row["placed"])
                    values, value_cells, method, label_src = cells[1:], [t[1] for t in tokens[1:]], "CELL_ORDER", tokens[0][1] if tokens else []
                    by_order += 1
                else:
                    _, values, value_cells, label_src = grid
                    method = "GRID"
                heading = transposed["heading"]
                month, day = _month_day(heading["text"])
                period = dated_period(duration_of(heading["text"]), date(int(m.group(1)), month, day))
                row_basis = "NON-GAAP" if m.group(2) else "GAAP"
                for col, cell, vcells in zip(transposed["columns"], values, value_cells):
                    if col["metric"] is None or cell is None:
                        continue
                    num = parse_number(cell)
                    if num is None:
                        issues.append({"code": "UNREADABLE_ROW", "where": where, "detail": f"'{col['metric']}' value '{cell}' is not a plain number; skipped"})
                        continue
                    if num[2] == "percent":
                        issues.append({"code": "UNIT_AMBIGUOUS", "where": where, "detail": f"'{col['metric']}' value '{cell}' is a percentage, not an amount; skipped"})
                        continue
                    refs = {"alignment": method, "label_cells": [_cell_ref(c) for c in label_src], "value_cells": [_cell_ref(c) for c in vcells],
                            "header_cells": [heading["ref"], col["ref"]]}
                    facts.append(_fact(col["metric"], row_basis, period, num, scale, None, table, row, label, {}, scope, table_dollar, refs))
                continue
            if columns is None:
                continue
            grid = _read_grid(row, columns, covering)
            label = grid[0] if grid else cells[0]
            found = metric_for(label, section)
            if found is None:
                continue
            metric, label_basis, label_scale = found
            if per_share_table and metric != "eps_diluted":
                continue   # a table stated per common share: its 'Net earnings' row is a per-share amount
            if grid is None:
                if not simple:
                    misaligned += 1
                    continue
                if len(cells) - 1 != len(columns):
                    skipped += 1
                    continue
                tokens = _merge_with_cells(row["placed"])
                values, value_cells, method, label_src = cells[1:], [t[1] for t in tokens[1:]], "CELL_ORDER", tokens[0][1] if tokens else []
                by_order += 1
            else:
                _, values, value_cells, label_src = grid
                method = "GRID"
            ancestor_basis = {("NON-GAAP" if BASIS_RE.match(c["text"].strip()).group(1).lower().startswith("non") else "GAAP")
                              for c in label_src if c not in row["placed"] and BASIS_RE.match(c["text"].strip())}
            if len(ancestor_basis) > 1 or (label_basis and ancestor_basis and {label_basis} != ancestor_basis):
                basis_conflicts += 1
                continue
            row_basis = label_basis or (next(iter(ancestor_basis)) if ancestor_basis else basis)
            nums, bad = [], False
            for col, cell in zip(columns, values):
                if col["type"] != "period" or cell is None:
                    nums.append(None)
                    continue
                num = parse_number(cell)
                if num is None:
                    bad = True
                    break
                nums.append(num)
            if bad:
                issues.append({"code": "UNREADABLE_ROW", "where": where, "detail": f"'{label}': a value in a period column is not a plain number; row skipped"})
                continue
            label_refs = [_cell_ref(c) for c in label_src]
            for col, num, vcells in zip(columns, nums, value_cells):
                if num is None:
                    continue
                # The release's printed change for this column is the one under the same duration heading (a quarter is never checked against a 9-month 'Y/Y').
                printed = {c["label"]: v for c, v in zip(columns, values) if c["type"] == "change" and v is not None and c.get("heading_key") == col.get("heading_key")}
                if metric != "gross_margin" and num[2] == "percent":
                    issues.append({"code": "UNIT_AMBIGUOUS", "where": where, "detail": f"'{label}' is printed as a percentage, not an amount; not extracted"})
                    break
                if metric == "gross_margin" and num[2] != "percent":
                    issues.append({"code": "UNIT_AMBIGUOUS", "where": where, "detail": "gross margin without a % sign (a dollar amount?); not extracted"})
                    break
                if metric == "eps_diluted" and num[1] is None and (label.strip().lower() == "diluted" or "." not in cell_text(values, columns, col)):
                    issues.append({"code": "UNIT_AMBIGUOUS", "where": where, "detail": f"'{label}' has no currency sign (a share count?); not read as earnings per share"})
                    break
                if metric in ("net_income", "net_income_attributable", "eps_diluted") and LOSS_LABEL.search(label.strip().lower()) and num[0] > 0:
                    num = (-num[0], num[1], num[2])   # 'Net loss | 4,828': a loss of 4,828
                refs = {"alignment": method, "label_cells": label_refs, "value_cells": [_cell_ref(c) for c in vcells], "header_cells": col["ancestry"]}
                facts.append(_fact(metric, row_basis, col["period"], num, label_scale or scale, label_scale, table, row, label, printed, scope, table_dollar, refs))
        if breakdown_rows:
            issues.append({"code": "BREAKDOWN_ROWS_NOT_READ", "where": where_t, "detail": f"{breakdown_rows} recognised row(s) below '{breakdown}' are parts of the company (segments, categories "
                           "or regions), not the company figure; not read"})
        # Net income attributable to the company replaces the total that includes non-controlling interests, for the same period and basis in this table.
        attributable = {(f["basis"], f["period"]) for f in facts[table_start:] if f["metric"] == "net_income_attributable"}
        replaced = [f for f in facts[table_start:] if f["metric"] == "net_income" and (f["basis"], f["period"]) in attributable]
        if replaced:
            facts[table_start:] = [f for f in facts[table_start:] if all(f is not r for r in replaced)]
            issues.append({"code": "NET_INCOME_ATTRIBUTABLE_USED", "where": where_t, "detail": "net income attributable to the company is used; the total including "
                           f"non-controlling interests ({len(replaced)} value(s)) is not"})
        for f in facts[table_start:]:
            if f["metric"] == "net_income_attributable":
                f["metric"] = "net_income"
                f["flags"].append("ATTRIBUTABLE_TO_COMPANY")
        # One table printing the same metric, basis and period in several rows with different values (segment blocks, subtotals) cannot say which row is the company
        # figure: none is read. Equal values printed twice are the same figure and are kept as corroboration.
        rows_of, values_of = {}, {}
        for f in facts[table_start:]:
            k = (f["metric"], f["basis"], f["period"], f["unit"])
            rows_of.setdefault(k, set()).add(f["evidence"]["row"])
            values_of.setdefault(k, set()).add(Decimal(f["value"]))
        repeated = {k: sorted(v) for k, v in rows_of.items() if len(v) > 1 and len(values_of[k]) > 1}
        if repeated:
            facts[table_start:] = [f for f in facts[table_start:] if (f["metric"], f["basis"], f["period"], f["unit"]) not in repeated]
            for metric, rows in sorted({(k[0], tuple(v)) for k, v in repeated.items()}):
                issues.append({"code": "REPEATED_ROW_LABEL", "where": where_t, "detail": f"rows {', '.join(map(str, rows))} all read as {metric} for the same periods (segment or subtotal rows?); "
                               "none is taken as the company figure"})
        for why, labels in unknown.items():
            issues.append({"code": "COLUMN_DURATION_UNKNOWN", "where": where_t, "detail": f"dated column(s) {', '.join(labels)}: {why}; their values are not read"})
        if any("UNIT_SCALE_UNKNOWN" in f["flags"] and f["evidence"]["table"] == table["table"] for f in facts):
            issues.append({"code": "UNIT_SCALE_UNSTATED", "where": where_t, "detail": "no 'in millions/thousands' statement found for this table; amounts are kept unscaled and flagged"})
        if skipped:
            issues.append({"code": "COLUMN_COUNT_MISMATCH", "where": where_t, "detail": f"{skipped} recognised row(s) skipped because their value count differs from the header columns"})
        if misaligned:
            issues.append({"code": "COLUMN_ALIGNMENT_UNCLEAR", "where": where_t, "detail": f"{misaligned} recognised row(s) skipped because their cells do not sit under the header columns"})
        if by_order:
            issues.append({"code": "ALIGNED_BY_PRINTED_ORDER", "where": where_t, "detail": f"{by_order} row(s) do not line up with the header geometry; their values were read in printed "
                           "order because the table has no spans and each row has exactly one value per header column"})
        if basis_conflicts:
            issues.append({"code": "BASIS_CONFLICT", "where": where_t, "detail": f"{basis_conflicts} row(s) carry a GAAP/non-GAAP label that disagrees with the label spanning them; not read"})
    return _dedupe(_statement_precedence(_merge_quarter_labels(_adopt_scale(facts, issues), issues), doc, issues), issues), issues


def _merge_quarter_labels(facts: list, issues: list) -> list:
    """A dated quarter column ('quarter ended 2024-09-30') and a calendar quarter label ('Q3 2024') that it ends in are the same quarter: its figures are read under
    the label, keeping the column's end date. Only calendar labels: a fiscal label ('Q3 FY25') cannot be dated without the company's fiscal calendar."""
    labels = {f["period"]: f["period_info"] for f in facts if f["period_info"]["kind"] == "quarter"}
    named = {k: p for k, p in labels.items() if p["q"] and not p["fiscal"]}
    mapping = {}
    for k, p in labels.items():
        if p["end"] is None:
            continue
        hits = [n for n, q in named.items() if _calendar_consistent(q["q"], q["year"], p["end"])]
        if len(hits) == 1:
            mapping[k] = hits[0]
    for f in facts:
        target = mapping.get(f["period"])
        if target:
            f["evidence"]["column_period"] = f["period"]
            f["period_info"] = {**named[target], "end": f["period_info"]["end"]}
            f["period"] = target
    if mapping:
        issues.append({"code": "QUARTER_LABELS_MERGED", "where": "tables", "detail": "; ".join(f"{k} is read as {v}" for k, v in sorted(mapping.items()))})
    return facts


def _adopt_scale(facts: list, issues: list) -> list:
    """A table that states no scale takes the scale of another table that prints the same figures: at least two of the same metric and period with the same printed
    value, none with a different value, and every such table agreeing on one scale. Otherwise its figures stay unscaled and flagged."""
    unscaled = {f["evidence"]["table"] for f in facts if f["unit"] == "unscaled"}
    for t in sorted(unscaled):
        mine = {(f["metric"], f["period"]): Decimal(f["value"]) for f in facts if f["evidence"]["table"] == t and f["unit"] == "unscaled"}
        votes = {}
        for other in {f["evidence"]["table"] for f in facts} - {t}:
            theirs = {(f["metric"], f["period"]): (Decimal(f["value"]), f["unit"]) for f in facts if f["evidence"]["table"] == other
                      and f["unit"] in ("thousands", "millions", "billions")}
            same = [k for k in mine if k in theirs and theirs[k][0] == mine[k]]
            differ = [k for k in mine if k in theirs and theirs[k][0] != mine[k]]
            if len(same) >= 2 and not differ:
                votes.setdefault(theirs[same[0]][1], []).append(other)
        if len(votes) != 1:
            continue
        unit, sources = next(iter(votes.items()))
        for f in facts:
            if f["evidence"]["table"] == t and f["unit"] == "unscaled":
                f["unit"], f["evidence"]["unit"] = unit, unit
                f["flags"] = [x for x in f["flags"] if x != "UNIT_SCALE_UNKNOWN"] + ["SCALE_FROM_MATCHING_TABLE"]
                f["evidence"]["scale_source_tables"] = sorted(sources)
        issues.append({"code": "UNIT_SCALE_FROM_MATCHING_TABLE", "where": f"table {t}", "detail": f"no scale stated; table(s) {', '.join(map(str, sorted(sources)))} print the "
                       f"same figures in {unit}, so its figures are read in {unit}"})
    return facts


STATEMENT_CAPTION = re.compile(r"statements?\s+of\s+(?:consolidated\s+)?(?:operations|income|earnings|comprehensive\s+(?:income|loss))|income\s+statements?", re.I)
CORE = ("revenue", "operating_income", "net_income", "eps_diluted")


def _amount(f):
    return Decimal(f["value"]) * {"thousands": 10**3, "millions": 10**6, "billions": 10**9}.get(f["unit"], 1)


def _statement_precedence(facts: list, doc: dict, issues: list) -> list:
    """The income statement is the company figure. When the release has one (a table giving net income and diluted EPS, preferring a table captioned as a
    statement of operations, then the longest), a GAAP or unlabelled revenue, operating income, net income or EPS figure from another table is used when the
    statement prints the same amount, or, for a period the statement does not show (the previous quarter of a summary table), when that table agrees with the
    statement elsewhere for the metric. A figure that differs for a period the statement shows, or from a table that never agrees with it (a segment, region or
    rounded highlights table), is not the company figure."""
    facts_all, facts = facts, [f for f in facts if f["period_info"]["kind"] == "quarter"]
    by_table = {}
    for f in facts:
        if f["metric"] in CORE and f["basis"] in ("GAAP", "UNSTATED"):
            by_table.setdefault(f["evidence"]["table"], set()).add(f["metric"])
    full = [t for t, m in by_table.items() if {"net_income", "eps_diluted"} <= m]
    if not full:
        return facts_all
    tables = {t["table"]: t for t in doc["tables"]}

    def rank(t):
        table = tables[t]
        ctx = " ".join(doc["lines"][max(0, table["first_line"] - 4):table["first_line"]] + [r["line"] for r in table["rows"][:2]])
        return (bool(STATEMENT_CAPTION.search(ctx)), len(table["rows"]), -t)
    primary = max(full, key=rank)
    printed, shown = {}, {}
    for f in facts:
        if f["evidence"]["table"] == primary and f["metric"] in CORE and f["basis"] in ("GAAP", "UNSTATED"):
            printed.setdefault(f["metric"], set()).add(_amount(f))
            shown.setdefault(f["metric"], set()).add(f["period"])
    checked = [f for f in facts if f["evidence"]["table"] != primary and f["metric"] in printed and f["basis"] in ("GAAP", "UNSTATED")]
    agreeing = {(f["evidence"]["table"], f["metric"]) for f in checked if _amount(f) in printed[f["metric"]]}
    out, dropped = [], {}
    for f in facts_all:
        if any(f is c for c in checked) and _amount(f) not in printed[f["metric"]] and (f["period"] in shown[f["metric"]] or (f["evidence"]["table"], f["metric"]) not in agreeing):
            dropped.setdefault(f["evidence"]["table"], set()).add(f["metric"])
            continue
        if f["evidence"]["table"] == primary:
            f["flags"].append("INCOME_STATEMENT")
        out.append(f)
    for t, metrics in sorted(dropped.items()):
        issues.append({"code": "NOT_THE_STATEMENT_FIGURE", "where": f"table {t}", "detail": f"its {', '.join(sorted(metrics))} figure(s) differ from the income statement "
                       f"(table {primary}): a segment, region or rounded figure, not the company figure; not used"})
    return out


def cell_text(values, columns, col):
    """The printed text of a row's value in one column."""
    return next((v for c, v in zip(columns, values) if c is col), None) or ""


def _fact(metric, basis, period, num, scale, label_scale, table, row, label, printed, scope, table_dollar=False, refs=None):
    value, symbol, pct = num
    currency, currency_basis, currency_quote, flags = _fact_currency(metric, symbol, table_dollar, scope)
    if metric == "gross_margin":
        unit = "percent"
    elif metric == "eps_diluted":
        unit = "per_share"
    else:
        unit = scale if scale else "unscaled"
    if unit == "unscaled":
        flags.append("UNIT_SCALE_UNKNOWN")
    if basis == "UNSTATED":
        flags.append("BASIS_NOT_STATED")
    evidence = {"table": table["table"], "row": row["row"], "label": label, "quote": row["line"], "unit": unit, "currency": currency,
                "currency_basis": currency_basis, "currency_quote": currency_quote, **(refs or {})}
    return {"metric": metric, "basis": basis, "period": period["label"], "period_info": period, "value": _decimal_string(value), "unit": unit, "currency": currency,
            "evidence": evidence, "printed_changes": printed, "method": "TABLE_ROW_LABEL_MATCH", "flags": flags}


def _fact_key(f):
    """A financial value is meaningful only inside its full compatible group."""
    return f["metric"], f["basis"], f["period"], f["unit"], f["currency"]


def _fact_groups(facts):
    groups = {}
    for f in facts:
        groups.setdefault(_fact_key(f), []).append(f)
    return groups


def _ambiguous_fact_keys(facts):
    return {key for key, group in _fact_groups(facts).items() if len({Decimal(f["value"]) for f in group}) > 1}


def _unambiguous_facts(facts):
    """One value per compatible group; conflicts are never resolved by order."""
    return [group[0] for group in _fact_groups(facts).values() if len({Decimal(f["value"]) for f in group}) == 1]


def _guidance_groups(items):
    groups = {}
    for g in items:
        key = g["metric"], g["basis"], g["target_period"], g["unit"], g["currency"]
        groups.setdefault(key, []).append(g)
    return groups


def _guidance_values(g):
    return tuple(Decimal(g[k]) if g[k] is not None else None for k in ("midpoint", "low", "high"))


def _unambiguous_guidance(items):
    return [group[0] for group in _guidance_groups(items).values() if len({_guidance_values(g) for g in group}) == 1]


def _guidance_conflict_issues(items):
    return [{"code": "GUIDANCE_CONFLICT", "where": f"{key[0]} {key[1]} {key[2]}",
             "detail": "conflicting guidance values/ranges; no range selected: " + " ; ".join(g["quote"] for g in group)}
            for key, group in _guidance_groups(items).items() if len({_guidance_values(g) for g in group}) > 1]


def _attach_source(facts, source, role):
    """Retain document/version identity alongside exact table evidence."""
    identity = {"document_id": source.get("document_id", f"{role}-release"), "document_role": role,
                "source_version_id": source.get("source_version_id", source["doc"]["raw_sha256"]),
                "document_sha256": source["doc"]["raw_sha256"], "source_url": source["source_url"], "document_name": source["doc"]["name"]}
    for fact in facts:
        fact["evidence"].update(identity)
        for evidence in fact.get("also_in", []):
            evidence.update(identity)


def _dedupe(facts, issues):
    """Deduplicate only fully compatible facts; keep all conflicting values."""
    out, index = [], {}
    for f in facts:
        key = _fact_key(f)
        first = index.get(key)
        if first is None:
            index[key] = f
            out.append(f)
        elif first["value"] == f["value"]:
            first.setdefault("also_in", []).append(f["evidence"])
            for k, v in f["printed_changes"].items():
                first["printed_changes"].setdefault(k, v)
        else:
            f["flags"].append("CONFLICTS_WITH_EARLIER_TABLE")
            first["flags"].append("CONFLICTS_WITH_LATER_TABLE")
            issues.append({"code": "FIGURE_CONFLICT", "where": f"{f['metric']} {f['basis']} {f['period']}", "detail": f"table {first['evidence']['table']} says {first['value']}, table {f['evidence']['table']} says {f['value']}; both kept, nothing averaged"})
            out.append(f)
    return out


_ORDINAL = r"first|second|third|fourth"
# A quarter phrase: 'third quarter of 2024', 'Third Quarter Fiscal 2025', 'third-quarter 2024', 'Fourth Quarter and Fiscal 2025', 'fourth quarter and full year
# 2024', 'fiscal 2024 fourth quarter', 'Q3 2024', 'Q3 FY25', "Q3'24".
_PHRASE = (rf"(?:(?P<qa>{_ORDINAL})[\s-]+quarter(?:\s+and\s+(?P<fy_and>full|fiscal)(?:\s+year)?)?(?:\s+of)?(?:\s+(?P<fa>fiscal)(?:\s+year)?)?,?\s+(?P<ya>\d{{4}})"
           rf"|(?P<fb>fiscal)\s+(?:year\s+)?(?P<yb>\d{{4}})\s+(?P<qb>{_ORDINAL})\s+quarter"
           rf"|\bQ(?P<qc>[1-4])\s*(?P<fc>FY)?\s*'?(?P<yc>\d{{4}}|\d{{2}})\b)")
REPORTED_QUARTER = (
    ("verb", re.compile(r"\b(?:reports?|reported|announces?|announced)\s+(?:(?:its|the)\s+)?(?:financial\s+)?(?:results\s+for\s+(?:the\s+|its\s+)?)?" + _PHRASE, re.I)),
    ("noun", re.compile(_PHRASE + r"\s+(?:financial\s+)?(?:results|earnings)\b", re.I)),
    ("noun", re.compile(r"\bresults\s+for\s+(?:the\s+|its\s+)?" + _PHRASE, re.I)),
)
FUTURE_BEFORE = re.compile(r"\b(?:will|to\s+discuss|conference\s+call|webcast|scheduled|expects?|expected|plans?|outlook|guidance|forecast|upcoming)\b", re.I)
FUTURE_AFTER = re.compile(r"^(?:[^.;]|\.(?=\d)){0,60}\b(?:will|are\s+expected|is\s+expected|expected|to\s+be\s+(?:released|reported|announced|held)|scheduled)\b", re.I)
COMPARISON_BEFORE = re.compile(r"\b(?:compared|comparison|versus|vs\.?|from|than|prior|previous|preceding|year[- ]ago|last\s+year's|same\s+(?:quarter|period)|against)\b"
                               r"(?:[^.;]|\.(?=\d)){0,60}$", re.I)  # a decimal point ('$18.1 billion') does not end the phrase
QUARTER_ENDED = re.compile(rf"(?:(?:\b(?P<q>{_ORDINAL})\s+)?(?:fiscal\s+)?quarter|\bthree\s+months|\bthree\s+and\s+(?:six|nine|twelve)\s+months|\b(?:thirteen|13)[- ]weeks?)"
                           rf"\s+ended\s+(?P<date>[A-Za-z]{{3,9}}\.?\s+\d{{1,2}},\s+\d{{4}})", re.I)
# A reference to a filing ('our Form 10-Q for the quarter ended March 31, 2026') names another document's period, not this release's.
FILING_REFERENCE = re.compile(r"\b(?:form\s+10-[qk]|quarterly\s+report|annual\s+report|filed\s+with|filings?\s+with|securities\s+and\s+exchange\s+commission)\b", re.I)


def _narrative(doc: dict, limit: int = 60) -> list:
    """The release's opening narrative: paragraphs and layout tables among its first lines (a letterhead table does not hide the headline)."""
    data_lines = set()
    for t in doc["tables"]:
        if not _layout_table(t):
            data_lines.update(range(t["first_line"], t["first_line"] + len(t["rows"])))
    return [line for i, line in enumerate(doc["lines"][:limit]) if i not in data_lines]


def _sentence_around(line: str, start: int, end: int) -> tuple[str, str]:
    """The text of the match's sentence before and after it."""
    left = SENTENCE_BREAK.split(line[:start])[-1]
    right = SENTENCE_BREAK.split(line[end:], maxsplit=1)[0]
    return left, right


def reported_quarters(doc: dict) -> list:
    """The release's own statements of the quarter it reports ('AMD Reports Third Quarter 2024 Financial Results', 'Acme third-quarter 2024 results', 'Financial
    Results for Fourth Quarter and Fiscal 2025', 'financial results for its fiscal 2024 fourth quarter', 'Q3 2024 Results'), from its opening narrative. A
    comparison ('compared with third quarter 2023 results'), a future event ('fourth quarter results will be released on ...') or an outlook is not one."""
    out = []
    for line in _narrative(doc):
        for kind, rx in REPORTED_QUARTER:
            for m in rx.finditer(line):
                before, after = _sentence_around(line, m.start(), m.end())
                if FUTURE_BEFORE.search(before[-120:]) or COMPARISON_BEFORE.search(before):
                    continue
                if kind == "noun" and FUTURE_AFTER.search(after):
                    continue
                if m["qa"]:
                    q, year, fiscal = ORDINALS[m["qa"].lower()], int(m["ya"]), bool(m["fa"]) or (m["fy_and"] or "").lower() == "fiscal"
                elif m["qb"]:
                    q, year, fiscal = ORDINALS[m["qb"].lower()], int(m["yb"]), True
                else:
                    q, year, fiscal = int(m["qc"]), _full_year(m["yc"]), bool(m["fc"])
                item = {"quarter": q, "year": year, "fiscal": fiscal, "quote": m.group(0)}
                if not any((o["quarter"], o["year"], o["quote"]) == (q, year, item["quote"]) for o in out):
                    out.append(item)
    return out


def quarter_ended_mentions(doc: dict) -> list:
    """'<ordinal> quarter ended <date>' mentions in the opening narrative that describe the release's own period (not 'compared with the quarter ended ...')."""
    out = []
    for line in _narrative(doc, 70):
        for m in QUARTER_ENDED.finditer(line):
            before, after = _sentence_around(line, m.start(), m.end())
            day = parse_date(m["date"])
            if day is None or COMPARISON_BEFORE.search(before) or FILING_REFERENCE.search(before + after):
                continue
            out.append({"quarter": ORDINALS[m["q"].lower()] if m["q"] else None, "date": day.isoformat(), "quote": m.group(0)})
    return out


def _published_day(value):
    """The publication date of an ISO time ('2026-07-29T20:05:00Z'), or None."""
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _calendar_consistent(q: int, year: int, end: date) -> bool:
    """A calendar quarter (not fiscal) ends in its last month, or within ten days of it (52/53-week years end on a nearby weekday)."""
    start = date(year, 3 * q, 1)
    stop = (date(year + 1, 1, 1) if q == 4 else date(year, 3 * q + 1, 1)) - timedelta(days=1)
    return start - timedelta(days=10) <= end <= stop + timedelta(days=10)


def _from_release(quarters: dict, head: dict) -> dict:
    """The reported quarter from the release's own evidence only (see resolve_current)."""
    out = {"status": "UNRESOLVED", "period": None, "end": None, "basis": None, "evidence": [], "reason": None, "candidates": sorted(quarters), "aliases": []}

    def unresolved(reason):
        return {**out, "reason": reason}

    def resolved(label, evidence, end=None, aliases=()):
        p = quarters[label]
        names = list(aliases)
        if st:   # the quarter as the release names it ('Q3 FY25', 'Q2 2026'): an earlier outlook for that quarter matches this column
            stated_label = f"Q{st['quarter']} FY{str(st['year'])[-2:]}" if st["fiscal"] else f"Q{st['quarter']} {st['year']}"
            if stated_label != label and stated_label not in names:
                names.append(stated_label)
        return {**out, "status": "RESOLVED", "period": label, "end": (p["end"] or end).isoformat() if (p["end"] or end) else None, "basis": "RELEASE_STATEMENT",
                "evidence": evidence, "aliases": names}

    st = None
    if not quarters:
        return unresolved("no quarter columns were recognised")
    mentions = head.get("quarter_ended_all") or ([head["quarter_ended"]] if head.get("quarter_ended") else [])
    stated_all = head.get("reported_quarter") or []
    if len({m["date"] for m in mentions}) > 1 and len({(x["quarter"], x["year"], x["fiscal"]) for x in stated_all}) == 1:
        # The release states one quarter ('Reports Second Quarter 2026'); a mention of another date ('three months ended June 30, 2025') is not its period.
        st0 = stated_all[0]
        agree = [m for m in mentions if (not st0["fiscal"] and _calendar_consistent(st0["quarter"], st0["year"], date.fromisoformat(m["date"])))
                 or (st0["fiscal"] and m["quarter"] == st0["quarter"])]
        if len({m["date"] for m in agree}) == 1:
            mentions = agree
    if len({m["date"] for m in mentions}) > 1:
        return unresolved("the release names different quarter-end dates for its own period: " + "; ".join(f"'{m['quote']}'" for m in mentions))
    qe = mentions[0] if mentions else None
    if qe and len({m["quarter"] for m in mentions if m["quarter"]}) > 1:
        return unresolved("the release names different quarters ending " + qe["date"])
    if qe and not qe.get("quarter"):
        qe = {**qe, "quarter": next((m["quarter"] for m in mentions if m["quarter"]), None)}
    end = date.fromisoformat(qe["date"]) if qe else None
    stated = head.get("reported_quarter") or []
    if len({(s["quarter"], s["year"]) for s in stated}) > 1:
        return unresolved("the release states different quarters: " + "; ".join(f"'{s['quote']}'" for s in stated))
    st = stated[0] if stated else None
    evidence = [x["quote"] for x in (qe, st) if x]
    if qe and st and qe.get("quarter") and qe["quarter"] != st["quarter"]:
        return unresolved(f"'{qe['quote']}' and '{st['quote']}' name different quarters")
    if end and st and not st["fiscal"] and not _calendar_consistent(st["quarter"], st["year"], end):
        if (qe.get("quarter") == st["quarter"] and end.year in (st["year"] - 1, st["year"])
                and any(p["end"] == end for p in quarters.values())):
            # 'First Quarter 2027 Results' with 'first quarter ended July 31, 2026': a fiscal year named without the word 'fiscal'. The quarter-end date and
            # a dated column settle it; the quarter is read as fiscal.
            st = {**st, "fiscal": True}
        else:
            return unresolved(f"'{qe['quote']}' does not end calendar quarter {st['quarter']} of {st['year']} ('{st['quote']}')")
    if end and st and st["fiscal"] and end.year not in (st["year"] - 1, st["year"]):
        return unresolved(f"'{qe['quote']}' cannot end a quarter of fiscal {st['year']} ('{st['quote']}')")
    dated = {label: p for label, p in quarters.items() if p["end"]}
    labelled = {label: p for label, p in quarters.items() if p["q"]}
    dated_hit = [label for label, p in dated.items() if p["end"] == end] if end else []
    if end and dated and not dated_hit:
        return unresolved(f"the headline's end date {end.isoformat()} is not one of the dated quarter columns ({', '.join(sorted(dated))})")
    label_hit = []
    if st:
        label_hit = [label for label, p in labelled.items() if p["q"] == st["quarter"] and p["year"] == st["year"]]
        if labelled and not label_hit and not dated_hit:
            return unresolved(f"the stated quarter ('{st['quote']}') is not one of the quarter columns ({', '.join(sorted(labelled))})")
        if not end and not label_hit and dated and not st["fiscal"]:
            # A stated calendar quarter identifies the one dated quarter column that ends in it.
            dated_hit = [label for label, p in dated.items() if _calendar_consistent(st["quarter"], st["year"], p["end"])]
        published = _published_day(head.get("published_at"))
        if not end and not label_hit and dated and st["fiscal"] and published:
            # A fiscal quarter cannot be dated without the company's fiscal calendar, but a results release is published within weeks of the quarter it reports:
            # the one dated quarter column ending in the 100 days before publication, in or next to the stated fiscal year, is that quarter.
            recent = [label for label, p in dated.items() if timedelta(0) <= published - p["end"] <= timedelta(days=100) and p["end"].year in range(st["year"] - 1, st["year"] + 2)]
            if len(recent) == 1:
                dated_hit = recent
                evidence = evidence + [f"published {published.isoformat()}; {recent[0]} is the only quarter column ending in the 100 days before"]
    elif end and qe.get("quarter") and not dated_hit:
        # '<ordinal> quarter ended <date>' identifies a calendar-labelled column; a fiscal label cannot be dated without the company's fiscal calendar.
        label_hit = [label for label, p in labelled.items() if not p["fiscal"] and p["q"] == qe["quarter"] and _calendar_consistent(p["q"], p["year"], end)]
    if len(label_hit) > 1 or len(dated_hit) > 1:
        return unresolved("more than one column matches the stated period: " + ", ".join(label_hit + dated_hit))
    if label_hit:
        return resolved(label_hit[0], evidence, end, dated_hit)
    if dated_hit:
        return resolved(dated_hit[0], evidence)
    if not qe and not st:
        return unresolved("the release does not state which quarter it reports (no 'quarter ended <date>' and no 'reports <nth> quarter <year> results'); choose the period explicitly")
    return unresolved("the stated period could not be matched to a column: " + "; ".join(f"'{e}'" for e in evidence))


def resolve_current(facts: list, head: dict, override=None) -> dict:
    """Which quarter the release reports, from consistent evidence only: the release's own '<ordinal> quarter ended <date>' and its statement of the quarter it
    reports. Column order, the largest year and the first table are never evidence. Conflicting statements, or a stated period that is not a recognised column,
    leave it UNRESOLVED with the reason; the note is then withheld rather than labelled with a guess.

    An analyst's record (override) settles a release that does not establish its quarter. It never overrules the release: a record that contradicts the release's
    own statement leaves the period UNRESOLVED and says so.

    Returns {status, period, end, basis, evidence, reason, candidates, aliases}; `end` is the stated end date when the evidence gives one."""
    quarters = {}
    for f in facts:
        if f["period_info"]["kind"] == "quarter":
            quarters.setdefault(f["period"], f["period_info"])
    release = _from_release(quarters, head)
    if override is None:
        return release
    label = override.get("period") if isinstance(override, dict) else override
    note = {"source": "analyst override", "period": label,
            **({k: override.get(k) for k in ("recorded_by", "recorded_at", "rationale")} if isinstance(override, dict) else {})}
    if label not in quarters:
        return {**release, "status": "UNRESOLVED", "period": None, "end": None, "basis": None,
                "reason": f"the analyst's period {label!r} is not one of the recognised quarter columns ({', '.join(sorted(quarters))})"}
    if release["status"] == "RESOLVED":
        if release["period"] != label:
            return {**release, "status": "UNRESOLVED", "period": None, "end": None, "basis": None,
                    "reason": f"the analyst's record {label!r} contradicts the release, which states {release['period']} ("
                              + "; ".join(f"'{e}'" for e in release["evidence"]) + ")"}
        return {**release, "basis": "RELEASE_STATEMENT (analyst record agrees)", "evidence": release["evidence"] + [note]}
    p = quarters[label]
    return {**release, "status": "RESOLVED", "period": label, "end": p["end"].isoformat() if p["end"] else None, "basis": "ANALYST_OVERRIDE",
            "evidence": [note], "release_reason": release["reason"]}


def choose_current(facts: list, head: dict):
    """The resolved period label, or None (see resolve_current)."""
    resolution = head.get("resolution") or resolve_current(facts, head)
    return resolution["period"]


def headline_checks(doc: dict, facts: list, period_override=None, published_at=None) -> dict:
    """Reads the release's headline sentence(s): the quarter and end date they state, the resolution of the reported period (see resolve_current), and whether the
    headline figures agree with that period's table figures."""
    text = " ".join(doc["lines"][:70])
    para = next((l for l in doc["lines"][:70] if re.search(r"quarter ended", l) and re.search(r"revenue|net sales|results", l, re.I)), None)
    out = {"paragraph": para[:900] if para else None, "quarter_ended": None, "quarter_ended_all": [], "fiscal_quarter_title": None, "reported_quarter": [],
           "revenue_headline": None, "eps_headline": {}, "checks": [], "published_at": published_at}
    mentions = quarter_ended_mentions(doc)
    out["quarter_ended_all"] = mentions
    out["quarter_ended"] = mentions[0] if mentions else None
    m = re.search(r"(First|Second|Third|Fourth) Quarter Fiscal (\d{4})", text)
    if m:
        out["fiscal_quarter_title"] = {"quarter": ORDINALS[m.group(1).lower()], "fiscal_year": int(m.group(2)), "quote": m.group(0)}
    out["reported_quarter"] = reported_quarters(doc)
    m = re.search(r"[Rr]evenue(?: for the [^$]{0,70}?)?,? (?:of|was|were) \$(\d[\d,]*(?:\.\d+)?) (billion|million)", text)
    if m:
        out["revenue_headline"] = {"value": m.group(1), "scale": m.group(2), "quote": m.group(0)}
    for m in re.finditer(r"(Non-GAAP|GAAP) earnings per diluted share (?:was|were|of) \$(\d+(?:\.\d+)?)", text):
        out["eps_headline"][m.group(1).upper()] = {"value": m.group(2), "quote": m.group(0)}
    m = re.search(r"(?<!GAAP )diluted earnings per share (?:of|was) \$(\d+(?:\.\d+)?)", text)
    if m and not out["eps_headline"]:
        out["eps_headline"]["UNSTATED"] = {"value": m.group(1), "quote": m.group(0)}
    out["resolution"] = resolve_current(facts, out, period_override)
    current = out["resolution"]["period"]
    cur = _unambiguous_facts([f for f in facts if f["period"] == current]) if current else []
    rev = [f for f in cur if f["metric"] == "revenue" and f["unit"] == "millions"]
    if out["revenue_headline"] and rev:
        h = Decimal(out["revenue_headline"]["value"].replace(",", ""))
        decimals = len(out["revenue_headline"]["value"].split(".")[1]) if "." in out["revenue_headline"]["value"] else 0
        factor = {"billion": Decimal(1000), "million": Decimal(1)}[out["revenue_headline"]["scale"]]
        tolerance = factor * Decimal(5) / (Decimal(10) ** (decimals + 1))
        ok = abs(Decimal(rev[0]["value"]) - h * factor) <= tolerance
        out["checks"].append({"check": "headline revenue vs table revenue", "ok": bool(ok), "headline": out["revenue_headline"]["quote"], "table_value_millions": rev[0]["value"]})
    for basis, h in out["eps_headline"].items():
        match = [f for f in cur if f["metric"] == "eps_diluted" and (basis == "UNSTATED" or f["basis"] == basis)]
        if match:
            out["checks"].append({"check": f"headline {basis} diluted EPS vs table", "ok": any(Decimal(h["value"]) == Decimal(f["value"]) for f in match), "headline": h["quote"],
                                  "table_value": ", ".join(f["value"] for f in match)})
    return out


# ---------------------------------------------------------------- guidance

PAIR = re.compile(r"(?:GAAP and non-GAAP) ([a-z ]+?) (?:are|is) expected to be (?:approximately )?(\$?[\d.,]+%?)(?: (billion|million))? and (\$?[\d.,]+%?)(?: (billion|million))?, respectively(?:, plus or minus ([\d.]+) basis points)?")
SINGLE_REV = re.compile(r"Revenue is expected to be (approximately )?\$(\d[\d,]*(?:\.\d+)?) (billion|million)(?:, plus or minus (\d+(?:\.\d+)?)%)?")


def _money(token: str, scale: str | None):
    t = token.lstrip("$").rstrip("%").replace(",", "")
    v = Decimal(t)
    if token.endswith("%"):
        return v, "percent"
    if scale == "billion":
        return v * 1000, "millions"
    if scale == "million":
        return v, "millions"
    return v, "unscaled"


AMD_REV = re.compile(r"[Ff]or the (first|second|third|fourth) quarter of (fiscal )?(\d{4}),? [A-Za-z]+ expects revenue to be approximately \$(\d[\d,]*(?:\.\d+)?) (billion|million), plus or minus \$(\d[\d,]*(?:\.\d+)?) (billion|million)")
AMD_GM = re.compile(r"(Non-GAAP|GAAP) gross margin is expected to be approximately (\d+(?:\.\d+)?)%")


def guidance_currency(doc: dict, currency_override=None, facts=None) -> tuple:
    """(currency, basis) of '$' amounts in the outlook text, from the same evidence as the release's figures: the currency its tables state or print (when
    they agree), the document's statement, else the analyst's record, else US dollars assumed (and said so). Disagreeing evidence leaves it unresolved."""
    override = analyst_currency(currency_override)
    evidence = dict(document_currency_statements(doc))
    for f in facts or []:
        basis = f["evidence"].get("currency_basis") or ""
        if f["currency"] and basis.split(" (")[0] in ("TABLE_STATEMENT", "TABLE_SYMBOL", "CELL_SYMBOL"):
            evidence.setdefault(f["currency"], f"table {f['evidence']['table']}: {f['evidence'].get('currency_quote')}")
    if len(evidence) > 1:
        return None, "UNRESOLVED: the release's tables and text name several currencies (" + ", ".join(sorted(evidence)) + ")"
    if evidence:
        (code, quote), = evidence.items()
        if override and override["currency"] != code:
            return None, f"UNRESOLVED: analyst override {override['currency']} contradicts '{quote}'"
        return code, "SAME_AS_RELEASE_EVIDENCE" + (" (analyst override agrees)" if override else "")
    if override:
        return override["currency"], "ANALYST_OVERRIDE"
    return "USD", ASSUMED


def _amd_style(doc: dict, currency=("USD", "ASSUMED_FROM_$_SIGN")) -> list:
    """'For the fourth quarter of 2024, AMD expects revenue to be approximately $7.5 billion, plus or minus $300 million.' and '<basis> gross margin is expected to be approximately 54%'."""
    items = []
    for line in doc["lines"]:
        m = AMD_REV.search(line)
        if not m:
            continue
        label = f"Q{ORDINALS[m.group(1).lower()]} FY{m.group(3)[-2:]}" if m.group(2) else f"Q{ORDINALS[m.group(1).lower()]} {m.group(3)}"
        mid, _ = _money("$" + m.group(4), m.group(5))
        band, _ = _money("$" + m.group(6), m.group(7))
        items.append({"metric": "revenue", "basis": "UNSTATED", "target_period": label, "unit": "millions", "currency": currency[0], "currency_basis": currency[1], "midpoint": _decimal_string(mid), "low": _decimal_string(mid - band),
                      "high": _decimal_string(mid + band), "band": f"plus or minus {_decimal_string(band)} million", "conversion": "billion to million x1000" if "billion" in (m.group(5), m.group(7)) else None,
                      "quote": m.group(0), "method": "OUTLOOK_REGEX"})
        for g in AMD_GM.finditer(line):
            items.append({"metric": "gross_margin", "basis": "NON-GAAP" if g.group(1).lower().startswith("non") else "GAAP", "target_period": label, "unit": "percent", "currency": None, "currency_basis": None,
                          "midpoint": _decimal_string(Decimal(g.group(2))), "low": None, "high": None, "band": "point estimate (approximately)", "conversion": None, "quote": g.group(0), "method": "OUTLOOK_REGEX"})
    return items


_TARGET_Q = re.compile(rf"\b(?:(?P<qa>{_ORDINAL})[\s-]+(?:(?P<fa0>fiscal)\s+)?quarter(?:\s+(?:of\s+)?(?:(?P<fa>fiscal)(?:\s+year)?\s+)?(?P<ya>\d{{4}}))?"
                       rf"|(?:(?P<fb>fiscal)\s+(?:year\s+)?(?P<yb>\d{{4}})\s+(?P<qb>{_ORDINAL})\s+quarter)"
                       r"|Q(?P<qc>[1-4])\s*(?P<fc>FY|fiscal)?\s*'?(?P<yc>\d{4}|\d{2})?)\b", re.I)
_FORWARD = re.compile(r"\b(?:outlook\s+(?:is|for)|expects?|anticipates?|forecasts?|projects?|guidance\s+(?:is|for|of)|guides?|sees|is\s+expected|are\s+expected|targets?)\b", re.I)
_FULL_YEAR = re.compile(r"\b(?:full[- ]year|fiscal\s+year|annual|for\s+(?:the\s+)?year|20\d\d\s+(?:outlook|guidance))\b", re.I)
_OUT_METRIC = re.compile(r"(?P<basis>non-gaap|gaap|adjusted)?\s*(?P<m>(?:total\s+|net\s+)?(?:revenues?|sales)"
                         r"|(?:diluted\s+)?(?:earnings|net\s+income|net\s+loss|eps|income|loss)\s+per\s+(?:diluted\s+)?(?:common\s+)?share|(?:diluted\s+)?eps)\b", re.I)
_OUT_VAL = r"(?P<{n}o>\()?\$\s?(?P<{n}>\d[\d,]*(?:\.\d+)?)\)?(?:\s*(?P<{n}s>billion|million|thousand))?"
_OUT_RANGE = re.compile(r"(?:in\s+the\s+range\s+of|between|of|to\s+be|at|from|range\s+of)?\s*" + _OUT_VAL.format(n="a") + r"\s*(?:to|and|-|–|—)\s*" + _OUT_VAL.format(n="b"), re.I)
_OUT_POINT = re.compile(r"(?:approximately|about|around|of|to\s+be|at)\s+" + _OUT_VAL.format(n="a")
                        + r"(?:,?\s*plus\s+or\s+minus\s+(?:(?P<pct>\d+(?:\.\d+)?)%|" + _OUT_VAL.format(n="b") + "))?", re.I)
_SCALE_MILLIONS = {"billion": Decimal(1000), "million": Decimal(1), "thousand": Decimal("0.001")}


def _outlook_amount(match, n, metric, fallback_scale):
    value = Decimal(match[n].replace(",", ""))
    if match[f"{n}o"]:
        value = -value
    if metric == "eps_diluted":
        return value, "per_share"
    scale = match[f"{n}s"] or fallback_scale
    if scale is None:
        return None, None
    return value * _SCALE_MILLIONS[scale.lower()], "millions"


def _next_quarter(own, q):
    """The first quarter numbered q after the release's own quarter."""
    year = own["year"] + (1 if q <= own["quarter"] else 0)
    return year


def _sentence_outlook(doc: dict, currency, own) -> list:
    """An outlook stated in a sentence for a named later quarter: "TI's third quarter outlook is for revenue in the range of $3.94 billion to $4.26 billion and
    earnings per share between $1.24 and $1.48.", "The Company forecasts Q2 2026 revenue of $19.5 to $20.5 million", "For the third quarter of 2026, we expect
    revenue of approximately $500 million, plus or minus $20 million". Revenue and diluted EPS only, in dollars only. The quarter must be named and later than the
    release's own quarter (a quarter without a year is the next one with that number); a full-year outlook, a past result or a growth percentage is not read."""
    items = []
    for line in doc["lines"]:
        if "$" not in line:
            continue
        for sentence in SENTENCE_BREAK.split(line):
            if "$" not in sentence or not _FORWARD.search(sentence):
                continue
            tq = _TARGET_Q.search(sentence)
            if not tq or _FULL_YEAR.search(sentence[:tq.start()]):
                continue
            if tq["qa"]:
                q, year, fiscal = ORDINALS[tq["qa"].lower()], tq["ya"], bool(tq["fa"] or tq["fa0"])
            elif tq["qb"]:
                q, year, fiscal = ORDINALS[tq["qb"].lower()], tq["yb"], True
            else:
                q, year, fiscal = int(tq["qc"]), tq["yc"], bool(tq["fc"])
            if own is None:
                continue                      # without the release's own quarter, neither the year nor 'later' can be checked
            fiscal = fiscal or own["fiscal"]
            year = _full_year(year) if year else _next_quarter(own, q)
            if (year, q) <= (own["year"], own["quarter"]):
                continue                      # the release's own or an earlier quarter: a result, not an outlook
            label = f"Q{q} FY{str(year)[-2:]}" if fiscal else f"Q{q} {year}"
            metrics = list(_OUT_METRIC.finditer(sentence))
            for i, mm in enumerate(metrics):
                clause = sentence[mm.end(): metrics[i + 1].start() if i + 1 < len(metrics) else len(sentence)]
                m_name = "revenue" if re.search(r"revenue|sales", mm["m"], re.I) else "eps_diluted"
                basis = "NON-GAAP" if (mm["basis"] or "").lower() in ("non-gaap", "adjusted") else "GAAP" if (mm["basis"] or "").lower() == "gaap" else "UNSTATED"
                if re.search(r"\bnon-gaap\b|\badjusted\b", sentence[:mm.start()][-40:], re.I) and basis == "UNSTATED":
                    basis = "NON-GAAP"
                r = _OUT_RANGE.search(clause)
                if r and r.start() < 40:
                    low, unit = _outlook_amount(r, "a", m_name, r["bs"])
                    high, _ = _outlook_amount(r, "b", m_name, r["bs"])
                    if low is None or high is None or low > high:
                        continue
                    mid, band = (low + high) / 2, "range"
                else:
                    pnt = _OUT_POINT.search(clause)
                    if not pnt or pnt.start() > 40:
                        continue
                    mid, unit = _outlook_amount(pnt, "a", m_name, None)
                    if mid is None:
                        continue
                    if pnt["pct"]:
                        width = mid * Decimal(pnt["pct"]) / 100
                        band = f"plus or minus {pnt['pct']}%"
                    elif pnt["b"]:
                        width, _ = _outlook_amount(pnt, "b", m_name, pnt["as"])
                        band = f"plus or minus {pnt.group('b')}" + (f" {pnt['bs']}" if pnt["bs"] else "")
                    else:
                        width, band = None, "point estimate (approximately)"
                    low, high = (mid - width, mid + width) if width is not None else (None, None)
                items.append({"metric": m_name, "basis": basis, "target_period": label, "unit": unit, "currency": currency[0], "currency_basis": currency[1],
                              "midpoint": _decimal_string(mid), "low": _decimal_string(low) if low is not None else None, "high": _decimal_string(high) if high is not None else None,
                              "band": band, "conversion": "to millions" if unit == "millions" else None, "quote": sentence.strip()[:400], "method": "OUTLOOK_SENTENCE"})
    return items


def extract_guidance(doc: dict, currency_override=None, facts=None, own=None) -> tuple[list, list]:
    """The company's own outlook for the next period: revenue (plus or minus a percentage or amount) and 'GAAP and non-GAAP X are expected to be A and B, respectively' bullets,
    and revenue or diluted EPS stated for a named later quarter in a sentence (see _sentence_outlook). '$' amounts take the release's own currency evidence
    (see guidance_currency). own: the release's own quarter {quarter, year, fiscal}, which dates a quarter named without its year."""
    currency = guidance_currency(doc, currency_override, facts)
    items, issues = _amd_style(doc, currency), []
    if items:
        return items, _guidance_conflict_issues(items)
    sentence_items = _sentence_outlook(doc, currency, own)
    target = None
    for i, line in enumerate(doc["lines"]):
        m = re.search(r"outlook for the (first|second|third|fourth) quarter of fiscal (\d{4})", line, re.I)
        if m:
            target = (f"Q{ORDINALS[m.group(1).lower()]} FY{m.group(2)[-2:]}", i)
            break
    if target is None:
        if sentence_items:
            return sentence_items, _guidance_conflict_issues(sentence_items)
        return [], [{"code": "NO_OUTLOOK_FOUND", "where": "text", "detail": "no outlook for a named later quarter was found; no guidance extracted"}]
    for line in doc["lines"][target[1]:target[1] + 16]:
        m = SINGLE_REV.search(line)
        if m:
            mid, unit = _money("$" + m.group(2), m.group(3))
            band = Decimal(m.group(4)) if m.group(4) else None
            low = mid * (1 - band / 100) if band is not None else None
            high = mid * (1 + band / 100) if band is not None else None
            items.append({"metric": "revenue", "basis": "UNSTATED", "target_period": target[0], "unit": unit, "currency": currency[0], "currency_basis": currency[1], "midpoint": _decimal_string(mid),
                          "low": _decimal_string(low) if low is not None else None, "high": _decimal_string(high) if high is not None else None,
                          "band": f"plus or minus {m.group(4)}%" if band is not None else "point estimate" + (" (approximately)" if m.group(1) else ""),
                          "conversion": "billion to million x1000" if m.group(3) == "billion" else None, "quote": m.group(0), "method": "OUTLOOK_REGEX"})
            continue
        for m in PAIR.finditer(line):
            name = {"gross margins": "gross_margin", "operating expenses": "operating_expenses"}.get(m.group(1).strip())
            if name is None:
                issues.append({"code": "GUIDANCE_ITEM_NOT_PARSED", "where": "outlook", "detail": f"'{m.group(1)}' guidance is not a supported metric; listed in the source only"})
                continue
            for basis, tok, scale in (("GAAP", m.group(2), m.group(3)), ("NON-GAAP", m.group(4), m.group(5))):
                mid, unit = _money(tok, scale)
                band = Decimal(m.group(6)) / 100 if (m.group(6) and unit == "percent") else None
                items.append({"metric": name, "basis": basis, "target_period": target[0], "unit": unit, "currency": None if unit == "percent" else currency[0],
                              "currency_basis": None if unit == "percent" else currency[1], "midpoint": _decimal_string(mid),
                              "low": _decimal_string(mid - band) if band is not None else None, "high": _decimal_string(mid + band) if band is not None else None,
                              "band": f"plus or minus {m.group(6)} basis points" if band is not None else "point estimate (approximately)" if "approximately" in m.group(0) else "point estimate",
                              "conversion": "billion to million x1000" if scale == "billion" else None, "quote": m.group(0), "method": "OUTLOOK_REGEX"})
    have = {(g["metric"], g["target_period"]) for g in items}
    items += [g for g in sentence_items if (g["metric"], g["target_period"]) not in have]
    if not items:
        issues.append({"code": "NO_GUIDANCE_PARSED", "where": "outlook", "detail": "an outlook section exists but none of its sentences matched the supported wording"})
    issues.extend(_guidance_conflict_issues(items))
    return items, issues


# ---------------------------------------------------------------- comparisons

def _pct(diff: Decimal, base: Decimal):
    return None if base == 0 else (100 * diff / abs(base))


def _fmt(value, places=1):
    return "unknown" if value is None else f"{value:+.{places}f}"


def _prior_row(cur, prior, rel, source, check_printed):
    a, b = Decimal(cur["value"]), Decimal(prior["value"])
    diff = a - b
    row = {"label": "ACTUAL vs PRIOR-PERIOD ACTUAL", "relation": rel, "metric": cur["metric"], "basis": cur["basis"], "unit": cur["unit"], "currency": cur["currency"],
           "current_period": cur["period"], "prior_period": prior["period"], "actual": cur["value"], "prior_actual": prior["value"], "difference": _decimal_string(diff),
           "difference_unit": "percentage points" if cur["unit"] == "percent" else cur["unit"],
           "difference_pct": None if cur["unit"] == "percent" or _pct(diff, b) is None else _decimal_string(round(_pct(diff, b), 2)),
           "evidence": [cur["evidence"], prior["evidence"]], "source": source, "printed_change_check": None,
           "currency_assumed": any((f["evidence"].get("currency_basis") or "") == ASSUMED for f in (cur, prior))}
    printed = cur["printed_changes"].get({"YEAR_OVER_YEAR": "Y/Y", "SEQUENTIAL": "Q/Q"}.get(rel, "")) if check_printed else None
    m = re.fullmatch(r"(Up|Down)\s+([\d.]+)\s*%", printed or "")
    if m and row["difference_pct"] is not None:
        shown = Decimal(m.group(2)) * (1 if m.group(1) == "Up" else -1)
        row["printed_change_check"] = {"printed": printed, "agrees": bool(abs(Decimal(row["difference_pct"]) - shown) <= Decimal("0.5"))}
    elif printed and cur["unit"] == "percent":
        m2 = re.fullmatch(r"(Up|Down)\s+([\d.]+)\s*(?:pts?|ppts?)", printed)
        if m2:
            shown = Decimal(m2.group(2)) * (1 if m2.group(1) == "Up" else -1)
            row["printed_change_check"] = {"printed": printed, "agrees": bool(abs(diff - shown) <= Decimal("0.5"))}
    return row


def prior_period_comparisons(facts: list, current_period: str, earlier_facts: list | None = None, earlier_current: str | None = None) -> list:
    """ACTUAL vs PRIOR-PERIOD ACTUAL. A comparison needs a genuinely earlier period of the same duration kind and labelling (see relation()); a later column is never a prior
    period. Comparative columns printed in the same release are checked against the change the release itself prints. If an earlier release is supplied, its own
    current-period figures fill a SEQUENTIAL comparison the release does not print, labelled with that source, and only between figures of a known, equal currency."""
    out = []
    ambiguous = _ambiguous_fact_keys(facts)
    resolved = _unambiguous_facts(facts)
    current = sorted((f for f in resolved if f["period"] == current_period), key=lambda f: (f["metric"], f["basis"], f["unit"], f["currency"] or ""))
    blocked_relations = set()
    for cur in current:
        for prior in facts:
            if (prior["metric"] == cur["metric"] and prior["basis"] == cur["basis"] and prior["period"] != current_period
                    and prior["unit"] == cur["unit"] and prior["currency"] == cur["currency"] and (cur["currency"] is not None or cur["unit"] == "percent")):
                rel = relation(cur["period_info"], prior["period_info"])
                if _fact_key(prior) in ambiguous:
                    blocked_relations.add((_fact_key(cur), rel))
                    continue
                if rel is not None:
                    out.append(_prior_row(cur, prior, rel, "comparative column printed in the current release", True))
    if earlier_facts and earlier_current:
        have = {(r["metric"], r["basis"], r["unit"], r["currency"], r["relation"]) for r in out}
        for cur in current:
            for prior in _unambiguous_facts(earlier_facts):
                if (prior["period"] == earlier_current and prior["metric"] == cur["metric"] and prior["basis"] == cur["basis"] and prior["unit"] == cur["unit"]
                        and prior["currency"] == cur["currency"] and (cur["currency"] is not None or cur["unit"] == "percent")):
                    ident = cur["metric"], cur["basis"], cur["unit"], cur["currency"], "SEQUENTIAL"
                    if (relation(cur["period_info"], prior["period_info"]) == "SEQUENTIAL" and ident not in have
                            and (_fact_key(cur), "SEQUENTIAL") not in blocked_relations):
                        out.append(_prior_row(cur, prior, "SEQUENTIAL", "figure from the comparison release (not printed in the current release)", False))
                        have.add(ident)
    return out


def _own_quarter(head: dict, period: str | None):
    """The release's own quarter as {quarter, year, fiscal}: its column label ('Q3 FY25', 'Q2 2026'), else its one stated quarter ('Reports Second Quarter Fiscal 2027')."""
    p = qn_period(period) if period else None
    if p:
        return {"quarter": p["q"], "year": p["year"], "fiscal": p["fiscal"]}
    stated = {(s["quarter"], s["year"], s["fiscal"]) for s in head.get("reported_quarter") or []}
    if period and len(stated) == 1:
        q, year, fiscal = stated.pop()
        return {"quarter": q, "year": year, "fiscal": fiscal}
    return None


_UNIT_FACTOR = {"thousands": Decimal(10) ** 3, "millions": Decimal(10) ** 6, "billions": Decimal(10) ** 9}


GUIDANCE_CAVEAT = re.compile(r"\b(?:not|weren't|wasn't)\s+(?:been\s+)?(?:included\s+|reflected\s+|contemplated\s+)?in\s+(?:the\s+company's\s+|our\s+|its\s+|the\s+)?"
                             r"(?:original\s+|prior\s+|previous\s+|earlier\s+)?(?:guidance|outlook|forecast)\b", re.I)


def guidance_caveats(doc: dict) -> list:
    """The release's own statements that a result includes items outside its earlier guidance ('Earnings per share included a 3-cent benefit for items that were
    not in the company's original guidance.'): shown beside the comparison with that guidance, never used to adjust it."""
    out = []
    for line in doc["lines"]:
        for sentence in SENTENCE_BREAK.split(line):
            if GUIDANCE_CAVEAT.search(sentence) and len(sentence) < 600 and sentence.strip() not in out:
                out.append(sentence.strip())
    return out


def guidance_comparisons(facts: list, current_period: str, guidance: list, guidance_doc: dict | None, aliases=()) -> tuple[list, list]:
    """ACTUAL vs the company's EARLIER guidance for the same period. Compared only when metric, basis (or unstated), period, unit and currency agree. The period
    agrees when the outlook names the column's label or the quarter the release states for it (aliases); amounts in thousands, millions or billions are compared
    after restating the guidance in the actual's unit."""
    rows, withheld = [], []
    if guidance_doc is None:
        return rows, [{"reason": "no comparison document supplied; earlier company guidance for this period is unknown"}]
    current = [f for f in facts if f["period"] == current_period]
    ambiguous = _ambiguous_fact_keys(current)
    for group in _guidance_groups(guidance).values():
        g = group[0]
        if g["target_period"] != current_period and g["target_period"] not in aliases:
            withheld.append({"metric": g["metric"], "reason": f"the comparison document's outlook is for {g['target_period']}, not {current_period}"})
            continue
        if len({_guidance_values(item) for item in group}) != 1:
            withheld.append({"metric": g["metric"], "basis": g["basis"], "status": "DATA_CONFLICT",
                             "reason": "conflicting earlier guidance values/ranges; comparison withheld",
                             "guidance_evidence": [item["quote"] for item in group]})
            continue
        candidates = [f for f in current if f["metric"] == g["metric"] and (g["basis"] == "UNSTATED" or f["basis"] == g["basis"])]
        if not candidates:
            withheld.append({"metric": g["metric"], "basis": g["basis"], "reason": "the current release has no matching reported figure"})
            continue
        if any(_fact_key(f) in ambiguous for f in candidates):
            withheld.append({"metric": g["metric"], "basis": g["basis"], "status": "DATA_CONFLICT",
                             "reason": "conflicting current actuals; comparison withheld", "actual_evidence": [f["evidence"] for f in candidates]})
            continue
        if g["unit"] != "percent" and (g["currency"] is None or any(f["currency"] is None for f in candidates)):
            withheld.append({"metric": g["metric"], "basis": g["basis"], "status": "CURRENCY_UNRESOLVED",
                             "reason": "the currency of the actual or of the guidance is unresolved; no comparison is made"})
            continue
        if g["unit"] in _UNIT_FACTOR:
            # Restate the guidance in the unit of the reported figure ('$19.5 to $20.5 million' against a table in thousands).
            target_units = {f["unit"] for f in candidates if f["unit"] in _UNIT_FACTOR}
            if len(target_units) == 1 and g["unit"] not in target_units:
                to = target_units.pop()
                factor = _UNIT_FACTOR[g["unit"]] / _UNIT_FACTOR[to]
                restated = Decimal(g["midpoint"]) * factor
                actuals = [Decimal(f["value"]) for f in candidates if f["unit"] == to]
                # Only a plain restatement: an actual within a factor of three of the restated midpoint. Anything further apart is more likely a misread scale than a
                # miss of that size, and stays withheld as a unit mismatch.
                if restated > 0 and all(restated / 3 <= a <= restated * 3 for a in actuals):
                    g = {**g, "unit": to, "conversion": f"{g['unit']} to {to}",
                         **{k: _decimal_string(Decimal(g[k]) * factor) if g[k] is not None else None for k in ("midpoint", "low", "high")}}
        compatible = [f for f in candidates if f["unit"] == g["unit"] and f["currency"] == g["currency"]]
        if not compatible:
            withheld.append({"metric": g["metric"], "reason": "unit or currency mismatch between actual and guidance; no conversion supported"})
            continue
        candidates = _unambiguous_facts(compatible)
        # revenue is printed under both GAAP and non-GAAP; the same value is compared once and the duplicate listed
        act = candidates[0]
        same_basis = " and ".join(sorted({c["basis"] for c in candidates})) + (" (identical)" if len(candidates) > 1 else "")
        if len({c["value"] for c in candidates}) > 1:
            withheld.append({"metric": g["metric"], "reason": "the current release reports different values for this metric under different bases and the guidance states no basis"})
            continue
        if act["unit"] != g["unit"] or (act["currency"] or None) != (g["currency"] or None):
            withheld.append({"metric": g["metric"], "reason": f"unit or currency mismatch (reported {act['unit']}/{act['currency']}, guidance {g['unit']}/{g['currency']}); no conversion supported"})
            continue
        a, mid = Decimal(act["value"]), Decimal(g["midpoint"])
        low = Decimal(g["low"]) if g["low"] is not None else None
        high = Decimal(g["high"]) if g["high"] is not None else None
        position = "NO_RANGE_GIVEN" if low is None else "ABOVE_RANGE" if a > high else "BELOW_RANGE" if a < low else "WITHIN_RANGE"
        rows.append({"label": "ACTUAL vs EARLIER COMPANY GUIDANCE", "metric": g["metric"], "basis": same_basis if g["basis"] == "UNSTATED" else g["basis"], "period": current_period,
                     "unit": g["unit"], "currency": g["currency"], "actual": act["value"], "guidance_midpoint": g["midpoint"], "guidance_low": g["low"], "guidance_high": g["high"], "guidance_band": g["band"],
                     "difference_vs_midpoint": _decimal_string(a - mid), "difference_unit": "percentage points" if g["unit"] == "percent" else g["unit"],
                     "difference_pct": None if g["unit"] == "percent" or _pct(a - mid, mid) is None else _decimal_string(round(_pct(a - mid, mid), 2)),
                     "position": position, "conversion": g["conversion"], "guidance_quote": g["quote"], "actual_evidence": act["evidence"],
                     "currency_assumed": g["unit"] != "percent" and ((g.get("currency_basis") or "") == ASSUMED or (act["evidence"].get("currency_basis") or "") == ASSUMED)})
    return rows, withheld


# ---------------------------------------------------------------- time and sources

def sec_acceptance(headers_html: str) -> str | None:
    """The filing's own SGML-header acceptance time (New York clock, YYYYMMDDHHMMSS) as a UTC ISO timestamp."""
    stamps = set(re.findall(r"ACCEPTANCE-DATETIME>\s*(\d{14})(?!\d)", html.unescape(headers_html or "")))
    if len(stamps) != 1:
        return None  # none, or a header that disagrees with itself: no acceptance time is taken from it
    ny = datetime.strptime(stamps.pop(), "%Y%m%d%H%M%S").replace(tzinfo=ZoneInfo("America/New_York"))
    return fmt_ts(ny)


def has_dot_segments(path: str) -> bool:
    """A URL path with '.' or '..' segments (also percent-encoded) names a different resource after normalisation; such URLs are refused."""
    from urllib.parse import unquote
    return any(seg in (".", "..") for seg in unquote(path).split("/"))


def fetch_url(url: str, contact: str | None = None) -> bytes:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or has_dot_segments(parts.path):
        raise EarningsError("only plain https URLs (no '.' or '..' path segments) are fetched; or download the file and pass its path")
    agent = "KOD-Machine research"
    if parts.hostname.endswith("sec.gov"):
        contact = contact or os.environ.get("KOD_SEC_CONTACT", "").strip()
        if "@" not in (contact or ""):
            raise EarningsError("sec.gov requires a contact in the request: set KOD_SEC_CONTACT to your email address (it is sent in the User-Agent and never stored)")
        agent += " " + contact
    request = urllib.request.Request(url, headers={"User-Agent": agent})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read(40_000_000)
    except Exception as exc:
        raise EarningsError(f"could not fetch {url}: {type(exc).__name__}; download the file manually and pass its path") from exc


def sec_headers_url(url: str) -> str | None:
    if has_dot_segments(urlsplit(url).path):
        return None
    m = re.match(r"(https://www\.sec\.gov/Archives/edgar/data/\d+/)(\d{10})(\d{2})(\d{6})/", url)
    return f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}/{m.group(2)}-{m.group(3)}-{m.group(4)}-index-headers.html" if m else None


# ---------------------------------------------------------------- bundle and report

def build_bundle(company, ticker, venue, docs, consensus_docs, current_period, currency, current_info=None):
    """A KOD-WORKBENCH-v1 bundle. docs: list of dicts (role current|comparison) with parsed fields. Observations are the current release's reported figures (ACTUAL for the current
    period column, PRIOR for earlier columns, kept apart) and any supplied consensus."""
    sec_id = f"{ticker}.{venue}"
    bundle = {"schema_version": workbench.SCHEMA, "synthetic": False,
              "securities": [{"security_id": sec_id, "issuer_id": company, "ticker": ticker, "venue": venue, "currency": currency or "UNKNOWN"}], "documents": []}
    for d in docs:
        entry = {"document_id": d["document_id"], "event_id": d["event_id"], "security_ids": [sec_id], "source_kind": "PRIMARY", "publisher": company, "source_url": d["source_url"],
                 "source_family": "issuer-earnings-release", "published_at": d["published_at"], "observed_at": d["observed_at"], "title": d["title"], "text": d["text"], "observations": []}
        for f in d.get("facts", []):
            if f["period"] == current_period:
                role = "ACTUAL"
            elif current_info is not None and earlier(f["period_info"], current_info) is True:
                role = "PRIOR"
            else:
                continue  # a later column, or another duration kind, is not a prior period of this release
            entry["observations"].append({"metric": f"{f['metric']} [{f['basis']}]", "role": role, "value": f["value"], "unit": f["unit"], "currency": f["currency"], "period": f["period"],
                                          "source_quote": f["evidence"]["quote"]})
        bundle["documents"].append(entry)
    for c in consensus_docs:
        bundle["documents"].append(c)
    return bundle


def load_consensus(path: str, sec_id: str, event_id: str) -> list:
    """Optional consensus file: a JSON list of {metric, basis, period, value, unit, currency, published_at, observed_at, source_url, publisher, text, quote}. Each becomes a
    CONSENSUS observation in a SECONDARY document; the workbench then applies its own compatibility and ordering rules."""
    try:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EarningsError(f"consensus file unreadable: {exc}") from exc
    if not isinstance(rows, list):
        raise EarningsError("consensus file must be a JSON list of estimate objects")
    out = []
    for i, r in enumerate(rows):
        try:
            out.append({"document_id": f"consensus-{i + 1}", "event_id": event_id, "security_ids": [sec_id], "source_kind": "SECONDARY", "publisher": r["publisher"],
                        "source_url": r["source_url"], "source_family": None, "published_at": r["published_at"], "observed_at": r.get("observed_at"),
                        "title": f"Consensus estimate: {r['metric']} {r['period']}", "text": r["text"],
                        "observations": [{"metric": f"{r['metric']} [{r.get('basis', 'UNSTATED')}]", "role": "CONSENSUS", "value": str(r["value"]), "unit": r["unit"],
                                          "currency": r.get("currency"), "period": r["period"], "source_quote": r["quote"]}]})
        except KeyError as exc:
            raise EarningsError(f"consensus entry {i + 1}: missing field {exc}") from exc
    return out


def analyse(company, ticker, venue, primary, comparison, as_of, mode, consensus_path=None, currency_override=None, period_override=None):
    """primary / comparison: dicts with doc (read_document), source_url, published_at, observed_at, title. Returns the structured result (also the JSON companion).

    currency_override: the analyst's record of the reporting currency (an ISO code, or {currency, recorded_by, recorded_at, rationale}); it fills a currency the documents do
    not state and is reported as a conflict where they state another. period_override: the analyst's choice of the reported quarter (a column label, or {period, ...}) for a
    release that does not state it. Both are kept in the result as analyst inputs."""
    override_currency = analyst_currency(currency_override)
    facts, issues = extract_table_facts(primary["doc"], override_currency)
    _attach_source(facts, primary, "current")
    head = headline_checks(primary["doc"], facts, period_override, primary.get("published_at"))
    resolution = head["resolution"]
    if resolution["status"] != "RESOLVED":
        if not resolution["candidates"]:
            raise EarningsError(f"{primary['doc']['name']}: no earnings summary table with period-labelled columns (for example 'Q3 FY25  Q2 FY25' or 'Three Months Ended' over dated columns) and "
                                "recognised rows (revenue, net income, diluted EPS) was found. This version supports an official earnings press release in HTML; for SEC filers, use the 8-K Exhibit 99.1 .htm file")
        return _period_withheld(company, ticker, venue, primary, comparison, as_of, mode, facts, issues, head, override_currency, period_override)
    current_period = resolution["period"]
    current_info = next(f["period_info"] for f in facts if f["period"] == current_period)
    cp = qn_period(current_period)
    for key in ("quarter_ended", "fiscal_quarter_title"):
        h = head[key]
        if h and h.get("quarter") and cp and h["quarter"] != cp["q"]:
            issues.append({"code": "PERIOD_MISMATCH", "where": key, "detail": f"table column says {current_period}, the text says quarter {h['quarter']} ({h['quote']})"})
    if head["fiscal_quarter_title"] and cp and head["fiscal_quarter_title"]["fiscal_year"] % 100 != cp["yy"]:
        issues.append({"code": "PERIOD_MISMATCH", "where": "fiscal_quarter_title", "detail": f"table says year {cp['yy']}, title says fiscal {head['fiscal_quarter_title']['fiscal_year']}"})
    for chk in head["checks"]:
        if not chk["ok"]:
            issues.append({"code": "HEADLINE_TABLE_CONFLICT", "where": chk["check"], "detail": f"{chk['headline']} disagrees with the table; both are kept, nothing is averaged"})
    guidance_next, g_issues = extract_guidance(primary["doc"], override_currency, facts, _own_quarter(head, current_period))
    issues += g_issues
    comp_facts, comp_guidance, comp_issues, comp_current = [], [], [], None
    if comparison:
        comp_facts, ci = extract_table_facts(comparison["doc"], override_currency)
        _attach_source(comp_facts, comparison, "comparison")
        comp_head = headline_checks(comparison["doc"], comp_facts, published_at=comparison.get("published_at"))
        comp_resolution = comp_head["resolution"]
        comp_current = comp_resolution["period"]
        if comp_current is None:
            ci = ci + [{"code": "COMPARISON_PERIOD_UNRESOLVED", "where": "comparison document", "detail": f"its reported quarter could not be resolved ({comp_resolution['reason']}); its figures fill no comparison"}]
        cg, gi = extract_guidance(comparison["doc"], override_currency, comp_facts, _own_quarter(comp_head, comp_current))
        comp_guidance, comp_issues = cg, ci + gi
    event_id = f"{ticker}-{current_period.replace(' ', '-')}-earnings"
    currency = next((f["currency"] for f in facts if f["period"] == current_period and f["currency"]), None)
    docs = [{"document_id": "current-release", "event_id": event_id, **{k: primary[k] for k in ("source_url", "published_at", "observed_at", "title")}, "text": primary["doc"]["text"], "facts": facts}]
    if comparison:
        docs.append({"document_id": "comparison-release", "event_id": f"{ticker}-{(comp_current or 'unknown-period').replace(' ', '-')}-earnings",
                     **{k: comparison[k] for k in ("source_url", "published_at", "observed_at", "title")}, "text": comparison["doc"]["text"], "facts": []})
    sec_id = f"{ticker}.{venue}"
    consensus_docs = load_consensus(consensus_path, sec_id, event_id) if consensus_path else []
    bundle = build_bundle(company, ticker, venue, docs, consensus_docs, current_period, currency, current_info)
    report = workbench.build_report(bundle, as_of, query="", security_id=sec_id, limit=50, mode=mode)
    excluded = {row["document_id"]: row["reasons"] for row in report["excluded_documents"]}
    cutoff_ok = "current-release" not in excluded
    result = {"schema_version": SCHEMA, "parser_version": PARSER_VERSION, "research_only": True, "entry_permission": False, "company": company, "ticker": ticker, "venue": venue, "event": "EARNINGS_ANNOUNCEMENT",
              "period": current_period, "as_of": report["as_of"], "mode": mode, "cutoff": {"current_release_eligible": cutoff_ok, "excluded": excluded},
              "sources": [{"role": "current", "name": primary["doc"]["name"], "source_url": primary["source_url"], "sha256": primary["doc"]["raw_sha256"], "bytes": primary["doc"]["bytes"],
                           "published_at": primary["published_at"], "published_basis": primary["published_basis"], "observed_at": primary["observed_at"], "observed_basis": primary["observed_basis"]}],
              "bundle_sha256": report["input_bundle_sha256"], "workbench_report": report, "issues": issues, "headline": head,
              "period_resolution": {k: resolution.get(k) for k in ("status", "period", "end", "basis", "evidence", "aliases", "release_reason")},
              "analyst_inputs": {"reporting_currency": override_currency, "period": period_override}}
    if comparison:
        result["sources"].append({"role": "comparison", "name": comparison["doc"]["name"], "source_url": comparison["source_url"], "sha256": comparison["doc"]["raw_sha256"], "bytes": comparison["doc"]["bytes"],
                                  "published_at": comparison["published_at"], "published_basis": comparison["published_basis"], "observed_at": comparison["observed_at"], "observed_basis": comparison["observed_basis"]})
    if not cutoff_ok:
        result.update(facts=[], prior_period=[], guidance_comparisons=[], guidance_not_compared=[{"reason": "current release is not eligible at the information cutoff: " + ", ".join(excluded["current-release"])}],
                      next_guidance=[], consensus=[], consistency_with_comparison=[])
        # The report is a cutoff-specific read model, not a copy of the private
        # parser state. Even hidden headline/check/issue fields can leak values.
        result["headline"] = {"paragraph": None, "quarter_ended": None, "quarter_ended_all": [], "fiscal_quarter_title": None, "reported_quarter": [], "revenue_headline": None,
                              "eps_headline": {}, "checks": []}
        # Nothing read from a document that is not available at the cutoff is shown, not even which period it reports or whether that was established.
        result.update(period=None, period_resolution={"status": "WITHHELD_BY_CUTOFF"}, issues=[], reporting_currency={})
        return result

    def public(f):
        out = {k: v for k, v in f.items() if k not in ("printed_changes", "period_info")}
        end = f["period_info"]["end"]
        stated = f["period"] == current_period and resolution["basis"] == "RELEASE_STATEMENT" and resolution["end"]
        out["period_end"] = end.isoformat() if end else (resolution["end"] if stated else None)
        out["period_end_basis"] = "column heading" if end else ("release statement: " + "; ".join(resolution["evidence"]) if stated else None)
        out["period_kind"] = f["period_info"]["kind"]
        return out

    result["facts"] = [public(f) for f in facts if f["period"] == current_period]
    monetary = [f for f in result["facts"] if f["unit"] != "percent"]
    result["reporting_currency"] = {"currencies": sorted({f["currency"] or "UNRESOLVED" for f in monetary}),
                                    "bases": sorted({f["evidence"].get("currency_basis") or "NONE" for f in monetary}),
                                    "statements": document_currency_statements(primary["doc"]), "analyst_override": override_currency}
    result["other_period_figures"] = [public(f) for f in facts if f["period"] != current_period]
    comp_ok = comparison is not None and "comparison-release" not in excluded
    result["prior_period"] = prior_period_comparisons(facts, current_period, comp_facts if comp_ok else None, comp_current if comp_ok else None)
    if comparison and not comp_ok:
        gcomp, gwith = [], [{"reason": "comparison document is not eligible at the information cutoff: " + ", ".join(excluded["comparison-release"])}]
    else:
        gcomp, gwith = guidance_comparisons(facts, current_period, comp_guidance if comp_ok else [], comparison if comp_ok else None, resolution.get("aliases") or ())
        if comp_ok and not (comparison["published_at"] and primary["published_at"] and parse_ts(comparison["published_at"]) < parse_ts(primary["published_at"])):
            gcomp, gwith = [], gwith + [{"reason": "the comparison document must be published strictly before the current release; its publication time is unknown or not earlier"}]
    result["guidance_comparisons"], result["guidance_not_compared"] = gcomp, gwith
    result["guidance_caveats"] = guidance_caveats(primary["doc"]) if gcomp else []
    result["consistency_with_comparison"] = []
    if comp_ok and comp_current:
        earlier = {_fact_key(f): f for f in _unambiguous_facts(comp_facts) if f["period"] == comp_current}
        for f in _unambiguous_facts(facts):
            e = earlier.get(_fact_key(f)) if f["period"] != current_period else None
            if e is not None:
                result["consistency_with_comparison"].append({"metric": f["metric"], "basis": f["basis"], "period": f["period"], "earlier_release": e["value"], "printed_now": f["value"],
                                                              "agrees": Decimal(e["value"]) == Decimal(f["value"])})
    result["comparison_issues"] = comp_issues if comp_ok else []
    result["next_guidance"] = guidance_next
    consensus = []
    for card in report["search_results"]:
        if card["event_id"] == event_id:
            consensus = [c for c in card["comparisons"] if any(e["role"] == "CONSENSUS" for e in c["evidence"])]
    for c in consensus:
        if c["status"] == "OK" and c.get("currency") is None and c.get("unit") != "percent":
            c.update(status="CURRENCY_UNRESOLVED", actual=None, consensus=None, difference=None, difference_pct=None,
                     reason="the actual's currency is unresolved; a figure of unknown currency is not compared with an estimate")
    result["consensus"] = consensus
    return result


def _public_fact(f):
    out = {k: v for k, v in f.items() if k not in ("printed_changes", "period_info")}
    out["period_end"] = f["period_info"]["end"].isoformat() if f["period_info"]["end"] else None
    out["period_end_basis"] = "column heading" if f["period_info"]["end"] else None
    out["period_kind"] = f["period_info"]["kind"]
    return out


def _period_withheld(company, ticker, venue, primary, comparison, as_of, mode, facts, issues, head, override_currency, period_override):
    """The result for a release whose reported quarter is unresolved: no figure is labelled current or prior and no comparison is made. The recognised figures are listed by
    column (when the release is eligible at the cutoff) so the analyst can see the columns and record the period explicitly."""
    resolution = head["resolution"]
    sec_id = f"{ticker}.{venue}"
    docs = [{"document_id": "current-release", "event_id": f"{ticker}-unresolved-period-earnings", **{k: primary[k] for k in ("source_url", "published_at", "observed_at", "title")},
             "text": primary["doc"]["text"], "facts": []}]
    report = workbench.build_report(build_bundle(company, ticker, venue, docs, [], None, None), as_of, query="", security_id=sec_id, limit=50, mode=mode)
    excluded = {row["document_id"]: row["reasons"] for row in report["excluded_documents"]}
    eligible = "current-release" not in excluded
    sources = [{"role": role, "name": d["doc"]["name"], "source_url": d["source_url"], "sha256": d["doc"]["raw_sha256"], "bytes": d["doc"]["bytes"], "published_at": d["published_at"],
                "published_basis": d["published_basis"], "observed_at": d["observed_at"], "observed_basis": d["observed_basis"]}
               for role, d in (("current", primary), ("comparison", comparison)) if d]
    blank_head = {"paragraph": None, "quarter_ended": None, "fiscal_quarter_title": None, "reported_quarter": [], "revenue_headline": None, "eps_headline": {}, "checks": []}
    detail = f"{resolution['reason']}. Recognised quarter columns: {', '.join(resolution['candidates'])}. No figure is labelled current or prior under a guessed period"
    return {"schema_version": SCHEMA, "parser_version": PARSER_VERSION, "research_only": True, "entry_permission": False, "company": company, "ticker": ticker, "venue": venue,
            "event": "EARNINGS_ANNOUNCEMENT", "status": "PERIOD_UNRESOLVED" if eligible else "WITHHELD_BY_CUTOFF", "period": None, "as_of": report["as_of"], "mode": mode,
            "cutoff": {"current_release_eligible": eligible, "excluded": excluded}, "sources": sources, "bundle_sha256": report["input_bundle_sha256"], "workbench_report": report,
            "issues": ([{"code": "PERIOD_UNRESOLVED", "where": "current release", "detail": detail}] + issues) if eligible else [],
            "headline": {k: v for k, v in head.items() if k != "resolution"} if eligible else blank_head,
            "period_resolution": {"status": "UNRESOLVED", "period": None, "end": None, "basis": None, "evidence": [], "aliases": [],
                                  "reason": resolution["reason"], "candidates": resolution["candidates"]} if eligible else {"status": "WITHHELD_BY_CUTOFF"},
            "analyst_inputs": {"reporting_currency": override_currency, "period": period_override},
            "facts": [], "other_period_figures": [_public_fact(f) for f in facts] if eligible else [], "prior_period": [], "guidance_comparisons": [],
            "guidance_not_compared": [{"reason": "the reported period is unresolved; no guidance comparison is made"}], "next_guidance": [], "consensus": [],
            "consistency_with_comparison": [], "comparison_issues": [], "reporting_currency": {"currencies": [], "bases": [], "statements": {}, "analyst_override": override_currency}}


# ---------------------------------------------------------------- inputs

def prepare_source(ref, source_url=None, published_at=None, sec_headers=None, retrieved_at=None, now=None, contact=None, save_dir=None):
    """Load one document from a local path or an https URL and settle its identity and times without guessing.

    publication time: --published-at, else the SEC header acceptance time (a file given with --sec-headers, or fetched next to a sec.gov URL), else UNKNOWN (never the download time).
    observation time: the recorded retrieval time if given, else the moment this program loaded the file (a local file's real earlier retrieval is unknown)."""
    now = now or utc_now()
    is_url = isinstance(ref, str) and ref.startswith(("http://", "https://"))
    headers_text = None
    if is_url:
        raw = fetch_url(ref, contact)
        observed, observed_basis = now, "fetched by this run"
        url = ref
        hurl = sec_headers_url(ref)
        if published_at is None and sec_headers is None and hurl:
            headers_text = fetch_url(hurl, contact).decode("utf-8", "replace")
        if save_dir:
            Path(save_dir).mkdir(parents=True, exist_ok=True)
            (Path(save_dir) / Path(urlsplit(ref).path).name).write_bytes(raw)
    else:
        path = Path(ref)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise EarningsError(f"cannot read {ref}: {exc.strerror or exc}") from exc
        url = source_url or LOCAL_URL + path.name
        if retrieved_at:
            try:
                observed, observed_basis = fmt_ts(parse_ts(retrieved_at)), "retrieval time supplied by the user"
            except ValueError as exc:
                raise EarningsError(f"--retrieved-at: {exc}") from exc
        else:
            observed, observed_basis = now, "local file loaded by this run (its earlier retrieval time is unknown)"
    if published_at:
        try:
            published, basis = fmt_ts(parse_ts(published_at)), "publication time supplied by the user"
        except ValueError as exc:
            raise EarningsError(f"--published-at: {exc}") from exc
    else:
        if sec_headers:
            try:
                headers_text = Path(sec_headers).read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise EarningsError(f"cannot read SEC header file: {exc.strerror or exc}") from exc
        published = sec_acceptance(headers_text) if headers_text else None
        basis = "SEC acceptance time from the filing's own header (New York clock converted to UTC)" if published else "UNKNOWN: no publication time was supplied or found; download time is not substituted"
    doc = read_document(raw, Path(urlsplit(url).path).name or "document")
    m = re.search(r"<title>(.*?)</title>", raw.decode("utf-8", "replace"), re.I | re.S)
    title = next((l for l in doc["lines"] if re.search(r"announces|reports|results", l, re.I)), None) or (" ".join(m.group(1).split()) if m else doc["name"])
    return {"doc": doc, "source_url": url, "published_at": published, "published_basis": basis, "observed_at": observed, "observed_basis": observed_basis, "title": title[:200]}


# ---------------------------------------------------------------- note

NAMES = {"revenue": "Revenue", "gross_margin": "Gross margin", "operating_expenses": "Operating expenses", "operating_income": "Operating income", "net_income": "Net income",
         "eps_diluted": "Diluted EPS"}


def _unit(unit, currency):
    if unit == "percent":
        return "%"
    if unit == "per_share":
        return f"{currency or '?'} per share"
    return f"{currency or '?'} {unit}"


def _link(url, label):
    if urlsplit(url).hostname and urlsplit(url).hostname.endswith("example.invalid"):
        return _md(label) + " (local file; no public URL supplied)"
    return f"[{_md(label)}](<{quote(url, safe=':/?&=#%+@,;!$()*-._~')}>)"


def _row(*cells):
    return "| " + " | ".join(_md(c) for c in cells) + " |"


def _ref(ev):
    return f"table {ev['table']}, row {ev['row']}"


def _comparison_source(row):
    refs = [_md(row["source"])]
    for label, ev in zip(("actual", "prior"), row["evidence"]):
        name = f"{label}: {ev.get('document_role', 'source')} release, {_ref(ev)}"
        # Autolinks keep the label escaped while permitting deliberate source
        # navigation; untrusted Markdown link syntax is never copied through.
        if ev.get("source_url"):
            url = quote(ev["source_url"], safe=":/?&=#%+@,;!$()*-._~")
            refs.append(f"{_md(name)} <{url}>")
        else:
            refs.append(_md(name))
    return "; ".join(refs)


def questions(result):
    q = []
    if not result["consensus"]:
        q.append("Obtain a dated pre-release consensus for revenue and diluted EPS (same basis, period and currency, published before the release) before judging the result against expectations.")
    for g in result["guidance_comparisons"]:
        if g["position"] in ("ABOVE_RANGE", "BELOW_RANGE"):
            q.append(f"{NAMES[g['metric']]} ({g['basis']}) was {g['position'].replace('_', ' ').lower().replace(' range', ' the range')} the company guided earlier. What explains the gap? The release's own commentary is not extracted; read it.")
    def one_actual(metric, basis=None):
        candidates = [f for f in result["facts"] if f["metric"] == metric and (basis is None or f["basis"] == basis)]
        if _ambiguous_fact_keys(candidates):
            return None
        values = {(Decimal(f["value"]), f["unit"], f["currency"], f["period"]) for f in candidates}
        return candidates[0] if len(values) == 1 else None

    gaap, non = one_actual("eps_diluted", "GAAP"), one_actual("eps_diluted", "NON-GAAP")
    if (gaap and non and gaap["unit"] == non["unit"] and gaap["currency"] == non["currency"] and gaap["currency"] is not None
            and Decimal(gaap["value"]) != Decimal(non["value"])):
        q.append(f"Non-GAAP diluted EPS differs from GAAP by {_decimal_string(Decimal(non['value']) - Decimal(gaap['value']))}. Which reconciling items account for it? (The release's reconciliation tables are not extracted.)")
    for p in result["prior_period"]:
        if p["relation"] == "SEQUENTIAL" and p["unit"] == "percent" and Decimal(p["difference"]) < 0 and p["basis"] == "GAAP":
            q.append(f"{NAMES[p['metric']]} (GAAP) fell {_decimal_string(abs(Decimal(p['difference'])))} percentage points from the previous quarter. Does the company explain it in the supplied sources?")
    if result["next_guidance"]:
        revenues = [g for g in _unambiguous_guidance(result["next_guidance"]) if g["metric"] == "revenue"]
        rev = revenues[0] if len(revenues) == 1 else None
        cur = one_actual("revenue")
        if rev and cur and rev["unit"] == cur["unit"] and rev["currency"] == cur["currency"] and cur["currency"] is not None:
            change = _pct(Decimal(rev["midpoint"]) - Decimal(cur["value"]), Decimal(cur["value"]))
            if change is not None:
                q.append(f"The company guides {rev['target_period']} revenue at a midpoint of {rev['midpoint']} ({_unit(rev['unit'], rev['currency'])}), {_fmt(round(change, 1))}% against the quarter just reported. How does that compare with consensus once available?")
    for i in result["issues"]:
        if i["code"] in ("HEADLINE_TABLE_CONFLICT", "PERIOD_MISMATCH", "CURRENT_PERIOD_AMBIGUOUS"):
            q.append(f"Resolve before relying on the figures: {i['detail']}.")
    return q


def render_note(result):
    L = []
    add = L.append
    title = result["period"] or ("period withheld by the information cutoff" if not result["cutoff"]["current_release_eligible"] else "reported period unresolved")
    add(f"# Earnings research note: {_md(result['company'])} ({_md(result['ticker'])}), {_md(title)}")
    add("")
    add("> Research aid only. Not a recommendation, forecast or entry permission. It opened no case, wrote no ledger and placed no order.")
    add("")
    pr = result.get("period_resolution") or {}
    quotes = [e for e in pr.get("evidence", []) if isinstance(e, str)]
    if pr.get("basis") == "ANALYST_OVERRIDE":
        established = "chosen by the analyst because the release does not establish it" + (f" ({pr['release_reason']})" if pr.get("release_reason") else "")
    elif quotes:
        established = "stated by the release: " + "; ".join(f"'{e}'" for e in quotes) + ("; the analyst's record agrees" if "agrees" in (pr.get("basis") or "") else "")
    elif result.get("status") == "PERIOD_UNRESOLVED":
        established = "see the reason below"
    else:
        established = None
    period_line = "withheld with the figures" if established is None else f"{result['period'] or 'unresolved'}, {established}"
    add(f"- **Event:** earnings announcement (official release)  \n- **Reporting period:** {_md(period_line)}  \n- **Information cutoff:** {_md(result['as_of'])} (mode: {_md(result['mode'])})")
    if result["mode"] == "public":
        add("- **Historical reconstruction:** documents are admitted by their publication time only. This does not show what KOD possessed at the cutoff; the files were retrieved later (see Sources).")
    add("")
    if not result["cutoff"]["current_release_eligible"]:
        add("## Result withheld by the information cutoff")
        add("")
        add(f"The current release is not available at the cutoff: {_md(', '.join(result['cutoff']['excluded']['current-release']))}. No figures are shown, because a point-in-time note must not use information from after its cutoff.")
        add("")
    elif result.get("status") == "PERIOD_UNRESOLVED":
        pr = result["period_resolution"]
        add("## Result withheld: the reported period is unresolved")
        add("")
        add(f"{_md(pr['reason'])}. No figure is labelled current or prior and no comparison is made, because a guessed period could call a later column \"prior\".")
        add("")
        add(f"Recognised quarter columns: {_md(', '.join(pr['candidates']))}. If the release itself establishes which one it reports, record it explicitly and regenerate the note.")
        add("")
        if result["other_period_figures"]:
            add("| Metric | Basis | Column | Value | Unit | Evidence (exact table row) |")
            add("|---|---|---|---|---|---|")
            for f in result["other_period_figures"]:
                add(_row(NAMES[f["metric"]], f["basis"], f["period"], f["value"], _unit(f["unit"], f["currency"]), f"{_ref(f['evidence'])}: {f['evidence']['quote']}"))
            add("")
        for i in result["issues"][1:]:
            add(f"- {_md(i['code'])} ({_md(i['where'])}): {_md(i['detail'])}")
        add("")
    else:
        h = result["headline"]
        add("## What the source says")
        add("")
        add("Reported facts, quoted from the release (not paraphrased):")
        add("")
        if h["paragraph"]:
            add("> " + _md(h["paragraph"]))
        else:
            add("No headline paragraph matched the supported wording ('reported ... quarter ended ...'); see the figures below.")
        add("")
        add("## Reported figures (current period)")
        add("")
        add("| Metric | Basis | Period | Value | Unit | Evidence (exact table row) | Method / flags |")
        add("|---|---|---|---|---|---|---|")
        for f in result["facts"]:
            add(_row(NAMES[f["metric"]], f["basis"], f["period"], f["value"], _unit(f["unit"], f["currency"]), f"{_ref(f['evidence'])}: {f['evidence']['quote']}", f["method"] + ("; " + ", ".join(f["flags"]) if f["flags"] else "")))
        add("")
        add("## Comparisons (three different things, never mixed)")
        add("")
        add("### A. Actual vs prior-period actual")
        add("")
        add("Calculation from the current release's comparative columns or the explicitly identified earlier release. Each row identifies both sources; the prior actual is a reported number, not an expectation.")
        add("")
        if result["prior_period"]:
            add("| Metric | Basis | Unit | Current | Prior period | Prior actual | Difference | Change % | Relation | Agrees with the release's printed change | Source |")
            add("|---|---|---|---|---|---|---|---|---|---|---|")
            for p in result["prior_period"]:
                chk = p["printed_change_check"]
                add(_row(NAMES[p["metric"]], p["basis"], _unit(p["unit"], p["currency"]) + (" (assumed)" if p.get("currency_assumed") and p["source"].startswith("figure from") else ""), p["actual"], p["prior_period"], p["prior_actual"], f"{p['difference']} {p['difference_unit'] if p['unit']=='percent' else ''}".strip(), p["difference_pct"] or "n/a", p["relation"],
                         "not checked" if chk is None else f"{'yes' if chk['agrees'] else 'NO'} (printed: {chk['printed']})") + " " + _comparison_source(p) + " |")
        else:
            add("No comparative columns were extracted.")
        add("")
        add("### B. Actual vs earlier company guidance")
        add("")
        if result["guidance_comparisons"]:
            add("Guidance is the company's own outlook issued before the period, taken from the comparison document.")
            add("")
            add("| Metric | Basis | Unit | Actual | Guided midpoint | Guided range | Difference vs midpoint | Diff % | Position | Guidance quote |")
            add("|---|---|---|---|---|---|---|---|---|---|")
            for g in result["guidance_comparisons"]:
                rng = f"{g['guidance_low']} to {g['guidance_high']}" if g["guidance_low"] else g["guidance_band"]
                add(_row(NAMES[g["metric"]], g["basis"], _unit(g["unit"], g.get("currency")) + (" (assumed)" if g.get("currency_assumed") else ""), g["actual"], g["guidance_midpoint"], rng, g["difference_vs_midpoint"], g["difference_pct"] or "n/a", g["position"], g["guidance_quote"]))
            add("")
            for c in result.get("guidance_caveats", []):
                add(f"- The release says: \"{_md(c)}\" (the comparison above is not adjusted for it)")
            if result.get("guidance_caveats"):
                add("")
        for w in result["guidance_not_compared"]:
            add(f"- Not compared: {_md(w.get('metric', 'all'))}: {_md(w['reason'])}")
        add("")
        add("### C. Actual vs consensus")
        add("")
        if not result["consensus"]:
            add("**CONSENSUS UNKNOWN.** No dated analyst consensus was supplied, and none is invented. No surprise is calculated.")
        else:
            for c in result["consensus"]:
                add(f"- {_md(c['metric'])} / {_md(c['period'])}: {_md(c['status'])}; actual={_md(c['actual'])}, consensus={_md(c['consensus'])}, difference={_md(c['difference'])}, percentage={_md(c['difference_pct'])}" + (f" ({_md(c['reason'])})" if c["reason"] else ""))
        add("")
        add("## Company outlook given in this release (reported, not our forecast)")
        add("")
        if result["next_guidance"]:
            add("| Metric | Basis | Target period | Midpoint | Range | Quote |")
            add("|---|---|---|---|---|---|")
            for g in result["next_guidance"]:
                assumed = " (currency assumed from \"$\")" if g.get("currency_basis") == ASSUMED else (" (currency unresolved)" if g["unit"] != "percent" and not g["currency"] else "")
                add(_row(NAMES[g["metric"]], g["basis"], g["target_period"], f"{g['midpoint']} ({_unit(g['unit'], g['currency'])}){assumed}", f"{g['low']} to {g['high']}" if g["low"] else g["band"], g["quote"]))
        else:
            add("No outlook figures were extracted.")
        add("")
        add("## Calculations and interpretation")
        add("")
        add("Calculations are the differences above. **Interpretation: none offered.** This tool does not judge materiality, management intent, market expectations, price reaction or valuation.")
        add("")
        add("## Conflicts, unknowns and limitations")
        add("")
        for chk in result["headline"]["checks"]:
            add(f"- Check: {_md(chk['check'])}: {'consistent' if chk['ok'] else 'CONFLICT'}.")
        for i in result["issues"]:
            add(f"- {_md(i['code'])} ({_md(i['where'])}): {_md(i['detail'])}")
        for i in result.get("comparison_issues", []):
            add(f"- Comparison document: {_md(i['code'])} ({_md(i['where'])}): {_md(i['detail'])}")
        cons = result["consistency_with_comparison"]
        if cons:
            bad = [c for c in cons if not c["agrees"]]
            add(f"- Prior-period figures printed in the current release vs the earlier release: {len(cons) - len(bad)} of {len(cons)} agree." + ("" if not bad else " DIFFERENT: " + "; ".join(_md(f"{c['metric']} {c['basis']} {c['period']}: earlier {c['earlier_release']}, now {c['printed_now']}") for c in bad)))
        rc = result.get("reporting_currency") or {}
        how = {"ASSUMED_FROM_$_SIGN": "assumed from the \"$\" sign because no currency statement was found (confirm in the filing, or record it explicitly)",
               "TABLE_STATEMENT": "stated in the table caption", "DOCUMENT_STATEMENT": "stated in the release text", "ANALYST_OVERRIDE": "recorded by the analyst",
               "CELL_SYMBOL": "printed with the figures", "NONE": "unresolved (see conflicts above)"}
        bases = "; ".join(how.get(b.split(" (")[0], b) + (" (the analyst's record agrees)" if "agrees" in b else "") for b in rc.get("bases", []))
        add(f"- Reporting currency of the current-period figures: {_md(', '.join(rc.get('currencies', [])) or 'none')}" + (f"; {_md(bases)}." if bases else "."))
        add("- Only the summary table and the outlook bullets are read. Segment results, reconciliations and management commentary are not extracted.")
        add("- Supplied times and quotes are assertions; the tool does not authenticate the source or prove historical availability.")
        add("")
        add("## Questions for the analyst")
        add("")
        for n, text in enumerate(questions(result), 1):
            add(f"{n}. {_md(text)}")
        add("")
    add("## Sources and times")
    add("")
    add("| Role | Document | SHA-256 of the file | Published (UTC) | Basis | Retrieved/observed | Basis |")
    add("|---|---|---|---|---|---|---|")
    for s in result["sources"]:
        add(_row(s["role"], s["name"], s["sha256"], s["published_at"] or "UNKNOWN", s["published_basis"], s["observed_at"], s["observed_basis"]))
    add("")
    for s in result["sources"]:
        add(f"- {_md(s['role'])}: {_link(s['source_url'], s['source_url'])}")
    add("")
    add(f"Workbench bundle SHA-256: `{result['bundle_sha256']}`. Generated by `kod.earnings` ({SCHEMA}).")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- command

def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m kod.earnings", description="Turn an official earnings press release (HTML) into a source-linked research note.")
    ap.add_argument("--company", required=True, help="company name as it should appear in the note")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--venue", default="UNSPECIFIED", help="listing venue code (default UNSPECIFIED)")
    ap.add_argument("--document", required=True, help="local .htm file or https URL of the earnings release")
    ap.add_argument("--source-url", help="public URL of a local --document (shown as its citation)")
    ap.add_argument("--published-at", help="timezone-aware ISO publication time (otherwise read from SEC headers, else unknown)")
    ap.add_argument("--sec-headers", help="the filing's *-index-headers.html (gives the SEC acceptance time)")
    ap.add_argument("--retrieved-at", help="when the local file was actually downloaded (never backdate)")
    ap.add_argument("--comparison-document", help="an earlier release whose outlook covers this period")
    ap.add_argument("--comparison-source-url")
    ap.add_argument("--comparison-published-at")
    ap.add_argument("--comparison-sec-headers")
    ap.add_argument("--comparison-retrieved-at")
    ap.add_argument("--consensus", help="optional JSON list of dated consensus estimates (see EARNINGS.md)")
    ap.add_argument("--as-of", help="information cutoff, timezone-aware ISO (default: now)")
    ap.add_argument("--mode", choices=("observed", "public"), default="observed", help="observed: also require retrieval before the cutoff; public: historical reconstruction by publication time")
    ap.add_argument("--currency", help="record the reporting currency (ISO code, e.g. CAD) where the release does not state it; a contradicting statement is reported as a conflict")
    ap.add_argument("--period", help="record the reported quarter (one of the release's column labels) where the release does not state it")
    ap.add_argument("--decision-note", help="why the --currency/--period record is right (kept with the note)")
    ap.add_argument("--out-dir", help="output directory (default earnings_note_<ticker>)")
    args = ap.parse_args(argv)
    try:
        now = utc_now()
        out = Path(args.out_dir or f"earnings_note_{re.sub(r'[^A-Za-z0-9_-]', '_', args.ticker)}")
        primary = prepare_source(args.document, args.source_url, args.published_at, args.sec_headers, args.retrieved_at, now, save_dir=out / "sources")
        comparison = None
        if args.comparison_document:
            comparison = prepare_source(args.comparison_document, args.comparison_source_url, args.comparison_published_at, args.comparison_sec_headers, args.comparison_retrieved_at, now,
                                        save_dir=out / "sources")
        decision = {"recorded_by": "analyst (command line)", "recorded_at": now, "rationale": args.decision_note}
        result = analyse(args.company, args.ticker, args.venue, primary, comparison, args.as_of or now, args.mode, args.consensus,
                         {"currency": args.currency, **decision} if args.currency else None, {"period": args.period, **decision} if args.period else None)
        out.mkdir(parents=True, exist_ok=True)
        (out / "note.md").write_text(render_note(result), encoding="utf-8")
        (out / "note.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    except (EarningsError, ValueError, InvalidOperation) as exc:
        print(f"earnings note error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {out / 'note.md'} and {out / 'note.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

