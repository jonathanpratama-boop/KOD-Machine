# LEARNER-v2.4: the one live challenger (KOD-LEARNER-v2.4, protocol sha256 8132768cb6c1)

Generated 2026-11-16T22:59:33Z. Paper only; no orders.

## The three plain answers

**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower at the next session, when most of its twins do not? (Companion: the same over its 5-session plan.)

**What counts as success?** Prospectively, on sealed sets: the forecasts rank the dumpers above the others (AUC above 0.5, z >= 3.75 at the first look of 250/500/1000 resolved pairs), with the Brier gain over the base rate and over the volatility-and-context benchmark reported beside it. The gate that unlocks published confidence needs 30 populated sessions of resolution.

**What evidence so far?** 161 forecasts sealed; 116 headline outcomes resolved; AUC 0.649 (benchmark 0.578); gate closed, alpha 0.00, 8 of 30 sessions. Claim: no planned evaluation frozen; descriptive metrics only.

## Latest sets (2026-11-16)

- HIHO (2026-11-16): dump tomorrow 0.22 (base 0.19, benchmark 0.20, published 0.19); no call [the market's own move that day +0.15; an 8-K (or 6-K) that day or the day before +0.12; close near the day's high, in the call's direction -0.11]
- GMM (2026-11-16): dump tomorrow 0.44 (base 0.19, benchmark 0.21, published 0.19); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [close within its 14-session high-low range (Stochastic %K) +0.43; close near the day's high, in the call's direction -0.23; opening gap (the move came at the open) +0.19]
- GDHG (2026-11-16): dump tomorrow 0.32 (base 0.19, benchmark 0.21, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) +0.66; close near the day's high, in the call's direction -0.28; an offering filing in the last 90 days +0.16]
- AKAN (2026-11-16): dump tomorrow 0.31 (base 0.19, benchmark 0.21, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) -0.23; an offering filing in the last 90 days +0.16; the market's own move that day +0.15]
- CYAB (2026-11-16): dump tomorrow 0.29 (base 0.19, benchmark 0.19, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) +0.42; close near the day's high, in the call's direction -0.27; opening gap (the move came at the open) +0.18]
- TDTH (2026-11-16): dump tomorrow 0.28 (base 0.19, benchmark 0.18, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) +0.19; an offering filing in the last 90 days +0.16; the market's own move that day +0.15]
- BGIN (2026-11-16): dump tomorrow 0.18 (base 0.19, benchmark 0.19, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) -0.27; RSI(14) -0.16; the market's own move that day +0.15]
- VIVK (2026-11-16): dump tomorrow 0.55 (base 0.19, benchmark 0.22, published 0.19); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [MACD histogram +0.66; close within its 14-session high-low range (Stochastic %K) +0.62; RSI(14) +0.19]
- CLRO (2026-11-16): dump tomorrow 0.31 (base 0.19, benchmark 0.24, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) +0.34; MACD histogram -0.20; volatility before the spike +0.17]
- ETS (2026-11-16): dump tomorrow 0.13 (base 0.19, benchmark 0.19, published 0.19); no call [close within its 14-session high-low range (Stochastic %K) -0.31; MACD histogram -0.17; an offering filing in the last 90 days +0.16]
- COSM (2026-11-16): dump tomorrow 0.26 (base 0.19, benchmark 0.40, published 0.19); no call [the spike in units of that volatility +0.79; volume against its 20-session median -0.46; close near the day's high, in the call's direction -0.29]

## Appendix

| Statement | Resolved | Rate | AUC | AUC benchmark | Brier gain vs base (se) | benchmark vs base | learner vs benchmark | Calls shadow right/n | live right/n |
|---|---:|---:|---:|---:|---|---|---|---|---|
| NEXT_DUMP10_1 | 116 | 0.250 | 0.649 | 0.578 | +0.0141 (0.0107; 8 blocks) | +0.0003 (0.0120; 8 blocks) | +0.0138 (0.0075; 8 blocks) | 11/15 | 0/0 |
| DUMP10_5 | 30 | 0.500 | 0.484 | 0.471 | -0.0164 (0.0044; 2 blocks) | -0.0050 (0.0080; 2 blocks) | -0.0115 (0.0124; 2 blocks) | 0/0 | 0/0 |

Gates (confidence): **PATH/1** alpha 0.00, 8 observations, closed; **PATH/5** alpha 0.00, 2 observations, closed.

v2.2 against v2.3 on DUMP10_5, the same 30 sets: paired Brier gain of v2.3 -0.0047 (se 0.0238); AUC v2.2 0.4266666666666667 vs v2.3 0.48444444444444446.

Due sets without a forecast: 32 (SPEC-SCAN-US-2026-11-02-G2_RET30-SEGG, SPEC-SCAN-US-2026-11-02-G2_RET30-INLF, SPEC-SCAN-US-2026-11-02-G2_RET30-CLRO, SPEC-SCAN-US-2026-11-02-G2_RET30-HXHX, SPEC-SCAN-US-2026-11-02-G2_RET30-INO, SPEC-SCAN-US-2026-11-02-G2_RET30-IFBD, SPEC-SCAN-US-2026-11-02-G2_RET30-GNTA, SPEC-SCAN-US-2026-11-02-G2_RET30-PERI, SPEC-SCAN-US-2026-11-02-G2_RET30-EVGO, SPEC-SCAN-US-2026-11-02-G2_RET30-NMRA).

