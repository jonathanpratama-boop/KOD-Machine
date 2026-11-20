# LEARNER-v2.4: the one live challenger (KOD-LEARNER-v2.4, protocol sha256 8132768cb6c1)

Generated 2026-11-19T22:59:25Z. Paper only; no orders.

## The three plain answers

**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower at the next session, when most of its twins do not? (Companion: the same over its 5-session plan.)

**What counts as success?** Prospectively, on sealed sets: the forecasts rank the dumpers above the others (AUC above 0.5, z >= 3.75 at the first look of 250/500/1000 resolved pairs), with the Brier gain over the base rate and over the volatility-and-context benchmark reported beside it. The gate that unlocks published confidence needs 30 populated sessions of resolution.

**What evidence so far?** 202 forecasts sealed; 155 headline outcomes resolved; AUC 0.637 (benchmark 0.562); gate closed, alpha 0.00, 11 of 30 sessions. Claim: no planned evaluation frozen; descriptive metrics only.

## Latest sets (2026-11-19)

- VIVS (2026-11-19): dump tomorrow 0.42 (base 0.24, benchmark 0.30, published 0.24); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [the spike in units of that volatility +0.23; volume against shares outstanding +0.23; close within its 14-session high-low range (Stochastic %K) -0.19]
- SEAT (2026-11-19): dump tomorrow 0.21 (base 0.24, benchmark 0.25, published 0.24); no call [close within its 14-session high-low range (Stochastic %K) +0.21; opening gap (the move came at the open) +0.17; the market's own move that day +0.17]
- RAYA (2026-11-19): dump tomorrow 0.30 (base 0.24, benchmark 0.24, published 0.24); no call [close within its 14-session high-low range (Stochastic %K) +0.73; MACD histogram -0.30; the market's own move that day +0.17]
- MPU (2026-11-19): dump tomorrow 0.28 (base 0.24, benchmark 0.26, published 0.24); no call [close within its 14-session high-low range (Stochastic %K) -0.31; the market's own move that day +0.17; close near the day's high, in the call's direction +0.15]
- MRKR (2026-11-19): dump tomorrow 0.20 (base 0.24, benchmark 0.24, published 0.24); no call [the market's own move that day +0.17; an 8-K (or 6-K) that day or the day before -0.17; close near the day's high, in the call's direction -0.12]
- POAS (2026-11-19): dump tomorrow 0.31 (base 0.24, benchmark 0.32, published 0.24); no call [close near the day's high, in the call's direction -0.24; volatility before the spike +0.19; close within its 14-session high-low range (Stochastic %K) +0.19]
- LVWR (2026-11-19): dump tomorrow 0.21 (base 0.24, benchmark 0.27, published 0.24); no call [the market's own move that day +0.17; MACD histogram -0.16; the spike in units of that volatility -0.12]
- ZKIN (2026-11-19): dump tomorrow 0.15 (base 0.24, benchmark 0.23, published 0.24); no call [MACD histogram -0.19; that share against its 20-session median -0.18; the market's own move that day +0.17]
- ELOG (2026-11-19): dump tomorrow 0.21 (base 0.24, benchmark 0.25, published 0.24); no call [close within its 14-session high-low range (Stochastic %K) -0.32; an offering filing in the last 90 days +0.20; the market's own move that day +0.17]
- HTCR (2026-11-19): dump tomorrow 0.27 (base 0.24, benchmark 0.23, published 0.24); no call [close near the day's high, in the call's direction +0.21; the market's own move that day +0.17; MACD histogram -0.14]
- BAER (2026-11-19): dump tomorrow 0.26 (base 0.24, benchmark 0.24, published 0.24); no call [close near the day's high, in the call's direction +0.18; the market's own move that day +0.17; the spike in units of that volatility -0.13]
- BDMD (2026-11-19): dump tomorrow 0.52 (base 0.24, benchmark 0.27, published 0.24); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [MACD histogram +0.61; close within its 14-session high-low range (Stochastic %K) +0.52; volume against its 20-session median -0.25]

## Appendix

| Statement | Resolved | Rate | AUC | AUC benchmark | Brier gain vs base (se) | benchmark vs base | learner vs benchmark | Calls shadow right/n | live right/n |
|---|---:|---:|---:|---:|---|---|---|---|---|
| NEXT_DUMP10_1 | 155 | 0.271 | 0.637 | 0.562 | +0.0209 (0.0101; 11 blocks) | +0.0017 (0.0087; 11 blocks) | +0.0192 (0.0085; 11 blocks) | 17/25 | 0/0 |
| DUMP10_5 | 87 | 0.368 | 0.595 | 0.622 | -0.0164 (0.0044; 2 blocks) | -0.0050 (0.0080; 2 blocks) | -0.0115 (0.0124; 2 blocks) | 2/5 | 0/0 |

Gates (confidence): **PATH/1** alpha 0.00, 11 observations, closed; **PATH/5** alpha 0.00, 2 observations, closed.

v2.2 against v2.3 on DUMP10_5, the same 87 sets: paired Brier gain of v2.3 +0.0078 (se 0.0129); AUC v2.2 0.48806818181818185 vs v2.3 0.5948863636363636.

Due sets without a forecast: 32 (SPEC-SCAN-US-2026-11-02-G2_RET30-SEGG, SPEC-SCAN-US-2026-11-02-G2_RET30-INLF, SPEC-SCAN-US-2026-11-02-G2_RET30-CLRO, SPEC-SCAN-US-2026-11-02-G2_RET30-HXHX, SPEC-SCAN-US-2026-11-02-G2_RET30-INO, SPEC-SCAN-US-2026-11-02-G2_RET30-IFBD, SPEC-SCAN-US-2026-11-02-G2_RET30-GNTA, SPEC-SCAN-US-2026-11-02-G2_RET30-PERI, SPEC-SCAN-US-2026-11-02-G2_RET30-EVGO, SPEC-SCAN-US-2026-11-02-G2_RET30-NMRA).

