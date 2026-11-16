# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-16T23:32:44Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 29 (FIRE 11, ABSTAIN 18) over 10 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 14, SEALED 29, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 5, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 48 over 9 signal sessions; events seen: SEALED 48, SKIP_REPEAT_90D 42, SKIP_NO_TICKER 25, SKIP_NOT_IN_UNIVERSE 27, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 139 over 7 signal sessions; events seen: SEALED 139, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 5649, SKIP_LATE 41, SKIP_NO_TICKER 4, SKIP_NOT_OPERATING 3, SKIP_REPEAT_90D 25; coverage gaps 0.
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

Sets 27 over 9 signal sessions; events seen: SEALED 27; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 14, FIRE 13
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

220 tags: 55 true, 0 unknown.

## Latest sets

### FORM4_SHARP NXGL (NEXGEL, INC.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-051920`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 3.88 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-051920` by Kieser Brian Joseph (Interim CEO); purchases USD 732,688; top executive yes; holding up n/a.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001493152-26-051920.
Twins (band+liq+mom+dd): TORO 3.81, UPC 1.51, PAVM 1.63, EZGO 1.57, KTCC 1.3, SYPR 1.06, CSAI 1.42, PFAI 2.75, WXM 2.68, EDSA 1.94, SKYE 1.09, NSRX 2.87, INHD 2.65, HCTI 3.66, DUKR 2.02, NEUP 2.55, THH 1.2, SONM 2.17, KLRS 1.575, NXTS 2.21.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CRVS (Corvus Pharmaceuticals, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001610717-26-000454`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 10.64 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001610717-26-000454` by Arcara Jeffrey (Chief Business Officer); purchases USD 50,475; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001610717-26-000454.
Twins (band+liq+mom+dd): RXST 5.32, OPRT 11.73, LOVE 15.14, WBTN 9.85, KRRO 13.61, NMR 9.7, OIS 8.57, BUUU 5.32, CXM 6.8, FOSL 8.43, SHOE 14.36, SB 8.29, MSDL 13.84, TKNO 8.21, EPRX 8.15, OPFI 5.94, ELMT 19.83, INTT 13.73, ANGO 11.87, PLAY 8.02.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CTEV (Claritev Corp) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-073944`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 26.82 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-073944` by Dalton Travis (Pres., CEO & Executive Chair); purchases USD 149,927; top executive yes; holding up +9.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-073944.
Twins (band+liq+mom+dd): NBTX 30.655, DMRA 21.6, TYRA 20.025, GIBO 75.65, ASMB 21.12, MNPR 72, SPRB 43.31.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BW (Babcock & Wilcox Enterprises, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001630805-26-000089`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 4.56 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001630805-26-000089` by Tato Joseph A (director); purchases USD 52,692; top executive no; holding up +4.8%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001630805-26-000089.
Twins (band+liq+mom+dd): GT 4.12, LCID 2.955, NUAI 3.2, ORC 4.68, DCH 4.69.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP UPST (Upstart Holdings, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001832812-26-000012`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 19.56 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001832812-26-000012` by Gu Paul (Chief Executive Officer); purchases USD 1,028,400; top executive yes; holding up +38.5%.
Coverage **ABSTAIN** (ROUTINE); dilution filings 0; routine owners 1 of 1; parent CAT-FORM4-0001832812-26-000012.
Twins (band+liq+mom+dd): CDE 13.98, FSLY 16.62, RGTI 9.62, PBR 18.34, IBRX 6.02, CIFR 6.86, BMNR 17.58, QBTS 9.56, IOVA 7.76, FIG 19.45, IREN 18.17, XP 15.49, VALE 11.22, CTVA 9.43, HL 13.1, ONDS 5.16, INIO 14.57, CLSK 6.65, GLXY 14.38, UMC 15.4.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ABCL (AbCellera Biologics Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001834411-26-000010`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 11.49 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001834411-26-000010` by Booth Andrew (Chief Financial Officer); purchases USD 97,438; top executive yes; holding up +1.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001834411-26-000010.
Twins (band+liq+mom+dd): BBNX 16.42, GENI 6.26, HTGC 15.87, EFC 11.11, VIR 9.96, AMPX 7.93, VSTM 8.18, PZZA 19.92, CRSR 11.78, PGY 16.87, PTEN 10.97, FLG 10.48, NOV 18.09, IRT 14.96, SMMT 14.15, DEI 9.9, VIPS 13.26, BRSL 9.81, WSE 11.23, HAFN 9.59.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CTRI (Centuri Holdings, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001981599-26-000139`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 21.82 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001981599-26-000139` by MARIUCCI ANNE L (director), Patton Charles R. (director); purchases USD 349,910; top executive no; holding up +37.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001981599-26-000139.
Twins (band+liq+mom+dd): SBRA 20.44, HTO 60.56, ULS 80.36, MGNI 29.29, EXPO 87.31, SAIL 20.79, EBC 22.88, THG 248.26, HIW 31.07, INGM 28.42, AKR 20.21, OUT 33.54, PEB 21.62, RYAAY 57.72, JBTM 125.54, CGON 74.4, BIPC 39.56, ALSN 126.69, TRNO 66.95, TNL 78.65.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP KEEL (Keel Infrastructure Corp.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0002115914-26-000003`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 1.86 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002115914-26-000003` by Freedman Amy (director); purchases USD 76,100; top executive no; holding up +57.5%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002115914-26-000003.
Twins (band+liq+mom+dd): INTR 4.15, CYPH 1.87, SATL 3.3, NUVB 3.99, PONY 4.46, DNN 2.06, LZ 4.99, PGEN 4.54, ZURA 1.24, HTZ 1.5, ENVX 1.6, RCAT 3.8, MPT 1.67, PCT 1.705, ASM 4.29, LAC 1.49, UNIT 4.88, QS 3.68, FLNC 4.68, HIVE 1.57.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CRESY (CRESUD INC) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0002119764-26-000036`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 9.74 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002119764-26-000036` by Elsztain Alejandro Gustavo (director); purchases USD 89,000; top executive no; holding up +1.3%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002119764-26-000036.
Twins (band+liq+mom+dd): SD 13.04, MTRX 9.19, TTAM 11.25, PAYP 14.35, USNA 13.24, GPRK 9.42, TLX 9.23, MNRO 10.48, ILPT 6.07, PAX 9.17, MH 11.6, CEPU 10.86, GTE 9.47, ALLT 7.95, ZVRA 9.08, OBE 9.89, AGBK 6.26, VTS 15.42, RMR 16.75, MASS 9.74.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D BANL (CBL International Ltd) - accepted 2026-11-16T09:20:59-05:00, sealed 2026-11-16T23:32:15Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-SEC13D-0001493152-26-052084`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 3.225 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-052084` by Chia Teck Lim; Item 4 intent words: board, acquisition, director.
Coverage **FIRE**; pre-entry move +3.70%, market value USD 88.7M, dilution filings 0.
Twins (band+liq+mom+dd): ONEG 1.08, XRTX 1.04, SPHL 2.35, JEM 2.85, ANTA 2.185.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D AZTR (Azitra, Inc.) - accepted 2026-11-16T17:15:45-05:00, sealed 2026-11-16T23:32:15Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-SEC13D-0000945621-26-001427`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 0.627 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Filing `0000945621-26-001427` by Young Pharmaceuticals, Inc.; Item 4 intent words: board, director.
Coverage **ABSTAIN** (MICROCAP); pre-entry move +0.00%, market value USD 3.8M, dilution filings 0.
Twins (band+liq+mom+dd): BMR 0.8743, YDDL 1, BIOX 0.1997, ICCM 0.7601, RMCF 0.691.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D FUN (Six Flags Entertainment Corporation/NEW) - accepted 2026-11-16T18:01:33-05:00, sealed 2026-11-16T23:32:15Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-SEC13D-0000919574-26-008157`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 11.61 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Filing `0000919574-26-008157` by H PARTNERS MANAGEMENT, LLC; Item 4 intent words: board, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 1,187.8M, dilution filings 0.
Twins (band+liq+mom): MLTX 11.73, SBH 18.75, TIC 10.39, AMPL 17.77, CAPR 8.3.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 BANL (CBL International Ltd) - accepted 2026-11-16T09:20:59-05:00, sealed 2026-11-16T23:32:40Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-SEC13D_V2-0001493152-26-052084`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 3.225 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001493152-26-052084` by Chia Teck Lim; cover page max 41.5% of class; strong intent: none; Item 5(c): no transactions.
Coverage **FIRE**; market value USD 88.7M from XBRL; parent CAT-SEC13D-0001493152-26-052084.
Twins (band+liq+mom+dd): ONEG 1.08, XRTX 1.04, SPHL 2.35, JEM 2.85, ANTA 2.185, TVRD 1.1, CALC 1.19, ENLV 1.12, MGN 3.53, IMMP 3.4, LBGJ 1.7, AZR 3.81, REVB 3.82, CLLS 1.04, EPOW 3.3, LVO 2.72, WYHG 3.11, LGVN 2.14, FCUV 4.72, VRXA 1.045.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 AZTR (Azitra, Inc.) - accepted 2026-11-16T17:15:45-05:00, sealed 2026-11-16T23:32:40Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-SEC13D_V2-0000945621-26-001427`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 0.627 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0000945621-26-001427` by Young Pharmaceuticals, Inc.; cover page max 5.22% of class; strong intent: none; Item 5(c): 14 price(s).
Coverage **ABSTAIN** (MICROCAP); market value USD 3.8M from XBRL; parent CAT-SEC13D-0000945621-26-001427.
Twins (band+liq+mom+dd): BMR 0.8743, YDDL 1, BIOX 0.1997, ICCM 0.7601, RMCF 0.691, AZIO 0.4748, DCX 0.6902, SST 0.9333, SCKT 0.4074, CTOR 0.535, PETS 0.8977, INAB 0.816, VS 0.735, TOVX 0.14, BFRI 0.57, BTMD 0.9603, ACTU 0.268, VRAX 0.448, ZTG 0.3583, NMTC 0.745.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 FUN (Six Flags Entertainment Corporation/NEW) - accepted 2026-11-16T18:01:33-05:00, sealed 2026-11-16T23:32:40Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-SEC13D_V2-0000919574-26-008157`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 11.61 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0000919574-26-008157` by H PARTNERS MANAGEMENT, LLC; cover page max 7.2% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 1,187.8M from XBRL; parent CAT-SEC13D-0000919574-26-008157.
Twins (band+liq+mom): MLTX 11.73, SBH 18.75, TIC 10.39, AMPL 17.77, CAPR 8.3, BHVN 13.8, MAX 14.86, RDY 14.7, EQPT 14.51, CALY 16.96, XPEV 9.67, IMNM 17.61, ARHS 13.27, VERX 18.4, WEN 8.47, HAYW 16.2, PZZA 19.89, XRAY 8.945, OTF 9.42, KD 16.69.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

