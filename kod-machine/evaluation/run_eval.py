"""Run the analyst-task evaluation (evaluation/tasks.json) offline on fresh workspaces and score every answer against the hand-made expectations.

    python3 evaluation/run_eval.py [--out results.json] [--runs 2]

Each run builds a new workspace from the preserved SEC fixtures (examples/companyfacts, evaluation/fixtures) with a fixed clock, answers every task
through the same functions the workstation uses, and checks:

  * numbers against the expected value within the stated tolerance;
  * statuses (ok / missing / not_applicable / ...) and the words a reason must contain;
  * citations: every observation behind every supported change resolves, by its JSON pointer, to the same value, accession and period in the stored
    SEC response (no network; the preserved bytes);
  * reproducibility: the answers of separate runs (fresh workspaces) hash identically.

Outcomes per check: correct; allowed_unavailable (withheld, and the task allows it); missed (withheld where an answer exists); material_error (a value
or status presented as an answer that is wrong, or an answer where none should be given). Exit status 0 only when no material error was found.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
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
UNAVAILABLE = {"missing", "not_applicable", "incompatible", "not_derivable", "conflicted", "suspect", "unresolved"}


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def policy(cutoff, mode):
    return AsOfPolicy.parse(cutoff, mode, DAY_END)


class Checks:
    def __init__(self):
        self.items = []

    def add(self, name, outcome, expected=None, got=None, note=None):
        self.items.append({"check": name, "outcome": outcome, "expected": expected, "got": got, **({"note": note} if note else {})})

    def number(self, name, expected, got, tolerance="0", got_status="ok", allowed=()):
        if got_status != "ok" or got is None:
            self.add(name, "allowed_unavailable" if got_status in allowed else "missed", expected, got_status)
            return
        ok = abs(Decimal(str(got)) - Decimal(str(expected))) <= Decimal(str(tolerance))
        self.add(name, "correct" if ok else "material_error", expected, str(got))

    def status(self, name, expected, got, allowed=()):
        if got == expected:
            self.add(name, "correct", expected, got)
        elif got in allowed:
            self.add(name, "allowed_unavailable", expected, got)
        elif expected in UNAVAILABLE and got == "ok":
            self.add(name, "material_error", expected, got, "a value was presented where none should be")
        elif expected == "ok" and got in UNAVAILABLE:
            self.add(name, "missed", expected, got)
        else:
            self.add(name, "material_error", expected, got)

    def text(self, name, needle, haystack):
        self.add(name, "correct" if needle.lower() in (haystack or "").lower() else "material_error", needle, (haystack or "")[:300])


def import_company(service, ticker):
    sec = service.store.upsert_security(ticker, ticker, cik=CIKS[ticker])
    facts, subs = SOURCES[(ticker, "companyfacts")], SOURCES[(ticker, "submissions")]
    service.import_companyfacts(sec["id"], gzip.decompress((CF / facts["fixture"]).read_bytes()), facts["url"], observed_at=facts["observed_at"],
                                submissions=gzip.decompress((CF / subs["fixture"]).read_bytes()), submissions_url=subs["url"])
    return sec


def cell(d, group, metric, end):
    return next((c for c in d["history"][group].get(metric, []) if c["period"]["end"] == end), None)


def change(d, key):
    return next((c for c in d["changes"] if c["key"] == key), None)


def check_citations(service, d, checks, label):
    """Every observation behind a supported change must resolve in the stored SEC response to the value, accession and period it claims."""
    parsed, total, bad = {}, 0, []
    for ch in d["changes"]:
        if ch["status"] != "ok":
            continue
        stack, seen = [ch["calculation_id"]], set()
        while stack:
            cid = stack.pop()
            if cid in seen or cid not in d["calculations"]:
                continue
            seen.add(cid)
            for i in d["calculations"][cid]["inputs"]:
                if i["kind"] == "calculation":
                    stack.append(i["id"])
                    continue
                o = d["observations"].get(i["id"])
                if o is None or o["provider"] != "sec_companyfacts":
                    continue
                total += 1
                doc = o["source_document_id"]
                if doc not in parsed:
                    parsed[doc] = json.loads(service.store.raw(doc))
                try:
                    entry = companyfacts.resolve_pointer(parsed[doc], o["evidence"]["json_pointer"])
                except (KeyError, IndexError):
                    bad.append((o["id"], "pointer designates nothing"))
                    continue
                if Decimal(str(entry["val"])) != Decimal(o["raw_value"]) or entry.get("accn") != o["accession"] or entry["end"] != o["period"]["end"]:
                    bad.append((o["id"], f"source holds {entry.get('val')} {entry.get('accn')} {entry.get('end')}"))
    checks.add(f"{label}: citations resolve to the preserved response ({total} observations)", "correct" if total and not bad else "material_error" if bad else "missed",
               "all resolve", bad[:5] or total)
    return total


def run_dossier(service, task, secs, checks):
    citations = 0
    for b in task["builds"]:
        label = f"{b['cutoff'][:10]} {b['mode']} {b['view']}"
        d = dossier.build(service, secs[task["company"]]["id"], policy(b["cutoff"], b["mode"]), b["view"])
        e = b["expect"]
        if "latest_quarter_end" in e:
            checks.status(f"{label}: latest quarter", e["latest_quarter_end"], d.get("latest_quarter_end"))
        for c in e.get("cells", []):
            got = cell(d, c["group"], c["metric"], c["end"])
            name = f"{label}: {c['group']} {c['metric']} {c['end']}"
            shown = "ok" if got and got["status"] in ("reported", "derived") and got["value"] is not None else (got or {}).get("status", "missing")
            checks.number(name, c["value"], got and got["value"], "0", shown)
            if "revision" in c:
                revs = (got or {}).get("revisions", [])
                hit = [r for r in revs if Decimal(r["value"]) == Decimal(c["revision"]["value"]) and r["form"] == c["revision"]["form"]]
                checks.add(name + " revision", "correct" if hit else "missed", c["revision"], [(r["value"], r["form"]) for r in revs])
            if c.get("no_revisions"):
                revs = (got or {}).get("revisions", [])
                checks.add(name + " shows no later revision", "material_error" if revs else "correct", [], [(r["value"], r["form"]) for r in revs])
        for key, x in e.get("changes", {}).items():
            ch = change(d, key)
            name = f"{label}: {key}"
            allowed = tuple(x.get("allowed_statuses", ())) + tuple(s for s in UNAVAILABLE if key in task["allowed_unavailable"])
            if "value" in x:
                checks.number(name, x["value"], ch["value"], x.get("tolerance", "0"), ch["status"], allowed)
            else:
                checks.status(name, x["status"], ch["status"], allowed)
            if "reason_contains" in x:
                checks.text(name + " reason", x["reason_contains"], " ".join(ch["reasons"]))
            if "basis_contains" in x and ch["status"] == "ok":
                checks.text(name + " comparison basis", x["basis_contains"], ch.get("comparison_basis"))
            if "duration_contains" in x:
                checks.text(name + " period-length note", x["duration_contains"], (ch.get("duration_note") or "") + " " + " ".join(ch["reasons"]))
        citations += check_citations(service, d, checks, label)
    return {"citations_checked": citations}


def amount(value, unit):
    return Decimal(value) * SCALE.get(unit, Decimal(1))


def run_guidance(service, task, secs, checks):
    folder = HERE / task["fixtures"]
    src = json.loads((folder / "SOURCES.json").read_text())
    docs = {}
    for s in src:
        if s["kind"] == "release":
            raw = (folder / s["file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != s["sha256"]:
                raise SystemExit(f"fixture {s['file']} does not match its recorded SHA-256")
            headers = next(h for h in src if h["kind"] == "headers" and h["role"] == s["role"])
            docs[s["role"]] = earnings.prepare_source(str(folder / s["file"]), s["url"], sec_headers=str(folder / headers["file"]), retrieved_at=s["retrieved_at_utc"])
    result = earnings.analyse("Texas Instruments Incorporated", task["company"], "XNAS", docs["cur"], docs["pri"], task["as_of"], task["mode"])
    e = task["expect"]
    checks.add("reported period", "correct" if result["period"] in e["period_in"] else "material_error" if result["period"] else "missed", e["period_in"], result["period"])
    for f in e["facts"]:
        got = [x for x in result["facts"] if x["metric"] == f["metric"]]
        values = sorted({str(amount(x["value"], x["unit"]).normalize()) for x in got})
        if not got:
            checks.add(f"actual {f['metric']}", "missed", f["amount"], None)
        else:
            right = all(Decimal(v) == Decimal(f["amount"]) for v in values)
            checks.add(f"actual {f['metric']}", "correct" if right else "material_error", f["amount"], values)
    for g in e["guidance"]:
        got = [x for x in result["guidance_comparisons"] if x["metric"] == g["metric"]]
        if not got:
            checks.add(f"outlook {g['metric']}", "missed", g, [x["metric"] for x in result["guidance_comparisons"]] or result.get("guidance_not_compared"))
            continue
        x = got[0]
        lo, hi = (amount(x[k], x["unit"]) if x[k] is not None else None for k in ("guidance_low", "guidance_high"))
        right = lo == Decimal(g["low_amount"]) and hi == Decimal(g["high_amount"]) and x["position"] == g["position"]
        checks.add(f"outlook {g['metric']} range and position", "correct" if right else "material_error",
                   [g["low_amount"], g["high_amount"], g["position"]], [str(lo), str(hi), x["position"]])
    note = earnings.render_note(result)
    checks.add("the excluded-items caveat is visible in the note", "correct" if e["caveat_visible"] in note else "missed", e["caveat_visible"],
               "present" if e["caveat_visible"] in note else "absent from the rendered note")
    return {}


def independent_per_share(a, margin):
    """The MODEL.md formula, written again here (not imported), in floating point: a check on the model's arithmetic."""
    rev, pv, df, nopat = float(a["base"]["revenue"]), 0.0, 1.0, 0.0
    g, m, tax, da, capex, nwc, wacc = (float(a[k]) for k in ("revenue_growth", "operating_margin", "cash_tax_rate", "depreciation_rate", "capex_rate", "nwc_rate", "discount_rate"))
    m = float(margin)
    for t in range(1, a["horizon_years"] + 1):
        prev, rev = rev, rev * (1 + g)
        nopat = rev * m * (1 - tax)
        fcff = nopat + rev * da - rev * capex - (rev - prev) * nwc
        df = 1 / (1 + wacc) ** t
        pv += fcff * df
    tg, roic = float(a["terminal_growth"]), float(a["terminal_roic"])
    ev = pv + nopat * (1 + tg) * (1 - tg / roic) / (wacc - tg) * df
    return (ev + float(a["bridge"]["cash"]) - float(a["bridge"]["debt"]) - float(a["bridge"]["other_senior_claims"])) / float(a["shares"]["count"])


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
    before = next(x for x in first["theses"][0]["evaluations"] if x["condition_id"] == "base_value")
    checks.status("condition before the revision", e["before"], before["status"])
    clock.t = "2026-10-23T09:30:00Z"
    scenarios.save_assumptions(service, sid, "base", {**a, **task["revised"]}, "evaluation: margin cut")
    clock.t = "2026-10-23T09:40:00Z"
    second = decisions.review(service, sid, AsOfPolicy.parse("2026-10-23T09:40:00Z", "observed", DAY_END))
    after = next(x for x in second["theses"][0]["evaluations"] if x["condition_id"] == "base_value")
    checks.status("condition after the revision", e["after"], after["status"])
    trace = after["trace"][0]["left"]["sources"].get("assumption_trace", {})
    checks.add("trace names the changed assumption", "correct" if trace.get("changed") == e["changed"] else "material_error", e["changed"], trace.get("changed"))
    first_value = before["trace"][0]["left"]["sources"]["assumption_trace"]["result"]["per_share"]
    for name, got, margin, expected in (("per-share value before", first_value, a["operating_margin"], e["per_share_before"]),
                                        ("per-share value after", trace.get("result", {}).get("per_share"), task["revised"]["operating_margin"], e["per_share_after"])):
        checks.number(name + " (hand-computed expectation)", expected, got, e["per_share_tolerance"])
        mine = independent_per_share(a, margin)
        checks.add(name + " (independent re-implementation of MODEL.md)", "correct" if got and abs(Decimal(got) - Decimal(repr(mine))) < Decimal("0.0001") else "material_error",
                   round(mine, 6), got)
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
        c = cell(dossier.build(service, sec["id"], policy(later["cutoff"], task["mode"]), later["view"]), "annual", "revenue", "2024-09-01")
        shown = "ok" if c and c["status"] in ("reported", "derived") and c["value"] is not None else (c or {}).get("status", "missing")
        name = f"{later['cutoff'][:10]} {later['view']}: FY2024 revenue"
        checks.number(name, later["value"], c and c["value"], "0", shown)
        if "revision" in later:
            hit = [r for r in (c or {}).get("revisions", []) if Decimal(r["value"]) == Decimal(later["revision"]["value"]) and r["form"] == later["revision"]["form"]]
            checks.add(name + " lists the amendment", "correct" if hit else "missed", later["revision"], [(r["value"], r["form"]) for r in (c or {}).get("revisions", [])])
    return {}


