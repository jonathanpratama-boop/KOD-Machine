# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-09T10:35:46Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 14 (FIRE 6, ABSTAIN 8) over 5 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 11, SEALED 14, SKIP_NOT_OPERATING 3, SKIP_LATE 2, SKIP_NO_TICKER 3, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 22 over 5 signal sessions; events seen: SEALED 22, SKIP_REPEAT_90D 19, SKIP_NO_TICKER 21, SKIP_NOT_IN_UNIVERSE 18; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 38 over 3 signal sessions; events seen: SEALED 38, SKIP_NOT_IN_UNIVERSE 4, SKIP_NOT_PURCHASE 3287, SKIP_LATE 41, SKIP_NO_TICKER 2, SKIP_NOT_OPERATING 2; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 27 over 2 signal sessions; events seen: SEALED 27; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 10, FIRE 17
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 12 over 4 signal sessions; events seen: SEALED 12; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 5, FIRE 7
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

95 tags: 19 true, 0 unknown.

## Latest sets

### SEC13D TGE (Generation Essentials Group) - accepted 2026-11-06T18:43:39-05:00, sealed 2026-11-09T10:31:18Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D-0001213900-26-117049`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 0.3635 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Filing `0001213900-26-117049` by AMTD Group Inc.; Item 4 intent words: none.
Coverage **ABSTAIN** (MV_UNKNOWN); pre-entry move +0.00%, market value n/a, dilution filings 0.
Twins (band+liq+mom+dd): DXF 0.257, BRAG 0.7675, ZBAO 0.23, SOS 0.195, GIFT 0.5131.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D BAK (BRASKEM SA) - accepted 2026-11-06T19:58:00-05:00, sealed 2026-11-09T10:31:18Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D-0000921895-26-002956`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 1.09 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Filing `0000921895-26-002956` by HELU CARLOS SLIM; Item 4 intent words: board, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 492.3M, dilution filings 0.
Twins (band+liq+mom+dd): AUTL 1.28, STLN 3.62, ADTN 4.04, QTEX 1.03, ANGX 3.39.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 TGE (Generation Essentials Group) - accepted 2026-11-06T18:43:39-05:00, sealed 2026-11-09T10:31:36Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D_V2-0001213900-26-117049`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 0.3635 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001213900-26-117049` by AMTD Group Inc.; cover page max 95.7% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 89.8M from COVER_PAGE; parent CAT-SEC13D-0001213900-26-117049.
Twins (band+liq+mom+dd): DXF 0.257, NYXH 0.8456, CIGL 0.1833, NHTC 0.7698, SLXN 0.1452, SCNI 0.441, GLXG 0.71, LOT 0.3248, VRAX 0.7919, RDHL 0.4279, BQ 0.4211, CLIK 0.6787, REFR 0.3658, AZI 0.628, TCRX 0.188, MCRP 0.3577, GIPR 0.2548, FLUX 0.316, GTEC 0.5101, HDRN 0.675.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### SEC13D_V2 BAK (BRASKEM SA) - accepted 2026-11-06T19:58:00-05:00, sealed 2026-11-09T10:31:36Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-SEC13D_V2-0000921895-26-002956`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 1.09 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0000921895-26-002956` by HELU CARLOS SLIM; cover page max 4.0% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 492.3M from XBRL; parent CAT-SEC13D-0000921895-26-002956.
Twins (band+liq+mom+dd): FATE 1.835, GCTS 1.16, BTGO 4.86, TMQ 2.15, AIRJ 2.385, CRBP 3.07, ATOM 3.01, PSEC 1.41, ARTV 4.15, DKI 1.47, KOPN 3.035, RXT 2.53, ALT 2.08, HDSN 4.18, CCOI 3.98, CABA 1.3, WFF 1.17, MDXG 3.31, SION 3.28, XRX 1.08.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### FORM4 CVS (CVS HEALTH Corp) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0000064803-26-000112`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 83.85 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0000064803-26-000112` (1 filing(s)) by Shah Prem S (EVP and Group President).
Coverage **FIRE**; purchases USD 2,001,315, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): B 40.56, HPQ 28.46, FR 53.76, EQT 49.4, MUSA 521.89.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 TRNS (TRANSCAT INC) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0000891839-26-000478`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 101.51 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0000891839-26-000478` (1 filing(s)) by IRICK JAIME A (President and CEO).
Coverage **FIRE**; purchases USD 230,366, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): ITRI 98.44, ORKA 102.86, CVCO 638.55, GLBE 42.97, HTO 62.95.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 ANVS (Annovis Bio, Inc.) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001104659-26-123905`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 0.8449 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001104659-26-123905` (1 filing(s)) by Hoffman Michael B (director).
Coverage **FIRE**; purchases USD 5,000,000, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): LABT 0.3863, EU 0.6301, FLL 0.6225, NIVF 0.4565, OLOX 0.6961.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 KOD (Kodiak Sciences Inc.) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001193125-26-451994`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 99.3 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-451994` (1 filing(s)) by BAKER BROS. ADVISORS LP (director), 667, L.P. (director), Baker Bros. Advisors (GP) LLC (director), Baker Brothers Life Sciences LP (director), BAKER FELIX (director), BAKER JULIAN (director).
Coverage **FIRE**; purchases USD 24,340,836, owners 6, top executive no, lag 1 days.
Twins (band+liq+mom+dd): ENB 46.89, DBX 34.66, RMD 235.3, EPD 37.03, EMR 162.35.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 MDGL (MADRIGAL PHARMACEUTICALS, INC.) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001193125-26-452132`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 399.63 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001193125-26-452132` (1 filing(s)) by BAKER BROS. ADVISORS LP (director), Baker Bros. Advisors (GP) LLC (director), BAKER FELIX (director), BAKER JULIAN (director), 667, L.P. (director), Baker Brothers Life Sciences LP (director).
Coverage **FIRE**; purchases USD 35,023,032, owners 6, top executive no, lag 0 days.
Twins (band+liq+mom+dd): DINO 97.18, STM 41.72, MPWR 1190.44, ORCL 116.1, INSW 98.02.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 LKQ (LKQ CORP) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001214659-26-013801`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 20.05 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001214659-26-013801` (1 filing(s)) by GOVE SUE (director).
Coverage **FIRE**; purchases USD 201,085, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): DTM 113.66, UMBF 133.77, HALO 103.63, CACI 611.16, ATI 175.79.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 PMN (ProMIS Neurosciences Inc.) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001374339-26-000011`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 4.16 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001374339-26-000011` (1 filing(s)) by Williams Eugene (director).
Coverage **FIRE**; purchases USD 90,895, owners 1, top executive no, lag 2 days.
Twins (band+liq+mom+dd): MOB 2.17, ZONE 3.08, AMPG 2.305, GANX 1.03, GMTL 4.76.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 AGMB (AgomAb Therapeutics NV) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001445826-26-000018`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 7.635 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001445826-26-000018` (1 filing(s)) by Epstein David R (director).
Coverage **FIRE**; purchases USD 103,500, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): AOMR 5.95, TTRX 9.48, WYY 6.29, AUDC 7.85, AP 5.89.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 KMI (KINDER MORGAN, INC.) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001506307-26-000139`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 29.96 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001506307-26-000139` (1 filing(s)) by KINDER RICHARD D (Executive Chairman).
Coverage **FIRE**; purchases USD 14,994,200, owners 1, top executive no, lag 0 days.
Twins (band+liq+mom+dd): EXPE 259.24, WMB 64.08, PSX 245.72, OXY 56.38, TXN 277.36.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 GFS (GLOBALFOUNDRIES Inc.) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001628280-26-071813`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 38.62 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-071813` (1 filing(s)) by MOORTHY GANESH (director).
Coverage **FIRE**; purchases USD 93,688, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): INTC 56.28, ENPH 28.465, NTAP 169.19, POWL 133.12, KEYS 272.13.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 KMT (KENNAMETAL INC) - filed 2026-11-06, sealed 2026-11-09T10:35:31Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4-0001782435-26-000005`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 23 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20.
Form 4 `0001782435-26-000005` (1 filing(s)) by Chowbey Sanjay (President and CEO).
Coverage **FIRE**; purchases USD 165,368, owners 1, top executive yes, lag 1 days.
Twins (band+liq+mom+dd): ATRO 54.71, PRLB 65.69, GGAL 29.44, CVI 38.13, ACLS 99.24.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

