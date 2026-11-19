# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-19T10:38:25Z). Nothing here is a result until a look is reached.

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

Sets 215 over 10 signal sessions; events seen: SEALED 215; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 89, FIRE 126
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

### FORM4_SHARP PAL (Proficient Auto Logistics, Inc) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-121624`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 2.96 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-121624` by Gattoni James B (director), Lal Rohit (director); purchases USD 244,200; top executive no; holding up +97.4%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001213900-26-121624.
Twins (band+liq+mom+dd): ARMP 3.17, HTCO 1.31, FTFT 3.76, XCH 3.34, PZG 1.02, RETO 4.87, MGN 3.7, BESS 2.54, TRVG 4.39, STAK 1.88, FISN 2.71, RGP 2.54, VCIG 3.0401, FFTT 2.82, NUWE 3.89.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP RILY (BRC Group Holdings, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-121662`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 3.03 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-121662` by RILEY BRYANT R (Chairman and Co-CEO); purchases USD 116,767; top executive yes; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001213900-26-121662.
Twins (band+liq+mom+dd): CTMX 1.88, CCCC 2.475, JBI 3.23, DFDV 2.61, ACDC 2.84, WRD 3.67, ALMS 4.395, BIOA 4.77, ALOY 4.51, CYH 1.86, KOPN 2.98, TMQ 1.85, AUTL 1.06, NFGC 1.27, UPB 2.08, JMIA 2.74, NEWP 4.9, LTBR 3.63, ARTV 3.77, USAS 2.17.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP XTIA (XTI Aerospace, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-121959`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 0.8801 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-121959` by Evans Allan Thomas (director); purchases USD 86,874; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001213900-26-121959.
Twins (band+liq+mom+dd): IBIO 0.8481, LUCD 0.4095, CRMT 0.8291, CRIS 0.6143.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BA (BOEING CO) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001225208-26-009059`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 162.91 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001225208-26-009059` by JOHRI AKHIL (director); purchases USD 500,067; top executive no; holding up +2000.0%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001225208-26-009059.
Twins (band+liq+mom+dd): HTFL 45.89, NTAP 172.19, IT 178.84, SHOP 140.42, RVMD 159.82, NWSA 26.13, ASML 1395.27, DK 60.32, AFRM 58.91, NEU 703.23, BKR 47.375, PSX 244.83, SUPN 28.96, HXL 77.54, PBF 62.39, SM 28.82, VEEV 277.2, MTCH 39.6, MRNA 196.79, GOOGL 282.44.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP FLNA (FILANA THERAPEUTICS, INC.) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-037544`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 0.545 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-037544` by Cook Robert Christopher (Chief Operating& Legal Officer), Barry Richard (President & CEO); purchases USD 262,821; top executive yes; holding up +885.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001437749-26-037544.
Twins (band+liq+mom+dd): GLDG 0.6769, SOAR 0.1651, BZFD 0.4037, LDI 0.4445, QUCY 0.584, VIVK 0.2501, MEDS 0.739, KSCP 0.39, NBP 0.9031, CNTX 0.1664, SKYX 0.5634, DBGI 0.188, NMG 0.7455, OGI 0.6766, INVZ 0.1447, OPTT 0.3167, AMOD 0.7829, DEFT 0.2839, AARD 0.91, MVIS 0.8711.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP USAR (USA Rare Earth, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001458423-26-000012`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 6.56 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001458423-26-000012` by BLITZER MICHAEL (director); purchases USD 2,996,645; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001458423-26-000012.
Twins (band+liq+mom+dd): CIFR 6.57, VALE 10.04, IBRX 6.7, EQX 9.17, PATH 11.73, FSLY 17.9, QBTS 7.69, INIO 13.59, BMNR 15.47, EMBJ 18.77, AG 11.92, UPST 18.08, PBR 16.73, IOVA 7.48, APLD 14.45, HL 11.67, CAI 19.5, HBM 17.875, KGC 18.97, RDW 6.82.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP VIVO (VivoPower PLC) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-053023`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 1.82 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-053023` by Chin Kevin (Chairman & CEO); purchases USD 553,910; top executive yes; holding up +9.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001493152-26-053023.
Twins (band+liq+mom+dd): SRI 5, ADAG 1.82, HRZN 3.09, CNTN 1.335, MNTS 1.96, GSIT 2.755, DGNX 1.03, STEM 1.155, SY 1.83, IFRX 1.095, GYRE 4.61, PEW 1.35, PASW 1.39, ATNM 1.08, ELVA 3.905, GRDX 3.36, MSGM 3.69, ARAI 1.85, MGNX 1.97, IPSC 1.38.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP STXS (Stereotaxis, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-053130`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 0.9461 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-053130` by Menawat Arun Swarup (director); purchases USD 99,984; top executive no; holding up +11.7%.
Coverage **ABSTAIN** (NOT_SHARP, DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001493152-26-053130.
Twins (band+liq+mom+dd): ALDX 0.6711, CRDF 0.839, WWR 0.368, MRLN 0.8702, NPWR 0.9907, NMRA 0.3668, SRXH 1, BLNK 0.3909.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CRC (California Resources Corp) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001609253-26-000163`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 44.61 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001609253-26-000163` by Bremner Andrew B. (director); purchases USD 99,682; top executive no; holding up +7.1%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001609253-26-000163.
Twins (band+liq+mom+dd): WK 66.43, TX 47.36, LIFE 32.54, ARQT 27.61, IDCC 276.58, HWC 62.05, DDS 577.19, INSP 58.11, TEN 44.07, WBI 25.6, HRMY 33.11, SKYW 80.97, TFII 93.99, AMSC 22.495, NHC 201.6, NICE 90.96, WIX 63.54, DGII 55.93, RELY 20.605, EFOR 32.3.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP EFC (Ellington Financial Inc.) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-074680`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 10.81 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-074680` by Penn Laurence (CEO and President); purchases USD 106,540; top executive yes; holding up +9.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-074680.
Twins (band+liq+mom+dd): TLK 11.71, FLG 10.26, PBI 15.18, CC 12.09, WU 6.23, FLO 5.25, CLBT 11.16, PSNL 14.98, BCRX 7.3, MBC 6.31, WT 20, RITM 8.31, NIQ 17.38, IRT 14.695, ARLO 12.06, ADNT 15.44, BRSL 9.21, RVLV 19.4, GNTX 19.01, DXC 14.37.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP DDD (3D SYSTEMS CORP) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-074826`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 1.38 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-074826` by KEVER JIM D (director); purchases USD 572,000; top executive no; holding up +71.3%.
Coverage **ABSTAIN** (NOT_SHARP, DILUTION_RECENT); dilution filings 3; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-074826.
Twins (band+liq+mom+dd): CYH 1.86, SION 2.97, JMIA 2.74, WFF 1.02, BNC 3.39, AIRJ 1.755, WVE 2.77, ALOY 4.51, JBI 3.23, BTGO 3.63, LTRX 3.93, YSS 3.78, MITT 3.9, ALMS 4.395, SERV 2.4, DGXX 2.075, QTEX 1.12, KOPN 2.98, PSFE 2.98, MNTN 4.61.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP GWRS (Global Water Resources, Inc.) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-074877`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 6.48 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-074877` by Cohn Andrew M. (director); purchases USD 169,910; top executive no; holding up +0.9%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-074877.
Twins (band+liq+mom+dd): AGBK 5.81, INGN 5.57, LGCY 7.88, AMWL 11.03, CPIX 6.57, CODA 8.105, SOHU 10.85, FORR 8.92, AP 6.69, HQI 14.1, NRT 6.81, KWY 8.27, BALY 10.65, EPSN 5.24, OPRX 7.31, VINP 8.53, MFIN 9.69, TG 5.57, MTLS 6.36, AUDC 8.86.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NTB (Bank of N.T. Butterfield & Son Ltd) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001653242-26-000144`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 54.83 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001653242-26-000144` by Lynch Mark T (director); purchases USD 164,850; top executive no; holding up +1.3%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001653242-26-000144.
Twins (band+liq+mom+dd): JILL 21.735, PKE 24.27, SMC 30.56, PLOW 37.09, YSWY 21.29, NVGS 20.15, APEI 42.53, BCH 37.18, CWCO 24.83, IFS 49.67, BKTI 59.66, MLR 47.87, PXED 20.56, ITIC 256.56, BSAC 30.36, ASTE 36.78, EVTC 30.81, ZBIO 26.42, PRK 171.12, NWPX 88.45.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TISI (TEAM INC) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0001782810-26-000011`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 24.43 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001782810-26-000011` by Hill Gary L. (Chief Executive Officer); purchases USD 96,096; top executive yes; holding up +8.1%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001782810-26-000011.
Twins (band+liq+mom+dd): ESEA 60.2, SEG 20.1, DJP 46.31, ARTNA 32.18, CMT 22.14, HBB 30.28, MNSB 20.72, INBK 24.785, TWIN 23.34, IGIC 23.9, PPIH 27.71, HNVR 21.69, OLP 21.06, BOTJ 25, KEN 58.07, ISTR 27.24.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP AROW (ARROW FINANCIAL CORP) - filed 2026-11-18, sealed 2026-11-19T10:37:50Z, cutoff 2026-11-19T14:15:00Z
Set `CAT-FORM4_SHARP-0002045771-26-000010`, scan `SCAN-US-2026-11-18-G2_RET30`; signal close 37.18 on 2026-11-18; entry: the entry session's opening print (2026-11-19). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002045771-26-000010` by White Daniel James (director); purchases USD 99,837; top executive no; holding up +31.2%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002045771-26-000010.
Twins (band+liq+mom+dd): AVBC 21.89, CCNE 34.56, GABC 48.52, BSVN 57.07, IMKTA 85.07, HIPO 36.83, IRMD 82.31, TCBK 50.08, CWBC 24.46, SFST 58.49, DSGR 35.05, ORRF 42.41, FMBH 49.33, WS 38.29, RBCAA 89.28, PBAM 84.905, FSBC 42.6, IBCP 35.5, SYBT 76.91, BHRB 69.24.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

