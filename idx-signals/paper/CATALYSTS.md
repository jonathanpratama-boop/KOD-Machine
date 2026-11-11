# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-11T10:47:29Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 22 (FIRE 8, ABSTAIN 14) over 7 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 12, SEALED 22, SKIP_NOT_OPERATING 3, SKIP_LATE 2, SKIP_NO_TICKER 4, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 34 over 7 signal sessions; events seen: SEALED 34, SKIP_REPEAT_90D 32, SKIP_NO_TICKER 23, SKIP_NOT_IN_UNIVERSE 22, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 63 over 4 signal sessions; events seen: SEALED 63, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 3715, SKIP_LATE 41, SKIP_NO_TICKER 2, SKIP_NOT_OPERATING 2, SKIP_REPEAT_90D 6; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 63 over 4 signal sessions; events seen: SEALED 63; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 25, FIRE 38
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 20 over 6 signal sessions; events seen: SEALED 20; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 10, FIRE 10
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

141 tags: 30 true, 0 unknown.

## Latest sets

### FORM4_SHARP AUDC (AUDIOCODES LTD) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001976408-26-000933`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 8.5 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001976408-26-000933` by ADLERSBERG SHABTAI (President and CEO); purchases USD 126,140; top executive yes; holding up +0.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001976408-26-000933.
Twins (band+liq+mom+dd): WATT 8.69, SUPX 5.7, SDOT 6.475, KGEI 5.24, FXHO 5.48, RFIL 7.25, ECOR 7.18, AGPU 7.5, ESOA 9.06, AMTD 13.4, RYM 17.105, OPI 13.73, NVNO 6.85, AKTX 7.66, OTLY 8.125, BDSX 10.34, BNR 12.39, NEGG 8.91, AGMB 7.55, AOMR 6.24.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NLY (ANNALY CAPITAL MANAGEMENT INC) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001994436-26-000004`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 18.95 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001994436-26-000004` by Wede Scott (director); purchases USD 940,000; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001994436-26-000004.
Twins (band+liq+mom+dd): RIVN 14.01, F 12.52, CDE 16.45, LYFT 16.76, AVTR 15.91, MMED 17.88, CTVA 12.11, CLF 12.26, RIG 5.17, ACI 12.91, SAN 12.46, LYG 5.26, SKYD 8.7, HLN 8.97, HBAN 15.92, AGNC 8.93.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP DKNG (DraftKings Inc.) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0002019299-26-000018`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 18.7 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002019299-26-000018` by Ellingson Alan Wayne (Chief Financial Officer); purchases USD 349,987; top executive yes; holding up +9.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002019299-26-000018.
Twins (band+liq+mom+dd): PATH 12.98, RGTI 12.98, HL 15.41, WULF 12.38, PCG 13.14, NVTS 9.58, AG 15.87.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D CMMB (Chemomab Therapeutics Ltd.) - accepted 2026-11-10T17:30:05-05:00, sealed 2026-11-10T23:03:19Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-SEC13D-0001493152-26-051041`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.345 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-051041` by Scipher Medicine Corp; Item 4 intent words: board, merger, director.
Coverage **ABSTAIN** (DILUTION_RECENT); pre-entry move +0.00%, market value USD 773.9M, dilution filings 1.
Twins (band+liq+mom+dd): YYAI 1.05, LEXX 4.68, SOWG 2.02, MB 3.797, CALC 1.37.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 CMMB (Chemomab Therapeutics Ltd.) - accepted 2026-11-10T17:30:05-05:00, sealed 2026-11-10T23:03:29Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-SEC13D_V2-0001493152-26-051041`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.345 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001493152-26-051041` by Scipher Medicine Corp; cover page max 10.4% of class; strong intent: none; Item 5(c): 1 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT); market value USD 773.9M from XBRL; parent CAT-SEC13D-0001493152-26-051041.
Twins (band+liq+mom+dd): YYAI 1.05, LEXX 4.68, SOWG 2.02, MB 3.797, CALC 1.37, MGN 3.4, AZR 3.76, HTCO 1.6, BCG 1.07, WYHG 3.52, WLDS 1.59, INBS 2.25, XAIR 2.52, SILO 1.79, ONEG 1.07, ENLV 1.2, IBO 4.62, LCU 4.35, XHG 3.3, CIIT 2.3.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K CKX - event `0001437749-26-035972`, accepted 2026-11-09T19:04:59-05:00, sealed 2026-11-10T23:03:54Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-DILUTION_8K-0001437749-26-035972`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 17.97 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +9.57%.
Twins (band+liq+mom+dd): UG 9.16, POCI 5.08, APT 6.25, PHAR 13.22, NL 7.15.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K CDXS - event `0001193125-26-454447`, accepted 2026-11-10T07:33:26-05:00, sealed 2026-11-10T23:03:54Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-454447`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -9.91%.
Twins (band+liq+mom+dd): CGTX 0.6702, EHTH 0.4588.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K MXCT - event `0001104659-26-124829`, accepted 2026-11-10T08:21:10-05:00, sealed 2026-11-10T23:03:54Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-DILUTION_8K-0001104659-26-124829`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.13 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -13.08%.
Twins (band+liq+mom+dd): ANTX 4.33, CAST 1.38, BLND 1.08, PRLD 3.76, FTFT 3.19.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K RXT - event `0001810019-26-000117`, accepted 2026-11-10T08:33:04-05:00, sealed 2026-11-10T23:03:54Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-DILUTION_8K-0001810019-26-000117`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 2.68 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -1.47%.
Twins (band+liq+mom+dd): RZLV 1.39, LTBR 4.53, AQST 3.52, RILY 3.66, HYLN 2.99.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K STXS - event `0001493152-26-050957`, accepted 2026-11-10T16:05:22-05:00, sealed 2026-11-10T23:03:54Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-050957`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.03 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): ELVA 4.91, TPET 1.64, PEW 1.81, METCB 3.94, RBBN 1.4.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K MTRI - event `0001193125-26-455640`, accepted 2026-11-10T16:45:24-05:00, sealed 2026-11-10T23:03:54Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-455640`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 12.2 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): CUVL 5.19, GSIW 10.17, NRDY 5.8, PCLA 6.15, GRNQ 7.44.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D PMAX (Powell Max Ltd) - accepted 2026-11-10T18:10:12-05:00, sealed 2026-11-11T10:47:04Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-SEC13D-0000921895-26-003015`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 0.8003 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Filing `0000921895-26-003015` by Hyperscale Data, Inc.; Item 4 intent words: board, director.
Coverage **ABSTAIN** (MV_UNKNOWN); pre-entry move +0.00%, market value n/a, dilution filings 0.
Twins (band+liq+mom+dd): FMST 0.695, XELB 0.431, FBDT 0.9156, MMA 0.357, DXLG 0.4198.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D LRN (Stride, Inc.) - accepted 2026-11-10T18:20:24-05:00, sealed 2026-11-11T10:47:04Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-SEC13D-0001213900-26-118179`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 76.82 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Filing `0001213900-26-118179` by Fivespan Partners, LP; Item 4 intent words: board, merger, acquisition, nominate, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 3,230.2M, dilution filings 0.
Twins (band+liq+mom+dd): IT 188.92, APA 45.12, C 122.27, URI 1104.94, ADI 393.3.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 PMAX (Powell Max Ltd) - accepted 2026-11-10T18:10:12-05:00, sealed 2026-11-11T10:47:19Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-SEC13D_V2-0000921895-26-003015`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 0.8003 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0000921895-26-003015` by Hyperscale Data, Inc.; cover page max 21.7% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (MICROCAP); market value USD 2.3M from COVER_PAGE; parent CAT-SEC13D-0000921895-26-003015.
Twins (band+liq+mom+dd): FMST 0.695, XELB 0.431, FBDT 0.9156, MMA 0.357, DXLG 0.4198, ALLR 0.9102, SCAG 0.99, BFRG 0.599, EDVA 0.17.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 LRN (Stride, Inc.) - accepted 2026-11-10T18:20:24-05:00, sealed 2026-11-11T10:47:19Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-SEC13D_V2-0001213900-26-118179`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 76.82 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001213900-26-118179` by Fivespan Partners, LP; cover page max 5.3% of class; strong intent: nominate; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 3,230.2M from XBRL; parent CAT-SEC13D-0001213900-26-118179.
Twins (band+liq+mom+dd): ALGM 30.7, LII 347.93, NTSK 21.44, IRM 110.78, CBRE 134.79, EMN 65.45, GMED 75.23, BCS 23.1, GWRE 155.48, PAYC 237.96, ADI 393.3, CEG 267.76, ATI 182.72, ANET 185.02, RBRK 109.34, CF 122.36, APA 45.12, MDGL 432.6, NRG 97.11, CFG 64.82.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

