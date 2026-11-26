# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-26T10:33:58Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 47 (FIRE 20, ABSTAIN 27) over 17 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 27, SEALED 47, SKIP_NOT_OPERATING 11, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 4; coverage gaps 1.

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

Sets 82 over 17 signal sessions; events seen: SEALED 82, SKIP_REPEAT_90D 68, SKIP_NO_TICKER 83, SKIP_NOT_IN_UNIVERSE 50, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 312 over 15 signal sessions; events seen: SEALED 312, SKIP_NOT_IN_UNIVERSE 11, SKIP_NOT_PURCHASE 10665, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 13, SKIP_REPEAT_90D 147; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 297 over 14 signal sessions; events seen: SEALED 297; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 133, FIRE 164
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 45 over 16 signal sessions; events seen: SEALED 45; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 23, FIRE 22
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

388 tags: 93 true, 1 unknown.

## Latest sets

### FORM4 NANO (Forge Nano Holdings, Inc.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0000950142-26-003161`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 3.97 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0000950142-26-003161` (1 filing(s)) by Smith Shane (Pres. of Forge Battery, Inc.).
Coverage **FIRE**; purchases USD 250,647, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): VYGR 1.78, SEV 1.5, FISN 2.83, PRQR 1.235, AVIR 3.88.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NOVT (NOVANTA INC) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001076930-26-000090`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 109.53 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001076930-26-000090` (1 filing(s)) by Wilson Frank Anders (director).
Coverage **FIRE**; purchases USD 52,200, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): NBR 73.31, HRI 136.64, DGII 53.3, ALGM 27.13, IDCC 254.475.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TMC (TMC the metals Co Inc.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001104659-26-131894`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 1.94 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001104659-26-131894` (1 filing(s)) by Karkar Andrei (director), ERAS Capital LLC (officer).
Coverage **FIRE**; purchases USD 805,000, owners 2, top executive no, lag 1 days.
Twins (band+liq+mom+dd): GDRX 2.38, BYND 4.45, TMQ 1.4, UROY 2.27, HYLN 1.97.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PATK (PATRICK INDUSTRIES INC) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001189422-26-000034`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 85.49 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001189422-26-000034` (1 filing(s)) by WELCH M SCOTT (director).
Coverage **FIRE**; purchases USD 432,941, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): SBRA 21.16, SIBN 24.79, FTDR 93.87, ITRI 100.81, EPR 60.5.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ADV (Advantage Solutions Inc.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001193125-26-478513`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 27.85 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-478513` (1 filing(s)) by PEACOCK DAVID A (Chief Executive Officer).
Coverage **FIRE**; purchases USD 50,000, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): BSAC 30.83, WS 36.75, ITIC 266.39, FTK 23.88, NGS 28.2.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ROAD (Construction Partners, Inc.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001193125-26-478515`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 72.12 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-478515` (1 filing(s)) by Fleming Ned N III (director).
Coverage **FIRE**; purchases USD 180,331, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): FLNG 24.26, CE 45.44, WDS 20.21, ARQT 29.59, JOE 65.87.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 AVD (AMERICAN VANGUARD CORP) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001193125-26-478691`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 0.7825 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-478691` (1 filing(s)) by Gottschalk Patrick E (director).
Coverage **FIRE**; purchases USD 98,098, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): WHLR 0.4081, MIST 0.36, SDEV 0.4981, CRMN 0.9141, ANVS 0.8548.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CLW (Clearwater Paper Corp) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001414260-26-000006`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 16.76 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001414260-26-000006` (1 filing(s)) by TOELDTE ALEXANDER (director).
Coverage **FIRE**; purchases USD 125,688, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): PANL 8.34, FOSL 8.27, MNSO 10.46, TTI 6.07, TRTX 6.67.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 EMPD (Empery Digital Inc.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001683168-26-009142`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 2.19 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001683168-26-009142` (1 filing(s)) by READ IAN C (director).
Coverage **FIRE**; purchases USD 535,110, owners 1, top executive no, lag 6 days.
Twins (band+liq+mom+dd): IMPP 3.93, GRDX 3.09, SRI 4.29, MIND 2.33, SRTS 2.08.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 GRWG (GrowGeneration Corp.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001725239-26-000006`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 1.02 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001725239-26-000006` (1 filing(s)) by Lampert Darren (CEO).
Coverage **FIRE**; purchases USD 99,013, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): NKTX 1.12, NRXS 4.82, CNXU 1.55, TONX 2.26, RENT 1.89.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 EXE (EXPAND ENERGY Corp) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001730935-26-000015`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 86.77 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001730935-26-000015` (1 filing(s)) by Teunissen Marcel (EVP & CFO).
Coverage **FIRE**; purchases USD 81,560, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): CHWY 20.47, RVMD 175.67, BAC 48.54, AVGO 300.86, HUBS 210.21.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BFS (SAUL CENTERS, INC.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001804456-26-000004`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 28.45 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001804456-26-000004` (1 filing(s)) by Pearson David Todd (President & COO).
Coverage **FIRE**; purchases USD 99,719, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): BGSI 75.87, NBTX 29.15, USLM 104.68, MSBI 29.13, MLR 47.69.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NRGV (Energy Vault Holdings, Inc.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0001898769-26-000011`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 3.06 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0001898769-26-000011` (1 filing(s)) by Piconi Robert (Chief Executive Officer).
Coverage **FIRE**; purchases USD 60,750, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): DCH 4.2, INTR 4.01, VZLA 2.86, NUVB 4.31.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 KDK (Kodiak AI, Inc.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0002080471-26-000003`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 1.23 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0002080471-26-000003` (1 filing(s)) by Burnette Donald L. (Chief Executive Officer).
Coverage **FIRE**; purchases USD 2,213,400, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): ARTV 3.95, LENZ 2.99, CTMX 2.24, TOYO 3.41, AIV 1.46.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SHMD (SCHMID Group N.V.) - filed 2026-11-25, sealed 2026-11-26T10:33:41Z, cutoff 2026-11-27T14:15:00Z
Set `CAT-FORM4-0002125667-26-000005`, scan `SCAN-US-2026-11-25-G2_RET30`; signal close 1.89 on 2026-11-25; entry: the entry session's opening print (2026-11-27). Windows: H20: entry +1, hold 20.
Form 4 `0002125667-26-000005` (1 filing(s)) by Schuetz Arthur Josef Hermann (CFO Schmid Group N.V.).
Coverage **FIRE**; purchases USD 103,885,740,000, owners 1, top executive yes, lag 7305 days.
Twins (band+liq+mom+dd): GYRE 4.14, PSNY 2.4, IMDX 2.265, CNXU 1.55, TTGT 2.08.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

