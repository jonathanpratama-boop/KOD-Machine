# KOD paper book (PAPER_BOOK_v1)

## US forecast input health

**PARTIAL_INPUT — The latest US scan has unscanned names; full input coverage cannot be claimed.**

- Assessed 2026-11-19T23:01:03.629269Z; latest US scan session: 2026-11-19.
- Latest compatible LEARNER v2.4 forecast: 2026-11-19T22:58:39Z (signal session 2026-11-19).
- Eligible sets awaiting forecasts: 0; historical sets missed before cutoff: 32.
- Existing plan and account totals below are historical records, not proof that new input is flowing.
- SEC contact is configured in the checked execution context; successful source access and a sealed forecast still require verification.

Generated 2026-11-19T23:01:03Z. Paper only: no orders, no money. Protocol: `research/PAPER_BOOK_v1/protocol.json`.

## The three plain answers

- **What does it do?** For every US stock that just closed +30%, KOD says DONT_BUY when its dump-tomorrow probability is 0.46 or more, otherwise BUY_OK. The KOD book buys every BUY_OK at the next open and sells five sessions later; $1,000 a position, real costs.
- **Evidence so far?** 192 spikes planned, 78 trades closed. The verdict waits for the planned look at 300 closed trades; until then the numbers are a running tally.
- **What counts as success?** Two separate questions, each at the planned look: DONT_BUY works if the skipped spikes do worse than the bought ones (95% bound below zero); the KOD book makes money if its average trade is above zero (95% bound above zero).

## The books

| Book | What it holds | Positions | Open | Closed | Wins | P&L | Average trade |
|---|---|---:|---:|---:|---:|---:|---:|
| KOD | every BUY_OK | 175 | 101 | 66 | 12 | $-8,163 | -12.37% |
| ALL | every spike | 192 | 106 | 78 | 15 | $-10,828 | -13.88% |
| AVOIDED | every DONT_BUY (kept out) | 17 | 5 | 12 | 3 | $-2,665 | -22.21% |
| OWNER | spikes you confirmed BUY | 0 | 0 | 0 | 0 | $+0 | - |

## Every spike

