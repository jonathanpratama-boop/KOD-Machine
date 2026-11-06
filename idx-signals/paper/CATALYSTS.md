# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-06T00:26:57Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 8 (FIRE 3, ABSTAIN 5) over 4 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 8, SEALED 8, SKIP_NOT_OPERATING 2, SKIP_LATE 2, SKIP_NO_TICKER 2; coverage gaps 1.

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

Sets 7 over 3 signal sessions; events seen: SEALED 7, SKIP_REPEAT_90D 7, SKIP_NO_TICKER 5, SKIP_NOT_IN_UNIVERSE 7; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 9 over 1 signal sessions; events seen: SEALED 9, SKIP_NOT_IN_UNIVERSE 1, SKIP_NOT_PURCHASE 252; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 9 over 1 signal sessions; events seen: SEALED 9; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 5, FIRE 4
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 6 over 3 signal sessions; events seen: SEALED 6; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 4, FIRE 2
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

41 tags: 9 true, 0 unknown.

## Latest sets

### FORM4_SHARP HBAN (HUNTINGTON BANCSHARES INC /MD/) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001225208-26-008552`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 15.97 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001225208-26-008552` by TORGOW GARY (director); purchases USD 199,834; top executive no; holding up +1.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001225208-26-008552.
Twins (band+liq+mom+dd): OWL 10.41, CPNG 14.57, CAG 14.09, ACI 12.79, JBS 12.16, WY 19.75.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP XYL (Xylem Inc.) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001524472-26-000150`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 90.76 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001524472-26-000150` by KOCH D CHRISTIAN (director); purchases USD 985,600; top executive no; holding up +882.1%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001524472-26-000150.
Twins (band+liq+mom+dd): MTZ 177.82, AMKR 41.21, CORT 85.95, AAOI 79.19, INTC 92.07, UCTT 54.7, LPLA 279.54, STRL 373.66, FIX 1326.23, APP 254.91, CAT 647.39, DOCN 99.97, VICR 206.62, STX 700.47, ONTO 221.89, VIAV 33.32, MP 41.64, RDDT 129.6, ALGM 33.03, AGI 28.83.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TFC (TRUIST FINANCIAL CORP) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001534574-26-000018`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 49.32 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001534574-26-000018` by Lyons Michael P. (President & CEO); purchases USD 1,209,050; top executive yes; holding up +119.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001534574-26-000018.
Twins (band+liq+mom+dd): AOS 63.49, CTAS 218.07, ABBV 290.79, RPRX 65.93, LH 368.16, GRAL 158.92, GH 185.31, ES 67.9, CCK 118.2, XEL 79.04, SPGI 460.66, SNY 43.13, PTC 194.8, WTFC 154.13, REGN 818.77, QLYS 230.29, SRE 85.89, CINF 181.87, MNST 46.35, BIO 384.4.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BBT (Beacon Financial Corp) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-068056`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 30.66 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-068056` by Callahan Mary Anne (director); purchases USD 96,672; top executive no; holding up +18.4%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-068056.
Twins (band+liq+mom+dd): EPAC 39.42, ENR 23.15, WKC 37.21, MGY 26.22, DIN 35.16, ENSG 186.32, WAY 28.21, MMSI 93.39, SMG 61.87, TILE 36.87, AWR 85.35, BSY 39.655, KBR 38.32, GFF 102.92, WGO 30.23, XHR 20.72, ABM 53.93, CACC 575.78, PAGP 28.82, SMA 35.76.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP UTMD (UTAH MEDICAL PRODUCTS INC) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001733614-26-000005`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 66.8 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001733614-26-000005` by CORNWELL KEVIN L (Chairman, CEO); purchases USD 66,750; top executive yes; holding up +0.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001733614-26-000005.
Twins (band+liq+mom+dd): PKX 50.91, GLIBK 21.61, CMCL 21.4, XRN 30.52, ATNI 25.88, IFS 49.35, CWCO 26.76, REX 38.86, CVLG 28.82, CVEO 30.55, PS 49.15, KOP 41.86, HBB 32.51, FLXS 75.57, SII 106.65, MPTI 69.02, WF 67.67, ODC 73.26, NVGS 21.71, HBCP 61.37.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D LEE (LEE ENTERPRISES, Inc) - accepted 2026-10-30T12:28:03-04:00, sealed 2026-10-30T23:02:22Z, cutoff 2026-11-02T14:15:00Z
Set `CAT-SEC13D-0002011620-26-000006`, scan `SCAN-US-2026-10-30-G2_RET30`; signal close 6.12 on 2026-10-30; entry: the entry session's opening print (2026-11-02). Windows: H20: entry +1, hold 20.
Filing `0002011620-26-000006` by Quint Digital Ltd; Item 4 intent words: board, acquisition, director.
Coverage **FIRE**; pre-entry move -1.61%, market value USD 136.4M, dilution filings 0.
Twins (band+liq+mom+dd): AIFU 9.8, LIVE 7.3001, NYC 5.96, FGI 7.91, NXTT 5.3.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 LEE (LEE ENTERPRISES, Inc) - accepted 2026-10-30T12:28:03-04:00, sealed 2026-10-30T23:02:29Z, cutoff 2026-11-02T14:15:00Z
Set `CAT-SEC13D_V2-0002011620-26-000006`, scan `SCAN-US-2026-10-30-G2_RET30`; signal close 6.12 on 2026-10-30; entry: the entry session's opening print (2026-11-02). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0002011620-26-000006` by Quint Digital Ltd; cover page max 14.4% of class; strong intent: none; Item 5(c): no transactions.
Coverage **FIRE**; market value USD 136.4M from XBRL; parent CAT-SEC13D-0002011620-26-000006.
Twins (band+liq+mom+dd): AIFU 9.8, LIVE 7.3001, NYC 5.96, FGI 7.91, NXTT 5.3, VHC 9.48, VMAR 6.26.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K PTHS - event `0001104659-26-120457`, accepted 2026-10-30T09:17:39-04:00, sealed 2026-10-30T23:02:40Z, cutoff 2026-11-02T14:15:00Z
Set `CAT-DILUTION_8K-0001104659-26-120457`, scan `SCAN-US-2026-10-30-G2_RET30`; signal close 9.4 on 2026-10-30; entry: the entry session's opening print (2026-11-02). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -43.17%.
Twins (band+liq+mom+dd): OCC 11.53, AIRO 5.16, ESOA 9.4, CNL 10.5, MF 8.35.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K RAPP - event `0001193125-26-441851`, accepted 2026-10-30T17:12:36-04:00, sealed 2026-10-30T23:02:40Z, cutoff 2026-11-02T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-441851`, scan `SCAN-US-2026-10-30-G2_RET30`; signal close 25.05 on 2026-10-30; entry: the entry session's opening print (2026-11-02). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): TSAT 40.09, JBSS 53.9, ASMB 20.13, CYD 22.45, OPY 86.2.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D MSIF (MSC INCOME FUND, INC.) - accepted 2026-11-04T17:15:23-05:00, sealed 2026-11-06T00:26:23Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-SEC13D-0001396440-26-000153`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 12.25 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Filing `0001396440-26-000153` by Main Street Capital CORP; Item 4 intent words: none.
Coverage **FIRE**; pre-entry move -0.73%, market value USD 555.5M, dilution filings 0.
Twins (band+liq+mom+dd): FRBT 19.15, DIBS 6.04, FINW 13.67, MOBI 11.28, GLRE 16.38.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D YCBD (cbdMD, Inc.) - accepted 2026-11-04T19:16:08-05:00, sealed 2026-11-06T00:26:23Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-SEC13D-0001437749-26-035032`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 0.388 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Filing `0001437749-26-035032` by Akretive Holdings LLC; Item 4 intent words: nominate, director.
Coverage **ABSTAIN** (DILUTION_RECENT, MICROCAP); pre-entry move -4.43%, market value USD 4.3M, dilution filings 1.
Twins (band+liq+mom+dd): VRXA 0.9522, SXTP 0.9164, ALLR 0.9759, PMCB 0.3752, BFRI 0.8078.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D PRSO (Peraso Inc.) - accepted 2026-11-04T19:45:37-05:00, sealed 2026-11-06T00:26:23Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-SEC13D-0001193125-26-447929`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 0.3502 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Filing `0001193125-26-447929` by Nant Capital, LLC; Item 4 intent words: board, director.
Coverage **ABSTAIN** (DILUTION_RECENT, MICROCAP); pre-entry move -12.45%, market value USD 5.3M, dilution filings 2.
Twins (band+liq+mom+dd): BLNK 0.4081, VJET 0.569, BLNE 0.607, CRDF 0.7553, QNC 0.8601.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 MSIF (MSC INCOME FUND, INC.) - accepted 2026-11-04T17:15:23-05:00, sealed 2026-11-06T00:26:53Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-SEC13D_V2-0001396440-26-000153`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 12.25 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001396440-26-000153` by Main Street Capital CORP; cover page max None% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 555.5M from XBRL; parent CAT-SEC13D-0001396440-26-000153.
Twins (band+liq+mom+dd): FRBT 19.15, DIBS 6.04, FINW 13.67, MOBI 11.28, GLRE 16.38, PERI 11.41, HYNE 18.67, NODK 15.39, OSG 5.14, SPOK 11.75, PBFS 18.235, SKYH 10, TCX 11.92, LAW 5.62, FGBI 11.78, LYEL 15, BOC 13.98, LCNB 19.53.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 YCBD (cbdMD, Inc.) - accepted 2026-11-04T19:16:08-05:00, sealed 2026-11-06T00:26:53Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-SEC13D_V2-0001437749-26-035032`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 0.388 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001437749-26-035032` by Akretive Holdings LLC; cover page max 15.9% of class; strong intent: nominate; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT, MICROCAP); market value USD 4.3M from XBRL; parent CAT-SEC13D-0001437749-26-035032.
Twins (band+liq+mom+dd): VRXA 0.9522, SXTP 0.9164, ALLR 0.9759, PMCB 0.3752, BFRI 0.8078, SEED 0.7098, VGAS 0.984, INTZ 0.621, MERC 0.2493, RYDE 0.676, HPAI 0.2811, MBIO 0.394, XCUR 0.8901, MRKR 0.8955, ICMB 0.6104, FBDT 0.8599, AGIG 0.831, BLIN 0.6688, AURE 0.9503, APRE 0.4953.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 PRSO (Peraso Inc.) - accepted 2026-11-04T19:45:37-05:00, sealed 2026-11-06T00:26:53Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-SEC13D_V2-0001193125-26-447929`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 0.3502 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001193125-26-447929` by Nant Capital, LLC; cover page max 19.99% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT, MICROCAP); market value USD 5.3M from XBRL; parent CAT-SEC13D-0001193125-26-447929.
Twins (band+liq+mom+dd): BLNK 0.4081, VJET 0.569, BLNE 0.607, CRDF 0.7553, QNC 0.8601, CNTB 0.7317, FNGR 0.107, NMG 0.805, AIAI 0.9086, ARAY 0.1239, ZENA 0.6532, WHLR 0.4582, CODX 0.2671, UAVS 0.3101, CJMB 0.286, GLDG 0.75, CIRC 0.205, ACH 0.2981, AIIO 0.4004, SKYX 0.681.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

