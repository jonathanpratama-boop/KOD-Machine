# Speculation Register (KOD-SPEC-REGISTER-v1.1, protocol sha256 b0e9b6d9b533)

Generated 2026-11-04T10:30:22Z from `paper/speculations.jsonl`: 84 sets sealed, 44 resolutions. Paper only; no orders. The register never changes a decision and runs no variant of a retired entry.

Windows: **BASE5**: the frozen plan: the validated harness plan, prospectively, beside twins; **PATH20**: the 20-session price path of the candidate and its twins; no plan; **NEXT1**: the next session's close of the candidate and its twins; no plan.

## IDX: 17 sets over 5 signal sessions (2026-10-29 .. 2026-11-04, 3.40 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.151 (validation trade sd 0.1967 (run 20261009T050040Z_MOONSHOT_E1_D1_v1.1), paired, / sqrt(sets per session)) | 513 | 82 | 21 | 18 |

PATH20 windows resolved: 0; NEXT1: 6.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |
| DOWN10_1 | 6 | 0.000 | 0.000 | 0.500 | 0.2500 | 0.2500 | 0.2500 |
| UP10_1 | 6 | 0.000 | 0.033 | 0.500 | 0.2500 | 0.2500 | 0.2500 |
| BEATS_TWINS_1 | 6 | 0.000 | 0.533 | 0.500 | 0.2500 | 0.2500 | 0.2500 |

## US: 62 sets over 6 signal sessions (2026-10-27 .. 2026-11-03, 10.33 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.151 (validation trade sd 0.3429 (run 20261008T115656Z_MOONSHOT_E2_US_D1_v1), paired, / sqrt(sets per session)) | 513 | 82 | 21 | 6 |

PATH20 windows resolved: 0; NEXT1: 32.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |
| DOWN10_1 | 32 | 0.312 | 0.056 | 0.500 | 0.2500 | 0.2500 | 0.2318 |
| UP10_1 | 32 | 0.219 | 0.029 | 0.500 | 0.2500 | 0.2500 | 0.2757 |
| BEATS_TWINS_1 | 32 | 0.469 | 0.528 | 0.500 | 0.2500 | 0.2500 | 0.2544 |

## CRYPTO: 5 sets over 4 signal sessions (2026-10-27 .. 2026-10-30, 0.62 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 2 | 2 | 2 | 2 | -20.83% | -20.83% | -8.98% | -11.84% | -0.53 | 0.654 | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.441 (validation trade sd 0.3486 (run 20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1), paired, / sqrt(sets per session)) | 4375 | 700 | 175 | 93 |

PATH20 windows resolved: 0; NEXT1: 3.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 2 | 0.000 | 0.100 | 0.185 | 0.0341 | 0.2500 | 0.2500 |
| FADE10_5 | 2 | 0.500 | 0.400 | 0.511 | 0.2501 | 0.2500 | 0.2500 |
| GAIN0_5 | 2 | 0.500 | 0.100 | 0.314 | 0.2846 | 0.2500 | 0.2500 |
| BEATS_TWINS_5 | 2 | 0.500 | 0.500 | 0.500 | 0.2500 | 0.2500 | 0.2500 |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |
| DOWN10_1 | 3 | 0.667 | 0.067 | 0.500 | 0.2500 | 0.2500 | 0.2500 |
| UP10_1 | 3 | 0.333 | 0.067 | 0.500 | 0.2500 | 0.2500 | 0.2500 |
| BEATS_TWINS_1 | 3 | 0.333 | 0.533 | 0.500 | 0.2500 | 0.2500 | 0.2500 |

## Latest sealed sets (postcards from the future)