| Signal | Ticker | Dump tomorrow | KOD | You | Status | Net |
|---|---|---:|---|---|---|---:|
| 2026-11-19 | ZKIN | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-19 | VIVS | 0.42 | BUY_OK | - | OPEN | - |
| 2026-11-19 | SEAT | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-19 | RAYA | 0.30 | BUY_OK | - | OPEN | - |
| 2026-11-19 | POAS | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-19 | MRKR | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-19 | MPU | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-19 | LVWR | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-19 | HTCR | 0.27 | BUY_OK | - | OPEN | - |
| 2026-11-19 | ELOG | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-19 | BDMD | 0.52 | DONT_BUY | - | OPEN | - |
| 2026-11-19 | BAER | 0.26 | BUY_OK | - | OPEN | - |
| 2026-11-18 | VWAV | 0.51 | DONT_BUY | - | OPEN | - |
| 2026-11-18 | SVRE | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-18 | SKYA | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-18 | NUR | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-18 | MPU | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-18 | ICU | 0.24 | BUY_OK | - | OPEN | - |
| 2026-11-18 | HIHO | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-18 | CUE | 0.18 | BUY_OK | - | OPEN | - |
| 2026-11-18 | CLRO | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-18 | BTOC | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-18 | AZI | 0.21 | BUY_OK | - | OPEN | - |
| 2026-11-18 | ANPA | 0.20 | BUY_OK | - | OPEN | - |
| 2026-11-18 | AKAN | 0.32 | BUY_OK | - | OPEN | - |
| 2026-11-17 | VAI | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-17 | TGL | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-17 | SYPR | 0.10 | BUY_OK | - | OPEN | - |
| 2026-11-17 | SMTK | 0.49 | DONT_BUY | - | OPEN | - |
| 2026-11-17 | SLS | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-17 | SGRX | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-17 | NCT | 0.61 | DONT_BUY | - | OPEN | - |
| 2026-11-17 | MPU | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-17 | KALA | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-17 | GP | 0.27 | BUY_OK | - | OPEN | - |
| 2026-11-17 | GLSI | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-17 | FRTT | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-17 | DFSC | 0.25 | BUY_OK | - | OPEN | - |
| 2026-11-17 | CVKD | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-17 | AZI | 0.23 | BUY_OK | - | OPEN | - |
| 2026-11-17 | AYTU | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-16 | VIVK | 0.55 | DONT_BUY | - | OPEN | - |
| 2026-11-16 | TDTH | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-16 | HIHO | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-16 | GMM | 0.44 | BUY_OK | - | OPEN | - |
| 2026-11-16 | GDHG | 0.32 | BUY_OK | - | OPEN | - |
| 2026-11-16 | ETS | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-16 | CYAB | 0.29 | BUY_OK | - | OPEN | - |
| 2026-11-16 | COSM | 0.26 | BUY_OK | - | OPEN | - |
| 2026-11-16 | CLRO | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-16 | BGIN | 0.18 | BUY_OK | - | OPEN | - |
| 2026-11-16 | AKAN | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-13 | ZBAO | 0.43 | BUY_OK | - | OPEN | - |
| 2026-11-13 | VTSI | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-13 | TGHL | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-13 | SLSN | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-13 | SLND | 0.09 | BUY_OK | - | OPEN | - |
| 2026-11-13 | SHIM | 0.10 | BUY_OK | - | OPEN | - |
| 2026-11-13 | SHFS | 0.43 | BUY_OK | - | OPEN | - |
| 2026-11-13 | SBC | 0.09 | BUY_OK | - | OPEN | - |
| 2026-11-13 | RAIN | 0.13 | BUY_OK | - | OPEN | - |
| 2026-11-13 | ONFO | 0.38 | BUY_OK | - | OPEN | - |
| 2026-11-13 | NMAX | 0.09 | BUY_OK | - | OPEN | - |
| 2026-11-13 | LFTO | 0.08 | BUY_OK | - | OPEN | - |
| 2026-11-13 | LFMD | 0.09 | BUY_OK | - | OPEN | - |
| 2026-11-13 | FCUV | 0.34 | BUY_OK | - | OPEN | - |
| 2026-11-13 | FCDH | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-13 | BKHA | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-13 | BGIN | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-13 | AKAN | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-13 | AEI | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-12 | XLAB | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-12 | TGHL | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-12 | TGEN | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-12 | RIME | 0.15 | BUY_OK | - | OPEN | - |
| 2026-11-12 | POAS | 0.32 | BUY_OK | - | OPEN | - |
| 2026-11-12 | PLCE | 0.28 | BUY_OK | - | OPEN | - |
| 2026-11-12 | PARA | 0.29 | BUY_OK | - | OPEN | - |
| 2026-11-12 | ICMB | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-12 | GP | 0.25 | BUY_OK | - | OPEN | - |
| 2026-11-12 | DBGI | 0.35 | BUY_OK | - | OPEN | - |
| 2026-11-12 | BGIN | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-12 | ARAI | 0.33 | BUY_OK | - | OPEN | - |
| 2026-11-12 | AIMD | 0.22 | BUY_OK | - | OPEN | - |
| 2026-11-12 | ADXN | 0.19 | BUY_OK | - | OPEN | - |
| 2026-11-12 | ADVB | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-11 | WHLR | 0.41 | BUY_OK | - | OPEN | - |
| 2026-11-11 | TANH | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-11 | SLXN | 0.31 | BUY_OK | - | OPEN | - |
| 2026-11-11 | SHFS | 0.40 | BUY_OK | - | OPEN | - |
| 2026-11-11 | SFWL | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-11 | SCKT | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-11 | RKDA | 0.17 | BUY_OK | - | OPEN | - |
| 2026-11-11 | RETO | 0.37 | BUY_OK | - | OPEN | - |
| 2026-11-11 | REED | 0.08 | BUY_OK | - | OPEN | - |
| 2026-11-11 | OPTT | 0.25 | BUY_OK | - | OPEN | - |
| 2026-11-11 | NWTG | 0.10 | BUY_OK | - | OPEN | - |
| 2026-11-11 | NCT | 0.25 | BUY_OK | - | OPEN | - |
| 2026-11-11 | GOVX | 0.36 | BUY_OK | - | OPEN | - |
| 2026-11-11 | GEVO | 0.08 | BUY_OK | - | OPEN | - |
| 2026-11-11 | ELOG | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-11 | CANG | 0.14 | BUY_OK | - | OPEN | - |
| 2026-11-11 | BURU | 0.33 | BUY_OK | - | OPEN | - |
| 2026-11-11 | BSEM | 0.16 | BUY_OK | - | OPEN | - |
| 2026-11-11 | BGS | 0.08 | BUY_OK | - | OPEN | - |
| 2026-11-10 | ZIP | 0.11 | BUY_OK | - | TRADED | -1.54% |
| 2026-11-10 | TTEC | 0.15 | BUY_OK | - | TRADED | +27.35% |
| 2026-11-10 | TREO | 0.18 | BUY_OK | - | TRADED | -23.61% |
| 2026-11-10 | TANH | 0.30 | BUY_OK | - | OPEN | - |
| 2026-11-10 | SMX | 0.26 | BUY_OK | - | TRADED | -82.51% |
| 2026-11-10 | PXLW | 0.17 | BUY_OK | - | TRADED | -12.65% |
| 2026-11-10 | PEPG | 0.26 | BUY_OK | - | TRADED | -29.54% |
| 2026-11-10 | NNOX | 0.16 | BUY_OK | - | TRADED | -37.44% |
| 2026-11-10 | NCI | 0.33 | BUY_OK | - | TRADED | -34.08% |
| 2026-11-10 | MNDO | 0.16 | BUY_OK | - | TRADED | -0.21% |
| 2026-11-10 | MI | 0.31 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-10 | LGVN | 0.19 | BUY_OK | - | TRADED | -34.90% |
| 2026-11-10 | INLF | 0.49 | DONT_BUY | - | TRADED | -54.92% |
| 2026-11-10 | ESLA | 0.31 | BUY_OK | - | TRADED | -58.32% |
| 2026-11-10 | AACG | 0.18 | BUY_OK | - | TRADED | -28.22% |
| 2026-11-09 | XHLD | 0.34 | BUY_OK | - | TRADED | -15.06% |
| 2026-11-09 | WOK | 0.29 | BUY_OK | - | TRADED | -6.33% |
| 2026-11-09 | UG | 0.17 | BUY_OK | - | TRADED | -23.40% |
| 2026-11-09 | TVRD | 0.32 | BUY_OK | - | TRADED | -28.06% |
| 2026-11-09 | TOPS | 0.48 | DONT_BUY | - | TRADED | -22.03% |
| 2026-11-09 | TLS | 0.16 | BUY_OK | - | TRADED | -3.36% |
| 2026-11-09 | TANH | 0.36 | BUY_OK | - | TRADED | +152.51% |
| 2026-11-09 | OMH | 0.49 | DONT_BUY | - | TRADED | -83.56% |
| 2026-11-09 | NCPL | 0.21 | BUY_OK | - | TRADED | +29.63% |
| 2026-11-09 | MODD | 0.14 | BUY_OK | - | TRADED | -1.54% |
| 2026-11-09 | MF | 0.31 | BUY_OK | - | TRADED | +48.85% |
| 2026-11-09 | JZ | 0.32 | BUY_OK | - | TRADED | +4.39% |
| 2026-11-09 | INLF | 0.40 | BUY_OK | - | TRADED | +14.45% |
| 2026-11-09 | GPUS | 0.28 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-09 | GFR | 0.15 | BUY_OK | - | TRADED | -0.56% |
| 2026-11-09 | FJET | 0.23 | BUY_OK | - | TRADED | -27.91% |
| 2026-11-09 | FISN | 0.28 | BUY_OK | - | TRADED | -1.00% |
| 2026-11-09 | ESLA | 0.36 | BUY_OK | - | TRADED | -39.28% |
| 2026-11-09 | DCTH | 0.17 | BUY_OK | - | TRADED | -4.63% |
| 2026-11-09 | CVKD | 0.27 | BUY_OK | - | TRADED | +36.86% |
| 2026-11-09 | CKX | 0.33 | BUY_OK | - | TRADED | -18.63% |
| 2026-11-09 | AKBA | 0.22 | BUY_OK | - | TRADED | -27.24% |
| 2026-11-06 | VSA | 0.17 | BUY_OK | - | TRADED | -33.61% |
| 2026-11-06 | VIVK | 0.29 | BUY_OK | - | TRADED | -13.88% |
| 2026-11-06 | VAI | 0.15 | BUY_OK | - | TRADED | -2.33% |
| 2026-11-06 | STAK | 0.20 | BUY_OK | - | TRADED | -50.35% |
| 2026-11-06 | SNT | 0.16 | BUY_OK | - | TRADED | -2.06% |
| 2026-11-06 | SMX | 0.23 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-06 | SKIN | 0.15 | BUY_OK | - | TRADED | -7.55% |
| 2026-11-06 | SERV | 0.10 | BUY_OK | - | TRADED | -26.08% |
| 2026-11-06 | SDA | 0.20 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-06 | RDGT | 0.14 | BUY_OK | - | TRADED | -9.92% |
| 2026-11-06 | RCT | 0.25 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-06 | POM | 0.22 | BUY_OK | - | TRADED | -0.38% |
| 2026-11-06 | OPTU | 0.14 | BUY_OK | - | TRADED | -9.14% |
| 2026-11-06 | OBX | 0.16 | BUY_OK | - | TRADED | -7.63% |
| 2026-11-06 | MTVA | 0.14 | BUY_OK | - | TRADED | -16.58% |
| 2026-11-06 | KRMN | 0.09 | BUY_OK | - | TRADED | -18.08% |
| 2026-11-06 | KDK | 0.14 | BUY_OK | - | TRADED | -17.11% |
| 2026-11-06 | INDI | 0.11 | BUY_OK | - | TRADED | +6.66% |
| 2026-11-06 | HTCO | 0.19 | BUY_OK | - | TRADED | -7.62% |
| 2026-11-06 | HPAI | 0.23 | BUY_OK | - | TRADED | -33.71% |
| 2026-11-06 | GOGO | 0.18 | BUY_OK | - | TRADED | -17.84% |
| 2026-11-06 | GIBO | 0.14 | BUY_OK | - | TRADED | -51.75% |
| 2026-11-06 | FROG | 0.08 | BUY_OK | - | TRADED | +8.00% |
| 2026-11-06 | FLY | 0.14 | BUY_OK | - | TRADED | +5.49% |
| 2026-11-06 | CIIT | 0.16 | BUY_OK | - | TRADED | -20.71% |
| 2026-11-06 | CABR | 0.20 | BUY_OK | - | TRADED | -25.95% |
| 2026-11-05 | ZNB | 0.22 | BUY_OK | - | TRADED | -30.41% |
| 2026-11-05 | XXII | 0.36 | BUY_OK | - | TRADED | -56.37% |
| 2026-11-05 | VXX | 0.11 | BUY_OK | - | TRADED | -13.98% |
| 2026-11-05 | PLCE | 0.14 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-05 | LABT | 0.33 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-05 | JDZG | 0.15 | BUY_OK | - | TRADED | -47.37% |
| 2026-11-05 | HTCR | 0.13 | BUY_OK | - | TRADED | -14.94% |
| 2026-11-05 | FLYE | 0.15 | BUY_OK | - | TRADED | -14.89% |
| 2026-11-05 | DNUT | 0.13 | BUY_OK | - | TRADED | -12.59% |
| 2026-11-05 | BDMD | 0.15 | BUY_OK | - | UNRESOLVABLE | - |
| 2026-11-05 | APP | 0.09 | BUY_OK | - | TRADED | +14.81% |
| 2026-11-05 | AMTX | 0.13 | BUY_OK | - | TRADED | -33.26% |
| 2026-11-05 | AEHL | 0.30 | BUY_OK | - | TRADED | -21.11% |
| 2026-10-30 | WHLR | 0.62 | DONT_BUY | - | TRADED | -60.01% |
| 2026-10-30 | SLGB | 0.52 | DONT_BUY | - | TRADED | -46.60% |
| 2026-10-30 | SGRX | 0.58 | DONT_BUY | - | TRADED | -28.30% |
| 2026-10-30 | ONEG | 0.61 | DONT_BUY | - | TRADED | -13.46% |
| 2026-10-30 | OMEX | 0.70 | DONT_BUY | - | TRADED | -4.73% |
| 2026-10-30 | MASK | 0.63 | DONT_BUY | - | TRADED | +9.12% |
| 2026-10-30 | GDYN | 0.47 | DONT_BUY | - | TRADED | +0.07% |
| 2026-10-30 | FMC | 0.38 | BUY_OK | - | TRADED | -11.72% |
| 2026-10-30 | CHOW | 0.68 | DONT_BUY | - | TRADED | -12.34% |
| 2026-10-30 | ATYR | 0.65 | DONT_BUY | - | TRADED | +50.24% |
| 2026-10-30 | ASUR | 0.43 | BUY_OK | - | TRADED | +3.69% |