def run_unsupported(service, task, secs, checks, clock):
    sid = secs[task["company"]]["id"]
    e = task["expect"]
    d = dossier.build(service, sid, policy(task["cutoff"], task["mode"]))
    checks.status("business type supported", e["business_supported"], d["coverage"]["business_type"]["supported"])
    for key in e["not_applicable_changes"]:
        checks.status(key, "not_applicable", change(d, key)["status"])
    clock.t = "2026-10-23T11:00:00Z"
    a = json.loads((HERE / "tasks.json").read_text())["tasks"]
    illustrative = next(t for t in a if t["kind"] == "assumption_to_review")["assumptions"]
    version = scenarios.save_assumptions(service, sid, "base", illustrative, "evaluation: any valid assumptions")
    checks.status("driver model", e["model_status"], scenarios.run_version(service, version["id"], record=False).valuation.status)
    return {}


def run_release(service, task, secs, checks):
    doc = earnings.read_document(task["html"].encode(), "synthetic.htm")
    src = {"doc": doc, "source_url": "https://example.com/synthetic.htm", "published_at": task["published_at"], "published_basis": "evaluation input",
           "observed_at": task["published_at"], "observed_basis": "evaluation input", "title": "synthetic"}
    result = earnings.analyse("Northwind Ltd.", "NWND", "XTSE", src, None, task["as_of"], "public")
    e = task["expect"]
    if "status" in e:
        checks.status("result status", e["status"], result["status"])
        checks.add("figures withheld", "correct" if len(result["facts"]) == e["facts_count"] else "material_error", e["facts_count"], len(result["facts"]))
        return {}
    checks.add("reported period", "correct" if result["period"] in e["period_in"] else "material_error" if result["period"] else "missed", e["period_in"], result["period"])
    for f in e["facts"]:
        got = [x for x in result["facts"] if x["metric"] == f["metric"]]
        values = sorted({str(amount(x["value"], x["unit"]).normalize()) for x in got})
        right = bool(got) and all(Decimal(v) == Decimal(f["amount"]) for v in values)
        checks.add(f"actual {f['metric']}", "correct" if right else "missed" if not got else "material_error", f["amount"], values)
        currencies = sorted({x["currency"] or "none" for x in got})
        if f["metric"] != "eps_diluted" and got:
            checks.add(f"currency of {f['metric']}", "correct" if currencies == [e["currency"]] else "material_error", e["currency"], currencies)
    for p in e["prior"]:
        got = [x for x in result["prior_period"] if x["metric"] == p["metric"] and x["relation"] == p["relation"]]
        if not got:
            checks.add(f"{p['relation'].lower()} {p['metric']}", "missed", p["prior_amount"], None)
            continue
        value = amount(got[0]["prior_actual"], got[0]["unit"])
        checks.add(f"{p['relation'].lower()} {p['metric']}", "correct" if value == Decimal(p["prior_amount"]) else "material_error", p["prior_amount"], str(value))
    return {}


