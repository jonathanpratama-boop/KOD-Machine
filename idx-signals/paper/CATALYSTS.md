# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-11T10:54:07Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 22 (FIRE 8, ABSTAIN 14) over 7 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 12, SEALED 22, SKIP_NOT_OPERATING 3, SKIP_LATE 2, SKIP_NO_TICKER 4, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 34 over 7 signal sessions; events seen: SEALED 34, SKIP_REPEAT_90D 32, SKIP_NO_TICKER 23, SKIP_NOT_IN_UNIVERSE 22, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 80 over 5 signal sessions; events seen: SEALED 80, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 4236, SKIP_LATE 41, SKIP_NO_TICKER 3, SKIP_NOT_OPERATING 3, SKIP_REPEAT_90D 12; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 63 over 4 signal sessions; events seen: SEALED 63; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 25, FIRE 38
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 20 over 6 signal sessions; events seen: SEALED 20; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 10, FIRE 10
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

141 tags: 30 true, 0 unknown.

## Latest sets

### FORM4 WD (Walker & Dunlop, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001104659-26-125243`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 39.97 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001104659-26-125243` (1 filing(s)) by Pinkus Gary S (director).
Coverage **FIRE**; purchases USD 200,526, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): FBNC 64.81, ABCB 82.94, GCT 61.77, BETA 28.09, MIDD 138.27.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TROX (Tronox Holdings plc) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001140361-26-042891`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 2.85 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001140361-26-042891` (1 filing(s)) by Johnston Peter (director).
Coverage **FIRE**; purchases USD 52,600, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): SERV 3.11, NRXP 2.36, TNXP 4.1, LODE 1.67, GCTS 1.45.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ARLO (Arlo Technologies, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001189819-26-000002`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 12.32 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001189819-26-000002` (1 filing(s)) by Faison Ralph E (director).
Coverage **FIRE**; purchases USD 100,402, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): BXDC 16.68, PZZA 19.98, DEI 10, BKD 9.38, FOXF 17.75.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 MX (MAGNACHIP SEMICONDUCTOR Corp) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001193125-26-454344`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 2.53 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-454344` (2 filing(s)) by LEE CHAE (Chief Executive Officer), Amoruso Cristiano (director).
Coverage **FIRE**; purchases USD 1,526,506, owners 2, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): TSQ 1.56, AARD 1.37, MNTS 1.9, TWG 2.64, EXFY 1.72.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 STVN (Stevanato Group S.p.A.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001193125-26-455579`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 13.53 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-455579` (1 filing(s)) by MOREL DONALD E JR (director).
Coverage **FIRE**; purchases USD 326,750, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): YARW 15.48, OFRM 10.02, LYTS 15.93, CD 5.19, SAFE 10.32.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 DTI (Drilling Tools International Corp) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001193125-26-455713`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.48 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-455713` (1 filing(s)) by Prejean Robert Wayne (Chief Executive Officer).
Coverage **FIRE**; purchases USD 164,300, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): STKE 1.125, NXDT 3.3, QMLS 3.07, AVX 4.06, JELD 1.01.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 WW (WW INTERNATIONAL, INC.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001193125-26-455831`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 12.02 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-455831` (2 filing(s)) by Gavales Lisa A (director), BYE STEPHEN J (President and CEO).
Coverage **FIRE**; purchases USD 192,750, owners 2, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): HPP 8.96, OFRM 10.02, TG 5.79, GRRR 7.42, XMAX 6.15.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ATEC (Alphatec Holdings, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001289408-26-000006`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 7 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001289408-26-000006` (1 filing(s)) by Valentine Keith (director).
Coverage **FIRE**; purchases USD 242,550, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): UMAC 12.59, CMPS 9.25, EROC 7.87, APPS 7.25, SNDX 9.49.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PSEC (PROSPECT CAPITAL CORP) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001294357-26-000018`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.5 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001294357-26-000018` (1 filing(s)) by Barry John F (CHIEF EXECUTIVE OFFICER).
Coverage **FIRE**; purchases USD 1,727,314, owners 1, top executive yes, lag 4 days.
Twins (band+liq+mom+dd): CERS 1.95, SSTK 2.83, FATE 1.77, LTBR 4.53, DPRO 3.21.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FIS (Fidelity National Information Services, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001628280-26-072763`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 28.31 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-072763` (1 filing(s)) by Gibson Kourtney (director).
Coverage **FIRE**; purchases USD 52,200, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): WDC 289.2, TER 245.4, STX 501.62, MTZ 180.84, CRS 297.37.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 SLQT (SelectQuote, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001794783-26-000091`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 0.4572 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001794783-26-000091` (3 filing(s)) by Danker Timothy Robert (CHIEF EXECUTIVE OFFICER), Hawks Donald L III (director), Weldon Raymond F (director).
Coverage **FIRE**; purchases USD 365,774, owners 3, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): SURG 0.1583, NMRA 0.4666, XTIA 0.9981, XHLD 0.858, CRIS 0.653.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 OBK (Origin Bancorp, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001839920-26-000008`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 54.24 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001839920-26-000008` (1 filing(s)) by Crotwell Jim (Chief Risk Officer).
Coverage **FIRE**; purchases USD 107,160, owners 1, top executive no, lag 4 days.
Twins (band+liq+mom+dd): FSBC 44.2, RBB 26.09, KARO 63.87, NBBK 22.19, MSBI 32.44.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 STRA (Strategic Education, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001859730-26-000004`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 54.59 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001859730-26-000004` (2 filing(s)) by Slocum William J (director), Thawley Michael (director).
Coverage **FIRE**; purchases USD 163,118, owners 2, top executive no, lag 0 days.
Twins (band+liq+mom+dd): GDS 21.41, KMT 24.03, GGAL 29.91, CECO 51.83, GIL 35.69.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 FUN (Six Flags Entertainment Corporation/NEW) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0001999001-26-000111`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 10.16 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0001999001-26-000111` (2 filing(s)) by HADDRILL RICHARD M (Executive Chair), JAFFER REHAN (director).
Coverage **FIRE**; purchases USD 15,019,720, owners 2, top executive no, lag 0 days.
Twins (band+liq+mom+dd): ALKT 14.16, QUBT 6.3, NAMS 19.18, HMY 16.37, SBSW 9.36.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 CNXN (PC CONNECTION INC) - filed 2026-11-10, sealed 2026-11-11T10:53:45Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4-0002160413-26-000005`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 82.1 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Form 4 `0002160413-26-000005` (1 filing(s)) by Zafirovski Matthew David (President & COO).
Coverage **FIRE**; purchases USD 199,698, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): NGVT 60.78, INVX 24.91, NICE 93.73, TEN 45.16, WIX 64.38.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

