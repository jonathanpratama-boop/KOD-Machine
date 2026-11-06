# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-06T10:28:47Z). Nothing here is a result until a look is reached.

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

Sets 19 over 4 signal sessions; events seen: SEALED 19, SKIP_REPEAT_90D 11, SKIP_NO_TICKER 15, SKIP_NOT_IN_UNIVERSE 14; coverage gaps 1.
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

63 tags: 12 true, 0 unknown.

## Latest sets

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

### DILUTION_8K PODC - event `0001213900-26-116003`, accepted 2026-11-04T17:00:57-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-116003`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 1.77 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -17.67%.
Twins (band+liq+mom+dd): NCTY 2.565, MDBH 1.5001, ANPA 1.16, CLRB 1.15, DWSN 1.58.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K EVMN - event `0001193125-26-447608`, accepted 2026-11-04T17:10:44-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-447608`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 6.37 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +5.46%.
Twins (band+liq+mom+dd): PESI 12.84, QFIN 5.46, SVC 5.5, SLDB 6.18, CIM 7.92.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K YCBD - event `0001437749-26-034991`, accepted 2026-11-04T17:28:37-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001437749-26-034991`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 0.388 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -4.43%.
Twins (band+liq+mom+dd): MRKR 0.8955, APRE 0.4953, NHTC 0.849, HPAI 0.2811, AGIG 0.831.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K DDD - event `0001193125-26-448362`, accepted 2026-11-05T06:02:43-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-448362`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 1.67 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -36.74%.
Twins (band+liq+mom+dd): ITG 4.23, ATOM 2.605, BLDP 1.46, LTBR 3.99, BAK 1.06.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K VST - event `0001140361-26-042013`, accepted 2026-11-05T06:02:54-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001140361-26-042013`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 112.89 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -6.15%.
Twins (band+liq+mom+dd): LRCX 185.2, MU 656.39, HBM 20.58, BE 167.52, SMTC 91.54.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K BRC - event `0000746598-26-000052`, accepted 2026-11-05T07:05:10-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0000746598-26-000052`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 79.79 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -3.68%.
Twins (band+liq+mom+dd): SLF 73.48, HWC 71.41, TMDX 68.98, EDU 53.96, IMAX 48.13.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K ENHA - event `0001628280-26-070679`, accepted 2026-11-05T09:20:39-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001628280-26-070679`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 8.17 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +14.91%.
Twins (band+liq+mom+dd): ACFN 14.53, OTLY 7.7, LMNR 10.41, AOMR 6.17, NOA 9.44.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K CYCU - event `0001493152-26-050228`, accepted 2026-11-05T16:05:25-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-050228`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 2.24 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): TLSI 3.53, JELD 1.01, LPCN 1.53, MGNX 2.22, BBDO 2.37.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K XEL - event `0001193125-26-449951`, accepted 2026-11-05T16:24:52-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-449951`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 80.37 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): NKE 39.56, CI 301.48, EL 107.65, NTES 126.56, REGN 902.9.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K SUNS - event `0001628280-26-071144`, accepted 2026-11-05T16:47:58-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001628280-26-071144`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 6.68 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): CNL 12.47, DMAC 9.04, BOOM 7.055, NPCE 12.69, SLSR 7.01.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K AXON - event `0001628280-26-071150`, accepted 2026-11-05T16:54:17-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001628280-26-071150`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 382.56 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): ARWR 57.46, CELC 64.04, PRAX 262.59, ALB 98.37, AMBA 55.17.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K ISPC - event `0001213900-26-116431`, accepted 2026-11-05T17:00:14-05:00, sealed 2026-11-06T00:27:48Z, cutoff 2026-11-06T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-116431`, scan `SCAN-US-2026-11-05-G2_RET30`; signal close 0.8079 on 2026-11-05; entry: the entry session's opening print (2026-11-06). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): MKZR 0.98, VIDA 0.755, MGX 0.7308, GLXG 0.7, DXF 0.2273.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

