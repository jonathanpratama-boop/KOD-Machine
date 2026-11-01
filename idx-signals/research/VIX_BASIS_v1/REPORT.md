# VIX_BASIS_v1: selling VIX futures in contango (futures study, simulation only)

Ran 2026-11-01T09:09:23Z at commit `d9a4ad9396bacbe2dfdff6cb87223129c02d66f0` on the frozen protocol (`protocol.json`, sha256 `2eb2ba8f072c5a3b...`, RFC 3161 timestamps in `timestamps/`). One run. Rule: the Simon-Campasano entry (front = nearest VX with >= 10 trading days; short when (F - VIX)/days > 0.10; 5-session segments), short leg only, unhedged, notional 20% of equity, 0.065 points per side, fills at settlement.

## Verdict: NOT_CONFIRMED

| Gate | Result |
|---|---|
| D0_sample | PASS |
| D1_account | PASS |
| D2_net | PASS |
| D3_drawdown | PASS |
| D4_stress | PASS |
| D5_not_brittle | PASS |
| D6_years | PASS |
| V1_account | PASS |
| V2_net | PASS |
| V3_drawdown | PASS |
| V4_costs | FAIL |

## Discovery 2006-01-03 .. 2015-12-31 (2006-2011 is the paper's own sample)

| Arm | Positions (segments) | Mean net / position | Median | Win | Account (USD 10,000) | CAGR | Max DD (daily) | Worst day | Years up | Exposure | Costs/yr | P&L without top 5 | Bootstrap LB (95%, 1-sided) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| primary | 106 (193) | +3.21% | +3.61% | +62% | 19,134 (+91.3%) | +6.7% | -19.1% | -7.5% | 9/10 | +38% | +1.6% | 4,838 | +1.20% |
| S1_double_costs | 106 (193) | +2.52% | +3.11% | +60% | 16,534 (+65.3%) | +5.2% | -21.6% | -7.6% | 9/10 | +38% | +3.2% | 2,589 | +0.50% |
| S2_lag_2 | 106 (193) | +3.43% | +3.16% | +70% | 20,063 (+100.6%) | +7.2% | -16.6% | -7.4% | 8/10 | +38% | +1.6% | 6,144 | +1.51% |
| N1_threshold_0.05 | 154 (346) | +1.96% | +1.14% | +55% | 17,289 (+72.9%) | +5.6% | -17.0% | -7.0% | 7/10 | +69% | +2.3% | 3,144 | +0.22% |
| N2_threshold_0.15 | 49 (71) | +5.36% | +5.21% | +76% | 16,745 (+67.5%) | +5.3% | -5.3% | -2.6% | 8/10 | +14% | +0.6% | 3,735 | +3.50% |
| D1_both_sides | 147 (251) | +3.32% | +3.15% | +57% | 24,859 (+148.6%) | +9.5% | -29.2% | -7.6% | 8/10 | +50% | +2.1% | 6,548 | +1.28% |
| B1_always_short | 121 (504) | +1.91% | +5.25% | +66% | 14,065 (+40.7%) | +3.5% | -42.8% | -7.4% | 6/10 | +100% | +1.7% | 423 | -1.43% |
| R1_whole_vxm_contracts | 103 (188) | +2.58% | +3.38% | +61% | 16,185 (+61.9%) | +4.9% | -20.4% | -8.9% | 8/10 | +37% | +1.6% | 2,474 | +0.52% |
| SPX price index, held (context) | - | - | - | - | +61.1% | - | -56.8% | - | - | 100% | - | - | - |
| Cash | - | - | - | - | 10,000 (+0.0%) | - | - | - | - | 0% | - | - | - |

| Arm | 2006 | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 |
|---|---|---|---|---|---|---|---|---|---|---|
| primary | +1.9% | +3.8% | +3.5% | +20.8% | +16.5% | +5.9% | +24.6% | +6.4% | +4.3% | -15.1% |
| S1_double_costs | +1.1% | +3.2% | +2.4% | +19.4% | +14.5% | +4.9% | +22.4% | +4.2% | +2.3% | -17.4% |
| B1_always_short | +9.1% | -15.3% | -22.8% | +21.7% | +22.8% | -10.4% | +26.5% | +22.1% | -6.7% | +2.0% |

