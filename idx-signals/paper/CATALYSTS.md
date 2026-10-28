# Catalyst Register

Protocol `KOD-CATALYST-REGISTER-v1` (sha256 `fd027bbdd1a5`), `research/CATALYST_REGISTER_v1/PROTOCOL.md`. Paper only; derived from `paper/catalysts.jsonl` (generated 2026-10-28T23:03:49Z). Nothing here is a result until a look is reached.

## SEC13D (counted at each look)

Sets 2 (FIRE 1, ABSTAIN 1) over 1 signal sessions; events seen: SKIP_NOT_IN_UNIVERSE 1, SEALED 2; coverage gaps 0.

| Class | Paired | Sessions | Mean net | Mean diff vs twins | t | p (one-sided) |
|---|---|---|---|---|---|---|
| FIRE | 0 | 0 | n/a | n/a | n/a | n/a |
| ABSTAIN | 0 | 0 | n/a | n/a | n/a | n/a |

Primaries (`research/CATALYST_REGISTER_v1/prereg_2.json`), looks at [60, 120, 240, 480, 960, 1920] FIRE pairs, t at least [3.75, 3.0, 3.0, 3.0, 3.0, 3.0]:
- MEAN (plan net minus twins' mean): **accumulating (no look reached)**
- WIN_RATE (plan beats twins' median): 0 of 0 (n/a), t n/a: **accumulating (no look reached)**

## IDX_INDEX (descriptive)

Sets 14 over 1 sessions.

- RUNUP: paired 0, mean signed diff n/a, share with the flow n/a
- POST20: paired 0, mean signed diff n/a, share with the flow n/a

## DILUTION_8K (counted at each look; direction -1; `KOD-CATALYST-FAMILY-DILUTION_8K-v1`)

Sets 0 over 0 signal sessions; events seen: none; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## FORM4 (counted at each look; direction +1; `KOD-CATALYST-FAMILY-FORM4-v1`)

Sets 0 over 0 signal sessions; events seen: none; coverage gaps 0.
- MEAN (signed edge over the twins) n/a over 0 pairs: **accumulating (no look reached)**
- WIN_RATE 0 of 0 (n/a): **accumulating (no look reached)**

## Calibration

| Family | Statement | n | Realised | Mean prior | Twins | Brier | Brier at 0.5 |
|---|---|---|---|---|---|---|---|
| SEC13D | GAIN0_20 | 0 | | | | | |
| SEC13D | BEATS_TWINS_20 | 0 | | | | | |
| SEC13D | FADE10_20 | 0 | | | | | |
| SEC13D | RUN30_20 | 0 | | | | | |
| IDX_INDEX | WITH_FLOW_RUNUP | 0 | | | | | |
| IDX_INDEX | REVERSAL_POST20 | 0 | | | | | |
| DILUTION_8K | LOSES_TO_TWINS_20 | 0 | | | | | |
| DILUTION_8K | GAIN0_20 | 0 | | | | | |
| DILUTION_8K | FADE10_20 | 0 | | | | | |
| DILUTION_8K | RUN30_20 | 0 | | | | | |
| FORM4 | BEATS_TWINS_20 | 0 | | | | | |
| FORM4 | GAIN0_20 | 0 | | | | | |
| FORM4 | FADE10_20 | 0 | | | | | |
| FORM4 | RUN30_20 | 0 | | | | | |

## DILUTION_RECENT tags on Speculation Register sets

15 tags: 2 true, 0 unknown.

## Latest sets

### IDX_INDEX CUAN (DELETE LQ45, DELETE IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `35d548e06a46`, scan `SCAN-2026-10-28-F1_ARA`; signal close 432 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): IRSX 226, NICL 232, ARTO 565, EXCL 1690, JARR 2230.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX ELSA (ADD LQ45) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `442aaefcb526`, scan `SCAN-2026-10-28-F1_ARA`; signal close 655 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): ULTJ 2120, ACES 330, GULA 750, AYAM 492, CLEO 390.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX HEAL (DELETE IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `bcf70b85ea8b`, scan `SCAN-2026-10-28-F1_ARA`; signal close 545 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom): UNSP 276, MSTI 1210, MOLI 364, AVIA 302, MITI 256.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX ISAT (ADD IDX30) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `0e6e539a9300`, scan `SCAN-2026-10-28-F1_ARA`; signal close 1570 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): EXCL 1690, EMTK 324, SSIA 1225, ARCI 990, TEBE 1750.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX MIKA (DELETE IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `034c9b860b8b`, scan `SCAN-2026-10-28-F1_ARA`; signal close 1380 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): FORE 590, ASPI 810, DGWG 268, HBAT 286, NRCA 434.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX PGEO (DELETE IDX30) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `adb72d0f2148`, scan `SCAN-2026-10-28-F1_ARA`; signal close 990 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): CMNT 725, CMRY 4150, CTRA 580, HMSP 660, DMAS 210.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX PTBA (ADD IDX30) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `9d45813eb6de`, scan `SCAN-2026-10-28-F1_ARA`; signal close 3250 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): MEDC 1405, CMNT 725, CMRY 4150, AKRA 1405, GULA 750.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX SCMA (DELETE LQ45) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `79e7f38692f6`, scan `SCAN-2026-10-28-F1_ARA`; signal close 139 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): MDIA 78, KOTA 84, LUCY 114, MNCN 84, KIJA 119.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX SMGR (ADD LQ45) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `6c6ec54d5e41`, scan `SCAN-2026-10-28-F1_ARA`; signal close 1440 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom): DEWI 232, PRDA 3720, AUTO 3350, DMAS 210, CTRA 580.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX SMRA (DELETE IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `3498b443e72a`, scan `SCAN-2026-10-28-F1_ARA`; signal close 252 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom): PRDA 3720, ACES 330, DMAS 210, TOWR 392, SMDR 388.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX TINS (ADD IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `a66aa2a43d39`, scan `SCAN-2026-10-28-F1_ARA`; signal close 3820 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom): AMRT 1020, RATU 2230, EMTK 324, BUVA 360, HRTA 1595.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX TKIM (ADD IDX80) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `37e8f93a0f4f`, scan `SCAN-2026-10-28-F1_ARA`; signal close 6525 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence SINGLE_SOURCE; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq): PKPK 7250, AADI 11650, UNTR 25600, ICBP 5775, INKP 6750.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### IDX_INDEX UNVR (DELETE IDX30) - effective 2026-11-02, sealed 2026-10-28T10:38:02Z, cutoff 2026-10-29T01:45:00Z
Set `3c048a49f734`, scan `SCAN-2026-10-28-F1_ARA`; signal close 1405 on 2026-10-28; entry: the closing auction of the session after the signal session (2026-10-29). Windows: POST20: entry +2, hold 20; RUNUP: entry +1, hold 1.
Confidence CONFIRMED; events file sha256 `39df501b3e5a`.
Coverage DESCRIPTIVE (not counted).
Twins (band+liq+mom+dd): ANTM 2800, SSMS 940, AMMN 3900, ESSA 525, HRUM 725.
Cone: WITH_FLOW_RUNUP p=0.50; REVERSAL_POST20 p=0.50.

### SEC13D BKU (BankUnited, Inc.) - accepted 2026-10-28T16:24:02-04:00, sealed 2026-10-28T23:03:12Z, cutoff 2026-10-29T13:15:00Z
Set `dd2d6840461e`, scan `SCAN-US-2026-10-28-G2_RET30`; signal close 42.81 on 2026-10-28; entry: the entry session's opening print (2026-10-29). Windows: H20: entry +1, hold 20.
Filing `0000921895-26-002864` by HoldCo Asset Management, LP; Item 4 intent words: board, director.
Coverage **FIRE**; pre-entry move +0.00%, market value USD 3,049.5M, dilution filings 0.
Twins (band+liq+mom+dd): STRA 77.55, NHC 211.79, BCC 74.56, SLG 48.99, PHIN 57.68.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

### SEC13D SWBI (SMITH & WESSON BRANDS, INC.) - accepted 2026-10-28T17:53:47-04:00, sealed 2026-10-28T23:03:12Z, cutoff 2026-10-29T13:15:00Z
Set `e13fc212025b`, scan `SCAN-US-2026-10-28-G2_RET30`; signal close 13.89 on 2026-10-28; entry: the entry session's opening print (2026-10-29). Windows: H20: entry +1, hold 20.
Filing `0001493152-26-049116` by JDH Capital I, L.P.; Item 4 intent words: board, merger, acquisition, director.
Coverage **ABSTAIN** (DILUTION_RECENT); pre-entry move +0.00%, market value USD 622.8M, dilution filings 1.
Twins (band+liq+mom+dd): GLSI 18.31, USNA 14.62, FDUS 19.09, TIPT 17.21, AERO 15.21.
Cone: GAIN0_20 p=0.55; BEATS_TWINS_20 p=0.50; FADE10_20 p=0.50; RUN30_20 p=0.50.

