# LEARNER-v2.4: the one live challenger (KOD-LEARNER-v2.4, protocol sha256 8132768cb6c1)

Generated 2026-11-12T23:00:21Z. Paper only; no orders.

## The three plain answers

**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower at the next session, when most of its twins do not? (Companion: the same over its 5-session plan.)

**What counts as success?** Prospectively, on sealed sets: the forecasts rank the dumpers above the others (AUC above 0.5, z >= 3.75 at the first look of 250/500/1000 resolved pairs), with the Brier gain over the base rate and over the volatility-and-context benchmark reported beside it. The gate that unlocks published confidence needs 30 populated sessions of resolution.

**What evidence so far?** 131 forecasts sealed; 88 headline outcomes resolved; AUC 0.654 (benchmark 0.630); gate closed, alpha 0.00, 6 of 30 sessions. Claim: no planned evaluation frozen; descriptive metrics only.

## Latest sets (2026-11-12)

- ADXN (2026-11-12): dump tomorrow 0.19 (base 0.16, benchmark 0.18, published 0.16); no call [20-session move in the call's direction +0.17; the spike in units of that volatility +0.16; an 8-K (or 6-K) that day or the day before -0.16]
- AIMD (2026-11-12): dump tomorrow 0.22 (base 0.16, benchmark 0.18, published 0.16); no call [close within its 14-session high-low range (Stochastic %K) +0.28; close near the day's high, in the call's direction -0.13; an 8-K (or 6-K) that day or the day before +0.13]
- POAS (2026-11-12): dump tomorrow 0.32 (base 0.16, benchmark 0.22, published 0.16); no call [close within its 14-session high-low range (Stochastic %K) +0.19; opening gap (the move came at the open) +0.19; close near the day's high, in the call's direction -0.17]
- GP (2026-11-12): dump tomorrow 0.25 (base 0.16, benchmark 0.20, published 0.16); no call [the spike in units of that volatility +0.14; 20-session move in the call's direction -0.13; an 8-K (or 6-K) that day or the day before +0.13]
- PARA (2026-11-12): dump tomorrow 0.29 (base 0.16, benchmark 0.31, published 0.16); no call [close within its 14-session high-low range (Stochastic %K) +0.65; volatility before the spike +0.62; MACD histogram -0.58]
- ICMB (2026-11-12): dump tomorrow 0.16 (base 0.16, benchmark 0.18, published 0.16); no call [an 8-K (or 6-K) that day or the day before -0.16; the spike in units of that volatility +0.16; volatility before the spike -0.14]
- DBGI (2026-11-12): dump tomorrow 0.35 (base 0.16, benchmark 0.17, published 0.16); no call [close within its 14-session high-low range (Stochastic %K) +0.61; MACD histogram +0.45; 20-session move in the call's direction -0.30]
- PLCE (2026-11-12): dump tomorrow 0.28 (base 0.16, benchmark 0.21, published 0.16); no call [close within its 14-session high-low range (Stochastic %K) +0.36; close near the day's high, in the call's direction -0.27; 20-session move in the call's direction -0.22]
- BGIN (2026-11-12): dump tomorrow 0.16 (base 0.16, benchmark 0.16, published 0.16); no call [an 8-K (or 6-K) that day or the day before +0.13; volatility before the spike -0.11; the market's own move that day +0.11]
- XLAB (2026-11-12): dump tomorrow 0.28 (base 0.16, benchmark 0.21, published 0.16); no call [close within its 14-session high-low range (Stochastic %K) +0.22; MACD histogram -0.22; volatility before the spike +0.21]
- TGHL (2026-11-12): dump tomorrow 0.17 (base 0.16, benchmark 0.15, published 0.16); no call [an offering filing in the last 90 days +0.14; an 8-K (or 6-K) that day or the day before +0.13; the spike in units of that volatility -0.11]
- ADVB (2026-11-12): dump tomorrow 0.17 (base 0.16, benchmark 0.15, published 0.16); no call [20-session move in the call's direction -0.14; an 8-K (or 6-K) that day or the day before +0.13; the market's own move that day +0.11]
- RIME (2026-11-12): dump tomorrow 0.15 (base 0.16, benchmark 0.16, published 0.16); no call [an 8-K (or 6-K) that day or the day before -0.16; the market's own move that day +0.11; volume against its 20-session median +0.10]
- TGEN (2026-11-12): dump tomorrow 0.14 (base 0.16, benchmark 0.15, published 0.16); no call [an 8-K (or 6-K) that day or the day before -0.16; an offering filing in the last 90 days +0.14; the spike in units of that volatility -0.11]
- ARAI (2026-11-12): dump tomorrow 0.33 (base 0.16, benchmark 0.39, published 0.16); no call [the spike in units of that volatility +0.83; volume against its 20-session median -0.37; 20-session move in the call's direction +0.21]

## Appendix

| Statement | Resolved | Rate | AUC | AUC benchmark | Brier gain vs base (se) | benchmark vs base | learner vs benchmark | Calls shadow right/n | live right/n |
|---|---:|---:|---:|---:|---|---|---|---|---|
| NEXT_DUMP10_1 | 88 | 0.239 | 0.654 | 0.630 | +0.0111 (0.0132; 6 blocks) | +0.0010 (0.0160; 6 blocks) | +0.0101 (0.0105; 6 blocks) | 7/9 | 0/0 |
| DUMP10_5 | 20 | 0.300 | 0.643 | 0.583 | -0.0208 (n/a; 1 blocks) | +0.0030 (n/a; 1 blocks) | -0.0238 (n/a; 1 blocks) | 0/0 | 0/0 |

Gates (confidence): **PATH/1** alpha 0.00, 6 observations, closed; **PATH/5** alpha 0.00, 1 observations, closed.

v2.2 against v2.3 on DUMP10_5, the same 20 sets: paired Brier gain of v2.3 -0.0011 (se 0.0238); AUC v2.2 0.5 vs v2.3 0.6428571428571429.

Due sets without a forecast: 32 (SPEC-SCAN-US-2026-11-02-G2_RET30-SEGG, SPEC-SCAN-US-2026-11-02-G2_RET30-INLF, SPEC-SCAN-US-2026-11-02-G2_RET30-CLRO, SPEC-SCAN-US-2026-11-02-G2_RET30-HXHX, SPEC-SCAN-US-2026-11-02-G2_RET30-INO, SPEC-SCAN-US-2026-11-02-G2_RET30-IFBD, SPEC-SCAN-US-2026-11-02-G2_RET30-GNTA, SPEC-SCAN-US-2026-11-02-G2_RET30-PERI, SPEC-SCAN-US-2026-11-02-G2_RET30-EVGO, SPEC-SCAN-US-2026-11-02-G2_RET30-NMRA).

