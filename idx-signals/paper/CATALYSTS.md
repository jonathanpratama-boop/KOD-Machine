# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-10-30T10:58:58Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 3 (FIRE 1, ABSTAIN 2) over 2 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 1, SEALED 3; coverage gaps 0.

| Class | Paired | Sessions | Mean net | Mean diff vs twins | t | p (one-sided) |
|---|---|---|---|---|---|---|
| FIRE | 0 | 0 | n/a | n/a | n/a | n/a |
| ABSTAIN | 0 | 0 | n/a | n/a | n/a | n/a |

Primaries (`research/CATALYST_REGISTER_v1/prereg_2.json`), looks at [60, 120, 240, 480, 960, 1920] FIRE pairs, t at least [3.75, 3.0, 3.0, 3.0, 3.0, 3.0]:
- MEAN (plan net minus twins' mean): **accumulating (no look reached)**
- WIN_RATE (plan beats twins' median): 0 of 0 (n/a), t n/a: **accumulating (no look reached)**

## IDX_INDEX (descriptive)

Sets 14 over 1 sessions.

- RUNUP: paired 0, mean signed diff n/a, share with the flow n/a
- POST20: paired 0, mean signed diff n/a, share with the flow n/a

## DILUTION_8K (counted at each look; direction -1; `KOD-CATALYST-FAMILY-DILUTION_8K-v1`)

Sets 4 over 2 signal sessions; events seen: SEALED 4, SKIP_REPEAT_90D 2, SKIP_NO_TICKER 4, SKIP_NOT_IN_UNIVERSE 2; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 0 over 0 signal sessions; events seen: none; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 0 over 0 signal sessions; events seen: none; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: none
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 1 over 1 signal sessions; events seen: SEALED 1; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 1
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
| IDX_INDEX | WITH_FLOW_RUNUP | 0 | | | | | |
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

30 tags: 6 true, 0 unknown.

## Latest sets

### IDX_INDEX PTBA (ADD IDX30) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `CAT-IDX_INDEX-IDX-MAJOR-2026-11-02-PTBA`, scan `SCAN-2026-10-28-F1_ARA`; signal close 3250 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): MEDC 1405, CMNT 725, CMRY 4150, AKRA 1405, GULA 750.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX SCMA (DELETE LQ45) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `CAT-IDX_INDEX-IDX-MAJOR-2026-11-02-SCMA`, scan `SCAN-2026-10-28-F1_ARA`; signal close 139 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): MDIA 78, KOTA 84, LUCY 114, MNCN 84, KIJA 119.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX SMGR (ADD LQ45) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `CAT-IDX_INDEX-IDX-MAJOR-2026-11-02-SMGR`, scan `SCAN-2026-10-28-F1_ARA`; signal close 1440 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom): DEWI 232, PRDA 3720, AUTO 3350, DMAS 210, CTRA 580.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX SMRA (DELETE IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `CAT-IDX_INDEX-IDX-MAJOR-2026-11-02-SMRA`, scan `SCAN-2026-10-28-F1_ARA`; signal close 252 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom): PRDA 3720, ACES 330, DMAS 210, TOWR 392, SMDR 388.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX TINS (ADD IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `CAT-IDX_INDEX-IDX-MAJOR-2026-11-02-TINS`, scan `SCAN-2026-10-28-F1_ARA`; signal close 3820 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom): AMRT 1020, RATU 2230, EMTK 324, BUVA 360, HRTA 1595.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX TKIM (ADD IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `CAT-IDX_INDEX-IDX-MAJOR-2026-11-02-TKIM`, scan `SCAN-2026-10-28-F1_ARA`; signal close 6525 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq): PKPK 7250, AADI 11650, UNTR 25600, ICBP 5775, INKP 6750.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX UNVR (DELETE IDX30) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `CAT-IDX_INDEX-IDX-MAJOR-2026-11-02-UNVR`, scan `SCAN-2026-10-28-F1_ARA`; signal close 1405 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): ANTM 2800, SSMS 940, AMMN 3900, ESSA 525, HRUM 725.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### SEC13D BKU (BankUnited, Inc.) - accepted 2026-10-28T16:24:02-04:00, sealed 2026-10-28T23:03:12Z, cutoff 2026-10-29T13:15:00Z
Set `CAT-SEC13D-0000921895-26-002864`, scan `SCAN-US-2026-10-28-G2_RET30`; signal close 42.81 on 2026-10-28; entry: the entry session's opening print (2026-10-29). Windows: H20: entry +1, hold 20.
Filing `0000921895-26-002864` by HoldCo Asset Management, LP; Item 4 intent words: board, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 3,049.5M, dilution filings 0.
Twins (band+liq+mom+dd): STRA 77.55, NHC 211.79, BCC 74.56, SLG 48.99, PHIN 57.68.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D SWBI (SMITH & WESSON BRANDS, INC.) - accepted 2026-10-28T17:53:47-04:00, sealed 2026-10-28T23:03:12Z, cutoff 2026-10-29T13:15:00Z
Set `CAT-SEC13D-0001493152-26-049116`, scan `SCAN-US-2026-10-28-G2_RET30`; signal close 13.89 on 2026-10-28; entry: the entry session's opening print (2026-10-29). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-049116` by JDH Capital I, L.P.; Item 4 intent words: board, merger, acquisition, director.
Coverage **ABSTAIN** (DILUTION_RECENT); pre-entry move +0.00%, market value USD 622.8M, dilution filings 1.
Twins (band+liq+mom+dd): GLSI 18.31, USNA 14.62, FDUS 19.09, TIPT 17.21, AERO 15.21.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K FRHC - event `0000924805-26-000055`, accepted 2026-10-29T06:22:36-04:00, sealed 2026-10-29T10:36:13Z, cutoff 2026-10-29T13:15:00Z
Set `CAT-DILUTION_8K-0000924805-26-000055`, scan `SCAN-US-2026-10-28-G2_RET30`; signal close 175.55 on 2026-10-28; entry: the entry session's opening print (2026-10-29). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): MUR 42.99, RTO 22.79, ABM 53.3, CUZ 28.51, ASB 30.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D NNOX (Nano-X Imaging Ltd.) - accepted 2026-10-29T14:20:08-04:00, sealed 2026-10-29T23:02:13Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-SEC13D-0001178913-26-004909`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 0.3058 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Filing `0001178913-26-004909` by Moalem Moshe; Item 4 intent words: board, proxy, nominate, director.
Coverage **ABSTAIN** (MICROCAP); pre-entry move -4.74%, market value USD 21.3M, dilution filings 0.
Twins (band+liq+mom+dd): OPTT 0.4189, TGL 0.2349, QUCY 0.91, ONCY 0.4277, CDT 0.077.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K INMB - event `0001213900-26-113535`, accepted 2026-10-29T07:40:32-04:00, sealed 2026-10-29T23:02:41Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-113535`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 1.6 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +4.58%.
Twins (band+liq+mom+dd): JELD 1.36, VIVO 2.6, BIRD 2.12, LPCN 1.52, RDZN 1.12.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K OFAL - event `0001493152-26-049292`, accepted 2026-10-29T16:50:56-04:00, sealed 2026-10-29T23:02:41Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-049292`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 0.3098 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): BIOX 0.2295, AACG 0.65, MNY 0.5513, AMST 0.5679, LZMH 0.7901.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K DFNS - event `0001185185-26-005079`, accepted 2026-10-29T17:27:25-04:00, sealed 2026-10-29T23:02:41Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-DILUTION_8K-0001185185-26-005079`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 3.66 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): CCLD 1.8, XOS 2.65, SPAI 3.39, ALTI 2.56, STEM 2.39.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 NNOX (Nano-X Imaging Ltd.) - accepted 2026-10-29T14:20:08-04:00, sealed 2026-10-29T23:06:18Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-SEC13D_V2-0001178913-26-004909`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 0.3058 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001178913-26-004909` by Moalem Moshe; cover page max 8.49% of class; strong intent: nominate, proxy; Item 5(c): no transactions.
Coverage **ABSTAIN** (MICROCAP); market value USD 21.3M from XBRL; parent CAT-SEC13D-0001178913-26-004909.
Twins (band+liq+mom+dd): OPTT 0.4189, TGL 0.2349, QUCY 0.91, ONCY 0.4277, CDT 0.077, ARAI 0.1214, CGC 0.675, LASE 0.74, HUHU 0.509, ALDX 0.6591, CHRS 0.8984, FNUC 0.739, RCT 0.062, GMEX 0.8783, DDC 0.1389, RANI 0.6054, BLNK 0.4122, STEX 0.4396, VCIG 0.196, EONR 0.3622.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

