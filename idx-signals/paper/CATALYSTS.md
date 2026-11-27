# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-27T10:29:39Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 47 (FIRE 20, ABSTAIN 27) over 17 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 27, SEALED 47, SKIP_NOT_OPERATING 11, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 4; coverage gaps 1.

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
- POST20: paired 14, mean signed diff -5.68%, share with the flow 21%

## DILUTION_8K (counted at each look; direction -1; `KOD-CATALYST-FAMILY-DILUTION_8K-v1`)

Sets 82 over 17 signal sessions; events seen: SEALED 82, SKIP_REPEAT_90D 68, SKIP_NO_TICKER 83, SKIP_NOT_IN_UNIVERSE 50, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 312 over 15 signal sessions; events seen: SEALED 312, SKIP_NOT_IN_UNIVERSE 11, SKIP_NOT_PURCHASE 10665, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 13, SKIP_REPEAT_90D 147; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 312 over 15 signal sessions; events seen: SEALED 312; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 142, FIRE 170
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 45 over 16 signal sessions; events seen: SEALED 45; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 23, FIRE 22
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
| IDX_INDEX | REVERSAL_POST20 | 14 | 0.79 | 0.50 | n/a | 0.250 | 0.250 |
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

391 tags: 94 true, 1 unknown.

## Latest sets

