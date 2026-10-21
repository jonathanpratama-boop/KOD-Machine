"""Shared constants and helpers of IDX_INSIDER_NEWS_OOT (see PROTOCOL.md)."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "research" / "IDX_INSIDER_NEWS"          # test 23: the scripts and instructions this replication reuses unchanged
FIRST, LAST = "2025-03-03", "2026-09-07"               # posting dates (WIB) of the events; both follow from the panel calendar
START, END = "2025-02-24", "2026-10-06"                # market window: first session after the sealed holdout .. last session of the panel
SEALED_END = "2025-02-21"                              # last session of the sealed IDX holdout (2024-01-02 .. 2025-02-21)
LAST_SESSIONS_BEFORE_END = 22                          # LAST is the date of this many sessions before the last one (a 20-session hold must fit)


def last_posting_date(sessions) -> str:
    """The protocol's rule: the date of the 22nd-last session of the segment, so that any event posted on or before it can complete a
    20-session hold before the panel ends."""
    return str(sessions[len(sessions) - LAST_SESSIONS_BEFORE_END])


def load_old(name: str):
    """Load a committed script of IDX_INSIDER_NEWS (test 23) as a module."""
    if str(OLD) not in sys.path:
        sys.path.insert(0, str(OLD))                       # audit_sample imports make_batches
    spec = importlib.util.spec_from_file_location(f"idxnews_{name}", OLD / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
