# SPLIT_REVISIONS_v1: dry run of the assessments

Generated 2026-11-12T23:57:48Z on repository commit `134f58f`, from the provider responses recorded on 2026-11-12. No live ledger was written: the 168 proposed records were sealed into a temporary ledger, validated there, and are listed in `dry_run_records.jsonl`. This is the run under contract addenda 1 and 2; the two earlier runs are kept in `first-run/` and `second-run/`.

## What the command would append

| Assessment | Sets |
|---|---:|
| ARTIFACT_CONFIRMED | 6 |
| ARTIFACT_PROBABLE | 5 |
| NOT_ASSESSABLE | 5 |
| NO_ACTION_FOUND | 145 |
| REAL_MOVE_AFTER_SPLIT | 4 |
| UNEXPLAINED_EXTREME_MOVE | 2 |
| UNITS_INCONSISTENT | 1 |

- Sealed US sets: 168. Responses read: 151 tickers, 147 with bars.
- Validator problems on the temporary ledger: 0.
- Records a second pass over the same pull would add: 0.
- Left out of the corrected view (11): ATYR 2026-10-30, ENLV 2026-10-28, GOVX 2026-11-11, MASK 2026-10-30, OMEX 2026-10-30, PARA 2026-10-28, SCAG 2026-10-28, SLXN 2026-11-11, TOPS 2026-11-09, WHLR 2026-10-30, XXII 2026-11-05.
- Left out of the view as known at the time (1): SMX 2026-11-10.
- Unresolved, kept in every view (8): ADIL 2026-10-28, GNTA 2026-11-02, HUBC 2026-11-03, NUWE 2026-10-27, OMH 2026-11-04, RCT 2026-11-06, SGRX 2026-10-30, VCIG 2026-11-02.
- Against the KODCHECK run of 2026-11-12 on the same sets: 163 of 168 classes are the same. The 5 that differ are the sets of addenda 1 and 2: the KODCHECK run reported them as "no corporate action found".
- First run, before addendum 1: 150 `NO_ACTION_FOUND` and no `NOT_ASSESSABLE`; four of those sets (GNTA, HUBC, RCT, SGRX) had a provider response with no bars.
- Second run, under addendum 1 only: 146 `NO_ACTION_FOUND` and 4 `NOT_ASSESSABLE`; one more set (ADIL 2026-10-28) had a response that holds only the signal session's bar.
- In this run every one of the 145 `NO_ACTION_FOUND` sets has its previous session identified in the provider's bars.

## The named cases and every set that is not a plain pass

