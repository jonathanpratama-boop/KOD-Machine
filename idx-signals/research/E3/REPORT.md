# E3 results (protocol KOD-IDX-E3-v1): no execution plan admitted

Historical research on IDX TIER_1 data, discovery period 2021-01-22 .. 2022-12-30 only.
Validation (2023) was not run and the holdout was not touched: the protocol runs validation only
for a selected pair, and none was selected.

## Result

108 harness runs: the ARA detectors F1_ARA, F7_ARA_VOL3 and F8_ARA_EARLY, each under the 36
pre-registered plans (4 entries x 3 exits x hold 2/3/5), fill model C, corporate-action
registry, 200 matched and 200 same-session random draws per run (`discovery/plans.csv`,
`discovery/summary.json`).

**Admissible pairs: 0 of 108.** `moonshot_e3.SELECTED` stays None, `MOONSHOT_E3_D1` is never
created, and the paper policy keeps PASS for IDX candidates.

| | count of 108 |
|---|---:|
| average net return > 0 | 18 |
| above matched random at one-sided p < 0.05 | 3 |
| average net return > 0 in 2021 | 28 |
| average net return > 0 in 2022 | **0** |

Best by average net return (none admissible):

| Pair | Scored | Avg net | Matched random | p | 2021 | 2022 |
|---|---:|---:|---:|---:|---:|---:|
| F8_ARA_EARLY, confirm within 3, fixed exit, hold 5 | 218 | +1.49% | +0.56% | 0.14 | +2.45% | -0.03% |
| F7_ARA_VOL3, confirm within 3, fixed exit, hold 5 | 301 | +1.40% | +0.20% | 0.08 | +2.65% | -1.06% |
| F7_ARA_VOL3, next close, fixed exit, hold 5 | 487 | +1.10% | +0.14% | 0.015 | +2.51% | -1.60% |
| F7_ARA_VOL3, next close, stop at reference, hold 5 | 488 | +1.09% | +0.06% | 0.005 | +2.52% | -1.63% |
| F1_ARA, next close, hold 5 (reference: D1's original plan) | 652 | +0.24% | +0.17% | 0.44 | | -1.56% |

The three pairs that beat matched random at p < 0.05 all lost money in 2022, so the per-year
condition excluded them. Every one of the 108 lost money in 2022.

Averages over the grid: by entry, confirm -0.68%, fixed -0.98%, unlock -1.09%, pullback
-1.95%; by holding period, 5 sessions -0.34%, 3 sessions -1.22%, 2 sessions -1.96%. The worst
pair (F1_ARA, pullback entry, first-down exit, hold 5) averaged -3.50%.

## Reading

- Waiting for confirmation (a close above the signal close within three sessions) was the best
  entry family, and holding longer was better than cutting early. That is consistent with E1's
  finding that the next-close fills select the moves that are fading, and with a fat right tail
  that early exits cut off.
- The edge, where there was one, was 2021 only. 2021 was the most active year in E1's base rates
  (+30% in 5 sessions: 2.5% of ticker-days vs 1.3% in 2022). A plan that only paid in a hot year
  is what the per-year condition exists to reject, and it did.
- This family of plans is now exhausted for these detectors on discovery. Re-tuning thresholds on
  the same discovery data, or relaxing the admission rule after reading this table, would be
  selection on noise and is not done.

## Precondition and deviations

The recorded E1 trading runs reproduce exactly on the rule side; the matched baseline differs
in the fourth decimal because the control-matching code changed after those runs
(`ADDENDUM_1.md`, `ADDENDUM_2.md`, `reproduce/result.json`). Discovery ran with
`--accept-deviation`, recorded in `discovery/summary.json`.

## What would be a new experiment

A new protocol, not an amendment: a different signal family (E1 found prior volatility is the
only pre-event separator, AUC 0.68), or a regime condition fixed in advance (for example, trade
only when the market-wide ARA count is above its trailing median), each designed without
looking at 2023 and tested once on it. The holdout stays sealed for a final test after
prospective evidence exists.
