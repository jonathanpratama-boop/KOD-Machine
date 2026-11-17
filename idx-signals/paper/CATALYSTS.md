# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-17T23:03:49Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 33 (FIRE 12, ABSTAIN 21) over 11 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 14, SEALED 33, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 5, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 168 over 8 signal sessions; events seen: SEALED 168; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 66, FIRE 102
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

### FORM4_SHARP OPAL (OPAL Fuels Inc.) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-074148`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.21 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-074148` by Sutton Scott McDougald (director); purchases USD 61,500; top executive no; holding up +100.0%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-074148.
Twins (band+liq+mom+dd): ADCT 1.25, SXTC 2.99, GMTL 4.1, NAKA 4.59, DAVA 1.4, SOTK 4.135, YDES 4.83, ZSQR 2.22, ARAY 2.55, BRAI 1.68, SCYX 2.91, MOVE 4.7, AVX 3.62, ASTI 1.19, ZONE 3.15, NXDT 2.89, VYGR 1.63, CANG 1.47, LNZA 2.81, AMTX 1.18.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP REI (RING ENERGY, INC.) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-074217`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.11 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-074217` by Johl Sundip Singh (EVP, Chief Financial Officer); purchases USD 70,087; top executive yes; holding up +10.6%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-074217.
Twins (band+liq+mom+dd): NXDR 2.04, CIG 1.86, AMPY 4.03, AIOT 2.22, NUS 3.93, CYH 2.13, VOXR 4.36, ALVO 4.405.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TG (TREDEGAR CORP) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-074262`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 5.64 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-074262` by DasGupta Arijit (See Remarks); purchases USD 96,730; top executive no; holding up +12.1%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-074262.
Twins (band+liq+mom+dd): NATR 10.56, USCB 19.78, INGN 5.63, AGCC 13.52, MFIN 9.4, MTLS 6.21, EPSN 5.3, CDRO 8.2, SMHI 7.58, VINP 8.53, ELA 9.84, LGCY 8.02, GBFH 15, CODA 8.32, BALY 10.82, NRT 7.03, SOHU 11.17, FORR 8.82, AUDC 8.79, MRBK 16.48.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PED (PEDEVCO CORP) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001654954-26-009873`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 10.76 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001654954-26-009873` by Howie John K (director); purchases USD 53,000; top executive no; holding up +28.7%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001654954-26-009873.
Twins (band+liq+mom+dd): USAU 9.87, AKTX 6.51, MAKO 6.91, HQI 13.52, PTHS 7.15, MPAA 7.55, AMTD 13.29, RYM 12.23, AP 6.23, PXS 5.47, CHRN 9.39, SIF 14.74, WATT 7.4, APLM 17.84, HQ 11, ENHA 5.86, CPIX 5.21, BCIC 5.22, RVII 14.18, GFUZ 5.25.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP YUMC (Yum China Holdings, Inc.) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001673358-26-000169`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 51.45 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001673358-26-000169` by DIMITRIEF ALEXANDER (director); purchases USD 247,500; top executive no; holding up +135.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001673358-26-000169.
Twins (band+liq+mom+dd): CMCSA 25.6, JXN 137.59, CUBE 44.85, ED 121.88, FE 47.55, SHW 350.54, USFD 108.19, VOYA 102.47, AJG 287, BRZE 46.57, BAM 50.89, MDLN 39.17, SO 94.64, QGEN 49.81, CHYM 34.29, REGN 952.4, FNF 44.39, JD 27.54, SWK 112.92, UMBF 134.4.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ADIG (ADI GLOBAL DISTRIBUTION INC.) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001753285-26-000006`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 9.3 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001753285-26-000006` by Lane Jeannine J (Exec. VP, GC, Corp. Sec. & CCO), Aarnes Robert B (President and CEO), Carlet Michael (Executive VP, CFO), Copeland Alicia Crispin (Executive VP and COO); purchases USD 300,523; top executive yes; holding up +25.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 4; parent CAT-FORM4-0001753285-26-000006.
Twins (band+liq+mom+dd): SSYS 5.82, GLUE 9.16, CPS 18.21, CLB 8.45, HPK 7.8, PRAA 11.43, WW 9.46, GRRR 6.46, HNRG 10.17, NEXA 10.66, ADAM 5.08, METC 6.15, CADL 5.81, RYAM 5.3, BBAR 9.83, RMIX 5.32, ETD 16.84, LU 7.09, LAND 6.46, JANX 10.92.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP AOMR (Angel Oak Mortgage REIT, Inc.) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001766478-26-000074`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 5.59 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001766478-26-000074` by MINAMI W D (director); purchases USD 53,255; top executive no; holding up +10.5%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001766478-26-000074.
Twins (band+liq+mom+dd): PMI 7.24, ENHA 5.86, AEHL 7.6, NREF 11.34, LMNR 9.89, BRCC 8.05, OCC 9.84, VTVT 17.69, MAAS 9.88, BCIC 5.22, OPRX 6.64, ATYR 5.24, MSB 15.96, NEGG 8.62, NLOP 7.71, MAKO 6.91, OESX 11.98, ALTG 5.17, RVII 14.18, EDN 13.02.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP IMRX (Immuneering Corp) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001790340-26-000105`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 3.52 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001790340-26-000105` by Gengos Andrew (Chief Financial Officer); purchases USD 89,500; top executive yes; holding up +11.1%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001790340-26-000105.
Twins (band+liq+mom+dd): PACK 3.08, CCCC 2.65, RXT 2.515, VZLA 2.93, QSI 1.06, TENX 1.48, WRD 3.98, RCKT 2.16, EH 3.4, CWH 4.12, KDK 1.08, WVE 2.87, VNDA 3.81.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP KTOS (KRATOS DEFENSE & SECURITY SOLUTIONS, INC.) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001803860-26-000005`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 31.66 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001803860-26-000005` by King David Arnold (director); purchases USD 201,091; top executive no; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001803860-26-000005.
Twins (band+liq+mom+dd): WDC 280.93, OKLO 23.03, PAAS 35.58, ASX 32.8, SANM 153.815, IESC 165.9, EGO 30.11, LEU 97.53, SMTC 105.3, MSTR 103.03, SMCI 25.025, FN 311.01, MTSI 220.44, TWST 105.04, VSH 25.37, DDOG 172.86, MU 719.02, COHR 203.43, AAOI 45.16, CIEN 257.56.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP GERN (GERON CORP) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001809747-26-000002`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 0.9419 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001809747-26-000002` by Semerjian Harout (President & CEO); purchases USD 50,825; top executive yes; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001809747-26-000002.
Twins (band+liq+mom+dd): SLNH 0.4571, IQ 0.6801, AKBA 0.4486, RR 0.7395, JDZG 0.1389, RBNE 0.135, OPTU 0.6273, NAK 0.5501, DVLT 0.028, EYPT 0.3076, SIDU 0.9027, AREC 0.9, SID 0.6217, SDEV 0.7055, URG 0.5591, SITC 0.71, XRX 0.9217, EU 0.5127, SHFS 0.023, CENN 0.14.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PCT (PureCycle Technologies, Inc.) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001847066-26-000009`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.68 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001847066-26-000009` by Musa Fernando (Executive Chairman); purchases USD 98,496; top executive no; holding up +17.5%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001847066-26-000009.
Twins (band+liq+mom+dd): POET 4.66, FLNC 4.29, NAUT 2.1, ENVX 1.42, KOS 2.06, ASM 4.03, CRML 4.19, BULL 4.9, UNIT 4.79, QS 3.43, NUVB 3.84, RXRX 2.905, FRMI 2.48, LAC 1.41, VISN 3.95, SOUN 3.23, DJT 4.08, LZ 4.86, OI 4.76, ABR 1.17.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP HL (HECLA MINING CO/DE/) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0001866675-26-000007`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 12.22 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001866675-26-000007` by Andres Dale (director); purchases USD 125,000; top executive no; holding up +200.0%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001866675-26-000007.
Twins (band+liq+mom+dd): FSLY 15.86, CLSK 6.3, KGC 19.94, AG 12.67, UMC 14.34, ASST 18.81, APLD 14.58, GLXY 13.14, IBRX 5.98, HIMS 18.56, CDE 13.12, INIO 13.82, IREN 16.39, CIFR 6.54, RDW 7.05, XP 14.83, QBTS 8.67, BMNR 16.26, PBR 17.3, HBM 19.55.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP LEGN (Legend Biotech Corp) - filed 2026-11-16, sealed 2026-11-17T10:37:24Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-FORM4_SHARP-0002088468-26-000008`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 15.99 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002088468-26-000008` by Salovey Peter (director); purchases USD 183,250; top executive no; holding up +36.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002088468-26-000008.
Twins (band+liq+mom+dd): STNE 8.01, LBRT 12.25, MBLY 5.26, UMAC 10.59, MLYS 14.53, UEC 6.13, BZ 12.67, BLSH 19.75, SVM 8.06, ATEC 6.78, ABSI 7.475, SLM 16.31, SLS 7.47, APPS 7.06, EXK 7.15, ALHC 7.47, AADX 6.81, LPTH 6.16, SNDX 9.13, SECZ 7.33.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D TDTH (Trident Digital Tech Holdings Ltd) - accepted 2026-11-17T06:06:15-05:00, sealed 2026-11-17T23:03:46Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-SEC13D-0001213900-26-121050`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 1.16 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Filing `0001213900-26-121050` by Lim Soon Huat; Item 4 intent words: board.
Coverage **ABSTAIN** (MOVED_ALREADY, MV_UNKNOWN); pre-entry move +18.61%, market value n/a, dilution filings 0.
Twins (band+liq+mom+dd): LNKS 1.01, RYOJ 2.4901, NCI 4.8971, CALC 1.22, NPT 1.79.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D FF (FutureFuel Corp.) - accepted 2026-11-17T16:30:06-05:00, sealed 2026-11-17T23:03:46Z, cutoff 2026-11-18T14:15:00Z
Set `CAT-SEC13D-0001493152-26-052855`, scan `SCAN-US-2026-11-17-G2_RET30`; signal close 3.06 on 2026-11-17; entry: the entry session's opening print (2026-11-18). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-052855` by 222 Capital, U/I dated March 25, 2003; Item 4 intent words: board, merger, acquisition, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 134.2M, dilution filings 0.
Twins (band+liq+mom+dd): EDIT 1.825, PICS 4.83, TMC 1.86, DGXX 2.04, NNBR 2.77.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

