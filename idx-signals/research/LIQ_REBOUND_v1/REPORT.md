# LIQ_REBOUND_v1: buying BTC/ETH spot after forced-deleveraging cascades

Ran 2026-10-31T23:06:31Z at commit `ae6a42994667698e6d0fee65ac7b6c0c9a6f53e4` on the frozen protocol (PROTOCOL.md, protocol.json). One run. Simulation only, development data only (no row dated 2024-01-01 or later).

## Verdict: FAIL

| Gate | Result |
|---|---|
| G0_sample | PASS |
| G1_net_edge | FAIL |
| G2_timing | FAIL |
| G3_mechanism | FAIL |
| G4_account | FAIL |
| G5_stress | FAIL |
| G6_screen_2023 | FAIL |

## Discovery (signals 2020-09-01..2022-12-31)

| Account | End equity | Net return | CAGR | Max drawdown | Mean exposure | Turnover / yr | Trades | Win rate | Mean / median trade | Worst trade | P&L w/o top 3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 maker, licensed IDR exchange | 7,817 | -21.83% | -10.02% | -32.73% | 3.8% | 9.8x | 23 | 43% | -1.74% / -2.02% | -20.77% | -4,726 |
| A2 base, market orders | 7,552 | -24.48% | -11.34% | -34.50% | 3.8% | 9.7x | 23 | 39% | -2.03% / -2.32% | -21.01% | -4,912 |
| A3 eToro real crypto (reported only) | 5,682 | -43.18% | -21.52% | -49.39% | 3.8% | 9.4x | 23 | 26% | -4.45% / -4.73% | -22.96% | -6,193 |
| S1 stress: entry 4h after signal | 8,201 | -17.99% | -8.15% | -32.86% | 3.9% | 9.8x | 23 | 39% | -1.46% / -2.38% | -21.50% | -4,203 |
| S2 stress: doubled slippage | 7,381 | -26.19% | -12.21% | -35.75% | 3.8% | 9.7x | 23 | 35% | -2.23% / -2.51% | -21.17% | -5,032 |
| Cash | 10,000 | +0.00% | +0.00% | 0.00% | 0% | 0 | 0 | | | | |
| Buy-and-hold BTC/ETH 50/50 (A2 costs) | 20,714 | +107.14% | | -78.81% | 100% | | | | | | |

- Episodes (7-day gap): 18. Mean net trade (A2) -2.03%; episode-cluster bootstrap 95% interval -7.16% to +2.82%, one-sided 95% lower bound -6.48%.
- Random-entry placebo (same coins and counts, 2000 draws): median -0.99%, 90th percentile +0.88%; matched unconditional mean of a 72h hold -1.03%.
- Mechanism: cascade trades 23 (mean gross -1.21%, net A2 -2.03%) vs control (drop-only, no recent cascade) trades 59 (mean gross -0.58%, net A2 -1.40%).
- Missed-fill stress (each entry fails with p = 0.3, 500 draws): median end equity 8,229, 5th percentile 6,813, share above start 5%.
- A2 exits: {'TIME': 20, 'STOP_AT_LOW': 3}; skips and events: {}; CVaR 95% of trades -20.95%; best trade +22.02%.
- By coin: {"BTCUSDT": {"trades": 16, "mean_net": -0.0253259053336045, "pnl": -2108.814538862428}, "ETHUSDT": {"trades": 7, "mean_net": -0.008831150420361866, "pnl": -338.779236506261}}
- By year: {"2021": {"trades": 8, "mean_net": 0.030140398755155146, "pnl": 1195.106620454525}, "2022": {"trades": 15, "mean_net": -0.04721038188809642, "pnl": -3642.700395823214}}

## 2023 provisional screen (an already-used year)

| Account | End equity | Net return | CAGR | Max drawdown | Mean exposure | Turnover / yr | Trades | Win rate | Mean / median trade | Worst trade | P&L w/o top 3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 maker, licensed IDR exchange | 9,764 | -2.36% | -2.36% | -14.21% | 6.2% | 15.0x | 15 | 27% | -0.24% / -1.34% | -7.12% | -1,312 |
| A2 base, market orders | 9,547 | -4.53% | -4.53% | -15.48% | 6.2% | 15.0x | 15 | 27% | -0.54% / -1.63% | -7.40% | -1,478 |
| A3 eToro real crypto (reported only) | 7,929 | -20.71% | -20.72% | -25.62% | 6.1% | 15.0x | 15 | 20% | -3.00% / -4.06% | -9.69% | -2,685 |
| S1 stress: entry 4h after signal | 9,835 | -1.65% | -1.66% | -15.94% | 6.2% | 15.0x | 15 | 33% | -0.14% / -1.40% | -6.92% | -1,299 |
| S2 stress: doubled slippage | 9,405 | -5.95% | -5.96% | -16.36% | 6.2% | 15.0x | 15 | 27% | -0.74% / -1.83% | -7.59% | -1,586 |
| Cash | 10,000 | +0.00% | +0.00% | 0.00% | 0% | 0 | 0 | | | | |
| Buy-and-hold BTC/ETH 50/50 (A2 costs) | 22,135 | +121.35% | | -23.13% | 100% | | | | | | |

- Episodes (7-day gap): 11. Mean net trade (A2) -0.54%; episode-cluster bootstrap 95% interval -3.00% to +2.39%, one-sided 95% lower bound -2.69%.
- Random-entry placebo (same coins and counts, 2000 draws): median -0.19%, 90th percentile +1.21%; matched unconditional mean of a 72h hold -0.13%.
- Mechanism: cascade trades 15 (mean gross +0.29%, net A2 -0.54%) vs control (drop-only, no recent cascade) trades 34 (mean gross +1.44%, net A2 +0.60%).
- Missed-fill stress (each entry fails with p = 0.3, 500 draws): median end equity 9,705, 5th percentile 9,075, share above start 21%.
- A2 exits: {'TIME': 15}; skips and events: {}; CVaR 95% of trades -7.40%; best trade +12.11%.
- By coin: {"BTCUSDT": {"trades": 5, "mean_net": 0.000521017353591513, "pnl": 6.81581475549865}, "ETHUSDT": {"trades": 10, "mean_net": -0.00842940399678036, "pnl": -459.95196513126757}}
- By year: {"2023": {"trades": 15, "mean_net": -0.005445930213323069, "pnl": -453.1361503757689}}

## What this does and does not show

- Development data only; KOD and the literature have looked at these years. A pass would be a candidate for validation, never proof; a fail ends this rule (no retune).
- Binance USDT prices stand in for IDR exchange fills; the IDR basis during cascades is unmeasured.
- Open-interest files were regenerated by the archive (2026-03-18) and are not guaranteed point-in-time.
- A live open-interest source reachable from Indonesia is not yet verified.
- eToro counts only for positions tagged as real crypto at 1x; at its standard-tier costs (A3) the rule's economics are shown above.
