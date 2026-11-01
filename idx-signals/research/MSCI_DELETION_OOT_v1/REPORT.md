# MSCI_DELETION_OOT_v1: the frozen MSCI deletion rule on the reviews after the sealed IDX holdout

Ran 2026-11-01T00:38:29Z at commit `9220b7b4d91babbdbfe32293f2709c509657bfcd` on the frozen protocol. One run. Simulation only; reviews Feb 2025 .. Aug 2026 on the post-holdout IDX segment (2025-02-24 .. 2026-10-06); the sealed holdout's outcomes were not computed.

## Verdict: NOT_CONFIRMED

| Gate | Result |
|---|---|
| O0_sample | PASS |
| O1_net | FAIL |
| O2_excess | PASS |
| O3_account | FAIL |

## Out-of-time reviews (Feb 2025 .. Aug 2026)

| Variant | Scored | Mean net | Median net | Win rate | Worst / best | Mean matched control | Mean excess | Excess 95% (review clusters) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Primary: buy the implementation close, hold 20 | 46 | -4.19% | -5.05% | 28% | -40.24% / +60.94% | -8.72% | +4.53% | -3.55% to +10.60% |
| S1: buy one session later | 45 | -9.06% | -8.33% | 16% | -40.24% / +23.83% | -8.31% | -0.76% | -6.98% to +3.93% |
| S2: one tick per side added | 46 | -5.21% | -5.87% | 28% | -43.37% / +59.28% | -9.75% | +4.54% | -3.48% to +10.58% |
| Descriptive: hold 5 | 46 | +0.98% | +1.82% | 54% | -46.64% / +40.90% | -5.69% | +6.67% | +2.78% to +9.45% |
| Descriptive: hold 60 | 35 | +15.35% | +15.28% | 69% | -47.15% / +130.78% | +6.08% | +9.27% | +0.44% to +17.22% |

- Mean net (primary) review-cluster bootstrap: 95% -9.68% to -0.20%, one-sided lower bound -8.90%, 7 reviews.
- Account (slots fixed before the auction, each at most 25% of equity and IDR 40m, cash otherwise): IDR 160.0m -> IDR 129.5m (-19.05%), cash stays IDR 160.0m; drawdown at review exits -19.05%; 46 trades over 7 reviews; mean capital deployed per review 86%; P&L without the 3 largest winners IDR -45.4m.
- Account without its best review (Aug25): IDR 127.0m (-20.63%).
- Match levels of scored events (0 = every bucket): {'0': 29, '2': 6, '3': 11}.
- Status counts (primary): {'EXITED': 46, 'SKIP_NOT_TRADED': 2, 'SKIP_ARA_LOCK': 2, 'SKIP_LIQUIDITY': 1}.
- By deletion kind: {"SC_EXIT": {"n": 33, "mean_net": -0.06655396600236764, "mean_excess": 0.009333022754529817}, "ST_EXIT": {"n": 6, "mean_net": 0.03667292270360489, "mean_excess": 0.20731877154165437}, "ST_TO_SC": {"n": 7, "mean_net": 0.007179946280637292, "mean_excess": 0.0758859598792897}}
- By review: {"Feb25": {"n": 6, "mean_net": -0.022969253844449183, "mean_excess": 0.11546908903089396}, "May25": {"n": 3, "mean_net": -0.057039860390321495, "mean_excess": -0.02398322761340685}, "Aug25": {"n": 3, "mean_net": 0.026580814265650288, "mean_excess": -0.02498996493824683}, "Nov25": {"n": 4, "mean_net": 0.020077843726299616, "mean_excess": 0.021162718146537002}, "Feb26": {"n": 3, "mean_net": -0.04062199269926973, "mean_excess": 0.01729175111126985}, "May26": {"n": 16, "mean_net": -0.008289832643592662, "mean_excess": 0.12718932894535212}, "Aug26": {"n": 11, "mean_net": -0.1384181028146582, "mean_excess": -0.05766784057014143}}


## What this does and does not show

- Out of time for this question, but the segment's prices were used by other KOD studies; not pristine.
- Prices after 2025-02-21 come from Yahoo in the pinned panel; closing-auction fills are modelled.
- MSCI's treatment of Indonesia is changing (additions frozen since Jan 2026; reclassification proposed, decision by 30 Jun 2027); a past pattern is not a forecast.
