# TUNE_SWEEP_v1: result (both confirms, 2026-10-30)

1,470 model scenarios fitted on US +30% spikes of mid-2020-2022, ranked on 2023, the two pre-chosen candidates refit on
mid-2020-2023 and scored once on each confirm set (as-traded features, research/REPLAY_UNITS_v2). Numbers in
`results/CONFIRM_A.json` and `results/CONFIRM_B.json`.

| Confirm set | BEST (LightGBM) | TOP10 avg | v2.4 replay | v2.4 features, static | BEST vs v2.4 |
|---|---:|---:|---:|---:|---|
| A: 2026-04..10, 1,718 spikes | 0.650 | 0.647 | 0.620 | 0.637 | +0.030, p 0.015: **IMPROVES** |
| B: 2025-11..2026-03, 1,080 spikes | 0.639 | 0.638 | 0.643 | 0.631 | -0.004, p 0.61: **does not improve** |

All four beat chance on both periods (z 5.5 to 9.1). The 2023 pick score (0.695) overstated the winner by 0.05.

**Verdict.** The tuned model is as good as v2.4, better in one period and level in the other. The improvement does
not replicate, so it is not a reliable upgrade. Tuning found no hidden extra skill: v2.4's features already carry it.
