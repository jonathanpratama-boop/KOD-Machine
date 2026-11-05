#!/usr/bin/env python3
"""Repository entry point for KOD's explicit operations and analyst workstation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "idx-signals"), str(ROOT / "kod-machine")]


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("runtime", "workstation", "research", "llm"):
        print(
            "Usage: python tools/kod.py runtime --root PATH COMMAND [options]\n"
            "       python tools/kod.py workstation COMMAND [options]\n"
            "       python tools/kod.py research --root PATH COMMAND [options]\n"
            "       python tools/kod.py llm --root PATH COMMAND [options]\n"
            "Use COMMAND --help for arguments. Operations are explicit; no daemon is started."
        )
        return 2
    component = args.pop(0)
    if component == "runtime":
        from idxsig.runtime.__main__ import main as entry
    elif component == "workstation":
        from kod.workstation.cli import main as entry
    elif component == "llm":
        from idxsig.llm_arm.__main__ import main as entry
    else:
        from idxsig.research_workflow.__main__ import main as entry
    return entry(args)


if __name__ == "__main__":
    raise SystemExit(main())
