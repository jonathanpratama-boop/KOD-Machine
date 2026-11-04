# Idea parking lot

Created 2026-11-04 under `EARLY_ENTRY_CLOSE_RULE_2026-11-03.md` ("After closing"). New ideas from the owner or any agent
are added here as new rows. Nothing here is running, approved or tested.

## Gate (both must be yes before an idea leaves this list)
1. **New information:** does it use information KOD has never tested? A new framing of price, volume, flow, attention,
   peers or exchange-listing notices is not new information (closed by the rule).
2. **Money decision:** could its result change what the owner does with money, at the owner's real venue, cost and speed?

An idea that passes both still needs a locked protocol opening with the feasibility gate (`docs/PROTOCOL_TEMPLATE.md`).

## Review cadence
Once a month, by the architect, with the owner. First review: **2026-12-04**. Each review adds a dated line to the
review log below; rows are never deleted, only given a new status line.

## Ideas

| # | Idea | Source | New information? | Money decision? | Status (2026-11-04) |
|---|---|---|---|---|---|
| 1 | Bybit / OKX / Coinbase / Kraken listing notices as catalysts | Claude, 2026-11-04 | **No**: same family as BINANCE_ANN_1M and INFO_MAGNET_v0, both failed | — | Excluded by the close rule |
| 2 | Snapshot governance votes (exact times) | Hermes INFO_MAGNET plan | Yes (never tested) | Unclear: votes are scheduled, so the pre-event-preparation route applies, not early entry | Parked |
| 3 | Token-unlock calendar | Hermes INFO_MAGNET plan | Yes | Possibly, as an avoid flag | Parked; free source now paid (DefiLlama) |
| 4 | GitHub developer-activity bursts of crypto projects | Claude, 2026-11-04 | Yes | Unknown | Parked |
| 5 | On-chain large-wallet and exchange-inflow flows (Dune free tier, explorers) | Claude, 2026-11-04 | Partly (flow family failed on daily stablecoin data, SEESAW_v1) | Unknown | Parked |
| 6 | Meta-labeling (a take-or-skip model on detected alerts) | López de Prado, via Claude | No by itself (a method, needs new inputs) | Only with a new information input | Parked; method, not information |
| 7 | Triple-barrier labels, purged cross-validation, deflated Sharpe | López de Prado, via Claude | No (methods) | Improves validity of any future test | Adopt as methods when the next protocol is written |
| 8 | Freqtrade dry-run as the live paper harness | Claude, 2026-11-04 | No (infrastructure) | Indirect | Parked; server timer now covers scheduling |
| 9 | Prefect or Dagster scheduler, supervisor and watchdog | Claude, 2026-11-04 | No (infrastructure) | Indirect | Parked; `ops/kod-watch` covers the immediate need |
| 10 | In-house AI analyst on a schedule (Claude API, sealed calls) | Owner, 2026-11-04 | No (judgment, not information) | Possibly | Parked; LLM_ARM_v1 already collecting (24 of 60 calls at 2026-11-04) |
| 11 | CCXT streaming recorder for within-minute changes | Ace, 2026-11-04 | No | Only if the timing cohort shows within-minute misses | Parked until TIMING_CAPTURE_v1 reports |
| 12 | NautilusTrader / Qlib engines | Ace, 2026-11-04 | No | No evidence yet | Parked |
| 13 | Market map with real sector groups and a "jumping alone" label | Owner idea, Claude, 2026-11-03 | No (peer family, GROUP_FLOW_v1) | As an avoid flag only | Parked |
| 14 | SEC_8K_v1 (filings before moves) | Earlier approved, blocked | Yes for US filings | Possibly | Blocked: needs `KOD_SEC_CONTACT` in the environment |
| 15 | MOVERS_NOW holdout question (sanctioned or breach) | Earlier | — | Record-keeping | Owner decision still open |

## Review log
- 2026-11-04: list created after INFO_MAGNET_v0 failed its primary gate and early-entry research closed.
- 2026-11-04: early-entry research closed (`handoff/decisions/2026-11-04_early_entry_closed.md`). Row 1 (other exchanges' listing notices) is excluded by that closure; INFO_MAGNET showed the listing move happens inside the notice hour.