### US CHSN (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-CHSN` (PASS), bound to ledger record `92353d26f6c7`; set `9e9200068d8d`.
Signal close 3.38 (reference 0.991); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): SPPL 2.4572, TOMZ 2.24, INM 1.68, CHOW 4.08, TUSK 3.15.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US MERC (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-MERC` (PASS), bound to ledger record `d6f1ff729062`; set `45aaf81e2276`.
Signal close 0.212 (reference 0.13); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): RDHL 0.4159, BGL 0.1206, XELB 0.38, CELZ 0.6735, BRAG 0.9032.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US PARA (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-PARA` (PASS), bound to ledger record `fd12dba78880`; set `25484ad593b2`.
Signal close 2.72 (reference 1.69); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): MSC 1.07, WLDS 1.44, JFIN 1.565, INHD 3.48, ENLV 1.46.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US EHGO (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-EHGO` (PASS), bound to ledger record `b8477c46ea36`; set `c740462287b8`.
Signal close 2.5 (reference 1.91); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): GENK 1.39, PAVS 3.34, CTRM 1.36, MOLN 3.09, LBGJ 1.53.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US HUBC (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-HUBC` (PASS), bound to ledger record `4a60facd599c`; set `40bd6d8070ee`.
Signal close 0.1067 (reference 0.082); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): AVAT 0.8919, ABOS 0.2344, ACH 0.2828, LUCD 0.409, BEEM 0.797.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US KTTA (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-KTTA` (PASS), bound to ledger record `64dae1174e2f`; set `0a5d8e2eacdc`.
Signal close 0.53 (reference 0.368); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): ELUT 0.8132, CTXR 0.5732, GNTA 0.985, SYNX 0.9639, SAGT 0.6994.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US IFBD (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-IFBD` (PASS), bound to ledger record `39e03d2915ff`; set `e362ec65309e`.
Signal close 1.43 (reference 1.03); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): ICON 1.01, CLPR 3.36, SRTS 3.285, CHOW 4.08, INM 1.68.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US CRMT (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-CRMT` (PASS), bound to ledger record `47be452e7632`; set `fa690b544902`.
Signal close 1.21 (reference 0.91); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): IPSC 1.52, ALXO 1.29, CAST 1.28, FHTX 2.13, IHRT 2.09.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US REED (2026-11-03) - sealed 2026-11-03T22:57:07Z, cutoff 2026-11-04T13:30:00Z
Decision `SCAN-US-2026-11-03-G2_RET30-REED` (PASS), bound to ledger record `c198a0fe384a`; set `da1abea6e9f7`.
Signal close 1.02 (reference 0.76); entry: the next session's opening print.
Tag: 9 flags today vs trailing median 10.0 -> hot_day = False.
Twins (band+liq+mom+dd): AHG 1.21, SCAG 1.75, ALLR 1.13, MRT 2.05, EFOI 4.02.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.350 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.100 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### CRYPTO SOPH (2026-10-30) - sealed 2026-10-31T00:28:50Z, cutoff 2026-10-31T02:00:00Z
Decision `SCAN-CRYPTO-2026-10-30-G2_RET30-SOPH` (PASS), bound to ledger record `c6f3f7e68e72`; set `77c11b1d0eb4`.
Signal close 0.0022 (reference 0.00141); entry: the Binance spot quote taken at sealing time (the harness used the next day's open); quote 0.00223 at 2026-10-31T00:28:59Z.
Tag: 2 flags today vs trailing median 1.0 -> hot_day = True.
Twins (band+liq+mom+dd): ROBO 0.00528, GUN 0.002009, NOM 0.00159, FOGO 0.00288, BB 0.00729.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.185 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.511 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.314 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### CRYPTO BEAMX (2026-10-30) - sealed 2026-10-31T00:28:50Z, cutoff 2026-10-31T02:00:00Z
Decision `SCAN-CRYPTO-2026-10-30-G2_RET30-BEAMX` (PASS), bound to ledger record `d1fcbd0a0c41`; set `14f6ca1a2f0e`.
Signal close 0.004652 (reference 0.003338); entry: the Binance spot quote taken at sealing time (the harness used the next day's open); quote 0.004678 at 2026-10-31T00:28:52Z.
Tag: 2 flags today vs trailing median 1.0 -> hot_day = True.
Twins (band+liq+mom): KAT 0.00415, FLOKI 2.435e-05, SOLV 0.005082, RSR 0.001445, AMP 0.000655.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.185 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.511 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.314 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### IDX BOBA (2026-11-04) - sealed 2026-11-04T10:30:16Z, cutoff 2026-11-05T01:45:00Z
Decision `SCAN-2026-11-04-F1_ARA-BOBA` (PASS), bound to ledger record `17f3fa4ba5f4`; set `4675d7a89842`.
Signal close 214 (reference 159.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 6 flags today vs trailing median 5.0 -> hot_day = True.
Twins (band+liq+mom+dd): BOLT 760, BBMD 2060, GDYR 1055, PEHA 260, BPII 400.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.183 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.359 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.311 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### IDX TMPO (2026-11-04) - sealed 2026-11-04T10:30:16Z, cutoff 2026-11-05T01:45:00Z
Decision `SCAN-2026-11-04-F1_ARA-TMPO` (PASS), bound to ledger record `3a2b045d8358`; set `e35a88967e3a`.
Signal close 292 (reference 234.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 6 flags today vs trailing median 5.0 -> hot_day = True.
Twins (band+liq+mom+dd): BDMN 4600, BMRI 3600, BTPS 980, KLBF 725, ULTJ 2070.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.183 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.359 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.311 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### IDX YUPI (2026-11-04) - sealed 2026-11-04T10:30:16Z, cutoff 2026-11-05T01:45:00Z
Decision `SCAN-2026-11-04-F1_ARA-YUPI` (PASS), bound to ledger record `9c3395880336`; set `48d087053156`.
Signal close 910 (reference 730.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 6 flags today vs trailing median 5.0 -> hot_day = True.
Twins (band+liq+mom+dd): BSIM 760, SIPD 585, PDES 314, PALM 210, BALI 1210.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.183 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.359 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.311 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### IDX AIMS (2026-11-04) - sealed 2026-11-04T10:30:16Z, cutoff 2026-11-05T01:45:00Z
Decision `SCAN-2026-11-04-F1_ARA-AIMS` (PASS), bound to ledger record `fc6b622d5393`; set `390056007e8b`.
Signal close 755 (reference 605.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 6 flags today vs trailing median 5.0 -> hot_day = True.
Twins (band+liq+mom+dd): MTEL 360, STAA 1015, TUGU 1230, HEAL 478, DSNG 1315.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.183 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.359 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.311 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### IDX FLMC (2026-11-04) - sealed 2026-11-04T10:30:16Z, cutoff 2026-11-05T01:45:00Z
Decision `SCAN-2026-11-04-F1_ARA-FLMC` (PASS), bound to ledger record `7ed91f2993da`; set `0d396428feeb`.
Signal close 146 (reference 133.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 6 flags today vs trailing median 5.0 -> hot_day = True.
Twins (band+liq+mom+dd): DGIK 132, PRIM 124, BATR 94, INOV 140, AXIO 127.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.183 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.359 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.311 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

## Latest resolutions

| Set | Window | Status | Candidate | Net | Twins mean | Diff | Cone (candidate / twins' rate) |
|---|---|---|---|---:|---:|---:|---|
| US-2026-10-29-G2_RET30-BURU | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.33, UP10_1=0/0.00, BEATS_TWINS_1=0 |
| US-2026-10-29-G2_RET30-ADT | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=1/0.40 |
| US-2026-10-29-G2_RET30-GKOS | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| US-2026-10-29-G2_RET30-XCH | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.20, UP10_1=1/0.00, BEATS_TWINS_1=1/0.60 |
| US-2026-10-29-G2_RET30-NCPL | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| US-2026-10-29-G2_RET30-KPLT | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| CRYPTO-2026-10-29-G2_RET30-PARTI | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.20, UP10_1=0/0.20, BEATS_TWINS_1=0/0.60 |
| CRYPTO-2026-10-30-G2_RET30-SOPH | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.40 |
| CRYPTO-2026-10-30-G2_RET30-BEAMX | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=1/0.00, BEATS_TWINS_1=1/0.60 |
| 2026-10-30-F1_ARA-KONI | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.40 |
| 2026-10-30-F1_ARA-POLI | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| 2026-10-30-F1_ARA-ALKA | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.20, BEATS_TWINS_1=0/0.60 |
| US-2026-10-30-G2_RET30-ONEG | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.20, BEATS_TWINS_1=0/0.60 |
| US-2026-10-30-G2_RET30-SLGB | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.20, UP10_1=0/0.00, BEATS_TWINS_1=1/0.60 |
| US-2026-10-30-G2_RET30-CHOW | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0 |
| US-2026-10-30-G2_RET30-SGRX | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.20, BEATS_TWINS_1=1/0.40 |
| US-2026-10-30-G2_RET30-ASUR | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=1/0.40 |
| US-2026-10-30-G2_RET30-GDYN | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=1/0.40 |
| US-2026-10-30-G2_RET30-FMC | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.20, BEATS_TWINS_1=1/0.60 |
| US-2026-10-30-G2_RET30-WHLR | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.40 |
| US-2026-10-30-G2_RET30-OMEX | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=1/0.40 |
| US-2026-10-30-G2_RET30-MASK | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| US-2026-10-30-G2_RET30-ATYR | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.20, UP10_1=1/0.00, BEATS_TWINS_1=1/0.60 |
| CRYPTO-2026-10-27-G2_RET30-HAEDAL | BASE5 | RESOLVED | TRADED | +2.01% | -8.64% | +10.65% | RUN30_5=0/0.00, FADE10_5=0/0.20, GAIN0_5=1/0.00, BEATS_TWINS_5=1/0.60 |
| 2026-11-02-F1_ARA-DFAM | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.40 |
| 2026-11-02-F1_ARA-AKPI | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| 2026-11-02-F1_ARA-ROCK | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| US-2026-11-02-G2_RET30-SEGG | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=1/0.00, BEATS_TWINS_1=1/0.50 |
| US-2026-11-02-G2_RET30-INLF | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=1/0.00, BEATS_TWINS_1=1/0.50 |
| US-2026-11-02-G2_RET30-CLRO | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| US-2026-11-02-G2_RET30-HXHX | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| US-2026-11-02-G2_RET30-INO | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.40 |
| US-2026-11-02-G2_RET30-IFBD | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.25, UP10_1=1/0.00, BEATS_TWINS_1=1/0.50 |
| US-2026-11-02-G2_RET30-GNTA | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=1/0.33, BEATS_TWINS_1=1 |
| US-2026-11-02-G2_RET30-PERI | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=1/0.60 |
| US-2026-11-02-G2_RET30-EVGO | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| US-2026-11-02-G2_RET30-NMRA | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.00, UP10_1=1/0.00, BEATS_TWINS_1=1/0.60 |
| US-2026-11-02-G2_RET30-VCIG | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=1/0.20, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| US-2026-11-02-G2_RET30-MF | NEXT1 | RESOLVED | PATH | n/a | n/a | n/a | DOWN10_1=0/0.20, UP10_1=0/0.00, BEATS_TWINS_1=0/0.60 |
| CRYPTO-2026-10-28-G2_RET30-INIT | BASE5 | RESOLVED | TRADED | -43.66% | -9.33% | -34.34% | RUN30_5=0/0.20, FADE10_5=1/0.60, GAIN0_5=0/0.20, BEATS_TWINS_5=0/0.40 |

