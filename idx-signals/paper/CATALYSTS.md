# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-11-23T23:06:52Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 39 (FIRE 17, ABSTAIN 22) over 14 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 20, SEALED 39, SKIP_NOT_OPERATING 9, SKIP_LATE 2, SKIP_NO_TICKER 6, SKIP_REPEAT_90D 2; coverage gaps 1.

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

Sets 73 over 14 signal sessions; events seen: SEALED 73, SKIP_REPEAT_90D 59, SKIP_NO_TICKER 44, SKIP_NOT_IN_UNIVERSE 45, SKIP_NOT_OPERATING 1; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 257 over 12 signal sessions; events seen: SEALED 257, SKIP_NOT_IN_UNIVERSE 8, SKIP_NOT_PURCHASE 8976, SKIP_LATE 41, SKIP_NO_TICKER 5, SKIP_NOT_OPERATING 9, SKIP_REPEAT_90D 93; coverage gaps 1.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4_SHARP (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4_SHARP-v1`)

Sets 257 over 12 signal sessions; events seen: SEALED 257; coverage gaps 0.
Decision sample: FIRE sets, window H60, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 111, FIRE 146
- Descriptive H20_FIRE: n/a over 0 pairs
- Descriptive H20_ABSTAIN: n/a over 0 pairs
- Descriptive H60_ABSTAIN: n/a over 0 pairs

## SEC13D_V2 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-SEC13D_V2-v1`)

Sets 37 over 13 signal sessions; events seen: SEALED 37; coverage gaps 0.
Decision sample: FIRE sets, window H20, 0 distinct entry week(s).
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**
- Classes: ABSTAIN 18, FIRE 19
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

292 tags: 68 true, 0 unknown.

## Latest sets

