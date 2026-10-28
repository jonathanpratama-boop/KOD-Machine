# Decision 2026-10-26 (owner): research markets are US stocks, crypto and eToro's larger non-US stock exchanges

Owner's words: "Do us stocks crypto and other good country stocks." Asked just before: "Why Indonesian stocks? ...
There are so many in the world."

Why the machine was on IDX: it began on 2026-10-07 as an IDX harness, US and crypto were added on 2026-10-08, and the
broker (eToro, which lists no Indonesian stocks) surfaced on 2026-10-16.

Applied:

1. **IDX is no longer a research target.** The pre-registered consequence of LEAD_LADDER_v1 (validate the IDX
   slow-up youngest-listings cell on 2023 as counted test 29) is not run, by this decision; it is recorded here, not
   silently dropped. The IDX daily paper scan is unchanged (a descriptive log; the owner can switch it off).
2. **Markets of record:** US stocks, crypto, and the nine non-US exchanges where eToro lists at least 200 stocks
   (snapshot `etoro_instruments-20261016T190421Z`): London 726, Xetra 477, Paris 455, ASX 413, Stockholm 391,
   Oslo 273, Hong Kong 245, Tokyo 227, Milan 200. The universe in each is the stocks eToro lists, because that is
   what the owner can trade.
3. **Next test:** `idx-signals/research/LEAD_LADDER_INTL_v1/` (counted test 29): does what LEAD_LADDER_v1 found in US
   and crypto appear in those nine markets? Protocol committed before any of their prices is fetched.

Not changed: no real order, no sealed holdout, no change to the frozen paper cycle.
