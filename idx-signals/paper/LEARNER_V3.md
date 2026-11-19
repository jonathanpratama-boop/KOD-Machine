# LEARNER-v2.4: the one live challenger (KOD-LEARNER-v2.4, protocol sha256 8132768cb6c1)

Generated 2026-11-18T22:59:36Z. Paper only; no orders.

## The three plain answers

**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower at the next session, when most of its twins do not? (Companion: the same over its 5-session plan.)

**What counts as success?** Prospectively, on sealed sets: the forecasts rank the dumpers above the others (AUC above 0.5, z >= 3.75 at the first look of 250/500/1000 resolved pairs), with the Brier gain over the base rate and over the volatility-and-context benchmark reported beside it. The gate that unlocks published confidence needs 30 populated sessions of resolution.

**What evidence so far?** 190 forecasts sealed; 141 headline outcomes resolved; AUC 0.628 (benchmark 0.565); gate closed, alpha 0.00, 10 of 30 sessions. Claim: no planned evaluation frozen; descriptive metrics only.

## Latest sets (2026-11-18)

- HIHO (2026-11-18): dump tomorrow 0.19 (base 0.22, benchmark 0.18, published 0.22); no call [close near the day's high, in the call's direction -0.20; the spike in units of that volatility -0.13; RSI(14) -0.11]
- SVRE (2026-11-18): dump tomorrow 0.31 (base 0.22, benchmark 0.21, published 0.22); no call [opening gap (the move came at the open) +0.19; an offering filing in the last 90 days +0.17; close near the day's high, in the call's direction -0.16]
- AKAN (2026-11-18): dump tomorrow 0.32 (base 0.22, benchmark 0.22, published 0.22); no call [close within its 14-session high-low range (Stochastic %K) -0.18; an offering filing in the last 90 days +0.17; MACD histogram +0.13]
- AZI (2026-11-18): dump tomorrow 0.21 (base 0.22, benchmark 0.19, published 0.22); no call [close within its 14-session high-low range (Stochastic %K) -0.26; an offering filing in the last 90 days +0.17; an 8-K (or 6-K) that day or the day before -0.15]
- MPU (2026-11-18): dump tomorrow 0.22 (base 0.22, benchmark 0.19, published 0.22); no call [close within its 14-session high-low range (Stochastic %K) -0.33; the spike in units of that volatility -0.15; close near the day's high, in the call's direction +0.14]
- ANPA (2026-11-18): dump tomorrow 0.20 (base 0.22, benchmark 0.18, published 0.22); no call [that share against its 20-session median +0.14; close within its 14-session high-low range (Stochastic %K) +0.11; an 8-K (or 6-K) that day or the day before +0.11]
- VWAV (2026-11-18): dump tomorrow 0.51 (base 0.22, benchmark 0.21, published 0.22); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [close within its 14-session high-low range (Stochastic %K) +0.60; MACD histogram +0.51; 5-session move in the call's direction -0.19]
- CUE (2026-11-18): dump tomorrow 0.18 (base 0.22, benchmark 0.27, published 0.22); no call [MACD histogram -0.79; close within its 14-session high-low range (Stochastic %K) +0.69; 5-session move in the call's direction -0.29]
- BTOC (2026-11-18): dump tomorrow 0.28 (base 0.22, benchmark 0.18, published 0.22); no call [close within its 14-session high-low range (Stochastic %K) +0.28; close near the day's high, in the call's direction +0.17; an 8-K (or 6-K) that day or the day before +0.11]
- CLRO (2026-11-18): dump tomorrow 0.19 (base 0.22, benchmark 0.22, published 0.22); no call [an offering filing in the last 90 days +0.17; the spike in units of that volatility -0.15; an 8-K (or 6-K) that day or the day before -0.15]
- NUR (2026-11-18): dump tomorrow 0.24 (base 0.22, benchmark 0.18, published 0.22); no call [close within its 14-session high-low range (Stochastic %K) +0.43; an 8-K (or 6-K) that day or the day before -0.15; the spike in units of that volatility -0.12]
- SKYA (2026-11-18): dump tomorrow 0.19 (base 0.22, benchmark 0.21, published 0.22); no call [close within its 14-session high-low range (Stochastic %K) -0.24; MACD histogram -0.17; that share against its 20-session median +0.15]
- ICU (2026-11-18): dump tomorrow 0.24 (base 0.22, benchmark 0.19, published 0.22); no call [close within its 14-session high-low range (Stochastic %K) +0.63; MACD histogram -0.46; 5-session move in the call's direction -0.25]

## Appendix

| Statement | Resolved | Rate | AUC | AUC benchmark | Brier gain vs base (se) | benchmark vs base | learner vs benchmark | Calls shadow right/n | live right/n |
|---|---:|---:|---:|---:|---|---|---|---|---|
| NEXT_DUMP10_1 | 141 | 0.262 | 0.628 | 0.565 | +0.0173 (0.0104; 10 blocks) | +0.0000 (0.0095; 10 blocks) | +0.0172 (0.0082; 10 blocks) | 15/23 | 0/0 |
| DUMP10_5 | 74 | 0.392 | 0.625 | 0.634 | -0.0164 (0.0044; 2 blocks) | -0.0050 (0.0080; 2 blocks) | -0.0115 (0.0124; 2 blocks) | 2/4 | 0/0 |

Gates (confidence): **PATH/1** alpha 0.00, 10 observations, closed; **PATH/5** alpha 0.00, 2 observations, closed.

v2.2 against v2.3 on DUMP10_5, the same 74 sets: paired Brier gain of v2.3 +0.0137 (se 0.0144); AUC v2.2 0.46513409961685825 vs v2.3 0.6245210727969349.

Due sets without a forecast: 32 (SPEC-SCAN-US-2026-11-02-G2_RET30-SEGG, SPEC-SCAN-US-2026-11-02-G2_RET30-INLF, SPEC-SCAN-US-2026-11-02-G2_RET30-CLRO, SPEC-SCAN-US-2026-11-02-G2_RET30-HXHX, SPEC-SCAN-US-2026-11-02-G2_RET30-INO, SPEC-SCAN-US-2026-11-02-G2_RET30-IFBD, SPEC-SCAN-US-2026-11-02-G2_RET30-GNTA, SPEC-SCAN-US-2026-11-02-G2_RET30-PERI, SPEC-SCAN-US-2026-11-02-G2_RET30-EVGO, SPEC-SCAN-US-2026-11-02-G2_RET30-NMRA).

