# LEARNER-v2.4: the one live challenger (KOD-LEARNER-v2.4, protocol sha256 8132768cb6c1)

Generated 2026-11-20T22:58:09Z. Paper only; no orders.

## The three plain answers

**What are we predicting?** For a US stock that just closed 30% or more higher: will it close at least 10% lower at the next session, when most of its twins do not? (Companion: the same over its 5-session plan.)

**What counts as success?** Prospectively, on sealed sets: the forecasts rank the dumpers above the others (AUC above 0.5, z >= 3.75 at the first look of 250/500/1000 resolved pairs), with the Brier gain over the base rate and over the volatility-and-context benchmark reported beside it. The gate that unlocks published confidence needs 30 populated sessions of resolution.

**What evidence so far?** 212 forecasts sealed; 167 headline outcomes resolved; AUC 0.644 (benchmark 0.563); gate closed, alpha 0.00, 12 of 30 sessions. Claim: no planned evaluation frozen; descriptive metrics only.

## Latest sets (2026-11-20)

- NXAT (2026-11-20): dump tomorrow 0.40 (base 0.25, benchmark 0.31, published 0.25); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [close near the day's high, in the call's direction -0.27; the market's own move that day +0.23; close within its 14-session high-low range (Stochastic %K) +0.17]
- CIGL (2026-11-20): dump tomorrow 0.29 (base 0.25, benchmark 0.27, published 0.25); no call [close within its 14-session high-low range (Stochastic %K) +0.31; the market's own move that day +0.23; close near the day's high, in the call's direction -0.19]
- MSS (2026-11-20): dump tomorrow 0.33 (base 0.25, benchmark 0.27, published 0.25); no call [close within its 14-session high-low range (Stochastic %K) +0.33; the market's own move that day +0.23; close near the day's high, in the call's direction -0.20]
- RAYA (2026-11-20): dump tomorrow 0.41 (base 0.25, benchmark 0.28, published 0.25); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [close within its 14-session high-low range (Stochastic %K) +0.65; the market's own move that day +0.23; the spike in units of that volatility -0.14]
- MEDS (2026-11-20): dump tomorrow 0.32 (base 0.25, benchmark 0.28, published 0.25); no call [the market's own move that day +0.23; an offering filing in the last 90 days +0.21; an 8-K (or 6-K) that day or the day before -0.16]
- LVWR (2026-11-20): dump tomorrow 0.24 (base 0.25, benchmark 0.32, published 0.25); no call [close within its 14-session high-low range (Stochastic %K) -0.28; the market's own move that day +0.23; the spike in units of that volatility -0.15]
- BNAI (2026-11-20): dump tomorrow 0.25 (base 0.25, benchmark 0.26, published 0.25); no call [close within its 14-session high-low range (Stochastic %K) +0.48; MACD histogram -0.28; the market's own move that day +0.23]
- YOUL (2026-11-20): dump tomorrow 0.47 (base 0.25, benchmark 0.28, published 0.25); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [close within its 14-session high-low range (Stochastic %K) +0.59; the market's own move that day +0.23; an offering filing in the last 90 days +0.21]
- AMCI (2026-11-20): dump tomorrow 0.43 (base 0.25, benchmark 0.28, published 0.25); shadow AVOID the stock: it closes at least 10% below the signal close at the next session, when most of its twins do not [close within its 14-session high-low range (Stochastic %K) +0.58; the market's own move that day +0.23; an offering filing in the last 90 days +0.21]
- NIXX (2026-11-20): dump tomorrow 0.31 (base 0.25, benchmark 0.45, published 0.25); no call [the spike in units of that volatility +0.76; close near the day's high, in the call's direction -0.39; volume against its 20-session median -0.27]

## Appendix

| Statement | Resolved | Rate | AUC | AUC benchmark | Brier gain vs base (se) | benchmark vs base | learner vs benchmark | Calls shadow right/n | live right/n |
|---|---:|---:|---:|---:|---|---|---|---|---|
| NEXT_DUMP10_1 | 167 | 0.275 | 0.644 | 0.563 | +0.0230 (0.0095; 12 blocks) | +0.0014 (0.0080; 12 blocks) | +0.0216 (0.0087; 12 blocks) | 18/26 | 0/0 |
| DUMP10_5 | 103 | 0.320 | 0.564 | 0.645 | -0.0164 (0.0044; 2 blocks) | -0.0050 (0.0080; 2 blocks) | -0.0115 (0.0124; 2 blocks) | 2/6 | 0/0 |

Gates (confidence): **PATH/1** alpha 0.00, 12 observations, closed; **PATH/5** alpha 0.00, 2 observations, closed.

v2.2 against v2.3 on DUMP10_5, the same 103 sets: paired Brier gain of v2.3 +0.0032 (se 0.0117); AUC v2.2 0.4896103896103896 vs v2.3 0.564069264069264.

Due sets without a forecast: 32 (SPEC-SCAN-US-2026-11-02-G2_RET30-SEGG, SPEC-SCAN-US-2026-11-02-G2_RET30-INLF, SPEC-SCAN-US-2026-11-02-G2_RET30-CLRO, SPEC-SCAN-US-2026-11-02-G2_RET30-HXHX, SPEC-SCAN-US-2026-11-02-G2_RET30-INO, SPEC-SCAN-US-2026-11-02-G2_RET30-IFBD, SPEC-SCAN-US-2026-11-02-G2_RET30-GNTA, SPEC-SCAN-US-2026-11-02-G2_RET30-PERI, SPEC-SCAN-US-2026-11-02-G2_RET30-EVGO, SPEC-SCAN-US-2026-11-02-G2_RET30-NMRA).

