# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-10T10:32:06Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 19 (FIRE 7, ABSTAIN 12) over 6 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 12, SEALED 19, SKIP_NOT_OPERATING 3, SKIP_LATE 2, SKIP_NO_TICKER 3, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 28 over 6 signal sessions; events seen: SEALED 28, SKIP_REPEAT_90D 22, SKIP_NO_TICKER 23, SKIP_NOT_IN_UNIVERSE 18, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 38 over 3 signal sessions; events seen: SEALED 38, SKIP_NOT_IN_UNIVERSE 4, SKIP_NOT_PURCHASE 3287, SKIP_LATE 41, SKIP_NO_TICKER 2, SKIP_NOT_OPERATING 2; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 38 over 3 signal sessions; events seen: SEALED 38; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 16, FIRE 22
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 17 over 5 signal sessions; events seen: SEALED 17; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 8, FIRE 9
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

121 tags: 26 true, 0 unknown.

## Latest sets

### SEC13D ENGS (Energys Group Ltd) - accepted 2026-11-09T06:20:13-05:00, sealed 2026-11-09T23:02:43Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D-0001493152-26-050601`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 4.71 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-050601` by Lau Michael Kwok Yan; Item 4 intent words: none.
Coverage **FIRE**; pre-entry move -0.84%, market value USD 67.1M, dilution filings 0.
Twins (band+liq+mom): PACB 2.36, BBAI 2.45, NAUT 2.38, PRME 4.3, ENVX 2.78.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D HIHO (HIGHWAY HOLDINGS LTD) - accepted 2026-11-09T09:30:26-05:00, sealed 2026-11-09T23:02:43Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D-0000921895-26-002960`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 0.8578 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Filing `0000921895-26-002960` by Lazar David E.; Item 4 intent words: board, nominate, director, letter.
Coverage **ABSTAIN** (MICROCAP); pre-entry move +3.35%, market value USD 4.0M, dilution filings 0.
Twins (band+liq+mom+dd): JF 0.94, CNEY 0.5198, SNGX 0.3418, INEO 0.571, CETY 0.9473.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D MERC (MERCER INTERNATIONAL INC.) - accepted 2026-11-09T17:57:28-05:00, sealed 2026-11-09T23:02:43Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D-0000919574-26-007505`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 0.241 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Filing `0000919574-26-007505` by REDWOOD CAPITAL MANAGEMENT, LLC; Item 4 intent words: board, director, letter.
Coverage **ABSTAIN** (MICROCAP); pre-entry move +0.00%, market value USD 16.2M, dilution filings 0.
Twins (band+liq+mom+dd): FMST 0.8311, CRIS 0.6976, MMA 0.3549, EDVA 0.1831, DXLG 0.44.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 GMHS (Gamehaus Holdings Inc.) - accepted 2026-11-09T06:04:18-05:00, sealed 2026-11-09T23:03:08Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D_V2-0001493152-26-050586`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 0.6265 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001493152-26-050586` by Xie Feng; cover page max 31.5% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 52.9M from COVER_PAGE; parent CAT-SEC13D-0001493152-26-050586.
Twins (band+liq+mom+dd): NSPR 0.7134, GDTC 0.859, KTTA 0.5423, SYNX 0.9023, ELUT 0.8359, RYDE 0.889, PMCB 0.407, CTXR 0.5263, HPAI 0.3687, ORKT 1.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 ENGS (Energys Group Ltd) - accepted 2026-11-09T06:20:13-05:00, sealed 2026-11-09T23:03:08Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D_V2-0001493152-26-050601`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 4.71 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001493152-26-050601` by Lau Michael Kwok Yan; cover page max 98.9% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 67.1M from XBRL; parent CAT-SEC13D-0001493152-26-050601.
Twins (band+liq+mom): PACB 2.36, BBAI 2.45, NAUT 2.38, PRME 4.3, ENVX 2.78, UWMC 1.48, QS 4.57, COTY 4.22, AMC 3.4, WIT 2.14.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 HIHO (HIGHWAY HOLDINGS LTD) - accepted 2026-11-09T09:30:26-05:00, sealed 2026-11-09T23:03:08Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D_V2-0000921895-26-002960`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 0.8578 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0000921895-26-002960` by Lazar David E.; cover page max 16.7% of class; strong intent: nominate; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (MICROCAP); market value USD 4.0M from XBRL; parent CAT-SEC13D-0000921895-26-002960.
Twins (band+liq+mom+dd): JF 0.94, CNEY 0.5198, SNGX 0.3418, INEO 0.571, CETY 0.9473, FURY 0.52, TOON 0.508, MNDO 0.87, PNBK 0.8775, GHG 0.985, MDIA 1, SACH 0.8208, BRN 0.855, MAMO 0.9487, LUCY 0.8352.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 MERC (MERCER INTERNATIONAL INC.) - accepted 2026-11-09T17:57:28-05:00, sealed 2026-11-09T23:03:08Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D_V2-0000919574-26-007505`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 0.241 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0000919574-26-007505` by REDWOOD CAPITAL MANAGEMENT, LLC; cover page max 0% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (MICROCAP); market value USD 16.2M from XBRL; parent CAT-SEC13D-0000919574-26-007505.
Twins (band+liq+mom+dd): FMST 0.8311, CRIS 0.6976, MMA 0.3549, EDVA 0.1831, DXLG 0.44, HYFM 0.77, BRLS 1, YYAI 0.9453, PMAX 0.7997, ALLR 0.9431, FBDT 0.97, SCAG 0.9261, SDA 0.44.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K ABEO - event `0001493152-26-050606`, accepted 2026-11-09T06:30:34-05:00, sealed 2026-11-09T23:03:35Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-050606`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 2.54 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -39.09%.
Twins (band+liq+mom+dd): LAES 1.45, ASPI 2.14, AGNT 3.215, RZLV 1.42, CABA 1.5.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K CRMD - event `0001213900-26-117213`, accepted 2026-11-09T07:49:44-05:00, sealed 2026-11-09T23:03:35Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-117213`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 5.47 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +2.82%.
Twins (band+liq+mom+dd): RYAM 5.69, PRAA 12.71, REAX 12.47, KE 19.83, CEPU 10.19.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K QNME - event `0001213900-26-117226`, accepted 2026-11-09T08:01:49-05:00, sealed 2026-11-09T23:03:35Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-117226`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 0.3212 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -13.89%.
Twins (band+liq+mom+dd): NMTC 0.8852, XTNT 0.279, AIFF 0.9486, AEI 0.4978, RPID 0.73.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K SSNC - event `0001193125-26-452749`, accepted 2026-11-09T08:39:35-05:00, sealed 2026-11-09T23:03:35Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-452749`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 77.89 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.23%.
Twins (band+liq+mom+dd): TTE 88, DTM 116.48, NRG 97.4, CHRW 128.99, KRYS 303.06.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K PARK - event `0001104659-26-124485`, accepted 2026-11-09T16:05:51-05:00, sealed 2026-11-09T23:03:35Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-DILUTION_8K-0001104659-26-124485`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 21 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): CMT 22.38, IGIC 23.31, AIRT 28.69, HURC 21, TWIN 24.82.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K JBS - event `0001213900-26-117580`, accepted 2026-11-09T16:52:45-05:00, sealed 2026-11-09T23:03:35Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-117580`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 13.12 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): VSTS 14.48, DV 13.56, TAC 13.65, BEKE 18.4, YMM 8.97.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D GAME (GameSquare Holdings, Inc.) - accepted 2026-11-09T18:49:19-05:00, sealed 2026-11-10T10:31:54Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D-0001493152-26-050820`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 2.58 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-050820` by Credenza, Inc.; Item 4 intent words: board, nominate, director.
Coverage **ABSTAIN** (DILUTION_RECENT); pre-entry move +0.00%, market value USD 267.8M, dilution filings 1.
Twins (band+liq+mom+dd): XBIO 1.7975, CITR 2.58, CVM 1.35, HTLM 1.08, BJDX 2.49.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 GAME (GameSquare Holdings, Inc.) - accepted 2026-11-09T18:49:19-05:00, sealed 2026-11-10T10:32:05Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-SEC13D_V2-0001493152-26-050820`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 2.58 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001493152-26-050820` by Credenza, Inc.; cover page max 5.4% of class; strong intent: nominate; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT); market value USD 267.8M from XBRL; parent CAT-SEC13D-0001493152-26-050820.
Twins (band+liq+mom+dd): GYRO 3.9, SHIM 2.33, BMHL 3.244, AMCI 1.05, KPRX 1.51, QRHC 1.15, BJDX 2.49, MYSE 1.27, FBGL 2.275, GNLN 1.16, OPAD 2.15, PAVS 3.02, TNMG 2.91, QH 2.83, SMXT 4.05, PPCB 1.76, BTOC 1.8501, ATTT 2.14, HIND 1.59, RML 3.965.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

