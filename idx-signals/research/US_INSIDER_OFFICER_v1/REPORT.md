# US_INSIDER_OFFICER_v1: result (run once, 2026-10-27)

**Verdict: FAIL** (G1 fails: t 1.21 < 1.65; G2 holds: mean +2.73% >= 2.0%).

| hold | group | scored | mean excess | t | median | winsorised | hit rate |
|---|---|---|---|---|---|---|---|
| 20 | officer, not director | 173 | +2.09% | 2.06 | +0.77% | +2.02% | 54.3% |
| 20 | all other insiders | 900 | +1.07% | 2.14 | -0.18% | +0.77% | 44.9% |
| 60 | officer, not director | 173 | +2.73% | 1.21 | +0.96% | +1.82% | 57.2% |
| 60 | all other insiders | 900 | +1.35% | 1.46 | -1.34% | +0.92% | 49.1% |
| 120 | officer, not director | 111 | +7.03% | 1.54 | +2.68% | +5.76% | 51.4% |
| 120 | all other insiders | 572 | +1.13% | 0.70 | -1.91% | +0.77% | 44.1% |

## Reading (as fixed in PROTOCOL.md)
The Stage 1 split did not clear the out-of-sample gate. The direction held at all three holds, the officer group beat the other insiders at
all three, and its median was positive, but the size shrank from +5.85% to +2.73% at hold 60 and 173 events cannot tell that from zero.
Per the protocol this backtest question is closed; no rerun and no rule change. Survivor-only prices still push every number here up.
