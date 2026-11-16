# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-16T23:15:39Z). Nothing here is a result until a look is reached.

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

Sets 139 over 7 signal sessions; events seen: SEALED 139, SKIP_NOT_IN_UNIVERSE 5, SKIP_NOT_PURCHASE 5649, SKIP_LATE 41, SKIP_NO_TICKER 4, SKIP_NOT_OPERATING 3, SKIP_REPEAT_90D 25; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 139 over 7 signal sessions; events seen: SEALED 139; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 52, FIRE 87
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

220 tags: 55 true, 0 unknown.

## Latest sets

### FORM4_SHARP FCPT (Four Corners Property Trust, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-460757`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 23.32 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-460757` by Lenehan William H (President and CEO); purchases USD 149,992; top executive yes; holding up +0.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-460757.
Twins (band+liq+mom+dd): EPAC 39.37, BETA 23.33, SDGR 29.53, NBR 84.68, APAM 38.43, EXP 180.79, VIRT 59.33, STOK 26.68, SLG 49, LAZ 40.4, PVLA 152.48, SKM 34.57, ZLAB 24.6, PUK 25.57, VSNT 35.94, USLM 111.18, MRCY 81.415, RHI 42, KBH 47.9, RCI 33.24.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TRIN (Trinity Capital Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-460772`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 17.7 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-460772` by Brown Kyle Steven (CEO, President and CIO); purchases USD 58,000; top executive yes; holding up +0.5%.
Coverage **ABSTAIN** (ROUTINE); dilution filings 0; routine owners 1 of 1; parent CAT-FORM4-0001193125-26-460772.
Twins (band+liq+mom+dd): LION 14.03, VYX 10.48, OLN 17.46, AQN 5.6, LBTYA 10.77, BANC 17.83, CALY 17.1, CERT 11.57, CRK 15.18, SMPL 12.57, FSK 11.72, APLE 19.46, OBDC 10.97, GDYN 13.21, CYRX 19.89, RLJ 12.94, AHCO 7.66, TME 9.05, SVV 10.46, SLN 19.83.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP WY (WEYERHAEUSER CO) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001197193-26-000008`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 20.81 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001197193-26-000008` by BECKWITT RICHARD (director); purchases USD 306,600; top executive no; holding up +46.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001197193-26-000008.
Twins (band+liq+mom+dd): DKS 149.7, WYNN 85.06, SPHR 125.56, KRMN 40.66, LVS 40.39, FLR 48.98, GS 916.56, WFRD 86.45, AN 177.75, TPG 48.26, FTAI 180.2, DB 36.62, ARGX 960.04, PRAX 328.13, MANE 129.66, RH 129.39, ENTG 147.41, POR 45.91, CHWY 22.52, UAL 109.31.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NGS (NATURAL GAS SERVICES GROUP INC) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001236849-26-000015`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 29.7 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001236849-26-000015` by JACKSON JOHN EARL (director); purchases USD 57,790; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001236849-26-000015.
Twins (band+liq+mom+dd): RDVT 73.57, SMC 30.69, BFS 28.37, PLOW 37.44, BLX 50.55, PMTS 24.93, AAUC 20.68, ITRN 48.23, MLKN 21.13, TBN 29.25, SNDA 33, NWPX 90.02, BBSI 30.77, PBT 31.03, MLR 48.3, TFPM 30.38, WHK 26, EIG 47.6, MOV 31.78, FET 76.87.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP FF (FutureFuel Corp.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-036877`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 2.9 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-036877` by Polet Roeland (Chief Executive Officer), Bedell Donald C. (director); purchases USD 249,266; top executive yes; holding up +400.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001437749-26-036877.
Twins (band+liq+mom+dd): ADTN 4.83, LWLG 3.21, DDD 1.53, KDK 1.11, DFDV 3.035, NRXP 2.19, SERV 2.62, TDUP 1.58, XGN 4.13, AIRJ 2.15, QTEX 1.25, XTND 1.39, TNXP 3.01, ACDC 3.15, TMC 2.31, NNBR 3.04, CRMD 4.66, GEMI 2.375, USAS 2.5, STTK 4.65.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP LPCN (Lipocine Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-051673`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 1.71 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-051673` by Patel Mahesh V. (Chief Executive Officer); purchases USD 79,488; top executive yes; holding up +31.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001493152-26-051673.
Twins (band+liq+mom+dd): PMVP 1.27, RGP 2.67, PRLD 3.45, WHWK 3.06, OMH 5, FHTX 2.07, CAST 1.06, ARMP 3.87, TRVG 4.15, CLRO 3.37, OKUR 2.63, PRQR 1.41, TRON 1.41, CYCU 2.29, BLND 1.07, XTIA 1.03, SEV 1.57, EQ 1.29, VIVO 2.23, NVA 3.32.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP NXGL (NEXGEL, INC.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-051920`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 3.88 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-051920` by Kieser Brian Joseph (Interim CEO); purchases USD 732,688; top executive yes; holding up n/a.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0001493152-26-051920.
Twins (band+liq+mom+dd): TORO 3.81, UPC 1.51, PAVM 1.63, EZGO 1.57, KTCC 1.3, SYPR 1.06, CSAI 1.42, PFAI 2.75, WXM 2.68, EDSA 1.94, SKYE 1.09, NSRX 2.87, INHD 2.65, HCTI 3.66, DUKR 2.02, NEUP 2.55, THH 1.2, SONM 2.17, KLRS 1.575, NXTS 2.21.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CRVS (Corvus Pharmaceuticals, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001610717-26-000454`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 10.64 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001610717-26-000454` by Arcara Jeffrey (Chief Business Officer); purchases USD 50,475; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001610717-26-000454.
Twins (band+liq+mom+dd): RXST 5.32, OPRT 11.73, LOVE 15.14, WBTN 9.85, KRRO 13.61, NMR 9.7, OIS 8.57, BUUU 5.32, CXM 6.8, FOSL 8.43, SHOE 14.36, SB 8.29, MSDL 13.84, TKNO 8.21, EPRX 8.15, OPFI 5.94, ELMT 19.83, INTT 13.73, ANGO 11.87, PLAY 8.02.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CTEV (Claritev Corp) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-073944`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 26.82 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-073944` by Dalton Travis (Pres., CEO & Executive Chair); purchases USD 149,927; top executive yes; holding up +9.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-073944.
Twins (band+liq+mom+dd): NBTX 30.655, DMRA 21.6, TYRA 20.025, GIBO 75.65, ASMB 21.12, MNPR 72, SPRB 43.31.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BW (Babcock & Wilcox Enterprises, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001630805-26-000089`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 4.56 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001630805-26-000089` by Tato Joseph A (director); purchases USD 52,692; top executive no; holding up +4.8%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001630805-26-000089.
Twins (band+liq+mom+dd): GT 4.12, LCID 2.955, NUAI 3.2, ORC 4.68, DCH 4.69.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP UPST (Upstart Holdings, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001832812-26-000012`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 19.56 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001832812-26-000012` by Gu Paul (Chief Executive Officer); purchases USD 1,028,400; top executive yes; holding up +38.5%.
Coverage **ABSTAIN** (ROUTINE); dilution filings 0; routine owners 1 of 1; parent CAT-FORM4-0001832812-26-000012.
Twins (band+liq+mom+dd): CDE 13.98, FSLY 16.62, RGTI 9.62, PBR 18.34, IBRX 6.02, CIFR 6.86, BMNR 17.58, QBTS 9.56, IOVA 7.76, FIG 19.45, IREN 18.17, XP 15.49, VALE 11.22, CTVA 9.43, HL 13.1, ONDS 5.16, INIO 14.57, CLSK 6.65, GLXY 14.38, UMC 15.4.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ABCL (AbCellera Biologics Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001834411-26-000010`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 11.49 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001834411-26-000010` by Booth Andrew (Chief Financial Officer); purchases USD 97,438; top executive yes; holding up +1.8%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001834411-26-000010.
Twins (band+liq+mom+dd): BBNX 16.42, GENI 6.26, HTGC 15.87, EFC 11.11, VIR 9.96, AMPX 7.93, VSTM 8.18, PZZA 19.92, CRSR 11.78, PGY 16.87, PTEN 10.97, FLG 10.48, NOV 18.09, IRT 14.96, SMMT 14.15, DEI 9.9, VIPS 13.26, BRSL 9.81, WSE 11.23, HAFN 9.59.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CTRI (Centuri Holdings, Inc.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0001981599-26-000139`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 21.82 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001981599-26-000139` by MARIUCCI ANNE L (director), Patton Charles R. (director); purchases USD 349,910; top executive no; holding up +37.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001981599-26-000139.
Twins (band+liq+mom+dd): SBRA 20.44, HTO 60.56, ULS 80.36, MGNI 29.29, EXPO 87.31, SAIL 20.79, EBC 22.88, THG 248.26, HIW 31.07, INGM 28.42, AKR 20.21, OUT 33.54, PEB 21.62, RYAAY 57.72, JBTM 125.54, CGON 74.4, BIPC 39.56, ALSN 126.69, TRNO 66.95, TNL 78.65.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP KEEL (Keel Infrastructure Corp.) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0002115914-26-000003`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 1.86 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002115914-26-000003` by Freedman Amy (director); purchases USD 76,100; top executive no; holding up +57.5%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002115914-26-000003.
Twins (band+liq+mom+dd): INTR 4.15, CYPH 1.87, SATL 3.3, NUVB 3.99, PONY 4.46, DNN 2.06, LZ 4.99, PGEN 4.54, ZURA 1.24, HTZ 1.5, ENVX 1.6, RCAT 3.8, MPT 1.67, PCT 1.705, ASM 4.29, LAC 1.49, UNIT 4.88, QS 3.68, FLNC 4.68, HIVE 1.57.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CRESY (CRESUD INC) - filed 2026-11-13, sealed 2026-11-16T12:19:49Z, cutoff 2026-11-16T14:15:00Z
Set `CAT-FORM4_SHARP-0002119764-26-000036`, scan `SCAN-US-2026-11-13-G2_RET30`; signal close 9.74 on 2026-11-13; entry: the entry session's opening print (2026-11-16). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002119764-26-000036` by Elsztain Alejandro Gustavo (director); purchases USD 89,000; top executive no; holding up +1.3%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002119764-26-000036.
Twins (band+liq+mom+dd): SD 13.04, MTRX 9.19, TTAM 11.25, PAYP 14.35, USNA 13.24, GPRK 9.42, TLX 9.23, MNRO 10.48, ILPT 6.07, PAX 9.17, MH 11.6, CEPU 10.86, GTE 9.47, ALLT 7.95, ZVRA 9.08, OBE 9.89, AGBK 6.26, VTS 15.42, RMR 16.75, MASS 9.74.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