## Secondary view: split-unit assessments (display only, the frozen verdict above is unchanged)

14 of 192 planned spikes are split artifacts on current evidence (7 confirmed, 7 probable): a reverse split left the previous close in pre-split units, so the recorded +30% day did not happen. 1 are unresolved and stay in every view. 1 carried an artifact tag that current evidence does not support. Ledgers: `paper/split_flags.jsonl` (rule `SPLIT_ARTIFACT_V11`, the tag at the time) and `paper/split_assessments.jsonl` (rule `SPLIT_UNITS_V1`, research/SPLIT_REVISIONS_v1).

| Spike | Session | Tag at the time | Tag recorded before entry cutoff | Current assessment | Assessed |
|---|---|---|---|---|---|
| ATYR | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-13 |
| MASK | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-13 |
| OMEX | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_PROBABLE | 2026-11-13 |
| WHLR | 2026-10-30 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-13 |
| XXII | 2026-11-05 | ARTIFACT_V11 | no | ARTIFACT_CONFIRMED | 2026-11-13 |
| TOPS | 2026-11-09 | ARTIFACT_V11 | no | ARTIFACT_PROBABLE | 2026-11-13 |
| SMX | 2026-11-10 | ARTIFACT_V11 | yes | REAL_MOVE_AFTER_SPLIT | 2026-11-13 |
| GOVX | 2026-11-11 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-13 |
| SLXN | 2026-11-11 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-13 |
| ARAI | 2026-11-12 | INDETERMINATE | yes | ARTIFACT_CONFIRMED | 2026-11-13 |
| COSM | 2026-11-16 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-16 |
| DFSC | 2026-11-17 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-17 |
| KALA | 2026-11-17 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-17 |
| NCT | 2026-11-17 | INDETERMINATE | yes | REAL_MOVE_UNITS_UNVERIFIED | 2026-11-17 |
| SGRX | 2026-11-17 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-17 |
| TGL | 2026-11-17 | ARTIFACT_V11 | yes | ARTIFACT_PROBABLE | 2026-11-17 |

