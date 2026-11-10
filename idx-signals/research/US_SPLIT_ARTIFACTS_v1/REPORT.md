# US_SPLIT_ARTIFACTS_v1: result (2026-11-10)

**Verdict.** 9 of the 134 sealed US Speculation Register sets (2026-10-27 to 2026-11-09) recorded a reverse split as
a +30% day. Split-adjusted, their signal-day moves were between -21% and +9%: none was a spike. The frozen v1 rule
found 3 and closed the question as isolated; a premise of that rule proved false, and the disclosed addendum (v1.1)
finds 9. No outcome was read at any point.

## What was run
| Step | Commit / file | Result |
|---|---|---|
| Rule frozen before the run | `RULE.md` sha256 ae2af4c9…, commit 7fbd1bb4, RFC 3161 FreeTSA and Sectigo 2026-11-10T00:41:47Z | verified tokens |
| Independent tests (separate agent, from RULE.md only) | `test_classify.py` | 23 of 23 pass |
| v1 classification | `audit.py` → `results/sets.csv`, `results/summary.json` (run 00:46:12Z) | 0 confirmed, 3 provider-only, 6 split-real-move, 1 unexplained, 3 unknown, 121 clean → stop rule CLOSED_AS_ISOLATED |
| Addendum, written after v1 (disclosed) | `ADDENDUM_1.md`, `secondary_v11.py` → `results/sets_v11.csv` | 9 ARTIFACT_V11, 2 INDETERMINATE, 123 not flagged |

Inputs: `kod-main` at 239010bac (speculations, ledger, paper book, paper account, learner v2.4, catalysts) and the
LLM_ARM calls at ec335c553. All 21 input files byte-identical before and after (sha256 check).

## The nine (split-adjusted signal-day move; SEC tier of the split)
| Session | Ticker | Recorded | Split | Adjusted | SEC |
|---|---|---:|---|---:|---|
| 2026-10-28 | ENLV | +1,409% | 1:16 | -5.7% | ratio stated |
| 2026-10-28 | PARA | +691% | 1:10 | -20.9% | ratio stated |
| 2026-10-28 | SCAG | +1,235% | 1:15 | -11.0% | mention only |
| 2026-10-30 | ATYR | +3,884% | 1:40 | -0.4% | not searched (event outside v1 window) |
| 2026-10-30 | MASK | +253% | 1:4 | -11.7% | mention only |
| 2026-10-30 | OMEX | +2,000% | 1:25 | -16.0% | VERIFIED |
| 2026-10-30 | WHLR | +553% | 1:6 | +8.8% | ratio stated |
| 2026-11-05 | XXII | +4,495% | 1:58 | -20.8% | mention only |
| 2026-11-09 | TOPS | +884% | 1:10 | -1.6% | VERIFIED |

INDETERMINATE (huge move, no provider split record): VCIG 2026-11-02 (+4,728%), OMH 2026-11-04 (+433%).

## Where they sit (record types only)
- Ledger: 9 decisions, 7 scored outcomes. Speculation Register: 7 BASE5 and 5 NEXT1 resolutions (of 39 and 83).
- Paper book: ATYR, MASK, OMEX and WHLR are 4 of its 11 closed trades, all DONT_BUY, i.e. 4 of the 9 closed trades of
  the AVOIDED book that the DONT_BUY verdict compares. XXII is a BUY_OK plan; TOPS a DONT_BUY plan.
- LEARNER v2.4: 6 forecasts. Catalyst register: 9 dilution tags. Paper account: 2 declines (XXII). LLM_ARM: 2 calls
  (both already flagged the set as a split artifact in their reasons).

## What the run rejected
- The 11 UNRESOLVABLE register resolutions are NOT explained by later splits: only SMX has one (1:2.8 on 11-09).
  Their "signal close does not reconcile" failures need a different explanation.

## Cause (engineering)
The live US scan uses the provider's pull of that night. Around a reverse split the provider often has no close for
the split session(s) and leaves the last earlier close in pre-split units, so `close / previous` is the split ratio.
Volume ratio does not catch it: 8 of the 9 had volume below normal.

## Proposals for the architect (not applied)
1. A descriptive tag `SPLIT_ARTIFACT_V11` on each new US set, computed at sealing time from the provider's split
   events by the v1.1 test; it changes no detector, cone, plan or decision. Tests by a different agent.
2. A pre-declared disclosure line at the paper book's 300-trade look: each verdict also shown with tagged sets
   excluded, labelled secondary. The frozen primary verdict is unchanged.
3. Optionally, the scanner itself: drop a candidate whose provider split events in the last 10 days explain the move.
   That changes the live detector and needs its own decision.

## Limits
- v1.1 was written after the v1 classes were seen (not outcomes). Its rule is simple and its threshold is the
  detector's own, but it is not a pre-registered test.
- SEC tiers come from the strict us-actions-v2 verifier; "mention only" is not proof of the ratio.
- The provider's split records can themselves be wrong or missing (VCIG, OMH).
- Raw provider and SEC responses are kept in session scratch, not committed (Yahoo terms; public repository); their
  hashes are in `results/evidence_manifest.json`.

## Reproduce
```
cd idx-signals/research/US_SPLIT_ARTIFACTS_v1
python3 -m unittest test_classify
KOD_SEC_CONTACT=<contact> python3 audit.py --input-root <checkout>/idx-signals \
    --calls-dir <checkout>/idx-signals/research/LLM_ARM_v1 --cache <scratch>/cache --out results
python3 secondary_v11.py --input-root <checkout>/idx-signals --calls-dir <...>/LLM_ARM_v1 --cache <scratch>/cache
```
A fresh run re-fetches the provider; its split records and bars can change after 2026-11-10.
