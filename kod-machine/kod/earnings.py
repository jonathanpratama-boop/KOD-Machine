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
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
import urllib.request
from zoneinfo import ZoneInfo

from .hashing import fmt_ts, parse_ts, sha256_bytes, sha256_text, utc_now
from . import workbench
from .workbench import _decimal_string

SCHEMA = "KOD-EARNINGS-NOTE-v1"
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

class _Page(HTMLParser):
    BLOCKS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip, self.buf, self.blocks = 0, [], []
        self.tables, self.stack, self.row, self.cell = [], [], None, None

    def _flush(self):
        text = " ".join("".join(self.buf).split())
        self.buf = []
        if text and not self.stack:
            self.blocks.append(("p", text))

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
            return
        if tag == "table":
            self._flush()
            self.stack.append([])
        elif tag == "tr" and self.stack:
            self.row = []
        elif tag in ("td", "th") and self.stack:
            self.cell = []
        elif tag in self.BLOCKS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.stack:
            self.stack[-1].append(self.row)
            self.row = None
        elif tag == "table" and self.stack:
            self.tables.append(self.stack.pop())
            self.blocks.append(("t", len(self.tables) - 1))
        elif tag in self.BLOCKS:
            self._flush()

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
        elif not self.stack:
            self.buf.append(data)


def merge_cells(cells):
    """Drop empty cells; attach a lone '$' to the next cell and a lone '%' or ')' to the previous one."""
    out, pending = [], ""
    for cell in cells:
        cell = cell.strip()
        if not cell:
            continue
        if cell in ("$", "US$"):
            pending = "$"
        elif cell in ("%", ")", "%)") and out:
            out[-1] += cell
        else:
            out.append(pending + cell)
            pending = ""
    return out


def read_document(raw: bytes, name: str = "document") -> dict:
    """Parse an HTML earnings release into plain text lines and merged table rows. The returned `text` is what the workbench bundle carries and where evidence quotes are found."""
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
    except Exception as exc:  # malformed markup from an untrusted source
        raise EarningsError(f"{name}: the HTML could not be read ({type(exc).__name__}); provide the official release file") from exc
    lines, tables = [], []
    for kind, item in page.blocks:
        if kind == "p":
            lines.append(item)
            continue
        rows = []
        for r, row in enumerate(page.tables[item]):
            merged = merge_cells(row)
            if merged:
                rows.append({"row": r + 1, "cells": merged, "line": " | ".join(merged)})
        if rows:
            tables.append({"table": len(tables) + 1, "first_line": len(lines), "rows": rows})
            lines.extend(row["line"] for row in rows)
    return {"name": name, "raw_sha256": sha256_bytes(bytes(raw)), "bytes": len(raw), "lines": lines, "text": "\n".join(lines), "tables": tables}


# ---------------------------------------------------------------- figures

PERIOD_RE = re.compile(r"^Q([1-4])\s*(FY|fy)?\s*'?(\d{2}|\d{4})$")
CHANGE_RE = re.compile(r"^(y/y|q/q|yoy|qoq|% ?change|change)$", re.I)
DATE_RE = re.compile(r"^([A-Za-z]{3,9})\.?\s*(\d{1,2}),\s*(\d{4})$")
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
DURATIONS = {"three": "quarter", "six": "6 months", "nine": "9 months", "twelve": "12 months", "year": "12 months"}
DUR_RE = re.compile(r"\b(?:(three|six|nine|twelve)\s+months|(?:fiscal\s+)?(year))\s+ended\b", re.I)
BASIS_RE = re.compile(r"^(non-gaap|gaap)\b", re.I)


def qn_period(text: str):
    m = PERIOD_RE.match(text.strip())
    if not m:
        return None
    year = m.group(3)
    label = f"Q{m.group(1)} FY{year[-2:]}" if m.group(2) else f"Q{m.group(1)} {year}"
    return {"label": label, "kind": "quarter", "q": int(m.group(1)), "yy": int(year[-2:]), "end": None}


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
    return DURATIONS[(m.group(1) or m.group(2)).lower()] if m else None


def dated_period(kind: str, end: date):
    return {"label": f"{kind} ended {end.isoformat()}", "kind": kind, "q": None, "yy": None, "end": end}


def relation(cur: dict, other: dict):
    """How `other` relates to `cur`: YEAR_OVER_YEAR, SEQUENTIAL, OTHER, or None when the two are not comparable (different duration kinds or label styles)."""
    if cur["kind"] != other["kind"]:
        return None
    if cur["end"] and other["end"]:
        days = (cur["end"] - other["end"]).days
        if 350 <= days <= 380:
            return "YEAR_OVER_YEAR"
        return "SEQUENTIAL" if cur["kind"] == "quarter" and 75 <= days <= 105 else "OTHER"
    if cur["q"] and other["q"]:
        if other["q"] == cur["q"] and other["yy"] == cur["yy"] - 1:
            return "YEAR_OVER_YEAR"
        if (cur["q"] > 1 and other["q"] == cur["q"] - 1 and other["yy"] == cur["yy"]) or (cur["q"] == 1 and other["q"] == 4 and other["yy"] == cur["yy"] - 1):
            return "SEQUENTIAL"
        return "OTHER"
    return None


