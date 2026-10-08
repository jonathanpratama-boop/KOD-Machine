# Split verification correction — 8 October 2026

Review base: 713d54f. Runtime fixes: 2c71a91 and d97cc1d. This report supersedes the
v1 repair's split-evidence approvals and results for the current verification policy.
Original research artifacts remain unchanged and describe the older filter.

## Fixed behavior

- IDX split timestamps use Asia/Jakarta; US timestamps use America/New_York.
  Paper scoring passes the market explicitly.
- SEC acceptance requires an exact ratio in a definite event statement and a matching
  effective date. A related trading-start statement takes precedence over an evening
  legal date. Time abbreviations remain attached to their dates.
- Proposals, ranges, conditional wording, inverted ratios and unrelated dates fail the
  reproduced regression cases. RATIO_CONFIRMED is diagnostic only, never accepted.
- Evidence includes matched excerpts and the us-actions-v2 verifier version.
- The large-jump coverage check uses the same event-specific evidence rule. A nearby
  undated filing cannot establish a missing split or a date mismatch.
- Rechecks revisit approvals from older verifier versions. New repair panels reject
  v1 schedules and coverage files. Historical runs remain reproducible from their
  archived manifests; they are not retroactively relabelled as v2 verification.
- Prospective scoring is versioned paper-score-v3.

## Archived evidence audit

Rechecked all previously cited filings in the frozen v1 schedule and coverage files:
3,463 unique filing payloads matched the hashes in their archived SEC manifests.
The audit uses exact filing URLs already cited; it does not perform a new EDGAR search.
The old search cache contains multiple query versions, so replaying only the current
query would miss earlier cached searches. Offline search manifests now count cache misses.

Of 1,313 previously accepted records, 239 remain VERIFIED; 1,074 are now unverified.
This is NOT a count of false splits. Unsupported formatting, ambiguous context, undated
ratios and inadequate evidence all fail the conservative rule. See evidence_audit.json
for every status transition and filing hash, and the new schedule for matched excerpts.
Regex matching still has limits; difficult filings need further evidence review.

The 415-row coverage audit retains 7 JUMP_ON_RECORD_SESSION flags, 9 nearby-filing
rows and 399 NO_SPLIT_EVIDENCE rows. No matching evidence does not prove no split occurred.

## Recalculated 2023 validation

The rebuilt panel contains 4,443,730 rows and 4,878 tickers. Its SHA-256 is identical
to the v1 repaired panel: 8d3b7ce4be56d40b375ebac78b45be13910cbea492c29e456a417a6ae000cb4b.
Prices, volumes and unit factors are unchanged. The filter now excludes 891 names,
versus 228 previously: 669 added and 6 released.

Each rerun copies its original R1/R2 configuration exactly: frozen G2_RET30 detector,
2023 window, $5,000 notional, next-open entry, five-session hold, cost tiers, overlap
handling, 200 random draws and seeds. No strategy parameters were tuned.

| Fill model | Previously scored | Now scored | Rule average net return | Matched-random average |
|---|---:|---:|---:|---:|
| A: final-volume capacity | 1,092 | 516 | -2.23% | -0.27% |
| B: decision-time capacity | 880 | 438 | -1.69% | -0.30% |

Both have 683 signals: 796 removed, 11 added and 672 shared with their earlier run.
Every change is explained by the revised exclusions; no unexplained signal changes or
status changes on shared signals. Exact values, run IDs and reconciliation: results.json.
The no-quarantine variants were not rerun because neither their byte-identical input
panel nor their detector/execution path changed.

The rule remains below matched random under both models, on this smaller population.
These results do not validate the excluded names or the whole market. Survivor-only
coverage, assumed costs, daily-bar execution and parser limitations remain.
Runtime: Python 3.12.14, pandas 2.2.3, numpy 2.3.5 (recorded in results.json).

## Prospective ledger and verification

- At the ledger hash recorded in results.json: 4 scans, 18 decisions, 0 outcomes.
  No historical paper outcome needs a revision; future scoring uses paper-score-v3.
- 174 harness tests passed, including new timezone, proposal/range, date association,
  inverted-ratio, evening-date, ratio-only and stale-approval cases (test_output.txt).
- 95 KOD tests passed. Rule causal-source audit and run-hash verification passed.
- The three input archives matched SHA-256. Original input verification reports
  ALL ORIGINAL INPUTS PRESENT AND MATCHING (inputs_verification.json).
- Frozen history is preserved; schedules, manifests, audits and runs are new records.

## Reproduction

Extract the input and SEC archives using the instructions under data/archive.
From idx-signals, in a scratch checkout without the new audit output files:

    python3 research/E2/repair_v2/recheck_archived.py
    python3 research/E2/repair_v2/rerun.py
    python3 -m unittest discover -s tests
    python3 -m idxsig verify-runs

The scripts create audit files exclusively and append run records; they never replace
an earlier audit. Repeated audits require a separate output directory or scratch checkout.
