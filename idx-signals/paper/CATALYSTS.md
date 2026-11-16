# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-16T23:33:40Z). Nothing here is a result until a look is reached.

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

Sets 57 over 10 signal sessions; events seen: SEALED 57, SKIP_REPEAT_90D 46, SKIP_NO_TICKER 25, SKIP_NOT_IN_UNIVERSE 30, SKIP_NOT_OPERATING 1; coverage gaps 1.
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

### DILUTION_8K GLND - event `0001829126-26-012430`, accepted 2026-11-13T19:11:07-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001829126-26-012430`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.99 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -6.13%.
Twins (band+liq+mom+dd): ABTC 4.71, STLN 3.54, VELO 3.545, CRBP 3.375, OGG 2.15.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K NINE - event `0001213900-26-120080`, accepted 2026-11-16T06:30:57-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-120080`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 7.08 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -4.58%.
Twins (band+liq+mom+dd): FGI 5.23, VEEE 6.87, FTLF 6.83, LVLU 6.6208, ELTK 5.9.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K AKBA - event `0001517022-26-000089`, accepted 2026-11-16T08:12:50-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001517022-26-000089`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 0.4486 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -5.36%.
Twins (band+liq+mom+dd): RR 0.7395, OPTU 0.6273, SIDU 0.9027, EYPT 0.3076, IQ 0.6801.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K ARCT - event `0001193805-26-001485`, accepted 2026-11-16T08:30:51-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001193805-26-001485`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 8.31 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -0.60%.
Twins (band+liq+mom+dd): STDN 9.33, RYAM 5.3, ALMU 6.185, KC 6.87, PBYI 7.34.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K IPW - event `0001683168-26-008776`, accepted 2026-11-16T09:00:15-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001683168-26-008776`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.19 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -4.03%.
Twins (band+liq+mom+dd): DTI 1.63, QMLS 2.42, BIRD 1.2, NTWK 4.33, SRTS 2.34.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K GH - event `0001193125-26-463573`, accepted 2026-11-16T16:19:16-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-463573`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 144.03 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): POWL 151.2, PR 22.31, MDGL 423.96, UBS 47.61, KEX 127.86.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K FANG - event `0001104659-26-128377`, accepted 2026-11-16T16:24:04-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001104659-26-128377`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 177.41 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): TJX 131.09, FUTU 91.6, SCCO 153.87, GEV 763.57, IFF 79.99.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K VANI - event `0001753926-26-002153`, accepted 2026-11-16T16:30:32-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001753926-26-002153`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 1.02 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): GNPX 1.9, GLOO 2.87, NVA 2.95, METCB 3.56, HOLO 1.09.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K EPR - event `0001193125-26-463901`, accepted 2026-11-16T17:20:53-05:00, sealed 2026-11-16T23:33:26Z, cutoff 2026-11-17T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-463901`, scan `SCAN-US-2026-11-16-G2_RET30`; signal close 60.21 on 2026-11-16; entry: the entry session's opening print (2026-11-17). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): FSV 155.87, ABM 54.64, YOU 56.18, BKSY 23.15, SPNT 26.42.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

