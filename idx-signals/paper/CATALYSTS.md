# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-18T10:35:22Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 33 (FIRE 12, ABSTAIN 21) over 11 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 15, SEALED 33, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 5, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 61 over 11 signal sessions; events seen: SEALED 61, SKIP_REPEAT_90D 48, SKIP_NO_TICKER 26, SKIP_NOT_IN_UNIVERSE 32, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 189 over 9 signal sessions; events seen: SEALED 189, SKIP_NOT_IN_UNIVERSE 7, SKIP_NOT_PURCHASE 7202, SKIP_LATE 41, SKIP_NO_TICKER 4, SKIP_NOT_OPERATING 5, SKIP_REPEAT_90D 47; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 168 over 8 signal sessions; events seen: SEALED 168; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 66, FIRE 102
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 31 over 10 signal sessions; events seen: SEALED 31; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 17, FIRE 14
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

245 tags: 59 true, 0 unknown.

## Latest sets

### FORM4 ETN (Eaton Corp plc) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001104659-26-129065`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 337.11 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001104659-26-129065` (2 filing(s)) by Foster David B (See Remarks below.), Johnson Gerald (director).
Coverage **FIRE**; purchases USD 170,894, owners 2, top executive no, lag 1 days.
Twins (band+liq+mom+dd): SPCX 141.7, JBL 243.61, NKE 35.85, POWL 150.86, HRB 48.07.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PRAA (PRA GROUP INC) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001185352-26-000002`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 11.17 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001185352-26-000002` (1 filing(s)) by FREDRICKSON STEVEN D (director).
Coverage **FIRE**; purchases USD 295,000, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): FTH 9.04, PBYI 7.14, RYAM 5.18, ARCT 7.97, GRRR 6.49.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ITG (ITG, Inc./DE/) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001193125-26-465620`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 5.37 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-465620` (4 filing(s)) by LAPERCH WILLIAM G (director), Giacalone Peter (director), Parrott Andrew (Chief Executive Officer), Brooks Michael George (director).
Coverage **FIRE**; purchases USD 1,162,690, owners 4, top executive yes, lag 4 days.
Twins (band+liq+mom+dd): AKTS 16.31, EVMN 7.02, EAF 8.26, DBVT 9.99, ATTO 14.86.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 RMIX (Suncrete, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001193125-26-465843`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 6.05 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-465843` (1 filing(s)) by Fleming Ned N III (director).
Coverage **FIRE**; purchases USD 238,000, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): ALMU 5.68, MRAM 11.04, LAND 6.32, PAYS 9.81, OFIX 6.67.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 OPEN (Opendoor Technologies Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001195975-26-000007`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 1.18 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001195975-26-000007` (1 filing(s)) by HAMILTON DANA (director).
Coverage **FIRE**; purchases USD 241,990, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): PGEN 4.29, PLUG 1.05, RXRX 2.72, FRMI 2.41, KOS 2.03.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SSII (SS Innovations International, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001213900-26-121405`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 1.33 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-121405` (1 filing(s)) by Sudhir Srivastava (Chairman and CEO).
Coverage **FIRE**; purchases USD 300,000, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): SKIL 2.35, LUCK 4.17, YDES 4.73, ATLX 1.48, XNET 3.37.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PEPG (PepGen Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001231919-26-001588`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 3.88 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001231919-26-001588` (1 filing(s)) by RA CAPITAL MANAGEMENT, L.P. (director), RA Capital Healthcare Fund LP (director), RA Capital Nexus Fund II, L.P. (director), Kolchinsky Peter (director), Shah Rajeev M. (director).
Coverage **FIRE**; purchases USD 43,125,000, owners 5, top executive no, lag 4 days.
Twins (band+liq+mom+dd): ACB 4.52, SABR 1.68, TOYO 4.205, SFIX 2.8, CLNE 1.63.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SRTS (Sensus Healthcare, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001300111-26-000004`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 2.26 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001300111-26-000004` (1 filing(s)) by Sardano Joseph C (CHIEF EXECUTIVE OFFICER).
Coverage **FIRE**; purchases USD 72,108, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): SY 1.94, BWEN 2.25, AIIO 4.51, ARMP 2.66, HUBC 1.3.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NSPR (InspireMD, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001493152-26-052820`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 0.65 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001493152-26-052820` (3 filing(s)) by ROUBIN GARY S (director), Lawless Michael A (Chief Financial Officer), Stuka Paul (director).
Coverage **FIRE**; purchases USD 375,001, owners 3, top executive yes, lag 4 days.
Twins (band+liq+mom): INLF 0.3597, CRIS 0.5418, KTTA 0.4343, SURG 0.137, XHLD 0.6897.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NPCE (NeuroPace Inc) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001533175-26-000018`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 8.2 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001533175-26-000018` (2 filing(s)) by Becker Joel (CHIEF EXECUTIVE OFFICER), Williams Patrick F. (Chief Financial Officer).
Coverage **FIRE**; purchases USD 198,442, owners 2, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): ALTG 5.12, CPIX 5.8, VOGX 13.48, AMTD 12.76, VTVT 17.29.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 HNRG (HALLADOR ENERGY CO) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001628280-26-074438`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 10.31 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074438` (1 filing(s)) by Wesley Charles Ray IV (director).
Coverage **FIRE**; purchases USD 1,069,710, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): APMD 17.8, SLDB 6.23, CBIO 13.04, HPP 9.12, DQ 9.45.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 STUB (StubHub Holdings, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001628280-26-074600`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 4.53 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-074600` (2 filing(s)) by Raab Andrew John (director), Bhargava Sameer (director).
Coverage **FIRE**; purchases USD 3,547,771, owners 2, top executive no, lag 1 days.
Twins (band+liq+mom+dd): HTZ 1.35, INTR 3.92, ABR 1.14, PGEN 4.29, VISN 3.94.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 RDW (Redwire Corp) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001819810-26-000144`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 6.78 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001819810-26-000144` (1 filing(s)) by Cannito Peter Anthony Jr (Chairman and CEO).
Coverage **FIRE**; purchases USD 99,997, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): MARA 6.42, HL 12.5, CAI 19.94, ASST 18.09, HIMS 17.55.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ANGX (Angel Studios, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001865200-26-000102`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 4.14 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001865200-26-000102` (1 filing(s)) by Sarowitz Steven I (director).
Coverage **FIRE**; purchases USD 4,625,599, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): SFIX 2.8, EVGO 1.55, ALTO 3.6, ACB 4.52, FIP 3.76.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 MAIA (MAIA Biotechnology, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:34:48Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4-0001878313-26-000104`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 1.25 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Form 4 `0001878313-26-000104` (2 filing(s)) by Vitoc Vlad (Chief Executive Officer), Smith Stan (director).
Coverage **FIRE**; purchases USD 200,000, owners 2, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): CING 4.72, SMRT 1.49, TMCI 4.44, ENGN 1.72, BHR 1.53.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

