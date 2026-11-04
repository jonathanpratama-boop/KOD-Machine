"""Run finite, development-only experiments from strict human/AI proposal JSON."""

import argparse
import json
import sys
from pathlib import Path

from ..runtime.storage import read_json
from .demo import demo
from .worker import run_batch, status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, required=True, help="Dedicated research cohort directory"
    )
    parser.add_argument(
        "--details", action="store_true", help="Include retained per-opportunity results"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="Evaluate invented prices with a bounded synthetic protocol")
    commands.add_parser("status", help="Verify and read retained results without running proposals")
    run = commands.add_parser(
        "run", help="Evaluate allowlisted templates; no generated code or live orders"
    )
    run.add_argument("--protocol", type=Path, required=True)
    run.add_argument("--dataset", type=Path, required=True)
    run.add_argument(
        "--proposals", type=Path, required=True, help="JSON list of strict proposal objects"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = demo(args.root)
        elif args.command == "status":
            result = status(args.root)
        else:
            result = run_batch(
                args.root,
                read_json(args.protocol),
                read_json(args.dataset),
                read_json(args.proposals),
            )
        if not args.details and "results" in result:
            result = dict(
                result,
                results=[
                    {
                        key: value
                        for key, value in row.items()
                        if key not in {"evaluation", "strategy_checks"}
                    }
                    for row in result["results"]
                ],
            )
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, ArithmeticError) as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
