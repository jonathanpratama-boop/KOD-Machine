# Feasibility and scope

Owner instruction on 2026-11-08: “can we try combining it and see if it produces anything meaningful?”
This authorizes one frozen model comparison, following the discussion of a 24-hour continuation filter.
It is a narrow exception to the earlier price-entry closure, not a reopening of its other hypotheses.

| Gate | Assessment |
|---|---|
| Execution proxy | Binance USDT spot hourly open; one full hour allowed after the completed trigger candle, then a 24-hour hold. 2% round-trip owner cost assumption. Exchange prices are proxies; eToro instrument availability, spreads and fills are unverified. |
| Prior evidence | ENTRY_TIMING, IGNITION and HERMES_NOV3_REPRO_v1 did not establish a profitable entry strategy. The old late-entry/negative-net-result findings motivate a rejection filter rather than a claim that price-model sophistication creates an edge. |
| Decision value | Determine whether this pretrained model merits a separately approved, frozen prospective challenger study. No result authorizes live trades or changes the 30-day cloud study. |
| New information | No new information family: existing completed OHLCVA candles. The change is the pretrained model, explicitly requested by the owner. |
| Compute | CPU inference in an isolated workspace; measured runtime and process peak memory retained. The 1 GB market-data server is not the test runner. |

GO for an exploratory software/model comparison under that specific instruction. Historical source event inclusion
required future 72-hour data availability and its results were already examined. Neither this source cohort nor
this benchmark is an untouched or survivorship-free prospective evaluation.
