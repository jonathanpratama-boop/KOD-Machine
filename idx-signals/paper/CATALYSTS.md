# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-23T10:33:03Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 39 (FIRE 17, ABSTAIN 22) over 14 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 18, SEALED 39, SKIP_NOT_OPERATING 8, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 2; coverage gaps 1.

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

Sets 73 over 14 signal sessions; events seen: SEALED 73, SKIP_REPEAT_90D 59, SKIP_NO_TICKER 44, SKIP_NOT_IN_UNIVERSE 45, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 257 over 12 signal sessions; events seen: SEALED 257, SKIP_NOT_IN_UNIVERSE 8, SKIP_NOT_PURCHASE 8976, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 9, SKIP_REPEAT_90D 93; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 237 over 11 signal sessions; events seen: SEALED 237; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 102, FIRE 135
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 37 over 13 signal sessions; events seen: SEALED 37; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 18, FIRE 19
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

292 tags: 68 true, 0 unknown.

## Latest sets

### FORM4 SAGT (SAGTEC GLOBAL Ltd) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001213900-26-122442`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 1.11 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-122442` (1 filing(s)) by Ng Chen Lok (Chief Executive Officer).
Coverage **FIRE**; purchases USD 267,800, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): CLAR 4.75, TUSK 2.94, POWW 2.58, MYPS 4.94, SJT 4.37.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PICS (PicS N.V.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001213900-26-122444`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 5.02 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-122444` (2 filing(s)) by Teixeira Linares Marcio Antonio (director), Pruett William Rodney (director).
Coverage **FIRE**; purchases USD 531,900, owners 2, top executive no, lag 2 days.
Twins (band+liq+mom+dd): ADIG 8.96, HNRG 8.94, GLUE 8.64, CMCL 16.26, MTA 5.84.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 MED (MEDIFAST INC) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001213900-26-122629`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 11.75 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-122629` (1 filing(s)) by Kiai Parsa (director).
Coverage **FIRE**; purchases USD 1,133,816, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): KROS 11.08, XTER 9.8, CARL 17.42, GLRE 16.3, RDAG 10.505.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ALTO (Alto Ingredients, Inc.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001213900-26-122704`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 2.98 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-122704` (1 filing(s)) by NATHAN GILBERT E (director).
Coverage **FIRE**; purchases USD 81,362, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): AMBP 4.32, TSHA 3.72, VGZ 2.27, MOMO 4.075, GDRX 2.92.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 GBCI (GLACIER BANCORP, INC.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001347688-26-000006`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 45.49 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001347688-26-000006` (1 filing(s)) by Langel Craig A (director).
Coverage **FIRE**; purchases USD 53,452, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): DSGX 89.205, SFNC 21.56, WSBC 36.37, KWR 147.48, TS 55.17.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 HBCP (HOME BANCORP, INC.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001436425-26-000078`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 60.54 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001436425-26-000078` (1 filing(s)) by Hill Darren M (Chief Risk Officer).
Coverage **FIRE**; purchases USD 315,013, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): TNC 73.99, OSBC 24.17, GIII 30.55, CAE 26.71, APOG 43.43.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BOTJ (BANK OF THE JAMES FINANCIAL GROUP INC) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001437749-26-037847`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 24.67 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001437749-26-037847` (1 filing(s)) by FOSTER WATT R JR (director).
Coverage **FIRE**; purchases USD 50,300, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): SBR 60.83, DCBO 27.82, KEN 54.16, DJP 45.97, TWIN 21.21.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CLIK (Click Holdings Ltd.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001493152-26-053366`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 0.6702 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001493152-26-053366` (1 filing(s)) by Chan Chun Sing (Chief Executive Officer).
Coverage **FIRE**; purchases USD 63,856, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): HCWB 0.7491, BRLS 0.7, LIQT 0.1929, DTSS 0.361, CNEY 0.365.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SEI (Solaris Energy Infrastructure, Inc.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001628280-26-075232`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 54.67 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-075232` (3 filing(s)) by Zartler William A (Chairman and Co-CEO), Brock Amanda M (Co-Chief Executive Officer), Ramachandran Kyle S. (President).
Coverage **FIRE**; purchases USD 641,090, owners 3, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): XYL 94.66, OXY 53.9, ESI 29.52, PCVX 55.39, HSBC 80.02.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TMS (Teamshares Inc) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001628280-26-075322`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 3.91 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-075322` (1 filing(s)) by Eu Alexander Zai De (President).
Coverage **FIRE**; purchases USD 109,530, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): MWYN 1.19, SBMT 4.55, SMX 2.7, TENX 1.25, SEAT 1.56.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TJX (TJX COMPANIES INC /DE/) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001664921-26-000002`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 139.62 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001664921-26-000002` (1 filing(s)) by PINTOFF CRAIG ADAM (director).
Coverage **FIRE**; purchases USD 199,823, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): MAA 112.91, MNST 43.69, OKE 84.37, TD 112.87, RY 183.45.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 VANI (Vivani Medical, Inc.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001753926-26-002210`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 1.14 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001753926-26-002210` (1 filing(s)) by Williams Gregg (director).
Coverage **FIRE**; purchases USD 128,325, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): CCLD 2.02, FLX 1.48, ENGN 1.74, GECC 4.88, ONL 2.23.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BHRB (Burke & Herbert Financial Services Corp.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0001945031-26-000015`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 67.81 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0001945031-26-000015` (1 filing(s)) by Poillon Diane (director).
Coverage **FIRE**; purchases USD 106,131, owners 1, top executive no, lag 7 days.
Twins (band+liq+mom+dd): NBBK 21.06, SPFI 40.54, HAFC 30.47, FISI 38.24, IDT 73.72.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TSM (TAIWAN SEMICONDUCTOR MANUFACTURING CO LTD) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0002114032-26-000002`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 318.71 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0002114032-26-000002` (1 filing(s)) by Lu Lee-Chung (VP).
Coverage **FIRE**; purchases USD 302,850, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): MCHP 55.44, TPL 267.44, SU 63.82, GFS 35.56, UNF 228.42.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ESEA (EUROSEAS LTD.) - filed 2026-11-20, sealed 2026-11-23T10:32:32Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4-0002127484-26-000025`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 58.59 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20.
Form 4 `0002127484-26-000025` (1 filing(s)) by Pittas Aristeidis P (director).
Coverage **FIRE**; purchases USD 58,976, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): OFLX 21.15, AIRT 21.43, OLP 20.64, TWIN 21.21, TAYD 53.16.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

