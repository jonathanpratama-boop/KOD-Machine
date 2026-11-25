# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-25T11:36:29Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 45 (FIRE 19, ABSTAIN 26) over 16 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 22, SEALED 45, SKIP_NOT_OPERATING 11, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 4; coverage gaps 1.

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

Sets 80 over 16 signal sessions; events seen: SEALED 80, SKIP_REPEAT_90D 63, SKIP_NO_TICKER 72, SKIP_NOT_IN_UNIVERSE 47, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 297 over 14 signal sessions; events seen: SEALED 297, SKIP_NOT_IN_UNIVERSE 11, SKIP_NOT_PURCHASE 10182, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 11, SKIP_REPEAT_90D 123; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 277 over 13 signal sessions; events seen: SEALED 277; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 125, FIRE 152
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 43 over 15 signal sessions; events seen: SEALED 43; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 22, FIRE 21
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

361 tags: 89 true, 0 unknown.

## Latest sets

### FORM4 ASTS (AST SpaceMobile, Inc.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001104659-26-131559`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 23.6 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001104659-26-131559` (1 filing(s)) by Cisneros Adriana (director).
Coverage **FIRE**; purchases USD 1,025,401, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): CLS 196.64, MU 629.79, BE 156.41, NBIS 87.31, TPL 251.4.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CTSO (Cytosorbents Corp) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001104659-26-131710`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 4.37 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001104659-26-131710` (1 filing(s)) by Chan Phillip P. (Chief Executive Officer).
Coverage **FIRE**; purchases USD 355,001, owners 1, top executive yes, lag 4 days.
Twins (band+liq+mom+dd): BIYA 1.2, FLYE 1.69, MINE 2.055, STKS 1.02, ALZN 1.11.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 DTM (DT Midstream, Inc.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001140361-26-045502`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 114.23 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001140361-26-045502` (1 filing(s)) by Baker Stephen W (director).
Coverage **FIRE**; purchases USD 56,640, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): SEI 56.53, EXPE 239.26, HONA 154.77, SUPN 29.84, NTRS 165.94.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 USEA (United Maritime Corp) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001140361-26-045513`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 3.05 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001140361-26-045513` (1 filing(s)) by Tsantanis Stamatios (Director, CEO).
Coverage **FIRE**; purchases USD 131,274, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): CLNN 4.59, NGEN 2.08, POWW 2.88, ABLV 2.76, FLNT 3.68.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 RNA (Atrium Therapeutics, Inc.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001193125-26-475635`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 7.49 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-475635` (1 filing(s)) by Winslow Brendan R. (Chief Financial Officer).
Coverage **FIRE**; purchases USD 249,417, owners 1, top executive yes, lag 4 days.
Twins (band+liq+mom+dd): NEGG 8.36, SLQT 6.71, WYY 6.28, PAMT 10.45, FOA 9.39.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TEN (TSAKOS ENERGY NAVIGATION LTD) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001193125-26-475722`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 45.06 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-475722` (1 filing(s)) by TSAKOS NIKOLAOS (Chief Executive Officer).
Coverage **FIRE**; purchases USD 853,966, owners 1, top executive yes, lag 4 days.
Twins (band+liq+mom+dd): PFSI 59.35, GLNG 39.62, ZD 50.54, BCC 65.77, CWEN 29.35.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 OTF (Blue Owl Technology Finance Corp.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001193125-26-475725`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 9.24 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-475725` (1 filing(s)) by Packer Craig (Chief Executive Officer).
Coverage **FIRE**; purchases USD 501,202, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): ARHS 12.94, AVEX 11.49, BXMT 10.82, XRAY 9.38, DYN 17.75.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 OXSQ (Oxford Square Capital Corp.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001213900-26-123687`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 0.6345 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-123687` (2 filing(s)) by ROSENTHAL SAUL B (President and COO), COHEN JONATHAN H (Chief Executive Officer).
Coverage **FIRE**; purchases USD 114,948, owners 2, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): LITS 0.8441, KSCP 0.3086, SRFM 0.3687, CENN 0.1074, PLRX 0.6283.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FRD (FRIEDMAN INDUSTRIES INC) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001437749-26-038140`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 36.15 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001437749-26-038140` (1 filing(s)) by Taylor Mike J (President / CEO / Director).
Coverage **FIRE**; purchases USD 168,730, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): RCMT 32, PPIH 26.01, ISBA 36.46, BDL 47.8, CMT 21.3.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 XGPU (Reliance Global Group, Inc.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001493152-26-053875`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 1.61 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001493152-26-053875` (3 filing(s)) by Beyman Ezra (Chairman and CEO), Beyman Mordechai Menachem (Vice President), Korman Judah (Chief Operating Officer).
Coverage **FIRE**; purchases USD 514,553, owners 3, top executive yes, lag 4 days.
Twins (band+liq+mom+dd): SUNE 1.69, AUUD 2.37, NCI 3.45, WLDS 1.1, APXC 3.84.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SNEX (StoneX Group Inc.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001531352-26-000016`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 38.15 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001531352-26-000016` (2 filing(s)) by Thamodaran Dhamu R. (director), Lyon Charles M (President).
Coverage **FIRE**; purchases USD 497,468, owners 2, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): HLIO 44.67, AMBA 44.47, OII 31.96, PDFS 33, ACMR 40.34.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 MPB (MID PENN BANCORP INC) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001557321-26-000006`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 33.97 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001557321-26-000006` (1 filing(s)) by Noone John E (director).
Coverage **FIRE**; purchases USD 68,058, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): BFST 31.22, THFF 73.57, PNRG 217.7, RBB 24.8, FSBC 41.96.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PRE (Prenetics Global Ltd) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001628280-26-075614`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 10.15 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-075614` (1 filing(s)) by Rosin Brian J (CFO of IM8 (US) LLC).
Coverage **FIRE**; purchases USD 404,200, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): BCAX 9.48, ADUR 7.93, FRNM 9.97, AVBP 12.64, YARW 15.82.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 MKL (MARKEL GROUP INC.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001857626-26-000006`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 1961.44 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001857626-26-000006` (1 filing(s)) by Harris Greta J (director).
Coverage **FIRE**; purchases USD 184,832, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): RJF 160.6, EXR 158.88, ADSK 255.7, ABNB 173.39, CSL 396.51.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 HSHP (Himalaya Shipping Ltd.) - filed 2026-11-24, sealed 2026-11-25T11:35:56Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4-0001959455-26-000143`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 15.42 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Form 4 `0001959455-26-000143` (1 filing(s)) by Svensen Lars-Christian (Contracted CEO).
Coverage **FIRE**; purchases USD 103,088, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): SPTX 19.77, GSBD 7.76, ASIX 13.44, OIS 7.56, DBI 5.9.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

