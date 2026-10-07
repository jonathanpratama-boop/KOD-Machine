"""CLI for the KOD lab."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .anchor import GitAnchor
from .ledger import Ledger, LedgerError
from .remote import GitHubActionsClient, RemoteUnavailable, earliest_exact
from .score import build_report, render_json, render_markdown
from .timestamp import RFC3161Timestamper
from .verify import render as render_verify
from .verify import verify

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "var" / "kod.db"
DEFAULT_REGISTRY = ROOT / "registry"
SEED = ROOT / "seeds" / "retrospective_cases.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="kod", description="KOD forensic lab. Research only.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY),
                        help="git-tracked directory that receives each open's hash")
    parser.add_argument("--push", action="store_true",
                        help="push each anchor commit to origin as soon as it is made")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("seed")
    p_open = sub.add_parser("open")
    p_open.add_argument("card")
    p_open.add_argument("--no-push", action="store_true",
                        help="do not push a prospective anchor now (it then needs a push of exactly this commit "
                             "before the window opens to become AUTHORITATIVE)")
    p_close = sub.add_parser("close")
    p_close.add_argument("case_id")
    p_close.add_argument("outcome_json")
    p_scan = sub.add_parser("scan", help="log every name a scanner evaluated, flagged or not")
    p_scan.add_argument("scan_file")
    p_scan_close = sub.add_parser("scan-close", help="append outcomes for a logged scan")
    p_scan_close.add_argument("outcomes_file")
    sub.add_parser("report")
    p_ev = sub.add_parser("evidence", help="record a KOD-EVIDENCE-v2 object from a JSON declaration; prints its id")
    p_ev.add_argument("declaration", help="JSON file with the evidence fields (see README)")
    p_ev.add_argument("--file", help="the document's bytes, when available and permissible to keep")
    p_rc = sub.add_parser("receipt", help="fetch GitHub receipts for strict anchors that have none recorded")
    p_rc.add_argument("action", choices=["fetch"])
    p_st = sub.add_parser("receipt-selftest", help="CI: confirm GitHub reports a push run for a commit")
    p_st.add_argument("--sha", required=True)
    p_st.add_argument("--run-id")
    sub.add_parser("verify", help="recompute every hash; check git anchors, timestamps and GitHub receipts")
    sub.add_parser("check-immutable")
    args = parser.parse_args(argv)
    timestamper = RFC3161Timestamper()
    anchor = GitAnchor(Path(args.registry), push=args.push, trailer=os.environ.get("KOD_ANCHOR_TRAILER", ""),
                       timestamper=timestamper)
    client = GitHubActionsClient(repo_dir=ROOT)
    if args.cmd == "receipt-selftest":
        return receipt_selftest(client, args.sha, args.run_id)
    ledger = Ledger(Path(args.db), anchor=anchor)
    try:
        if args.cmd == "init":
            print(f"ledger {args.db}")
            print(f"doctrine {ledger.doctrine_sha}")
        elif args.cmd == "seed":
            n = load_seed(ledger, SEED)
            print(f"seeded {n} cases")
        elif args.cmd == "open":
            card = json.loads(Path(args.card).read_text(encoding="utf-8"))
            if card.get("call_type") == "PROSPECTIVE" and not args.no_push:
                anchor.push = True  # the GitHub receipt needs this exact commit pushed now
            digest = open_and_evaluate(ledger, card)
            print(f"{card['case_id']} {digest}")
            _print_receipt(ledger)
        elif args.cmd == "close":
            outcome = json.loads(args.outcome_json)
            ledger.close_case(args.case_id, outcome)
            print(f"closed {args.case_id}")
        elif args.cmd == "scan":
            scan = json.loads(Path(args.scan_file).read_text(encoding="utf-8"))
            anchor.push = True
            digest = ledger.log_scan(scan)
            print(f"{scan['scan_id']} {digest} ({len(scan['entries'])} names)")
            _print_receipt(ledger)
        elif args.cmd == "scan-close":
            payload = json.loads(Path(args.outcomes_file).read_text(encoding="utf-8"))
            n = ledger.close_scan(payload)
            print(f"closed {n} entries of {payload['scan_id']}")
        elif args.cmd == "report":
            report = build_report(ledger, anchor, client)
            out = ROOT / "reports"
            out.mkdir(exist_ok=True)
            (out / "KOD_LAB_STATUS.md").write_text(render_markdown(report), encoding="utf-8")
            (out / "calibration.json").write_text(render_json(report), encoding="utf-8")
            print(render_markdown(report))
        elif args.cmd == "evidence":
            meta = json.loads(Path(args.declaration).read_text(encoding="utf-8"))
            print(ledger.add_evidence(meta, Path(args.file) if args.file else None))
        elif args.cmd == "receipt":
            return fetch_receipts(ledger, client)
        elif args.cmd == "verify":
            result = verify(ledger, anchor, timestamper, client)
            print(render_verify(result))
            return 0 if result["ok"] else 1
        elif args.cmd == "check-immutable":
            ledger.assert_immutable()
            print("append-only triggers held")
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def fetch_receipts(ledger: Ledger, client: GitHubActionsClient) -> int:
    if not client.available:
        print(f"REMOTE_TIMESTAMP_UNVERIFIED: {client.why_unavailable}", file=sys.stderr)
        return 2
    strict = [("CASE", r["case_id"]) for r in ledger.rows(
        "SELECT case_id FROM cases WHERE card_hash_version = 'KOD-CARD-v3' AND integrity_level = 'STRICT-v3'")]
    strict += [("SCAN", r["scan_id"]) for r in ledger.rows(
        "SELECT scan_id FROM scan_runs WHERE scan_hash_version = 'KOD-SCAN-v3'")]
    for kind, record_id in strict:
        if ledger.receipts_for(kind, record_id):
            continue
        commit = ledger.rows("SELECT git_commit FROM anchors WHERE kind = ? AND record_id = ?", (kind, record_id))
        if not commit:
            print(f"{kind.lower()} {record_id}: no anchor")
            continue
        try:
            run = earliest_exact(client.runs_for_commit(commit[0]["git_commit"]), commit[0]["git_commit"])
        except RemoteUnavailable as exc:
            print(f"{kind.lower()} {record_id}: {exc}")
            continue
        if run is None:
            print(f"{kind.lower()} {record_id}: GitHub has no push run for exactly {commit[0]['git_commit'][:12]}")
            continue
        ledger.record_receipt(kind, record_id, run, client.repository)
        print(f"{kind.lower()} {record_id}: run {run.run_id} created {run.created_at.isoformat()} ({run.html_url})")
    return 0


def receipt_selftest(client: GitHubActionsClient, sha: str, run_id: str | None) -> int:
    """Exercise the real GitHub path: the run that is executing this check must be found for
    its own commit, with GitHub's created_at. Used in CI, where GITHUB_TOKEN is present."""
    if not client.available:
        print(f"REMOTE_TIMESTAMP_UNVERIFIED: {client.why_unavailable}", file=sys.stderr)
        return 2
    try:
        runs = client.runs_for_commit(sha)
    except RemoteUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    run = earliest_exact(runs, sha)
    if run is None or (run_id and run_id not in {r.run_id for r in runs}):
        print(f"error: GitHub reports no push run for {sha} (run {run_id})", file=sys.stderr)
        return 1
    print(f"receipt for {sha}: earliest push run {run.run_id} created {run.created_at.isoformat()} by GitHub "
          f"({len(runs)} runs for this commit)")
    return 0


