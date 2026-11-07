# BREADTH_v1 results: not passed, idea dropped

Run 2026-11-07 after the protocol, code and ONE's kline file were stamped (freetsa and sectigo, 18:39:39Z, commit 686997fe0).

| Period | Alerts | BROAD (B >= 2) | Mean net 24h, BROAD | Mean net 24h, rest | Difference (95% day-bootstrap) |
|---|---|---|---|---|---|
| 2020-2022 (disc) | 5,263 | 18 (0.3%) | -5.5% | -2.7% | -2.9 pts (-7.4 to +2.4) |
| 2023-2026 (hold) | 7,120 | 20 (0.3%) | -0.9% | -3.3% | +2.4 pts (-2.2 to +7.4) |

- The pass rule needed the interval above zero in both periods. Neither period has it, and the two point estimates point in
  opposite directions.
- Across all alerts, the five B quintiles have nearly the same mean and median 24h result in both periods (means
  -1.9% to -3.9%). A smooth breadth effect is not there either.
- **ONE itself was not a BROAD event.** Using the protocol's 7-day baseline, its trade multiple was 35.8x against a
  dollar multiple of 28.6x, so B = 1.25. The roughly 65x figure quoted in chat compared against quiet overnight hours
  rather than the 7-day average, and it was wrong.

Conclusion: across 12,383 past alerts, a bigger jump in trade count than in dollar volume does not predict better
24h outcomes. Dropped, per the protocol.