def run_once(tasks):
    with tempfile.TemporaryDirectory(prefix="kod-eval-") as tmp:
        clock = Clock(START)
        service = ResearchService(Store(Path(tmp) / "workspace"), clock=clock)
        secs = {t: import_company(service, t) for t in sorted({x["company"] for x in tasks if x["kind"] not in ("release",)} & set(CIKS))}
        out = []
        for task in tasks:
            checks = Checks()
            started = time.perf_counter()
            extra = {}
            try:
                if task["kind"] == "dossier":
                    extra = run_dossier(service, task, secs, checks)
                elif task["kind"] == "guidance":
                    extra = run_guidance(service, task, secs, checks)
                elif task["kind"] == "assumption_to_review":
                    extra = run_assumption_to_review(service, task, secs, checks, clock)
                elif task["kind"] == "packet_reproduce":
                    extra = run_packet(service, task, secs, checks, clock)
                elif task["kind"] == "unsupported":
                    extra = run_unsupported(service, task, secs, checks, clock)
                elif task["kind"] == "release":
                    extra = run_release(service, task, secs, checks)
            except Exception as exc:                      # a crash is a failed task, recorded with its message
                checks.add("task ran", "material_error", "no exception", f"{type(exc).__name__}: {exc}"[:300])
            outcomes = [c["outcome"] for c in checks.items]
            out.append({"id": task["id"], "type": task["type"], "real": task["real"], "overlaps_development": bool(task["overlaps_development"]),
                        "seconds": round(time.perf_counter() - started, 3), "passed": all(o in ("correct", "allowed_unavailable") for o in outcomes),
                        "counts": {k: outcomes.count(k) for k in ("correct", "allowed_unavailable", "missed", "material_error")}, "checks": checks.items, **extra})
        return out