## Validation 2016-01-04 .. 2023-12-29 (after publication)

| Arm | Positions (segments) | Mean net / position | Median | Win | Account (USD 10,000) | CAGR | Max DD (daily) | Worst day | Years up | Exposure | Costs/yr | P&L without top 5 | Bootstrap LB (95%, 1-sided) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| primary | 99 (196) | +0.79% | +1.91% | +57% | 11,362 (+13.6%) | +1.6% | -16.9% | -5.8% | 4/8 | +49% | +1.9% | -1,373 | -1.16% |
| S1_double_costs | 99 (196) | +0.03% | +1.00% | +55% | 9,784 (-2.2%) | -0.3% | -18.3% | -5.8% | 4/8 | +49% | +3.8% | -2,669 | -1.91% |
| S2_lag_2 | 99 (196) | +1.09% | +2.39% | +62% | 12,042 (+20.4%) | +2.4% | -17.4% | -6.9% | 4/8 | +49% | +1.9% | -645 | -0.91% |
| N1_threshold_0.05 | 123 (306) | +2.04% | +3.36% | +60% | 15,729 (+57.3%) | +5.8% | -14.5% | -10.0% | 5/8 | +76% | +2.3% | 1,756 | +0.03% |
| N2_threshold_0.15 | 46 (69) | +0.65% | +2.00% | +61% | 10,504 (+5.0%) | +0.6% | -14.0% | -5.0% | 5/8 | +17% | +0.8% | -1,223 | -2.26% |
| D1_both_sides | 125 (231) | +0.06% | +0.65% | +52% | 9,635 (-3.7%) | -0.5% | -30.2% | -5.8% | 3/8 | +57% | +2.2% | -4,225 | -2.10% |
| B1_always_short | 97 (403) | +3.13% | +8.85% | +66% | 15,724 (+57.2%) | +5.8% | -46.6% | -27.0% | 6/8 | +100% | +1.8% | 1,777 | -1.53% |
| R1_whole_vxm_contracts | 99 (196) | +0.29% | +1.82% | +56% | 11,160 (+11.6%) | +1.4% | -16.7% | -6.5% | 4/8 | +49% | +1.8% | -2,047 | -1.87% |
| SPX price index, held (context) | - | - | - | - | +137.0% | - | -33.9% | - | - | 100% | - | - | - |
| Cash | - | - | - | - | 10,000 (+0.0%) | - | - | - | - | 0% | - | - | - |

| Arm | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|
| primary | -2.1% | +14.3% | -2.2% | -2.8% | +6.4% | +3.2% | -8.7% | +6.4% |
| S1_double_costs | -4.5% | +10.8% | -3.2% | -4.8% | +5.2% | +0.8% | -9.8% | +4.9% |
| B1_always_short | +14.0% | +24.3% | -29.7% | +19.7% | -16.3% | +25.7% | +1.3% | +23.6% |

## What this does and does not show

- Discovery passed every gate, but 2006-2011 is the sample the rule was published on, so it is not independent evidence.
- After publication the same frozen rule earned far less: it ended above its start and stayed within the drawdown gate, but failed with doubled costs, its P&L without the 5 best positions is negative, its bootstrap lower bound is below zero, and it rose in only half the years. It trailed simply holding the S&P 500 by a wide margin.
- Other arms (thresholds 0.05/0.15, both sides, always short, whole contracts) are reported as frozen and are not candidates: picking the best of them after seeing validation would be a new, contaminated hypothesis.
- No stop is used and no result is a maximum loss: always-short's worst day in validation was -27% of equity at 20% notional (February 2018).
- The account curve assumes fractional contracts (R1 shows whole Mini VIX contracts), settlement-price fills, assumed VXM costs, and no interest on collateral. Venue eligibility is not verified; eToro's VIX is a CFD, not this product.
- Simulation only. The sealed 2024-2026 holdout was not used and is not requested: the rule did not confirm.
