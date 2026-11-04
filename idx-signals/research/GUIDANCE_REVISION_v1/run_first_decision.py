"""Record the first bounded guidance-paper cohort and a separate known historical fixture.

Uses saved acquisitions. No network requests and no historical price loading.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from idxsig import guidance as g
from idxsig.paper import verify_chain, ledger_lines


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open("x") as out:
        out.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fixture():
    binding = json.loads((ROOT / "fixtures/bindings.json").read_text())
    sources = {}
    for key, source in binding["sources"].items():
        compressed = (ROOT / source["path"]).read_bytes()
        if hashlib.sha256(compressed).hexdigest() != source["gzip_sha256"]:
            raise ValueError("fixture compression hash mismatch")
        raw = gzip.decompress(compressed)
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("fixture original hash mismatch")
        sources[key] = g.submission(raw, 2488, source["accession"])
    old_quote = "For the full year 2021, AMD expects revenue growth of approximately 37 percent over 2020 driven by growth in all businesses."
    new_quote = "For the full year 2021, AMD now expects revenue growth of approximately 50 percent over 2020 driven by growth in all businesses, up from prior guidance of approximately 37 percent annual growth."
    shared = {"classification":"NUMERIC_ANNUAL_REVENUE", "issuer_cik":2488, "fiscal_year":"2021",
              "metric":"full_year_revenue", "representation":"growth_percent", "currency":"USD",
              "units":"percent", "scope":"consolidated", "base_period":"2020"}
    old = g.bind_guidance(sources["preceding_earnings_document"], {**shared,"lower":37,"upper":37,
                          "document":"q420991.htm","quote":old_quote})
    new = g.bind_guidance(sources["current"], {**shared,"lower":50,"upper":50,
                          "document":"q12021991.htm","quote":new_quote})
    feature = g.revision(old,new,latest_prior_confirmed=True)
    if feature["classification"] != "RAISED":
        raise ValueError("known AMD extraction does not reproduce")
    return {"mode":"HISTORICAL_EXTRACTION_FIXTURE_ONLY", "ticker":"AMD", "prior":old,"current":new,
            "latest_prior_evidence":"The current release explicitly identifies the prior 37% guidance; checked against original prior release.",
            "feature":feature, "investment_returns_computed":False,
            "prospective_observation":False,"broker_fill_inferred":False}


def metadata_check(issuer, policy, freeze):
    if issuer["http_status"] != 200:
        return {"classification":"SOURCE_UNAVAILABLE","reason":"SEC submissions request failed"}
    key=hashlib.sha256(issuer["source_url"].encode()).hexdigest()[:32]
    path=ROOT/"data/sec"/(key+".bin")
    if sha(path) != issuer["source_sha256"]:
        raise ValueError("SEC metadata changed")
    data=json.loads(path.read_text())
    if int(data["cik"]) != issuer["cik"]:
        raise ValueError("SEC identity mismatch")
    recent=data["filings"]["recent"]
    fields=("form","filingDate","accessionNumber","items")
    if any(k not in recent for k in fields) or len({len(recent[k]) for k in fields}) != 1:
        return {"classification":"SOURCE_UNAVAILABLE","reason":"Incomplete SEC recent-filings schema"}
    cutoff=g.moment(freeze["frozen_at_utc"])
    lower=(cutoff-timedelta(days=policy["bootstrap_days"])).date().isoformat()
    selected=[recent["accessionNumber"][i] for i,f in enumerate(recent["form"])
              if f=="8-K" and lower<=recent["filingDate"][i]<=cutoff.date().isoformat()
              and "2.02" in [x.strip() for x in recent["items"][i].split(",")]]
    expected=[f["accession"] for f in issuer["filings"] if f["current_window"]]
    if set(selected)!=set(expected):
        raise ValueError("event inventory does not reproduce from original metadata")
    return {"classification":"NO_CURRENT_EVENT" if not selected else "REVIEW_REQUIRED",
            "issuer_cik":issuer["cik"],"current_accessions":selected,
            "reason":"No Item 2.02 8-K in the fixed window in the returned SEC metadata" if not selected else "Current documents need a source-cited guidance review",
            "latest_reported_filing_date":recent["filingDate"][0] if recent["filingDate"] else None}


def verify_outputs():
    policy,freeze=g.verify_freeze(ROOT)
    inputs=json.loads((ROOT/"IMPLEMENTATION_FREEZE.json").read_text())
    for name,expected in inputs["files"].items():
        if sha(ROOT/name)!=expected:raise ValueError("implementation/input changed: "+name)
    if sha(ROOT.parents[1]/"idxsig/guidance.py")!=inputs["module_sha256"]:
        raise ValueError("guidance module changed after paper freeze")
    if sha(ROOT.parents[1]/"tests/test_guidance_revision.py")!=inputs["tests_sha256"]:
        raise ValueError("guidance tests changed after paper freeze")
    ledger=ROOT/"paper/ledger.jsonl"
    if verify_chain(ledger):raise ValueError("guidance paper chain failed")
    rows=ledger_lines(ledger)
    if len({r["id"] for r in rows})!=len(rows):raise ValueError("duplicate decision IDs")
    decisions=[r for r in rows if r.get("type")=="GUIDANCE_DECISION"]
    if len(decisions)!=len(policy["universe"]):raise ValueError("cohort coverage incomplete")
    result=json.loads((ROOT/"paper/DECISION.json").read_text())
    if result["record_hashes"]!=[r["record_hash"] for r in rows]:raise ValueError("report/ledger mismatch")
    if any(r["real_trade_permission"] is not False or r["filled_exposure_usd"]!="0" for r in decisions):
        raise ValueError("first no-fill cohort has unexpected exposure")
    fixture_result=fixture()
    if g.digest(fixture_result)!=g.digest(json.loads((ROOT/"paper/AMD_FIXTURE.json").read_text())):
        raise ValueError("fixture does not reproduce")
    return {"status":"PASS","checks":["protocol hashes","implementation and evidence hashes","raw SEC inventory read-back",
            "seven issuer decisions","unique IDs","separate ledger hash chain","zero invented fills","original AMD source extraction"],
            "decisions":len(decisions),"strategy_returns_computed":False,"real_orders":0}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    if args.verify:
        # Recheck raw inventory rather than only trusting report claims.
        p,f=g.verify_freeze(ROOT)
        for row in json.loads((ROOT/"data/inventory.json").read_text())["issuers"]:metadata_check(row,p,f)
        print(json.dumps(verify_outputs(),indent=2));return
    if (ROOT/"paper/DECISION.json").exists():
        raise FileExistsError("decision already recorded; use --verify")
    policy,freeze=g.verify_freeze(ROOT)
    inventory=json.loads((ROOT/"data/inventory.json").read_text())
    if {r["cik"] for r in inventory["issuers"]}!={r["cik"] for r in policy["universe"]}:
        raise ValueError("cohort membership changed")
    features=[metadata_check(r,policy,freeze) for r in inventory["issuers"]]
    amd=fixture()
    files=["PROTOCOL.md","protocol.json","FREEZE.json","collect.py","run_first_decision.py","requirements.txt",
           "fixtures/bindings.json","data/inventory.json","data/packages.json","data/broker_reference.json"]
    files += [str(p.relative_to(ROOT)) for p in (ROOT/"data/sec").glob("*.bin")]
    files += [str(p.relative_to(ROOT)) for p in (ROOT/"fixtures").glob("*.gz")]
    module=ROOT.parents[1]/"idxsig/guidance.py"
    test=ROOT.parents[1]/"tests/test_guidance_revision.py"
    impl={"protocol_id":policy["protocol_id"],"frozen_at_utc":datetime.now(timezone.utc).isoformat(),
          "files":{f:sha(ROOT/f) for f in sorted(files)},"module_sha256":sha(module),"tests_sha256":sha(test),
          "outcome_read":False,"note":"Implementation frozen after synthetic checks, before current paper decisions; known historical fixture is declared."}
    write_new(ROOT/"IMPLEMENTATION_FREEZE.json",impl)
    now=datetime.now(timezone.utc).isoformat()
    records=[]
    for row,feature in zip(inventory["issuers"],features):
        if g.moment(row["retrieved_at_utc"])>g.moment(now):raise ValueError("future acquisition")
        decision=g.decide(feature,policy=policy,created_at=now)
        decision.update(id=f'GUIDANCE-v1/{freeze["frozen_at_utc"][:10]}/{row["cik"]}',type="GUIDANCE_DECISION",
                        ticker=row["ticker"],protocol_sha256=freeze["files"]["protocol.json"],
                        information_timing="BOOTSTRAP_EXISTING_INFORMATION",coverage_window_start=inventory["current_window_start"],
                        coverage_window_end=freeze["frozen_at_utc"][:10],
                        source={k:row[k] for k in ["source_url","http_status","retrieved_at_utc","source_sha256"]},
                        policy={"entry":"first regular 09:45 ET after decision readiness; at most second session after source",
                                "exit":"observed 5% stop or twentieth-session close","capital_usd":policy["capital_usd"],
                                "max_notional_fraction":policy["max_notional_fraction"],"risk_fraction":policy["risk_fraction"],
                                "commission_per_side_usd":policy["commission_per_side_usd"],"slippage_per_side_fraction":policy["slippage_per_side_fraction"]},
                        simulated_cash_after_usd=policy["capital_usd"],entry_price=None,stop_price=None,
                        time_exit_at_utc=None,reason_no_prices="No admitted current event; no trade plan activated and no stale quote used as a fill")
        records.append(g.append_once(decision,ROOT/"paper/ledger.jsonl"))
    result={"protocol_id":policy["protocol_id"],"created_at_utc":now,
            "decision":"STAY_IN_CASH" if all(r["action"]=="NO_SIGNAL" for r in records) else "REVIEW_REQUIRED",
            "reason":"No qualifying current event in the frozen seven-issuer operational cohort",
            "cohort":len(records),"current_earnings_events":sum(len(x.get("current_accessions",[])) for x in features),
            "decisions":[{"ticker":r["ticker"],"action":r["action"],"reason":r["reason"],"record_hash":r["record_hash"]} for r in records],
            "paper_positions":0,"simulated_cash_usd":policy["capital_usd"],"real_orders":0,
            "coverage_limit":"Only the seven fixed issuers, as returned by the captured SEC metadata; no claim about the whole market or feed latency.",
            "historical_fixture":"AMD 37% to 50% growth gives +9.489% revenue-forecast level; no stock-return calculation",
            "next_action":"For the next real earnings event in this cohort, retain source bytes, review current and latest prior guidance, then invoke the frozen decision function with actual clocks. No scheduled collector is installed.",
            "record_hashes":[r["record_hash"] for r in records]}
    write_new(ROOT/"paper/AMD_FIXTURE.json",amd)
    write_new(ROOT/"paper/DECISION.json",result)
    verified=verify_outputs()
    write_new(ROOT/"paper/VERIFICATION.json",verified)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
