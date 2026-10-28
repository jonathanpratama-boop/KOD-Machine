# MOVERS_NOW_v1: result of the check (run once, 2026-10-27)

**Neither rule held up** in the check window (signals 2026-04-01 .. 2026-09-08, IDX harness, hold 20, buy next close, fees included).

| rule | trades | mean net | median net | vs any similar-size stock (B) | B week-cluster t | +30% at exit | -20% or worse |
|---|---|---|---|---|---|---|---|
| R1 momentum (learn 2025-01 .. 2026-03) | 936 | +5.0% | -1.6% | +2.7% | 2.39 | 14.3% | 13.0% |
| R1 momentum (check) | 237 | -2.9% | -5.6% | +0.7% | 0.34 | 7.6% | 20.3% |
| R2 dilution news before the move (check) | 37 | -10.2% | -8.1% | -5.5% | -2.56 | 5.4% | 37.8% |

## Reading
- R1 is momentum. In the learn window most of its edge came from a few huge winners in rising months of 2025; in the weaker 2026 market it lost money
  outright and was no better than a random stock of the same size. It is not an early catcher: it buys names already up 15% or more.
- R2 flipped sign. In 2025, rights-issue and private-placement news on a quiet stock was followed by more rises than falls (85 name-months, rows only);
  in April-September 2026 the same setup was followed by falls (-5.5% against random, t -2.56, 37 trades). The direction of these stories depended
  on the market phase, which matches IDX_DILUTION_v1's negative result in 2023.
- Across 2025-2026, no sign built from daily prices, volume or headline words separated future 30% rises from 23% falls in the US or crypto;
  in IDX the two candidates that did in 2025 failed in 2026. The month-to-month rate of 30% rises moved far more with the market phase than with any
  single-stock sign, and the data hold only a few phase changes, too few to learn when a phase starts or ends.
- Limits: Yahoo-era IDX prices (after 2025-02-21) with weak corporate-action coverage; survivor-only; headline tagging from URL words, not article text.
