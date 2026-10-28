# E7-SQUEEZE-SPOT (KOD-CRYPTO-E7-v1) — DRAFT for review, not frozen

Built on the feasibility stage (`FEASIBILITY_SPEC.md` 6a2ba8f, `FEASIBILITY.json`). No discovery outcome has
been computed. Freezing requires the owner's go; nothing below may change after any outcome is seen.

**Question.** Does a negative-funding, rising-OI, price-holding setup on a Binance USDT-margined perpetual
predict the next 24 hours of the SPOT pair, beyond matched coins and beyond negative funding alone?
Perpetuals are an information source only.

**Data.** Spot hourly bars (E6 manifest `binance_1h-20261015T182940Z`), funding and 5-minute open interest
(`binance_perp-20261015T191341Z`), all checksum-verified. Discovery 2021-12-01 to 2022-12-30 (signal times).
Validation 2023 once, after a separate freeze, provisional. Holdout 2024+ never. OI publication latency is
unverified; mitigated by using snapshots at or before T − 5 minutes and entering at T + 1 hour.

**Universe.** Perps whose spot pair is in the E6 universe, delisted included, with spot eligibility at T:
30-day median daily quote ≥ 200,000 USDT, ≥ 60 complete days, spot bar ending at T present. Feasibility:
142 perps covered, about 131 distinct eligible contracts per settlement.

**Arms, exactly as in the feasibility specification.**
- **S, primary:** last three settled funding rates < 0; OI(T − 5 min) / OI(T − 7 d − 5 min) ≥ 1.20 in coin
  units; spot close at T ≥ spot close at T − 72 h. Debounce 72 h per coin. Feasibility: 845 events.
- **F, comparator:** last three settled funding rates < 0, same eligibility and debounce. 5,048 events.
- **F-only:** F events that are not S events; the contrast S minus F-only isolates OI growth and price holding.

**Outcome.** 24-hour spot return from the open of the bar starting T + 1 h to the close of the 24th bar.
Excess = outcome minus the mean of 200 draws from coins eligible at the same settlement hour in the same
liquidity and volatility quintiles, relaxed to liquidity alone below 5 coins. The number of distinct
contracts behind each flag's draws is reported, because draws are not independent coins.

**Gate (one primary arm, one outcome).**
1. At least 500 S events in discovery.
2. Mean excess of S > 0 with one-sided p < 0.025, week-cluster bootstrap, 10,000 resamples.
3. S minus F-only > 0 with p < 0.05, same bootstrap with weeks paired.
4. Mean excess > 0 in both halves: 2021-12..2022-06 and 2022-07..2022-12.
5. Sensitivity, reported and required to keep the sign: month-cluster bootstrap, and dropping the two
   weeks with the most events, because events bunch into stress weeks (up to 70 in one week).

**Decisions.** Pass: Stage 2 on spot only, entry and exit as above, 0.1% fee per side plus 0.1% per side
slippage sensitivity, capacity 1% of the median hourly quote over the 24 hours before T; admissible only with
positive net mean, positive net excess at p < 0.025 and positive halves. Fail with ≥ 500 events: stop the
family. Fewer events or an interval spanning both 0 and 0.5%: insufficient evidence, no extension.

**Power.** Unconditional 24-hour excess SD 4.06%; measured same-week correlation 0.003, design effect 1.04.

| Assumption | Events needed for 0.5% | For 1.0% |
|---|---|---|
| Measured SD, measured dependence | 537 | 135 |
| Measured SD, design effect 2 | 1,035 | 259 |
| SD × 1.5, design effect 2 | 2,327 | 582 |
| SD × 1.5, design effect 3 | 3,491 | 873 |

With 845 events the minimum detectable effect is about 0.4% under measured inputs and about 1.0% under the
pessimistic row. Event coins may be more volatile and stress weeks more correlated than the unconditional
estimates, so the pessimistic rows are the planning case.

**Known limits.** Capacity is small: median 1% capacity about 3,600 USDT per trade, lower quartile about
1,500. One bear-market year, with clustered stress episodes (May–June 2022, November 2022). Listing dates
are archive-derived. Funding intervals other than 8 hours occurred 182 times.

**Budget and stop.** About two days of implementation and synthetic tests, one discovery run, no re-tuning.
