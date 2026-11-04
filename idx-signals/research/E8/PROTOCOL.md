# E8 protocol (KOD-CRYPTO-E8-v1), frozen before any outcome

`protocol.json` is the binding text; this page restates it.

**Question.** When a coin reprices on its own (up 25% in a day, 20 points above the market, on
three times its usual volume), do its closely linked coins that have **not** moved yet go on to
outperform similar coins that are not linked? And can a fixed, costed trade capture that?

**Population.** Binance spot USDT coins, July 2020 to December 2022, delisted coins included,
at least $1M median daily volume, 60 days of history. 2023 and later are never read.

**Warning.** Up to 3 coins per leader with a partial correlation of at least 0.20 to the leader
over the 30 days before its move, and a 24-hour move no more than 5 points above the market.
Feasibility v1.1 counted 1,206 such events in 116 weeks, 266 distinct coins.

**Measures.** 72-hour return from the next hourly open (gross). "Moonshot" means the high reaches
+20% (U20, gated) or +30% (U30, reported) within those 72 hours.

**Fair comparison.** For each warning, 200 draws from coins at the same hour that pass the same
filters, are not linked to that leader (partial correlation below 0.10), and share its liquidity
and volatility quintiles. Same entry bar, same measures.

**Trade.** Buy at the next open. Take profit +20%, stop -10%, otherwise sell at the 72-hour close.
Stop assumed first when both are touched in one bar; gaps through the stop fill at the open.
Costs: 0.10% fee per side plus 0.10% (coins trading $10M+ a day) or 0.20% slippage per side,
so 0.4% to 0.6% per round trip. Reported: win rate (Wilson 95%), mean, median, mean win, mean
loss, worst 1%, worst trade, maximum concurrent positions, maximum drawdown at 5% of capital per
trade, and typical capacity at 1% of hourly volume.

**Pass rules (all required).** G0 at least 300 scored events in 50 weeks. G1 72-hour excess over
controls > 0 at one-sided p < 0.025 (week-cluster bootstrap). G2 more +20% moonshots than controls
at p < 0.025. G3 the trade's mean net return > 0 at p < 0.05 and above the same trade on controls.
G4 excess > 0 in 2021 and in 2022 separately. G5 excess > 0 without the two busiest weeks.
G0 failing is **inconclusive**; any other gate failing is a **fail**. A "high win rate" label
needs a pass plus a win-rate lower bound above 50%.

**After the result.** A fail is recorded and E8 stops, with nothing retuned. A pass is
discovery-only and can only be confirmed by prospective paper tracking, because no unused
historical crypto data remains.
