# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-19T10:35:19Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 34 (FIRE 13, ABSTAIN 21) over 12 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 17, SEALED 34, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 66 over 12 signal sessions; events seen: SEALED 66, SKIP_REPEAT_90D 51, SKIP_NO_TICKER 29, SKIP_NOT_IN_UNIVERSE 41, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 215 over 10 signal sessions; events seen: SEALED 215, SKIP_NOT_IN_UNIVERSE 8, SKIP_NOT_PURCHASE 7906, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 7, SKIP_REPEAT_90D 61; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 189 over 9 signal sessions; events seen: SEALED 189; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 75, FIRE 114
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 32 over 11 signal sessions; events seen: SEALED 32; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 17, FIRE 15
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

263 tags: 63 true, 0 unknown.

## Latest sets

### FORM4 PAL (Proficient Auto Logistics, Inc) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001213900-26-121624`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 2.96 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-121624` (2 filing(s)) by Gattoni James B (director), Lal Rohit (director).
Coverage **FIRE**; purchases USD 244,200, owners 2, top executive no, lag 2 days.
Twins (band+liq+mom+dd): ARMP 3.17, HTCO 1.31, FTFT 3.76, XCH 3.34, PZG 1.02.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 RILY (BRC Group Holdings, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001213900-26-121662`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 3.03 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-121662` (1 filing(s)) by RILEY BRYANT R (Chairman and Co-CEO).
Coverage **FIRE**; purchases USD 116,767, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): CTMX 1.88, CCCC 2.475, JBI 3.23, DFDV 2.61, ACDC 2.84.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 XTIA (XTI Aerospace, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001213900-26-121959`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 0.8801 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-121959` (1 filing(s)) by Evans Allan Thomas (director).
Coverage **FIRE**; purchases USD 86,874, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): IBIO 0.8481, LUCD 0.4095, CRMT 0.8291, CRIS 0.6143.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BA (BOEING CO) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001225208-26-009059`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 162.91 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001225208-26-009059` (1 filing(s)) by JOHRI AKHIL (director).
Coverage **FIRE**; purchases USD 500,067, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): HTFL 45.89, NTAP 172.19, IT 178.84, SHOP 140.42, RVMD 159.82.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FLNA (FILANA THERAPEUTICS, INC.) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001437749-26-037544`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 0.545 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001437749-26-037544` (2 filing(s)) by Cook Robert Christopher (Chief Operating& Legal Officer), Barry Richard (President & CEO).
Coverage **FIRE**; purchases USD 262,821, owners 2, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): GLDG 0.6769, SOAR 0.1651, BZFD 0.4037, LDI 0.4445, QUCY 0.584.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 USAR (USA Rare Earth, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001458423-26-000012`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 6.56 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001458423-26-000012` (1 filing(s)) by BLITZER MICHAEL (director).
Coverage **FIRE**; purchases USD 2,996,645, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): CIFR 6.57, VALE 10.04, IBRX 6.7, EQX 9.17, PATH 11.73.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 VIVO (VivoPower PLC) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001493152-26-053023`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 1.82 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001493152-26-053023` (1 filing(s)) by Chin Kevin (Chairman & CEO).
Coverage **FIRE**; purchases USD 553,910, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): SRI 5, ADAG 1.82, HRZN 3.09, CNTN 1.335, MNTS 1.96.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 STXS (Stereotaxis, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001493152-26-053130`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 0.9461 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001493152-26-053130` (1 filing(s)) by Menawat Arun Swarup (director).
Coverage **FIRE**; purchases USD 99,984, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): ALDX 0.6711, CRDF 0.839, WWR 0.368, MRLN 0.8702, NPWR 0.9907.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CRC (California Resources Corp) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001609253-26-000163`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 44.61 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001609253-26-000163` (1 filing(s)) by Bremner Andrew B. (director).
Coverage **FIRE**; purchases USD 99,682, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): WK 66.43, TX 47.36, LIFE 32.54, ARQT 27.61, IDCC 276.58.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 EFC (Ellington Financial Inc.) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001628280-26-074680`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 10.81 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074680` (1 filing(s)) by Penn Laurence (CEO and President).
Coverage **FIRE**; purchases USD 106,540, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): TLK 11.71, FLG 10.26, PBI 15.18, CC 12.09, WU 6.23.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 DDD (3D SYSTEMS CORP) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001628280-26-074826`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 1.38 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074826` (1 filing(s)) by KEVER JIM D (director).
Coverage **FIRE**; purchases USD 572,000, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): CYH 1.86, SION 2.97, JMIA 2.74, WFF 1.02, BNC 3.39.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 GWRS (Global Water Resources, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001628280-26-074877`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 6.48 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074877` (1 filing(s)) by Cohn Andrew M. (director).
Coverage **FIRE**; purchases USD 169,910, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): AGBK 5.81, INGN 5.57, LGCY 7.88, AMWL 11.03, CPIX 6.57.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NTB (Bank of N.T. Butterfield & Son Ltd) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001653242-26-000144`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 54.83 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001653242-26-000144` (1 filing(s)) by Lynch Mark T (director).
Coverage **FIRE**; purchases USD 164,850, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): JILL 21.735, PKE 24.27, SMC 30.56, PLOW 37.09, YSWY 21.29.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TISI (TEAM INC) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0001782810-26-000011`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 24.43 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0001782810-26-000011` (1 filing(s)) by Hill Gary L. (Chief Executive Officer).
Coverage **FIRE**; purchases USD 96,096, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): ESEA 60.2, SEG 20.1, DJP 46.31, ARTNA 32.18, CMT 22.14.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 AROW (ARROW FINANCIAL CORP) - filed 2026-11-18, sealed 2026-11-19T10:34:43Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4-0002045771-26-000010`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 37.18 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20.
Form 4 `0002045771-26-000010` (1 filing(s)) by White Daniel James (director).
Coverage **FIRE**; purchases USD 99,837, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): AVBC 21.89, CCNE 34.56, GABC 48.52, BSVN 57.07, IMKTA 85.07.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