| Set | Recorded move | Tag at the time | Tag recorded | Entry cutoff | Assessment | Split used | Adjusted move | Previous bar | Units |
|---|---:|---|---|---|---|---|---:|---|---|
| NUWE 2026-10-27 | +76% | NOT_FLAGGED | 2026-11-11T12:35:38Z | 2026-10-28T13:30:00Z | UNITS_INCONSISTENT | - | - | - | INCONSISTENT |
| ADIL 2026-10-28 | +36% | NOT_FLAGGED | 2026-11-11T12:35:38Z | 2026-10-29T13:30:00Z | NOT_ASSESSABLE | - | - | - | UNKNOWN |
| PARA 2026-10-28 | +691% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-10-29T13:30:00Z | ARTIFACT_PROBABLE | 2026-10-27 1:10 | -21% | 2026-10-23 (matched) | UNCHANGED |
| SCAG 2026-10-28 | +1,235% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-10-29T13:30:00Z | ARTIFACT_PROBABLE | 2026-10-27 1:15 | -11% | 2026-10-23 (matched) | UNCHANGED |
| ENLV 2026-10-28 | +1,409% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-10-29T13:30:00Z | ARTIFACT_PROBABLE | 2026-10-27 1:16 | -6% | 2026-10-23 (matched) | UNCHANGED |
| SGRX 2026-10-30 | +83% | NOT_FLAGGED | 2026-11-11T12:35:38Z | 2026-11-02T13:30:00Z | NOT_ASSESSABLE | - | - | - | UNKNOWN |
| WHLR 2026-10-30 | +553% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-11-02T13:30:00Z | ARTIFACT_CONFIRMED | 2026-10-30 1:6 | +9% | 2026-10-29 (rebased_match) | PRE_SPLIT_CONFIRMED |
| OMEX 2026-10-30 | +2,000% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-11-02T13:30:00Z | ARTIFACT_PROBABLE | 2026-10-29 1:25 | -16% | 2026-10-27 (matched) | UNCHANGED |
| MASK 2026-10-30 | +253% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-11-02T13:30:00Z | ARTIFACT_CONFIRMED | 2026-10-30 1:4 | -12% | 2026-10-29 (rebased_match) | PRE_SPLIT_CONFIRMED |
| ATYR 2026-10-30 | +3,884% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-11-02T13:30:00Z | ARTIFACT_CONFIRMED | 2026-10-29 1:40 | -0% | 2026-10-27 (rebased_match) | PRE_SPLIT_CONFIRMED |
| GNTA 2026-11-02 | +32% | NOT_FLAGGED | 2026-11-11T12:35:38Z | 2026-11-03T13:30:00Z | NOT_ASSESSABLE | - | - | - | UNKNOWN |
| VCIG 2026-11-02 | +4,728% | INDETERMINATE | 2026-11-11T12:35:38Z | 2026-11-03T13:30:00Z | UNEXPLAINED_EXTREME_MOVE | - | - | 2026-10-30 (matched) | UNCHANGED |
| HUBC 2026-11-03 | +30% | NOT_FLAGGED | 2026-11-11T12:35:38Z | 2026-11-04T13:30:00Z | NOT_ASSESSABLE | - | - | - | UNKNOWN |
| OMH 2026-11-04 | +433% | INDETERMINATE | 2026-11-11T12:35:38Z | 2026-11-05T13:30:00Z | UNEXPLAINED_EXTREME_MOVE | - | - | 2026-11-03 (matched) | UNCHANGED |
| XXII 2026-11-05 | +4,495% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-11-06T13:30:00Z | ARTIFACT_CONFIRMED | 2026-11-05 1:58 | -21% | 2026-11-04 (rebased_match) | PRE_SPLIT_CONFIRMED |
| RCT 2026-11-06 | +41% | NOT_FLAGGED | 2026-11-11T12:35:38Z | 2026-11-09T13:30:00Z | NOT_ASSESSABLE | - | - | - | UNKNOWN |
| TOPS 2026-11-09 | +884% | ARTIFACT_V11 | 2026-11-11T12:35:38Z | 2026-11-10T13:30:00Z | ARTIFACT_PROBABLE | 2026-11-06 1:10 | -2% | 2026-11-03 (matched) | UNCHANGED |
| SMX 2026-11-10 | +106% | ARTIFACT_V11 | 2026-11-11T12:38:16Z | 2026-11-11T13:30:00Z | REAL_MOVE_AFTER_SPLIT | - | - | 2026-11-09 (matched) | UNCHANGED |
| GOVX 2026-11-11 | +1,829% | INDETERMINATE | 2026-11-11T23:00:40Z | 2026-11-12T13:30:00Z | ARTIFACT_CONFIRMED | 2026-11-11 1:24 | -20% | 2026-11-10 (rebased_match) | PRE_SPLIT_CONFIRMED |
| SLXN 2026-11-11 | +2,863% | INDETERMINATE | 2026-11-11T23:00:40Z | 2026-11-12T13:30:00Z | ARTIFACT_CONFIRMED | 2026-11-11 1:24 | +23% | 2026-11-10 (rebased_match) | PRE_SPLIT_CONFIRMED |

Sources recorded on a record:
- SMX 2026-11-10: https://www.sec.gov/Archives/edgar/data/0001940674/000149315226049929/ex99-1.htm

## Reading the three named cases

- **SMX 2026-11-10.** The recorded previous close is found unchanged in the pull at 2026-11-09, the split's own effective session, so the previous bar does not precede the split and both closes are in the same units. The V11 tag was recorded 52 minutes before the entry cutoff: it is the one artifact tag that was available before a trade, and current evidence does not support it.
- **GOVX and SLXN 2026-11-11.** The pull lists a 1-for-24 split on the signal session and shows the previous session's close multiplied by 24, so the sealed previous close was in pre-split units. Both tags at the time were `INDETERMINATE`.

## What this does not show

The assessments above are first assessments from a later pull. A reassessment that supersedes an assessment made at sealing will first occur on a scheduled run after the merge. No recorded pull of a sealing night was available to this branch. `SIMULATION.md` runs the nightly function on a reconstruction of that night and on the nights after it; the scheduled job itself has not run this code.
