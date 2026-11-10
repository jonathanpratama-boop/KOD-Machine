# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-10T10:37:16Z). Nothing here is a result until a look is reached.

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

Sets 63 over 4 signal sessions; events seen: SEALED 63, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 3715, SKIP_LATE 41, SKIP_NO_TICKER 2, SKIP_NOT_OPERATING 2, SKIP_REPEAT_90D 6; coverage gaps 0.
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

### FORM4 ADM (Archer-Daniels-Midland Co) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001225208-26-008783`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 69.84 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001225208-26-008783` (1 filing(s)) by McAtee David R II (director).
Coverage **FIRE**; purchases USD 196,756, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): ENTG 140.06, PRIM 71.24, DINO 99.76, ARW 191.84, PWR 591.48.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 AN (AUTONATION, INC.) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001293167-26-000008`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 186.06 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001293167-26-000008` (2 filing(s)) by Szlosek Thomas A (EVP & CFO), TRAVISANO JACQUELINE A (director).
Coverage **FIRE**; purchases USD 298,004, owners 2, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): BX 124.05, FDXF 129.05, SWKS 82.83, WY 21.13, OC 127.02.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ECHO (EchoStar CORP) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001393025-26-000007`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 101.19 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001393025-26-000007` (1 filing(s)) by Wall William P (director).
Coverage **FIRE**; purchases USD 90,410, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): WELL 247.35, PSA 338.15, AEE 114.02, PLNT 61.11, ITT 218.21.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FGBI (First Guaranty Bancshares, Inc.) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001437749-26-035913`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 12.32 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001437749-26-035913` (1 filing(s)) by Smith Edgar R. III (director).
Coverage **FIRE**; purchases USD 59,000, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): HCM 15.32, WFCF 15.68, PERI 11.4, DIBS 5.79, CPSS 10.45.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NXRT (NexPoint Residential Trust, Inc.) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001437749-26-035984`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 15.75 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001437749-26-035984` (2 filing(s)) by Richards Paul (See Remarks), McGraner Matt (See Remarks).
Coverage **FIRE**; purchases USD 302,319, owners 2, top executive no, lag 0 days.
Twins (band+liq+mom+dd): SWMR 8.97, MNTN 5.19, ILPT 5.88, HNRG 10.59, JANX 12.76.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NSLR (Neostellar Capital Corp.) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001493152-26-050692`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 6.15 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001493152-26-050692` (1 filing(s)) by Potter Leonard (director).
Coverage **FIRE**; purchases USD 115,200, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): RPGL 9.19, AP 6, OPI 13.73, NOA 9.57, MAAS 10.15.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ROK (ROCKWELL AUTOMATION, INC) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001515154-26-000003`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 389.36 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001515154-26-000003` (1 filing(s)) by Moret Blake D. (President and CEO).
Coverage **FIRE**; purchases USD 1,545,450, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): INSW 96.45, SEI 62.61, ZBRA 326.71, DINO 99.76, STM 44.54.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CMCO (COLUMBUS MCKINNON CORP) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001628280-26-072106`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 19.67 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-072106` (1 filing(s)) by Wilson David J. (President & CEO).
Coverage **FIRE**; purchases USD 551,349, owners 1, top executive yes, lag 4 days.
Twins (band+liq+mom+dd): JBGS 12.38, IIIV 19.31, OABI 5.3, AURA 7.66, CHPT 12.39.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 AFCG (Advanced Flower Capital Inc.) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001628280-26-072331`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 3.435 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-072331` (1 filing(s)) by TANNENBAUM LEONARD M (director).
Coverage **FIRE**; purchases USD 56,980, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): YDKG 1.04, GROV 1.1, EFOI 4.395, TOMZ 2.42, ISPR 1.67.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 LUCK (Lucky Strike Entertainment Corp) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001628280-26-072428`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 3.76 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-072428` (1 filing(s)) by Young John Alan (director).
Coverage **FIRE**; purchases USD 56,990, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): SPAI 3.28, UP 2.76, SKIL 3.35, ACET 2.99, SOTK 4.3.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SOPH (SOPHiA GENETICS SA) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001840706-26-000351`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 7.49 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001840706-26-000351` (2 filing(s)) by Muken Ross (Chief Executive Officer), CARDOZA GEORGE (Chief Financial Officer).
Coverage **FIRE**; purchases USD 278,388, owners 2, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): DRTS 14.11, GAIN 15.09, FVRR 8.48, ACIC 10.01, AVO 11.91.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 GOOD (GLADSTONE COMMERCIAL CORP) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001873961-26-000002`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 10.225 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001873961-26-000002` (1 filing(s)) by Cooper Arthur S. (CEO & President).
Coverage **FIRE**; purchases USD 99,999, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): XGN 7.1, MNRO 11.14, SSYS 6.68, NAVI 7.84, AMSF 19.63.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 AUDC (AUDIOCODES LTD) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001976408-26-000933`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 8.5 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001976408-26-000933` (1 filing(s)) by ADLERSBERG SHABTAI (President and CEO).
Coverage **FIRE**; purchases USD 126,140, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): WATT 8.69, SUPX 5.7, SDOT 6.475, KGEI 5.24, FXHO 5.48.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NLY (ANNALY CAPITAL MANAGEMENT INC) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0001994436-26-000004`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 18.95 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0001994436-26-000004` (1 filing(s)) by Wede Scott (director).
Coverage **FIRE**; purchases USD 940,000, owners 1, top executive no, lag 3 days.
Twins (band+liq+mom+dd): RIVN 14.01, F 12.52, CDE 16.45, LYFT 16.76, AVTR 15.91.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 DKNG (DraftKings Inc.) - filed 2026-11-09, sealed 2026-11-10T10:36:52Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4-0002019299-26-000018`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 18.7 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20.
Form 4 `0002019299-26-000018` (1 filing(s)) by Ellingson Alan Wayne (Chief Financial Officer).
Coverage **FIRE**; purchases USD 349,987, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): PATH 12.98, RGTI 12.98, HL 15.41, WULF 12.38, PCG 13.14.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

