# E6 discovery (Stage 1): NULL at the frozen gate

Protocol KOD-CRYPTO-E6-v1 frozen `cacda7b`; implementation `973546d`, committed before this run; run once.
Historical research on hourly bars; nothing here is prospective performance, a probability or a trade.

**Scope.** Decision days 2020-07-01..2022-12-25. 351 coins had data in that span; the other 55 of the
manifest's 406 list only in 2023. 204,867 eligible coin-days, about 233 coins a day. No bar after
2022-12-31 23:00 was read. Exclusions: 0 coin-days failed the data-sanity rule; 0 flags lacked an entry bar;
0 lacked controls; 4 windows ended early on a delisting or missing bar (P1 1, B0 3) and are kept with the last
available close.

Excess = five-day return minus the mean of 200 matched coins; interval and one-sided p by week-cluster
bootstrap (10,000 resamples).

| Arm | Role | Flags | Coins | Mean 5-day return | Matched | Excess [95%] | p | E30 rate (matched) | +30% before −5%: win / loss / timeout |
|---|---|---|---|---|---|---|---|---|---|
| P1 pressure | primary | 776 | 265 | +1.26% | +0.90% | +0.37% [−1.01, +1.93] | 0.32 | 14.3% (13.2%) | 9.5% / 69.3% / 21.1% |
| P2 pressure then breakout | primary | 136 | 95 | +4.03% | +2.17% | +1.86% [−2.70, +7.83] | 0.26 | 24.3% (17.4%) | 16.2% / 72.1% / 11.8% |
| B0 plain breakout | comparator | 2,431 | 322 | +3.62% | +4.22% | −0.60% [−1.86, +0.87] | 0.80 | 25.3% (19.8%) | 11.7% / 81.2% / 7.1% |
| PL scrambled-flow placebo | placebo | 231 | 154 | −0.90% | −0.72% | −0.17% [−2.03, +1.77] | 0.59 | 12.1% (12.2%) | 5.6% / 72.7% / 21.6% |

| Comparison | Difference in excess [95%] | p |
|---|---|---|
| P1 minus placebo | +0.54% [−1.86, +3.01] | 0.33 |
| P1 minus breakout | +0.96% [−1.16, +3.15] | 0.19 |
| P2 minus placebo | +2.03% [−2.96, +8.10] | 0.25 |
| P2 minus breakout | +2.45% [−1.94, +8.23] | 0.18 |

By year, excess: P1 +0.44% (2020, 83 flags), +0.37% (2021, 251), +0.36% (2022, 442). P2 −3.8% (2020, 32),
+5.8% (2021, 68), −0.6% (2022, 36).

**Gates.** P1 FAILS: excess vs matched p 0.32 (needs < 0.025); minus placebo p 0.33 (needs < 0.05).
P2 FAILS: 136 flags (needs 200); p 0.26; 2022 negative; minus placebo p 0.25.

**Consequence (pre-registered).** Stage 2, validation on 2023 and the holdout are not authorised and were
not run. `consequences.stage_1_fails_both` applies: no information found in the buy/sell pressure response at
this resolution and with these rules; stop this family.

**How to read it.** Point estimates lean the hypothesised way (P1 and P2 above the placebo and the breakout)
but every interval includes zero, and P2 rests on 136 flags. That is not evidence of an effect and not
evidence of none at a smaller size; it is a null at the pre-registered gate. The same-hour flow/return
correlation in `data_check/` is a measurement check of the data, not predictive evidence. Most five-day
windows hit −5% before +30% in every arm, including matched coins, so a −5% stop is noise-level in this
universe.
