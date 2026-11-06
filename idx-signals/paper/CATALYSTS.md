# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-06T23:03:16Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 12 (FIRE 5, ABSTAIN 7) over 5 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 10, SEALED 12, SKIP_NOT_OPERATING 3, SKIP_LATE 2, SKIP_NO_TICKER 3, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 19 over 4 signal sessions; events seen: SEALED 19, SKIP_REPEAT_90D 11, SKIP_NO_TICKER 15, SKIP_NOT_IN_UNIVERSE 14; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 27 over 2 signal sessions; events seen: SEALED 27, SKIP_NOT_IN_UNIVERSE 4, SKIP_NOT_PURCHASE 2793, SKIP_LATE 41, SKIP_NO_TICKER 2, SKIP_NOT_OPERATING 1; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 27 over 2 signal sessions; events seen: SEALED 27; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 10, FIRE 17
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 10 over 4 signal sessions; events seen: SEALED 10; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 5, FIRE 5
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

63 tags: 12 true, 0 unknown.

## Latest sets

### FORM4_SHARP TRAD (APEX Tech Acquisition Inc.) - filed 2026-11-05, sealed 2026-11-06T10:42:45Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-FORM4_SHARP-0001477932-26-006731`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 10.1 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001477932-26-006731` by Liu Shaoren (CEO and CFO), APEX INNOVATION ACQUISITION CORP. (officer); purchases USD 2,089,710; top executive yes; holding up +7.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001477932-26-006731.
Twins (band+liq+mom+dd): PBHC 16.72, AFJK 12.21, GIX 10.01, SOUL 10.53, BRTM 9.76, NBRG 10.15, APT 5.48, DTSQ 11.519, BYFC 11.52, APAC 10.31, LEGO 9.96, NTIC 7.58, OCAC 10, CXII 10.352, GTEN 10.44, NL 7.1, MBBC 14.4, PGAC 10.83, ARCL 10, TLIH 5.7.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SPXC (SPX Technologies, Inc.) - filed 2026-11-05, sealed 2026-11-06T10:42:45Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-FORM4_SHARP-0001490816-26-000002`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 138.54 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001490816-26-000002` by Deck Brian A (director); purchases USD 493,020; top executive no; holding up +404.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001490816-26-000002.
Twins (band+liq+mom+dd): RMBS 69.68, AMAT 319.25, AMKR 30.49, FFIV 311.74, RKLB 45.99, MTSI 190.35, WOLF 20.36, ARM 166.72, IONQ 26.43, CW 433.87, ASST 20.59, MU 656.39, SANM 130.23, FN 292.97, ASX 29.72, MP 33.74, AMD 404.4, TWLO 200.96, CIEN 230.81, HBM 20.58.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP LBRT (Liberty Energy Inc.) - filed 2026-11-05, sealed 2026-11-06T10:42:45Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-071186`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 11.35 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-071186` by Gusek Ron (CEO and President); purchases USD 377,335; top executive yes; holding up +2.4%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-071186.
Twins (band+liq+mom+dd): EFXT 18.87, ALM 7.95, EROC 6.64, NN 8.03, UNIT 5.365, BCAX 8.19, MBLY 5.13, MLYS 15.24, AEVA 9.19, UGP 5.56, QUBT 5.63, CSQR 13.72, PPTA 16.75, KURA 6.8, FLNC 5.095, HLIT 9.31, ORIC 8.49, ADEA 14.82, ATEC 7.8, BTU 16.02.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SYY (SYSCO CORP) - filed 2026-11-05, sealed 2026-11-06T10:42:45Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-FORM4_SHARP-0001685591-26-000006`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 75.24 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001685591-26-000006` by Ondrof Thomas Gerard (director); purchases USD 191,550; top executive no; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001685591-26-000006.
Twins (band+liq+mom+dd): MANE 128.6, EQNR 42.54, TECK 59.91, PSX 247.04, BMRN 56.12, OKE 86.25, MTB 219.78, RVMD 177.65, TEAM 183.29, WPM 132.46, PTGX 135.26, UNF 243.2, AR 36.38, ATI 168.34, UPST 22.14, STLD 221.895, XYL 100.05, HESM 30.3, JBHT 218.99, JAZZ 227.32.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP RRBI (RED RIVER BANCSHARES INC) - filed 2026-11-05, sealed 2026-11-06T10:42:45Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-FORM4_SHARP-0001770071-26-000012`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 104.48 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001770071-26-000012` by Price Teddy Ray (director); purchases USD 112,606; top executive no; holding up +20.5%.
Coverage **ABSTAIN** (ROUTINE); dilution filings 0; routine owners 1 of 1; parent CAT-FORM4-0001770071-26-000012.
Twins (band+liq+mom+dd): CCBG 50.34, ALRS 33.85, HBNC 20.85, CBNK 42.6, MSEX 59.5, YSWY 25.09, ATLC 96.45, EVER 30.32, PDLB 21.83, SYBT 79.31, JAKK 32.99, CLMB 39.85, ACNB 65.49, WPP 27.94, RM 37.62, SRCE 87.35, BSVN 58.44, IBTA 57.85, NX 20.92, MBIN 52.14.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP MTDR (Matador Resources Co) - filed 2026-11-05, sealed 2026-11-06T10:42:45Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-FORM4_SHARP-0002020286-26-000011`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 49.87 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002020286-26-000011` by Calvert Christopher P (EVP and CFO); purchases USD 105,140; top executive yes; holding up +4.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002020286-26-000011.
Twins (band+liq+mom+dd): TJX 138.59, PTGX 135.26, BCS 22.82, UPST 22.14, TVTX 48.87, AU 88.56, KMX 52.6, RAL 62.83, STNG 80.74, CARR 53.21, NFLX 65.56, GPC 124.44, TECK 59.91, BAP 347.99, TNGX 20.87, NUE 245.68, ODFL 170.56, ALK 38.7, WWD 306.855, FTI 61.59.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CBAN (COLONY BANKCORP INC) - filed 2026-11-05, sealed 2026-11-06T10:42:45Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-FORM4_SHARP-0002051327-26-000020`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 19.95 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002051327-26-000020` by Canup Edward G (CHIEF BANKING OFFICER); purchases USD 60,645; top executive no; holding up +7.2%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002051327-26-000020.
Twins (band+liq+mom+dd): INNV 9.09, EGY 5.38, SXC 9.7, SOPH 6.62, FLGT 18.66, PAYP 14.54, AURA 6.34, NEXN 8.97, CION 6.6, LYTS 17.79, KREF 5.71, ZVRA 10.53, CTOS 9.3, CLB 8.93, EOLS 6.795, ASPN 5.16, ATS 17.32, ALLT 8.18, OOMA 17.56, NEWT 10.67.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D NIPG (NIP Group Inc.) - accepted 2026-11-06T06:36:23-05:00, sealed 2026-11-06T23:02:42Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D-0001493152-26-050350`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 3.72 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-050350` by Tang Heng; Item 4 intent words: none.
Coverage **FIRE**; pre-entry move +1.92%, market value USD 421.8M, dilution filings 0.
Twins (band+liq+mom+dd): HCAI 2.79, ARTL 1.91, SNAL 1.95, CLRB 1.25, MDBH 1.55.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D AIFU (AIFU Inc.) - accepted 2026-11-06T08:30:01-05:00, sealed 2026-11-06T23:02:42Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D-0001213900-26-116624`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 7.681 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Filing `0001213900-26-116624` by Zhang Zack; Item 4 intent words: board, director.
Coverage **FIRE**; pre-entry move -10.37%, market value USD 8,712.1M, dilution filings 0.
Twins (band+liq+mom+dd): VEEE 8.27, FEDU 7.9, AIOS 8.6465, AUC 6.56, GRNQ 7.1.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D SVIA (Silvia, Inc.) - accepted 2026-11-06T16:29:39-05:00, sealed 2026-11-06T23:02:42Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D-0001493152-26-050478`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 3.005 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-050478` by Noor Shain; Item 4 intent words: merger, director.
Coverage **ABSTAIN** (DILUTION_RECENT); pre-entry move +0.00%, market value USD 265.6M, dilution filings 3.
Twins (band+liq+mom+dd): SION 3.28, NRXP 2.38, TMQ 2.15, ACDC 3.005, TNXP 4.74.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D XYF (X Financial) - accepted 2026-11-06T16:35:32-05:00, sealed 2026-11-06T23:02:42Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D-0001104659-26-123916`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 5.75 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Filing `0001104659-26-123916` by Mangrove Coast Investment Ltd; Item 4 intent words: board, acquisition, director, letter.
Coverage **ABSTAIN** (MV_UNKNOWN); pre-entry move +0.00%, market value n/a, dilution filings 0.
Twins (band+liq+mom+dd): NL 7.13, CLST 17.5, WSBK 13.61, PHAR 12.29, CURX 6.21.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 NIPG (NIP Group Inc.) - accepted 2026-11-06T06:36:23-05:00, sealed 2026-11-06T23:03:10Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D_V2-0001493152-26-050350`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 3.72 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001493152-26-050350` by Tang Heng; cover page max 9.4% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 421.8M from XBRL; parent CAT-SEC13D-0001493152-26-050350.
Twins (band+liq+mom+dd): HCAI 2.79, ARTL 1.91, SNAL 1.95, CLRB 1.25, MDBH 1.55, ITOC 1.7201, BTOC 1.83, LFT 4.12, DCX 1.095, PLSM 1.5101, SEAT 2.09, EZGO 1.715, FOXX 1.6, NEXM 1.27, BJDX 2.35, GLE 2.63, EDSA 2.14, BCHT 1.15, DCM 2.98, HCTI 3.7.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 AIFU (AIFU Inc.) - accepted 2026-11-06T08:30:01-05:00, sealed 2026-11-06T23:03:10Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D_V2-0001213900-26-116624`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 7.681 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001213900-26-116624` by Zhang Zack; cover page max 56.12% of class; strong intent: none; Item 5(c): 3 price(s).
Coverage **FIRE**; market value USD 8,712.1M from XBRL; parent CAT-SEC13D-0001213900-26-116624.
Twins (band+liq+mom+dd): VEEE 8.27, FEDU 7.9, AIOS 8.6465, AUC 6.56, GRNQ 7.1, VRM 6.53, VHC 9.71, MFI 5.1, PXLW 5.06, TRIB 5.7, ZOOZ 5.28, CMND 5.5838, ELTK 5.9812, ROMA 6.05, NTRB 5.55, AERT 5.43, BRBI 7.31, BKHA 5.63, PTN 6.27, BBGI 5.9.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 SVIA (Silvia, Inc.) - accepted 2026-11-06T16:29:39-05:00, sealed 2026-11-06T23:03:10Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D_V2-0001493152-26-050478`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 3.005 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001493152-26-050478` by Noor Shain; cover page max 5.6% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT); market value USD 265.6M from XBRL; parent CAT-SEC13D-0001493152-26-050478.
Twins (band+liq+mom+dd): SION 3.28, NRXP 2.38, TMQ 2.15, ACDC 3.005, TNXP 4.74, STTK 4.62, TWI 4.93, GLAS 2.08, ANGX 3.39, AREC 1.09, ALLO 1.04, STLN 3.62, ARTV 4.15, TROX 2.51, FATE 1.835, AMPY 3.33, IMSR 2.84, OEC 3.96, RXT 2.53, KYTX 4.88.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 XYF (X Financial) - accepted 2026-11-06T16:35:32-05:00, sealed 2026-11-06T23:03:10Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D_V2-0001104659-26-123916`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 5.75 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001104659-26-123916` by Mangrove Coast Investment Ltd; cover page max 47.97% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 1,328.9M from COVER_PAGE; parent CAT-SEC13D-0001104659-26-123916.
Twins (band+liq+mom+dd): NL 7.13, CLST 17.5, WSBK 13.61, PHAR 12.29, CURX 6.21, SHPH 5.585, KFFB 5.93, BSBK 9.38.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

