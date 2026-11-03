"""Run finite, explicit paper/research operations. No continuous service."""
import argparse
import json
import sys
from pathlib import Path

from .coordinator import run_once, verify, status
from .demo import demo
from .collect import PublicDataUnavailable


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3] / "runtime" / "kod")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("demo", "verify", "status"):
        commands.add_parser(name)
    capture = commands.add_parser("capture", help="Explicitly collect two public snapshots and simulate paper operations")
    capture.add_argument("--initial-cash", default="1000")
    capture.add_argument("--fee-rate", default="0.001")
    capture.add_argument("--slippage", default="0.001")
    capture.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    once = commands.add_parser("once")
    once.add_argument("--snapshot", type=Path, required=True)
    once.add_argument("--profile", type=Path, required=True)
    once.add_argument("--as-of", required=True)
    once.add_argument("--evidence-root", type=Path)
    backup = commands.add_parser("backup")
    backup.add_argument("--output", type=Path, required=True)
    restore = commands.add_parser("restore")
    restore.add_argument("--archive", type=Path, required=True)
    assess = commands.add_parser("assess")
    assess.add_argument("--assessment", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            from .capture import capture
            result = capture(args.root, initial_cash=args.initial_cash, fee_rate=args.fee_rate, slippage=args.slippage, symbols=args.symbols)
        elif args.command == "once":
            result = run_once(args.root, args.snapshot, args.profile, args.as_of, args.evidence_root)
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
        return 0
    except (ValueError, OSError, KeyError, PublicDataUnavailable) as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
