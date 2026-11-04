# E7 data-feasibility specification (written and committed before any collection or count)

**Scope.** Feasibility only. The question for a later protocol is whether Binance USDT-margined perpetual
data, funding and open interest, helps predict a tradable opportunity in the SPOT pair. Perpetuals are an
information source only; they are not traded. This stage counts events and measures unconditional spot
volatility for sample planning. It computes no return conditional on any signal, tunes nothing, and runs no
performance test. Validation (2023) and holdout (2024+) data are not downloaded; 2023 is inspected only
through archive file listings.

## 1. Data, units, timestamps, availability

| Source | Archive path | Fields used | Units | Timestamp meaning |
|---|---|---|---|---|
| Funding | `data/futures/um/monthly/fundingRate/<SYM>/` | `calc_time`, `funding_interval_hours`, `last_funding_rate` | rate per interval, decimal | `calc_time` = settlement time in ms UTC (observed a few ms after the hour) |
| Open interest | `data/futures/um/daily/metrics/<SYM>/` | `create_time`, `sum_open_interest` | contracts = coins (base units) | `create_time` = 5-minute snapshot time, UTC, no zone suffix |
| Spot price and liquidity | E6 manifest `binance_1h-20261015T182940Z.jsonl` | hourly OHLC, quote volume | USDT | bar open time |

- **Archive timestamp versus historical availability.** The archive records when a value applies, not when
  it was first published. Funding at a settlement is realised at that time; the live API exposed a predicted
  rate before it, which is not in the archive and is not used. An open-interest snapshot labelled t is
  assumed available within minutes, but its historical publication latency is **unverified**. Mitigation:
  the signal uses only funding settled at or before T and the last OI snapshot at or before T − 5 minutes,
  and entry is at least one hour after T. Any claim beyond that is marked unverified.
- **Coverage, listing and delisting.** A perp's listing and delisting dates are inferred from its first and
  last archive files. That is archive-derived, not an exchange record, and is reported as such. Delisted
  perps are included. Every file is checked against its `.CHECKSUM`.
- **Gaps.** A metrics day with fewer than 288 snapshots, or a missing day, is counted per coin and month.
  Funding intervals other than 8 hours are counted.
- **OI in coin units**, not USD value, so a price rise does not mechanically raise OI.
- **Discovery window for counts: 2021-12-01 to 2022-12-31.** Metrics for most altcoins start 2021-12-01.
  Funding and spot are read only within this window plus the look-back each rule needs. 2023 files are
  listed, never downloaded.

## 2. Candidate setup and comparator, fixed before counting

Negative funding with rising OI is a **candidate setup**, not evidence that shorts are crowded or will cover.

Observation unit: a perp's funding settlement time T, for a perp whose spot pair is in the E6 universe.

- **Spot eligibility at T** (information before T only): the spot pair's last 30 completed UTC days have a
  median daily quote volume ≥ 200,000 USDT, at least 60 complete days of spot history exist, and the spot
  hourly bar ending at T exists.
- **Eligible observation:** spot eligible, and funding at T and its two previous settlements exist, and an
  OI snapshot exists within 30 minutes before T and within 30 minutes before T − 7 days.
- **F (funding-only comparator):** the settled funding rates at T and the two previous settlements are all
  < 0.
- **S (primary candidate):** F, and OI(T) / OI(T − 7 days) ≥ 1.20, and the spot close of the hourly bar
  ending at T ≥ the spot close of the bar ending at T − 72 hours.
- **Debounce:** per coin and per rule, an event at T blocks events for the next 72 hours.
- These definitions are final for counting. No threshold is changed after counts are seen.

The comparator tests whether OI growth and price resilience add information beyond negative funding: S ⊂ F,
and "S minus F-without-S" is the planned contrast. **Control draws are not independent coins.** A later
protocol may draw many controls, but the number of distinct eligible contracts at each settlement bounds the
information they carry; that number is reported here.

## 3. Sample planning, discovery data only

Unconditional quantities over eligible observations, never conditional on S or F:

- σ: standard deviation of 24-hour spot excess return (coin return minus that settlement's cross-sectional
  median over eligible coins), entry at the open of the bar starting T + 1 hour.
- ρ: average same-week correlation of those excess returns between different observations, as a dependence
  input. **E6's clustering factor is not transferred.**
- Events per week, for the design effect DE = 1 + (m − 1) ρ, with m events per weekly cluster.

Required events n = ((1.96 + 0.84) × σ / δ)² × DE, for δ in {0.25%, 0.5%, 1%, 2%}, σ at the measured value
and 1.5 times it (event coins may be more volatile), and DE at 1, the measured value, 2 and 3.

## 4. Spot execution model for the later protocol (fixed now, not run now)

- Entry at the open of the spot hourly bar starting T + 1 hour; exit at the close of the 24th bar.
- Capacity: position ≤ 1% of the median hourly spot quote volume over the 24 hours ending at T. Its
  distribution over eligible observations is reported.
- Costs: 0.1% per side, plus a 0.1% per side slippage sensitivity.
- Missing entry bar: no trade, counted. Missing later bars or delisting: exit at the last available close in
  the window, counted.

## 5. GO / PAUSE rule, fixed before counting

- **Coverage:** at least 100 perps with spot pairs, funding and metrics in the discovery window, each with at
  least 80% of expected metrics snapshots.
- **Sample:** primary S events after debounce ≥ the required n for δ = 1.0% at measured σ and measured DE.
- **Spread:** events in at least 10 of the 13 months, and the top 5 coins ≤ 40% of S events.
- **GO** if all three hold; **GO-LIMITED** if coverage and spread hold but n only covers δ ≥ 2%, with the
  minimum detectable effect stated; **PAUSE** otherwise, with the failing criterion named.
