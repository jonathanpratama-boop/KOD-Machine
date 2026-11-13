# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-13T10:43:04Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 25 (FIRE 8, ABSTAIN 17) over 8 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 13, SEALED 25, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 5, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 43 over 8 signal sessions; events seen: SEALED 43, SKIP_REPEAT_90D 36, SKIP_NO_TICKER 24, SKIP_NOT_IN_UNIVERSE 24, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 80 over 5 signal sessions; events seen: SEALED 80, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 4236, SKIP_LATE 41, SKIP_NO_TICKER 3, SKIP_NOT_OPERATING 3, SKIP_REPEAT_90D 12; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 80 over 5 signal sessions; events seen: SEALED 80; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 31, FIRE 49
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 23 over 7 signal sessions; events seen: SEALED 23; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 13, FIRE 10
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

186 tags: 44 true, 0 unknown.

## Latest sets

### SEC13D INTZ (INTRUSION INC) - accepted 2026-11-12T12:39:58-05:00, sealed 2026-11-12T23:03:04Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-SEC13D-0001815632-26-000005`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 0.5434 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Filing `0001815632-26-000005` by Tego Cyber, Inc.; Item 4 intent words: board, nominate, director.
Coverage **ABSTAIN** (DILUTION_RECENT, MICROCAP); pre-entry move -7.90%, market value USD 13.3M, dilution filings 2.
Twins (band+liq+mom+dd): SLGB 0.1811, APRE 0.44, SACH 0.7001, GTEC 0.4945, NCNA 0.93.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D AGLT (Agility Robotics, Inc.) - accepted 2026-11-12T16:30:11-05:00, sealed 2026-11-12T23:03:04Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-SEC13D-0001213900-26-118976`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 7.58 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Filing `0001213900-26-118976` by Hurst Jonathan; Item 4 intent words: board, merger, acquisition.
Coverage **ABSTAIN** (DILUTION_RECENT, MV_UNKNOWN); pre-entry move +0.00%, market value n/a, dilution filings 3.
Twins (band+liq+mom+dd): APPS 7.3, OCUL 6.28, ARIS 14.81, UUUU 6.68, RCUS 17.77.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D MTRI (InMed Pharmaceuticals Inc.) - accepted 2026-11-12T17:00:03-05:00, sealed 2026-11-12T23:03:04Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-SEC13D-0001193125-26-458677`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 18.35 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Filing `0001193125-26-458677` by Fairmount Funds Management LLC; Item 4 intent words: board, merger, director.
Coverage **ABSTAIN** (DILUTION_RECENT); pre-entry move +0.00%, market value USD 100.8M, dilution filings 2.
Twins (band+liq+mom+dd): RMBI 15.97, RVSB 6.47, CLAR 5.17, FRBT 19.34, CARL 17.3.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 INTZ (INTRUSION INC) - accepted 2026-11-12T12:39:58-05:00, sealed 2026-11-12T23:03:31Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-SEC13D_V2-0001815632-26-000005`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 0.5434 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001815632-26-000005` by Tego Cyber, Inc.; cover page max 8.9% of class; strong intent: nominate; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT, MICROCAP); market value USD 13.3M from XBRL; parent CAT-SEC13D-0001815632-26-000005.
Twins (band+liq+mom+dd): SLGB 0.1811, APRE 0.44, SACH 0.7001, GTEC 0.4945, NCNA 0.93, AEON 0.1587, BRFH 0.5017, KALA 0.161, CPHI 0.5599, PBK 0.1415, CIRC 0.1961, LOOP 0.2105, TMDE 0.43, FUFU 0.9089, IMNN 0.6368, NTCL 0.2095, FCHL 0.722, USBC 0.3661, CABR 0.8043, TEAD 0.1708.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 AGLT (Agility Robotics, Inc.) - accepted 2026-11-12T16:30:11-05:00, sealed 2026-11-12T23:03:31Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-SEC13D_V2-0001213900-26-118976`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 7.58 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001213900-26-118976` by Hurst Jonathan; cover page max 5.2% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT); market value USD 1,844.4M from COVER_PAGE; parent CAT-SEC13D-0001213900-26-118976.
Twins (band+liq+mom+dd): APPS 7.3, OCUL 6.28, ARIS 14.81, UUUU 6.68, RCUS 17.77, BRUN 5.92, NVAX 8.76, SECZ 8.39, FCEL 10.25, MUX 11.95, WYFI 10.335, UGP 5.63, FSM 9.11, UEC 6.8, STWD 11.44, SBET 5.77, UMAC 11.83, AESI 5.5, NVCR 11.72, POET 5.21.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 MTRI (InMed Pharmaceuticals Inc.) - accepted 2026-11-12T17:00:03-05:00, sealed 2026-11-12T23:03:31Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-SEC13D_V2-0001193125-26-458677`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 18.35 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001193125-26-458677` by Fairmount Funds Management LLC; cover page max 19.99% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT); market value USD 100.8M from XBRL; parent CAT-SEC13D-0001193125-26-458677.
Twins (band+liq+mom+dd): RMBI 15.97, RVSB 6.47, CLAR 5.17, FRBT 19.34, CARL 17.3, LAW 6.51, BBCP 10.27, HQI 18.53, AFRI 13.13, KMDA 8.13, JRSH 7.35, WHF 8.31, GRDX 5.42, RMNI 5.59, SKIN 15.96, DIBS 5.83, JXG 13.09, HYNE 18.84, INFU 14.79, RSVR 10.22.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K FOXX - event `0001213900-26-118345`, accepted 2026-11-12T07:00:18-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-118345`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 1.31 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -4.38%.
Twins (band+liq+mom+dd): RYOJ 2.575, CHR 1.319, ITOC 1.9, CDLX 1.43, ARTL 2.1.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K VOR - event `0001193125-26-456955`, accepted 2026-11-12T07:31:20-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-456955`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 19.32 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -3.83%.
Twins (band+liq+mom+dd): MAMA 13.24, PFLT 6.73, PAYP 14.18, XZO 16.14, NX 19.34.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K IBP - event `0001628280-26-073103`, accepted 2026-11-12T07:31:50-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001628280-26-073103`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 223.76 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +6.79%.
Twins (band+liq+mom+dd): BRKR 60.33, AN 180.51, CDNA 79.81, AMRZ 40.83, CG 39.36.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K NXGL - event `0001493152-26-051238`, accepted 2026-11-12T09:00:40-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-051238`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 3.79 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -10.61%.
Twins (band+liq+mom+dd): KPRX 1.33, SLNG 3.77, YJ 1.24, SUNE 1.95, YHC 1.65.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K LCTX - event `0001193125-26-458377`, accepted 2026-11-12T16:10:16-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-458377`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 0.9903 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom): WWR 0.3867, IBIO 0.7622, ESLA 0.5189, GLDG 0.7331, NMRA 0.433.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K LFMD - event `0001493152-26-051397`, accepted 2026-11-12T16:10:33-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-051397`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 1.655 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): ASTI 1.415, TSQ 1.46, GEOS 3.48, COYA 3.27, MNTK 1.03.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K OPHC - event `0001493152-26-051481`, accepted 2026-11-12T17:19:46-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-051481`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 8.96 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): SNFCA 8.97, YALA 5.47, FJDI 9.88, PSBD 9.83, SHOT 9.8998.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K DBX - event `0001104659-26-126351`, accepted 2026-11-12T17:22:27-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001104659-26-126351`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 33.51 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): SGI 60.62, GIS 33.52, NRG 98.05, TVTX 51.56, MTCH 41.78.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K APVO - event `0001193125-26-458751`, accepted 2026-11-12T17:25:33-05:00, sealed 2026-11-12T23:04:06Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-458751`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 0.6601 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): DXF 0.2666, TOVX 0.16, DOMH 0.7942, XPL 0.443.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

