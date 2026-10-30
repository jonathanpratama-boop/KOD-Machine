# Speculation Register (KOD-SPEC-REGISTER-v1.1, protocol sha256 b0e9b6d9b533)

Generated 2026-10-30T10:52:25Z from `paper/speculations.jsonl`: 38 sets sealed, 0 resolutions. Paper only; no orders. The register never changes a decision and runs no variant of a retired entry.

Windows: **BASE5**: the frozen plan: the validated harness plan, prospectively, beside twins; **PATH20**: the 20-session price path of the candidate and its twins; no plan; **NEXT1**: the next session's close of the candidate and its twins; no plan.

## IDX: 5 sets over 2 signal sessions (2026-10-29 .. 2026-10-30, 2.50 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.176 (validation trade sd 0.1967 (run 20261009T050040Z_MOONSHOT_E1_D1_v1.1), paired, / sqrt(sets per session)) | 697 | 112 | 28 | 24 |

PATH20 windows resolved: 0; NEXT1: 0.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |
| DOWN10_1 | 0 | | | | | | |
| UP10_1 | 0 | | | | | | |
| BEATS_TWINS_1 | 0 | | | | | | |

## US: 30 sets over 3 signal sessions (2026-10-27 .. 2026-10-29, 10.00 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.153 (validation trade sd 0.3429 (run 20261008T115656Z_MOONSHOT_E2_US_D1_v1), paired, / sqrt(sets per session)) | 530 | 85 | 22 | 6 |

PATH20 windows resolved: 0; NEXT1: 0.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |
| DOWN10_1 | 0 | | | | | | |
| UP10_1 | 0 | | | | | | |
| BEATS_TWINS_1 | 0 | | | | | | |

## CRYPTO: 3 sets over 3 signal sessions (2026-10-27 .. 2026-10-29, 1.00 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.493 (validation trade sd 0.3486 (run 20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1), paired, / sqrt(sets per session)) | 5469 | 875 | 219 | 60 |

PATH20 windows resolved: 0; NEXT1: 0.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |
| DOWN10_1 | 0 | | | | | | |
| UP10_1 | 0 | | | | | | |
| BEATS_TWINS_1 | 0 | | | | | | |

## Latest sealed sets (postcards from the future)

### US INLF (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-INLF` (PASS), bound to ledger record `900165238258`; set `9f5cec28530f`.
Signal close 0.265 (reference 0.18); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): RETO 0.6245, ONCO 0.586, VERI 0.67, ARBE 0.4327, ZENA 0.9235.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US PCLA (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-PCLA` (PASS), bound to ledger record `0c3777841eeb`; set `7acbd15fc28f`.
Signal close 11.1 (reference 5.965); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): ICCC 10.32, CCEL 5.185, SHPH 5.23, FSI 6.25, MPV 16.79.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US SGLY (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-SGLY` (PASS), bound to ledger record `aff6923083a1`; set `befc1c4c313c`.
Signal close 0.5049 (reference 0.36); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): EDBL 0.7597, RKTO 0.5156, AACG 0.65, EZGO 0.7462, MIRA 0.5716.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US JFIN (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-JFIN` (PASS), bound to ledger record `fe68bca54316`; set `ebfe94dc45f0`.
Signal close 1.72 (reference 1.25); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): LEXX 3.77, KXIN 2.09, EPOW 4.8, INTS 3.34, RNAZ 1.73.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US BURU (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-BURU` (PASS), bound to ledger record `db388f84e2ee`; set `e512943f13c8`.
Signal close 0.3717 (reference 0.172); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): ACH 0.233, CHRS 0.8984, CDT 0.077, HAIN 0.1232, YFOR 0.151.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US ADT (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-ADT` (PASS), bound to ledger record `cd89c6e0f00c`; set `154f4590fdc2`.
Signal close 9.87 (reference 7.41); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): VERX 14.86, REPL 17.39, TDOC 8.73, ABSI 12.1, CERT 11.2.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US GKOS (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-GKOS` (PASS), bound to ledger record `3a8dcb868894`; set `c0d0c89bc649`.
Signal close 242.48 (reference 181.43); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): LMT 643.59, DHT 25.08, EBAY 121.19, KDP 35.3, TFX 141.39.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US XCH (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-XCH` (PASS), bound to ledger record `75c4b8273f7b`; set `05763c43916a`.
Signal close 3.46 (reference 2.44); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): APYX 2.69, XTIA 1.11, MWYN 1.76, BLND 1.16, LHSW 4.82.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US NCPL (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-NCPL` (PASS), bound to ledger record `6081c5e0d47c`; set `951a04d19bbb`.
Signal close 1.78 (reference 1.1); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): OVID 2.56, ALEC 2.24, WOOF 2.59, EVH 4.25, REI 1.42.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### US KPLT (2026-10-29) - sealed 2026-10-29T23:00:35Z, cutoff 2026-10-30T13:30:00Z
Decision `SCAN-US-2026-10-29-G2_RET30-KPLT` (PASS), bound to ledger record `c890fb766ca1`; set `de755c4b7bcd`.
Signal close 12.52 (reference 9.1); entry: the next session's opening print.
Tag: 10 flags today vs trailing median 9.5 -> hot_day = True.
Twins (band+liq+mom+dd): MHF 6.56, BRCC 12.99, NIM 9.12, INGN 7.26, FORR 12.18.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |
| DOWN10_1: the close of s+1 is <= 0.90 x the signal close | 0.500 | NEXT1 |
| UP10_1: the close of s+1 is >= 1.10 x the signal close | 0.500 | NEXT1 |
| BEATS_TWINS_1: the s+1 close over the signal close exceeds the median of the twins' (at least 3 twins with a bar at s+1) | 0.500 | NEXT1 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); windows BASE5, PATH20, NEXT1.

