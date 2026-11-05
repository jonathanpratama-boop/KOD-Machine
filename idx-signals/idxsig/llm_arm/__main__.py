"""Explicit LLM evidence workbench; model invocation and delivery are external."""

import argparse
import json
import sys
from pathlib import Path

from ..runtime.storage import read_json
from .audit import audit, load_jsonl
from .demo import demo
from .workbench import (
    initialize,
    learning_memory,
    prepare,
    record_file,
    recover,
    resolve,
    status,
    watch,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Dedicated LLM cohort directory")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("demo", "memory", "watch", "recover", "proposals"):
        commands.add_parser(name)
    query = commands.add_parser("status")
    query.add_argument("--checkpoint", type=Path)
    init = commands.add_parser("init")
    init.add_argument("--spec", type=Path, required=True)
    init.add_argument("--memory-root", type=Path)
    for name in ("prepare", "record"):
        item = commands.add_parser(name)
        item.add_argument("--set-id", required=True)
        item.add_argument("--input", type=Path, required=True)
    outcomes = commands.add_parser("resolve")
    outcomes.add_argument("--register", type=Path, required=True)
    legacy = commands.add_parser("audit-v1")
    legacy.add_argument("--calls", type=Path, nargs="+", required=True)
    legacy.add_argument("--register", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "audit-v1":
            result = audit(
                [row for path in args.calls for row in load_jsonl(path)], load_jsonl(args.register)
            )
        elif args.root is None:
            parser.error("--root is required for cohort operations")
        elif args.command == "init":
            result = initialize(args.root, read_json(args.spec), memory_root=args.memory_root)
        elif args.command == "prepare":
            result = prepare(args.root, args.set_id, read_json(args.input))
        elif args.command == "record":
            result = record_file(args.root, args.set_id, args.input)
        elif args.command == "resolve":
            result = resolve(args.root, load_jsonl(args.register))
        elif args.command == "status":
            result = status(
                args.root,
                expected_checkpoint=read_json(args.checkpoint) if args.checkpoint else None,
            )
        elif args.command == "proposals":
            report = status(args.root)
            result = {
                "proposals": [
                    {"set_id": c["set_id"], **c["proposal"]}
                    for c in report["cases"]
                    if c["proposal"]
                ],
                "checkpoint": report["checkpoint"],
                "execution": "REQUIRES_SEPARATE_FROZEN_RESEARCH_REQUEST",
                "entry_permission": False,
            }
        else:
            result = {"demo": demo, "memory": learning_memory, "watch": watch, "recover": recover}[
                args.command
            ](args.root)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 2 if args.command == "watch" and result["alerts"] else 0
    except (ValueError, OSError, KeyError, TypeError, ArithmeticError) as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