def _print_receipt(ledger: Ledger) -> None:
    receipt = ledger.last_receipt
    if receipt is None:
        return
    print(f"anchored in git {receipt.commit} ({receipt.registry_path})")
    for stamp in receipt.timestamps:
        print(f"externally timestamped by {stamp['authority']} at {stamp['time']}")
    for error in receipt.timestamp_errors:
        print(f"warning: timestamp authority failed: {error}", file=sys.stderr)
    if receipt.pushed:
        print("anchor pushed; run `kod receipt fetch` (with GITHUB_TOKEN) to record GitHub's receipt")
    elif receipt.push_error:
        print(f"warning: anchor push failed: {receipt.push_error}; until exactly this commit is pushed the case "
              f"is REMOTE_TIMESTAMP_UNVERIFIED", file=sys.stderr)
    else:
        print("anchor is local only; push exactly this commit before the window opens or the case is not authoritative")


def open_and_evaluate(ledger: Ledger, card: dict) -> str:
    """Open a card. Detector evaluations are computed and frozen inside open_case."""
    return ledger.open_case(card)


def load_seed(ledger: Ledger, path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for card in payload["cases"]:
        exists = ledger.rows("SELECT case_id FROM cases WHERE case_id = ?", (card["case_id"],))
        if exists:
            continue
        digest = open_and_evaluate(ledger, card)
        if card.get("outcome"):
            ledger.close_case(card["case_id"], {**card["outcome"], "card_sha": digest})
        n += 1
    return n


if __name__ == "__main__":
    raise SystemExit(main())
