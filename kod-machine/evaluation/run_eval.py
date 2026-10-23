"""Run the analyst-task evaluation (evaluation/tasks.json) offline on fresh workspaces and score every answer against the hand-made expectations.

    python3 evaluation/run_eval.py [--runs 2] [--out results.json] [--baseline results.json | --no-baseline]

Each run builds a new workspace from the preserved SEC fixtures (examples/companyfacts, evaluation/fixtures; every file's recorded SHA-256 is checked
first) with a fixed clock, answers every task through the same functions the workstation uses, and checks:

  * numbers against the expected value within the stated tolerance; statuses; the words a reason must contain;
  * citations: every observation behind every supported change must be in the dossier and resolve, by its JSON pointer, in the stored SEC response to the
    same concept, value, accession, form, filing date and period; the stored response must be byte-identical to the verified fixture;
  * the model's arithmetic, against a separate implementation of the formula in MODEL.md;
  * reproducibility: separate runs on fresh workspaces must produce identical outputs (a SHA-256 over every output, not only the scores).

Outcomes per check:
  * correct;
  * allowed_unavailable: withheld with a status and reason the task allows;
  * missed: withheld or not found where the documents hold an answer;
  * material_error: a wrong value or status presented as an answer, an answer where none should be, a withholding for a wrong reason, or a citation that
    does not resolve.

Exit status 1 on any material error, on answers that differ between runs, on a task without checks, or on a regression against the recorded baseline
(a check that was correct or allowed there and is not now).
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from kod import earnings  # noqa: E402
from kod.workstation import companyfacts, decisions, dossier, financials, scenarios, thesis  # noqa: E402
from kod.workstation.domain import canonical, identity  # noqa: E402
from kod.workstation.policy import DAY_END, AsOfPolicy  # noqa: E402
from kod.workstation.services import ResearchService  # noqa: E402
from kod.workstation.store import Store  # noqa: E402

CF = ROOT / "examples" / "companyfacts"
SOURCES = {(s["ticker"], s["kind"]): s for s in json.loads((CF / "SOURCES.json").read_text())}
CIKS = {"TXN": "97476", "COST": "909832", "JPM": "19617", "NVDA": "1045810", "AAPL": "320193"}
START = "2026-10-23T09:00:00Z"
SCALE = {"thousands": Decimal(1000), "millions": Decimal(10) ** 6, "billions": Decimal(10) ** 9}
UNAVAILABLE = {"missing", "not_applicable", "incompatible", "not_derivable", "conflicted", "suspect", "unresolved", "PERIOD_UNRESOLVED"}
GOOD = ("correct", "allowed_unavailable")


class FixtureError(SystemExit):
    pass


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def policy(cutoff, mode):
    return AsOfPolicy.parse(cutoff, mode, DAY_END)


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


class Checks:
    def __init__(self):
        self.items = []
        self.outputs = []                      # SHA-256 of every output the task produced (for the reproducibility hash)

    def output(self, obj):
        self.outputs.append(digest(obj))

    def add(self, name, outcome, expected=None, got=None, note=None):
        self.items.append({"check": name, "outcome": outcome, "expected": expected, "got": got, **({"note": note} if note else {})})

    def _withheld(self, name, expected, status, allowed, reason, reason_contains):
        if status in allowed:
            if reason_contains and reason_contains.lower() not in (reason or "").lower():
                self.add(name, "material_error", expected, status, f"withheld for another reason than the expected one: {(reason or '')[:200]}")
            else:
                self.add(name, "allowed_unavailable", expected, status)
        else:
            self.add(name, "missed", expected, status, (reason or "")[:200] or None)

    def number(self, name, expected, got, tolerance="0", got_status="ok", allowed=(), reason=None, reason_contains=None):
        if got_status != "ok" or got is None:
            self._withheld(name, expected, got_status if got_status != "ok" else "no value", allowed, reason, reason_contains)
            return
        ok = abs(Decimal(str(got)) - Decimal(str(expected))) <= Decimal(str(tolerance))
        self.add(name, "correct" if ok else "material_error", expected, str(got))

    def status(self, name, expected, got, allowed=(), reason=None, reason_contains=None):
        if got == expected:
            if reason_contains and expected in UNAVAILABLE and reason_contains.lower() not in (reason or "").lower():
                self.add(name, "material_error", expected, got, f"the reason does not say why: {(reason or '')[:200]}")
            else:
                self.add(name, "correct", expected, got)
        elif got in allowed:
            self._withheld(name, expected, got, allowed, reason, reason_contains)
        elif expected in UNAVAILABLE and got == "ok":
            self.add(name, "material_error", expected, got, "a value was presented where none should be")
        elif got in UNAVAILABLE and (expected == "ok" or expected in UNAVAILABLE):     # withheld, but not with the status the documents call for
            self.add(name, "missed", expected, got, (reason or "")[:200] or None)
        else:
            self.add(name, "material_error", expected, got)

    def text(self, name, needle, haystack):
        self.add(name, "correct" if needle.lower() in (haystack or "").lower() else "material_error", needle, (haystack or "")[:300])

    def same_filing(self, name, basis):
        ok = "presented in the same filing" in (basis or "") and "not presented" not in (basis or "")
        self.add(name, "correct" if ok else "material_error", "year-ago figure presented in the same filing(s)", (basis or "")[:300])


def fixture_bytes(path: Path, sha256: str) -> bytes:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise FixtureError(f"fixture {path} does not match its recorded SHA-256; refusing to evaluate")
    return raw


def import_company(service, ticker, stored_sha):
    try:
        sec = service.store.upsert_security(ticker, ticker, cik=CIKS[ticker], now=service.clock())     # identity recorded on the run's fixed clock
    except TypeError:                                    # code from before upsert_security took a time (used to measure earlier commits)
        sec = service.store.upsert_security(ticker, ticker, cik=CIKS[ticker])
    facts, subs = SOURCES[(ticker, "companyfacts")], SOURCES[(ticker, "submissions")]
    raw_facts = gzip.decompress(fixture_bytes(CF / facts["fixture"], facts["fixture_sha256"]))
    raw_subs = gzip.decompress(fixture_bytes(CF / subs["fixture"], subs["fixture_sha256"]))
    stored_sha.update({hashlib.sha256(raw_facts).hexdigest(), hashlib.sha256(raw_subs).hexdigest()})
    service.import_companyfacts(sec["id"], raw_facts, facts["url"], observed_at=facts["observed_at"], submissions=raw_subs, submissions_url=subs["url"])
    return sec


CELL_KEYS = {"group", "metric", "end", "value", "revision", "no_revisions"}
CHANGE_KEYS = {"status", "value", "tolerance", "allowed_statuses", "reason_contains", "basis_contains", "duration_contains"}


def known_keys(where, expect, allowed):
    """A misspelled expectation key would silently skip its check; refuse it instead (the task then fails as crashed)."""
    unknown = set(expect) - allowed
    if unknown:
        raise ValueError(f"{where}: unknown expectation keys {sorted(unknown)}")


def cell(d, group, metric, end):
    return next((c for c in d["history"][group].get(metric, []) if c["period"]["end"] == end), None)


def count_cells(d, group, metric, end):
    return sum(1 for c in d["history"][group].get(metric, []) if c["period"]["end"] == end)


def cell_status(c):
    return "ok" if c and c["status"] in ("reported", "derived") and c["value"] is not None else (c or {}).get("status", "missing")


def change(d, key):
    return next((c for c in d["changes"] if c["key"] == key), None)


def check_citations(service, d, checks, label, stored_sha):
    """Every observation behind every supported change: present in the dossier, resolving in the stored, fixture-identical response to the same concept,
    value, accession, form, filing date and period."""
    parsed, references, distinct, bad, other = {}, 0, set(), [], 0
    supported = [ch for ch in d["changes"] if ch["status"] == "ok"]
    for ch in supported:
        stack, seen = [ch["calculation_id"]], set()
        while stack:
            cid = stack.pop()
            if cid in seen:
                continue
            seen.add(cid)
            if cid not in d["calculations"]:
                bad.append((cid, "calculation not in the dossier"))
                continue
            for i in d["calculations"][cid]["inputs"]:
                if i["kind"] == "calculation":
                    stack.append(i["id"])
                    continue
                if i["kind"] != "observation":
                    continue
                o = d["observations"].get(i["id"])
                if o is None:
                    bad.append((i["id"], "observation not in the dossier"))
                    continue
                if o["provider"] != "sec_companyfacts":
                    other += 1
                    continue
                references += 1
                distinct.add(o["id"])
                doc_id = o["source_document_id"]
                if doc_id not in parsed:
                    document = service.store.document(doc_id)
                    if document["sha256"] not in stored_sha:
                        bad.append((o["id"], "the stored response is not byte-identical to a verified fixture"))
                        parsed[doc_id] = None
                        continue
                    parsed[doc_id] = json.loads(service.store.raw(doc_id))
                if parsed[doc_id] is None:
                    continue
                pointer = o["evidence"].get("json_pointer", "")
                try:
                    entry = companyfacts.resolve_pointer(parsed[doc_id], pointer)
                except (KeyError, IndexError):
                    bad.append((o["id"], "pointer designates nothing"))
                    continue
                parts = pointer.split("/")
                concept = f"{parts[2]}:{parts[3]}" if len(parts) > 3 else None
                period = o["period"]
                problems = [name for name, ok in (
                    ("concept", concept == o["concept"]), ("value", Decimal(str(entry.get("val"))) == Decimal(o["raw_value"]) == Decimal(o["value"])),
                    ("accession", entry.get("accn") == o["accession"]), ("form", entry.get("form") == o["form"]), ("filed", entry.get("filed") == o["filed"]),
                    ("end", entry.get("end") == (period.get("end") or period.get("instant"))), ("start", entry.get("start") == period.get("start"))) if not ok]
                if problems:
                    bad.append((o["id"], "differs in " + ", ".join(problems)))
    name = f"{label}: citations resolve"                 # counts go in the result, so a change in them is not read as a different check
    if bad:
        checks.add(name, "material_error", "all resolve", bad[:5])
    elif supported and not distinct and not other:
        checks.add(name, "material_error", "supported changes cite verifiable observations", "none")
    else:
        checks.add(name, "correct", "all resolve", f"{len(distinct)} distinct observations, {references} references"
                   + (f"; {other} non-SEC inputs not checked here" if other else ""))
    return len(distinct)


def run_dossier(service, task, secs, checks, stored_sha):
    citations = 0
    for b in task["builds"]:
        label = f"{b['cutoff'][:10]} {b['mode']} {b['view']}"
        d = dossier.build(service, secs[task["company"]]["id"], policy(b["cutoff"], b["mode"]), b["view"])
        checks.output(d)
        e = b["expect"]
        if "latest_quarter_end" in e:
            checks.status(f"{label}: latest quarter", e["latest_quarter_end"], d.get("latest_quarter_end"))
        for c in e.get("cells", []):
            known_keys(label, c, CELL_KEYS)
            got = cell(d, c["group"], c["metric"], c["end"])
            name = f"{label}: {c['group']} {c['metric']} {c['end']}"
            if count_cells(d, c["group"], c["metric"], c["end"]) > 1:
                checks.add(name + " listed once", "material_error", 1, count_cells(d, c["group"], c["metric"], c["end"]))
            checks.number(name, c["value"], got and got["value"], "0", cell_status(got), reason="; ".join((got or {}).get("reasons", [])))
            revs = (got or {}).get("revisions", [])
            if "revision" in c:
                hit = [r for r in revs if Decimal(r["value"]) == Decimal(c["revision"]["value"]) and r["form"] == c["revision"]["form"]]
                checks.add(name + " revision", "correct" if hit else "missed", c["revision"], [(r["value"], r["form"]) for r in revs])
            if c.get("no_revisions"):
                checks.add(name + " shows no later revision", "material_error" if revs else "correct", [], [(r["value"], r["form"]) for r in revs])
        for key, x in e.get("changes", {}).items():
            known_keys(f"{label} {key}", x, CHANGE_KEYS)
            ch = change(d, key)
            name = f"{label}: {key}"
            if sum(1 for c in d["changes"] if c["key"] == key) > 1:
                checks.add(name + " listed once", "material_error", 1, sum(1 for c in d["changes"] if c["key"] == key))
            if ch is None:
                checks.add(name, "missed", x, "not in the dossier")
                continue
            reason = " ".join(ch["reasons"])
            allowed = tuple(x.get("allowed_statuses", ()))
            if "value" in x:
                checks.number(name, x["value"], ch["value"], x.get("tolerance", "0"), ch["status"], allowed, reason, x.get("reason_contains"))
            else:
                checks.status(name, x["status"], ch["status"], allowed, reason, x.get("reason_contains"))
            if "basis_contains" in x and ch["status"] == "ok":
                checks.same_filing(name + " comparison basis", ch.get("comparison_basis"))
            for needle in ([x["duration_contains"]] if isinstance(x.get("duration_contains"), str) else x.get("duration_contains", [])):
                checks.text(f"{name} period-length note ({needle})", needle, (ch.get("duration_note") or "") + " " + reason)
        citations += check_citations(service, d, checks, label, stored_sha)
    return {"citations_checked": citations}


def amount(value, unit):
    return Decimal(value) * SCALE.get(unit, Decimal(1))


def release_sources(folder):
    src = json.loads((folder / "SOURCES.json").read_text())
    for s in src:                                                   # every fixture file, releases and headers alike
        fixture_bytes(folder / s["file"], s["sha256"])
    return src


def check_facts(checks, result, expected_facts, currency=None, prefix="actual"):
    for f in expected_facts:
        got = [x for x in result["facts"] if x["metric"] == f["metric"]]
        values = sorted({str(amount(x["value"], x["unit"]).normalize()) for x in got})
        periods = sorted({x["period"] for x in got})
        if not got:
            checks.add(f"{prefix} {f['metric']}", "missed", f["amount"], None)
            continue
        right = all(Decimal(v) == Decimal(f["amount"]) for v in values) and periods == [result["period"]]
        checks.add(f"{prefix} {f['metric']}", "correct" if right else "material_error", f["amount"], {"values": values, "periods": periods})
        if currency:
            currencies = sorted({x["currency"] or "none" for x in got})
            checks.add(f"{prefix} {f['metric']} currency", "correct" if currencies == [currency] else "material_error", currency, currencies)


def run_guidance(service, task, secs, checks, stored_sha):
    folder = HERE / task["fixtures"]
    src = release_sources(folder)
    docs = {}
    for s in src:
        if s["kind"] == "release":
            headers = next(h for h in src if h["kind"] == "headers" and h["role"] == s["role"])
            docs[s["role"]] = earnings.prepare_source(str(folder / s["file"]), s["url"], sec_headers=str(folder / headers["file"]), retrieved_at=s["retrieved_at_utc"])
    result = earnings.analyse("Texas Instruments Incorporated", task["company"], "XNAS", docs["cur"], docs["pri"], task["as_of"], task["mode"])
    checks.output({k: v for k, v in result.items() if k != "workbench_report"})
    e = task["expect"]
    checks.add("reported period", "correct" if result["period"] in e["period_in"] else "material_error" if result["period"] else "missed", e["period_in"], result["period"])
    check_facts(checks, result, e["facts"], e.get("currency"))
    for g in e["guidance"]:
        rows = [x for x in result["guidance_comparisons"] if x["metric"] == g["metric"]]
        if not rows:
            checks.add(f"outlook {g['metric']}", "missed", g, [x["metric"] for x in result["guidance_comparisons"]] or result.get("guidance_not_compared"))
            continue
        seen = sorted({json.dumps([str(amount(x["guidance_low"], x["unit"])) if x["guidance_low"] is not None else None,
                                   str(amount(x["guidance_high"], x["unit"])) if x["guidance_high"] is not None else None, x["position"],
                                   str(amount(x["actual"], x["unit"])), x["period"], x["currency"]]) for x in rows})
        want = [g["low_amount"], g["high_amount"], g["position"], g["actual_amount"], result["period"], e.get("currency")]
        right = len(seen) == 1 and all(Decimal(a) == Decimal(b) if i in (0, 1, 3) else a == b for i, (a, b) in enumerate(zip(json.loads(seen[0]), want)))
        checks.add(f"outlook {g['metric']} range, actual and position", "correct" if right else "material_error", want, [json.loads(s) for s in seen])
    note = earnings.render_note(result)
    checks.output(note)
    checks.add("the excluded-items caveat is visible in the note", "correct" if e["caveat_visible"] in note else "missed", e["caveat_visible"],
               "present" if e["caveat_visible"] in note else "absent from the rendered note")
    return {}


def independent_per_share(a, margin):
    """The MODEL.md formula written again here, not imported from KOD, in decimals: yearly paths, the tax floor on losses, the value-driver terminal
    value and the full bridge (cash, debt, other senior claims, other adjustments)."""
    with localcontext() as ctx:
        ctx.prec = 34
        n = a["horizon_years"]

        def path(name):
            v = margin if name == "operating_margin" and margin is not None else a[name]
            return [Decimal(str(x)) for x in v] if isinstance(v, list) else [Decimal(str(v))] * n
        g, m, tax, da, capex, nwc = (path(k) for k in ("revenue_growth", "operating_margin", "cash_tax_rate", "depreciation_rate", "capex_rate", "nwc_rate"))
        wacc, tg, roic = (Decimal(str(a[k])) for k in ("discount_rate", "terminal_growth", "terminal_roic"))
        rev, pv, df, nopat = Decimal(str(a["base"]["revenue"])), Decimal(0), Decimal(1), Decimal(0)
        for t in range(n):
            prev, rev = rev, rev * (1 + g[t])
            ebit = rev * m[t]
            nopat = ebit - max(ebit, Decimal(0)) * tax[t]
            fcff = nopat + rev * da[t] - rev * capex[t] - (rev - prev) * nwc[t]
            df = 1 / (1 + wacc) ** (t + 1)
            pv += fcff * df
        ev = pv + nopat * (1 + tg) * (1 - tg / roic) / (wacc - tg) * df
        b = {k: Decimal(str(a["bridge"].get(k) or 0)) for k in ("cash", "debt", "other_senior_claims", "other_adjustments")}
        return (ev + b["cash"] - b["debt"] - b["other_senior_claims"] + b["other_adjustments"]) / Decimal(str(a["shares"]["count"]))


def run_assumption_to_review(service, task, secs, checks, clock):
    sid = secs[task["company"]]["id"]
    a, e = task["assumptions"], task["expect"]
    clock.t = "2026-10-23T09:10:00Z"
    scenarios.save_assumptions(service, sid, "base", a, "evaluation: illustrative inputs")
    decisions.save_thesis(service, sid, "Evaluation thesis", "The base case stays above the threshold.", [
        thesis.comparison({"kind": "scenario", "scenario": "base", "name": "default", "measure": "per_share"}, "<",
                          {"kind": "constant", "value": task["threshold"], "unit": "currency/share", "currency": "USD"},
                          f"Review if the base case falls below {task['threshold']} per share", "base_value")], "evaluation")
    clock.t = "2026-10-23T09:20:00Z"
    first = decisions.review(service, sid, AsOfPolicy.parse("2026-10-23T09:20:00Z", "observed", DAY_END))
    checks.output(first)
    before = next(x for x in first["theses"][0]["evaluations"] if x["condition_id"] == "base_value")
    checks.status("condition before the revision", e["before"], before["status"])
    clock.t = "2026-10-23T09:30:00Z"
    scenarios.save_assumptions(service, sid, "base", {**a, **task["revised"]}, "evaluation: margin cut")
    clock.t = "2026-10-23T09:40:00Z"
    second = decisions.review(service, sid, AsOfPolicy.parse("2026-10-23T09:40:00Z", "observed", DAY_END))
    checks.output(second)
    after = next(x for x in second["theses"][0]["evaluations"] if x["condition_id"] == "base_value")
    checks.status("condition after the revision", e["after"], after["status"])
    trace = after["trace"][0]["left"]["sources"].get("assumption_trace", {})
    checks.add("trace names the changed assumption", "correct" if trace.get("changed") == e["changed"] else "material_error", e["changed"], trace.get("changed"))
    first_value = before["trace"][0]["left"]["sources"]["assumption_trace"]["result"]["per_share"]
    for name, got, margin, expected in (("per-share value before", first_value, None, e["per_share_before"]),
                                        ("per-share value after", trace.get("result", {}).get("per_share"), task["revised"]["operating_margin"], e["per_share_after"])):
        checks.number(name + " (hand-computed expectation)", expected, got, e["per_share_tolerance"])
        mine = independent_per_share(a, margin)
        checks.add(name + " (separate implementation of MODEL.md)", "correct" if got and abs(Decimal(got) - mine) < Decimal("0.000001") else "material_error",
                   str(mine), got)
    return {}


def synthetic_amendment(service, sec, value, filed):
    store = service.store
    doc = store.save_document(sec["id"], b'{"synthetic": "evaluation amendment"}', "amendment.json", "https://data.sec.gov/api/xbrl/companyfacts/CIK0000909832.json",
                              published_at=None, published_basis="synthetic evaluation amendment", observed_at=service.clock(), role="other",
                              association="user_asserted", provider="evaluation", extraction_status="companyfacts", metadata={"kind": "evaluation"})
    p = financials.period("12 months", start="2023-09-04", end="2024-09-01")
    oid = identity("fob", "evaluation-synthetic", value)
    row = {"id": oid, "provider": "sec_companyfacts", "issuer_id": None, "security_id": sec["id"], "concept": "Revenues", "taxonomy": "us-gaap",
           "metric": "revenue", "metric_version": 1, "raw_value": value, "value": value, "unit": "currency", "scale": 1, "currency": "USD",
           "currency_basis": "UNIT_OF_MEASURE", "period_id": p.id, "basis": "GAAP", "context": "consolidated (companyfacts whole entity)", "dimensions_available": 0,
           "accession": "0009999999-25-000001", "form": "10-K/A", "filed": filed, "amendment": 1, "source_document_id": doc["id"], "source_sha256": doc["sha256"],
           "evidence": canonical({"json_pointer": "/synthetic"}), "published_at": None, "publication_date": filed, "publication_precision": "date",
           "publication_basis": "synthetic", "observed_at": service.clock(), "recorded_at": service.clock(), "parser_version": "evaluation", "mapping_version": "evaluation",
           "flags": "[]"}
    store.record_observations([p], [row])


def run_packet(service, task, secs, checks, clock):
    sec = secs[task["company"]]
    e = task["expect"]
    pol = policy(task["cutoff"], task["mode"])
    clock.t = "2026-10-23T10:00:00Z"
    stored = decisions.save_packet(service, sec["id"], pol, "as_reported", "Did fiscal 2024 revenue turn into profit and cash?", "keep researching",
                                   "evaluation decision")
    checks.output(stored["packet"])
    checks.add("packet reproduces when reopened", "correct" if decisions.reproduce(service, stored["id"])["reproduced"] == e["reproduced_before"] else "material_error",
               e["reproduced_before"], None)
    before = json.dumps(dossier.build(service, sec["id"], pol), sort_keys=True, default=str)
    clock.t = "2026-10-23T10:10:00Z"
    synthetic_amendment(service, sec, "999999000000", "2025-03-01")
    again = decisions.reproduce(service, stored["id"])
    checks.add("packet still reproduces after the later amendment", "correct" if again["reproduced"] == e["reproduced_after"] else "material_error",
               e["reproduced_after"], again["reproduced"])
    checks.add("dossier at the packet's cutoff unchanged", "correct" if (json.dumps(dossier.build(service, sec["id"], pol), sort_keys=True, default=str) == before)
               == e["dossier_unchanged_at_cutoff"] else "material_error", e["dossier_unchanged_at_cutoff"], None)
    stored_again = decisions.packet(service, stored["id"])
    checks.add("stored packet hash verifies", "correct" if stored_again["packet_sha256"] == stored["packet_sha256"] else "material_error", stored["packet_sha256"],
               stored_again["packet_sha256"])
    for later in task["later_checks"]:
        d = dossier.build(service, sec["id"], policy(later["cutoff"], task["mode"]), later["view"])
        checks.output(d)
        c = cell(d, "annual", "revenue", "2024-09-01")
        name = f"{later['cutoff'][:10]} {later['view']}: FY2024 revenue"
        checks.number(name, later["value"], c and c["value"], "0", cell_status(c))
        if "revision" in later:
            hit = [r for r in (c or {}).get("revisions", []) if Decimal(r["value"]) == Decimal(later["revision"]["value"]) and r["form"] == later["revision"]["form"]]
            checks.add(name + " lists the amendment", "correct" if hit else "missed", later["revision"], [(r["value"], r["form"]) for r in (c or {}).get("revisions", [])])
    return {}


def run_unsupported(service, task, secs, checks, clock):
    sid = secs[task["company"]]["id"]
    e = task["expect"]
    d = dossier.build(service, sid, policy(task["cutoff"], task["mode"]))
    checks.output(d)
    checks.status("business type supported", e["business_supported"], d["coverage"]["business_type"]["supported"])
    for key in e["not_applicable_changes"]:
        ch = change(d, key)
        checks.status(key, "not_applicable", ch["status"], reason=" ".join(ch["reasons"]), reason_contains="bank")
    clock.t = "2026-10-23T11:00:00Z"
    tasks = json.loads((HERE / "tasks.json").read_text())["tasks"]
    illustrative = next(t for t in tasks if t["kind"] == "assumption_to_review")["assumptions"]
    version = scenarios.save_assumptions(service, sid, "base", illustrative, "evaluation: any valid assumptions")
    valuation = scenarios.run_version(service, version["id"], record=False).valuation
    checks.status("driver model", e["model_status"], valuation.status, reason=" ".join(valuation.warnings), reason_contains="bank")
    return {}


def release_source(task, html):
    return {"doc": earnings.read_document(html.encode(), "synthetic.htm"), "source_url": "https://example.com/synthetic.htm", "published_at": task["published_at"],
            "published_basis": "evaluation input", "observed_at": task["published_at"], "observed_basis": "evaluation input", "title": "synthetic"}


def run_release(service, task, secs, checks):
    result = earnings.analyse("Northwind Ltd.", "NWND", "XTSE", release_source(task, task["html"]), None, task["as_of"], "public")
    checks.output({k: v for k, v in result.items() if k != "workbench_report"})
    e = task["expect"]
    checks.add("reported period", "correct" if result["period"] in e["period_in"] else "material_error" if result["period"] else "missed", e["period_in"],
               result["period"] or result.get("status"))
    check_facts(checks, result, e["facts"], e.get("currency"))
    for p in e["prior"]:
        rows = [x for x in result["prior_period"] if x["metric"] == p["metric"] and x["relation"] == p["relation"]]
        name = f"{p['relation'].lower()} {p['metric']}"
        if not rows:
            checks.add(name, "missed", p["prior_amount"], None)
            continue
        values = sorted({str(amount(x["prior_actual"], x["unit"]).normalize()) for x in rows})
        checks.add(name, "correct" if values == [str(Decimal(p["prior_amount"]).normalize())] else "material_error", p["prior_amount"], values)
        if "growth_pct" in p:
            growth = sorted({x["difference_pct"] for x in rows}, key=str)
            ok = len(growth) == 1 and growth[0] is not None and abs(Decimal(growth[0]) - Decimal(p["growth_pct"])) <= Decimal(p["growth_tolerance"])
            checks.add(name + " growth", "correct" if ok else "material_error", p["growth_pct"], growth)
    if "analyst_period" in e:
        recorded = earnings.analyse("Northwind Ltd.", "NWND", "XTSE", release_source(task, task["html"]), None, task["as_of"], "public",
                                    period_override=e["analyst_period"])
        checks.output({k: v for k, v in recorded.items() if k != "workbench_report"})
        check_facts(checks, recorded, e["facts"], e.get("currency"), prefix=f"with the analyst's period record ({e['analyst_period']}):")
    return {}


def run_once(tasks):
    with tempfile.TemporaryDirectory(prefix="kod-eval-") as tmp:
        clock = Clock(START)
        service = ResearchService(Store(Path(tmp) / "workspace"), clock=clock)
        stored_sha = set()
        secs = {t: import_company(service, t, stored_sha) for t in sorted({x["company"] for x in tasks if x["kind"] != "release"} & set(CIKS))}
        out = []
        for task in tasks:
            checks = Checks()
            started = time.perf_counter()
            extra = {}
            try:
                kind = task["kind"]
                if kind == "dossier":
                    extra = run_dossier(service, task, secs, checks, stored_sha)
                elif kind == "guidance":
                    extra = run_guidance(service, task, secs, checks, stored_sha)
                elif kind == "assumption_to_review":
                    extra = run_assumption_to_review(service, task, secs, checks, clock)
                elif kind == "packet_reproduce":
                    extra = run_packet(service, task, secs, checks, clock)
                elif kind == "unsupported":
                    extra = run_unsupported(service, task, secs, checks, clock)
                elif kind == "release":
                    extra = run_release(service, task, secs, checks)
                else:
                    raise ValueError(f"unknown task kind {kind!r}")
            except FixtureError:
                raise
            except Exception as exc:                      # a crash is a failed task, recorded with its message
                checks.add("task ran", "material_error", "no exception", f"{type(exc).__name__}: {exc}"[:300])
            if not checks.items:
                checks.add("task has checks", "material_error", "at least one check", "none")
            outcomes = [c["outcome"] for c in checks.items]
            out.append({"id": task["id"], "type": task["type"], "real": task["real"], "overlaps_development": bool(task["overlaps_development"]),
                        "seconds": round(time.perf_counter() - started, 3), "passed": all(o in GOOD for o in outcomes),
                        "counts": {k: outcomes.count(k) for k in ("correct", "allowed_unavailable", "missed", "material_error")}, "checks": checks.items,
                        "output_sha256": checks.outputs, **extra})
        return out


def answers_hash(results):
    """Over every check record and the SHA-256 of every output each task produced (timings excluded)."""
    return digest([{k: v for k, v in r.items() if k != "seconds"} for r in results])


def regressions(results, baseline):
    """Checks that were correct or allowed in the baseline and are not now (a check missing now counts as a regression)."""
    now = {(r["id"], c["check"]): c["outcome"] for r in results for c in r["checks"]}
    out = []
    for r in baseline["results"]:
        for c in r["checks"]:
            if c["outcome"] in GOOD and now.get((r["id"], c["check"])) not in GOOD:
                out.append(f"{r['id']} · {c['check']}: {c['outcome']} -> {now.get((r['id'], c['check']), 'absent')}")
    return out


def summary_markdown(results, hashes, regressed=None):
    lines = ["| Task | Real | Overlaps dev | Checks | Correct | Allowed unavailable | Missed | Material errors | Citations | Seconds | Passed |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        c = r["counts"]
        lines.append(f"| {r['id']} | {'yes' if r['real'] else 'synthetic'} | {'yes' if r['overlaps_development'] else 'no'} | {sum(c.values())} | {c['correct']} | "
                     f"{c['allowed_unavailable']} | {c['missed']} | {c['material_error']} | {r.get('citations_checked', '')} | {r['seconds']} | {'yes' if r['passed'] else 'NO'} |")
    total = {k: sum(r["counts"][k] for r in results) for k in ("correct", "allowed_unavailable", "missed", "material_error")}
    fresh = [r for r in results if not r["overlaps_development"]]
    lines += ["", f"Tasks passed: {sum(r['passed'] for r in results)} of {len(results)} (not overlapping development tests: "
                  f"{sum(r['passed'] for r in fresh)} of {len(fresh)}).",
              f"Checks: {sum(total.values())}; correct {total['correct']}, allowed unavailable {total['allowed_unavailable']}, missed {total['missed']}, "
              f"material errors {total['material_error']}.",
              f"Citations: {sum(r.get('citations_checked', 0) for r in results)} distinct observations (counted per build) resolved against the verified preserved responses.",
              f"Reproducibility: {len(hashes)} run(s) on fresh workspaces; output hashes "
              f"{'not compared (one run)' if len(hashes) == 1 else 'identical' if len(set(hashes)) == 1 else 'DIFFERENT'} ({hashes[0][:16]}…)."]
    if regressed is not None:
        lines.append(f"Regressions against the baseline: {len(regressed)}." + "".join(f"\n- {x}" for x in regressed))
    for r in results:
        for c in r["checks"]:
            if c["outcome"] in ("missed", "material_error"):
                lines.append(f"- {r['id']} · {c['check']}: {c['outcome']} (expected {c['expected']}, got {c['got']})")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, help="write the full results as JSON")
    ap.add_argument("--runs", type=int, default=2, help="separate fresh-workspace runs compared for reproducibility (default 2)")
    ap.add_argument("--baseline", type=Path, default=HERE / "results.json", help="recorded results to compare against (default evaluation/results.json)")
    ap.add_argument("--no-baseline", action="store_true", help="do not compare with recorded results")
    args = ap.parse_args(argv)
    tasks = json.loads((HERE / "tasks.json").read_text())["tasks"]
    runs = [run_once(tasks) for _ in range(max(1, args.runs))]
    hashes = [answers_hash(r) for r in runs]
    results = runs[0]
    regressed = None
    if not args.no_baseline:
        if not args.baseline.exists():                   # a missing baseline must not silently turn the regression gate off
            print(f"no baseline at {args.baseline}; pass --no-baseline to run without one", file=sys.stderr)
            return 1
        regressed = regressions(results, json.loads(args.baseline.read_text()))
    report = {"schema": "KOD-ANALYST-EVAL-RESULTS-v2", "tasks_file_sha256": hashlib.sha256((HERE / "tasks.json").read_bytes()).hexdigest(),
              "runs": len(runs), "answer_hashes": hashes, "reproducible": None if len(runs) == 1 else len(set(hashes)) == 1, "results": results}
    if args.out:
        args.out.write_text(json.dumps(report, indent=1, default=str) + "\n")
    print(summary_markdown(results, hashes, regressed))
    failed = any(r["counts"]["material_error"] for r in results) or report["reproducible"] is False or bool(regressed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
