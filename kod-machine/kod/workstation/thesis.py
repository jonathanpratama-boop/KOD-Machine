"""Structured thesis conditions: a constrained, typed expression tree evaluated against the dossier at a cutoff. Nothing is ever eval'd.

A condition is 'review if <expression>'. Expressions are JSON objects of exactly these shapes:

    {"op": "<" | "<=" | ">" | ">=", "left": <operand>, "right": <operand>}
    {"op": "all" | "any", "args": [<expression>, ...]}            (1 to 8 sub-expressions)
    {"op": "not", "arg": <expression>}

Operands come from a fixed catalog; each has a unit, and a comparison needs equal units (and equal currencies for money):

    {"kind": "change", "key": <dossier change key>}                     e.g. revenue_yoy (percent), operating_margin_yoy (percentage points)
    {"kind": "margin", "key": "operating_margin_latest_quarter"}       percent
    {"kind": "metric", "metric": <catalog metric>, "at": "latest_quarter" | "latest_fiscal_year" | "latest_balance"}
    {"kind": "scenario", "scenario": "bear" | "base" | "bull", "name": <set name>, "measure": "per_share" | "enterprise_value"}
    {"kind": "price", "measure": "latest_close"}                        the latest raw close eligible at the cutoff
    {"kind": "constant", "value": "<decimal text>", "unit": <unit>, "currency": <ISO code, money only>}

Evaluation is three-valued. A missing, conflicted or not-applicable input makes the comparison UNRESOLVED, never false; 'all' is false if any part is
false, 'any' is true if any part is true, otherwise unresolved parts make the whole unresolved. Every evaluation returns a trace naming the thesis version,
the condition, each operand's value and the records it came from (calculation, observations, assumption version, price).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json

from .dossier import CHANGES, HISTORY_METRICS, LABELS, display, series_unit

COMPARISONS = ("<", "<=", ">", ">=")
UNITS = ("percent", "percentage points", "currency", "currency/share", "shares")
AT = ("latest_quarter", "latest_fiscal_year", "latest_balance")
MAX_DEPTH, MAX_ARGS, MAX_CONDITIONS = 4, 8, 12
CHANGE_KEYS = tuple(k for k, *_ in CHANGES)
TRUE, FALSE, UNRESOLVED = "triggered", "not_triggered", "unresolved"


class ConditionError(ValueError):
    pass


def _operand(o, path):
    if not isinstance(o, dict):
        raise ConditionError(f"{path}: an operand must be an object")
    kind = o.get("kind")
    allowed = {"change": {"kind", "key"}, "margin": {"kind", "key"}, "metric": {"kind", "metric", "at"}, "scenario": {"kind", "scenario", "name", "measure"},
               "price": {"kind", "measure"}, "constant": {"kind", "value", "unit", "currency"}}
    if kind not in allowed:
        raise ConditionError(f"{path}: unknown operand kind {kind!r}")
    extra = set(o) - allowed[kind]
    if extra:
        raise ConditionError(f"{path}: unexpected fields {sorted(extra)}")
    if kind == "change" and o.get("key") not in CHANGE_KEYS:
        raise ConditionError(f"{path}: unknown change {o.get('key')!r}")
    if kind == "margin" and o.get("key") != "operating_margin_latest_quarter":
        raise ConditionError(f"{path}: the margin operand is operating_margin_latest_quarter")
    if kind == "metric" and (o.get("metric") not in HISTORY_METRICS or o.get("at") not in AT):
        raise ConditionError(f"{path}: metric must be one of the catalog metrics and 'at' one of {AT}")
    if kind == "scenario" and (o.get("scenario") not in ("bear", "base", "bull") or o.get("measure") not in ("per_share", "enterprise_value")
                               or not isinstance(o.get("name", "default"), str) or len(o.get("name", "default")) > 80):
        raise ConditionError(f"{path}: a scenario operand needs scenario bear/base/bull, a set name and measure per_share or enterprise_value")
    if kind == "price" and o.get("measure") != "latest_close":
        raise ConditionError(f"{path}: the price operand is latest_close")
    if kind == "constant":
        try:
            value = Decimal(str(o.get("value")))
        except (InvalidOperation, ValueError):
            raise ConditionError(f"{path}: constant value {o.get('value')!r} is not a number")
        if isinstance(o.get("value"), float) or not value.is_finite():
            raise ConditionError(f"{path}: constant values are finite decimal text")
        if o.get("unit") not in UNITS:
            raise ConditionError(f"{path}: constant unit must be one of {UNITS}")
        if o.get("unit") in ("currency", "currency/share") and not (isinstance(o.get("currency"), str) and len(o["currency"]) == 3 and o["currency"].isupper()):
            raise ConditionError(f"{path}: a money constant needs its currency code")
        if o.get("unit") not in ("currency", "currency/share") and o.get("currency"):
            raise ConditionError(f"{path}: only money constants carry a currency")


def validate_expression(e, path="expression", depth=0):
    if depth > MAX_DEPTH:
        raise ConditionError(f"{path}: nested more than {MAX_DEPTH} levels")
    if not isinstance(e, dict):
        raise ConditionError(f"{path}: an expression must be an object")
    op = e.get("op")
    if op in COMPARISONS:
        if set(e) != {"op", "left", "right"}:
            raise ConditionError(f"{path}: a comparison has exactly op, left and right")
        _operand(e["left"], path + ".left")
        _operand(e["right"], path + ".right")
        if e["left"].get("kind") == "constant" and e["right"].get("kind") == "constant":
            raise ConditionError(f"{path}: comparing two constants is not a condition")
    elif op in ("all", "any"):
        if set(e) != {"op", "args"} or not isinstance(e["args"], list) or not 1 <= len(e["args"]) <= MAX_ARGS:
            raise ConditionError(f"{path}: {op} takes 1 to {MAX_ARGS} sub-expressions in args")
        for i, sub in enumerate(e["args"]):
            validate_expression(sub, f"{path}.args[{i}]", depth + 1)
    elif op == "not":
        if set(e) != {"op", "arg"}:
            raise ConditionError(f"{path}: not takes one sub-expression in arg")
        validate_expression(e["arg"], path + ".arg", depth + 1)
    else:
        raise ConditionError(f"{path}: unknown operator {op!r}")


def validate_conditions(conditions) -> list:
    """[{'id', 'label', 'expression'}] checked completely; ids are unique short slugs."""
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= MAX_CONDITIONS:
        raise ConditionError(f"a thesis needs 1 to {MAX_CONDITIONS} conditions")
    seen = set()
    out = []
    for i, c in enumerate(conditions):
        if not isinstance(c, dict) or set(c) - {"id", "label", "expression"}:
            raise ConditionError(f"condition {i + 1}: fields are id, label and expression")
        cid, label = str(c.get("id") or f"c{i + 1}"), str(c.get("label") or "").strip()
        if not cid.replace("_", "").replace("-", "").isalnum() or len(cid) > 40 or cid in seen:
            raise ConditionError(f"condition {i + 1}: id must be a unique short slug")
        if not label or len(label) > 300:
            raise ConditionError(f"condition {i + 1}: describe it in a label of 1 to 300 characters")
        validate_expression(c.get("expression"), f"condition {cid}")
        seen.add(cid)
        out.append({"id": cid, "label": label, "expression": c["expression"]})
    return out


def parse_conditions(text: str) -> list:
    """Conditions from JSON text (the only way an expression enters, besides the form builder). JSON is parsed, never executed."""
    try:
        data = json.loads(text, parse_float=str, parse_int=str)
    except ValueError as exc:
        raise ConditionError(f"conditions are not valid JSON: {exc}") from exc
    return validate_conditions(data)


def comparison(left: dict, op: str, right: dict, label: str, cid: str = "c1") -> dict:
    return {"id": cid, "label": label, "expression": {"op": op, "left": left, "right": right}}


# ---- evaluation ----

def _resolve(o: dict, d: dict, context: dict) -> dict:
    """{'value': Decimal | None, 'unit', 'currency', 'status', 'reason', 'sources': {...}, 'label'}"""
    kind = o["kind"]
    if kind == "constant":
        return {"value": Decimal(str(o["value"])), "unit": o["unit"], "currency": o.get("currency"), "status": "ok", "label": f"{o['value']} {o['unit']}",
                "sources": {}}
    if kind in ("change", "margin"):
        key = o["key"] if kind == "change" else "operating_margin_yoy"
        c = next((c for c in d["changes"] if c["key"] == key), None)
        if c is None:
            return {"value": None, "status": "missing", "reason": f"{key} is not in the dossier", "unit": None, "sources": {}, "label": key}
        if kind == "margin":
            value = c.get("current_margin")
            calc = c.get("current_margin_calculation_id")
            return {"value": Decimal(value) if value else None, "unit": "percent", "currency": None, "status": "ok" if value else "missing",
                    "reason": None if value else "no operating margin for the latest quarter: " + "; ".join(c["reasons"]),
                    "label": f"Operating margin, quarter ended {d.get('latest_quarter_end')}", "sources": {"calculation_id": calc}}
        unit = {"percent growth": "percent", "percent change": "percent", "percent of": "percent", "percentage points": "percentage points",
                "amount": "currency"}[c["measure"]]
        currency = None
        if unit == "currency":
            rec = d["calculations"].get(c["calculation_id"], {})
            currency = (rec.get("detail") or {}).get("currency")
        caveats = "; ".join(c[k] for k in ("duration_note", "concept_note") if c.get(k)) or None
        return {"value": Decimal(c["value"]) if c["status"] == "ok" else None, "unit": unit, "currency": currency,
                "status": "ok" if c["status"] == "ok" else c["status"], "reason": "; ".join(c["reasons"]) or None,
                "label": f"{c['label']} ({c['periods']})", "note": caveats, "sources": {"calculation_id": c["calculation_id"]}}
    if kind == "metric":
        group = {"latest_quarter": "quarterly", "latest_fiscal_year": "annual", "latest_balance": "instant"}[o["at"]]
        cells = [cell for cell in d["history"][group].get(o["metric"], []) if cell["value"] is not None]
        unit, currency = series_unit(d, o["metric"])
        if not cells:
            return {"value": None, "unit": unit, "currency": currency, "status": "missing", "reason": f"no eligible {LABELS[o['metric']]} for the {o['at'].replace('_', ' ')}",
                    "label": LABELS[o["metric"]], "sources": {}}
        cell = cells[-1]
        return {"value": Decimal(cell["value"]), "unit": unit, "currency": currency, "status": "ok", "reason": None,
                "label": f"{LABELS[o['metric']]}, {cell['period']['label']}", "sources": {"observation_ids": cell["observation_ids"],
                                                                                         "calculation_id": cell.get("calculation_id")}}
    if kind == "scenario":
        name = o.get("name", "default")
        sc = next((s for s in d.get("scenarios", []) if s["scenario"] == o["scenario"] and s["name"] == name), None)
        if sc is None:
            return {"value": None, "unit": None, "status": "missing", "reason": f"no {o['scenario']} scenario '{name}' saved by this cutoff", "sources": {},
                    "label": f"{o['scenario']} scenario"}
        value = sc["per_share"] if o["measure"] == "per_share" else sc["enterprise_value"]
        return {"value": Decimal(value) if value else None, "unit": "currency/share" if o["measure"] == "per_share" else "currency", "currency": sc["currency"],
                "status": "ok" if value else sc["status"], "reason": None if value else f"the scenario gives no {o['measure'].replace('_', ' ')} ({sc['status']})",
                "label": f"{sc['scenario']} scenario '{sc['name']}' v{sc['version']} {o['measure'].replace('_', ' ')}",
                "sources": {"assumption_version_id": sc["version_id"]}}
    if kind == "price":
        p = context.get("price")
        if not p:
            return {"value": None, "unit": "currency/share", "status": "missing", "reason": "no raw price eligible at this cutoff", "sources": {},
                    "label": "latest close"}
        return {"value": Decimal(p["close"]), "unit": "currency/share", "currency": p["currency"], "status": "ok", "reason": None,
                "label": f"close {p['observed_on']} ({p['source']})", "sources": {"price_id": p["id"]}}
    raise ConditionError(f"unknown operand kind {kind!r}")


def _evaluate(e: dict, d: dict, context: dict, trace: list) -> str:
    op = e["op"]
    if op in COMPARISONS:
        left, right = _resolve(e["left"], d, context), _resolve(e["right"], d, context)
        step = {"op": op, "left": _public(left), "right": _public(right)}
        if left["value"] is None or right["value"] is None:
            step["result"] = UNRESOLVED
            step["reason"] = "; ".join(r["reason"] for r in (left, right) if r["value"] is None and r.get("reason")) or "an input is unavailable"
        elif left["unit"] != right["unit"]:
            step["result"], step["reason"] = UNRESOLVED, f"units differ ({left['unit']} vs {right['unit']}); nothing is converted"
        elif left["unit"] in ("currency", "currency/share") and left.get("currency") != right.get("currency"):
            step["result"], step["reason"] = UNRESOLVED, f"currencies differ ({left.get('currency')} vs {right.get('currency')}); nothing is converted"
        else:
            a, b = left["value"], right["value"]
            step["result"] = TRUE if {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op] else FALSE
        trace.append(step)
        return step["result"]
    if op == "not":
        inner = _evaluate(e["arg"], d, context, trace)
        return inner if inner == UNRESOLVED else (FALSE if inner == TRUE else TRUE)
    results = [_evaluate(sub, d, context, trace) for sub in e["args"]]
    if op == "all":
        return FALSE if FALSE in results else (UNRESOLVED if UNRESOLVED in results else TRUE)
    return TRUE if TRUE in results else (UNRESOLVED if UNRESOLVED in results else FALSE)


def _public(r):
    return {"label": r.get("label"), "value": None if r["value"] is None else str(r["value"]), "unit": r.get("unit"), "currency": r.get("currency"),
            "status": r["status"], "reason": r.get("reason"), "sources": r.get("sources", {}), **({"note": r["note"]} if r.get("note") else {})}


def evaluate(version: dict, d: dict, context: dict | None = None) -> list:
    """Evaluate every condition of a thesis version against a dossier (and its price context). Returns one record per condition with its status and trace."""
    out = []
    for c in version["conditions"]:
        trace = []
        status = _evaluate(c["expression"], d, context or {}, trace)
        out.append({"thesis_id": version["thesis_id"], "thesis_version_id": version["id"], "thesis_version": version["version"], "condition_id": c["id"],
                    "label": c["label"], "status": status, "trace": trace, "policy": d["policy"], "view": d["view"]})
    return out


def describe(e: dict) -> str:
    """A readable rendering of an expression (for pages and exports)."""
    op = e["op"]
    if op in COMPARISONS:
        return f"{_describe_operand(e['left'])} {op} {_describe_operand(e['right'])}"
    if op == "not":
        return f"not ({describe(e['arg'])})"
    return f" {op.upper()} ".join(f"({describe(a)})" for a in e["args"])


def _describe_operand(o):
    kind = o["kind"]
    if kind == "constant":
        return f"{o['value']}{'%' if o['unit'] == 'percent' else ' pp' if o['unit'] == 'percentage points' else ' ' + (o.get('currency') or '') + ('/share' if o['unit'] == 'currency/share' else '') if o['unit'] in ('currency', 'currency/share') else ' shares'}"
    if kind == "change":
        return next(label for k, label, _ in CHANGES if k == o["key"])
    if kind == "margin":
        return "operating margin (latest quarter)"
    if kind == "metric":
        return f"{LABELS[o['metric']]} ({o['at'].replace('_', ' ')})"
    if kind == "scenario":
        return f"{o['scenario']} scenario '{o.get('name', 'default')}' {o['measure'].replace('_', ' ')}"
    return "latest eligible close"


def shown(side: dict) -> str:
    """An evaluated operand for reading: rounded for display; the exact value stays in the trace."""
    if side.get("value") is None:
        return "unavailable"
    return display(side["value"], side.get("unit") or "pure", side.get("currency"))


def operand_options(scenario_names=("default",)) -> list:
    """(code, label) pairs for the form builder. A code is parsed by operand_from_code; nothing in it is executed."""
    out = [(f"change:{k}", label) for k, label, _ in CHANGES]
    out.append(("margin:operating_margin_latest_quarter", "Operating margin, latest quarter"))
    for m in HISTORY_METRICS:
        at = "latest_balance" if m in ("cash_and_equivalents", "total_assets", "total_liabilities", "stockholders_equity", "long_term_debt", "shares_outstanding") else None
        for when in ((at,) if at else ("latest_quarter", "latest_fiscal_year")):
            out.append((f"metric:{m}:{when}", f"{LABELS[m]} ({when.replace('_', ' ')})"))
    for name in scenario_names:
        for sc in ("bear", "base", "bull"):
            for measure in ("per_share", "enterprise_value"):
                out.append((f"scenario:{sc}:{name}:{measure}", f"{sc.capitalize()} scenario '{name}' {measure.replace('_', ' ')}"))
    out.append(("price:latest_close", "Latest eligible close (raw)"))
    return out


def operand_from_code(code: str) -> dict:
    parts = str(code or "").split(":")
    kind = parts[0]
    if kind == "change" and len(parts) == 2:
        return {"kind": "change", "key": parts[1]}
    if kind == "margin" and len(parts) == 2:
        return {"kind": "margin", "key": parts[1]}
    if kind == "metric" and len(parts) == 3:
        return {"kind": "metric", "metric": parts[1], "at": parts[2]}
    if kind == "scenario" and len(parts) == 4:
        return {"kind": "scenario", "scenario": parts[1], "name": parts[2], "measure": parts[3]}
    if kind == "price" and len(parts) == 2:
        return {"kind": "price", "measure": parts[1]}
    raise ConditionError(f"unknown operand {code!r}")
