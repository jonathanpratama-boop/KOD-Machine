# MAJORS_TREND_v1: result (one look, 2026-11-15 UTC)

**Verdict under the frozen pass mark: INCONCLUSIVE.** At Binance costs since 2023, the 10/40 rule beat holding its own
average exposure on 6 of 8 coins, but the pooled excess (+14.5 points a year, 90% interval -7.5 to +37.4) has a
one-sided p of 0.142, above the 0.05 bar. At eToro costs: 5 of 8 positive, pooled +7.0 points, p 0.316.

| Coin | Exposure | Rule CAGR / Sharpe / MaxDD | Matched CAGR / Sharpe / MaxDD | Excess a year (90% interval) | p |
|---|---:|---|---|---|---:|
| SOL | 52% | +90% / 1.33 / -52% | +54% / 1.18 / -49% | +30.6 (-5.2 to +67.8) | 0.083 |
| BNB | 57% | +20% / 0.64 / -51% | +22% / 0.84 / -38% | +1.9 (-20.0 to +24.3) | 0.440 |
| XRP | 43% | +9% / 0.42 / -66% | +28% / 0.84 / -40% | -8.0 (-47.3 to +36.3) | 0.633 |
| DOGE | 42% | +29% / 0.71 / -63% | +12% / 0.49 / -49% | +27.6 (-13.5 to +72.1) | 0.140 |
| ADA | 42% | +28% / 0.73 / -60% | +8% / 0.40 / -54% | +24.1 (-12.5 to +61.6) | 0.140 |
| AVAX | 45% | +33% / 0.77 / -65% | +10% / 0.44 / -58% | +30.3 (-9.0 to +70.6) | 0.101 |
| LINK | 51% | +34% / 0.78 / -53% | +23% / 0.71 / -46% | +17.4 (-14.1 to +49.3) | 0.182 |
| LTC | 49% | -11% / 0.06 / -70% | +5% / 0.32 / -41% | -7.5 (-35.7 to +21.0) | 0.663 |

Binance costs, 2023-01-01 to 2026-09-29. Whole pinned history (reported only): all 8 coins positive, 5 with p below 0.05.

Reading: the direction agrees with ETH (trend beat matched holding on most coins) but the size is not distinguishable
from luck on the 2023+ window, and the rule's worst fall was deeper than the matched benchmark's on 7 of 8 coins.
Consequence fixed in the protocol: keep the existing ETH paper log only; no new trend work.

Inputs: 743 monthly archives, every sha256 matched the FRESH_EYES_v1 pin. Code: `run_majors.py`, `fetch_pinned.py`.
Full figures: `results/result.json`.
