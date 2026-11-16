# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-16T12:11:17Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 26 (FIRE 9, ABSTAIN 17) over 9 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 14, SEALED 26, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 5, SKIP_REPEAT_90D 1; coverage gaps 1.

| Class | Paired | Sessions | Mean net | Mean diff vs twins | t | p (one-sided) |
|---|---|---|---|---|---|---|
| FIRE | 0 | 0 | n/a | n/a | n/a | n/a |
| ABSTAIN | 0 | 0 | n/a | n/a | n/a | n/a |

Primaries (`research/CATALYST_REGISTER_v1/prereg_2.json`), looks at [60, 120, 240, 480, 960, 1920] FIRE pairs, t at least [3.75, 3.0, 3.0, 3.0, 3.0, 3.0]:
- MEAN (plan net minus twins' mean): **accumulating (no look reached)**
- WIN_RATE (plan beats twins' median): 0 of 0 (n/a), t n/a: **accumulating (no look reached)**

## IDX_INDEX (descriptive)

Sets 14 over 1 sessions.

- RUNUP: paired 14, mean signed diff +1.16%, share with the flow 64%
- POST20: paired 0, mean signed diff n/a, share with the flow n/a

## DILUTION_8K (counted at each look; direction -1; `KOD-CATALYST-FAMILY-DILUTION_8K-v1`)

Sets 48 over 9 signal sessions; events seen: SEALED 48, SKIP_REPEAT_90D 42, SKIP_NO_TICKER 25, SKIP_NOT_IN_UNIVERSE 27, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 139 over 7 signal sessions; events seen: SEALED 139, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 5649, SKIP_LATE 41, SKIP_NO_TICKER 4, SKIP_NOT_OPERATING 3, SKIP_REPEAT_90D 25; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 112 over 6 signal sessions; events seen: SEALED 112; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 41, FIRE 71
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 24 over 8 signal sessions; events seen: SEALED 24; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 13, FIRE 11
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_FIRE: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## DOCUMENT_CLASS (pooled, pre-registered; `KOD-CATALYST-REGISTER-v1-PREREG-3-DOCUMENT-CLASS`)

Families SEC13D, DILUTION_8K, FORM4, parents only, one record per set; the paired excess signed by direction; window H20, FIRE sets.
- MEAN (signed edge over the twins) n/a over 0 pairs in 0 sessions: **accumulating (no look reached)**
- Win rate (descriptive, never a primary): none yet
- By family: SEC13D 0 (n/a), DILUTION_8K 0 (n/a), FORM4 0 (n/a)
- By price band: close_ge_20 0 (n/a), close_lt_20 0 (n/a), close_unknown 0 (n/a)

## Calibration

| Family | Statement | n | Realised | Mean prior | Twins | Brier | Brier at 0.5 |
|---|---|---|---|---|---|---|---|
| SEC13D | GAIN0_20 | 0 | | | | | |
| SEC13D | BEATS_TWINS_20 | 0 | | | | | |
| SEC13D | FADE10_20 | 0 | | | | | |
| SEC13D | RUN30_20 | 0 | | | | | |
| IDX_INDEX | WITH_FLOW_RUNUP | 14 | 0.64 | 0.50 | n/a | 0.250 | 0.250 |
| IDX_INDEX | REVERSAL_POST20 | 0 | | | | | |
| DILUTION_8K | LOSES_TO_TWINS_20 | 0 | | | | | |
| DILUTION_8K | GAIN0_20 | 0 | | | | | |
| DILUTION_8K | FADE10_20 | 0 | | | | | |
| DILUTION_8K | RUN30_20 | 0 | | | | | |
| FORM4 | BEATS_TWINS_20 | 0 | | | | | |
| FORM4 | GAIN0_20 | 0 | | | | | |
| FORM4 | FADE10_20 | 0 | | | | | |
| FORM4 | RUN30_20 | 0 | | | | | |
| FORM4_SHARP | BEATS_TWINS_60 | 0 | | | | | |
| FORM4_SHARP | GAIN0_60 | 0 | | | | | |
| FORM4_SHARP | BEATS_TWINS_20 | 0 | | | | | |
| FORM4_SHARP | GAIN0_20 | 0 | | | | | |
| FORM4_SHARP | FADE10_20 | 0 | | | | | |
| FORM4_SHARP | RUN30_20 | 0 | | | | | |
| FORM4_SHARP | MECH_SECOND_BUY_20 | 0 | | | | | |
| SEC13D_V2 | GAIN0_20 | 0 | | | | | |
| SEC13D_V2 | BEATS_TWINS_20 | 0 | | | | | |
| SEC13D_V2 | FADE10_20 | 0 | | | | | |
| SEC13D_V2 | RUN30_20 | 0 | | | | | |
| SEC13D_V2 | GAIN0_60 | 0 | | | | | |
| SEC13D_V2 | BEATS_TWINS_60 | 0 | | | | | |
| SEC13D_V2 | MECH_13DA_UP_60 | 0 | | | | | |

## DILUTION_RECENT tags on Speculation Register sets

209 tags: 50 true, 0 unknown.

## Latest sets

### FORM4 FCPT (Four Corners Property Trust, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001193125-26-460757`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 23.32 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-460757` (1 filing(s)) by Lenehan William H (President and CEO).
Coverage **FIRE**; purchases USD 149,992, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): EPAC 39.37, BETA 23.33, SDGR 29.53, NBR 84.68, APAM 38.43.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TRIN (Trinity Capital Inc.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001193125-26-460772`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 17.7 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-460772` (1 filing(s)) by Brown Kyle Steven (CEO, President and CIO).
Coverage **FIRE**; purchases USD 58,000, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): LION 14.03, VYX 10.48, OLN 17.46, AQN 5.6, LBTYA 10.77.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 WY (WEYERHAEUSER CO) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001197193-26-000008`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 20.81 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001197193-26-000008` (1 filing(s)) by BECKWITT RICHARD (director).
Coverage **FIRE**; purchases USD 306,600, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): DKS 149.7, WYNN 85.06, SPHR 125.56, KRMN 40.66, LVS 40.39.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NGS (NATURAL GAS SERVICES GROUP INC) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001236849-26-000015`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 29.7 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001236849-26-000015` (1 filing(s)) by JACKSON JOHN EARL (director).
Coverage **FIRE**; purchases USD 57,790, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): RDVT 73.57, SMC 30.69, BFS 28.37, PLOW 37.44, BLX 50.55.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FF (FutureFuel Corp.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001437749-26-036877`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 2.9 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001437749-26-036877` (2 filing(s)) by Polet Roeland (Chief Executive Officer), Bedell Donald C. (director).
Coverage **FIRE**; purchases USD 249,266, owners 2, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): ADTN 4.83, LWLG 3.21, DDD 1.53, KDK 1.11, DFDV 3.035.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 LPCN (Lipocine Inc.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001493152-26-051673`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 1.71 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001493152-26-051673` (1 filing(s)) by Patel Mahesh V. (Chief Executive Officer).
Coverage **FIRE**; purchases USD 79,488, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): PMVP 1.27, RGP 2.67, PRLD 3.45, WHWK 3.06, OMH 5.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NXGL (NEXGEL, INC.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001493152-26-051920`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 3.88 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001493152-26-051920` (1 filing(s)) by Kieser Brian Joseph (Interim CEO).
Coverage **FIRE**; purchases USD 732,688, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): TORO 3.81, UPC 1.51, PAVM 1.63, EZGO 1.57, KTCC 1.3.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CRVS (Corvus Pharmaceuticals, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001610717-26-000454`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 10.64 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001610717-26-000454` (1 filing(s)) by Arcara Jeffrey (Chief Business Officer).
Coverage **FIRE**; purchases USD 50,475, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): RXST 5.32, OPRT 11.73, LOVE 15.14, WBTN 9.85, KRRO 13.61.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CTEV (Claritev Corp) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001628280-26-073944`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 26.82 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-073944` (1 filing(s)) by Dalton Travis (Pres., CEO & Executive Chair).
Coverage **FIRE**; purchases USD 149,927, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): NBTX 30.655, DMRA 21.6, TYRA 20.025, GIBO 75.65, ASMB 21.12.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BW (Babcock & Wilcox Enterprises, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001630805-26-000089`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 4.56 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001630805-26-000089` (1 filing(s)) by Tato Joseph A (director).
Coverage **FIRE**; purchases USD 52,692, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): GT 4.12, LCID 2.955, NUAI 3.2, ORC 4.68, DCH 4.69.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 UPST (Upstart Holdings, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001832812-26-000012`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 19.56 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001832812-26-000012` (1 filing(s)) by Gu Paul (Chief Executive Officer).
Coverage **FIRE**; purchases USD 1,028,400, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): CDE 13.98, FSLY 16.62, RGTI 9.62, PBR 18.34, IBRX 6.02.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ABCL (AbCellera Biologics Inc.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001834411-26-000010`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 11.49 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001834411-26-000010` (1 filing(s)) by Booth Andrew (Chief Financial Officer).
Coverage **FIRE**; purchases USD 97,438, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): BBNX 16.42, GENI 6.26, HTGC 15.87, EFC 11.11, VIR 9.96.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CTRI (Centuri Holdings, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0001981599-26-000139`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 21.82 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0001981599-26-000139` (2 filing(s)) by MARIUCCI ANNE L (director), Patton Charles R. (director).
Coverage **FIRE**; purchases USD 349,910, owners 2, top executive no, lag 2 days.
Twins (band+liq+mom+dd): SBRA 20.44, HTO 60.56, ULS 80.36, MGNI 29.29, EXPO 87.31.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 KEEL (Keel Infrastructure Corp.) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0002115914-26-000003`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 1.86 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0002115914-26-000003` (1 filing(s)) by Freedman Amy (director).
Coverage **FIRE**; purchases USD 76,100, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): INTR 4.15, CYPH 1.87, SATL 3.3, NUVB 3.99, PONY 4.46.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CRESY (CRESUD INC) - filed 2026-11-13, sealed 2026-11-16T12:10:50Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4-0002119764-26-000036`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 9.74 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Form 4 `0002119764-26-000036` (1 filing(s)) by Elsztain Alejandro Gustavo (director).
Coverage **FIRE**; purchases USD 89,000, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): SD 13.04, MTRX 9.19, TTAM 11.25, PAYP 14.35, USNA 13.24.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

