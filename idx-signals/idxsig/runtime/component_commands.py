"""Explicit component tools; importing this module never runs an experiment."""

from __future__ import annotations

from pathlib import Path

from .storage import read_json

COMMANDS = frozenset(
    {
        "validate",
        "strategies",
        "strategy-evaluate",
        "strategy-plan",
        "strategy-check",
        "execution-replay",
    }
)


def add_parsers(commands):
    """Keep the runtime entry point readable as optional tools grow."""
    validation = commands.add_parser(
        "validate", help="Replay a retained account in isolation and verify restart consistency"
    )
    validation.add_argument("--output-root", type=Path)
    commands.add_parser("strategies", help="List strategy contracts and their actual authority")
    for name, help_text in (
        ("strategy-evaluate", "Evaluate a registered research rule on supplied observations"),
        ("strategy-plan", "Build a risk-checked intent for a separate simulation profile"),
        ("strategy-check", "Check causal signals and sensitivity to warm-up history"),
        ("execution-replay", "Apply recorded lifecycle events to an isolated simulation executor"),
    ):
        parser = commands.add_parser(name, help=help_text)
        parser.add_argument("--input", type=Path, required=True)
        if name == "strategy-check":
            parser.add_argument("--warmup-lengths", type=int, nargs="+", default=[40, 80])


def run(args):
    """Return a JSON result; caller owns display and process exit status."""
    if args.command == "validate":
        from .validation import validate_recorded_run

        return validate_recorded_run(args.root, output_root=args.output_root)
    if args.command == "strategies":
        from ..components.strategy import registry

        return registry()
    request = read_json(args.input)
    if not isinstance(request, dict):
        raise ValueError("component input must be a JSON object")
    if args.command == "strategy-evaluate":
        from ..components.strategy import evaluate_batch

        return evaluate_batch(request)
    if args.command == "strategy-check":
        from ..components.strategy import evaluate_batch, evaluate_series
        from ..strategy_checks import run_strategy_checks

        # Validate the same request contract as normal evaluation before testing
        # shortened prefixes. Unknown fields and future receipts stay errors.
        evaluated = evaluate_batch(request)
        strategy = evaluated["strategy"]
        result = run_strategy_checks(
            lambda observations: evaluate_series(strategy, observations),
            request["observations"],
            warmup_lengths=args.warmup_lengths,
        )
        return {**result, "strategy": strategy, "input_sha256": evaluated["input_sha256"]}
    if args.command == "strategy-plan":
        from ..components.plans import evaluate_plan

        return evaluate_plan(request)
    if args.command == "execution-replay":
        from ..components.execution import execution_run

        return execution_run(args.root, request)
    raise ValueError("unknown component command")


def exit_status(result):
    """A completed diagnostic may still be inconclusive or fail its checks."""
    if isinstance(result, dict):
        if result.get("status") in {"FAIL", "FAILED", "BLOCKED"} or result.get("ok") is False:
            return 1
        if result.get("status") in {"UNKNOWN", "INCOMPLETE"}:
            return 2
    return 0