### FORM4_SHARP SAGT (SAGTEC GLOBAL Ltd) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-122442`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 1.11 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-122442` by Ng Chen Lok (Chief Executive Officer); purchases USD 267,800; top executive yes; holding up +3.0%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001213900-26-122442.
Twins (band+liq+mom+dd): CLAR 4.75, TUSK 2.94, POWW 2.58, MYPS 4.94, SJT 4.37, COSM 2.81, SMRT 1.47, RYDE 1.07, GCL 1.47, ENTX 3.305, SND 4.65, FLNT 3.725, SPWH 1.22, USEA 2.82, TPET 1.75, CVGI 3.06, PSHG 1.83, ARQ 2.82, RERE 3.92, JVA 4.93.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP PICS (PicS N.V.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-122444`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 5.02 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-122444` by Teixeira Linares Marcio Antonio (director), Pruett William Rodney (director); purchases USD 531,900; top executive no; holding up +40.0%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 2; parent CAT-FORM4-0001213900-26-122444.
Twins (band+liq+mom+dd): ADIG 8.96, HNRG 8.94, GLUE 8.64, CMCL 16.26, MTA 5.84, SWMR 6.95, RMIX 5.85, MPLT 5.94, CIM 6.36, IDR 13.85, CLB 7.76, SCTX 12.07, ORIC 7.36, ARCT 7.45, METC 5.41, HMH 10.98, LAND 6.2, NPKI 8.14, ENTA 7.62, SECZ 6.09.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP MED (MEDIFAST INC) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-122629`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 11.75 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-122629` by Kiai Parsa (director); purchases USD 1,133,816; top executive no; holding up n/a.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001213900-26-122629.
Twins (band+liq+mom+dd): KROS 11.08, XTER 9.8, CARL 17.42, GLRE 16.3, RDAG 10.505, FNRN 16.92, LSBK 18.36, LAW 5.89, DMII 10.23, JRSH 7.01, PACH 10.42, LFCR 6.39, PSBD 9.5, LTGR 10.07, BCSS 10.26, BPAC 10.3, BRTM 9.8, CEPS 10.11, PXLW 6.705, CPAC 13.04.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ALTO (Alto Ingredients, Inc.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001213900-26-122704`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 2.98 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001213900-26-122704` by NATHAN GILBERT E (director); purchases USD 81,362; top executive no; holding up +2.9%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001213900-26-122704.
Twins (band+liq+mom+dd): AMBP 4.32, TSHA 3.72, VGZ 2.27, MOMO 4.075, GDRX 2.92, TV 2.11, EGHT 1.96, CRON 3.04, IMRX 3.38, HLLY 2.29, TOYO 3.7, ICL 4.08, TKC 4.42, ARKO 3.21, BUR 3.24, HNST 4.44, ASTL 4.31, ABUS 4.02, LPL 2.33, IVA 3.14.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP GBCI (GLACIER BANCORP, INC.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001347688-26-000006`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 45.49 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001347688-26-000006` by Langel Craig A (director); purchases USD 53,452; top executive no; holding up +1.2%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001347688-26-000006.
Twins (band+liq+mom+dd): DSGX 89.205, SFNC 21.56, WSBC 36.37, KWR 147.48, TS 55.17, HIW 29.55, FELE 95.44, HOMB 28.35, SSB 99.18, HMC 32.58, UGI 35.51, TRMK 43.58, FOX 56.14, LTC 42.24, UCB 35.23, JOYY 73.87, PAGP 25.53, MMSI 84.34, TXCP 95.28, BKE 44.15.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP HBCP (HOME BANCORP, INC.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001436425-26-000078`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 60.54 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001436425-26-000078` by Hill Darren M (Chief Risk Officer); purchases USD 315,013; top executive no; holding up +255.2%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001436425-26-000078.
Twins (band+liq+mom+dd): TNC 73.99, OSBC 24.17, GIII 30.55, CAE 26.71, APOG 43.43, SI 20.15, GTY 28.36, DSGR 35, MPB 33.93, ONT 21.69, LCLN 26.55, OBK 51.65, CBLL 27.39, NRP 114.45, BWFG 67.71, JAKK 33.44, HBT 35.26, RRBI 101.66, CBNK 40.4, WCCB 60.94.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BOTJ (BANK OF THE JAMES FINANCIAL GROUP INC) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001437749-26-037847`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 24.67 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001437749-26-037847` by FOSTER WATT R JR (director); purchases USD 50,300; top executive no; holding up +1.6%.
Coverage **ABSTAIN** (NOT_SHARP); dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001437749-26-037847.
Twins (band+liq+mom+dd): SBR 60.83, DCBO 27.82, KEN 54.16, DJP 45.97, TWIN 21.21, AIRT 21.43, OLP 20.64, NKSH 36.86, OFLX 21.15, HNVR 21.37, SMID 20.68, TAYD 53.16, INBK 24.28, HBB 28.91, PPIH 25.5, NC 30.2, MNSB 20.13, ELMD 22.98.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP CLIK (Click Holdings Ltd.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001493152-26-053366`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 0.6702 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001493152-26-053366` by Chan Chun Sing (Chief Executive Officer); purchases USD 63,856; top executive yes; holding up +1.9%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001493152-26-053366.
Twins (band+liq+mom+dd): HCWB 0.7491, BRLS 0.7, LIQT 0.1929, DTSS 0.361, CNEY 0.365, VS 0.5705, IVDA 0.17, MGX 0.565, GMEX 0.192, GFAI 0.0841, TPST 0.287, LCFY 0.7015, GXAI 0.3613, OLB 0.115, XTNT 0.21, ZTG 0.2605, SLGB 0.1402, HPAI 0.2201, TURB 0.6446, FRSX 0.44.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP SEI (Solaris Energy Infrastructure, Inc.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075232`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 54.67 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075232` by Zartler William A (Chairman and Co-CEO), Brock Amanda M (Co-Chief Executive Officer), Ramachandran Kyle S. (President); purchases USD 641,090; top executive yes; holding up +1.9%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 3; parent CAT-FORM4-0001628280-26-075232.
Twins (band+liq+mom+dd): XYL 94.66, OXY 53.9, ESI 29.52, PCVX 55.39, HSBC 80.02, ADBE 217.71, BWXT 108.54, SYF 67.76, XYZ 69.66, CVLT 145.9, IBKR 71.19, VST 115.25, MLI 49.85, Q 103.47, SCI 69.14, JBHT 218.54, DHT 21.58, DVA 161.03, PR 21.15, CTSH 58.06.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TMS (Teamshares Inc) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001628280-26-075322`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 3.91 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001628280-26-075322` by Eu Alexander Zai De (President); purchases USD 109,530; top executive yes; holding up +8.4%.
Coverage **ABSTAIN** (DILUTION_RECENT); dilution filings 2; routine owners 0 of 1; parent CAT-FORM4-0001628280-26-075322.
Twins (band+liq+mom+dd): MWYN 1.19, SBMT 4.55, SMX 2.7, TENX 1.25, SEAT 1.56, RCT 1.49, COYA 2.95, STI 2.89, DFNS 1.21, CNTN 1.21, PRQR 1.04, BBDO 2.09, METCB 2.77, MDAI 1.04, GRDX 3.16, VATE 3.55, BBOT 1.81, UPLD 1.5, SHMD 1.57, WKHS 1.75.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TJX (TJX COMPANIES INC /DE/) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001664921-26-000002`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 139.62 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001664921-26-000002` by PINTOFF CRAIG ADAM (director); purchases USD 199,823; top executive no; holding up n/a.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001664921-26-000002.
Twins (band+liq+mom+dd): MAA 112.91, MNST 43.69, OKE 84.37, TD 112.87, RY 183.45, PLD 122.5, EWBC 121.54, TDY 598.56, PNFP 92.56, PAYC 241.64, RL 366.65, BMO 156.29, NUE 239.62, TFC 45.81, IEX 219.64, LMT 565.5, UHS 179.43, FCNCA 2075.52, LOGI 97.21, SRE 76.16.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP VANI (Vivani Medical, Inc.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001753926-26-002210`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 1.14 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001753926-26-002210` by Williams Gregg (director); purchases USD 128,325; top executive no; holding up +0.3%.
Coverage **ABSTAIN** (DILUTION_RECENT, ROUTINE); dilution filings 1; routine owners 1 of 1; parent CAT-FORM4-0001753926-26-002210.
Twins (band+liq+mom+dd): CCLD 2.02, FLX 1.48, ENGN 1.74, GECC 4.88, ONL 2.23, ABLV 2.16, APYX 2.4, CAMP 3.79, TZOO 4.96, FPH 4.35, GNLX 2.17, CHOW 3.36, CURV 2.14, LZM 3.88, KRMD 3.19, LUNG 2.57, TMCI 4.31, FBIO 1.9, ASLE 4.93, CMTG 1.41.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP BHRB (Burke & Herbert Financial Services Corp.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0001945031-26-000015`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 67.81 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0001945031-26-000015` by Poillon Diane (director); purchases USD 106,131; top executive no; holding up +36.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0001945031-26-000015.
Twins (band+liq+mom+dd): NBBK 21.06, SPFI 40.54, HAFC 30.47, FISI 38.24, IDT 73.72, FCBC 44.55, AMAL 46.84, FBNC 60.74, KARO 59.45, UVSP 38.41, CNOB 30.3, CARE 28.41, UFCS 49.78, VLGEA 40.61, JMSB 22.22, BSVN 55.94, BHB 39.06, CZFS 80.7, BBSI 30.5, AROW 36.57.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP TSM (TAIWAN SEMICONDUCTOR MANUFACTURING CO LTD) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0002114032-26-000002`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 318.71 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002114032-26-000002` by Lu Lee-Chung (VP); purchases USD 302,850; top executive no; holding up +33.3%.
Coverage **FIRE**; dilution filings 0; routine owners 0 of 1; parent CAT-FORM4-0002114032-26-000002.
Twins (band+liq+mom+dd): MCHP 55.44, TPL 267.44, SU 63.82, GFS 35.56, UNF 228.42, IRTC 94.72, KBR 31.44, INTU 270.44, IT 174.49, PLTR 143.49, BKR 44.81, FSLR 137.59, EXPE 234.96, NTAP 157.65, OSCR 24.73, MELI 1355, BROS 32.78, ZS 194.82, ASML 1266.22, NWSA 25.05.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

### FORM4_SHARP ESEA (EUROSEAS LTD.) - filed 2026-11-20, sealed 2026-11-23T10:35:17Z, cutoff 2026-11-23T14:15:00Z
Set `CAT-FORM4_SHARP-0002127484-26-000025`, scan `SCAN-US-2026-11-20-G2_RET30`; signal close 58.59 on 2026-11-20; entry: the entry session's opening print (2026-11-23). Windows: H20: entry +1, hold 20; H60: entry +1, hold 60; M20: 20 sessions.
Form 4 `0002127484-26-000025` by Pittas Aristeidis P (director); purchases USD 58,976; top executive no; holding up +1.6%.
Coverage **ABSTAIN** (NOT_SHARP, DILUTION_RECENT); dilution filings 1; routine owners 0 of 1; parent CAT-FORM4-0002127484-26-000025.
Twins (band+liq+mom+dd): OFLX 21.15, AIRT 21.43, OLP 20.64, TWIN 21.21, TAYD 53.16, HNVR 21.37, NKSH 36.86, INBK 24.28, PPIH 25.5, ELMD 22.98, KEN 54.16, DJP 45.97, NC 30.2, MNSB 20.13, HBB 28.91, SMID 20.68, DCBO 27.82, SBR 60.83.
Cone: BEATS_TWINS_60 p=0.50; GAIN0_60 p=0.50; BEATS_TWINS_20 p=0.50; GAIN0_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50; MECH_SECOND_BUY_20 p=0.50.