def answers_hash(results):
    stripped = [{k: v for k, v in r.items() if k != "seconds"} for r in results]
    return hashlib.sha256(json.dumps(stripped, sort_keys=True, default=str).encode()).hexdigest()


def summary_markdown(results, hashes):
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
              f"Citations resolved against the preserved responses: {sum(r.get('citations_checked', 0) for r in results)}.",
              f"Reproducibility: {len(hashes)} runs on fresh workspaces, answer hashes {'identical' if len(set(hashes)) == 1 else 'DIFFERENT'} ({hashes[0][:16]}…)."]
    for r in results:
        for c in r["checks"]:
            if c["outcome"] in ("missed", "material_error"):
                lines.append(f"- {r['id']} · {c['check']}: {c['outcome']} (expected {c['expected']}, got {c['got']})")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, help="write the full results as JSON")
    ap.add_argument("--runs", type=int, default=2, help="separate fresh-workspace runs compared for reproducibility (default 2)")
    args = ap.parse_args(argv)
    tasks = json.loads((HERE / "tasks.json").read_text())["tasks"]
    runs = [run_once(tasks) for _ in range(max(1, args.runs))]
    hashes = [answers_hash(r) for r in runs]
    results = runs[0]
    report = {"schema": "KOD-ANALYST-EVAL-RESULTS-v1", "tasks_file_sha256": hashlib.sha256((HERE / "tasks.json").read_bytes()).hexdigest(),
              "runs": len(runs), "answer_hashes": hashes, "reproducible": len(set(hashes)) == 1, "results": results}
    if args.out:
        args.out.write_text(json.dumps(report, indent=1, default=str) + "\n")
    print(summary_markdown(results, hashes))
    return 0 if not any(r["counts"]["material_error"] for r in results) and report["reproducible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