def parse_number(cell: str):
    """(Decimal, '$'|None, 'percent'|None) from '$12,345', '(1,234)', '74.6%'; None if the cell is not a plain number."""
    text = cell.strip()
    neg = text.startswith("(") and text.rstrip("%").endswith(")")
    text = text.strip("()")
    currency = "$" if text.startswith("$") else None
    text = text.lstrip("$").strip()
    percent = text.endswith("%")
    text = text.rstrip("%").replace(",", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    return Decimal(("-" if neg else "") + text), currency, ("percent" if percent else None)


METRICS = (
    ("revenue", re.compile(r"^(total )?(net )?(revenues?|sales)$")),
    ("gross_margin", re.compile(r"^gross (profit )?margin$")),
    ("operating_expenses", re.compile(r"^(total )?operating expenses$")),
    ("operating_income", re.compile(r"^(income from operations|operating income)$")),
    ("net_income", re.compile(r"^net income$")),
    ("eps_diluted", re.compile(r"^(diluted (earnings|eps)( per (common )?share)?|(earnings|net income) per diluted share|diluted net income per share)$")),
)
COMPACT = {"revenue": "revenue", "operatingincome": "operating_income", "netincome": "net_income", "dilutedearningspershare": "eps_diluted"}
SCALE_WORDS = {"m": "millions", "million": "millions", "millions": "millions", "thousand": "thousands", "thousands": "thousands", "billion": "billions", "billions": "billions"}


def unit_scale(text: str):
    m = re.search(r"\bin\s+(thousands|millions|billions)\b", text or "", re.I) or re.search(r"\(\s*\$\s*(m)\s*\)", text or "", re.I)
    return SCALE_WORDS[m.group(1).lower()] if m else None


def metric_for(label: str, section: str | None = None):
    """(metric, basis-from-label or None, scale-from-label or None), or None. Footnote marks, '(1)', '($M)' and a leading GAAP / Non-GAAP are read off the label first."""
    s = re.sub(r"[*†‡]+$", "", label.strip())
    s = re.sub(r"\s*\(\d+\)$", "", s)
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
    s = s.lower()
    if s == "diluted" and section and "per share" in section and "shares used" not in section and "weighted" not in section:
        return "eps_diluted", basis, scale
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


def extract_table_facts(doc: dict, currency_override: str | None = None) -> tuple[list, list]:
    """Facts from tables whose columns are periods (a 'Qn FYyy' / 'Qn yyyy' label, or a date under a 'Three/Twelve Months Ended' heading, or a year under 'Three Months Ended <Month day>,')
    and from tables with the periods down the rows (metric names across the top). One value, one period, one basis per fact; the table row is the evidence. Column meaning always
    comes from the header cells, aligned one to one with the row's values; a row whose value count differs is skipped and listed. Returns (facts, issues)."""
    facts, issues = [], []
    lines = doc["lines"]
    for table in doc["tables"]:
        ctx = lines[max(0, table["first_line"] - 4):table["first_line"]]
        basis = _basis_in(ctx) or "UNSTATED"
        scale = unit_scale(" ".join(ctx[-3:]))
        section, groups, columns, transposed, skipped, unknown_cols, groups_unclear = None, [], None, None, 0, False, None
        table_dollar = any("$" in c for r in table["rows"] for c in r["cells"])
        for row in table["rows"]:
            cells = row["cells"]
            where = f"table {table['table']} row {row['row']}"
            if len(cells) == 1:
                t = cells[0]
                if BASIS_RE.match(t) and len(t) < 40:
                    basis = "NON-GAAP" if t.lower().startswith("non") else "GAAP"
                elif duration_of(t):
                    groups = [t]
                elif t.endswith(":"):
                    section = t.rstrip(":").strip().lower()
                elif unit_scale(t):
                    scale = unit_scale(t)
                continue
            if all(duration_of(c) for c in cells):
                groups = cells
                continue
            kinds = [None if CHANGE_RE.match(c) is None and qn_period(c) is None and parse_date(c) is None and not re.fullmatch(r"\d{4}", c) else c for c in cells]
            body = cells if kinds[0] is not None else cells[1:]
            head_ok = sum(k is not None for k in (kinds if kinds[0] is not None else kinds[1:])) >= 2 and all(k is not None for k in (kinds if kinds[0] is not None else kinds[1:]))
            compact = [COMPACT.get(re.sub(r"\W", "", c.lower())) for c in cells[1:]]
            if head_ok:
                if kinds[0] is None:
                    scale = unit_scale(cells[0]) or scale
                    b = BASIS_RE.match(cells[0].strip())
                    if b or re.search(r"\bgaap\b", cells[0], re.I):
                        basis = "NON-GAAP" if re.search(r"non-gaap", cells[0], re.I) else "GAAP"
                n_dates = sum(1 for c in body if parse_date(c) or re.fullmatch(r"\d{4}", c))
                size = None
                if groups and n_dates:
                    size = n_dates if len(groups) == 1 else (n_dates // len(groups) if n_dates % len(groups) == 0 else None)
                    if size is None:
                        groups_unclear = f"{n_dates} dated columns under {len(groups)} duration headings"
                columns, seen = [], 0
                for c in body:
                    if CHANGE_RE.match(c):
                        columns.append({"type": "change", "label": c.upper()})
                    elif qn_period(c):
                        columns.append({"type": "period", "period": qn_period(c)})
                    else:
                        d = parse_date(c)
                        year_only = re.fullmatch(r"\d{4}", c) is not None
                        gtext = groups[min(seen // size, len(groups) - 1)] if (groups and size) else None
                        kind = duration_of(gtext) if gtext else None
                        if year_only and gtext and _month_day(gtext):
                            month, day = _month_day(gtext)
                            try:
                                d = date(int(c), month, day)
                            except ValueError:
                                d = None
                        seen += 1
                        if d is not None and kind:
                            columns.append({"type": "period", "period": dated_period(kind, d)})
                        else:
                            columns.append({"type": "unknown", "label": c})
                transposed = None
                continue
            if sum(m is not None for m in compact) >= 2 and groups and _month_day(groups[0]):
                transposed = compact
                scale = unit_scale(cells[0]) or scale
                columns = None
                continue
            if transposed:
                m = re.fullmatch(r"(\d{4}) As (?:Reported|Adjusted) \((Non-)?GAAP\)", cells[0].strip())
                if not m:
                    continue
                month, day = _month_day(groups[0])
                kind = duration_of(groups[0])
                period = dated_period(kind, date(int(m.group(1)), month, day))
                row_basis = "NON-GAAP" if m.group(2) else "GAAP"
                for metric, cell in zip(transposed, cells[1:]):
                    if metric is None:
                        continue
                    num = parse_number(cell)
                    if num is None:
                        issues.append({"code": "UNREADABLE_ROW", "where": where, "detail": f"'{metric}' value '{cell}' is not a plain number; skipped"})
                        continue
                    facts.append(_fact(metric, row_basis, period, num, scale, None, table, row, cells[0], {}, currency_override, table_dollar))
                continue
            if columns is None:
                continue
            found = metric_for(cells[0], section)
            if found is None:
                continue
            metric, label_basis, label_scale = found
            values = cells[1:]
            if len(values) != len(columns):
                skipped += 1
                continue
            nums, bad = [], False
            unknown_cols = unknown_cols or any(c["type"] == "unknown" for c in columns)
            for col, cell in zip(columns, values):
                if col["type"] != "period":
                    nums.append(None)
                    continue
                num = parse_number(cell)
                if num is None:
                    bad = True
                    break
                nums.append(num)
            if bad:
                issues.append({"code": "UNREADABLE_ROW", "where": where, "detail": f"'{cells[0]}': a value in a period column is not a plain number; row skipped"})
                continue
            printed = {col["label"]: cell for col, cell in zip(columns, values) if col["type"] == "change"}
            for col, num in zip(columns, nums):
                if num is None:
                    continue
                if metric == "gross_margin" and num[2] != "percent":
                    issues.append({"code": "UNIT_AMBIGUOUS", "where": where, "detail": "gross margin without a % sign (a dollar amount?); not extracted"})
                    break
                if metric == "eps_diluted" and num[1] is None:
                    issues.append({"code": "UNIT_AMBIGUOUS", "where": where, "detail": f"'{cells[0]}' has no $ sign (a share count?); not read as earnings per share"})
                    break
                facts.append(_fact(metric, label_basis or basis, col["period"], num, label_scale or scale, label_scale, table, row, cells[0], printed, currency_override, table_dollar))
        if unknown_cols:
            issues.append({"code": "COLUMN_DURATION_UNKNOWN", "where": f"table {table['table']}", "detail": "some dated columns have no 'Three/Twelve Months Ended' heading above them" + (f" ({groups_unclear})" if groups_unclear else "") + "; their values are not read"})
        if any("UNIT_SCALE_UNKNOWN" in f["flags"] and f["evidence"]["table"] == table["table"] for f in facts):
            issues.append({"code": "UNIT_SCALE_UNSTATED", "where": f"table {table['table']}", "detail": "no 'in millions/thousands' statement found for this table; amounts are kept unscaled and flagged"})
        if skipped:
            issues.append({"code": "COLUMN_COUNT_MISMATCH", "where": f"table {table['table']}", "detail": f"{skipped} recognised row(s) skipped because their value count differs from the header columns"})
    return _dedupe(facts, issues), issues


def _fact(metric, basis, period, num, scale, label_scale, table, row, label, printed, currency_override, table_dollar=False):
    value, cur, pct = num
    cur = cur or ("$" if (table_dollar and metric not in ("gross_margin", "eps_diluted")) else None)
    if metric == "gross_margin":
        unit, currency = "percent", None
    elif metric == "eps_diluted":
        unit, currency = "per_share", ("USD" if cur else None)
    else:
        unit, currency = (scale if scale else "unscaled"), ("USD" if cur else None)
    if currency_override and currency:
        currency = currency_override
    flags = []
    if currency == "USD" and not currency_override:
        flags.append("CURRENCY_ASSUMED_USD_FROM_$_SIGN")
    if unit == "unscaled":
        flags.append("UNIT_SCALE_UNKNOWN")
    if basis == "UNSTATED":
        flags.append("BASIS_NOT_STATED")
    return {"metric": metric, "basis": basis, "period": period["label"], "period_info": period, "value": _decimal_string(value), "unit": unit, "currency": currency,
            "evidence": {"table": table["table"], "row": row["row"], "label": label, "quote": row["line"]}, "printed_changes": printed, "method": "TABLE_ROW_LABEL_MATCH", "flags": flags}


def _dedupe(facts, issues):
    """The same metric, basis and period printed in several tables is one fact (first table kept; others listed as `also_in`); differing values are a conflict, both kept."""
    out, index = [], {}
    for f in facts:
        key = (f["metric"], f["basis"], f["period"])
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


def choose_current(facts: list, head: dict):
    """The period the release is about: the quarter whose end date the headline states, else the first quarter-period column of the first recognised table. None if there is none."""
    quarters = [f for f in facts if f["period_info"]["kind"] == "quarter"]
    if head.get("quarter_ended") and head["quarter_ended"].get("date"):
        want = date.fromisoformat(head["quarter_ended"]["date"])
        hit = [f for f in quarters if f["period_info"]["end"] == want]
        if hit:
            return hit[0]["period"]
    return quarters[0]["period"] if quarters else None


def headline_checks(doc: dict, facts: list) -> dict:
    """Reads the release's headline sentence(s); returns the period it states and whether its figures agree with the tables. Called before the current period is chosen, so checks run against
    every period's facts with the stated end date, else the first column."""
    text = " ".join(doc["lines"][:70])
    para = next((l for l in doc["lines"][:70] if re.search(r"quarter ended", l) and re.search(r"revenue|net sales|results", l, re.I)), None)
    out = {"paragraph": para[:900] if para else None, "quarter_ended": None, "fiscal_quarter_title": None, "revenue_headline": None, "eps_headline": {}, "checks": []}
    m = re.search(r"(?:(first|second|third|fourth)\s+)?quarter ended ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if m:
        out["quarter_ended"] = {"quarter": ORDINALS[m.group(1)] if m.group(1) else None, "date": datetime.strptime(m.group(2), "%B %d, %Y").date().isoformat(), "quote": m.group(0)}
    m = re.search(r"(First|Second|Third|Fourth) Quarter Fiscal (\d{4})", text)
    if m:
        out["fiscal_quarter_title"] = {"quarter": ORDINALS[m.group(1).lower()], "fiscal_year": int(m.group(2)), "quote": m.group(0)}
    m = re.search(r"[Rr]evenue(?: for the [^$]{0,70}?)?,? (?:of|was|were) \$(\d[\d,]*(?:\.\d+)?) (billion|million)", text)
    if m:
        out["revenue_headline"] = {"value": m.group(1), "scale": m.group(2), "quote": m.group(0)}
    for m in re.finditer(r"(Non-GAAP|GAAP) earnings per diluted share (?:was|were|of) \$(\d+(?:\.\d+)?)", text):
        out["eps_headline"][m.group(1).upper()] = {"value": m.group(2), "quote": m.group(0)}
    m = re.search(r"(?<!GAAP )diluted earnings per share (?:of|was) \$(\d+(?:\.\d+)?)", text)
    if m and not out["eps_headline"]:
        out["eps_headline"]["UNSTATED"] = {"value": m.group(1), "quote": m.group(0)}
    current = choose_current(facts, out)
    cur = [f for f in facts if f["period"] == current] if current else []
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


def _amd_style(doc: dict) -> list:
    """'For the fourth quarter of 2024, AMD expects revenue to be approximately $7.5 billion, plus or minus $300 million.' and '<basis> gross margin is expected to be approximately 54%'."""
    items = []
    for line in doc["lines"]:
        m = AMD_REV.search(line)
        if not m:
            continue
        label = f"Q{ORDINALS[m.group(1).lower()]} FY{m.group(3)[-2:]}" if m.group(2) else f"Q{ORDINALS[m.group(1).lower()]} {m.group(3)}"
        mid, _ = _money("$" + m.group(4), m.group(5))
        band, _ = _money("$" + m.group(6), m.group(7))
        items.append({"metric": "revenue", "basis": "UNSTATED", "target_period": label, "unit": "millions", "currency": "USD", "midpoint": _decimal_string(mid), "low": _decimal_string(mid - band),
                      "high": _decimal_string(mid + band), "band": f"plus or minus {_decimal_string(band)} million", "conversion": "billion to million x1000" if "billion" in (m.group(5), m.group(7)) else None,
                      "quote": m.group(0), "method": "OUTLOOK_REGEX"})
        for g in AMD_GM.finditer(line):
            items.append({"metric": "gross_margin", "basis": "NON-GAAP" if g.group(1).lower().startswith("non") else "GAAP", "target_period": label, "unit": "percent", "currency": None,
                          "midpoint": _decimal_string(Decimal(g.group(2))), "low": None, "high": None, "band": "point estimate (approximately)", "conversion": None, "quote": g.group(0), "method": "OUTLOOK_REGEX"})
    return items


def extract_guidance(doc: dict) -> tuple[list, list]:
    """The company's own outlook for the next period: revenue (plus or minus a percentage or amount) and 'GAAP and non-GAAP X are expected to be A and B, respectively' bullets."""
    items, issues = _amd_style(doc), []
    if items:
        return items, issues
    target = None
    for i, line in enumerate(doc["lines"]):
        m = re.search(r"outlook for the (first|second|third|fourth) quarter of fiscal (\d{4})", line, re.I)
        if m:
            target = (f"Q{ORDINALS[m.group(1).lower()]} FY{m.group(2)[-2:]}", i)
            break
    if target is None:
        return [], [{"code": "NO_OUTLOOK_FOUND", "where": "text", "detail": "no sentence of the form 'outlook for the <n>th quarter of fiscal <year>' was found; no guidance extracted"}]
    for line in doc["lines"][target[1]:target[1] + 16]:
        m = SINGLE_REV.search(line)
        if m:
            mid, unit = _money("$" + m.group(2), m.group(3))
            band = Decimal(m.group(4)) if m.group(4) else None
            low = mid * (1 - band / 100) if band is not None else None
            high = mid * (1 + band / 100) if band is not None else None
            items.append({"metric": "revenue", "basis": "UNSTATED", "target_period": target[0], "unit": unit, "currency": "USD", "midpoint": _decimal_string(mid),
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
                items.append({"metric": name, "basis": basis, "target_period": target[0], "unit": unit, "currency": None if unit == "percent" else "USD", "midpoint": _decimal_string(mid),
                              "low": _decimal_string(mid - band) if band is not None else None, "high": _decimal_string(mid + band) if band is not None else None,
                              "band": f"plus or minus {m.group(6)} basis points" if band is not None else "point estimate (approximately)" if "approximately" in m.group(0) else "point estimate",
                              "conversion": "billion to million x1000" if scale == "billion" else None, "quote": m.group(0), "method": "OUTLOOK_REGEX"})
    if not items:
        issues.append({"code": "NO_GUIDANCE_PARSED", "where": "outlook", "detail": "an outlook section exists but none of its sentences matched the supported wording"})
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
           "evidence": [cur["evidence"], prior["evidence"]], "source": source, "printed_change_check": None}
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
    """ACTUAL vs PRIOR-PERIOD ACTUAL. Comparative columns printed in the same release (same duration kind only) are checked against the change the release itself prints. If an earlier release is
    supplied, its own current-period figures fill a SEQUENTIAL comparison the release does not print, labelled with that source."""
    out = []
    current = sorted((f for f in facts if f["period"] == current_period), key=lambda f: (f["metric"], f["basis"]))
    for cur in current:
        for prior in facts:
            if prior["metric"] == cur["metric"] and prior["basis"] == cur["basis"] and prior["period"] != current_period:
                rel = relation(cur["period_info"], prior["period_info"])
                if rel is not None:
                    out.append(_prior_row(cur, prior, rel, "comparative column printed in the current release", True))
    if earlier_facts and earlier_current:
        have = {(r["metric"], r["basis"], r["relation"]) for r in out}
        for cur in current:
            for prior in earlier_facts:
                if prior["period"] == earlier_current and prior["metric"] == cur["metric"] and prior["basis"] == cur["basis"] and prior["unit"] == cur["unit"] and prior["currency"] == cur["currency"]:
                    if relation(cur["period_info"], prior["period_info"]) == "SEQUENTIAL" and (cur["metric"], cur["basis"], "SEQUENTIAL") not in have:
                        out.append(_prior_row(cur, prior, "SEQUENTIAL", "figure from the comparison release (not printed in the current release)", False))
    return out


def guidance_comparisons(facts: list, current_period: str, guidance: list, guidance_doc: dict | None) -> tuple[list, list]:
    """ACTUAL vs the company's EARLIER guidance for the same period. Compared only when metric, basis (or unstated), period, unit and currency agree."""
    rows, withheld = [], []
    if guidance_doc is None:
        return rows, [{"reason": "no comparison document supplied; earlier company guidance for this period is unknown"}]
    current = {(f["metric"], f["basis"]): f for f in facts if f["period"] == current_period}
    for g in guidance:
        if g["target_period"] != current_period:
            withheld.append({"metric": g["metric"], "reason": f"the comparison document's outlook is for {g['target_period']}, not {current_period}"})
            continue
        candidates = [current[k] for k in current if k[0] == g["metric"] and (g["basis"] == "UNSTATED" or k[1] == g["basis"])]
        if not candidates:
            withheld.append({"metric": g["metric"], "basis": g["basis"], "reason": "the current release has no matching reported figure"})
            continue
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
                     "unit": g["unit"], "actual": act["value"], "guidance_midpoint": g["midpoint"], "guidance_low": g["low"], "guidance_high": g["high"], "guidance_band": g["band"],
                     "difference_vs_midpoint": _decimal_string(a - mid), "difference_unit": "percentage points" if g["unit"] == "percent" else g["unit"],
                     "difference_pct": None if g["unit"] == "percent" or _pct(a - mid, mid) is None else _decimal_string(round(_pct(a - mid, mid), 2)),
                     "position": position, "conversion": g["conversion"], "guidance_quote": g["quote"], "actual_evidence": act["evidence"]})
    return rows, withheld


# ---------------------------------------------------------------- time and sources

def sec_acceptance(headers_html: str) -> str | None:
    """The filing's own SGML-header acceptance time (New York clock, YYYYMMDDHHMMSS) as a UTC ISO timestamp."""
    m = re.search(r"ACCEPTANCE-DATETIME>\s*(\d{14})", headers_html or "")
    if not m:
        return None
    ny = datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=ZoneInfo("America/New_York"))
    return fmt_ts(ny)


def fetch_url(url: str, contact: str | None = None) -> bytes:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise EarningsError("only https URLs are fetched; or download the file and pass its path")
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
    m = re.match(r"(https://www\.sec\.gov/Archives/edgar/data/\d+/)(\d{10})(\d{2})(\d{6})/", url)
    return f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}/{m.group(2)}-{m.group(3)}-{m.group(4)}-index-headers.html" if m else None


# ---------------------------------------------------------------- bundle and report

def build_bundle(company, ticker, venue, docs, consensus_docs, current_period, currency):
    """A KOD-WORKBENCH-v1 bundle. docs: list of dicts (role current|comparison) with parsed fields. Observations are the current release's reported figures (ACTUAL for the current
    period column, PRIOR for earlier columns, kept apart) and any supplied consensus."""
    sec_id = f"{ticker}.{venue}"
    bundle = {"schema_version": workbench.SCHEMA, "synthetic": False,
              "securities": [{"security_id": sec_id, "issuer_id": company, "ticker": ticker, "venue": venue, "currency": currency or "UNKNOWN"}], "documents": []}
    for d in docs:
        entry = {"document_id": d["document_id"], "event_id": d["event_id"], "security_ids": [sec_id], "source_kind": "PRIMARY", "publisher": company, "source_url": d["source_url"],
                 "source_family": "issuer-earnings-release", "published_at": d["published_at"], "observed_at": d["observed_at"], "title": d["title"], "text": d["text"], "observations": []}
        for f in d.get("facts", []):
            role = "ACTUAL" if f["period"] == current_period else "PRIOR"
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


def analyse(company, ticker, venue, primary, comparison, as_of, mode, consensus_path=None, currency_override=None):
    """primary / comparison: dicts with doc (read_document), source_url, published_at, observed_at, title. Returns the structured result (also the JSON companion)."""
    facts, issues = extract_table_facts(primary["doc"], currency_override)
    head = headline_checks(primary["doc"], facts)
    current_period = choose_current(facts, head)
    if current_period is None:
        raise EarningsError(f"{primary['doc']['name']}: no earnings summary table with period-labelled columns (for example 'Q3 FY25  Q2 FY25' or 'Three Months Ended' over dated columns) and "
                            "recognised rows (revenue, net income, diluted EPS) was found. This version supports an official earnings press release in HTML; for SEC filers, use the 8-K Exhibit 99.1 .htm file")
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
    guidance_next, g_issues = extract_guidance(primary["doc"])
    issues += g_issues
    comp_facts, comp_guidance, comp_issues, comp_current = [], [], [], None
    if comparison:
        comp_facts, ci = extract_table_facts(comparison["doc"], currency_override)
        comp_current = choose_current(comp_facts, headline_checks(comparison["doc"], comp_facts))
        cg, gi = extract_guidance(comparison["doc"])
        comp_guidance, comp_issues = cg, ci + gi
    event_id = f"{ticker}-{current_period.replace(' ', '-')}-earnings"
    currency = next((f["currency"] for f in facts if f["currency"]), None)
    docs = [{"document_id": "current-release", "event_id": event_id, **{k: primary[k] for k in ("source_url", "published_at", "observed_at", "title")}, "text": primary["doc"]["text"], "facts": facts}]
    if comparison:
        docs.append({"document_id": "comparison-release", "event_id": f"{ticker}-{(comp_current or 'unknown-period').replace(' ', '-')}-earnings",
                     **{k: comparison[k] for k in ("source_url", "published_at", "observed_at", "title")}, "text": comparison["doc"]["text"], "facts": []})
    sec_id = f"{ticker}.{venue}"
    consensus_docs = load_consensus(consensus_path, sec_id, event_id) if consensus_path else []
    bundle = build_bundle(company, ticker, venue, docs, consensus_docs, current_period, currency)
    report = workbench.build_report(bundle, as_of, query="", security_id=sec_id, limit=50, mode=mode)
    excluded = {row["document_id"]: row["reasons"] for row in report["excluded_documents"]}
    cutoff_ok = "current-release" not in excluded
    result = {"schema_version": SCHEMA, "research_only": True, "entry_permission": False, "company": company, "ticker": ticker, "venue": venue, "event": "EARNINGS_ANNOUNCEMENT",
              "period": current_period, "as_of": report["as_of"], "mode": mode, "cutoff": {"current_release_eligible": cutoff_ok, "excluded": excluded},
              "sources": [{"role": "current", "name": primary["doc"]["name"], "source_url": primary["source_url"], "sha256": primary["doc"]["raw_sha256"], "bytes": primary["doc"]["bytes"],
                           "published_at": primary["published_at"], "published_basis": primary["published_basis"], "observed_at": primary["observed_at"], "observed_basis": primary["observed_basis"]}],
              "bundle_sha256": report["input_bundle_sha256"], "workbench_report": report, "issues": issues, "headline": head}
    if comparison:
        result["sources"].append({"role": "comparison", "name": comparison["doc"]["name"], "source_url": comparison["source_url"], "sha256": comparison["doc"]["raw_sha256"], "bytes": comparison["doc"]["bytes"],
                                  "published_at": comparison["published_at"], "published_basis": comparison["published_basis"], "observed_at": comparison["observed_at"], "observed_basis": comparison["observed_basis"]})
    if not cutoff_ok:
        result.update(facts=[], prior_period=[], guidance_comparisons=[], guidance_not_compared=[{"reason": "current release is not eligible at the information cutoff: " + ", ".join(excluded["current-release"])}],
                      next_guidance=[], consensus=[], consistency_with_comparison=[])
        return result

    def public(f):
        out = {k: v for k, v in f.items() if k not in ("printed_changes", "period_info")}
        out["period_end"] = f["period_info"]["end"].isoformat() if f["period_info"]["end"] else None
        out["period_kind"] = f["period_info"]["kind"]
        return out

    result["facts"] = [public(f) for f in facts if f["period"] == current_period]
    result["other_period_figures"] = [public(f) for f in facts if f["period"] != current_period]
    comp_ok = comparison is not None and "comparison-release" not in excluded
    result["prior_period"] = prior_period_comparisons(facts, current_period, comp_facts if comp_ok else None, comp_current if comp_ok else None)
    if comparison and not comp_ok:
        gcomp, gwith = [], [{"reason": "comparison document is not eligible at the information cutoff: " + ", ".join(excluded["comparison-release"])}]
    else:
        gcomp, gwith = guidance_comparisons(facts, current_period, comp_guidance if comp_ok else [], comparison if comp_ok else None)
        if comp_ok and not (comparison["published_at"] and primary["published_at"] and parse_ts(comparison["published_at"]) < parse_ts(primary["published_at"])):
            gcomp, gwith = [], gwith + [{"reason": "the comparison document must be published strictly before the current release; its publication time is unknown or not earlier"}]
    result["guidance_comparisons"], result["guidance_not_compared"] = gcomp, gwith
    result["consistency_with_comparison"] = []
    if comp_ok and comp_current:
        earlier = {(f["metric"], f["basis"], f["period"]): f for f in comp_facts if f["period"] == comp_current}
        for f in facts:
            e = earlier.get((f["metric"], f["basis"], f["period"])) if f["period"] != current_period else None
            if e is not None and e["unit"] == f["unit"] and e["currency"] == f["currency"]:
                result["consistency_with_comparison"].append({"metric": f["metric"], "basis": f["basis"], "period": f["period"], "earlier_release": e["value"], "printed_now": f["value"],
                                                              "agrees": Decimal(e["value"]) == Decimal(f["value"])})
    result["comparison_issues"] = comp_issues
    result["next_guidance"] = guidance_next
    consensus = []
    for card in report["search_results"]:
        if card["event_id"] == event_id:
            consensus = [c for c in card["comparisons"] if any(e["role"] == "CONSENSUS" for e in c["evidence"])]
    result["consensus"] = consensus
    return result


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
    return f"[{_md(label)}](<{url.replace(' ', '%20').replace('>', '%3E').replace('<', '%3C')}>)"


def _row(*cells):
    return "| " + " | ".join(_md(c) for c in cells) + " |"


def _ref(ev):
    return f"table {ev['table']}, row {ev['row']}"


def questions(result):
    q = []
    if not result["consensus"]:
        q.append("Obtain a dated pre-release consensus for revenue and diluted EPS (same basis, period and currency, published before the release) before judging the result against expectations.")
    for g in result["guidance_comparisons"]:
        if g["position"] in ("ABOVE_RANGE", "BELOW_RANGE"):
            q.append(f"{NAMES[g['metric']]} ({g['basis']}) was {g['position'].replace('_', ' ').lower().replace(' range', ' the range')} the company guided earlier. What explains the gap? The release's own commentary is not extracted; read it.")
    gaap = {f["metric"]: Decimal(f["value"]) for f in result["facts"] if f["basis"] == "GAAP"}
    non = {f["metric"]: Decimal(f["value"]) for f in result["facts"] if f["basis"] == "NON-GAAP"}
    if "eps_diluted" in gaap and "eps_diluted" in non and gaap["eps_diluted"] != non["eps_diluted"]:
        q.append(f"Non-GAAP diluted EPS differs from GAAP by {_decimal_string(non['eps_diluted'] - gaap['eps_diluted'])}. Which reconciling items account for it? (The release's reconciliation tables are not extracted.)")
    for p in result["prior_period"]:
        if p["relation"] == "SEQUENTIAL" and p["unit"] == "percent" and Decimal(p["difference"]) < 0 and p["basis"] == "GAAP":
            q.append(f"{NAMES[p['metric']]} (GAAP) fell {_decimal_string(abs(Decimal(p['difference'])))} percentage points from the previous quarter. Does the company explain it in the supplied sources?")
    if result["next_guidance"]:
        rev = next((g for g in result["next_guidance"] if g["metric"] == "revenue"), None)
        cur = next((f for f in result["facts"] if f["metric"] == "revenue"), None)
        if rev and cur and rev["unit"] == cur["unit"]:
            q.append(f"The company guides {rev['target_period']} revenue at a midpoint of {rev['midpoint']} ({_unit(rev['unit'], rev['currency'])}), {_fmt(round(_pct(Decimal(rev['midpoint']) - Decimal(cur['value']), Decimal(cur['value'])), 1))}% against the quarter just reported. How does that compare with consensus once available?")
    for i in result["issues"]:
        if i["code"] in ("HEADLINE_TABLE_CONFLICT", "PERIOD_MISMATCH", "CURRENT_PERIOD_AMBIGUOUS"):
            q.append(f"Resolve before relying on the figures: {i['detail']}.")
    return q


def render_note(result):
    L = []
    add = L.append
    add(f"# Earnings research note: {_md(result['company'])} ({_md(result['ticker'])}), {_md(result['period'])}")
    add("")
    add("> Research aid only. Not a recommendation, forecast or entry permission. It opened no case, wrote no ledger and placed no order.")
    add("")
    add(f"- **Event:** earnings announcement (official release)  \n- **Reporting period:** {_md(result['period'])}  \n- **Information cutoff:** {_md(result['as_of'])} (mode: {_md(result['mode'])})")
    if result["mode"] == "public":
        add("- **Historical reconstruction:** documents are admitted by their publication time only. This does not show what KOD possessed at the cutoff; the files were retrieved later (see Sources).")
    add("")
    if not result["cutoff"]["current_release_eligible"]:
        add("## Result withheld by the information cutoff")
        add("")
        add(f"The current release is not available at the cutoff: {_md(', '.join(result['cutoff']['excluded']['current-release']))}. No figures are shown, because a point-in-time note must not use information from after its cutoff.")
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
        add("Calculation from the comparative columns printed in the same release. The prior figure is the company's reported number for that period, not an expectation.")
        add("")
        if result["prior_period"]:
            add("| Metric | Basis | Unit | Current | Prior period | Prior actual | Difference | Change % | Relation | Agrees with the release's printed change |")
            add("|---|---|---|---|---|---|---|---|---|---|")
            for p in result["prior_period"]:
                chk = p["printed_change_check"]
                add(_row(NAMES[p["metric"]], p["basis"], _unit(p["unit"], p["currency"]), p["actual"], p["prior_period"], p["prior_actual"], f"{p['difference']} {p['difference_unit'] if p['unit']=='percent' else ''}".strip(), p["difference_pct"] or "n/a", p["relation"],
                         "not checked" if chk is None else f"{'yes' if chk['agrees'] else 'NO'} (printed: {chk['printed']})"))
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
                add(_row(NAMES[g["metric"]], g["basis"], _unit(g["unit"], "USD" if g["unit"] != "percent" else None), g["actual"], g["guidance_midpoint"], rng, g["difference_vs_midpoint"], g["difference_pct"] or "n/a", g["position"], g["guidance_quote"]))
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
                add(_row(NAMES[g["metric"]], g["basis"], g["target_period"], f"{g['midpoint']} ({_unit(g['unit'], g['currency'])})", f"{g['low']} to {g['high']}" if g["low"] else g["band"], g["quote"]))
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
        add("- Currency is read from the \"$\" sign and assumed to be US dollars unless the user overrode it; confirm in the filing.")
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
    ap.add_argument("--currency", help="override the assumed currency of '$' amounts, e.g. CAD")
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
        result = analyse(args.company, args.ticker, args.venue, primary, comparison, args.as_of or now, args.mode, args.consensus, args.currency)
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
