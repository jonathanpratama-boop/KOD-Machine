# Earnings-note workflow: progress checkpoint (non-frozen)

Objective: company + official earnings release (HTML) -> facts with evidence -> workbench bundle -> readable Markdown note; one real event; tests; draft PR. Not a trading strategy.

- Branch `claude/earnings-note-20261022` (stacked on PR #10's head `ca91470`, branch `codex/analyst-evidence-workbench-20261022`). Draft PR base: that branch. Nothing merged.
- Demonstration: NVIDIA Q3 FY2025 release (SEC 0001045810-24-000315, Ex. 99.1 `q3fy25pr.htm`), comparison Q2 FY2025 release (0001045810-24-000262, `q2fy25pr.htm`). Frozen in `examples/earnings_demo/` with hashes and retrieval times in `SOURCES.json` (retrieved 2026-10-22T14:40Z; do not refetch).
- Files: `kod/earnings.py`, `tests/test_earnings.py`, `EARNINGS.md`, `examples/earnings_demo/**`, README paragraph, this file.
- Done: extraction (summary tables, headline, outlook), three separate comparisons, cutoff handling via the workbench, CLI, 40 tests, real note generated and checked against the sources.
- Second round ("do it"): ran the tool on AMD, Apple and Microsoft releases. Found and fixed: AMD columns silently mislabelled (first version assumed the first cell was a row label), Apple share counts read as EPS, dollar sign only on a table's first row, Microsoft periods-down-rows layout unsupported. Added 11 tests, frozen real releases in `examples/earnings_demo/more/`, `regenerate.py`.
- Remaining: none for the first version. Not done by design: PDFs, other table layouts, segment data, consensus sourcing, live-URL path exercised only through unit tests (no network in CI).
- Resume: `git worktree list`; `cd kod-machine && python3 -m unittest tests.test_earnings`; regenerate the example with the command in `EARNINGS.md`.
