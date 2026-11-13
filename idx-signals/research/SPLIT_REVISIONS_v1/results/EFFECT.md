# SPLIT_REVISIONS_v1: effect on published results (descriptive)

Generated 2026-11-12T23:57:48Z from the ledgers at repository commit `134f58f`, with each consumer's own code, under `PROTOCOL.md`. Left column: every record. Right column: without the 11 sets that current evidence classes as split artifacts. The 8 unresolved sets are in both columns. No verdict changes: every frozen verdict stays as frozen, and no scheduled look is taken here.

Sets left out: ATYR 2026-10-30, ENLV 2026-10-28, GOVX 2026-11-11, MASK 2026-10-30, OMEX 2026-10-30, PARA 2026-10-28, SCAG 2026-10-28, SLXN 2026-11-11, TOPS 2026-11-09, WHLR 2026-10-30, XXII 2026-11-05.

Unresolved, kept: ADIL 2026-10-28, GNTA 2026-11-02, HUBC 2026-11-03, NUWE 2026-10-27, OMH 2026-11-04, RCT 2026-11-06, SGRX 2026-10-30, VCIG 2026-11-02.

## Paper book

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

## Speculation register, US

All sets:

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 57 | 57 | 57 | 6 | -12.50% | -11.72% | -1.82% | -10.68% | -2.24 | 0.963 | - / next 60 | accumulating (no look reached) |

Without the artifact sets:

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 50 | 50 | 50 | 6 | -10.27% | -11.21% | -0.94% | -9.33% | -2.30 | 0.965 | - / next 60 | accumulating (no look reached) |

| Statement | Graded | Realised rate | Twins' rate | Brier (register) | Graded, corrected | Realised rate, corrected | Twins' rate, corrected | Brier (register), corrected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 57 | 0.105 | 0.052 | 0.0965 | 50 | 0.100 | 0.059 | 0.0929 |
| FADE10_5 | 57 | 0.544 | 0.348 | 0.2679 | 50 | 0.540 | 0.352 | 0.2672 |
| GAIN0_5 | 57 | 0.263 | 0.377 | 0.2201 | 50 | 0.260 | 0.396 | 0.2196 |
| BEATS_TWINS_5 | 57 | 0.333 | 0.510 | 0.2500 | 50 | 0.340 | 0.511 | 0.2500 |
| DOWN10_1 | 118 | 0.263 | 0.053 | 0.2116 | 112 | 0.250 | 0.053 | 0.2083 |
| UP10_1 | 118 | 0.220 | 0.047 | 0.1980 | 112 | 0.223 | 0.047 | 0.1991 |
| BEATS_TWINS_1 | 116 | 0.500 | 0.512 | 0.2500 | 110 | 0.500 | 0.513 | 0.2500 |

## LEARNER v2.4 (descriptive metrics; no planned evaluation is frozen)

| Statement | Pairs | Rate | AUC | Benchmark AUC | Pairs, corrected | Rate, corrected | AUC, corrected | Benchmark AUC, corrected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NEXT_DUMP10_1 | 88 | 0.239 | 0.654 | 0.630 | 82 | 0.220 | 0.639 | 0.608 |
| DUMP10_5 | 20 | 0.300 | 0.643 | 0.583 | 16 | 0.375 | 0.683 | 0.817 |

Pairs on the sets left out: 10. The report printed on 2026-11-11 shows 74 headline pairs and an AUC of 0.693; it predates the outcomes resolved since.

## LEARNER v2.2, US speculation statements

| Statement | n | Rate | Brier anchor | Brier raw | n, corrected | Rate, corrected | Brier anchor, corrected | Brier raw, corrected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SPEC_US:BEATS_TWINS_5 | 52 | 0.33 | 0.2500 | 0.2504 | 45 | 0.33 | 0.2500 | 0.2526 |
| SPEC_US:DUMP10_5 | 52 | 0.33 | 0.2258 | 0.2258 | 45 | 0.36 | 0.2314 | 0.2314 |
| SPEC_US:PUMP30_5 | 52 | 0.10 | 0.0902 | 0.0902 | 45 | 0.09 | 0.0852 | 0.0852 |
| SPEC_US:PUMP_AND_DUMP_5 | 52 | 0.00 | 0.0038 | 0.0038 | 45 | 0.00 | 0.0038 | 0.0038 |

Pairs on the sets left out: 28.

## Consumers reported by count only

| Consumer | Records citing a set left out | Sets left out that are cited |
|---|---:|---:|
| LLM_ARM_v1 US calls (first look not taken) | 4 | 4 |
| Catalyst tags and sets | 11 | 11 |
| Decision ledger | 18 | 11 |
| Paper account | 6 | 3 |

The paper account's records on these sets are declined candidates; the KODCHECK trace of 2026-11-12 found no order, entry or exit on any of them.
