# PRESSURE_v1: result (run once, 2026-11-03)

**No incremental value.** Adding taker-buy pressure to KOD's own information made the 3-day ranking slightly worse.
See RESULT.json for the numbers by horizon and year.

- P minus A daily rank correlation is negative at 1, 3 and 5 days, with 95% ranges below zero; P's top 5 beat A's in 2 of 6 years
  (bar: 4).
- On its own, urgent buying points the wrong way for a buyer: a higher taker-buy share on the day (tb1) and over 5 days (tb5) came
  before slightly worse 3-day returns (about -0.01 rank correlation), most clearly in 2021-2024. Pressure relative to liquidity
  (tbz) was near zero and changed sign between years.
- Reading: aggressive buying at the daily scale is the crowd arriving, and like price spikes it tends to be faded, not followed.
  Order-flow effects in the literature work at seconds-to-minutes; daily aggregates don't carry them to a 3-day trade.
- Nothing is profitable at eToro costs (A -1.6%, P -1.7% per pick).
- Limits: 2023-2026 already inspected; 82 archive files failed; coins without taker data that day were set neutral.