The same books three ways. As frozen counts every planned spike. Known at the time leaves out only the spikes whose artifact tag was recorded before their entry cutoff: it is what a filter could have done on the day. Corrected leaves out the spikes that current evidence classes as artifacts: it uses evidence that arrived later and is not a filter that was available before the trade. This is a disclosure, not a second verdict: the planned look and the bounds above are computed on every planned spike, as frozen.

| Book | View | Positions | Closed | Wins | P&L | Average trade |
|---|---|---:|---:|---:|---:|---:|
| KOD | As frozen | 175 | 66 | 12 | $-8,163 | -12.37% |
| KOD | Known at the time | 168 | 65 | 12 | $-7,337 | -11.29% |
| KOD | Corrected | 166 | 65 | 12 | $-7,599 | -11.69% |
| ALL | As frozen | 192 | 78 | 15 | $-10,828 | -13.88% |
| ALL | Known at the time | 185 | 77 | 15 | $-10,003 | -12.99% |
| ALL | Corrected | 178 | 72 | 13 | $-9,990 | -13.87% |
| AVOIDED | As frozen | 17 | 12 | 3 | $-2,665 | -22.21% |
| AVOIDED | Known at the time | 17 | 12 | 3 | $-2,665 | -22.21% |
| AVOIDED | Corrected | 12 | 7 | 1 | $-2,391 | -34.16% |
| OWNER | As frozen | 0 | 0 | 0 | $+0 | - |
| OWNER | Known at the time | 0 | 0 | 0 | $+0 | - |
| OWNER | Corrected | 0 | 0 | 0 | $+0 | - |
