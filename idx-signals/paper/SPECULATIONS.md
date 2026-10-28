# Speculation Register (KOD-SPEC-REGISTER-v1, protocol sha256 c0ec3bbfa948)

Generated 2026-10-28T00:27:02Z from `paper/speculations.jsonl`: 6 sets sealed, 0 resolutions. Paper only; no orders. The register never changes a decision and runs no variant of a retired entry.

Windows: **BASE5**: the frozen plan: the validated harness plan, prospectively, beside twins; **PATH20**: the 20-session price path of the candidate and its twins; no plan.

## IDX: 0 sets over 0 signal sessions

No set sealed yet.

## US: 5 sets over 1 signal sessions (2026-10-27 .. 2026-10-27, 5.00 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.217 (validation trade sd 0.3429 (run 20261008T115656Z_MOONSHOT_E2_US_D1_v1), paired, / sqrt(sets per session)) | 1059 | 170 | 43 | 12 |

PATH20 windows resolved: 0.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |

## CRYPTO: 1 sets over 1 signal sessions (2026-10-27 .. 2026-10-27, 1.00 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.493 (validation trade sd 0.3486 (run 20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1), paired, / sqrt(sets per session)) | 5469 | 875 | 219 | 60 |

PATH20 windows resolved: 0.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |

## Latest sealed sets (postcards from the future)

### US NUWE (2026-10-27) - sealed 2026-10-27T23:56:46Z, cutoff 2026-10-28T13:30:00Z
Decision `SCAN-US-2026-10-27-G2_RET30-NUWE` (PASS), bound to ledger record `9bc28e120ecc`; set `b94611ff6709`.
Signal close 5.41 (reference 3.0654); entry: the next session's opening print.
Tag: 5 flags today vs trailing median 9.5 -> hot_day = False.
Twins (band+liq+mom+dd): SKIL 5.17, CUVL 5.02, PCLA 6, PLRZ 8.58, AIOS 9.9.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US BRAI (2026-10-27) - sealed 2026-10-27T23:56:46Z, cutoff 2026-10-28T13:30:00Z
Decision `SCAN-US-2026-10-27-G2_RET30-BRAI` (PASS), bound to ledger record `88ff6ff68aca`; set `66e59c601878`.
Signal close 3.31 (reference 2.12); entry: the next session's opening print.
Tag: 5 flags today vs trailing median 9.5 -> hot_day = False.
Twins (band+liq+mom+dd): YQ 3, TRNR 1.6, DWSN 2.04, NXB 1.58, CXAI 1.75.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US AEYE (2026-10-27) - sealed 2026-10-27T23:56:46Z, cutoff 2026-10-28T13:30:00Z
Decision `SCAN-US-2026-10-27-G2_RET30-AEYE` (PASS), bound to ledger record `7c9eda0f68f6`; set `8869c188de9e`.
Signal close 10.14 (reference 7.42); entry: the next session's opening print.
Tag: 5 flags today vs trailing median 9.5 -> hot_day = False.
Twins (band+liq+mom+dd): FCBM 12.97, PMO 9.89, HCKT 12.19, DGICA 18.84, DPG 13.8.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US MBRX (2026-10-27) - sealed 2026-10-27T23:56:46Z, cutoff 2026-10-28T13:30:00Z
Decision `SCAN-US-2026-10-27-G2_RET30-MBRX` (PASS), bound to ledger record `29443c6573de`; set `741017a83e3c`.
Signal close 9.265 (reference 7.085); entry: the next session's opening print.
Tag: 5 flags today vs trailing median 9.5 -> hot_day = False.
Twins (band+liq+mom+dd): BBGI 6.85, NTRB 5.95, HCTI 6.8, PLRZ 8.58, PHOE 15.37.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US OWLS (2026-10-27) - sealed 2026-10-27T23:56:46Z, cutoff 2026-10-28T13:30:00Z
Decision `SCAN-US-2026-10-27-G2_RET30-OWLS` (PASS), bound to ledger record `7ab234f5a991`; set `6b56bcf51e6e`.
Signal close 2.66 (reference 2.04); entry: the next session's opening print.
Tag: 5 flags today vs trailing median 9.5 -> hot_day = False.
Twins (band+liq+mom+dd): MLGO 2.62, RMCO 2.21, POAS 1.245, MTR 1.925, XPON 3.7.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### CRYPTO HAEDAL (2026-10-27) - sealed 2026-10-28T00:26:56Z, cutoff 2026-10-28T02:00:00Z
Decision `SCAN-CRYPTO-2026-10-27-G2_RET30-HAEDAL` (PASS), bound to ledger record `f996464c890d`; set `6aa9edb1877f`.
Signal close 0.02977 (reference 0.02132); entry: the Binance spot quote taken at sealing time (the harness used the next day's open); quote 0.02808 at 2026-10-28T00:26:57Z.
Tag: 1 flags today vs trailing median 1.0 -> hot_day = False.
Twins (band+liq+mom+dd): MIRA 0.04579, SOMI 0.1826, SHELL 0.02378, LISTA 0.0797, NEXO 0.802.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.185 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.511 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.314 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

