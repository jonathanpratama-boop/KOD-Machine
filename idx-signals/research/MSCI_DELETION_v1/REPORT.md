# MSCI_DELETION_v1: buying MSCI Indonesia deletions in the trackers' closing auction

Ran 2026-11-01T00:19:01Z at commit `a24746f2eb28ec8474eda656ceca42bd49ffcdcd` on the frozen protocol. One run. Simulation only; IDX data to 2023-12-29 (the sealed holdout 2024-01-02..2025-02-21 was not read).

## Verdict: PROMISING

| Gate | Result |
|---|---|
| G0_sample | PASS |
| G1_net_edge | PASS |
| G2_vs_matched_controls | PASS |
| G3_account | PASS |
| G4_stress | PASS |
| G5_screen_2023 | PASS |

## Discovery (reviews Nov 2019 .. Nov 2022)

| Variant | Scored | Mean net | Median net | Win rate | Worst / best | Mean matched control | Mean excess | Excess 95% (review clusters) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Primary: buy the implementation close, hold 20 | 40 | +14.02% | +5.33% | 68% | -10.59% / +104.98% | +2.91% | +11.10% | +0.93% to +17.74% |
| S1: buy one session later | 40 | +11.17% | +2.44% | 62% | -15.72% / +100.49% | +1.45% | +9.72% | +0.29% to +15.87% |
| S2: one tick per side added | 40 | +12.66% | +4.24% | 60% | -12.68% / +100.62% | +1.70% | +10.96% | +0.96% to +17.45% |
| Descriptive: hold 5 | 40 | +14.82% | +8.01% | 78% | -7.35% / +94.87% | +4.80% | +10.01% | +1.18% to +16.88% |
| Descriptive: hold 60 | 40 | +19.97% | +10.37% | 65% | -42.75% / +110.61% | +14.63% | +5.33% | -6.41% to +11.95% |

- Mean net (primary) review-cluster bootstrap: 95% -0.15% to +22.24%, one-sided lower bound +1.42%, 8 reviews.
- Account (slots fixed before the auction, each at most 25% of equity and IDR 40m, cash otherwise): IDR 160.0m -> IDR 262.8m (+64.26%), cash stays IDR 160.0m; drawdown at review exits -4.18%; 40 trades over 8 reviews; mean capital deployed per review 62%; P&L without the 3 largest winners IDR 42.2m.
- Account without its best review (May20): IDR 215.1m (+34.41%).
- Match levels of scored events (0 = every bucket): {'0': 8, '1': 1, '2': 5, '3': 15, '4': 9, '5': 2}.
- Status counts (primary): {'EXITED': 40, 'SKIP_LIQUIDITY': 5, 'SKIP_NOT_TRADED': 1}.
- By deletion kind: {"SC_EXIT": {"n": 25, "mean_net": 0.160755386638205, "mean_excess": 0.1364356673791538}, "ST_EXIT": {"n": 3, "mean_net": 0.006462493199894337, "mean_excess": 0.004841737518102257}, "ST_TO_SC": {"n": 12, "mean_net": 0.1307329731064474, "mean_excess": 0.08464976352995356}}
- By review: {"Nov19": {"n": 3, "mean_net": 0.20052587996674984, "mean_excess": 0.18350291914285488}, "May20": {"n": 16, "mean_net": 0.26023938217018694, "mean_excess": 0.21143445850059694}, "Nov20": {"n": 5, "mean_net": 0.21035956576877873, "mean_excess": 0.0661265006209607}, "Feb21": {"n": 1, "mean_net": 0.0058027712529566955, "mean_excess": 0.029034030295874015}, "May21": {"n": 3, "mean_net": -0.011488999424360657, "mean_excess": -0.00835787574362148}, "Nov21": {"n": 3, "mean_net": -0.022626404222947927, "mean_excess": -0.013299240605136056}, "May22": {"n": 3, "mean_net": 0.05775499424706628, "mean_excess": 0.11152470430950277}, "Nov22": {"n": 6, "mean_net": -0.04780988394786454, "mean_excess": -0.02025255522140579}}

## 2023 provisional screen (an already-used year)

| Variant | Scored | Mean net | Median net | Win rate | Worst / best | Mean matched control | Mean excess | Excess 95% (review clusters) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Primary: buy the implementation close, hold 20 | 7 | +8.90% | -1.19% | 43% | -8.28% / +68.99% | +0.21% | +8.69% | -4.68% to +20.37% |
| S1: buy one session later | 7 | +3.66% | -3.97% | 43% | -10.40% / +39.98% | +0.58% | +3.07% | -8.02% to +13.39% |
| S2: one tick per side added | 7 | +7.72% | -1.98% | 43% | -9.35% / +66.81% | -1.06% | +8.79% | -4.23% to +20.62% |
| Descriptive: hold 5 | 13 | +1.64% | -0.40% | 46% | -12.52% / +28.17% | +0.11% | +1.53% | -1.31% to +5.43% |
| Descriptive: hold 60 | 7 | +0.33% | -9.57% | 43% | -13.98% / +17.71% | -2.20% | +2.53% | -12.09% to +18.65% |

- Mean net (primary) review-cluster bootstrap: 95% -3.06% to +19.69%, one-sided lower bound -0.48%, 3 reviews.
- Account (slots fixed before the auction, each at most 25% of equity and IDR 40m, cash otherwise): IDR 160.0m -> IDR 184.9m (+15.54%), cash stays IDR 160.0m; drawdown at review exits -1.53%; 7 trades over 4 reviews; mean capital deployed per review 58%; P&L without the 3 largest winners IDR -6.4m.
- Account without its best review (Aug23): IDR 161.2m (+0.77%).
- Match levels of scored events (0 = every bucket): {'0': 1, '2': 2, '3': 2, '5': 2}.
- Status counts (primary): {'EXITED': 7, 'INCOMPLETE': 6, 'SKIP_NOT_TRADED': 1}.
- By deletion kind: {"SC_EXIT": {"n": 6, "mean_net": 0.1058576683505254, "mean_excess": 0.0917070972193555}, "ST_EXIT": {"n": 1, "mean_net": -0.011930311703759133, "mean_excess": 0.05821461423498728}}
- By review: {"Feb23": {"n": 2, "mean_net": -0.03059866014090057, "mean_excess": 0.0454611224677717}, "May23": {"n": 2, "mean_net": 0.04681235722174315, "mean_excess": -0.04677596931226183}, "Aug23": {"n": 3, "mean_net": 0.19692943474590272, "mean_excess": 0.20369563041336683}}

## What this does and does not show

- Development data with 8 discovery reviews; May 2020 (after the COVID low) holds 20 of 46 events. Matched controls bought at the same close absorb market moves.
- Closing-auction fills are the harness's model (decision-time capacity, 10% participation), not observed fills.
- Between-review MSCI changes are not included. Forward relevance depends on MSCI's treatment of Indonesia (additions frozen since Jan 2026; reclassification proposed, decision by 30 Jun 2027) and on the IDX short-selling restart.
