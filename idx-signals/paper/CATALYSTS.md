# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-25T23:04:42Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 46 (FIRE 19, ABSTAIN 27) over 17 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 26, SEALED 46, SKIP_NOT_OPERATING 11, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 4; coverage gaps 1.

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

Sets 297 over 14 signal sessions; events seen: SEALED 297; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 133, FIRE 164
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

### FORM4_SHARP CTSO (Cytosorbents Corp) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001104659-26-131710`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 4.37 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001104659-26-131710` by Chan Phillip P. (Chief Executive Officer); purchases USD 355,001; top executive yes; holding up +67.9%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 2; routine owners 0 of 1; parent CAT-FORM4-0001104659-26-131710.
Twins (band+liq+mom+dd): BIYA 1.2, FLYE 1.69, MINE 2.055, STKS 1.02, ALZN 1.11, ZEPP 2.25, SER 1.41, SIEB 1.665, INLX 3.6001, BRTX 1.15, FBGL 2.052, FIEE 2.65, JFIN 1.22, ZKIN 1.4, LGVN 1.68, PAVS 2.56, RYOJ 2.06, LIMN 2.7, WYHG 2.6, SWAG 1.14.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP DTM (DT Midstream, Inc.) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001140361-26-045502`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 114.23 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001140361-26-045502` by Baker Stephen W (director); purchases USD 56,640; top executive no; holding up +17.8%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001140361-26-045502.
Twins (band+liq+mom+dd): SEI 56.53, EXPE 239.26, HONA 154.77, SUPN 29.84, NTRS 165.94, TRI 107.23, CDNS 296.6, LSCC 100.37, FUTU 88.09, MS 168.79, ONON 31.48, MOD 131.13, SLB 46.99, FCFS 168.87, HSBC 82.03, ZM 88.4, BCS 21.29, JBHT 223.47, Z 28.63, WCC 289.47.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP USEA (United Maritime Corp) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001140361-26-045513`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 3.05 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001140361-26-045513` by Tsantanis Stamatios (Director, CEO); purchases USD 131,274; top executive yes; holding up +3.2%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001140361-26-045513.
Twins (band+liq+mom+dd): CLNN 4.59, NGEN 2.08, POWW 2.88, ABLV 2.76, FLNT 3.68, ARQ 2.98, AFCG 3.52, FPH 4.6, CLAR 4.69, SMRT 1.54, YHGJ 3.5, CVGI 3.09, SPWH 1.28, SAGT 1.01, CAMP 4.3, BOSC 4.32, SJT 4.38, CMRC 3.43, ENTX 3.23, MYPS 4.93.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP RNA (Atrium Therapeutics, Inc.) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-475635`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 7.49 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-475635` by Winslow Brendan R. (Chief Financial Officer); purchases USD 249,417; top executive yes; holding up +95.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-475635.
Twins (band+liq+mom+dd): NEGG 8.36, SLQT 6.71, WYY 6.28, PAMT 10.45, FOA 9.39, NSLR 5.04, BAFN 5.39, JSPR 13.3, MAAS 10.15, PMI 6.45, MSLE 5.82, AEHL 6.9, AFYA 9.74, RFIL 6.54.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TEN (TSAKOS ENERGY NAVIGATION LTD) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-475722`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 45.06 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-475722` by TSAKOS NIKOLAOS (Chief Executive Officer); purchases USD 853,966; top executive yes; holding up +1.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-475722.
Twins (band+liq+mom+dd): PFSI 59.35, GLNG 39.62, ZD 50.54, BCC 65.77, CWEN 29.35, INGR 89.82, NWS 28.735, DAC 143.33, UGI 34.65, LB 70.38, RUSHA 44.86, PAGP 25.5, DCO 140.22, KNF 49.81, PNTG 35.32, LAUR 32.94, ATRC 56.71, NBHC 36.72, PLAB 24.52, CNS 68.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP OTF (Blue Owl Technology Finance Corp.) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-475725`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 9.24 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-475725` by Packer Craig (Chief Executive Officer); purchases USD 501,202; top executive yes; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-475725.
Twins (band+liq+mom+dd): ARHS 12.94, AVEX 11.49, BXMT 10.82, XRAY 9.38, DYN 17.75, HAPN 14.49, WU 6.22, SFD 18.93, GRND 13.63, FLG 10.43, TDOC 7.52, YELP 18.95, SMPL 11.71, SGHC 10.47, PMT 7.67, BNL 18.19, JMKE 17.49, CPRI 17.99, PZZA 19.76, REAL 11.29.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP OXSQ (Oxford Square Capital Corp.) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-123687`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 0.6345 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-123687` by ROSENTHAL SAUL B (President and COO), COHEN JONATHAN H (Chief Executive Officer); purchases USD 114,948; top executive yes; holding up +4.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001213900-26-123687.
Twins (band+liq+mom+dd): LITS 0.8441, KSCP 0.3086, SRFM 0.3687, CENN 0.1074, PLRX 0.6283, OTLK 0.4385, EYPT 0.2732, FFAI 0.093, YMAT 0.8726, ZNB 0.284, STEX 0.2816, QUCY 0.6054, CHRS 0.3591, LUCD 0.3591, GUTS 0.6862, BZFD 0.4725, ADBT 0.084, PROP 0.293, AVAT 0.7686, DKI 0.9085.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP FRD (FRIEDMAN INDUSTRIES INC) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-038140`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 36.15 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-038140` by Taylor Mike J (President / CEO / Director); purchases USD 168,730; top executive yes; holding up +2.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001437749-26-038140.
Twins (band+liq+mom+dd): RCMT 32, PPIH 26.01, ISBA 36.46, BDL 47.8, CMT 21.3, ISTR 27.1, AIRT 22.405, TCI 44.75, HNVR 21.19, TAYD 54.43, INBK 25.18, ARTNA 31.96, RICK 26.06, HBB 29.43, NKSH 37.5, INTG 33.75, NC 30.24, ELMD 24.76, SBR 61.75, DJP 45.51.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP XGPU (Reliance Global Group, Inc.) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-053875`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 1.61 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-053875` by Beyman Ezra (Chairman and CEO), Beyman Mordechai Menachem (Vice President), Korman Judah (Chief Operating Officer); purchases USD 514,553; top executive yes; holding up +774.4%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 3; parent CAT-FORM4-0001493152-26-053875.
Twins (band+liq+mom+dd): SUNE 1.69, AUUD 2.37, NCI 3.45, WLDS 1.1, APXC 3.84, NIXX 2.12, SCNX 2.06, EVAX 2.46, SOS 3.505, LSF 2.11, LFWD 3.21, UFG 1.79, JLHL 4.32, ROLR 2.57, HIND 1.14, CGTL 1.57, EXYN 1.45, VMAR 4.14, GWAV 1.82, SONM 1.76.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SNEX (StoneX Group Inc.) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001531352-26-000016`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 38.15 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001531352-26-000016` by Thamodaran Dhamu R. (director), Lyon Charles M (President); purchases USD 497,468; top executive yes; holding up +42.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001531352-26-000016.
Twins (band+liq+mom+dd): HLIO 44.67, AMBA 44.47, OII 31.96, PDFS 33, ACMR 40.34, BAND 37.34, ERO 21.75, UCTT 36.08, VCYT 26.59, CVI 31.48, LMND 35.93, VIST 49.61, AUGO 60.67, AMSC 20.14, KALU 95.62, WGS 48.97, ALNT 74.46, TFII 88.4, KLIC 57.59, AMR 133.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP MPB (MID PENN BANCORP INC) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001557321-26-000006`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 33.97 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001557321-26-000006` by Noone John E (director); purchases USD 68,058; top executive no; holding up +3.1%.
Coverage **ABSTAIN** (NOT_SHARP, ROUTINE); dilution filings 0; routine owners 1 of 1; parent CAT-FORM4-0001557321-26-000006.
Twins (band+liq+mom+dd): BFST 31.22, THFF 73.57, PNRG 217.7, RBB 24.8, FSBC 41.96, UVSP 39.14, GSBC 78.52, AMAL 47.94, SPFI 40.99, BHRB 68.86, HBT 35.74, VTMX 34.51, IMKTA 84.09, HIPO 36.79, CHMG 80.09, SCHL 37.55, BHB 39.6, NWFL 34.93, WASH 37.22, NRP 115.58.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PRE (Prenetics Global Ltd) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075614`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 10.15 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075614` by Rosin Brian J (CFO of IM8 (US) LLC); purchases USD 404,200; top executive yes; holding up +173.2%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075614.
Twins (band+liq+mom+dd): BCAX 9.48, ADUR 7.93, FRNM 9.97, AVBP 12.64, YARW 15.82, SPIR 7.07, CIM 6.88, LYTS 14.06, IDR 14.25, ARCT 8.79, OBE 8.3, FTH 9.71, KC 6.21, METC 5.53, SSYS 5.1, CLPT 7.37, NPKI 8.34, LIME 19.79, HY 15.68, CNL 9.19.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP MKL (MARKEL GROUP INC.) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001857626-26-000006`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 1961.44 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001857626-26-000006` by Harris Greta J (director); purchases USD 184,832; top executive no; holding up +14.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001857626-26-000006.
Twins (band+liq+mom+dd): RJF 160.6, EXR 158.88, ADSK 255.7, ABNB 173.39, CSL 396.51, SOLS 62.73, CBRE 133.48, TBBB 65.65, ACGL 109.69, AOS 65.95, AHR 59.75, CB 375.37, SNA 357.62, DG 138.65, SPOT 599.74, EGP 200.56, TLN 347.68, PPL 35.16, NBIX 163.47, VIK 100.87.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP HSHP (Himalaya Shipping Ltd.) - filed 2026-11-24, sealed 2026-11-25T11:38:58Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-FORM4_SHARP-0001959455-26-000143`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 15.42 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001959455-26-000143` by Svensen Lars-Christian (Contracted CEO); purchases USD 103,088; top executive yes; holding up +29.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001959455-26-000143.
Twins (band+liq+mom+dd): SPTX 19.77, GSBD 7.76, ASIX 13.44, OIS 7.56, DBI 5.9, KEP 9.12, AUPH 15.21, NMFC 6.62, HTLD 9.87, GLUE 9.88, RMR 16.29, CRVS 10.34, DAKT 17.63, NEWT 10.34, DEC 12.55, CPS 18.19, SHEN 9.23, KRNY 8.8, LXU 8.94, DRTS 12.475.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D VMAR (Vision Marine Technologies Inc.) - accepted 2026-11-25T17:22:57-05:00, sealed 2026-11-25T23:04:40Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-SEC13D-0001829126-26-012896`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 4.93 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Filing `0001829126-26-012896` by Greenland Energy Co; Item 4 intent words: board, director.
Coverage **ABSTAIN** (MICROCAP); pre-entry move +0.00%, market value USD 3.5M, dilution filings 0.
Twins (band+liq+mom+dd): KG 3.3, UK 1.02, FMFC 1.255, KTCC 1.21, OFAL 1.7386.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

