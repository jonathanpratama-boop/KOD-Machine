"""Render research/MSCI_DELETION_OOT_v1/run/RESULT.json as REPORT.md (presentation only; written before the run).
Reuses MSCI_DELETION_v1's report helpers, unchanged.

    python3 research/MSCI_DELETION_OOT_v1/report.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "v1_report", HERE.parent / "MSCI_DELETION_v1/report.py"
)
v1r = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v1r)


def main() -> int:
    r = json.loads((HERE / "run/RESULT.json").read_text())
    lines = [
        "# MSCI_DELETION_OOT_v1: the frozen MSCI deletion rule on the reviews after the sealed IDX holdout",
        "",
        (f"Ran {r['ran_at']} at commit `{r['commit']}` on the frozen protocol. One run. Simulation only; reviews Feb "
        "2025 .. Aug 2026 on the post-holdout IDX segment (2025-02-24 .. 2026-10-06); the sealed holdout's outcomes "
        "were not computed."),
        "",
        f"## Verdict: {r['verdict']}",
        "",
        "| Gate | Result |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in r["gates"].items()],
        "",
        *v1r.period("Out-of-time reviews (Feb 2025 .. Aug 2026)", r),
        "",
        "## What this does and does not show",
        "",
        "- Out of time for this question, but the segment's prices were used by other KOD studies; not pristine.",
        "- Prices after 2025-02-21 come from Yahoo in the pinned panel; closing-auction fills are modelled.",
        ("- MSCI's treatment of Indonesia is changing (additions frozen since Jan 2026; reclassification proposed, "
        "decision by 30 Jun 2027); a past pattern is not a forecast."),
        "",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:14]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
