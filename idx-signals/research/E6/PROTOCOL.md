# E6-PRESSURE-RESPONSE (KOD-CRYPTO-E6-v1)

`protocol.json` is the protocol; this file states it in plain words. Both are frozen in the commit that adds
them, before any outcome is computed. Origin: Astra's "market seismograph" proposal, refined in review.

**Question.** On Binance spot, when selling stops pushing a coin down and buying starts pushing it up, while
trading activity rises and the price is still inside its range, are the next five days better than for
comparable coins? And is that because of the buy/sell split, not just because volume rose?

**Data.** Free hourly candles from the public Binance archive, each file checked against the archive's own
checksum. Every hour carries traded value and the part of it initiated by buyers, so selling-initiated value
is the remainder. Delisted coins are included. Stablecoins and leveraged tokens are excluded. Nothing from
2024 onward is downloaded: that is the sealed holdout.

**The measurement.** For each coin and day, price move per unit of net buying and per unit of net selling,
in the last 7 days and in the 30 days before that. The absorption score is how much buying's impact grew
relative to selling's impact. Positive means the coin got harder to push down and easier to push up.

**Four rules, fixed in advance.**
- **P1, pressure setup, primary:** top 5% absorption that day, activity up at least 1.5 times, still inside
  its 30-day range, not lagging the market over the week.
- **P2, pressure then breakout, primary:** a breakout on rising activity within 10 days after a P1 flag.
- **B0, plain breakout, comparator.**
- **PL, placebo:** P1 computed after scrambling the buy/sell sign of every hour. Volume is unchanged; the
  buy/sell information is destroyed. If the placebo does as well, the edge is volume, not pressure.

**Outcome.** Enter at the 01:00 UTC open after the decision, one hour of processing delay. Five-day return,
the chance of touching +30%, and +30% before −5%, reported with absolute rates. Each flag is compared with
200 coins from the same day of similar liquidity and volatility. Uncertainty is clustered by calendar week
because five-day windows overlap.

**Gate 1, information, before any trade design.** For P1 or P2: at least 200 flags in mid-2020 to 2022,
better than matched coins at p < 0.025, positive in both 2021 and 2022, and better than the placebo.

**Gate 2, execution, only if gate 1 passes.** Buy at the entry, take +30%, stop at −5% or the gap open,
otherwise exit after five days, with 0.1% fees per side and a slippage sensitivity.

**Then.** One provisional validation on 2023. A pass licenses prospective paper scoring only.

**Limits, declared.** Hourly bars only. No order book, so capacity is assumed small. Adjacent weeks still
overlap at their edges. Thresholds are fixed choices, not optimised ones, and a null means "not found with
these rules", not "impossible".

## Data check before the freeze (no outcome read)

Run: `python3 research/E6/data_check.py data/manifests/binance_1h-20261015T182940Z.jsonl`, output in
`data_check/`. 406 coins, 12,032 monthly files, zero download failures, every file matching the archive
checksum. 46 coins were delisted before 2023-12 and are included. No hour has buyer-initiated value above
total value, no price is non-positive, and the median coin misses 0.09% of its hours. Same-hour net flow and
return are positively correlated in all 346 coins with enough history (median 0.27), so the buy/sell split
is real information about price pressure. The most one-sided hours move less than moderately one-sided ones,
consistent with thin hours; the protocol measures flow in traded value, so thin hours carry little weight.
About 250 coins a day pass the liquidity rule; the top 5% before the other filters is about 10,700 coin-days
in discovery, so the 200-flag minimum is feasible.

## Freeze

Frozen in the commit that adds this directory, before any outcome is computed. Nothing after 2023-12 exists
on disk.
