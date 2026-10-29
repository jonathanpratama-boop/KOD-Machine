# Speculation Register (KOD-SPEC-REGISTER-v1, protocol sha256 c0ec3bbfa948)

Generated 2026-10-29T10:35:30Z from `paper/speculations.jsonl`: 24 sets sealed, 0 resolutions. Paper only; no orders. The register never changes a decision and runs no variant of a retired entry.

Windows: **BASE5**: the frozen plan: the validated harness plan, prospectively, beside twins; **PATH20**: the 20-session price path of the candidate and its twins; no plan.

## IDX: 2 sets over 1 signal sessions (2026-10-29 .. 2026-10-29, 2.00 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.197 (validation trade sd 0.1967 (run 20261009T050040Z_MOONSHOT_E1_D1_v1.1), paired, / sqrt(sets per session)) | 871 | 140 | 35 | 30 |

PATH20 windows resolved: 0.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |

## US: 20 sets over 2 signal sessions (2026-10-27 .. 2026-10-28, 10.00 sets per scan)

| Plan | Resolved | Traded | Paired | Sessions | Mean net | Median net | Twins net | Diff | t | p | Look | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BASE5 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | - / next 60 | accumulating (no look reached) |

Projection (labelled): sessions of resolved sets needed for t >= 3 if the true paired effect were 2, 5 or 10 points per set, and sessions to the next look at the current candidate rate.

| sd per session (source) | 2pt | 5pt | 10pt | to next look |
|---|---:|---:|---:|---:|
| 0.153 (validation trade sd 0.3429 (run 20261008T115656Z_MOONSHOT_E2_US_D1_v1), paired, / sqrt(sets per session)) | 530 | 85 | 22 | 6 |

PATH20 windows resolved: 0.

| Statement | Graded | Realised rate | Twins' rate | Mean prior | Brier (register) | Brier (0.5) | Brier (running) |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUN30_5 | 0 | | | | | | |
| FADE10_5 | 0 | | | | | | |
| GAIN0_5 | 0 | | | | | | |
| BEATS_TWINS_5 | 0 | | | | | | |
| RUN30_20 | 0 | | | | | | |
| DOUBLE_20 | 0 | | | | | | |

## CRYPTO: 2 sets over 2 signal sessions (2026-10-27 .. 2026-10-28, 1.00 sets per scan)

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

