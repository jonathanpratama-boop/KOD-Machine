"""Run finite, explicit paper/research operations. No continuous service."""

import argparse
import json
import sys
from pathlib import Path

from .coordinator import run_once, verify, status
from .demo import demo
from .collect import PublicDataUnavailable
from . import component_commands


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[3] / "runtime" / "kod"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    component_commands.add_parsers(commands)
    for name in ("demo", "verify", "status"):
        commands.add_parser(name)
    capture = commands.add_parser(
        "capture", help="Explicitly collect two public snapshots and simulate paper operations"
    )
    capture.add_argument("--initial-cash", default="1000")
    capture.add_argument("--fee-rate", default="0.001")
    capture.add_argument("--slippage", default="0.001")
    capture.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    capture.add_argument(
        "--scheduled-at", help="Declared UTC slot; omitted means schedule latency is unknown"
    )
    capture.add_argument(
        "--no-external-timestamp",
        action="store_true",
        help="Explicitly disable batch timestamp requests; availability proof remains unverified",
    )
    once = commands.add_parser("once")
    once.add_argument("--snapshot", type=Path, required=True)
    once.add_argument("--profile", type=Path, required=True)
    once.add_argument("--as-of", required=True)
    once.add_argument("--evidence-root", type=Path)
    once.add_argument("--scheduled-at")
    timing = commands.add_parser(
        "timing-status", help="Read verified timing observations without collection"
    )
    timing.add_argument("--as-of")
    intraday = commands.add_parser(
        "timing-capture", help="One bounded public intraday observation; no signal or order"
    )
    intraday.add_argument("--scheduled-at", required=True)
    intraday.add_argument("--symbols", nargs="+", required=True)
    intraday.add_argument("--interval", choices=("1m", "5m", "15m"), default="1m")
    intraday.add_argument("--bars", type=int, default=60)
    context = commands.add_parser(
        "timing-context", help="Retain prepared catalysts and shadow quote assessments"
    )
    context.add_argument("--input", type=Path, required=True)
    context.add_argument("--as-of", required=True)
    missed = commands.add_parser(
        "timing-missed", help="Record a missed scheduled observation explicitly"
    )
    missed.add_argument("--scheduled-at", required=True)
    missed.add_argument("--symbols", nargs="+", required=True)
    missed.add_argument("--reason", required=True)
    commands.add_parser(
        "timing-demo", help="Offline synthetic end-to-end timing and context example"
    )
    backup = commands.add_parser("backup")
    backup.add_argument("--output", type=Path, required=True)
    restore = commands.add_parser("restore")
    restore.add_argument("--archive", type=Path, required=True)
    assess = commands.add_parser("assess")
    assess.add_argument("--assessment", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in component_commands.COMMANDS:
            result = component_commands.run(args)
        elif args.command == "capture":
            from .capture import capture

            result = capture(
                args.root,
                initial_cash=args.initial_cash,
                fee_rate=args.fee_rate,
                slippage=args.slippage,
                symbols=args.symbols,
                scheduled_at=args.scheduled_at,
                timestamp_decisions=not args.no_external_timestamp,
            )
        elif args.command == "once":
            result = run_once(
                args.root,
                args.snapshot,
                args.profile,
                args.as_of,
                args.evidence_root,
                scheduled_at=args.scheduled_at,
            )
        elif args.command == "timing-status":
            from .timing import timing_status

            result = timing_status(args.root, as_of=args.as_of)
        elif args.command == "timing-capture":
            from .timing import capture_intraday

            result = capture_intraday(
                args.root,
                scheduled_at=args.scheduled_at,
                symbols=args.symbols,
                interval=args.interval,
                bars=args.bars,
            )
        elif args.command == "timing-context":
            from .timing import retain_context
            from .storage import read_json

            result = retain_context(args.root, read_json(args.input), as_of=args.as_of)
        elif args.command == "timing-missed":
            from .timing import record_missed

            result = record_missed(
                args.root, scheduled_at=args.scheduled_at, members=args.symbols, reason=args.reason
            )
        elif args.command == "timing-demo":
            from .timing_demo import timing_demo

            result = timing_demo(args.root)
        elif args.command == "demo":
            result = demo(args.root)
        elif args.command == "backup":
            from .backup import backup

            result = backup(args.root, args.output)
        elif args.command == "restore":
            from .backup import restore

            result = restore(args.archive, args.root)
        elif args.command == "assess":
            from .candidates import record_assessment
            from .storage import read_json

            result = record_assessment(args.root, read_json(args.assessment))
        else:
            result = (verify if args.command == "verify" else status)(args.root)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return component_commands.exit_status(result)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        ArithmeticError,
        PublicDataUnavailable,
    ) as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
