# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-20T10:37:32Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 36 (FIRE 15, ABSTAIN 21) over 13 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 17, SEALED 36, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 69 over 13 signal sessions; events seen: SEALED 69, SKIP_REPEAT_90D 54, SKIP_NO_TICKER 34, SKIP_NOT_IN_UNIVERSE 41, SKIP_NOT_OPERATING 1; coverage gaps 1.
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

Sets 34 over 12 signal sessions; events seen: SEALED 34; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 17, FIRE 17
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

278 tags: 65 true, 0 unknown.

## Latest sets

### FORM4_SHARP ITT (ITT INC.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-468584`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 206.26 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-468584` by Berryman Kevin C (director); purchases USD 501,561; top executive no; holding up +58.8%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-468584.
Twins (band+liq+mom+dd): TTWO 208.65, ORKA 97.57, TRGP 285.42, VICI 24.19, WH 78.71, TMO 688.75, WEC 116.11, PNR 68.68, BAX 25.39, HAE 120.37, AAPL 349.21, JAZZ 236.45, AIZ 316.03, BOOT 139.37, WTW 331.26, DTE 136.13, PTC 195.63, NTSK 24.8, OPCH 31.61, IEX 227.01.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP APC (ARKO Petroleum Corp.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-468657`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 12.95 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-468657` by HEYER ANDREW R (director); purchases USD 279,000; top executive no; holding up +198.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-468657.
Twins (band+liq+mom+dd): CODA 7.75, MTLS 6.31, BALY 9.9, AGCC 11.77, HQI 13.52, VINP 8.22, DMRC 6.04, CPIX 6.3, SOHU 10.74, TG 5.65, OPRX 7.01, INGN 5.42, FORR 8.76, AMWL 10.69, RRGB 6.28, SDHC 8.2, MFIN 9.67, TRAK 5.95, AUDC 9, CHCI 14.51.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PLD (Prologis, Inc.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-468660`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 123.36 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-468660` by KELLY ALFRED F JR (director); purchases USD 587,350; top executive no; holding up +1690.6%.
Coverage **ABSTAIN** (NOT_SHARP, DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-468660.
Twins (band+liq+mom+dd): WMB 66.13, WPM 116.13, NTES 104.94, FUTU 87.21, QLYS 192.425, FND 46.38, SNX 228.14, EXE 82.44, GIS 34.48, CI 273.04, STT 161.23, BAP 342.75, FSLR 151.95, KRMN 32.99, SBAC 169.66, ON 65.72, SHEL 94.01, GS 847.53, FOUR 37.97, AEIS 212.24.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP AIRJ (AirJoule Technologies Corp.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-468951`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 1.66 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-468951` by Murphy Thomas Edward (director); purchases USD 50,183; top executive no; holding up +49.4%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-468951.
Twins (band+liq+mom+dd): FWDI 3.94, BTQ 1.14, DPRO 2, SUPV 4.76, GEMI 1.705, IAUX 1.05, XXI 4.31, IMSR 2.3, CCOI 3.15, SERV 2.29, VUZI 1.2, MDXG 3.11, GLAS 1.21, ABR 1.11, LODE 1.36, ZNTL 1.36, MNTN 4.67, SPRY 3.36, LAR 3.21, ARTV 3.83.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP DX (DYNEX CAPITAL INC) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001283563-26-000006`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 9.85 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001283563-26-000006` by BOSTON BYRON L (Co-CEO & Chairman of the Board); purchases USD 50,003; top executive yes; holding up +0.6%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001283563-26-000006.
Twins (band+liq+mom+dd): SGHC 10.55, BHVN 13.65, SHLS 7.19, RITM 8.24, NEO 15.09, ARLO 12.03, SHC 16.21, XRAY 8.49, TAL 10.02, EQPT 14.11, ADNT 15.08, WTTR 16.07, GNTX 19.17, GENI 5.82, MUFG 19.65, PTEN 9.72, RLAY 15.91, YELP 18.56, PZZA 18.35, GNW 7.69.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP IRTC (iRhythm Holdings, Inc.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001316065-26-000016`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 94.24 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001316065-26-000016` by TALWALKAR ABHIJIT Y (director); purchases USD 763,706; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001316065-26-000016.
Twins (band+liq+mom+dd): GOOGL 272.66, DVN 42.05, UNM 77.04, APTV 37.36, TPL 277.72, HPQ 27.82, RNG 67.26, ENS 132.5, CTSH 56.31, SUPN 28.35, BROS 34.15, NWSA 25.31, FLUT 68.42, SM 29.34, ILMN 200.655, ANF 137.64, FTNT 131.46, CVS 80.04, GMED 68.6, PLTR 153.68.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BCML (BayCom Corp) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-037732`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 30.05 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-037732` by PERDUE MICHAEL J (director); purchases USD 151,000; top executive no; holding up +62.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001437749-26-037732.
Twins (band+liq+mom+dd): TSBK 45.6, SBFG 27.99, WTBA 28.8, FCCO 31.62, EFSI 44.4, OVBC 45.43, RGCO 21.49, ATMP 33.8813, FSBW 41.55, BSET 21.07, BPRN 43.31, IGIC 23.84, FNWD 41.69, FNLC 35.42, GCBC 34.3, PKBK 31.38, CFBK 33.96, DCBO 29.39, FXNC 28.91, TCI 45.77.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SKYH (Sky Harbour Group Corp) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-037735`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 10.94 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-037735` by GESSOW ANDREW J (director); purchases USD 56,400; top executive no; holding up +21.8%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001437749-26-037735.
Twins (band+liq+mom+dd): GRFS 8.2, ZGN 13.71, AOUT 18.54, PUBM 19.8, BBDC 8.36, RSKD 9.63, MATW 19.37, PERI 11.08, VLRS 8.09, HLMN 7.79, CASK 16.87, GBDC 12.3, INN 7.18, FVR 18.06, DDI 15.35, LILAK 9.42, CHCT 14.29, MOBI 11.86, YALA 5.69, SVRA 5.21.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CRVO (CervoMed Inc.) - filed 2026-11-19, sealed 2026-11-20T10:36:58Z, cutoff 2026-11-20T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-037784`, scan `SCAN-US-2026-11-19-G2_RET30`; signal close 1.33 on 2026-11-19; entry: the entry session's opening print (2026-11-20). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-037784` by ALAM JOHN J (CEO & President); purchases USD 152,621; top executive yes; holding up +6.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001437749-26-037784.
Twins (band+liq+mom+dd): EXFY 1.57, CDXS 1.05, ELTX 1.5, SSII 1.28, MRDN 3.76, HURA 1.36, CURR 1.87, HSCS 2.03, VIVO 1.67, BMM 2.73, CANG 1.64, ICU 1.05, PSNY 2.53, BWEN 2.16, PMN 3.21, QTRX 2.03, MGNX 1.98, TAOX 1.73, ALTG 4.73, ACET 2.46.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

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

