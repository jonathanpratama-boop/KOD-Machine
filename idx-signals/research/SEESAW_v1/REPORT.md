# SEESAW_v1: result (run once, 2026-11-03; run 1 crashed at import before reading data, see RUN_NOTES.txt; produced by run_v2.py)

**Reading: FLOW DESCRIBES, DOES NOT LEAD.** 79 monthly blocks, 2020-03 .. 2026-09.

| Signal known at the start of the month | Rank correlation with next month's moonshot rate, 2020-22 | 2023-26 | With next month's median alt return, 2020-22 | 2023-26 |
|---|---:|---:|---:|---:|
| S1 stablecoin supply, 30-day change | +0.34 | +0.17 | +0.22 | -0.14 |
| S2 alts minus BTC, last 30 days (the seesaw) | +0.06 | -0.04 | -0.04 | -0.11 |
| S3 share of alts above their 50-day SMA | +0.23 | +0.24 | +0.09 | +0.14 |

| Locked "tide on" rule (S1 > 0 and S2 > 0) | Months | Moonshot rate | Median alt return next 30 days |
|---|---:|---:|---:|
| 2020-22 on | 13 | 36.9% | -0.2% |
| 2020-22 off | 21 | 31.3% | +2.0% |
| 2023-26 on | 7 | 19.9% | -9.3% |
| 2023-26 off | 38 | 23.9% | -1.4% |

- The locked rule failed in the check period: "tide on" months were worse, not better.
- The seesaw itself (S2) carried no stable information at a monthly horizon; its extremes flipped sign between periods
  (2020-22: alts leading BTC came before better months; 2023-26: before worse ones).
- Stablecoin growth and breadth lean weakly toward more moonshots in both periods (rank correlation +0.17 to +0.34), but
  not toward better returns in 2023-26. With about 80 months these are leans, not findings.
- Stablecoin supply barely moved after 2023 compared with 2020-21 (monthly changes of a few percent), so the flow gauge had
  little to say in the current market.
