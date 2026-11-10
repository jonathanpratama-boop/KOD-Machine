# LEARNER-v2.4: the one live challenger (KOD-LEARNER-v2.4, protocol sha256 8132768cb6c1)

Generated 2026-11-10T23:00:33Z. Paper only; no orders.

## The three plain answers

**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower at the next session, when most of its twins do not? (Companion: the same over its 5-session plan.)

**What counts as success?** Prospectively, on sealed sets: the forecasts rank the dumpers above the others (AUC above 0.5, z >= 3.75 at the first look of 250/500/1000 resolved pairs), with the Brier gain over the base rate and over the volatility-and-context benchmark reported beside it. The gate that unlocks published confidence needs 30 populated sessions of resolution.

**What evidence so far?** 97 forecasts sealed; 53 headline outcomes resolved; AUC 0.709 (benchmark 0.705); gate closed, alpha 0.00, 4 of 30 sessions. Claim: no planned evaluation frozen; descriptive metrics only.

## Latest sets (2026-11-10)

- AACG (2026-11-10): dump tomorrow 0.18 (base 0.19, benchmark 0.17, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) -0.24; the spike in units of that volatility -0.15; an 8-K (or 6-K) that day or the day before +0.14]
- MI (2026-11-10): dump tomorrow 0.31 (base 0.19, benchmark 0.18, published 0.19); no call [MACD histogram +0.42; close within its 14-session high-low range (Stochastic %K) +0.22; 20-session move in the call's direction -0.17]
- PXLW (2026-11-10): dump tomorrow 0.17 (base 0.19, benchmark 0.18, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) -0.26; volatility before the spike -0.16; an 8-K (or 6-K) that day or the day before +0.14]
- SMX (2026-11-10): dump tomorrow 0.26 (base 0.19, benchmark 0.22, published 0.19); no call [volatility before the spike +0.21; close within its 14-session high-low range (Stochastic %K) -0.19; MACD histogram +0.19]
- MNDO (2026-11-10): dump tomorrow 0.16 (base 0.19, benchmark 0.24, published 0.19); no call [the spike in units of that volatility +0.48; close within its 14-session high-low range (Stochastic %K) -0.29; volatility before the spike -0.18]
- NNOX (2026-11-10): dump tomorrow 0.16 (base 0.19, benchmark 0.18, published 0.19); no call [an 8-K (or 6-K) that day or the day before -0.15; volatility before the spike -0.12; 20-session move in the call's direction -0.12]
- PEPG (2026-11-10): dump tomorrow 0.26 (base 0.19, benchmark 0.21, published 0.19); no call [the spike in units of that volatility +0.26; 20-session move in the call's direction +0.20; close near the day's high, in the call's direction -0.19]
- TTEC (2026-11-10): dump tomorrow 0.15 (base 0.19, benchmark 0.19, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) -0.22; an 8-K (or 6-K) that day or the day before -0.15; the spike in units of that volatility +0.13]
- NCI (2026-11-10): dump tomorrow 0.33 (base 0.19, benchmark 0.16, published 0.19); no call [MACD histogram +0.45; an 8-K (or 6-K) that day or the day before +0.14; RSI(14) +0.14]
- INLF (2026-11-10): dump tomorrow 0.49 (base 0.19, benchmark 0.34, published 0.19); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [volatility before the spike +0.68; MACD histogram +0.45; 20-session move in the call's direction -0.27]
- TANH (2026-11-10): dump tomorrow 0.30 (base 0.19, benchmark 0.24, published 0.19); no call [volatility before the spike +0.33; the spike in units of that volatility -0.21; 20-session move in the call's direction +0.21]
- TREO (2026-11-10): dump tomorrow 0.18 (base 0.19, benchmark 0.16, published 0.19); no call [the spike in units of that volatility -0.16; close within its 14-session high-low range (Stochastic %K) -0.14; an 8-K (or 6-K) that day or the day before +0.14]
- LGVN (2026-11-10): dump tomorrow 0.19 (base 0.19, benchmark 0.16, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) -0.31; an 8-K (or 6-K) that day or the day before +0.14; the spike in units of that volatility -0.13]
- ZIP (2026-11-10): dump tomorrow 0.11 (base 0.19, benchmark 0.17, published 0.19); shadow the stock holds: not: it closes at least 10% below the signal close at the next session, when most of its twins do not [close within its 14-session high-low range (Stochastic %K) -0.32; an 8-K (or 6-K) that day or the day before -0.15; close near the day's high, in the call's direction +0.10]
- ESLA (2026-11-10): dump tomorrow 0.31 (base 0.19, benchmark 0.21, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) +0.21; 20-session move in the call's direction +0.21; the spike in units of that volatility -0.20]

## Appendix

| Statement | Resolved | Rate | AUC | AUC benchmark | Brier gain vs base (se) | benchmark vs base | learner vs benchmark | Calls shadow right/n | live right/n |
|---|---:|---:|---:|---:|---|---|---|---|---|
| NEXT_DUMP10_1 | 53 | 0.264 | 0.709 | 0.705 | +0.0176 (0.0195; 4 blocks) | +0.0018 (0.0249; 4 blocks) | +0.0158 (0.0182; 4 blocks) | 4/4 | 0/0 |
| DUMP10_5 | 20 | 0.300 | 0.643 | 0.583 | -0.0208 (n/a; 1 blocks) | +0.0030 (n/a; 1 blocks) | -0.0238 (n/a; 1 blocks) | 0/0 | 0/0 |

Gates (confidence): **PATH/1** alpha 0.00, 4 observations, closed; **PATH/5** alpha 0.00, 1 observations, closed.

v2.2 against v2.3 on DUMP10_5, the same 20 sets: paired Brier gain of v2.3 -0.0011 (se 0.0238); AUC v2.2 0.5 vs v2.3 0.6428571428571429.

Due sets without a forecast: 32 (SPEC-SCAN-US-2026-11-02-G2_RET30-SEGG, SPEC-SCAN-US-2026-11-02-G2_RET30-INLF, SPEC-SCAN-US-2026-11-02-G2_RET30-CLRO, SPEC-SCAN-US-2026-11-02-G2_RET30-HXHX, SPEC-SCAN-US-2026-11-02-G2_RET30-INO, SPEC-SCAN-US-2026-11-02-G2_RET30-IFBD, SPEC-SCAN-US-2026-11-02-G2_RET30-GNTA, SPEC-SCAN-US-2026-11-02-G2_RET30-PERI, SPEC-SCAN-US-2026-11-02-G2_RET30-EVGO, SPEC-SCAN-US-2026-11-02-G2_RET30-NMRA).

