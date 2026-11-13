## Secondary view: split-unit assessments (display only, the frozen verdict above is unchanged)

8 of 106 planned spikes are split artifacts on current evidence (6 confirmed, 2 probable): a reverse split left the previous close in pre-split units, so the recorded +30% day did not happen. 2 are unresolved and stay in every view. 1 carried an artifact tag that current evidence does not support. Ledgers: `paper/split_flags.jsonl` (rule `SPLIT_ARTIFACT_V11`, the tag at the time) and `paper/split_assessments.jsonl` (rule `SPLIT_UNITS_V1`, research/SPLIT_REVISIONS_v1).

| Spike | Session | Tag at the time | Tag recorded before entry cutoff | Current assessment | Assessed |
|---|---|---|---|---|---|
| ATYR | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-12 |
| MASK | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-12 |
| OMEX | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_PROBABLE | 2026-11-12 |
| SGRX | 2026-10-30 | NOT_FLAGGED | no | NOT_ASSESSABLE | 2026-11-12 |
| WHLR | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-12 |
| XXII | 2026-11-05 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-12 |
| RCT | 2026-11-06 | NOT_FLAGGED | no | NOT_ASSESSABLE | 2026-11-12 |
| TOPS | 2026-11-09 | ARTIFACT_V11 | no | ARTIFACT_PROBABLE | 2026-11-12 |
| SMX | 2026-11-10 | ARTIFACT_V11 | yes | REAL_MOVE_AFTER_SPLIT | 2026-11-12 |
| GOVX | 2026-11-11 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-12 |
| SLXN | 2026-11-11 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-12 |

The same books three ways. As frozen counts every planned spike. Known at the time leaves out only the spikes whose artifact tag was recorded before their entry cutoff: it is what a filter could have done on the day. Corrected leaves out the spikes that current evidence classes as artifacts: it uses evidence that arrived later and is not a filter that was available before the trade. This is a disclosure, not a second verdict: the planned look and the bounds above are computed on every planned spike, as frozen.

| Book | View | Positions | Closed | Wins | P&L | Average trade |
|---|---|---:|---:|---:|---:|---:|
| KOD | As frozen | 94 | 2 | 1 | $-80 | -4.02% |
| KOD | Known at the time | 93 | 2 | 1 | $-80 | -4.02% |
| KOD | Corrected | 91 | 2 | 1 | $-80 | -4.02% |
| ALL | As frozen | 106 | 11 | 4 | $-1,140 | -10.37% |
| ALL | Known at the time | 105 | 11 | 4 | $-1,140 | -10.37% |
| ALL | Corrected | 98 | 7 | 2 | $-1,087 | -15.52% |
| AVOIDED | As frozen | 12 | 9 | 3 | $-1,060 | -11.78% |
| AVOIDED | Known at the time | 12 | 9 | 3 | $-1,060 | -11.78% |
| AVOIDED | Corrected | 7 | 5 | 1 | $-1,006 | -20.13% |
| OWNER | As frozen | 0 | 0 | 0 | $+0 | - |
| OWNER | Known at the time | 0 | 0 | 0 | $+0 | - |
| OWNER | Corrected | 0 | 0 | 0 | $+0 | - |
