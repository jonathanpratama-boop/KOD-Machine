#!/usr/bin/env python3
"""Warn when a new study script reads raw data itself instead of through a shared idxsig loader.

Rule (handoff/KOD_FIX_PLAN.md, Fix 3): new studies load data only through shared loaders in
idx-signals/idxsig, so that timestamp units, as-of cutoffs and provenance are handled once per
source rather than once per study. Existing study scripts are frozen records and never flagged.

Scope: Python files ADDED under idx-signals/research/ in the range (git diff --diff-filter=A
--no-renames, so a moved file counts as new), read as committed at HEAD. In those files each call
below is reported, unless the called name was imported from idxsig (the shared-loader route):
  tabular readers  read_csv, read_table, read_parquet, read_pickle, read_feather, read_json,
                   read_excel, read_hdf, read_fwf, read_orc (pandas, polars, pyarrow, ...)
  array readers    np.load, np.loadtxt, np.genfromtxt, np.fromfile
  archives         zipfile.ZipFile, tarfile.TarFile, tarfile.open, unless opened for writing
  downloads        urlopen, urlretrieve, and get/post/head/request/stream on requests or httpx
  file opens       open, io/gzip/bz2/lzma/codecs.open, Path.open/read_text/read_bytes, in a read
                   mode, on a data path: an expression whose source has "data" or "raw" at the
                   start of a word, or a data-file suffix (.csv, .parquet, .pkl, .zip, .gz, .jsonl,
                   see DATA_PATH)

Output: one GitHub ::warning annotation per call (file and line), then a summary line.
Exit status: 0, also when the range cannot be read (that is reported as a warning too); with
--strict, 1 when anything was reported; 2 for invalid arguments.

Not claimed: the check is static and heuristic. A path held in a neutrally named variable, or
built in another module, is not resolved, so a file without warnings is not proof that it reads
only through loaders, and a warning is not proof of a look-ahead defect. Whether a shared loader
exists for every source, and whether it is as-of aware, is outside this check. Standard library
only: CI runs it before installing requirements.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import re
import sys

import ci_push

RESEARCH = "idx-signals/research/"
TITLE = "Shared data rule"
TABULAR_READERS = frozenset(
    {
        "read_csv",
        "read_table",
        "read_parquet",
        "read_pickle",
        "read_feather",
        "read_json",
        "read_excel",
        "read_hdf",
        "read_fwf",
        "read_orc",
    }
)
ARRAY_READERS = frozenset({"load", "loadtxt", "genfromtxt", "fromfile"})
NUMPY = frozenset({"np", "numpy"})
DOWNLOADERS = frozenset({"urlopen", "urlretrieve"})
HTTP_CLIENTS = frozenset({"requests", "httpx"})
HTTP_METHODS = frozenset({"get", "post", "head", "request", "stream"})
FILE_MODULES = frozenset({"io", "gzip", "bz2", "lzma", "codecs"})
DATA_PATH = re.compile(
    r"(?<![a-z])(?:data|raw)"
    r"|\.(?:csv|tsv|parquet|pq|pkl|pickle|feather|arrow|orc|h5|hdf5|xlsx|xls"
    r"|zip|gz|bz2|xz|zst|jsonl|ndjson)\b",
    re.IGNORECASE,
)
WRITE_MODES = frozenset("wax")


@dataclass(frozen=True, order=True)
class Finding:
    line: int
    call: str


def scan(source: bytes, path: str) -> list[Finding]:
    """Direct raw-data reads in one script; raises SyntaxError or ValueError if it cannot parse."""
    tree = ast.parse(source, filename=path)
    loaders = idxsig_names(tree)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _root_name(node.func) not in loaders:
            if _reads_raw_data(node):
                found.add(Finding(node.lineno, _label(node.func)))
    return sorted(found)


def idxsig_names(tree: ast.AST) -> set[str]:
    """Names bound by importing idxsig; calls through them use the shared loaders."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "idxsig":
                    names.add(alias.asname or "idxsig")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] == "idxsig":
                names.update(alias.asname or alias.name for alias in node.names)
    return names


