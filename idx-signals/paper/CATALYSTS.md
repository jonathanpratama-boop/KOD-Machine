# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-09T10:37:18Z). Nothing here is a result until a look is reached.

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

Sets 38 over 3 signal sessions; events seen: SEALED 38; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 16, FIRE 22
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

### FORM4_SHARP CVS (CVS HEALTH Corp) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0000064803-26-000112`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 83.85 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0000064803-26-000112` by Shah Prem S (EVP and Group President); purchases USD 2,001,315; top executive yes; holding up +36.9%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0000064803-26-000112.
Twins (band+liq+mom+dd): B 40.56, HPQ 28.46, FR 53.76, EQT 49.4, MUSA 521.89, ADBE 239.3, IVZ 27.08, BURL 246.76, AEM 191.57, EXE 84.6, OXY 56.38, FHN 23.04, HUBB 429.45, TJX 135.3, LYB 60.72, BIDU 81.87, AA 39.54, POR 45.95, GLPI 38.89, RTX 189.53.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TRNS (TRANSCAT INC) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0000891839-26-000478`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 101.51 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0000891839-26-000478` by IRICK JAIME A (President and CEO); purchases USD 230,366; top executive yes; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0000891839-26-000478.
Twins (band+liq+mom+dd): ITRI 98.44, ORKA 102.86, CVCO 638.55, GLBE 42.97, HTO 62.95, SMG 64.71, KMTS 28.8, AWR 89.98, SKWD 60.35, NATL 47.18, SARO 27.63, BILL 52.41, SNN 31.15, GHC 1212.02, MWA 24.05, UBSI 48.22, PFS 22.96, AVNT 45.47, FHI 63.99, SBRA 21.02.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ANVS (Annovis Bio, Inc.) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001104659-26-123905`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 0.8449 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001104659-26-123905` by Hoffman Michael B (director); purchases USD 5,000,000; top executive no; holding up +148.6%.
Coverage **ABSTAIN** (NOT_SHARP, DILUTION_RECENT); dilution filings 2; routine owners 0 of 1; parent CAT-FORM4-0001104659-26-123905.
Twins (band+liq+mom+dd): LABT 0.3863, EU 0.6301, FLL 0.6225, NIVF 0.4565, OLOX 0.6961, NPWR 0.8092, UPXI 0.6399, ALDX 0.6337, AZTR 0.7325, TRX 0.97, QNC 0.8604, BENF 0.7088, HUBC 0.0918, TLSA 0.6888, ABOS 0.2235, VJET 0.5211, WWR 0.3903, SUIG 0.9868, CHRS 0.77, OLB 0.1831.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP KOD (Kodiak Sciences Inc.) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-451994`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 99.3 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-451994` by BAKER BROS. ADVISORS LP (director), 667, L.P. (director), Baker Bros. Advisors (GP) LLC (director), Baker Brothers Life Sciences LP (director), BAKER FELIX (director), BAKER JULIAN (director); purchases USD 24,340,836; top executive no; holding up +1.2%.
Coverage **ABSTAIN** (NOT_SHARP, DILUTION_RECENT); dilution filings 1; routine owners 0 of 6; parent CAT-FORM4-0001193125-26-451994.
Twins (band+liq+mom+dd): ENB 46.89, DBX 34.66, RMD 235.3, EPD 37.03, EMR 162.35, CVLT 158.36, AIG 77.75, HUM 433.74, EQH 52.66, HSIC 86.05, WAL 75.55, SYY 76.86, NSC 319.94, PDD 83.03, SYF 73.74, AMZN 259.3, MRK 146.73, RRX 169.07, PM 197.88, EWBC 128.84.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP MDGL (MADRIGAL PHARMACEUTICALS, INC.) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-452132`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 399.63 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-452132` by BAKER BROS. ADVISORS LP (director), Baker Bros. Advisors (GP) LLC (director), BAKER FELIX (director), BAKER JULIAN (director), 667, L.P. (director), Baker Brothers Life Sciences LP (director); purchases USD 35,023,032; top executive no; holding up +4.7%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 6; parent CAT-FORM4-0001193125-26-452132.
Twins (band+liq+mom+dd): DINO 97.18, STM 41.72, MPWR 1190.44, ORCL 116.1, INSW 98.02, BKR 47.87, META 610.15, ADM 69.97, ROK 375.86, OKTA 168.69, JCI 135.03, CVE 27.45, NTNX 58.37, MSM 113.27, PLTR 160.38, GOOG 283.93, WCC 292.68, ESI 31.35, PRIM 65.4, SEI 57.77.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP LKQ (LKQ CORP) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001214659-26-013801`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 20.05 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001214659-26-013801` by GOVE SUE (director); purchases USD 201,085; top executive no; holding up +89.1%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001214659-26-013801.
Twins (band+liq+mom+dd): DTM 113.66, UMBF 133.77, HALO 103.63, CACI 611.16, ATI 175.79, NWSA 26.385, TECK 60.46, SOLS 58, OVV 60.52, SU 68.74, HUBB 429.45, COP 136.27, WPC 65.05, MTCH 39.03, ARE 44.8, CPT 99.44, LNG 277.95, SNPS 450.46, BURL 246.76, FLUT 81.7.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PMN (ProMIS Neurosciences Inc.) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001374339-26-000011`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 4.16 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001374339-26-000011` by Williams Eugene (director); purchases USD 90,895; top executive no; holding up +193.2%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001374339-26-000011.
Twins (band+liq+mom+dd): MOB 2.17, ZONE 3.08, AMPG 2.305, GANX 1.03, GMTL 4.76, FBIO 1.85, XNET 3.54, MX 2.36, ACET 3.05, WORX 1.29, BSEM 1.13, LHSW 3.24, LITS 1.02, XOS 2.43, GALT 3.14, GSIT 3.015, FRMM 3.04, WRN 1.49, ASTI 1.45, XXII 1.55.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP AGMB (AgomAb Therapeutics NV) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001445826-26-000018`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 7.635 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001445826-26-000018` by Epstein David R (director); purchases USD 103,500; top executive no; holding up +60.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001445826-26-000018.
Twins (band+liq+mom+dd): AOMR 5.95, TTRX 9.48, WYY 6.29, AUDC 7.85, AP 5.89, AMTD 11.63, USAU 11.33, NOA 9.26, ATYR 6.35, WW 11.31, REA 8.06, SBMT 5.51, ACFN 14.63, RFIL 6.66, MRDN 8.68, RPGL 11.26, ANIK 14.55, BNR 13.42, MOVE 5.01, PRPO 18.62.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP KMI (KINDER MORGAN, INC.) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001506307-26-000139`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 29.96 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001506307-26-000139` by KINDER RICHARD D (Executive Chairman); purchases USD 14,994,200; top executive no; holding up +0.2%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001506307-26-000139.
Twins (band+liq+mom+dd): EXPE 259.24, WMB 64.08, PSX 245.72, OXY 56.38, TXN 277.36, BP 44.53, FLR 46.48, UBS 47.78, RIO 83.73, SF 71.35, LPLA 295.51, TECK 60.46, CARR 52.38, UMBF 133.77, URI 1055.57, BABA 109.45, FANG 178.96, GH 150.87, OKE 85.19, JBHT 217.55.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP GFS (GLOBALFOUNDRIES Inc.) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-071813`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 38.62 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-071813` by MOORTHY GANESH (director); purchases USD 93,688; top executive no; holding up +83.3%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-071813.
Twins (band+liq+mom+dd): INTC 56.28, ENPH 28.465, NTAP 169.19, POWL 133.12, KEYS 272.13, SIMO 162.76, TWLO 202.02, LRCX 200.44, P 96.75, IONQ 32.62, FIX 1017.5, ASTS 32.33, MOD 96.61, CORT 72.77, AKAM 83.09, CAT 558.63, IESC 158.45, FIS 28.73, BWA 48.81, CCJ 71.3.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP KMT (KENNAMETAL INC) - filed 2026-11-06, sealed 2026-11-09T10:37:05Z, cutoff 2026-11-09T14:15:00Z
Set `CAT-FORM4_SHARP-0001782435-26-000005`, scan `SCAN-US-2026-11-06-G2_RET30`; signal close 23 on 2026-11-06; entry: the entry session's opening print (2026-11-09). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001782435-26-000005` by Chowbey Sanjay (President and CEO); purchases USD 165,368; top executive yes; holding up +2.6%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001782435-26-000005.
Twins (band+liq+mom+dd): ATRO 54.71, PRLB 65.69, GGAL 29.44, CVI 38.13, ACLS 99.24, SCSC 42.78, AMR 147.93, GIL 34.75, AAON 57.19, YPF 38.66, BAND 40.34, VPG 44.21, TDW 70.06, KALU 106.84, CMPR 56.38, CAMT 97.05, ICHR 30.965, DOX 42.09, PLXS 192.17, COHU 38.49.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

