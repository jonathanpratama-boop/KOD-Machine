# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-24T10:30:29Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 42 (FIRE 18, ABSTAIN 24) over 15 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 21, SEALED 42, SKIP_NOT_OPERATING 9, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 3; coverage gaps 1.

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

Sets 75 over 15 signal sessions; events seen: SEALED 75, SKIP_REPEAT_90D 61, SKIP_NO_TICKER 52, SKIP_NOT_IN_UNIVERSE 47, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 257 over 12 signal sessions; events seen: SEALED 257, SKIP_NOT_IN_UNIVERSE 8, SKIP_NOT_PURCHASE 8976, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 9, SKIP_REPEAT_90D 93; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 257 over 12 signal sessions; events seen: SEALED 257; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 111, FIRE 146
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 40 over 14 signal sessions; events seen: SEALED 40; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 20, FIRE 20
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

330 tags: 80 true, 0 unknown.

## Latest sets

### FORM4_SHARP SEI (Solaris Energy Infrastructure, Inc.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075232`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 54.67 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075232` by Zartler William A (Chairman and Co-CEO), Brock Amanda M (Co-Chief Executive Officer), Ramachandran Kyle S. (President); purchases USD 641,090; top executive yes; holding up +1.9%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 3; parent CAT-FORM4-0001628280-26-075232.
Twins (band+liq+mom+dd): XYL 94.66, OXY 53.9, ESI 29.52, PCVX 55.39, HSBC 80.02, ADBE 217.71, BWXT 108.54, SYF 67.76, XYZ 69.66, CVLT 145.9, IBKR 71.19, VST 115.25, MLI 49.85, Q 103.47, SCI 69.14, JBHT 218.54, DHT 21.58, DVA 161.03, PR 21.15, CTSH 58.06.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TMS (Teamshares Inc) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075322`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 3.91 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075322` by Eu Alexander Zai De (President); purchases USD 109,530; top executive yes; holding up +8.4%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 2; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075322.
Twins (band+liq+mom+dd): MWYN 1.19, SBMT 4.55, SMX 2.7, TENX 1.25, SEAT 1.56, RCT 1.49, COYA 2.95, STI 2.89, DFNS 1.21, CNTN 1.21, PRQR 1.04, BBDO 2.09, METCB 2.77, MDAI 1.04, GRDX 3.16, VATE 3.55, BBOT 1.81, UPLD 1.5, SHMD 1.57, WKHS 1.75.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TJX (TJX COMPANIES INC /DE/) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001664921-26-000002`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 139.62 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001664921-26-000002` by PINTOFF CRAIG ADAM (director); purchases USD 199,823; top executive no; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001664921-26-000002.
Twins (band+liq+mom+dd): MAA 112.91, MNST 43.69, OKE 84.37, TD 112.87, RY 183.45, PLD 122.5, EWBC 121.54, TDY 598.56, PNFP 92.56, PAYC 241.64, RL 366.65, BMO 156.29, NUE 239.62, TFC 45.81, IEX 219.64, LMT 565.5, UHS 179.43, FCNCA 2075.52, LOGI 97.21, SRE 76.16.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP VANI (Vivani Medical, Inc.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001753926-26-002210`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 1.14 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001753926-26-002210` by Williams Gregg (director); purchases USD 128,325; top executive no; holding up +0.3%.
Coverage **ABSTAIN** (DILUTION_RECENT, ROUTINE); dilution filings 1; routine owners 1 of 1; parent CAT-FORM4-0001753926-26-002210.
Twins (band+liq+mom+dd): CCLD 2.02, FLX 1.48, ENGN 1.74, GECC 4.88, ONL 2.23, ABLV 2.16, APYX 2.4, CAMP 3.79, TZOO 4.96, FPH 4.35, GNLX 2.17, CHOW 3.36, CURV 2.14, LZM 3.88, KRMD 3.19, LUNG 2.57, TMCI 4.31, FBIO 1.9, ASLE 4.93, CMTG 1.41.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BHRB (Burke & Herbert Financial Services Corp.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001945031-26-000015`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 67.81 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001945031-26-000015` by Poillon Diane (director); purchases USD 106,131; top executive no; holding up +36.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001945031-26-000015.
Twins (band+liq+mom+dd): NBBK 21.06, SPFI 40.54, HAFC 30.47, FISI 38.24, IDT 73.72, FCBC 44.55, AMAL 46.84, FBNC 60.74, KARO 59.45, UVSP 38.41, CNOB 30.3, CARE 28.41, UFCS 49.78, VLGEA 40.61, JMSB 22.22, BSVN 55.94, BHB 39.06, CZFS 80.7, BBSI 30.5, AROW 36.57.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TSM (TAIWAN SEMICONDUCTOR MANUFACTURING CO LTD) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0002114032-26-000002`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 318.71 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002114032-26-000002` by Lu Lee-Chung (VP); purchases USD 302,850; top executive no; holding up +33.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002114032-26-000002.
Twins (band+liq+mom+dd): MCHP 55.44, TPL 267.44, SU 63.82, GFS 35.56, UNF 228.42, IRTC 94.72, KBR 31.44, INTU 270.44, IT 174.49, PLTR 143.49, BKR 44.81, FSLR 137.59, EXPE 234.96, NTAP 157.65, OSCR 24.73, MELI 1355, BROS 32.78, ZS 194.82, ASML 1266.22, NWSA 25.05.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ESEA (EUROSEAS LTD.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0002127484-26-000025`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 58.59 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002127484-26-000025` by Pittas Aristeidis P (director); purchases USD 58,976; top executive no; holding up +1.6%.
Coverage **ABSTAIN** (NOT_SHARP, DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0002127484-26-000025.
Twins (band+liq+mom+dd): OFLX 21.15, AIRT 21.43, OLP 20.64, TWIN 21.21, TAYD 53.16, HNVR 21.37, NKSH 36.86, INBK 24.28, PPIH 25.5, ELMD 22.98, KEN 54.16, DJP 45.97, NC 30.2, MNSB 20.13, HBB 28.91, SMID 20.68, DCBO 27.82, SBR 60.83.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### DILUTION_8K ALTG - event `0001193125-26-472368`, accepted 2026-11-23T16:15:23-05:00, sealed 2026-11-23T23:07:02Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-472368`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 4.61 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): AMPG 1.85, AISP 1.52, WRN 1.28, SRI 4.26, HRZN 3.23.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K INHD - event `0001493152-26-053790`, accepted 2026-11-23T16:45:22-05:00, sealed 2026-11-23T23:07:02Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-053790`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 1.92 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): EZGO 1.62, ASTC 3.58, LOBO 2.38, LFT 3.35, OPAD 1.31.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D WIX (Wix.com Ltd.) - accepted 2026-11-23T18:35:18-05:00, sealed 2026-11-24T10:29:44Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-SEC13D-0001418812-26-000003`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 62.88 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Filing `0001418812-26-000003` by VA Partners I, LLC; Item 4 intent words: board, merger, acquisition, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 3,457.7M, dilution filings 0.
Twins (band+liq+mom+dd): PARR 63.41, GEF 66.27, KMT 23.17, NGVT 57.11, RHI 38.55.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D MNTS (Momentus Inc.) - accepted 2026-11-23T20:33:42-05:00, sealed 2026-11-24T10:29:44Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-SEC13D-0000905148-26-005136`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 2.05 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Filing `0000905148-26-005136` by OA3, LLC; Item 4 intent words: board, merger, acquisition, strategic alternatives, director.
Coverage **ABSTAIN** (MICROCAP); pre-entry move +0.00%, market value USD 49.3M, dilution filings 0.
Twins (band+liq+mom+dd): EQ 1.14, DTI 1.63, VYGR 1.58, EDSA 2.38, ELTX 1.46.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D HPK (HighPeak Energy, Inc.) - accepted 2026-11-23T21:33:19-05:00, sealed 2026-11-24T10:29:44Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-SEC13D-0001437749-26-038124`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 6.55 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Filing `0001437749-26-038124` by PT Danantara Energy International; Item 4 intent words: board, merger, strategic alternatives, director, letter.
Coverage **ABSTAIN** (DILUTION_RECENT); pre-entry move +0.00%, market value USD 828.8M, dilution filings 1.
Twins (band+liq+mom+dd): IDR 14.86, OFIX 6.17, KE 19.21, GENB 10.21, LIME 19.69.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 WIX (Wix.com Ltd.) - accepted 2026-11-23T18:35:18-05:00, sealed 2026-11-24T10:30:15Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-SEC13D_V2-0001418812-26-000003`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 62.88 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001418812-26-000003` by VA Partners I, LLC; cover page max 7.0% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 3,457.7M from XBRL; parent CAT-SEC13D-0001418812-26-000003.
Twins (band+liq+mom+dd): PARR 63.41, GEF 66.27, KMT 23.17, NGVT 57.11, RHI 38.55, LPG 45.84, FTRE 20.38, AGIO 28.65, TNET 62.97, VAL 71.6, WBI 24.95, PRDO 27.81, MGY 22.3, MTDR 47.46, NE 37.73, IMO 114.73, LAUR 32.53, DGII 56.07, DFTX 29.33, NBR 70.39.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 MNTS (Momentus Inc.) - accepted 2026-11-23T20:33:42-05:00, sealed 2026-11-24T10:30:15Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-SEC13D_V2-0000905148-26-005136`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 2.05 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0000905148-26-005136` by OA3, LLC; cover page max 10.6% of class; strong intent: strategic alternatives; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (MICROCAP); market value USD 49.3M from XBRL; parent CAT-SEC13D-0000905148-26-005136.
Twins (band+liq+mom+dd): EQ 1.14, DTI 1.63, VYGR 1.58, EDSA 2.38, ELTX 1.46, HOVR 1.12, FAC 3.65, TONX 2.59, MGNX 2.16, GANX 1.03, MX 2.34, FHTX 1.92, TGEN 1.76, LUCK 3.74, IPSC 1.32, NSLR 4.94, NEOV 2.11, KULR 1.44, IKT 1.43, GALT 2.8.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 HPK (HighPeak Energy, Inc.) - accepted 2026-11-23T21:33:19-05:00, sealed 2026-11-24T10:30:15Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-SEC13D_V2-0001437749-26-038124`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 6.55 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001437749-26-038124` by PT Danantara Energy International; cover page max 17.2% of class; strong intent: strategic alternatives; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT); market value USD 828.8M from XBRL; parent CAT-SEC13D-0001437749-26-038124.
Twins (band+liq+mom+dd): IDR 14.86, OFIX 6.17, KE 19.21, GENB 10.21, LIME 19.69, OFRM 11.75, ENTA 8.06, SSYS 5.32, XPRO 11.93, AVBP 11.26, BBAR 9.2, CRESY 8.21, BCAX 8.75, YARW 12.94, AGRO 7.93, EAF 8.02, NRDS 7.43, NPKI 8.57, HIMX 7.86, GILT 5.01.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

