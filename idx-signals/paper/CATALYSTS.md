# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-13T23:06:44Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 26 (FIRE 9, ABSTAIN 17) over 9 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 14, SEALED 26, SKIP_NOT_OPERATING 4, SKIP_LATE 2, SKIP_NO_TICKER 5, SKIP_REPEAT_90D 1; coverage gaps 1.

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

Sets 48 over 9 signal sessions; events seen: SEALED 48, SKIP_REPEAT_90D 42, SKIP_NO_TICKER 25, SKIP_NOT_IN_UNIVERSE 27, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 112 over 6 signal sessions; events seen: SEALED 112, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 5022, SKIP_LATE 41, SKIP_NO_TICKER 4, SKIP_NOT_OPERATING 3, SKIP_REPEAT_90D 19; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 112 over 6 signal sessions; events seen: SEALED 112; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 41, FIRE 71
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 24 over 8 signal sessions; events seen: SEALED 24; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 13, FIRE 11
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

### FORM4_SHARP URG (UR-ENERGY INC) - filed 2026-11-12, sealed 2026-11-13T10:55:58Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4_SHARP-0001654954-26-009739`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 0.6185 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001654954-26-009739` by Walle Jade (VICE PRESIDENT FINANCE); purchases USD 109,999; top executive no; holding up +38.7%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001654954-26-009739.
Twins (band+liq+mom+dd): SHFS 0.0225, CENN 0.182, EYPT 0.3195, OPTU 0.6374, AKBA 0.498, SIDU 0.9558, SDEV 0.7845, XRX 0.9912, SID 0.7723, ALLO 0.827, SLNH 0.5338, BMGL 0.57, RBNE 0.1202, CATX 0.8424, SITC 0.6944, DVLT 0.0564, NAK 0.604, ORBS 0.6734, JDZG 0.1916, RR 0.8188.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TH (Target Hospitality Corp.) - filed 2026-11-12, sealed 2026-11-13T10:55:58Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4_SHARP-0001712189-26-000063`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 11.98 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001712189-26-000063` by Archer James Bradley (Director and CEO and President); purchases USD 312,675; top executive yes; holding up +1.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001712189-26-000063.
Twins (band+liq+mom+dd): IE 6.95, BTU 17.41, WYFI 10.335, ADEA 16.63, STWD 11.44, MBLY 5.64, LPTH 7.21, STNE 7.72, UUUU 6.68, BFLY 6.67, MUX 11.95, MFA 5.56, UMAC 11.83, AESI 5.5, HMY 15.44, ORIC 8.5, UEC 6.8, NMRK 10.86, BLZE 8.79, FCEL 10.25.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BLMN (Bloomin' Brands, Inc.) - filed 2026-11-12, sealed 2026-11-13T10:55:58Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4_SHARP-0001719998-26-000016`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 10.12 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001719998-26-000016` by Spanos Mike (CEO); purchases USD 502,000; top executive yes; holding up +20.6%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001719998-26-000016.
Twins (band+liq+mom+dd): NHP 15.17, FOXF 17.32, ASAN 9.67, SGHC 11.42, DNLI 18.89, HAFN 9.62, AMPX 8.35, PTEN 10.67, GNW 8.41, LI 11.69, GNTX 19.37, BCRX 7.68, PWP 13.445, ABCL 11.62, WLTH 10.2, MFG 10.12, TALO 15.98, BXMT 10.82, LEGN 18.54, ASC 19.02.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP LILA (Liberty Latin America Ltd.) - filed 2026-11-12, sealed 2026-11-13T10:55:58Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4_SHARP-0001724519-26-000014`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 9.73 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001724519-26-000014` by DE ANGOITIA ALFONSO (director); purchases USD 5,061,969; top executive no; holding up +52.4%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001724519-26-000014.
Twins (band+liq+mom+dd): ASTL 5.61, ACEL 13.83, TLS 7.72, LFTO 18.71, JBGS 11.99, AHCO 7.87, SENS 10.04, EVC 9.43, MAGN 12.97, GRNT 6.49, PHR 12.62, PEPG 5.04, PUBM 19.02, SBGI 14.58, YEXT 7.65, CASK 17, INN 7.23, MITK 18.25, INTT 14.76, CODI 11.8.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ITIC (INVESTORS TITLE CO) - filed 2026-11-12, sealed 2026-11-13T10:55:58Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4_SHARP-0001804353-26-000010`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 251.59 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001804353-26-000010` by Parker, Jr. Elton C. (director); purchases USD 133,000; top executive no; holding up +13.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001804353-26-000010.
Twins (band+liq+mom+dd): NSSC 30.34, ODC 73.15, CSV 27.9, ROOT 43.63, BGSI 74.46, MMI 24.25, ATLC 79.3, FLXS 75.13, NTGR 20.09, JILL 22.43, XPEL 37.62, HBB 30.5, VEON 75.15, FOR 22.24, CWCO 25.29, BXC 62.83, APEI 41.16, BWLP 22.09, ASTH 31.77, PBT 30.32.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ZVIA (Zevia PBC) - filed 2026-11-12, sealed 2026-11-13T10:55:58Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4_SHARP-0001847944-26-000007`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 1.06 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001847944-26-000007` by Ruberti Alexandre (President & CEO); purchases USD 99,910; top executive yes; holding up +6.7%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001847944-26-000007.
Twins (band+liq+mom+dd): GNLX 1.9, PROK 1.15, BMM 3.15, ICU 1.05, ZONE 3.5, BIAF 2.34, IKT 1.53, MWYN 1.36, ATOM 2.9, ANNA 2.29, PMN 3.48, TWG 2.5, NKTX 1.265, WORX 1.27, LNZA 3.93, MOB 2.32, EMPD 2.03, HOLO 1.23, IPWR 2.19, YMAT 1.23.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP FIP (FTAI Infrastructure Inc.) - filed 2026-11-12, sealed 2026-11-13T10:55:58Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4_SHARP-0001899883-26-000044`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 4.23 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001899883-26-000044` by Nicholson Kenneth J. (CEO and President); purchases USD 1,530,000; top executive yes; holding up +18.4%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001899883-26-000044.
Twins (band+liq+mom+dd): MNKD 4.16, BDN 3.06, EGHT 2.33, EVGO 1.75, UIS 2.87, CLVT 2.3, CRON 3.41, CLNE 1.98, OABI 4.95, ACB 4.99, LZM 4.29, SSP 3.62, IRWD 4.85, GEVO 1.86, OPK 1.67.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NOMD (Nomad Foods Ltd) - filed 2026-11-12, sealed 2026-11-13T10:55:58Z, cutoff 2026-11-13T14:15:00Z
Set `CAT-FORM4_SHARP-0002111999-26-000011`, scan `SCAN-US-2026-11-12-G2_RET30`; signal close 11.65 on 2026-11-12; entry: the entry session's opening print (2026-11-13). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002111999-26-000011` by BALDEW RUBEN (Chief Financial Officer); purchases USD 100,161; top executive yes; holding up +2.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002111999-26-000011.
Twins (band+liq+mom+dd): IHS 8.41, LXFR 17.34, PAYO 7.18, DGICA 18.96, MATV 12.01, RELL 19.74, VREX 18.27, RNW 6.96, FDUS 19.32, KRNT 17.13, CFFN 8.46, VNCE 12.91, FMNB 15.46, MQ 18.03, TSLX 17.56, LFCR 6.4, GLAD 19.39, PRTH 7.91, FNKO 6.9.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D COUR (Coursera, Inc.) - accepted 2026-11-13T16:20:15-05:00, sealed 2026-11-13T23:06:05Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-SEC13D-0001072613-26-000890`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 3.51 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Filing `0001072613-26-000890` by NEW ENTERPRISE ASSOCIATES 13 LP; Item 4 intent words: board, merger, acquisition, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 889.1M, dilution filings 0.
Twins (band+liq+mom+dd): PGEN 4.54, RCAT 3.8, SOUN 3.49, NUVB 3.99, UNIT 4.88.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 COUR (Coursera, Inc.) - accepted 2026-11-13T16:20:15-05:00, sealed 2026-11-13T23:06:16Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-SEC13D_V2-0001072613-26-000890`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 3.51 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001072613-26-000890` by NEW ENTERPRISE ASSOCIATES 13 LP; cover page max 5.1% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 889.1M from XBRL; parent CAT-SEC13D-0001072613-26-000890.
Twins (band+liq+mom+dd): PGEN 4.54, RCAT 3.8, SOUN 3.49, NUVB 3.99, UNIT 4.88, OI 4.96, CRML 4.88, ENVX 1.6, FLNC 4.68, HIVE 1.57, PONY 4.46, INTR 4.15, DJT 4.64, KEEL 1.86, ASM 4.29, BBAI 1.91, OPEN 1.19, LAC 1.49, VISN 4.24, QS 3.68.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K SPCE - event `0001193125-26-459413`, accepted 2026-11-13T08:39:13-05:00, sealed 2026-11-13T23:06:37Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-459413`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 1.84 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -31.09%.
Twins (band+liq+mom+dd): STTK 4.65, GLAS 1.27, BLDP 1.4, GCTS 1.26, SERV 2.62.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K RAIN - event `0001213900-26-119274`, accepted 2026-11-13T09:18:50-05:00, sealed 2026-11-13T23:06:37Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-DILUTION_8K-0001213900-26-119274`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 0.7499 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +58.21%.
Twins (band+liq+mom+dd): PMAX 0.6403, LNKS 0.8998, CNEY 0.4672, RKDA 0.218, SCAG 0.9.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K XRX - event `0001193125-26-460692`, accepted 2026-11-13T16:16:11-05:00, sealed 2026-11-13T23:06:37Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-460692`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 0.9153 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): OPTU 0.5245, RR 0.7553, EYPT 0.306, SID 0.6288, AKBA 0.4742.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K ARAY - event `0001437749-26-036943`, accepted 2026-11-13T17:01:49-05:00, sealed 2026-11-13T23:06:37Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-DILUTION_8K-0001437749-26-036943`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 2.8 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): VYGR 1.73, AARD 1.33, HYPD 2.58, GANX 1.04, AVX 3.86.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K YYAI - event `0001493152-26-051834`, accepted 2026-11-13T17:15:19-05:00, sealed 2026-11-13T23:06:37Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-051834`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 0.76 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): LNKS 0.8998, SCAG 0.9, SNES 0.862, BFRG 0.5415, CNEY 0.4672.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

