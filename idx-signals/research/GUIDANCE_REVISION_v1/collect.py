"""Bounded SEC acquisition using the existing KOD SecClient; no prices or outcomes."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--contact-config", type=Path, required=True)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    freeze = json.loads((root / "FREEZE.json").read_text())
    for name, digest in freeze["files"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("frozen protocol changed: " + name)
    policy = json.loads((root / "protocol.json").read_text())
    sys.path.insert(0, str(args.repo / "idx-signals"))
    from idxsig.us_actions import SecClient
    contact = json.loads(args.contact_config.read_text())["sec_user_agent"]
    raw = root / "data" / "sec"
    client = SecClient(contact, raw)
    cutoff = datetime.fromisoformat(freeze["frozen_at_utc"])
    lower = (cutoff - timedelta(days=policy["bootstrap_days"])).date().isoformat()
    prior_lower = (cutoff - timedelta(days=policy["prior_days"])).date().isoformat()
    inventory = []
    for issuer in policy["universe"]:
        url = f'https://data.sec.gov/submissions/CIK{issuer["cik"]:010d}.json'
        started = datetime.now(timezone.utc).isoformat()
        status, body = client.get(url)
        completed = datetime.now(timezone.utc).isoformat()
        item = {**issuer, "source_url": url, "http_status": status,
                "request_started_at_utc": started, "retrieved_at_utc": completed,
                "source_sha256": hashlib.sha256(body).hexdigest(), "filings": []}
        if status == 200:
            data = json.loads(body)
            if int(data["cik"]) != issuer["cik"]:
                raise ValueError("CIK mismatch")
            recent = data["filings"]["recent"]
            for i, form in enumerate(recent["form"]):
                day = recent["filingDate"][i]
                if form != "8-K" or not prior_lower <= day <= cutoff.date().isoformat():
                    continue
                items = recent.get("items", [""] * len(recent["form"]))[i]
                if "2.02" not in [item.strip() for item in items.split(",")]:
                    continue
                item["filings"].append({"accession": recent["accessionNumber"][i],
                    "filing_date": day, "items": items,
                    "primary_document": recent["primaryDocument"][i],
                    "current_window": day >= lower})
            item["filings"].sort(key=lambda x: (x["filing_date"], x["accession"]))
        inventory.append(item)
        print(issuer["ticker"], status, len(item["filings"]), "earnings filings;",
              sum(f["current_window"] for f in item["filings"]), "in current window", flush=True)
    metadata = {"cutoff_utc": cutoff.isoformat(), "current_window_start": lower,
                "issuers": inventory, "strategy_returns_computed": False}
    meta_path = root / "data" / "inventory.json"
    if meta_path.exists():
        previous = json.loads(meta_path.read_text())
        if previous != metadata:
            # Retrieval time changes even on a cache hit; preserve original evidence.
            inventory = previous["issuers"]
            metadata = previous
    else:
        meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
    if args.metadata_only:
        return
    fetched = []
    for issuer in inventory:
        current = [f for f in issuer["filings"] if f["current_window"]]
        if not current:
            continue
        first = min(f["filing_date"] for f in current)
        prior = [f for f in issuer["filings"] if f["filing_date"] < first]
        chosen = prior[-policy["prior_package_cap"]:] + current
        for filing in chosen:
            if len(fetched) >= policy["max_draft_documents_per_run"]:
                raise ValueError("document cap reached; preserve inventory")
            cik, acc = issuer["cik"], filing["accession"]
            url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace("-", "")}/{acc}.txt'
            started = datetime.now(timezone.utc).isoformat()
            status, body = client.get(url)
            completed = datetime.now(timezone.utc).isoformat()
            match = re.search(rb"<ACCEPTANCE-DATETIME>\s*(\d{14})", body)
            key = hashlib.sha256(url.encode()).hexdigest()[:32]
            row = {"ticker": issuer["ticker"], "cik": cik, **filing,
                   "url": url, "http_status": status, "sha256": hashlib.sha256(body).hexdigest(),
                   "raw_path": f"data/sec/{key}.bin", "request_started_at_utc": started,
                   "retrieved_at_utc": completed,
                   "acceptance_header": match[1].decode() if match else None}
            fetched.append(row)
            print("package", issuer["ticker"], filing["filing_date"], status,
                  "current" if filing["current_window"] else "prior", flush=True)
    path = root / "data" / "packages.json"
    if path.exists():
        raise FileExistsError("packages already saved; use existing acquisition")
    path.write_text(json.dumps(fetched, indent=2) + "\n")


if __name__ == "__main__":
    main()