### CRYPTO PARTI (2026-10-29) - sealed 2026-10-30T00:26:54Z, cutoff 2026-10-30T02:00:00Z
Decision `SCAN-CRYPTO-2026-10-29-G2_RET30-PARTI` (PASS), bound to ledger record `34dd0783f353`; set `f67b7b62de42`.
Signal close 0.0598 (reference 0.0388); entry: the Binance spot quote taken at sealing time (the harness used the next day's open); quote 0.0573 at 2026-10-30T00:26:57Z.
Tag: 1 flags today vs trailing median 1.0 -> hot_day = False.
Twins (band+liq+mom+dd): INIT 0.21817, 币安人生 0.5045, RUNE 0.619, OSMO 0.0466, AT 0.143.

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

### IDX KONI (2026-10-30) - sealed 2026-10-30T10:52:22Z, cutoff 2026-11-02T01:45:00Z
Decision `SCAN-2026-10-30-F1_ARA-KONI` (PASS), bound to ledger record `62006a318fb2`; set `0ca09931b7e3`.
Signal close 1940 (reference 1555.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 4 flags today vs trailing median 5.0 -> hot_day = False.
Twins (band+liq+mom): LFLO 680, DAYA 1200, OMRE 950, GUNA 212, SKBM 484.

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

### IDX POLI (2026-10-30) - sealed 2026-10-30T10:52:22Z, cutoff 2026-11-02T01:45:00Z
Decision `SCAN-2026-10-30-F1_ARA-POLI` (PASS), bound to ledger record `50ac7e20bc4e`; set `acc44ccd2e0b`.
Signal close 830 (reference 665.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 4 flags today vs trailing median 5.0 -> hot_day = False.
Twins (band+liq+mom): CSAP 264, ASDM 490, DAYA 1200, DUTI 4700, PRAY 710.

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

### IDX ALKA (2026-10-30) - sealed 2026-10-30T10:52:22Z, cutoff 2026-11-02T01:45:00Z
Decision `SCAN-2026-10-30-F1_ARA-ALKA` (PASS), bound to ledger record `3873d69ee2b7`; set `e1a1020166a5`.
Signal close 5525 (reference 4420.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 4 flags today vs trailing median 5.0 -> hot_day = False.
Twins (band): LIFE 9000, INDF 6400, INKP 6575, EMAS 5450, MLBI 6150.

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

