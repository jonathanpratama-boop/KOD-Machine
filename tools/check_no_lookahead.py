#!/usr/bin/env python3
"""Run KOD's look-ahead check on a study and print one JSON verdict.

compare  Two decision CSV files written by a study: one from the full data, one from the
         same study on data cut at --cutoff. Cells are compared as the text written.
module   A Python file defining decide(data) -> DataFrame, and its input as CSV: runs the
         truncation and scramble checks of idxsig.lookahead at every --cutoff.

Exit status: 0 PASS, 1 LEAK, 2 the check could not run (a JSON ERROR verdict names the
reason; command-line usage errors are reported by argparse). A study that raises, or
calls sys.exit while it is imported or run, is an ERROR, never a PASS. A PASS does not
show that the input data was available at its stated time; see docs/LOOKAHEAD_CHECK.md.
Paper research only: nothing is fetched, ordered or written, but module mode executes
the study file it is given.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import traceback

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXIT_STATUS = {"PASS": 0, "LEAK": 1, "ERROR": 2}
BARE_NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)")


class UsageError(ValueError):
    """The command line names something the check cannot use."""


def read_csv(path: Path, **options) -> pd.DataFrame:
    if not path.name.endswith((".csv", ".csv.gz")):
        raise UsageError(f"{path} is not a .csv or .csv.gz file")
    if not path.is_file():
        raise UsageError(f"{path} does not exist")
    return pd.read_csv(path, **options)


@contextlib.contextmanager
def as_script(study: Path):
    """While the study runs, sys.argv holds only its path and its prints go to stderr.

    Module-level code that reads sys.argv then sees no arguments rather than this tool's
    own, and stdout carries nothing but the JSON verdict. Output written straight to file
    descriptor 1 (a subprocess, C code) bypasses sys.stdout and is not redirected.
    """
    argv = sys.argv
    sys.argv = [str(study)]
    try:
        with contextlib.redirect_stdout(sys.stderr):
            yield
    finally:
        sys.argv = argv


def load_decide(path: Path):
    """Execute the study file as a module and return its ``decide`` function."""
    if path.suffix != ".py" or not path.is_file():
        raise UsageError(f"study module {path} is not an existing .py file")
    name = "kod_lookahead_study_" + hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # Dataclasses and pickling resolve classes through sys.modules.
    spec.loader.exec_module(module)
    decide = getattr(module, "decide", None)
    if not callable(decide):
        raise UsageError(f"study module {path} defines no callable decide(data)")
    return decide


def parse_lag(text: str) -> tuple[str, pd.Timedelta]:
    """COLUMN=DURATION; a bare number is refused because pandas reads it as nanoseconds."""
    column, separator, duration = text.rpartition("=")
    if not separator or not column or BARE_NUMBER.fullmatch(duration.strip()):
        raise UsageError(
            f"--lag {text!r} must be COLUMN=DURATION with a unit, such as fwd3=3D or fwd3=72h"
        )
    try:
        return column, pd.Timedelta(duration)
    except ValueError as exc:
        raise UsageError(f"--lag {text!r} has an unreadable duration") from exc


def run_compare(args: argparse.Namespace, lookahead) -> list:
    """Only an empty cell is missing; text such as NA or nan is compared as written."""
    reference, candidate = (
        read_csv(Path(path), dtype=str, keep_default_na=False, na_values=[""])
        for path in (args.reference, args.candidate)
    )
    report = lookahead.compare_decisions(
        reference,
        candidate,
        time_column=args.time_column,
        key_columns=args.key_columns,
        cutoff=args.cutoff,
        assume_utc=args.assume_utc,
    )
    return [report]


def run_module(args: argparse.Namespace, lookahead) -> list:
    scramble = {
        "columns": args.scramble_columns,
        "seed": args.seed,
        "missing_share": args.missing_share,
    }
    scramble = {name: value for name, value in scramble.items() if value is not None}
    if scramble and args.check == "truncation":
        raise UsageError("--scramble-columns, --seed and --missing-share apply only to scramble")
    lags = dict(parse_lag(text) for text in args.lag)
    if len(lags) != len(args.lag):
        raise UsageError("each --lag column may be given once")
    data = read_csv(Path(args.data))
    common = dict(
        data_time_column=args.data_time_column,
        time_column=args.time_column,
        key_columns=args.key_columns,
        cutoffs=args.cutoff,
        value_lags=lags,
        assume_utc=args.assume_utc,
    )
    study = Path(args.study)
    reports = []
    with as_script(study):
        decide = load_decide(study)
        if args.check in ("truncation", "both"):
            reports.append(lookahead.truncation_check(decide, data, **common))
        if args.check in ("scramble", "both"):
            reports.append(lookahead.scramble_check(decide, data, **common, **scramble))
    return reports


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    modes = root.add_subparsers(dest="mode", required=True)
    compare = modes.add_parser("compare", help="compare two decision CSV files up to a cutoff")
    compare.add_argument("reference", help="decisions the study wrote from the full data")
    compare.add_argument("candidate", help="decisions the study wrote from data cut at --cutoff")
    compare.add_argument("--cutoff", required=True, help="ISO 8601 time with a UTC offset")
    module = modes.add_parser("module", help="run a study's decide(data) under both checks")
    module.add_argument("study", help="Python file defining decide(data) -> DataFrame")
    module.add_argument("data", help="study input as .csv or .csv.gz, read with pandas defaults")
    module.add_argument("--data-time-column", required=True, help="time column of the input")
    module.add_argument("--cutoff", nargs="+", required=True, help="ISO 8601 times with offsets")
    module.add_argument("--check", choices=("truncation", "scramble", "both"), default="both")
    module.add_argument(
        "--lag",
        action="append",
        default=[],
        metavar="COLUMN=DURATION",
        help="column first known DURATION after its row time, e.g. fwd3=3D (repeatable)",
    )
    module.add_argument(
        "--scramble-columns", nargs="+", help="default: numpy and pandas nullable numbers, bools"
    )
    module.add_argument("--seed", type=int, help="scramble noise seed (default 0)")
    module.add_argument(
        "--missing-share", type=float, help="share of noise set missing where a column can hold it"
    )
    for mode in (compare, module):
        mode.add_argument("--time-column", required=True, help="decision-time column")
        mode.add_argument("--key-columns", nargs="+", required=True, help="one decision per key")
        mode.add_argument("--assume-utc", action="store_true", help="read offset-less times as UTC")
    return root


def error_verdict(head: dict, error_type: str, error: str) -> str:
    """One JSON ERROR verdict; every field is text, so it always encodes."""
    return json.dumps(
        {**head, "verdict": "ERROR", "error_type": error_type, "error": error}, indent=2
    )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    library = str(ROOT / "idx-signals")
    if library not in sys.path:
        sys.path.insert(0, library)  # The study file may import idxsig as well.
    from idxsig import lookahead

    head = {"version": lookahead.VERSION, "mode": args.mode}
    try:  # The verdict is written inside the try: a failure to write it is an ERROR too.
        reports = (run_compare if args.mode == "compare" else run_module)(args, lookahead)
        verdict = "LEAK" if any(report.verdict == "LEAK" for report in reports) else "PASS"
        checks = [report.to_dict() for report in reports]
        text = json.dumps({**head, "verdict": verdict, "checks": checks}, indent=2)
    except (UsageError, lookahead.LookaheadCheckError) as exc:
        verdict, text = "ERROR", error_verdict(head, type(exc).__name__, str(exc))
    except SystemExit as exc:  # sys.exit at import or in decide(); its code 0 would read as PASS
        traceback.print_exc(file=sys.stderr)
        message = (
            f"the study raised SystemExit with code {exc.code!r}; a study file must define "
            "decide(data) and return its decisions, not exit"
        )
        verdict, text = "ERROR", error_verdict(head, "SystemExit", message)
    except Exception as exc:  # The study's own failure is still an explicit, nonzero verdict.
        traceback.print_exc(file=sys.stderr)
        verdict, text = "ERROR", error_verdict(head, type(exc).__name__, str(exc))
    print(text)
    return EXIT_STATUS[verdict]


if __name__ == "__main__":
    raise SystemExit(main())
