# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-10T23:03:31Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 20 (FIRE 7, ABSTAIN 13) over 7 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 12, SEALED 20, SKIP_NOT_OPERATING 3, SKIP_LATE 2, SKIP_NO_TICKER 3, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 63 over 4 signal sessions; events seen: SEALED 63; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 25, FIRE 38
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 18 over 6 signal sessions; events seen: SEALED 18; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 9, FIRE 9
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

### FORM4_SHARP ECHO (EchoStar CORP) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001393025-26-000007`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 101.19 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001393025-26-000007` by Wall William P (director); purchases USD 90,410; top executive no; holding up +40.0%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001393025-26-000007.
Twins (band+liq+mom+dd): WELL 247.35, PSA 338.15, AEE 114.02, PLNT 61.11, ITT 218.21, BYD 77.86, VOYA 104.59, AZN 189.39, GPN 97.77, O 59.5, BAH 86.7, CART 58.46, INCY 121.89, BUD 85.09, NKE 39.88, KNSL 386.07, TROW 110.82, TTEK 41.09, GDDY 111.71, PRMB 24.13.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP FGBI (First Guaranty Bancshares, Inc.) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-035913`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 12.32 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-035913` by Smith Edgar R. III (director); purchases USD 59,000; top executive no; holding up +0.2%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001437749-26-035913.
Twins (band+liq+mom+dd): HCM 15.32, WFCF 15.68, PERI 11.4, DIBS 5.79, CPSS 10.45, SPOK 11.99, LAW 5.62, LUXE 10.56, GNE 19.25, OPRX 9.47, SKYH 10.89, TCX 13.52, MOBI 12.26, BCBP 9.17, GLRE 16.13, MED 13.37, RMNI 5.41, HYNE 18.24, FCBM 13.49, ULBI 15.69.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NXRT (NexPoint Residential Trust, Inc.) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-035984`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 15.75 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-035984` by Richards Paul (See Remarks), McGraner Matt (See Remarks); purchases USD 302,319; top executive no; holding up +19.6%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001437749-26-035984.
Twins (band+liq+mom+dd): SWMR 8.97, MNTN 5.19, ILPT 5.88, HNRG 10.59, JANX 12.76, AMCX 8.9, DUOT 5.2, QUAD 7.47, ALMU 7.47, STVN 13.73, RVII 15.83, OBE 9.22, TG 5.9, RNGR 12.47, TWI 5.04, PRAA 12.71, CIM 7.28, NRDS 7.82, AGRO 9.12, VELO 6.23.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NSLR (Neostellar Capital Corp.) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-050692`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 6.15 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-050692` by Potter Leonard (director); purchases USD 115,200; top executive no; holding up +18.9%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001493152-26-050692.
Twins (band+liq+mom+dd): RPGL 9.19, AP 6, OPI 13.73, NOA 9.57, MAAS 10.15, PTN 7.23, ENHA 8.48, ELA 10.56, GMTL 5.14, TMS 5.13, KGEI 5.24, SAR 13.02, NEGG 8.91, EUDA 14.18, WYY 6.24, OCC 10.6, SUPX 5.7, CPIX 5.37, RYM 17.105, HQ 13.81.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ROK (ROCKWELL AUTOMATION, INC) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001515154-26-000003`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 389.36 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001515154-26-000003` by Moret Blake D. (President and CEO); purchases USD 1,545,450; top executive yes; holding up +4.2%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001515154-26-000003.
Twins (band+liq+mom+dd): INSW 96.45, SEI 62.61, ZBRA 326.71, DINO 99.76, STM 44.54, FCFS 187.83, WMB 66.45, ANET 186.17, PANW 330.89, PBF 69.55, BKR 48.45, ENS 151.63, MSTR 125.59, GTLB 47.12, ORCL 119.79, PWR 591.48, PRIM 71.24, NTAP 176.07, SHOP 152.06, GGG 69.82.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CMCO (COLUMBUS MCKINNON CORP) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-072106`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 19.67 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-072106` by Wilson David J. (President & CEO); purchases USD 551,349; top executive yes; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-072106.
Twins (band+liq+mom+dd): JBGS 12.38, IIIV 19.31, OABI 5.3, AURA 7.66, CHPT 12.39, TIC 11.29, SWIM 8.4, CRCT 8.79, PSFE 7.09, PTLO 6.89, ZVRA 12.14, LILA 9.29, YEXT 7.58, HLMN 8.38, UA 5.28, VEL 17.65, ARDT 17.97, INN 7.21, RPC 9.96, DBI 6.75.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP AFCG (Advanced Flower Capital Inc.) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-072331`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 3.435 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-072331` by TANNENBAUM LEONARD M (director); purchases USD 56,980; top executive no; holding up +0.3%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-072331.
Twins (band+liq+mom+dd): YDKG 1.04, GROV 1.1, EFOI 4.395, TOMZ 2.42, ISPR 1.67, LEDS 2.44, MRT 2.17, AWX 2.76, BRIA 1.47, AIRI 2.82, SERA 2.19, ORIO 1.08, CLPR 3.28, GCL 1.05, MLCI 3.59, YHGJ 3.61, REED 1.25, KMRK 1.51, CLGN 4.29, SNT 2.45.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP LUCK (Lucky Strike Entertainment Corp) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-072428`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 3.76 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-072428` by Young John Alan (director); purchases USD 56,990; top executive no; holding up +16.7%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-072428.
Twins (band+liq+mom+dd): SPAI 3.28, UP 2.76, SKIL 3.35, ACET 2.99, SOTK 4.3, SND 3.95, AIFA 3.91, CURR 1.9, MGNX 2.34, CRVO 1.43, WORX 1.39, GTBP 4.32, PROK 1.15, DAIC 1.06, VIVO 1.89, BBOT 2.3, CDXS 1.11, MITT 4.56, BXBL 1.87, PMN 4.05.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SOPH (SOPHiA GENETICS SA) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001840706-26-000351`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 7.49 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001840706-26-000351` by Muken Ross (Chief Executive Officer), CARDOZA GEORGE (Chief Financial Officer); purchases USD 278,388; top executive yes; holding up +6.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001840706-26-000351.
Twins (band+liq+mom+dd): DRTS 14.11, GAIN 15.09, FVRR 8.48, ACIC 10.01, AVO 11.91, ASIX 15.63, FF 5.07, DEC 12.91, PHI 18.11, MTA 8.45, MASS 11.51, USNA 13.85, PFLT 6.86, EPRX 7.42, HTLD 10.52, AVNW 19.13, SCZM 8.09, SHEN 10.21, PRTA 8.775, XZO 16.5.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP GOOD (GLADSTONE COMMERCIAL CORP) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001873961-26-000002`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 10.225 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001873961-26-000002` by Cooper Arthur S. (CEO & President); purchases USD 99,999; top executive yes; holding up +27.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001873961-26-000002.
Twins (band+liq+mom+dd): XGN 7.1, MNRO 11.14, SSYS 6.68, NAVI 7.84, AMSF 19.63, SHIP 14.33, EOLS 6.98, INVA 19, XXI 5.57, EGY 5.39, SB 7.22, TTAM 11.64, SD 12.24, HSHP 15.66, EBS 6.1, RMR 15.75, ELPC 10.91, FPI 8.85, OOMA 18.18, OPRA 15.49.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP AUDC (AUDIOCODES LTD) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001976408-26-000933`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 8.5 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001976408-26-000933` by ADLERSBERG SHABTAI (President and CEO); purchases USD 126,140; top executive yes; holding up +0.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001976408-26-000933.
Twins (band+liq+mom+dd): WATT 8.69, SUPX 5.7, SDOT 6.475, KGEI 5.24, FXHO 5.48, RFIL 7.25, ECOR 7.18, AGPU 7.5, ESOA 9.06, AMTD 13.4, RYM 17.105, OPI 13.73, NVNO 6.85, AKTX 7.66, OTLY 8.125, BDSX 10.34, BNR 12.39, NEGG 8.91, AGMB 7.55, AOMR 6.24.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NLY (ANNALY CAPITAL MANAGEMENT INC) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0001994436-26-000004`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 18.95 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001994436-26-000004` by Wede Scott (director); purchases USD 940,000; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001994436-26-000004.
Twins (band+liq+mom+dd): RIVN 14.01, F 12.52, CDE 16.45, LYFT 16.76, AVTR 15.91, MMED 17.88, CTVA 12.11, CLF 12.26, RIG 5.17, ACI 12.91, SAN 12.46, LYG 5.26, SKYD 8.7, HLN 8.97, HBAN 15.92, AGNC 8.93.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP DKNG (DraftKings Inc.) - filed 2026-11-09, sealed 2026-11-10T10:40:18Z, cutoff 2026-11-10T14:15:00Z
Set `CAT-FORM4_SHARP-0002019299-26-000018`, scan `SCAN-US-2026-11-09-G2_RET30`; signal close 18.7 on 2026-11-09; entry: the entry session's opening print (2026-11-10). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002019299-26-000018` by Ellingson Alan Wayne (Chief Financial Officer); purchases USD 349,987; top executive yes; holding up +9.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002019299-26-000018.
Twins (band+liq+mom+dd): PATH 12.98, RGTI 12.98, HL 15.41, WULF 12.38, PCG 13.14, NVTS 9.58, AG 15.87.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D CMMB (Chemomab Therapeutics Ltd.) - accepted 2026-11-10T17:30:05-05:00, sealed 2026-11-10T23:03:19Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-SEC13D-0001493152-26-051041`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.345 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-051041` by Scipher Medicine Corp; Item 4 intent words: board, merger, director.
Coverage **ABSTAIN** (DILUTION_RECENT); pre-entry move +0.00%, market value USD 773.9M, dilution filings 1.
Twins (band+liq+mom+dd): YYAI 1.05, LEXX 4.68, SOWG 2.02, MB 3.797, CALC 1.37.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 CMMB (Chemomab Therapeutics Ltd.) - accepted 2026-11-10T17:30:05-05:00, sealed 2026-11-10T23:03:29Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-SEC13D_V2-0001493152-26-051041`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.345 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001493152-26-051041` by Scipher Medicine Corp; cover page max 10.4% of class; strong intent: none; Item 5(c): 1 price(s).
Coverage **ABSTAIN** (DILUTION_RECENT); market value USD 773.9M from XBRL; parent CAT-SEC13D-0001493152-26-051041.
Twins (band+liq+mom+dd): YYAI 1.05, LEXX 4.68, SOWG 2.02, MB 3.797, CALC 1.37, MGN 3.4, AZR 3.76, HTCO 1.6, BCG 1.07, WYHG 3.52, WLDS 1.59, INBS 2.25, XAIR 2.52, SILO 1.79, ONEG 1.07, ENLV 1.2, IBO 4.62, LCU 4.35, XHG 3.3, CIIT 2.3.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

