# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-23T10:29:23Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 39 (FIRE 17, ABSTAIN 22) over 14 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 18, SEALED 39, SKIP_NOT_OPERATING 8, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 2; coverage gaps 1.

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

Sets 73 over 14 signal sessions; events seen: SEALED 73, SKIP_REPEAT_90D 59, SKIP_NO_TICKER 44, SKIP_NOT_IN_UNIVERSE 45, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 237 over 11 signal sessions; events seen: SEALED 237, SKIP_NOT_IN_UNIVERSE 8, SKIP_NOT_PURCHASE 8438, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 8, SKIP_REPEAT_90D 72; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 237 over 11 signal sessions; events seen: SEALED 237; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 102, FIRE 135
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 36 over 13 signal sessions; events seen: SEALED 36; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 18, FIRE 18
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

292 tags: 68 true, 0 unknown.

## Latest sets

### FORM4_SHARP ARR (Armour Residential REIT, Inc.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001469064-26-000010`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 10.83 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001469064-26-000010` by ULM SCOTT (CEO); purchases USD 52,248; top executive yes; holding up +6.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001469064-26-000010.
Twins (band+liq+mom+dd): DNA 8.2, AESI 5.62, SSL 11.71, UUUU 5.48, TGB 5.61, ATEC 6.9, STNE 7.22, BBNX 13.32, NRIX 13.6, SVM 7.26, IE 5.76, NVCR 10.69, UMAC 10.15, WYFI 7.65, APPS 6.22, NVAX 7.72, INFQ 7.3, PGY 14.62, NNE 9.97, AMPX 6.4.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PALI (PALISADE BIO, INC.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-053267`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 0.9254 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-053267` by Baltera Robert Jr. (director); purchases USD 50,285; top executive no; holding up +10.8%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001493152-26-053267.
Twins (band+liq+mom+dd): SLNH 0.4012, CATX 0.784, URG 0.4827, IQ 0.554, SDEV 0.5574, BMGL 0.3193, RR 0.6573, XRX 0.86, ZURA 0.9524, ORBS 0.6247, PARA 0.0365, ALLO 0.6669, SITC 0.6838, CENN 0.1133, SIDU 0.7996, NAK 0.5103, RBNE 0.1277, AREC 0.8871, RZLV 0.931, EU 0.4747.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BGS (B&G Foods, Inc.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001601974-26-000016`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 3.36 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001601974-26-000016` by Mills Robert D (President & CEO); purchases USD 249,714; top executive yes; holding up +29.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001601974-26-000016.
Twins (band+liq+mom+dd): GEVO 1.67, OPK 1.61, BDN 2.92, UIS 2.71, LZM 4.23, MNKD 3.95, PLTK 2.51, IRWD 4.71, FULC 3.71, NCPL 3.33, KXIN 2.56.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP HMH (HMH Holding Inc) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075005`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 11.2 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075005` by McGee Thomas W. (Chief Financial Officer), Bergsvik Eirik (Chief Executive Officer); purchases USD 1,736,052; top executive yes; holding up +254.6%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 2; parent CAT-FORM4-0001628280-26-075005.
Twins (band+liq+mom+dd): CDNL 5.18, XRPN 7.35, CTEV 19.03, ENTA 7.98, CRMD 5.08, GRRR 6.28, JANX 10.29, MTA 6.22, SCTX 13.22, BDSX 8.3, OFIX 6.34, TGS 19.95, IMXI 5.36, WW 7.97, SSYS 5.49, MGTX 8.14, IMTX 5.95, OBE 8.55, CRESY 8.01, PHAT 5.08.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CWBC (Community West Bancshares) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075017`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 24.03 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075017` by GILL JAGROOP (director); purchases USD 293,988; top executive no; holding up +2.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075017.
Twins (band+liq+mom+dd): MG 20.19, BHRB 68.46, ORRF 41.82, VLGEA 40.73, YORW 31.11, CSR 54.85, STBA 49.38, UHT 37.16, SMBK 46.13, CCBG 49.53, FISI 38.59, RUSHB 56.73, FCBC 44.76, SHBI 21.81, RBCAA 90.2, FMAO 35.1, NBBK 21.14, CHMG 81.205, CBL 48.86, WASH 36.91.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NBP (NovaBridge Biosciences) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0002126029-26-000006`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 0.8798 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002126029-26-000006` by Hagler Mark Arnold (Chief Commercial Officer); purchases USD 85,882; top executive no; holding up +100.0%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002126029-26-000006.
Twins (band+liq+mom+dd): IHRT 0.4766, KSCP 0.3593, SPRO 0.8263, FRGT 0.6001, DAVI 1, SUIG 0.741, RC 0.7, ZNB 0.4122, OXSQ 0.5648, BLND 0.8842, AXG 0.7571, TLSA 0.6756, CRBU 0.3105, REKR 0.2097, QNC 0.8963, GLDG 0.6158, JDZG 0.114, MVIS 0.861, SRFM 0.4101, MEDS 0.7277.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D SRXH (SRX Global Inc.) - accepted 2026-11-20T08:45:38-05:00, sealed 2026-11-20T23:00:57Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-SEC13D-0000921895-26-003228`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 0.8 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Filing `0000921895-26-003228` by EGAN KEVIN; Item 4 intent words: board, sale of the, director.
Coverage **ABSTAIN** (MICROCAP); pre-entry move -22.33%, market value USD 16.2M, dilution filings 0.
Twins (band+liq+mom+dd): NMG 0.6705, GANX 0.9994, EHTH 0.3477, BTCS 0.653, DBGI 0.1602.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D GPN (GLOBAL PAYMENTS INC) - accepted 2026-11-20T17:01:47-05:00, sealed 2026-11-20T23:00:57Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-SEC13D-0001193125-26-470458`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 91.83 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Filing `0001193125-26-470458` by GTCR W Aggregator LP; Item 4 intent words: board, acquisition, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 24,301.5M, dilution filings 0.
Twins (band+liq+mom+dd): PFGC 108.28, RTX 190.17, CART 57.31, LTH 46.33, PAG 212.25.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 SRXH (SRX Global Inc.) - accepted 2026-11-20T08:45:38-05:00, sealed 2026-11-20T23:01:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-SEC13D_V2-0000921895-26-003228`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 0.8 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0000921895-26-003228` by EGAN KEVIN; cover page max 7.9% of class; strong intent: sale of the; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (MICROCAP); market value USD 16.2M from XBRL; parent CAT-SEC13D-0000921895-26-003228.
Twins (band+liq+mom+dd): NMG 0.6705, GANX 0.9994, EHTH 0.3477, BTCS 0.653, DBGI 0.1602, CAN 0.1177, EMAT 0.6031, LIDR 0.644, SOAR 0.165, MYO 0.811, EU 0.4492, MVIS 0.8306, ARBE 0.3214, GLDG 0.6156, BIVI 0.8, CODX 0.1295, CNSY 0.6301, PROP 0.2881, GNS 0.4993, VENU 0.9929.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 GPN (GLOBAL PAYMENTS INC) - accepted 2026-11-20T17:01:47-05:00, sealed 2026-11-20T23:01:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-SEC13D_V2-0001193125-26-470458`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 91.83 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001193125-26-470458` by GTCR W Aggregator LP; cover page max 16.35% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 24,301.5M from XBRL; parent CAT-SEC13D-0001193125-26-470458.
Twins (band+liq+mom+dd): PFGC 108.28, RTX 190.17, CART 57.31, LTH 46.33, PAG 212.25, DG 130.53, AXGN 55.75, BMRN 60.41, TXRH 178.05, DGX 258.28, GNRC 193.22, FMX 126.06, BCE 21.86, AWK 149.53, COST 1102.15, DIS 117.98, BAM 48.94, ROIV 38.655, BBIO 76.03, RYTM 112.36.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K CTSO - event `0001104659-26-130442`, accepted 2026-11-20T08:56:08-05:00, sealed 2026-11-20T23:01:37Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-DILUTION_8K-0001104659-26-130442`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 4.16 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -18.91%.
Twins (band+liq+mom+dd): XTLB 1.37, EHGO 1.3, FABC 1.02, BTOC 1.79, TNMG 2.12.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K ADVB - event `0001213900-26-122692`, accepted 2026-11-20T16:05:26-05:00, sealed 2026-11-20T23:01:37Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-122692`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 1.65 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): SINT 1.1, FBGL 1.73, NEUP 2.35, CLWT 1.05, RVSN 1.69.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K NRGV - event `0001828536-26-000123`, accepted 2026-11-20T16:30:43-05:00, sealed 2026-11-20T23:01:37Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-DILUTION_8K-0001828536-26-000123`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 2.77 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom): WIT 2.05, ARRY 3.785, COTY 3.95.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K APUS - event `0001213900-26-122743`, accepted 2026-11-20T16:45:18-05:00, sealed 2026-11-20T23:01:37Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-122743`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 1.6 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): JWEL 1.58, RML 2.98, THH 1.02, QNTM 1.29, AXIL 4.27.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D NAMI (Jinxin Technology Holding Co) - accepted 2026-11-20T21:44:38-05:00, sealed 2026-11-23T10:29:21Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-SEC13D-0001213900-26-122856`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 1.55 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Filing `0001213900-26-122856` by Xu Jin Justing; Item 4 intent words: none.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 2,206.1M, dilution filings 0.
Twins (band+liq+mom+dd): REVB 3.5, NTRB 4.92, UCAR 3, PSNYW 2.7899, CGTL 2.2.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

