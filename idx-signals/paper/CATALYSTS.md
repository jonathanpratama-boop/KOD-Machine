# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-25T11:31:22Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 43 (FIRE 19, ABSTAIN 24) over 16 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 22, SEALED 43, SKIP_NOT_OPERATING 10, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 4; coverage gaps 1.

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

Sets 79 over 16 signal sessions; events seen: SEALED 79, SKIP_REPEAT_90D 63, SKIP_NO_TICKER 70, SKIP_NOT_IN_UNIVERSE 47, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 277 over 13 signal sessions; events seen: SEALED 277, SKIP_NOT_IN_UNIVERSE 11, SKIP_NOT_PURCHASE 9562, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 11, SKIP_REPEAT_90D 114; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 277 over 13 signal sessions; events seen: SEALED 277; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 125, FIRE 152
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 41 over 15 signal sessions; events seen: SEALED 41; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 20, FIRE 21
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

361 tags: 89 true, 0 unknown.

## Latest sets

### FORM4_SHARP BWFG (Bankwell Financial Group, Inc.) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075380`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 68.45 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075380` by SEIDMAN LAWRENCE B (director); purchases USD 167,972; top executive no; holding up +16.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075380.
Twins (band+liq+mom+dd): DLX 25.2, KIDS 32.64, RUSHB 58.63, EGBN 33.18, SMP 44.62, GLIBK 26.86, ASR 278.27, TNC 76.47, BBUC 27.97, LEGH 28.51, MTW 22.42, AVBH 34.34, ALRS 32.66, OBK 52.66, QNBC 46.07, SI 20.24, APOG 45.37, PMTS 26.08, BWB 20.52, CVEO 32.83.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BORR (Borr Drilling Ltd) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075382`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 3.81 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075382` by Troim Tor Olav (director); purchases USD 30,451,500; top executive no; holding up +22.4%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075382.
Twins (band+liq+mom+dd): AMC 2.86, SBS 4.63, ABEV 2.64, UAA 4.51, ORC 4.59.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BG (Bunge Global SA) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075421`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 91.97 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075421` by Mahoney Christopher (director); purchases USD 1,161,650; top executive no; holding up +84.3%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075421.
Twins (band+liq+mom+dd): UBS 44.88, BX 115.86, GPC 120.27, HAL 30.57, MTCH 40.33, MOH 197.23, STT 161.25, MAA 113.19, FUTU 88.5, DAR 50.54, AEM 159.7, EOG 145.34, BKNG 144.94, IBKR 76.47, BMY 59.84, ECHO 88.25, ELV 379.55, HUM 383.68, STLD 215.52, RVMD 168.19.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SUNS (Sunrise Realty Trust, Inc.) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075460`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 6.6 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075460` by TANNENBAUM LEONARD M (Executive Chairman); purchases USD 344,500; top executive no; holding up +8.5%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075460.
Twins (band+liq+mom+dd): DIBS 5.28, PROF 6.55, BNR 13.69, ELA 12.01, DMAC 8.82, QUIK 9.38, AGBK 5.54, UFI 5.69, ADSE 9.35, AUC 7.955, SVCO 7.49, TZOO 5.25, MF 17, ANTX 5.14, USCB 19.72, FGBI 11.45, FGC 6.2, EGAN 6.1, TCX 12.745, SKIN 12.07.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP HYLN (Hyliion Holdings Corp.) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075493`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 1.85 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075493` by Boehm Rodger L (director); purchases USD 80,400; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075493.
Twins (band+liq+mom+dd): PACK 2.8, EH 2.45, XNDU 2.01, PDYN 2.57, TROX 1.64, GRML 3.24, ANNX 3.12, NXH 1.27, STTK 4.58, BTQ 1.19, LTBR 3.35, ALMS 4.11, ALT 1.36, UROY 2.39, OSS 4.32, JMIA 2.49, TDUP 1.54, ARTV 3.78, LODE 1.36, FWDI 3.68.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ECVT (Ecovyst Inc.) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0001708035-26-000113`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 9.34 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001708035-26-000113` by Fogarty Kevin Michael (director), Catalano Anna C (director); purchases USD 300,805; top executive no; holding up +53.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001708035-26-000113.
Twins (band+liq+mom+dd): SEG 19.7, FNKO 5.95, NMFC 6.5, MAMA 11.26, KEP 9.31, TLX 8.7, PAX 8.97, GDOT 11.05, VRA 5.42, GAIN 13.81, GOOS 7.63, ARVN 7.01, MANU 19.9, NPB 14.77, PAYP 12.39, NEXN 8.34, EVI 19.56, ANGO 11.01, USNA 13.26, SLRC 10.97.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SCOR (COMSCORE, INC.) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0001853874-26-000016`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 3.41 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001853874-26-000016` by McLaughlin Matthew F. (Chief Executive Officer); purchases USD 258,279; top executive yes; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001853874-26-000016.
Twins (band+liq+mom+dd): YMT 1.28, AZR 3.94, NCRA 1.43, TVRD 1.02, BOF 1.73, TOPS 1.93, WOK 1.15, UZX 1.02, WYHG 2.54, VCIG 2.95, MNDR 1.02, IMMP 3.44, MNOV 1.52, ETS 1.72, ADXN 3.5, AKAN 2.58, OWLS 2.1, LEXX 4.22, TULP 2.29, GP 2.43.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BULL (Webull Corp) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0002093135-26-000006`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 4.45 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002093135-26-000006` by Wang Haichen (Chief Financial Officer); purchases USD 90,000; top executive yes; holding up +1.6%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0002093135-26-000006.
Twins (band+liq+mom+dd): ENVX 1.13, HIVE 1.34, KOS 1.6, POET 3.94, INTR 3.69, LAC 1.33, MPT 1.88, OI 4.26, CRML 3.085, VISN 4.06, PONY 3.37, UAMY 2.39, DNN 1.78, RUM 4.16, DJT 3.885, QS 2.93, SPCE 1.07, BRUN 4.18, ASM 3.67, GT 3.675.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP EDRY (EuroDry Ltd.) - filed 2026-11-23, sealed 2026-11-24T10:36:19Z, cutoff 2026-11-24T14:15:00Z
Set `CAT-FORM4_SHARP-0002127484-26-000026`, scan `SCAN-US-2026-11-23-G2_RET30`; signal close 35.27 on 2026-11-23; entry: the entry session's opening print (2026-11-24). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002127484-26-000026` by Pittas Aristeidis P (director); purchases USD 60,520; top executive no; holding up +2.3%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002127484-26-000026.
Twins (band+liq+mom+dd): DGP 102, KRT 30.06, DRUG 20.11, VPG 46.36, TBN 21.93, IMOS 41.88, SILC 25.53, KRUS 23.59, KOP 29.49.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D VNDA (Vanda Pharmaceuticals Inc.) - accepted 2026-11-24T16:22:35-05:00, sealed 2026-11-24T23:05:17Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-SEC13D-0001193125-26-475804`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 3.75 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Filing `0001193125-26-475804` by Polymeropoulos Mihael Hristos; Item 4 intent words: board, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 226.8M, dilution filings 0.
Twins (band+liq+mom+dd): ICL 4.23, EVH 3.9, TOYO 3.66, SFIX 2.61, GAU 1.8.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 VNDA (Vanda Pharmaceuticals Inc.) - accepted 2026-11-24T16:22:35-05:00, sealed 2026-11-24T23:05:30Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-SEC13D_V2-0001193125-26-475804`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 3.75 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0001193125-26-475804` by Polymeropoulos Mihael Hristos; cover page max 5.01% of class; strong intent: none; Item 5(c): 0 price(s).
Coverage **FIRE**; market value USD 226.8M from XBRL; parent CAT-SEC13D-0001193125-26-475804.
Twins (band+liq+mom+dd): ICL 4.23, EVH 3.9, TOYO 3.66, SFIX 2.61, GAU 1.8, TKC 4.45, TV 2.07, LPL 2.39, CERS 2.04, IVA 3.53, CLNE 1.42, TSHA 4.08, CCCC 3.1, EVLV 4.11, HUCK 2.87, JBI 3.73, CIG 1.79, NUS 4.12, ASTL 4.43, ANNX 3.54.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K APLD - event `0001493152-26-054002`, accepted 2026-11-24T16:15:18-05:00, sealed 2026-11-24T23:05:51Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-054002`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 12.22 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): UMC 13.4, PL 10.64, HIMS 14.74, FIG 16.95, CDE 11.19.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K LOCL - event `0001628280-26-075757`, accepted 2026-11-24T16:37:19-05:00, sealed 2026-11-24T23:05:51Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-DILUTION_8K-0001628280-26-075757`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 0.7406 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): BYAH 0.8, TEAD 0.1443, SLGB 0.1361, CLRB 0.79, LOT 0.1925.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K HY - event `0001173514-26-000269`, accepted 2026-11-24T17:00:45-05:00, sealed 2026-11-24T23:05:51Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-DILUTION_8K-0001173514-26-000269`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 15.68 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): NRDS 7.64, CGEM 10.22, KE 18.1, BETR 13.81, WW 7.645.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K MVIS - event `0001493152-26-054051`, accepted 2026-11-24T17:17:12-05:00, sealed 2026-11-24T23:05:51Z, cutoff 2026-11-25T14:15:00Z
Set `CAT-DILUTION_8K-0001493152-26-054051`, scan `SCAN-US-2026-11-24-G2_RET30`; signal close 0.8576 on 2026-11-24; entry: the entry session's opening print (2026-11-25). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): DOMH 0.8644, BTCS 0.5389, AVD 0.7584, PROP 0.293, SEGG 0.8352.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

