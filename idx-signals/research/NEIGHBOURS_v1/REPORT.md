# NEIGHBOURS_v1: result (run once, 2026-11-03)

**Neighbours add no information. Next stop adds no information.** Walk-forward 2021-2026, 482,598 coin-days, Binance USDT spot.

## Information (mean daily rank correlation between prediction and realised return; higher is better)

| Horizon | A own information | B + neighbours | C + next stop | B minus A (95% range) | C minus B (95% range) |
|---|---:|---:|---:|---|---|
| 3 days (primary) | 0.054 | 0.049 | 0.049 | -0.005 (-0.010 .. -0.001) | -0.000 (-0.004 .. +0.003) |
| 1 day | 0.059 | 0.053 | 0.053 | -0.005 (-0.009 .. -0.002) | -0.001 (-0.003 .. +0.002) |
| 5 days | 0.051 | 0.047 | 0.048 | -0.004 (-0.010 .. +0.001) | +0.001 (-0.003 .. +0.005) |

Adding peer information made the ranking slightly worse; the station "next stop" signals changed nothing. B beat A in 2 of 6
years and C beat B in 2 of 6 (the locked bar was 4).

## Decisions (top 5 every 3rd day, held 3 days; mean per pick)

| Picks | Gross | Net at 0.4% round trip | Net at eToro 2% |
|---|---:|---:|---:|
| A | +0.41% | +0.01% | -1.59% |
| B | +0.33% | -0.07% | -1.67% |
| C | +0.36% | -0.04% | -1.64% |
| Random 5 | +0.28% | -0.12% | -1.72% |
| All eligible | +0.28% | -0.12% | -1.72% |
| Already-strong group | +0.69% | +0.29% | -1.31% |

"Already-strong group" was best on average but not steady: 2021 +3.9%, 2022 -1.4%, 2023 +1.7%, 2024 +0.4%, 2025 -0.5%,
2026 -0.2% gross. Nothing is profitable at eToro's costs.

## Post-run (not part of the verdict): where model A's ranking skill comes from
Single-feature daily rank correlations with the 3-day return, 2021-2026: 20-day volatility -0.088 (every year, strongest in
2025-26 at -0.12); 3-, 7- and 20-day own return about -0.05 (recent winners lag; fading in 2025-26); volume surge -0.037; peer
participation -0.017. In plain words: calm coins beat wild ones, and recent pumps give back, over the next few days. This repeats
KOD's avoid-side findings (AVOID_TILT, "recent spikers keep falling") in crypto at a 3-day horizon. It is a ranking effect
across coins; the top-5 long-only picks capture little of it.

## Limits
2023-2026 already inspected by earlier studies; Binance-removed pairs missing; daily bars; one fixed ridge setting.
