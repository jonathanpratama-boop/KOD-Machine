# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-18T10:38:14Z). Nothing here is a result until a look is reached.

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

Sets 189 over 9 signal sessions; events seen: SEALED 189; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 75, FIRE 114
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

### FORM4_SHARP ETN (Eaton Corp plc) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001104659-26-129065`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 337.11 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001104659-26-129065` by Foster David B (See Remarks below.), Johnson Gerald (director); purchases USD 170,894; top executive no; holding up +16.4%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001104659-26-129065.
Twins (band+liq+mom+dd): SPCX 141.7, JBL 243.61, NKE 35.85, POWL 150.86, HRB 48.07, OVV 63.84, PR 22.18, QLYS 174.67, ENTG 140.78, MDGL 421.99, ETSY 82.62, MKC 44.73, W 107, XYL 94.65, BURL 235.14, AKAM 84.64, CTSH 60, NEM 111.26, PH 920.84, SLB 48.95.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PRAA (PRA GROUP INC) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001185352-26-000002`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 11.17 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001185352-26-000002` by FREDRICKSON STEVEN D (director); purchases USD 295,000; top executive no; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001185352-26-000002.
Twins (band+liq+mom+dd): FTH 9.04, PBYI 7.14, RYAM 5.18, ARCT 7.97, GRRR 6.49, AORT 18.27, MBUU 18.97, XRPN 7.25, JANX 10.71, NXRT 14.73, OFRM 11.66, CIM 6.33, CADL 5.4, PAYS 9.81, MPLT 6.57, FUBO 6.87, HPK 7.57, LAND 6.32, STRO 8.92, FDMT 10.79.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ITG (ITG, Inc./DE/) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-465620`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 5.37 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-465620` by LAPERCH WILLIAM G (director), Giacalone Peter (director), Parrott Andrew (Chief Executive Officer), Brooks Michael George (director); purchases USD 1,162,690; top executive yes; holding up +177.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 4; parent CAT-FORM4-0001193125-26-465620.
Twins (band+liq+mom+dd): AKTS 16.31, EVMN 7.02, EAF 8.26, DBVT 9.99, ATTO 14.86, BLSM 15.13, ODTX 19.37, CTNM 9.55.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP RMIX (Suncrete, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-465843`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 6.05 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-465843` by Fleming Ned N III (director); purchases USD 238,000; top executive no; holding up n/a.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 2; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-465843.
Twins (band+liq+mom+dd): ALMU 5.68, MRAM 11.04, LAND 6.32, PAYS 9.81, OFIX 6.67, BDSX 8.88, CLPT 7.86, ABX 6.65, GLUE 9.07, YARW 14.21, NRDS 7.07, ASYS 11.36, RYAM 5.18, OFRM 11.66, TSSI 5.63, IMTX 6.29, PHAT 5.5, AORT 18.27, HMH 10.98, OPTX 6.05.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP OPEN (Opendoor Technologies Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001195975-26-000007`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 1.18 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001195975-26-000007` by HAMILTON DANA (director); purchases USD 241,990; top executive no; holding up +57.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001195975-26-000007.
Twins (band+liq+mom+dd): PGEN 4.29, PLUG 1.05, RXRX 2.72, FRMI 2.41, KOS 2.03, DJT 4.055, MPT 1.59, SOUN 3.06, OI 4.7, CRML 3.82, ENVX 1.37, HIVE 1.43, LWLG 3.155, BBAI 1.8, BRUN 4.68, ABR 1.14, UAMY 2.48, RCAT 2.41, KEEL 1.75, SPCE 1.3.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SSII (SS Innovations International, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-121405`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 1.33 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-121405` by Sudhir Srivastava (Chairman and CEO); purchases USD 300,000; top executive yes; holding up +0.1%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001213900-26-121405.
Twins (band+liq+mom+dd): SKIL 2.35, LUCK 4.17, YDES 4.73, ATLX 1.48, XNET 3.37, RTB 4.46, FAC 3.7, LSAK 3.25, HUBC 1.3, DFNS 1.63, ECOR 4.79, ARAI 2.14, UP 2.14, STEM 1.2, ONCO 3, PSNY 2.83, NXDT 2.85, ZSQR 1.94, MWYN 1.33, MSGM 3.75.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PEPG (PepGen Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001231919-26-001588`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 3.88 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001231919-26-001588` by RA CAPITAL MANAGEMENT, L.P. (director), RA Capital Healthcare Fund LP (director), RA Capital Nexus Fund II, L.P. (director), Kolchinsky Peter (director), Shah Rajeev M. (director); purchases USD 43,125,000; top executive no; holding up +46.5%.
Coverage **ABSTAIN** (NOT_SHARP, DILUTION_RECENT); dilution filings 2; routine owners 0 of 5; parent CAT-FORM4-0001231919-26-001588.
Twins (band+liq+mom+dd): ACB 4.52, SABR 1.68, TOYO 4.205, SFIX 2.8, CLNE 1.63, WOOF 2.69, RZLT 4.015, GOGO 3.02, ALTO 3.6, FIP 3.76, CLRO 4.72, EVGO 1.55, INO 1.63, DNUT 3.58, MLCO 4.22, GEVO 1.64, LXRX 1.78, BUR 3.6, UIS 2.46, LRMR 2.99.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SRTS (Sensus Healthcare, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001300111-26-000004`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 2.26 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001300111-26-000004` by Sardano Joseph C (CHIEF EXECUTIVE OFFICER); purchases USD 72,108; top executive yes; holding up +2.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001300111-26-000004.
Twins (band+liq+mom+dd): SY 1.94, BWEN 2.25, AIIO 4.51, ARMP 2.66, HUBC 1.3, LFMD 1.795, FAC 3.7, XNET 3.37, ZH 2.53, KGEI 4.91, HYPD 2.38, QMLS 2.6, OWLT 3.25, NSTR 1.76, MOVE 4.37, WKHS 1.9, BKYI 1.94, PASW 1.44, MSGM 3.75, BBOT 1.94.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NSPR (InspireMD, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-052820`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 0.65 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-052820` by ROUBIN GARY S (director), Lawless Michael A (Chief Financial Officer), Stuka Paul (director); purchases USD 375,001; top executive yes; holding up +72.6%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 2; routine owners 0 of 3; parent CAT-FORM4-0001493152-26-052820.
Twins (band+liq+mom): INLF 0.3597, CRIS 0.5418, KTTA 0.4343, SURG 0.137, XHLD 0.6897, HUMA 0.501, LUCD 0.399, XTIA 0.893, CRMT 0.8711.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NPCE (NeuroPace Inc) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001533175-26-000018`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 8.2 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001533175-26-000018` by Becker Joel (CHIEF EXECUTIVE OFFICER), Williams Patrick F. (Chief Financial Officer); purchases USD 198,442; top executive yes; holding up +17.6%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001533175-26-000018.
Twins (band+liq+mom+dd): ALTG 5.12, CPIX 5.8, VOGX 13.48, AMTD 12.76, VTVT 17.29, SLSR 6, RVII 13.71, AKTX 5.7, ANIK 12.85, NEGG 7.78, BRCC 8.04, CHRN 9.74, SAR 11.07, NREF 11.42, JSPR 10.34, SIF 14.35, MPAA 7.4, SPCB 7.05, ISOU 6.62, RNA 6.48.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP HNRG (HALLADOR ENERGY CO) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-074438`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 10.31 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-074438` by Wesley Charles Ray IV (director); purchases USD 1,069,710; top executive no; holding up +29.5%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-074438.
Twins (band+liq+mom+dd): APMD 17.8, SLDB 6.23, CBIO 13.04, HPP 9.12, DQ 9.45, LTGO 13.76, CPS 18.22, GHRS 18.27, KLRA 12.2, ANL 9.48, BRVE 18.78, SPIR 8.18, KARD 13.19, SPTX 18.17, BIOA 5.1, OLMA 7.22, OBX 12.07, DSGN 9.84, PRE 16.33, ADUR 9.16.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP STUB (StubHub Holdings, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-074600`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 4.53 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-074600` by Raab Andrew John (director), Bhargava Sameer (director); purchases USD 3,547,771; top executive no; holding up +186.6%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001628280-26-074600.
Twins (band+liq+mom+dd): HTZ 1.35, INTR 3.92, ABR 1.14, PGEN 4.29, VISN 3.94, BULL 4.73, AESI 4.9, CRML 3.82, SPCE 1.3, KEEL 1.75, RXRX 2.72, ENVX 1.37, POET 4.4, RCAT 2.41, PONY 3.99, SOUN 3.06, FLNC 4.08, HIVE 1.43, LAC 1.41, OI 4.7.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP RDW (Redwire Corp) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001819810-26-000144`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 6.78 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001819810-26-000144` by Cannito Peter Anthony Jr (Chairman and CEO); purchases USD 99,997; top executive yes; holding up +1.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001819810-26-000144.
Twins (band+liq+mom+dd): MARA 6.42, HL 12.5, CAI 19.94, ASST 18.09, HIMS 17.55, FIG 18.18, INIO 13.7, QBTS 8.08, CLSK 6.15, PBR 17.41, BMNR 15.86, AG 12.77, APLD 14.22, VALE 10.42, PURR 7.96, NVTS 7.6, CIFR 6.42, IOVA 7.53, FSLY 15.9, CDE 13.17.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ANGX (Angel Studios, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001865200-26-000102`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 4.14 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001865200-26-000102` by Sarowitz Steven I (director); purchases USD 4,625,599; top executive no; holding up +75.1%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001865200-26-000102.
Twins (band+liq+mom+dd): SFIX 2.8, EVGO 1.55, ALTO 3.6, ACB 4.52, FIP 3.76, GEVO 1.64, BUR 3.6, CLRO 4.72, GOGO 3.02, INO 1.63, SABR 1.68, UIS 2.46, MLCO 4.22, WOOF 2.69, RZLT 4.015, CLNE 1.63, DNUT 3.58, TOYO 4.205, LRMR 2.99, LXRX 1.78.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP MAIA (MAIA Biotechnology, Inc.) - filed 2026-11-17, sealed 2026-11-18T10:37:32Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-FORM4_SHARP-0001878313-26-000104`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 1.25 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001878313-26-000104` by Vitoc Vlad (Chief Executive Officer), Smith Stan (director); purchases USD 200,000; top executive yes; holding up +9.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001878313-26-000104.
Twins (band+liq+mom+dd): CING 4.72, SMRT 1.49, TMCI 4.44, ENGN 1.72, BHR 1.53, DOUG 1.57, SEV 1.66, STFS 4.98, VFS 2.92, LUNG 2.735, CAMP 4, GECC 4.94, ONL 2.44, CHOW 3.53, ANTX 4.23, ABLV 2.21, SPWH 1.15, VEEA 4.67, RBBN 1.42, QTRX 2.86.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

