# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-10-30T11:01:40Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 4 (FIRE 1, ABSTAIN 3) over 2 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 3, SEALED 4, SKIP_NOT_OPERATING 1; coverage gaps 0.

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

Sets 5 over 2 signal sessions; events seen: SEALED 5, SKIP_REPEAT_90D 3, SKIP_NO_TICKER 4, SKIP_NOT_IN_UNIVERSE 3; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 9 over 1 signal sessions; events seen: SEALED 9, SKIP_NOT_IN_UNIVERSE 1, SKIP_NOT_PURCHASE 252; coverage gaps 0.
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

Sets 2 over 1 signal sessions; events seen: SEALED 2; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 2
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

30 tags: 6 true, 0 unknown.

## Latest sets

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

### SEC13D ZVIA (Zevia PBC) - accepted 2026-10-29T19:53:14-04:00, sealed 2026-10-30T10:59:33Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-SEC13D-0002162656-26-000001`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 1.23 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Filing `0002162656-26-000001` by Bubble Holdings, LLC; Item 4 intent words: board, acquisition, proxy, director.
Coverage **ABSTAIN** (DILUTION_RECENT, MV_UNKNOWN); pre-entry move +0.00%, market value n/a, dilution filings 1.
Twins (band+liq+mom+dd): AMPY 4.33, SPWH 1.07, GALT 3.52, LSAK 4.06, SND 4.89.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 ZVIA (Zevia PBC) - accepted 2026-10-29T19:53:14-04:00, sealed 2026-10-30T10:59:45Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-SEC13D_V2-0002162656-26-000001`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 1.23 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0002162656-26-000001` by Bubble Holdings, LLC; cover page max 16.1% of class; strong intent: proxy; Item 5(c): 2 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT); market value USD 105.5M from COVER_PAGE; parent CAT-SEC13D-0002162656-26-000001.
Twins (band+liq+mom+dd): AMPY 4.33, SPWH 1.07, GALT 3.52, LSAK 4.06, SND 4.89, TUYA 1.66, CLNE 1.49, ARQ 1.77, CURV 2.22, SIGA 3.18, ONL 2.32, MAIA 1.18, CHMI 2.64, XYF 4.89, SNDL 1.3, NAGE 2.5, TLYS 4.34, AUNA 4.8, MSGM 4.66, GRWG 1.5.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K RGEN - event `0001628280-26-068382`, accepted 2026-10-30T06:04:21-04:00, sealed 2026-10-30T10:59:53Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-DILUTION_8K-0001628280-26-068382`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 188.64 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): URBN 92.19, DHR 236.98, RBA 88.3, IFF 90.81, GTLB 56.65.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BFC (Bank First Corp) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001104659-26-120006`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 150.62 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001104659-26-120006` (1 filing(s)) by Sprang Todd A. (director).
Coverage **FIRE**; purchases USD 59,348, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): BKTI 72.3, FISI 40.88, AMTB 29.9, EQBK 49.11, SMBK 49.07.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 DINO (HF Sinclair Corp) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001193125-26-438100`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 111.89 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-438100` (1 filing(s)) by MYERS FRANKLIN (CEO).
Coverage **FIRE**; purchases USD 1,108,000, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): SPCX 143.89, CBRE 128.58, SNA 358.6, DAVE 334.8, FNV 231.6.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 LRN (Stride, Inc.) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001213900-26-113987`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 80.7 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-113987` (1 filing(s)) by Haggart Dylan G. (director), Fivespan Partners, LP (officer), Fivespan Partners GP, LLC (officer).
Coverage **FIRE**; purchases USD 62,188, owners 3, top executive no, lag 2 days.
Twins (band+liq+mom+dd): TRMD 43.045, OPLN 38.76, CNM 44.14, FSV 144.5, MORN 222.54.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PNFP (Pinnacle Financial Partners, Inc.) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001219004-26-000004`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 101.71 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001219004-26-000004` (1 filing(s)) by INGRAM DAVID B (director).
Coverage **FIRE**; purchases USD 991,600, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): PAG 212.34, EVRG 85.41, BDX 198.34, EXPD 198.39, PFE 29.95.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 HBAN (HUNTINGTON BANCSHARES INC /MD/) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001225208-26-008552`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 15.97 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001225208-26-008552` (1 filing(s)) by TORGOW GARY (director).
Coverage **FIRE**; purchases USD 199,834, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): OWL 10.41, CPNG 14.57, CAG 14.09, ACI 12.79, JBS 12.16.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 XYL (Xylem Inc.) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001524472-26-000150`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 90.76 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001524472-26-000150` (1 filing(s)) by KOCH D CHRISTIAN (director).
Coverage **FIRE**; purchases USD 985,600, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): MTZ 177.82, AMKR 41.21, CORT 85.95, AAOI 79.19, INTC 92.07.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TFC (TRUIST FINANCIAL CORP) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001534574-26-000018`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 49.32 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001534574-26-000018` (1 filing(s)) by Lyons Michael P. (President & CEO).
Coverage **FIRE**; purchases USD 1,209,050, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): AOS 63.49, CTAS 218.07, ABBV 290.79, RPRX 65.93, LH 368.16.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BBT (Beacon Financial Corp) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001628280-26-068056`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 30.66 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-068056` (1 filing(s)) by Callahan Mary Anne (director).
Coverage **FIRE**; purchases USD 96,672, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): EPAC 39.42, ENR 23.15, WKC 37.21, MGY 26.22, DIN 35.16.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 UTMD (UTAH MEDICAL PRODUCTS INC) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001733614-26-000005`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 66.8 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001733614-26-000005` (1 filing(s)) by CORNWELL KEVIN L (Chairman, CEO).
Coverage **FIRE**; purchases USD 66,750, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): PKX 50.91, GLIBK 21.61, CMCL 21.4, XRN 30.52, ATNI 25.88.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