### FORM4_SHARP NANO (Forge Nano Holdings, Inc.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0000950142-26-003161`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 3.97 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0000950142-26-003161` by Smith Shane (Pres. of Forge Battery, Inc.); purchases USD 250,647; top executive no; holding up n/a.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 2; routine owners 0 of 1; parent CAT-FORM4-0000950142-26-003161.
Twins (band+liq+mom+dd): VYGR 1.78, SEV 1.5, FISN 2.83, PRQR 1.235, AVIR 3.88, AIRG 3.56, GCTS 1.22, LUCK 3.84, DTI 1.66, XNET 3.075, MGNX 2.36, NEPH 2.83, CVM 1.57, BBDO 2.21, GANX 1.1, SEAT 2.06, WHWK 3.15, ATYR 4.77, OSTX 1.12, WRAP 1.13.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NOVT (NOVANTA INC) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001076930-26-000090`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 109.53 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001076930-26-000090` by Wilson Frank Anders (director); purchases USD 52,200; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001076930-26-000090.
Twins (band+liq+mom+dd): NBR 73.31, HRI 136.64, DGII 53.3, ALGM 27.13, IDCC 254.475, GEF 68.26, UVV 32.55, PNTG 34.77, DFTX 31.09, AGIO 31.5, NUTX 165.95, LOPE 114.59, MUR 32.56, LIFE 32.56, BLLN 94.15, POWI 41.4, ECO 81.59, LMND 37.99, CRC 44.66, NE 37.97.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TMC (TMC the metals Co Inc.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001104659-26-131894`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 1.94 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001104659-26-131894` by Karkar Andrei (director), ERAS Capital LLC (officer); purchases USD 805,000; top executive no; holding up +0.8%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001104659-26-131894.
Twins (band+liq+mom+dd): GDRX 2.38, BYND 4.45, TMQ 1.4, UROY 2.27, HYLN 1.97, SGML 3.98, ABR 1.26, XTND 1.39, XGN 3.97, LAES 1.07, SERV 2.29, DC 3.61, AIOT 1.99, DDD 1.4, BNC 3.04, VRRM 1.77, WVE 3.04, DFDV 2.245, MITT 4.22, LAR 3.33.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PATK (PATRICK INDUSTRIES INC) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001189422-26-000034`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 85.49 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001189422-26-000034` by WELCH M SCOTT (director); purchases USD 432,941; top executive no; holding up +3.3%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 2; routine owners 0 of 1; parent CAT-FORM4-0001189422-26-000034.
Twins (band+liq+mom+dd): SBRA 21.16, SIBN 24.79, FTDR 93.87, ITRI 100.81, EPR 60.5, VNT 45.51, COGT 36.08, HASI 37.61, THO 79.32, ULS 77.02, PRM 29.02, SKWD 64.73, GIB 83.46, TEX 59.01, LEVI 24.49, ADUS 122.53, LZB 30.24, WWW 25.34, BIRK 35.73, AXTA 36.06.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ADV (Advantage Solutions Inc.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-478513`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 27.85 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-478513` by PEACOCK DAVID A (Chief Executive Officer); purchases USD 50,000; top executive yes; holding up +0.9%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-478513.
Twins (band+liq+mom+dd): BSAC 30.83, WS 36.75, ITIC 266.39, FTK 23.88, NGS 28.2, ODC 69.26, AD 28.2, XRN 27.38, TCBX 37.52, USLM 104.68, BCH 36.67, BGSI 75.87, CSV 31.32, ZBIO 27.13, SAH 58.6, FOR 23.27, BWLP 22.67, DMC 25.05, KARO 60.12, CENTA 32.52.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ROAD (Construction Partners, Inc.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-478515`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 72.12 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-478515` by Fleming Ned N III (director); purchases USD 180,331; top executive no; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-478515.
Twins (band+liq+mom+dd): FLNG 24.26, CE 45.44, WDS 20.21, ARQT 29.59, JOE 65.87, BOH 67.23, RHI 39.4, BCC 67.63, UGI 34.27, ESLT 662.03, PLSE 47.86, BPOP 146.79, SHOO 39.76, ZD 50.47, UNF 232.8, AX 87.05, TFPM 29.07, PJT 146.11, PLAB 25.03, BLTE 138.34.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP AVD (AMERICAN VANGUARD CORP) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-478691`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 0.7825 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-478691` by Gottschalk Patrick E (director); purchases USD 98,098; top executive no; holding up +44.5%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-478691.
Twins (band+liq+mom+dd): WHLR 0.4081, MIST 0.36, SDEV 0.4981, CRMN 0.9141, ANVS 0.8548, OPTT 0.1918, YMAT 0.8136, EU 0.5105, ECX 0.5849, PLRX 0.6321, LDI 0.4711, ZENA 0.4686, ASTI 0.7521, STEM 0.58, CDT 0.2192, MBOT 0.7539, SPRO 0.8441, CHRS 0.379, REKR 0.1806, BIVI 0.9021.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CLW (Clearwater Paper Corp) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001414260-26-000006`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 16.76 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001414260-26-000006` by TOELDTE ALEXANDER (director); purchases USD 125,688; top executive no; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001414260-26-000006.
Twins (band+liq+mom+dd): PANL 8.34, FOSL 8.27, MNSO 10.46, TTI 6.07, TRTX 6.67, INNV 9.38, PTLO 6.17, AMCX 8.935, EVC 8.77, CMCO 18.49, OCS 8.47, VEL 15.93, OPRT 10.73, MRTN 11.675, SCZM 7.51, FRPH 18.59, CRVS 10.94, OPFI 6, OLMA 8.2, AEYE 12.36.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP EMPD (Empery Digital Inc.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001683168-26-009142`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 2.19 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001683168-26-009142` by READ IAN C (director); purchases USD 535,110; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001683168-26-009142.
Twins (band+liq+mom+dd): IMPP 3.93, GRDX 3.09, SRI 4.29, MIND 2.33, SRTS 2.08, ATOM 2.165, ZNTL 1.65, NXDT 3.34, NAGE 1.905, SCYX 2.56, DERM 3.45, METCB 2.79, BWEN 2.08, DAVA 1.15, GTBP 3.45, NRXS 4.82, SPAI 2.23, SUJA 4.85, SLE 4.01, FAC 3.63.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP GRWG (GrowGeneration Corp.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001725239-26-000006`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 1.02 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001725239-26-000006` by Lampert Darren (CEO); purchases USD 99,013; top executive yes; holding up +5.4%.
Coverage **ABSTAIN** (ROUTINE); dilution filings 0; routine owners 1 of 1; parent CAT-FORM4-0001725239-26-000006.
Twins (band+liq+mom+dd): NKTX 1.12, NRXS 4.82, CNXU 1.55, TONX 2.26, RENT 1.89, AMPG 1.725, PROK 1.21, USIO 1.9, IMDX 2.265, GLOO 2.37, GFUZ 4.22, SMTK 1.02, DERM 3.45, INDO 2.04, TENX 1.35, IXHL 2.16, UPLD 1.53, MRDN 4.24, ARAI 1.485, LFMD 1.4.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP EXE (EXPAND ENERGY Corp) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001730935-26-000015`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 86.77 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001730935-26-000015` by Teunissen Marcel (EVP & CFO); purchases USD 81,560; top executive yes; holding up +9.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001730935-26-000015.
Twins (band+liq+mom+dd): CHWY 20.47, RVMD 175.67, BAC 48.54, AVGO 300.86, HUBS 210.21, IVZ 28.1, APH 73.08, FRO 47.65, IT 184.8, AU 77.94, MGY 23.08, TENB 45.7, DTM 115.7, GFI 34.06, FANG 180.15, NWSA 26.08, URI 1015.72, OKE 86.45, VEEV 271.9, MOD 136.34.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BFS (SAUL CENTERS, INC.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001804456-26-000004`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 28.45 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001804456-26-000004` by Pearson David Todd (President & COO); purchases USD 99,719; top executive yes; holding up +4.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001804456-26-000004.
Twins (band+liq+mom+dd): BGSI 75.87, NBTX 29.15, USLM 104.68, MSBI 29.13, MLR 47.69, IMKTA 74.57, IIIN 26.7, BAR 35.19, FTK 23.88, EIG 45.84, CMP 22.1, VTOL 38.43, PBAM 80.14, REX 33.74, PLOW 37.62, FSBC 41.94, PKE 23.27, ZBIO 27.13, RIGL 44.63, CWCO 24.74.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NRGV (Energy Vault Holdings, Inc.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0001898769-26-000011`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 3.06 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001898769-26-000011` by Piconi Robert (Chief Executive Officer); purchases USD 60,750; top executive yes; holding up +0.2%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001898769-26-000011.
Twins (band+liq+mom+dd): DCH 4.2, INTR 4.01, VZLA 2.86, NUVB 4.31.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP KDK (Kodiak AI, Inc.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0002080471-26-000003`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 1.23 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002080471-26-000003` by Burnette Donald L. (Chief Executive Officer); purchases USD 2,213,400; top executive yes; holding up +7.4%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 2; routine owners 0 of 1; parent CAT-FORM4-0002080471-26-000003.
Twins (band+liq+mom+dd): ARTV 3.95, LENZ 2.99, CTMX 2.24, TOYO 3.41, AIV 1.46, SPRY 3.1, PSEC 1.43, CWH 4.41, INDI 1.56, RLMD 2.89, ACRS 3.735, RCKT 2.43.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SHMD (SCHMID Group N.V.) - filed 2026-11-25, sealed 2026-11-26T10:36:34Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4_SHARP-0002125667-26-000005`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 1.89 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002125667-26-000005` by Schuetz Arthur Josef Hermann (CFO Schmid Group N.V.); purchases USD 103,885,740,000; top executive yes; holding up +142.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002125667-26-000005.
Twins (band+liq+mom+dd): GYRE 4.14, PSNY 2.4, IMDX 2.265, CNXU 1.55, TTGT 2.08, PODC 1.77, BMM 2.47, IXHL 2.16, FRMM 2.35, HOVR 1.07, SSII 1.24, HURA 1.28, ALTI 1.31, OWLT 3.08, GSIT 2.605, AIXI 1.46, UPLD 1.53, GEOS 2.23, DFNS 1.21, CYAB 1.53.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

