# Edge search 2026-10-31 .. 2026-11-01: verdict (owner's request: "find and test a credible source of trading profit")

Constraints followed: simulation only; unleveraged spot buying, cash allowed (owner's addition of 2026-10-31); no
shorting, perpetual carry, margin or option selling; no paid data, credentials, deployment or real orders; frozen
protocols before any outcome; previously inspected data treated as development data; no sealed dataset opened.
Ace's funding-carry and execution work was not duplicated.

## What was tested (every attempt, in order)

| # | Study | Mechanism (who pays) | Data | Verdict |
|---|---|---|---|---|
| 1 | `research/LIQ_REBOUND_v1` | Liquidity provision to forced deleveraging: buy BTC/ETH spot 1h after a 24h drop with a coin-unit open-interest collapse, hold 72h (liquidated leveraged traders) | Binance spot 1h + 5-min OI, 2020-09..2022-12, 2023 screen | **FAIL**, independently re-derived from raw data: 23 trades, -2.0% per trade net, account -24.5% vs cash; worse than random entries and than drops without an OI collapse |
| 2 | `research/MSCI_DELETION_v1` | Liquidity provision to index trackers: buy MSCI Indonesia deletions in the implementation-day closing auction, hold 20 sessions (passive funds forced to sell) | MSCI's own lists + KOD's IDX harness, Nov 2019..Nov 2022, 2023 screen | **PROMISING** on development data, independently confirmed (prices match Yahoo on 3,001 ticker-days): +14.0% per trade, +11.1% over matched controls, account IDR 160m -> 262.8m; but one regime (2019-2020 reviews +24%; 2021-22 about zero) |
| 3 | `research/MSCI_DELETION_OOT_v1` | The same frozen rule, unchanged, on the reviews after the sealed IDX holdout | Feb 2025..Aug 2026 (unsealed segment, never used for this question) | **NOT_CONFIRMED**: 46 trades, -4.2% per trade net (28% winners), account IDR 160m -> 129.5m (-19%) vs cash; excess over controls +4.5% (95% -3.6% to +10.6%) because the controls fell -8.7% |

Considered and not run (reasons recorded in each study's PROTOCOL.md): crypto option volatility-risk-premium selling
(owner's spot-only rule), token-unlock shorts (shorting; data paywalled), turn-of-month and pre-FOMC index timing (weak
recent evidence, no verified spot-ETF venue, holdout breached by a sub-agent: see
`2026-10-31_holdout_breach_by_research_agent.md`), crypto time-series trend (weak post-2018 evidence, too few switches to
test, price-only signals that E5's decision stopped).

## What passed, what failed, what is unknown

- **Passed:** the engineering. Each test was frozen and externally timestamped (FreeTSA, Sectigo) before its run, ran
  once, and was independently re-derived to the cent. The audited IDX harness, provenance and append-only rules were
  reused, not rebuilt.
- **Failed:** both mechanisms as spot-long profit sources. Forced crypto deleveraging continued rather than reverted.
  MSCI deletions rebounded relative to similar stocks in both periods, but in 2025-26 the market fell and buying them
  lost money.
- **Unknown:** whether the relative MSCI-deletion effect (positive excess in development and out of time, significant
  only in development) can be harvested; doing so needs a hedge (an index short or future), which this task excluded.
  The 2019-2020 strength may be specific to the COVID shock.

## Next decision for the owner

1. **Default: stop here on these two mechanisms.** Neither is an executable spot-long edge; no retune (other holds,
   entries or windows) is allowed after these results.
2. Optional, no money: a pre-registered prospective paper log of MSCI Indonesia deletions through MSCI's
   reclassification decision (due by 30 June 2027). A reclassification would be the largest forced-selling event yet, but
   the frozen rule has just failed out of time, so its prior is low.
3. If hedging is ever allowed (IDX short selling restarted in October 2026 for a few LQ45 names; index futures), the
   relative deletion effect is the one consistent signal in this search and the thing to test, on fresh data only.
