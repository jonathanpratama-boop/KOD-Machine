# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-13T10:51:58Z). Nothing here is a result until a look is reached.

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

Sets 112 over 6 signal sessions; events seen: SEALED 112, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 5022, SKIP_LATE 41, SKIP_NO_TICKER 4, SKIP_NOT_OPERATING 3, SKIP_REPEAT_90D 19; coverage gaps 0.
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

### FORM4 AQST (Aquestive Therapeutics, Inc.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001214659-26-014004`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 3.57 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001214659-26-014004` (1 filing(s)) by Daly Richard J (director).
Coverage **FIRE**; purchases USD 99,331, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): FATE 1.34, SION 3.43, PSFE 3.87, DFDV 2.95, QTEX 1.19.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 HOS (HORNBECK OFFSHORE SERVICES, INC.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001284591-26-000002`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 5.83 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001284591-26-000002` (1 filing(s)) by HORNBECK TODD M (PRESIDENT & CEO).
Coverage **FIRE**; purchases USD 1,500,009, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): IE 6.95, KURA 7.43, EROC 8.34, NAVI 6.14, ALM 7.63.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FLG (FLAGSTAR BANK, NATIONAL ASSOCIATION) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001323101-26-000007`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 10.34 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001323101-26-000007` (1 filing(s)) by Otting Joseph M (Exec Chairman and CEO).
Coverage **FIRE**; purchases USD 496,429, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): LI 11.69, FLO 6.01, BILI 13.5, BXDC 16.55, NIQ 19.22.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BKD (Brookdale Senior Living Inc.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001332349-26-000074`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 8.96 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001332349-26-000074` (1 filing(s)) by WINKLE C CHRISTIAN (director).
Coverage **FIRE**; purchases USD 358,068, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): DX 9.96, WTTR 16.33, NEOG 11.19, NWG 15.73, RVLV 18.75.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 EGBN (EAGLE BANCORP INC) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001441890-26-000007`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 34.38 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001441890-26-000007` (1 filing(s)) by Curley Stephen Russell (President/CEO).
Coverage **FIRE**; purchases USD 149,582, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): EFSC 62.38, PBAM 86.95, CLMB 43.09, CIVB 28.72, THFF 76.99.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BOOT (Boot Barn Holdings, Inc.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001562356-26-000004`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 133.67 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001562356-26-000004` (1 filing(s)) by Watkins James M (CFO & SECRETARY).
Coverage **FIRE**; purchases USD 270,740, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): OSK 140.4, FNF 43.1, FTAI 182.87, TENB 41.05, MGM 33.24.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ECL (ECOLAB INC.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001628280-26-073457`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 304.41 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-073457` (1 filing(s)) by MacLennan David (director).
Coverage **FIRE**; purchases USD 184,875, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): EXEL 69.84, TCOM 43.21, AVGO 364.36, TTWO 226.95, VTR 89.65.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 URG (UR-ENERGY INC) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001654954-26-009739`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 0.6185 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001654954-26-009739` (1 filing(s)) by Walle Jade (VICE PRESIDENT FINANCE).
Coverage **FIRE**; purchases USD 109,999, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): SHFS 0.0225, CENN 0.182, EYPT 0.3195, OPTU 0.6374, AKBA 0.498.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TH (Target Hospitality Corp.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001712189-26-000063`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 11.98 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001712189-26-000063` (1 filing(s)) by Archer James Bradley (Director and CEO and President).
Coverage **FIRE**; purchases USD 312,675, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): IE 6.95, BTU 17.41, WYFI 10.335, ADEA 16.63, STWD 11.44.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 BLMN (Bloomin' Brands, Inc.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001719998-26-000016`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 10.12 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001719998-26-000016` (1 filing(s)) by Spanos Mike (CEO).
Coverage **FIRE**; purchases USD 502,000, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): NHP 15.17, FOXF 17.32, ASAN 9.67, SGHC 11.42, DNLI 18.89.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 LILA (Liberty Latin America Ltd.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001724519-26-000014`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 9.73 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001724519-26-000014` (1 filing(s)) by DE ANGOITIA ALFONSO (director).
Coverage **FIRE**; purchases USD 5,061,969, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): ASTL 5.61, ACEL 13.83, TLS 7.72, LFTO 18.71, JBGS 11.99.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ITIC (INVESTORS TITLE CO) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001804353-26-000010`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 251.59 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001804353-26-000010` (1 filing(s)) by Parker, Jr. Elton C. (director).
Coverage **FIRE**; purchases USD 133,000, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): NSSC 30.34, ODC 73.15, CSV 27.9, ROOT 43.63, BGSI 74.46.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ZVIA (Zevia PBC) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001847944-26-000007`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 1.06 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001847944-26-000007` (1 filing(s)) by Ruberti Alexandre (President & CEO).
Coverage **FIRE**; purchases USD 99,910, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): GNLX 1.9, PROK 1.15, BMM 3.15, ICU 1.05, ZONE 3.5.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FIP (FTAI Infrastructure Inc.) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0001899883-26-000044`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 4.23 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0001899883-26-000044` (1 filing(s)) by Nicholson Kenneth J. (CEO and President).
Coverage **FIRE**; purchases USD 1,530,000, owners 1, top executive yes, lag 2 days.
Twins (band+liq+mom+dd): MNKD 4.16, BDN 3.06, EGHT 2.33, EVGO 1.75, UIS 2.87.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 NOMD (Nomad Foods Ltd) - filed 2026-11-12, sealed 2026-11-13T10:51:16Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4-0002111999-26-000011`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 11.65 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20.
Form 4 `0002111999-26-000011` (1 filing(s)) by BALDEW RUBEN (Chief Financial Officer).
Coverage **FIRE**; purchases USD 100,161, owners 1, top executive yes, lag 3 days.
Twins (band+liq+mom+dd): IHS 8.41, LXFR 17.34, PAYO 7.18, DGICA 18.96, MATV 12.01.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

