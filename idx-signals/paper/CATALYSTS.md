# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-12T23:03:36Z). Nothing here is a result until a look is reached.

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

Sets 34 over 7 signal sessions; events seen: SEALED 34, SKIP_REPEAT_90D 32, SKIP_NO_TICKER 23, SKIP_NOT_IN_UNIVERSE 22, SKIP_NOT_OPERATING 1; coverage gaps 1.
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

165 tags: 40 true, 0 unknown.

## Latest sets

### FORM4_SHARP WW (WW INTERNATIONAL, INC.) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-455831`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 12.02 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-455831` by Gavales Lisa A (director), BYE STEPHEN J (President and CEO); purchases USD 192,750; top executive yes; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001193125-26-455831.
Twins (band+liq+mom+dd): HPP 8.96, OFRM 10.02, TG 5.79, GRRR 7.42, XMAX 6.15, RYAM 5.61, CRMD 5.37, YARW 15.48, ADAM 5.45, LAND 6.88, AGBK 5.1, PICS 6.96, HPK 6.82, ASYS 12.06, BYND 5.65, CLB 8.95, RMIX 8.62, TSSI 6.96, ANL 9.96, SAFE 10.32.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ATEC (Alphatec Holdings, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0001289408-26-000006`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 7 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001289408-26-000006` by Valentine Keith (director); purchases USD 242,550; top executive no; holding up +13.2%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001289408-26-000006.
Twins (band+liq+mom+dd): UMAC 12.59, CMPS 9.25, EROC 7.87, APPS 7.25, SNDX 9.49, UGP 5.39, NRIX 15.88, MBLY 5.63, AESI 5.36, UUUU 6.74, SBET 5.85, FCEL 10.28, AGLT 9.18, RCUS 18.67, AVBP 13.49, ADEA 16.25, SLM 16.78, BCAX 10.18, NAVI 6.745, LBRT 12.49.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PSEC (PROSPECT CAPITAL CORP) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0001294357-26-000018`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 1.5 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001294357-26-000018` by Barry John F (CHIEF EXECUTIVE OFFICER); purchases USD 1,727,314; top executive yes; holding up +1.3%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 3; routine owners 0 of 1; parent CAT-FORM4-0001294357-26-000018.
Twins (band+liq+mom+dd): CERS 1.95, SSTK 2.83, FATE 1.77, LTBR 4.53, DPRO 3.21, RXT 2.68, GCTS 1.45, STTK 4.85, TBLA 2.02, TNXP 4.1, IAUX 1.39, BMGL 1.93, KOPN 3.32, GEMI 2.65, SION 3.7, GSM 2.76, AUTL 1.32, REI 1.13, VRRM 2.06, BTGO 4.27.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP FIS (Fidelity National Information Services, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-072763`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 28.31 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-072763` by Gibson Kourtney (director); purchases USD 52,200; top executive no; holding up +43.9%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-072763.
Twins (band+liq+mom+dd): WDC 289.2, TER 245.4, STX 501.62, MTZ 180.84, CRS 297.37, MOD 103.07, IESC 172.43, ASST 21.55, CORT 73.35, RMBS 80.76, DAVE 273.85, FFIV 317.31, CRDO 129.8, AXTI 39.31, CIEN 272.1, SE 76.8, KGS 42.26, FPS 21.48, ALNY 151.64, MTSI 226.48.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SLQT (SelectQuote, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0001794783-26-000091`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 0.4572 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001794783-26-000091` by Danker Timothy Robert (CHIEF EXECUTIVE OFFICER), Hawks Donald L III (director), Weldon Raymond F (director); purchases USD 365,774; top executive yes; holding up +79.9%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 3; parent CAT-FORM4-0001794783-26-000091.
Twins (band+liq+mom+dd): SURG 0.1583, NMRA 0.4666, XTIA 0.9981, XHLD 0.858, CRIS 0.653.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP OBK (Origin Bancorp, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0001839920-26-000008`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 54.24 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001839920-26-000008` by Crotwell Jim (Chief Risk Officer); purchases USD 107,160; top executive no; holding up +8.2%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001839920-26-000008.
Twins (band+liq+mom+dd): FSBC 44.2, RBB 26.09, KARO 63.87, NBBK 22.19, MSBI 32.44, CFFI 107.7, CASS 55.55, UVSP 40.83, SAFT 104.49, OSBC 25.08, BHRB 70.6, CWBC 26.22, AVBC 22.83, PLBC 63.09, HTH 36.9, SPFI 43.08, CSR 57.17, SHBI 22.85, PBAM 86.48, WABC 59.85.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP STRA (Strategic Education, Inc.) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0001859730-26-000004`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 54.59 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001859730-26-000004` by Slocum William J (director), Thawley Michael (director); purchases USD 163,118; top executive no; holding up +16.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001859730-26-000004.
Twins (band+liq+mom+dd): GDS 21.41, KMT 24.03, GGAL 29.91, CECO 51.83, GIL 35.69, ICHR 35.27, PSIX 36.58, ETOR 21.56, KLIC 69.7, CMPR 56.52, SEDG 25.86, SSRM 28.2, OII 35.06, DOX 41.46, CAMT 102.19, WERN 27.75, ECG 85.73, DCO 145.58, LGN 32.05, PRLB 67.93.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP FUN (Six Flags Entertainment Corporation/NEW) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0001999001-26-000111`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 10.16 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001999001-26-000111` by HADDRILL RICHARD M (Executive Chair), JAFFER REHAN (director); purchases USD 15,019,720; top executive no; holding up +29.6%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001999001-26-000111.
Twins (band+liq+mom+dd): ALKT 14.16, QUBT 6.3, NAMS 19.18, HMY 16.37, SBSW 9.36, MBC 6.66, INFQ 9.35, SRPT 16.42, STWD 11.89, ACAD 18.28, AADX 10.72, OCUL 6.61, ALHC 7.67, EXK 8.07, LUNR 11.81, AEVA 12.27, IVR 5.33, PPTA 19.33, BBNX 16.52, SVM 9.31.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CNXN (PC CONNECTION INC) - filed 2026-11-10, sealed 2026-11-11T10:55:57Z, cutoff 2026-11-11T14:15:00Z
Set `CAT-FORM4_SHARP-0002160413-26-000005`, scan `SCAN-US-2026-11-10-G2_RET30`; signal close 82.1 on 2026-11-10; entry: the entry session's opening print (2026-11-11). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002160413-26-000005` by Zafirovski Matthew David (President & COO); purchases USD 199,698; top executive yes; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002160413-26-000005.
Twins (band+liq+mom+dd): NGVT 60.78, INVX 24.91, NICE 93.73, TEN 45.16, WIX 64.38, BH 349.22, WBI 26.26, EFXT 20.09, BMA 57.83, SKYW 83.76, SXI 246.22, DAC 147.24, TDW 73.98, TRMD 34.3, IOSP 77.72, CRC 47.12, NOVT 123.71, DGII 65.05, ERO 30.67, OTTR 79.77.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

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

