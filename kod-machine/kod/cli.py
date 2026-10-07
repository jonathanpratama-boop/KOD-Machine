"""CLI for the KOD lab."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .detectors import evaluate
from .ledger import Ledger, LedgerError
from .score import build_report, render_json, render_markdown

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "var" / "kod.db"
SEED = ROOT / "seeds" / "retrospective_cases.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="kod", description="KOD forensic lab. Research only.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("seed")
    p_open = sub.add_parser("open")
    p_open.add_argument("card")
    p_close = sub.add_parser("close")
    p_close.add_argument("case_id")
    p_close.add_argument("outcome_json")
    sub.add_parser("report")
    sub.add_parser("check-immutable")
    args = parser.parse_args(argv)
    ledger = Ledger(Path(args.db))
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
        elif args.cmd == "close":
            outcome = json.loads(args.outcome_json)
            ledger.close_case(args.case_id, outcome)
            print(f"closed {args.case_id}")
        elif args.cmd == "report":
            report = build_report(ledger)
            out = ROOT / "reports"
            out.mkdir(exist_ok=True)
            (out / "KOD_LAB_STATUS.md").write_text(render_markdown(report), encoding="utf-8")
            (out / "calibration.json").write_text(render_json(report), encoding="utf-8")
            print(render_markdown(report))
        elif args.cmd == "check-immutable":
            ledger.assert_immutable()
            print("append-only triggers held")
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


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
        open_and_evaluate(ledger, card)
        if card.get("outcome"):
            ledger.close_case(card["case_id"], card["outcome"])
        n += 1
    return n


if __name__ == "__main__":
    raise SystemExit(main())
