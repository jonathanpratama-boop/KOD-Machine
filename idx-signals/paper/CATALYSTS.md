# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-17T10:34:31Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 31 (FIRE 11, ABSTAIN 20) over 10 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 14, SEALED 31, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 5, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 57 over 10 signal sessions; events seen: SEALED 57, SKIP_REPEAT_90D 46, SKIP_NO_TICKER 25, SKIP_NOT_IN_UNIVERSE 30, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 168 over 8 signal sessions; events seen: SEALED 168, SKIP_NOT_IN_UNIVERSE 6, SKIP_NOT_PURCHASE 6214, SKIP_LATE 41, SKIP_NO_TICKER 4, SKIP_NOT_OPERATING 3, SKIP_REPEAT_90D 39; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 139 over 7 signal sessions; events seen: SEALED 139; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 52, FIRE 87
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 29 over 9 signal sessions; events seen: SEALED 29; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 16, FIRE 13
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

226 tags: 55 true, 0 unknown.

## Latest sets

### FORM4 BRSP (BrightSpire Capital, Inc.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001598424-26-000011`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 3.27 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001598424-26-000011` (1 filing(s)) by Mazzei Michael (CEO).
Coverage **FIRE**; purchases USD 1,000,180, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): WRD 3.98, EH 3.4, VNDA 3.81, WVE 2.87, RCKT 2.16.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TLSI (TriSalus Life Sciences, Inc.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001628280-26-074009`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 2.27 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074009` (1 filing(s)) by Wahlstrom Mats (director).
Coverage **FIRE**; purchases USD 112,000, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): USGO 4.55, SUPX 4.41, BDTX 1.53, HURA 1.33, AVAT 1.05.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 OPAL (OPAL Fuels Inc.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001628280-26-074148`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.21 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074148` (1 filing(s)) by Sutton Scott McDougald (director).
Coverage **FIRE**; purchases USD 61,500, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): ADCT 1.25, SXTC 2.99, GMTL 4.1, NAKA 4.59, DAVA 1.4.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 REI (RING ENERGY, INC.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001628280-26-074217`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.11 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074217` (1 filing(s)) by Johl Sundip Singh (EVP, Chief Financial Officer).
Coverage **FIRE**; purchases USD 70,087, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): NXDR 2.04, CIG 1.86, AMPY 4.03, AIOT 2.22, NUS 3.93.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TG (TREDEGAR CORP) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001628280-26-074262`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 5.64 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074262` (1 filing(s)) by DasGupta Arijit (See Remarks).
Coverage **FIRE**; purchases USD 96,730, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): NATR 10.56, USCB 19.78, INGN 5.63, AGCC 13.52, MFIN 9.4.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PED (PEDEVCO CORP) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001654954-26-009873`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 10.76 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001654954-26-009873` (1 filing(s)) by Howie John K (director).
Coverage **FIRE**; purchases USD 53,000, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): USAU 9.87, AKTX 6.51, MAKO 6.91, HQI 13.52, PTHS 7.15.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 YUMC (Yum China Holdings, Inc.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001673358-26-000169`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 51.45 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001673358-26-000169` (1 filing(s)) by DIMITRIEF ALEXANDER (director).
Coverage **FIRE**; purchases USD 247,500, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): CMCSA 25.6, JXN 137.59, CUBE 44.85, ED 121.88, FE 47.55.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ADIG (ADI GLOBAL DISTRIBUTION INC.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001753285-26-000006`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 9.3 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001753285-26-000006` (4 filing(s)) by Lane Jeannine J (Exec. VP, GC, Corp. Sec. & CCO), Aarnes Robert B (President and CEO), Carlet Michael (Executive VP, CFO), Copeland Alicia Crispin (Executive VP and COO).
Coverage **FIRE**; purchases USD 300,523, owners 4, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): SSYS 5.82, GLUE 9.16, CPS 18.21, CLB 8.45, HPK 7.8.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 AOMR (Angel Oak Mortgage REIT, Inc.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001766478-26-000074`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 5.59 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001766478-26-000074` (1 filing(s)) by MINAMI W D (director).
Coverage **FIRE**; purchases USD 53,255, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): PMI 7.24, ENHA 5.86, AEHL 7.6, NREF 11.34, LMNR 9.89.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 IMRX (Immuneering Corp) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001790340-26-000105`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 3.52 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001790340-26-000105` (1 filing(s)) by Gengos Andrew (Chief Financial Officer).
Coverage **FIRE**; purchases USD 89,500, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): PACK 3.08, CCCC 2.65, RXT 2.515, VZLA 2.93, QSI 1.06.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 KTOS (KRATOS DEFENSE & SECURITY SOLUTIONS, INC.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001803860-26-000005`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 31.66 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001803860-26-000005` (1 filing(s)) by King David Arnold (director).
Coverage **FIRE**; purchases USD 201,091, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): WDC 280.93, OKLO 23.03, PAAS 35.58, ASX 32.8, SANM 153.815.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 GERN (GERON CORP) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001809747-26-000002`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 0.9419 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001809747-26-000002` (1 filing(s)) by Semerjian Harout (President & CEO).
Coverage **FIRE**; purchases USD 50,825, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): SLNH 0.4571, IQ 0.6801, AKBA 0.4486, RR 0.7395, JDZG 0.1389.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PCT (PureCycle Technologies, Inc.) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001847066-26-000009`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.68 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001847066-26-000009` (1 filing(s)) by Musa Fernando (Executive Chairman).
Coverage **FIRE**; purchases USD 98,496, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): POET 4.66, FLNC 4.29, NAUT 2.1, ENVX 1.42, KOS 2.06.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 HL (HECLA MINING CO/DE/) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0001866675-26-000007`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 12.22 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0001866675-26-000007` (1 filing(s)) by Andres Dale (director).
Coverage **FIRE**; purchases USD 125,000, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): FSLY 15.86, CLSK 6.3, KGC 19.94, AG 12.67, UMC 14.34.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 LEGN (Legend Biotech Corp) - filed 2026-11-16, sealed 2026-11-17T10:33:59Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4-0002088468-26-000008`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 15.99 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Form 4 `0002088468-26-000008` (1 filing(s)) by Salovey Peter (director).
Coverage **FIRE**; purchases USD 183,250, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): STNE 8.01, LBRT 12.25, MBLY 5.26, UMAC 10.59, MLYS 14.53.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

