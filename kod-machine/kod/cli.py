"""CLI for the KOD lab."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .anchor import GitAnchor
from .detectors import evaluate
from .ledger import Ledger, LedgerError
from .score import build_report, render_json, render_markdown
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
    p_close = sub.add_parser("close")
    p_close.add_argument("case_id")
    p_close.add_argument("outcome_json")
    p_scan = sub.add_parser("scan", help="log every name a scanner evaluated, flagged or not")
    p_scan.add_argument("scan_file")
    p_scan_close = sub.add_parser("scan-close", help="append outcomes for a logged scan")
    p_scan_close.add_argument("outcomes_file")
    sub.add_parser("report")
    sub.add_parser("verify", help="recompute every hash from the stored rows and check git anchors")
    sub.add_parser("check-immutable")
    args = parser.parse_args(argv)
    anchor = GitAnchor(Path(args.registry), push=args.push, trailer=os.environ.get("KOD_ANCHOR_TRAILER", ""))
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
            digest = open_and_evaluate(ledger, card)
            print(f"{card['case_id']} {digest}")
            _print_receipt(ledger)
        elif args.cmd == "close":
            outcome = json.loads(args.outcome_json)
            ledger.close_case(args.case_id, outcome)
            print(f"closed {args.case_id}")
        elif args.cmd == "scan":
            scan = json.loads(Path(args.scan_file).read_text(encoding="utf-8"))
            digest = ledger.log_scan(scan)
            print(f"{scan['scan_id']} {digest} ({len(scan['entries'])} names)")
            _print_receipt(ledger)
        elif args.cmd == "scan-close":
            payload = json.loads(Path(args.outcomes_file).read_text(encoding="utf-8"))
            n = ledger.close_scan(payload)
            print(f"closed {n} entries of {payload['scan_id']}")
        elif args.cmd == "report":
            report = build_report(ledger)
            out = ROOT / "reports"
            out.mkdir(exist_ok=True)
            (out / "KOD_LAB_STATUS.md").write_text(render_markdown(report), encoding="utf-8")
            (out / "calibration.json").write_text(render_json(report), encoding="utf-8")
            print(render_markdown(report))
        elif args.cmd == "verify":
            result = verify(ledger, anchor)
            print(render_verify(result))
            return 0 if result["ok"] else 1
        elif args.cmd == "check-immutable":
            ledger.assert_immutable()
            print("append-only triggers held")
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def _print_receipt(ledger: Ledger) -> None:
    receipt = ledger.last_receipt
    if receipt is None:
        return
    print(f"anchored in git {receipt.commit} at {receipt.committed_at} ({receipt.registry_path})")
    if receipt.pushed:
        print("anchor pushed")
    elif receipt.push_error:
        print(f"warning: anchor push failed: {receipt.push_error}", file=sys.stderr)
    else:
        print("anchor is local only; push this commit so the timestamp is held outside this machine")


def open_and_evaluate(ledger: Ledger, card: dict) -> str:
    digest = ledger.open_case(card)
    for result in evaluate(card["information_sets"]):
        ledger.record_evaluation(
            card["case_id"],
            result["detector"],
            result["rule_version"],
            result["status"],
            result["features"],
        )
    return digest


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
