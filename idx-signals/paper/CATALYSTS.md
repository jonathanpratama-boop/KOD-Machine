# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-10-30T23:02:42Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 5 (FIRE 2, ABSTAIN 3) over 3 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 3, SEALED 5, SKIP_NOT_OPERATING 2; coverage gaps 0.

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

Sets 7 over 3 signal sessions; events seen: SEALED 7, SKIP_REPEAT_90D 7, SKIP_NO_TICKER 5, SKIP_NOT_IN_UNIVERSE 7; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 9 over 1 signal sessions; events seen: SEALED 9, SKIP_NOT_IN_UNIVERSE 1, SKIP_NOT_PURCHASE 252; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 9 over 1 signal sessions; events seen: SEALED 9; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 5, FIRE 4
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 3 over 2 signal sessions; events seen: SEALED 3; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 2, FIRE 1
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

30 tags: 6 true, 0 unknown.

## Latest sets

### FORM4 BBT (Beacon Financial Corp) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001628280-26-068056`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 30.66 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001628280-26-068056` (1 filing(s)) by Callahan Mary Anne (director).
Coverage **FIRE**; purchases USD 96,672, owners 1, top executive no, lag 1 days.
Twins (band+liq+mom+dd): EPAC 39.42, ENR 23.15, WKC 37.21, MGY 26.22, DIN 35.16.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4 UTMD (UTAH MEDICAL PRODUCTS INC) - filed 2026-10-29, sealed 2026-10-30T11:01:26Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4-0001733614-26-000005`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 66.8 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20.
Form 4 `0001733614-26-000005` (1 filing(s)) by CORNWELL KEVIN L (Chairman, CEO).
Coverage **FIRE**; purchases USD 66,750, owners 1, top executive yes, lag 0 days.
Twins (band+liq+mom+dd): PKX 50.91, GLIBK 21.61, CMCL 21.4, XRN 30.52, ATNI 25.88.
Cone: BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### FORM4_SHARP BFC (Bank First Corp) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001104659-26-120006`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 150.62 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001104659-26-120006` by Sprang Todd A. (director); purchases USD 59,348; top executive no; holding up +19.7%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001104659-26-120006.
Twins (band+liq+mom+dd): BKTI 72.3, FISI 40.88, AMTB 29.9, EQBK 49.11, SMBK 49.07, RBB 26.04, GABC 49.41, TRST 56.87, AROW 38.665, KRT 54.39, RRBI 102.1, INVA 21.31, KE 27.01, SMP 38.25, HG 34.43, EBF 21.76, LQDT 45.29, FMBH 51.13, BBSI 32.36, TRNS 90.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP DINO (HF Sinclair Corp) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001193125-26-438100`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 111.89 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001193125-26-438100` by MYERS FRANKLIN (CEO); purchases USD 1,108,000; top executive yes; holding up +5.1%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001193125-26-438100.
Twins (band+liq+mom+dd): SPCX 143.89, CBRE 128.58, SNA 358.6, DAVE 334.8, FNV 231.6, VST 140.95, WWD 314.92, GNRC 203.36, PH 928.45, NRG 97.54, GRMN 279.94, LVS 37.04, MAA 118.26, GME 24, FCX 66.14, CMCSA 22.27, GWRE 160.07, TT 431.1, RGLD 236.83, DASH 179.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP LRN (Stride, Inc.) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-113987`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 80.7 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-113987` by Haggart Dylan G. (director), Fivespan Partners, LP (officer), Fivespan Partners GP, LLC (officer); purchases USD 62,188; top executive no; holding up +0.0%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 3; parent CAT-FORM4-0001213900-26-113987.
Twins (band+liq+mom+dd): TRMD 43.045, OPLN 38.76, CNM 44.14, FSV 144.5, MORN 222.54, CON 41.25, ERIE 250.79, SMA 35.76, MAC 24.31, QTWO 65.28, AZTA 41.27, GIB 79.59, FIBK 37.95, ECPG 102.36, TAK 20.01, PRCH 20.89, L 111.69, NIC 172.52, FIGS 21.56, TILE 36.87.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PNFP (Pinnacle Financial Partners, Inc.) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001219004-26-000004`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 101.71 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001219004-26-000004` by INGRAM DAVID B (director); purchases USD 991,600; top executive no; holding up +15.3%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001219004-26-000004.
Twins (band+liq+mom+dd): PAG 212.34, EVRG 85.41, BDX 198.34, EXPD 198.39, PFE 29.95, CNP 42.21, EW 94.44, STLD 253.53, SOLS 62.56, TSCO 33.65, AEO 20.12, REGN 818.77, NDAQ 105.6, WSM 259.86, GDDY 105.89, ZTS 78.8, EQNR 47.58, SYNA 117.91, SIRI 28.67, GTLB 56.65.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP HBAN (HUNTINGTON BANCSHARES INC /MD/) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001225208-26-008552`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 15.97 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001225208-26-008552` by TORGOW GARY (director); purchases USD 199,834; top executive no; holding up +1.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001225208-26-008552.
Twins (band+liq+mom+dd): OWL 10.41, CPNG 14.57, CAG 14.09, ACI 12.79, JBS 12.16, WY 19.75.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP XYL (Xylem Inc.) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001524472-26-000150`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 90.76 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001524472-26-000150` by KOCH D CHRISTIAN (director); purchases USD 985,600; top executive no; holding up +882.1%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001524472-26-000150.
Twins (band+liq+mom+dd): MTZ 177.82, AMKR 41.21, CORT 85.95, AAOI 79.19, INTC 92.07, UCTT 54.7, LPLA 279.54, STRL 373.66, FIX 1326.23, APP 254.91, CAT 647.39, DOCN 99.97, VICR 206.62, STX 700.47, ONTO 221.89, VIAV 33.32, MP 41.64, RDDT 129.6, ALGM 33.03, AGI 28.83.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TFC (TRUIST FINANCIAL CORP) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001534574-26-000018`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 49.32 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001534574-26-000018` by Lyons Michael P. (President & CEO); purchases USD 1,209,050; top executive yes; holding up +119.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001534574-26-000018.
Twins (band+liq+mom+dd): AOS 63.49, CTAS 218.07, ABBV 290.79, RPRX 65.93, LH 368.16, GRAL 158.92, GH 185.31, ES 67.9, CCK 118.2, XEL 79.04, SPGI 460.66, SNY 43.13, PTC 194.8, WTFC 154.13, REGN 818.77, QLYS 230.29, SRE 85.89, CINF 181.87, MNST 46.35, BIO 384.4.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BBT (Beacon Financial Corp) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-068056`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 30.66 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-068056` by Callahan Mary Anne (director); purchases USD 96,672; top executive no; holding up +18.4%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-068056.
Twins (band+liq+mom+dd): EPAC 39.42, ENR 23.15, WKC 37.21, MGY 26.22, DIN 35.16, ENSG 186.32, WAY 28.21, MMSI 93.39, SMG 61.87, TILE 36.87, AWR 85.35, BSY 39.655, KBR 38.32, GFF 102.92, WGO 30.23, XHR 20.72, ABM 53.93, CACC 575.78, PAGP 28.82, SMA 35.76.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP UTMD (UTAH MEDICAL PRODUCTS INC) - filed 2026-10-29, sealed 2026-10-30T11:02:40Z, cutoff 2026-10-30T13:15:00Z
Set `CAT-FORM4_SHARP-0001733614-26-000005`, scan `SCAN-US-2026-10-29-G2_RET30`; signal close 66.8 on 2026-10-29; entry: the entry session's opening print (2026-10-30). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001733614-26-000005` by CORNWELL KEVIN L (Chairman, CEO); purchases USD 66,750; top executive yes; holding up +0.5%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001733614-26-000005.
Twins (band+liq+mom+dd): PKX 50.91, GLIBK 21.61, CMCL 21.4, XRN 30.52, ATNI 25.88, IFS 49.35, CWCO 26.76, REX 38.86, CVLG 28.82, CVEO 30.55, PS 49.15, KOP 41.86, HBB 32.51, FLXS 75.57, SII 106.65, MPTI 69.02, WF 67.67, ODC 73.26, NVGS 21.71, HBCP 61.37.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### SEC13D LEE (LEE ENTERPRISES, Inc) - accepted 2026-10-30T12:28:03-04:00, sealed 2026-10-30T23:02:22Z, cutoff 2026-11-02T14:15:00Z
Set `CAT-SEC13D-0002011620-26-000006`, scan `SCAN-US-2026-10-30-G2_RET30`; signal close 6.12 on 2026-10-30; entry: the entry session's opening print (2026-11-02). Windows: H20: entry +1, hold 20.
Filing `0002011620-26-000006` by Quint Digital Ltd; Item 4 intent words: board, acquisition, director.
Coverage **FIRE**; pre-entry move -1.61%, market value USD 136.4M, dilution filings 0.
Twins (band+liq+mom+dd): AIFU 9.8, LIVE 7.3001, NYC 5.96, FGI 7.91, NXTT 5.3.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D_V2 LEE (LEE ENTERPRISES, Inc) - accepted 2026-10-30T12:28:03-04:00, sealed 2026-10-30T23:02:29Z, cutoff 2026-11-02T14:15:00Z
Set `CAT-SEC13D_V2-0002011620-26-000006`, scan `SCAN-US-2026-10-30-G2_RET30`; signal close 6.12 on 2026-10-30; entry: the entry session's opening print (2026-11-02). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M60: 60 calendar days.
Filing `0002011620-26-000006` by Quint Digital Ltd; cover page max 14.4% of class; strong intent: none; Item 5(c): no transactions.
Coverage **FIRE**; market value USD 136.4M from XBRL; parent CAT-SEC13D-0002011620-26-000006.
Twins (band+liq+mom+dd): AIFU 9.8, LIVE 7.3001, NYC 5.96, FGI 7.91, NXTT 5.3, VHC 9.48, VMAR 6.26.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_60 p=0.50; MECH_13DA_UP_60 p=0.50.