### US CHSN (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-CHSN` (PASS), bound to ledger record `ec77a5043e1b`; set `44d79010309b`.
Signal close 1.46 (reference 1.08); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): IBG 1.02, ASRV 4.9, KMRK 1.6, JYD 2.09, JCSE 1.7.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US FTFT (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-FTFT` (PASS), bound to ledger record `eec20459f2f5`; set `2fa31d0f6487`.
Signal close 2.89 (reference 1.86); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): TRVG 3.85, ARTL 2.33, NTRP 1.41, XTLB 2.01, QXL 3.7.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US ROMA (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-ROMA` (PASS), bound to ledger record `92911cbade26`; set `16291c4b49b7`.
Signal close 7 (reference 4.69); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): FGI 7.18, NTRB 6.4, LFWD 5.75, PLRZ 8.61, NRDY 5.77.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US ULBI (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-ULBI` (PASS), bound to ledger record `87f3977788ee`; set `8f92a73e266f`.
Signal close 15.61 (reference 6.36); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): ARL 17.51, TACT 5.5, GRX 10.015, FEDU 11.495, FGBI 9.35.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US PODC (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-PODC` (PASS), bound to ledger record `e8c6ff057405`; set `ff316904ecfe`.
Signal close 2.45 (reference 1.8); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): PCSA 1.85, MB 4.12, OMH 2.96, INHD 4.07, PRPL 3.29.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US BOOM (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-BOOM` (PASS), bound to ledger record `38e7b35cb9b1`; set `55e2a9d53717`.
Signal close 7.73 (reference 5.35); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): JRSH 5.97, LCNB 19.64, WFCF 15.88, RLGT 9.04, MMD 14.02.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US KPTI (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-KPTI` (PASS), bound to ledger record `5b971c06aa18`; set `872b748b88ed`.
Signal close 0.8321 (reference 0.48); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): WHLR 0.2688, SLQT 0.3637, TGL 0.2578, ORGO 0.8247, BLNK 0.4088.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US GIFT (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-GIFT` (PASS), bound to ledger record `1de1519a0440`; set `20361f60ac33`.
Signal close 0.63 (reference 0.442); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): CCHH 0.9998, MYND 0.34, ELOG 0.863, REED 0.7389, SNES 0.97.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US PDC (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-PDC` (PASS), bound to ledger record `f9c8e72cc539`; set `1ba53aa3ffae`.
Signal close 2.92 (reference 2.04); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): DUKR 4.1, KLRS 2.01, VIP 1.325, DCOY 1.1, AUXX 4.17.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US AXGN (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-AXGN` (PASS), bound to ledger record `9b78babd27aa`; set `a7491b35404f`.
Signal close 49.25 (reference 37.46); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): TAK 20.15, AROC 31.86, FIVN 37.63, CXT 58.29, CRAI 192.84.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US ADIL (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-ADIL` (PASS), bound to ledger record `c0f334ead8a2`; set `fa8a6d8d0683`.
Signal close 5.05 (reference 3.71); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): FVN 12.06, CCG 7.85, NINE 8.14, VHC 10.8834, AIFU 10.41.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US BEAT (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-BEAT` (PASS), bound to ledger record `2bde1501aeb6`; set `9fbc0acc192b`.
Signal close 0.5318 (reference 0.4); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom): PROP 0.4477, ESLA 0.8217, XHLD 0.97, LDI 0.6179, JZ 0.995.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US PARA (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-PARA` (PASS), bound to ledger record `8bbdee60642f`; set `d5a71cab8363`.
Signal close 3.36 (reference 0.425); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): JYD 2.09, JCSE 1.7, IBG 1.02, INM 1.5992, OIO 1.95.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US SCAG (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-SCAG` (PASS), bound to ledger record `552bd490c072`; set `281513ee72c6`.
Signal close 2.15 (reference 0.161); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): JYD 2.09, MWG 1.48, HMR 1.85, INM 1.5992, ASRV 4.9.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### US ENLV (2026-10-28) - sealed 2026-10-28T23:02:37Z, cutoff 2026-10-29T13:30:00Z
Decision `SCAN-US-2026-10-28-G2_RET30-ENLV` (PASS), bound to ledger record `ff9191149c58`; set `a26e13ff4b82`.
Signal close 2.61 (reference 0.173); entry: the next session's opening print.
Tag: 15 flags today vs trailing median 9.0 -> hot_day = True.
Twins (band+liq+mom+dd): HMR 1.85, MAMO 1.045, BRLT 1.55, DLTH 4.23, BRIA 1.46.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.154 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.403 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.425 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### CRYPTO INIT (2026-10-28) - sealed 2026-10-29T00:27:43Z, cutoff 2026-10-29T02:00:00Z
Decision `SCAN-CRYPTO-2026-10-28-G2_RET30-INIT` (PASS), bound to ledger record `2b3f2537d3da`; set `e67ed656f66a`.
Signal close 0.22316 (reference 0.16619); entry: the Binance spot quote taken at sealing time (the harness used the next day's open); quote 0.21769 at 2026-10-29T00:27:46Z.
Tag: 1 flags today vs trailing median 1.0 -> hot_day = False.
Twins (band+liq+mom+dd): PARTI 0.0388, DODO 0.0244, IO 0.1516, AXL 0.0488, AT 0.1436.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.185 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.511 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.314 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### IDX YPAS (2026-10-29) - sealed 2026-10-29T10:35:28Z, cutoff 2026-10-30T01:45:00Z
Decision `SCAN-2026-10-29-F1_ARA-YPAS` (PASS), bound to ledger record `d71d086097e6`; set `b32758e651be`.
Signal close 1055 (reference 845.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 3 flags today vs trailing median 5.5 -> hot_day = False.
Twins (band+liq+mom+dd): ITMA 1070, SIPD 615, TALF 580, GMTD 820, LION 258.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.183 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.359 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.311 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

### IDX ALKA (2026-10-29) - sealed 2026-10-29T10:35:28Z, cutoff 2026-10-30T01:45:00Z
Decision `SCAN-2026-10-29-F1_ARA-ALKA` (PASS), bound to ledger record `a1368533b604`; set `96f608acc6a4`.
Signal close 4420 (reference 3540.0); entry: the next session's closing auction, if traded and not locked at ARA.
Tag: 3 flags today vs trailing median 5.5 -> hot_day = False.
Twins (band+liq+mom+dd): NICL 224, KDTN 260, DATA 955, WBSA 474, FILM 322.

| Statement | Prior | Resolves with |
|---|---:|---|
| RUN30_5: a close in s+1..s+5 is >= 1.30 x the signal close | 0.183 | BASE5 |
| FADE10_5: the BASE5 net return is <= -0.10 | 0.359 | BASE5 |
| GAIN0_5: the BASE5 net return is > 0 | 0.311 | BASE5 |
| BEATS_TWINS_5: the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.500 | BASE5 |
| RUN30_20: a close in s+1..s+20 is >= 1.30 x the signal close | 0.500 | PATH20 |
| DOUBLE_20: a close in s+1..s+20 is >= 2.00 x the signal close | 0.500 | PATH20 |

Plan: BASE5 (the frozen plan: the validated harness plan, prospectively, beside twins); path window PATH20.

