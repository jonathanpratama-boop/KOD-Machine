# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-24T10:34:05Z). Nothing here is a result until a look is reached.

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

Sets 277 over 13 signal sessions; events seen: SEALED 277, SKIP_NOT_IN_UNIVERSE 11, SKIP_NOT_PURCHASE 9562, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 11, SKIP_REPEAT_90D 114; coverage gaps 1.
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

### FORM4 URI (UNITED RENTALS, INC.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001193125-26-472335`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 1040.7 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-472335` (1 filing(s)) by Taussig Alexander R. (director).
Coverage **FIRE**; purchases USD 150,086, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): AEIS 214.07, HSBC 83.01, CSGP 30.2, JPM 316.66, HRB 45.98.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CCAP (Crescent Capital BDC, Inc.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001193125-26-472359`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 9.92 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-472359` (1 filing(s)) by Chung Henry (President).
Coverage **FIRE**; purchases USD 88,380, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): SGU 13.16, APXT 10.21, AESP 10.08, BDCI 10.19, BBCP 9.44.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FRMI (Fermi Inc.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001213900-26-123347`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 2.1 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001213900-26-123347` (1 filing(s)) by Wentz George R. Jr. (General Counsel).
Coverage **FIRE**; purchases USD 6,448,510, owners 1, top executive no, lag 26 days.
Twins (band+liq+mom+dd): DJT 3.885, RUM 4.16, LWLG 2.915, SBET 4.81, CYPH 1.61.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 WMB (WILLIAMS COMPANIES, INC.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001405444-26-000008`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 65.43 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001405444-26-000008` (1 filing(s)) by Turner Robb E (director).
Coverage **FIRE**; purchases USD 646,500, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): SPXC 145.37, IOT 38.77, SHEL 92.91, GL 154.99, COP 132.19.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 MPLT (MapLight Therapeutics, Inc.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001470798-26-000007`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 5.83 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001470798-26-000007` (1 filing(s)) by Pavlov George (director).
Coverage **FIRE**; purchases USD 120,000, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): ORIC 7.54, MNRO 8.38, XRPN 6.98, ANL 9, ARCT 8.32.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BTU (PEABODY ENERGY CORP) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001570382-26-000015`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 15.97 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001570382-26-000015` (1 filing(s)) by Grech James C. (President and CEO).
Coverage **FIRE**; purchases USD 70,532, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): BBNX 13.87, PGY 14.61, VIR 9.03, VSTM 6.64, IE 5.68.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BWFG (Bankwell Financial Group, Inc.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001628280-26-075380`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 68.45 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-075380` (1 filing(s)) by SEIDMAN LAWRENCE B (director).
Coverage **FIRE**; purchases USD 167,972, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): DLX 25.2, KIDS 32.64, RUSHB 58.63, EGBN 33.18, SMP 44.62.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BORR (Borr Drilling Ltd) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001628280-26-075382`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 3.81 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-075382` (1 filing(s)) by Troim Tor Olav (director).
Coverage **FIRE**; purchases USD 30,451,500, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): AMC 2.86, SBS 4.63, ABEV 2.64, UAA 4.51, ORC 4.59.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BG (Bunge Global SA) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001628280-26-075421`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 91.97 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-075421` (1 filing(s)) by Mahoney Christopher (director).
Coverage **FIRE**; purchases USD 1,161,650, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): UBS 44.88, BX 115.86, GPC 120.27, HAL 30.57, MTCH 40.33.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SUNS (Sunrise Realty Trust, Inc.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001628280-26-075460`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 6.6 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-075460` (1 filing(s)) by TANNENBAUM LEONARD M (Executive Chairman).
Coverage **FIRE**; purchases USD 344,500, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): DIBS 5.28, PROF 6.55, BNR 13.69, ELA 12.01, DMAC 8.82.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 HYLN (Hyliion Holdings Corp.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001628280-26-075493`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 1.85 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-075493` (1 filing(s)) by Boehm Rodger L (director).
Coverage **FIRE**; purchases USD 80,400, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): PACK 2.8, EH 2.45, XNDU 2.01, PDYN 2.57, TROX 1.64.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ECVT (Ecovyst Inc.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001708035-26-000113`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 9.34 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001708035-26-000113` (2 filing(s)) by Fogarty Kevin Michael (director), Catalano Anna C (director).
Coverage **FIRE**; purchases USD 300,805, owners 2, top executive no, lag 3 days.
Twins (band+liq+mom+dd): SEG 19.7, FNKO 5.95, NMFC 6.5, MAMA 11.26, KEP 9.31.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SCOR (COMSCORE, INC.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0001853874-26-000016`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 3.41 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0001853874-26-000016` (1 filing(s)) by McLaughlin Matthew F. (Chief Executive Officer).
Coverage **FIRE**; purchases USD 258,279, owners 1, top executive yes, lag 4 days.
Twins (band+liq+mom+dd): YMT 1.28, AZR 3.94, NCRA 1.43, TVRD 1.02, BOF 1.73.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BULL (Webull Corp) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0002093135-26-000006`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 4.45 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0002093135-26-000006` (1 filing(s)) by Wang Haichen (Chief Financial Officer).
Coverage **FIRE**; purchases USD 90,000, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): ENVX 1.13, HIVE 1.34, KOS 1.6, POET 3.94, INTR 3.69.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 EDRY (EuroDry Ltd.) - filed 2026-11-23, sealed 2026-11-24T10:33:39Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4-0002127484-26-000026`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 35.27 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20.
Form 4 `0002127484-26-000026` (1 filing(s)) by Pittas Aristeidis P (director).
Coverage **FIRE**; purchases USD 60,520, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): DGP 102, KRT 30.06, DRUG 20.11, VPG 46.36, TBN 21.93.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