### DILUTION_8K PTHS - event `0001104659-26-120457`, accepted 2026-10-30T09:17:39-04:00, sealed 2026-10-30T23:02:40Z, cutoff 2026-11-02T14:15:00Z
Set `CAT-DILUTION_8K-0001104659-26-120457`, scan `SCAN-US-2026-10-30-G2_RET30`; signal close 9.4 on 2026-10-30; entry: the entry session's opening print (2026-11-02). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move -43.17%.
Twins (band+liq+mom+dd): OCC 11.53, AIRO 5.16, ESOA 9.4, CNL 10.5, MF 8.35.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### DILUTION_8K RAPP - event `0001193125-26-441851`, accepted 2026-10-30T17:12:36-04:00, sealed 2026-10-30T23:02:40Z, cutoff 2026-11-02T14:15:00Z
Set `CAT-DILUTION_8K-0001193125-26-441851`, scan `SCAN-US-2026-10-30-G2_RET30`; signal close 25.05 on 2026-10-30; entry: the entry session's opening print (2026-11-02). Windows: H20: entry +1, hold 20.
Direction -1; protocol `KOD-CATALYST-FAMILY-DILUTION_8K-v1`.
Coverage **FIRE**; pre-entry move +0.00%.
Twins (band+liq+mom+dd): TSAT 40.09, JBSS 53.9, ASMB 20.13, CYD 22.45, OPY 86.2.
Cone: LOSES_TO_TWINS_20 p=0.55; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

