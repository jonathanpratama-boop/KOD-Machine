# KOD-Machine

The integrated paper operations and research workstation are described in
[Operating architecture](docs/OPERATING_SYSTEM.md), with setup and recovery in
[Runtime guide](docs/RUNTIME.md). Start with `python tools/kod.py runtime --root /tmp/kod-demo demo`
after installing `requirements-runtime.txt`. [Timing research](docs/TIMING_RESEARCH.md)
records Hermes' negative findings and the next bounded diagnostic. Synthetic checks do not establish an investment edge.

Two research tools. Neither grants entry permission.

| Directory | What it is |
|---|---|
| [`kod-machine/`](kod-machine/README.md) | KOD forensic lab: freezes what was knowable before a move, hashes the call, anchors the hash in git, and refuses to rewrite it after the outcome. Stdlib only. |
| [`idx-signals/`](idx-signals/README.md) | Signal test harness for IDX, US equities and crypto: daily price panels with per-file provenance and quality tiers, an IDX corporate-action registry, an execution model per market (lots, fees and cost tiers, IDX auto-rejection limits), causal-by-construction rule evaluation, matched and same-session random baselines, an append-only results log, and a prospective paper ledger. |

## Status

- The IDX detector rule has **not** been supplied (the request contained the placeholder
  `[paste your detector rule]`). Its slot is `idx-signals/idxsig/rules/user_rule.py`; the
  harness refuses to run it until the text and code are there. The only runs on record are
  three placebo runs that check the harness (first harness, after the external review's
  fixes, after hardening v2); all are indistinguishable from random entries, as a price-blind
  rule should be.
- Experiment E1 (historical, `idx-signals/research/E1/REPORT.md`): base rates of +30/50/100%
  five-session repricings, the first 100 events with matched controls, 20 pre-event signals,
  and detector D1 (ARA close) validated for detection (9.3x matched random) but not for
  execution (the next-close entry loses). Holdout untouched.
- Experiment E2 (historical, `idx-signals/research/E2/REPORT.md`): the same design on US
  equities (survivor-only) and Binance crypto. Detector G2_RET30 (a +30% day) validated for
  detection in both (5.4x and 4.6x matched random) and failed for execution in both (buying
  the next open loses: US -3.65% vs -0.60%, crypto -1.90% vs +1.42%). Holdout untouched.
- Experiment E3 (historical, `idx-signals/research/E3/REPORT.md`): 36 pre-registered execution
  plans x 3 ARA detectors on IDX discovery 2021-22, 108 harness runs. None admissible: all 108
  lost money in 2022, and the three that beat matched random did so in 2021 alone. No plan
  frozen, no validation run, holdout untouched. The harness now has conditional entries and
  exits (`--entry-rule`, `--exit-rule`) and refuses detector runs that touch the holdout; paper
  policy v4 would carry a validated plan into IDX decisions and is dormant.
- Experiment E4 (historical, `idx-signals/research/E4/REPORT.md` and `v2/REPORT.md`): the fade
  on the short side, crypto. The harness now has a short side with liquidation and a
  redenomination rule. v1: 144 short-side plans, none admissible (two trades in three win; every
  plan lost in 2021 and nearly every plan won in 2022; the worst 1% lose more than the position).
  v2, with a bear-regime condition: 31 of 288 admissible on discovery, and the selected pair
  (70% hit rate, +5.8% per trade on 2020-22) failed its one validation test on 2023 (68% hit
  rate, -1.5% average, three liquidations in 34 trades). No paper policy change; holdout untouched.
- Prospective paper ledger (`idx-signals/paper/`), daily routines in all three markets: IDX
  since session 2026-10-07 (4 candidates: 3 PASS, 1 NOT EXECUTABLE), crypto and US since
  2026-10-07 (see the ledger). Every candidate so far is PASS or NOT EXECUTABLE because no
  executable plan has passed validation. No real orders.
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
CI (`.github/workflows/checks.yml`) runs it over the whole history on every push/PR, plus selected test suites,
`kod verify` (with a read-only `GITHUB_TOKEN`, so GitHub receipts are checked),
`kod receipt-selftest` for the commit being built, `idxsig rules` (source audit) and
`idxsig verify-runs`. See [CI routing and timestamp safety](docs/CI_EFFICIENCY.md) for
PR/default-branch test routing, forecast-only selection and uncancelled integrity checks.

Branch protection and rulesets are not available for private repositories on GitHub Free,
and the API reports this branch as unprotected, so a force-push is not prevented here. That
is why KOD does not rely on git history alone: an open counts only with a GitHub
workflow-run receipt for its exact anchor commit, created by GitHub before the window, and
the RFC 3161 tokens are independent of GitHub altogether.
