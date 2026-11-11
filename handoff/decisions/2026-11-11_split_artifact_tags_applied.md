# Decision: tag reverse-split "spikes" and disclose them in the paper book report

Date: 2026-11-11 UTC
Decided by: Jonathan (owner), on reading research/US_SPLIT_ARTIFACTS_v1: "Apply these fixes."
Applied by: Claude, without architect review. Astra can review or revert at any time.
Evidence: `idx-signals/research/US_SPLIT_ARTIFACTS_v1/REPORT.md` (branch `fable/kod-us-split-artifacts-20261110`).

## What was applied (proposals 1 and 2 of that report)

1. A descriptive tag ledger, `idx-signals/paper/split_flags.jsonl` (hash chained, RFC 3161 stamped like the other
   ledgers), written by `idxsig/split_flags.py`. Rule SPLIT_ARTIFACT_V11 is the disclosed addendum v1.1 unchanged:
   a provider split event in the 10 days up to the signal session whose division brings the recorded ratio closer
   to no move and below +30%. It reads the split events already inside the nightly US price pull, so there is no
   new network call.
   - New command: `idxsig split-flag [--manifest M] [--backfill-audit SETS_V11_CSV --basis TEXT] [--commit]`.
   - After `speculate --market US` seals its sets, the same step tags them. The hook cannot block sealing: any
     error is printed and ignored, and the next run tags whatever is still untagged.
   - `paper-verify` now also checks this ledger (hash chain, one tag per set, valid values, set exists).
   - `tools/check_append_only.py` now protects the ledger.
2. `idxsig/paper_book_report.py` appends, only when some planned spike is tagged, a section "Secondary view: sets
   tagged SPLIT_ARTIFACT_V11 excluded" with the four books recomputed. With no tagged spike the report is
   byte-identical to before. The planned look at 300 trades, the bounds and the frozen verdict are unchanged.

## Not applied

Proposal 3 (drop such names inside the scanner) changes the live detector and needs its own decision. Nothing in
the detector, cone, plan, decision, cutoff, account limits or any protocol changed. No earlier ledger line changed.

## Verification

- 23 new tests (`idx-signals/tests/test_split_flags.py`) written by a separate agent from the interface spec alone;
  one test setup was corrected by the implementer because `paper.append` collapses identical records (disclosed
  in the commit). All pass. Lint passes with the pinned ruff.
- Full suite: 1,945 tests; 9 failures and errors, all environment: 6 need the `exchange_calendars` package that
  this cloud container lacks, 3 are pandas date-type differences. None is in a module this change touches.
- Dry run on a temporary ledger with real data: the live rule agreed with the audit's classification on all 132
  sets that have provider data in the retained pull (the other 2 are covered by the audit backfill), tagged
  tonight's SMX (1:2.8 split on 2026-11-09 against a recorded +106%), and found no other new artifact.
- Tampering with a tag line is caught by `paper-verify`.

## Limits

The retained raw pulls only go back to 2026-11-06, so same-night availability of the split event is directly
confirmed for TOPS only; the earlier eight artifacts were found in later pulls. The 134 sets sealed before this
change are tagged from the audit's own file (basis says so), not from a seal-time pull.

## To revert

Remove the `split-flag` parser entry, `_split_flag_hook` and its one call in `idxsig/cli.py`, the `split_flags`
term in `paper-verify`, and the secondary view in `paper_book_report.py`. The ledger file can stay: it is
append-only and nothing else reads it.
