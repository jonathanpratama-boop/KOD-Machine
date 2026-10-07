# KOD-Machine

Two research tools. Neither grants entry permission.

| Directory | What it is |
|---|---|
| [`kod-machine/`](kod-machine/README.md) | KOD forensic lab: freezes what was knowable before a move, hashes the call, anchors the hash in git, and refuses to rewrite it after the outcome. Stdlib only. |
| [`idx-signals/`](idx-signals/README.md) | IDX signal test harness: daily price panel for the whole IDX universe with per-file provenance and quality tiers, a corporate-action registry, an execution model with lots, fees and auto-rejection limits, causal-by-construction rule evaluation, matched and same-session random baselines, and an append-only results log. |

## Status

- The IDX detector rule has **not** been supplied (the request contained the placeholder
  `[paste your detector rule]`). Its slot is `idx-signals/idxsig/rules/user_rule.py`; the
  harness refuses to run it until the text and code are there. The only runs on record are
  three placebo runs that check the harness (first harness, after the external review's
  fixes, after hardening v2); all are indistinguishable from random entries, as a price-blind
  rule should be.
- KOD calibration: NOT_STARTED, 0 prospective cases. Doctrine `246deb4a…`. A prospective case
  counts toward calibration only at integrity AUTHORITATIVE: its card hash is in the exact
  anchor commit, GitHub's own workflow-run record for that commit predates the outcome
  window, and its evidence objects verify (see `kod-machine/README.md`).

## Append-only records

Run once per clone so local commits are checked:

```sh
git config core.hooksPath .githooks
```

`tools/check_append_only.py` rejects any commit that edits or deletes a backtest run, a data
manifest, a corporate-action registry, a KOD card, scan, evidence file or timestamp token, a
pinned TSA certificate, or an earlier line of `RUNS.jsonl` / `opens.jsonl` / `scans.jsonl` /
`receipts.jsonl` / `manual.csv`.
CI (`.github/workflows/checks.yml`) runs it over the whole history, plus both test suites,
`kod verify` (with a read-only `GITHUB_TOKEN`, so GitHub receipts are checked),
`kod receipt-selftest` for the commit being built, `idxsig rules` (source audit) and
`idxsig verify-runs`.

Branch protection and rulesets are not available for private repositories on GitHub Free,
and the API reports this branch as unprotected, so a force-push is not prevented here. That
is why KOD does not rely on git history alone: an open counts only with a GitHub
workflow-run receipt for its exact anchor commit, created by GitHub before the window, and
the RFC 3161 tokens are independent of GitHub altogether.