def _reads_raw_data(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        name, receiver = func.id, None
    elif isinstance(func, ast.Attribute):
        name, receiver = func.attr, func.value
    else:
        return False
    module = receiver.id if isinstance(receiver, ast.Name) else None
    if name in TABULAR_READERS or name in DOWNLOADERS:
        return True
    if name in ARRAY_READERS:
        return module in NUMPY
    if name in HTTP_METHODS:
        return module in HTTP_CLIENTS
    if name in ("ZipFile", "TarFile") or (name == "open" and module == "tarfile"):
        return _read_mode(_argument(call, 1, "mode"))
    if name == "open" and (receiver is None or module in FILE_MODULES):
        path = _argument(call, 0, "file", "filename")
        return _read_mode(_argument(call, 1, "mode")) and _is_data_path(path)
    if name == "open":
        return _read_mode(_argument(call, 0, "mode")) and _is_data_path(receiver)
    if name in ("read_text", "read_bytes"):
        return _is_data_path(receiver)
    return False


def _argument(call: ast.Call, index: int, *keywords: str) -> ast.expr | None:
    positional = call.args[: index + 1]
    if len(positional) > index and not any(isinstance(a, ast.Starred) for a in positional):
        return call.args[index]
    return next((k.value for k in call.keywords if k.arg in keywords), None)


def _read_mode(mode: ast.expr | None) -> bool:
    # The default mode reads; a mode computed at run time is treated as a read (warn, never miss).
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return not WRITE_MODES & set(mode.value)
    return True


def _is_data_path(node: ast.expr | None) -> bool:
    return node is not None and DATA_PATH.search(ast.unparse(node)) is not None


def _root_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _label(func: ast.expr) -> str:
    text = ast.unparse(func)
    return text if len(text) <= 60 else text[:57] + "..."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ci_push.add_range_arguments(parser)
    parser.add_argument("--strict", action="store_true", help="exit 1 when anything is reported")
    args = parser.parse_args(argv)
    try:
        commits = ci_push.resolve(args)
        if commits.fallback:
            print(
                ci_push.workflow_command(
                    "notice",
                    f"shared data: {commits.fallback}; reading only the head commit "
                    f"{commits.head[:12]}",
                )
            )
        added = ci_push.changed_paths(
            ci_push.compared_tree(commits), commits.head, added_only=True, under=RESEARCH
        )
        scripts = [path for path in added if path.endswith(".py")]
        warnings, flagged = 0, 0
        for path in scripts:
            reported = report(path, ci_push.blob(commits.head, path))
            warnings += reported
            flagged += reported > 0
    except ci_push.RangeError as exc:
        print(
            ci_push.workflow_command(
                "warning", f"shared data check could not run: {exc}", title=TITLE
            )
        )
        return 1 if args.strict else 0
    print(
        f"shared data: {warnings} warning(s) in {flagged} of {len(scripts)} new study script(s), "
        f"{commits}{'' if args.strict else ' (warning only)'}"
    )
    return 1 if args.strict and warnings else 0


def report(path: str, source: bytes) -> int:
    """Print one annotation per direct raw read in `path`; returns how many were printed."""
    try:
        findings = scan(source, path)
    except (SyntaxError, ValueError) as exc:
        message = f"{path} could not be parsed ({exc}); the shared data rule was not checked"
        print(ci_push.workflow_command("warning", message, file=path, title=TITLE))
        return 1
    for finding in findings:
        message = (
            f"{finding.call}(...) reads raw data directly in a new study script; load it through "
            "a shared idxsig loader (handoff/KOD_FIX_PLAN.md, Fix 3)"
        )
        print(
            ci_push.workflow_command("warning", message, file=path, line=finding.line, title=TITLE)
        )
    return len(findings)


if __name__ == "__main__":
    sys.exit(main())
