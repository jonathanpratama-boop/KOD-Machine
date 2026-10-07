# KOD-Machine

Two research tools. Neither grants entry permission.

| Directory | What it is |
|---|---|
| [`kod-machine/`](kod-machine/README.md) | KOD forensic lab: freezes what was knowable before a move, hashes the call, anchors the hash in git, and refuses to rewrite it after the outcome. Stdlib only. |
| [`idx-signals/`](idx-signals/README.md) | IDX signal test harness: daily price panel for the whole IDX universe with per-file provenance, an execution model with lots, fees and auto-rejection limits, a random-entry baseline, and an append-only results log. |

## Status

- The IDX detector rule has **not** been supplied (the request contained the placeholder
  `[paste your detector rule]`). Its slot is `idx-signals/idxsig/rules/user_rule.py`; the
  harness refuses to run it until the text and code are there. The only run on record is a
  placebo that checks the harness.
- KOD calibration: NOT_STARTED, 0 prospective cases. Doctrine `246deb4a…`.

## Append-only records

Run once per clone so local commits are checked:

```sh
git config core.hooksPath .githooks
```

`tools/check_append_only.py` rejects any commit that edits or deletes a backtest run, a data
manifest, a KOD card, or an earlier line of `RUNS.jsonl` / `opens.jsonl` / `scans.jsonl`.
CI (`.github/workflows/checks.yml`) runs it over the whole history, plus both test suites,
`kod verify` and `idxsig verify-runs`.
