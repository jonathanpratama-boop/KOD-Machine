# LIQ_REBOUND_v1: is a spot buyer paid for absorbing forced deleveraging in BTC and ETH?

Written 2026-10-31, before any return of this rule was computed. Simulation only: no orders, no paid data, no
credentials. Code: `rebound.py` (modes `--feasibility`, `--freeze`, `--run`), data: `collect.py`, tests:
`tests/test_liq_rebound.py`. The machine-readable freeze is `protocol.json`, which pins the hashes of all of these.

## 1. Owner constraints this test obeys
Unleveraged spot buying only, cash is a valid position; no shorting, no perpetual funding carry, no margin, no option
selling (owner, 2026-10-31). Manageable frequency (about 10 round trips a year). Not Ace's funding-carry work: perps are
used only as public information, never traded. A different mechanism from the failed ADMISSION rule (no retune of it).

## 2. Hypothesis, payer and falsifier
- **Mechanism.** When BTC or ETH falls sharply while perpetual-futures open interest (coin units) collapses, leveraged
  longs are being force-closed at market by liquidation engines and stop cascades. Theory (Grossman & Miller 1988;
  Brunnermeier & Pedersen 2009; Nagel 2012) says such demand for immediacy is met at a temporary price concession that
  reverses as liquidity providers return.
- **Who pays.** The forced sellers: liquidated leveraged traders (BitMEX liquidations average about 60x leverage, Cheng
  et al. 2021) and stop-loss sellers.
- **Why it could persist.** Liquidity supply shrinks exactly when it is demanded (dealer capital and risk limits bind),
  and in real time a cascade is hard to tell from news; the buyer bears crash risk (LUNA, FTX). The crypto
  liquidity-provision premium rises with volatility and crash risk (Farag et al. 2025, JBF).
- **Evidence grade before the test: weak and mixed.** No peer-reviewed study tests BTC/ETH spot returns after an OI
  collapse net of costs. Direct crypto evidence is gross and pre-2019 (De Nicola 2021: 2h reversal after 4-sigma
  moves), small and in-sample (Caporale & Plastun 2019: ETH reverses next day, BTC continues), and industry research
  finds weak 30-day returns after big liquidation days (K33, 2025). Large coins show daily momentum (Zaremba et al.
  2021). This test is designed to be able to kill the idea.
- **Observable before entry.** A 24h spot log return at or below -k x trailing sigma, and a 24h change in coin-unit
  open interest in its trailing 5% tail, both computable at the signal close from public data.
- **What disproves it.** Any failed gate in section 7, in particular: no net edge after Indonesian-exchange costs; no
  better than random entry times; cascades (OI collapsing) reverting no more than equally sharp drops without an OI
  collapse (that would kill the forced-deleveraging mechanism even if a generic reversal existed).

## 3. Prior KOD work (duplicate check)
No KOD study has backtested buying crypto spot after a crash (registry audit of every `research/` study, the
BLUEPRINT and the decisions). Adjacent: E7 (2021-12..2022-12, same Binance metrics files, the opposite setup: rising OI
plus negative funding, long 24h; FAILED -0.35 pts); E6 (selling-pressure absorption, NULL); E2's G8_DD_REBOUND
(detection only); LEAD_LADDER_v1's beaten-down cell (detection, placebo ratio 1.46). None tests this payer.

## 4. Data and periods (audit)
- Spot: Binance BTCUSDT and ETHUSDT 1h klines 2020-04..2023-12, already on disk (manifest
  `binance_1h-20261015T182940Z.jsonl`, hashes re-verified). Binance prices stand in for the owner's IDR exchange.
- Open interest: Binance USDT-M daily metrics files (5-minute `sum_open_interest`, coin units), BTCUSDT 2020-09-01..
  2023-12-31 and ETHUSDT 2021-12-01..2023-12-31, 1,978 files, none missing (manifest
  `liq_rebound-20261031T223330Z.jsonl`); the 799 files overlapping E7's pins are byte-identical. The archive
  regenerated these files on 2026-03-18, so they are not guaranteed point-in-time.
- Data hygiene (fixed after the pre-freeze code review, before any return was computed): open-interest rows equal to
  0 (the archive's missing-data marker) are dropped; inside a run of 3 or more identical consecutive open-interest
  values (a frozen feed) only the first row is kept; both become gaps, so the 15-minute tolerance gives no signal.
  Spot klines with no trades or no volume (exchange-halt placeholders) are treated as missing bars.
- **Already influenced research (development data):** crypto daily 2020-2023 (many studies); hourly 2020-07..2022-12
  (E6) and 2021-12..2022-12 (E7, including these OI files and their cascade weeks); 2023 is an already-used validation
  year (BLUEPRINT): here it is a one-time provisional screen only.
- **Sealed / not read:** every row dated 2024-01-01 or later (crypto holdout; largely spent at daily resolution by
  CRYPTO_TUNE_v1 and ADMISSION_HOLDOUT_v1, but never at hourly or OI resolution for this question). Loading refuses
  later files; no position may need a price after 2023-12-31 23:00.
- Disclosed incidents in this session (handoff/decisions/2026-10-31_holdout_breach_by_research_agent.md): a research
  sub-agent computed turn-of-month statistics on sealed US and BTC daily rows (not used here); five BTC prices for
  2026-10-27..31 were printed once.

## 5. The rule (frozen)
- Universe: BTCUSDT, ETHUSDT spot (both listed on OJK-licensed Indonesian exchanges and on eToro).
- Signal at the close T of each hourly bar: lr24 = ln(close_T / close_T-24h) <= -k x sigma, where sigma is the
  standard deviation of hourly-sampled 24h log returns over the 30 days ending 24h before T (at least 576 values);
  AND dOI24 = OI(T-5min) / OI(T-24h-5min) - 1 <= the 5th percentile of dOI24 over the 180 days ending 24h before T (at
  least 90 days). OI rows are taken as of 5 minutes before the needed time (publication allowance) and must be no more
  than 15 minutes older than that, else no signal.
- **k = 2.0**, set by the pre-declared outcome-blind rule in `FEASIBILITY.json` (largest k in {3.0, 2.5, 2.0} with at
  least 30 discovery signals and 8 episodes, else the smallest; `rebound.py` re-derives it and refuses a mismatch).
  Counts only, no return: k 3.0 -> 17 signals / 14 episodes, 2.5 -> 21 / 16, 2.0 -> 23 / 18 (the same before and
  after the hygiene fixes; the first pass is kept as `FEASIBILITY_pass1_before_review.json`). No k qualified, so 2.0.
- Entry: market buy at the open of the bar starting 1 hour after T (never at the signal price).
- Exit: market sell at the open of the bar 72 hours after the entry bar; if that bar is missing, the next valid open.
  Catastrophic stop: if a bar's low reaches -20% from the entry price, the position is sold at that bar's LOW (the
  worst price of the hour; a touched level is never assumed to be a fill).
- Sizing: 50% of equity at the decision (equity marked at hourly closes), capped by free cash, minimum order 10 USDT;
  one position per coin, so at most 100% invested, never leveraged; a coin already held or pending ignores new
  signals. Cash earns 0%. Start 10,000 USDT (about IDR 160m).
- An order whose entry bar is missing lapses at that bar (the coin was pending until then); a signal whose scheduled
  exit falls outside the loaded data is skipped (both counted).
- Windows are signal-bar opens: discovery bars opening 2020-09-01 00:00..2022-12-31 23:00 (signal times 2020-09-01
  01:00..2023-01-01 00:00); positions may run to their exits in 2023. The 2023 screen is a separate account starting at
  10,000 USDT.

## 6. Costs, benchmarks and stresses (declared)
Per side, fraction of notional = fee + spread/slippage + tax (sources in the session's venue review: Indodax API fee
table, Pintu/Reku fee pages, CFX bourse fee, PMK 50/2025 tax of 0.21% on sales via domestic licensed exchanges):
- A1 maker on a licensed IDR exchange: buy 0.16%, sell 0.37% (per-side sum 0.53%).
- **A2 base, market orders on the same venues: buy 0.31%, sell 0.52% (per-side sum 0.83%).**
- A3 eToro real crypto, Bronze-Gold tiers: buy 1.15%, sell 2.15% (1% fee each way plus an assumed 0.15% spread plus
  the 1% foreign-platform sale tax): reported only. eToro counts as spot only if a position is tagged as a real asset
  at 1x; its Seychelles terms allow crypto trades to be executed as CFDs, which this test excludes.
- Stresses on A2: S1 entry 4 hours after the signal instead of 1; S2 doubled spread/slippage (buy 0.41%, sell 0.62%);
  S3 missed fills (each entry independently fails with probability 0.3 and the coin then stays out until that
  trade's scheduled exit, so a miss is a lost trade, not a delay; 500 seeded draws; reported).
- Benchmarks: cash (0%); equal-weight BTC/ETH buy-and-hold over the same window at A2 costs; a random-entry placebo
  (same coins, same number of trades, same rules and costs, entries drawn from all eligible signal hours, 2,000
  draws); the mechanism control: drop-only hours (same price leg, OI change above its 5% tail) with no cascade hour on
  the same coin in the preceding 1 + 1 + 72 bars. It is causal (a buyer without the OI leg could trade it; the early
  hours of a crash, before OI reaches its tail, stay in) and never contains a cascade's own aftermath. Drop size is
  not matched; the mean signal-hour return of each set is reported.
- Reported: end equity, net return, CAGR, max drawdown, mean exposure, turnover, win rate, mean/median/worst trade,
  CVaR 95%, P&L without the 3 largest winners, by coin and by year, monthly returns, episode-cluster bootstrap
  interval (7-day episode gap, 2,000 draws), event-time mean paths (descriptive).

## 7. Pass/fail (frozen; discovery = signals 2020-09-01..2022-12-31, A2 unless stated)
- G0 sample: at least 20 cascade trades and 8 episodes, else INCONCLUSIVE.
- G1 net edge: mean net trade return > 0 and its episode-cluster bootstrap one-sided 95% lower bound > 0.
- G2 timing: mean net trade return above the 90th percentile of the random-entry placebo.
- G3 mechanism: cascade mean gross return > control mean gross return (NOT_EVALUABLE below 5 control trades).
- G4 account: end equity > start, max drawdown no worse than -25%, realized P&L without the 3 largest winners > 0.
- G5 stress: S1 and S2 accounts both end above start.
- G6 2023 screen: with at least 3 trades, mean net trade return >= 0 (fewer than 3: uninformative, flagged).
- **Verdict:** PROMISING only if G0-G6 all pass; INCONCLUSIVE if G0 fails or G3 is NOT_EVALUABLE; otherwise FAIL.
  INCONCLUSIVE takes precedence over failed G1, G2, G4 or G5.
  Episodes pool BTC and ETH signals, ordered in time, a new episode starting after a gap of more than 7 days; they set
  G0's count and G1's bootstrap clusters. Max drawdown is measured on hourly-close marks. The OI percentile uses
  pandas' linear interpolation. Where this text and the pinned code differ, `rebound.py` and the GATES stored in
  `protocol.json` govern.
  PROMISING is a candidate for validation, never proof: it licenses (a) measuring the IDR exchange basis at each event,
  (b) a prospective paper log from 2026-11 with a kill rule, and (c) asking the owner whether to open the 2024-01..
  2026-10-29 hourly/OI holdout once. FAIL or INCONCLUSIVE ends this rule: no retune, no other k, window or horizon.

## 8. Attempted variants and the pre-freeze review (complete list)
One run of this rule. Before it: the feasibility counts for k in {3.0, 2.5, 2.0} (signals only), twice (before and
after the hygiene fixes, identical cascade counts). G0's thresholds (20 trades, 8 episodes) were written in
`rebound.py` before the first count; the count rule's 30 is the bar for choosing k, not the sample gate, and the
count rule's comment was reworded (from "the run will then probably be INCONCLUSIVE" to "G0 then decides whether the
sample suffices") without changing its logic. A sample of about 23 trades can kill the idea; it cannot confirm it.

An independent three-lens code review (timing/look-ahead, accounting/fills, specification vs code) ran before the
freeze, with no return computed. It found no look-ahead. Fixed as a result: zero and frozen open-interest rows,
halted placeholder klines, a guard that could not fire on 2024 rows, an account/trade-list inconsistency for missing
entry bars, unresolved positions now fail loudly, the missed-fill stress now loses the trade, the mechanism control
no longer overlaps cascade aftermaths, and the run now refuses unless protocol.json matches the code's config, costs,
windows, seeds, gates and library versions and every pinned file is committed and unmodified (provenance.py and
report.py added to the pins). Hypotheses considered
and not run: crypto option volatility-risk-premium selling (dropped on the owner's spot-only constraint before any
data was read), token-unlock shorts (shorting; unlock data paywalled), turn-of-the-month and pre-FOMC index timing
(weak recent evidence, no verified spot-ETF venue for the owner, holdout breached by a sub-agent).

## 9. Known limits (stated before the result)
Binance USDT prices proxy IDR fills (the IDR basis during cascades is unmeasured); a live OI source reachable from
Indonesia is not yet verified (Binance is reported blocked; Bybit/OKX public endpoints are candidates); metrics files
are regenerated, not point-in-time; costs are fee-page assumptions and slippage in cascades may be larger; the sample
is small (about 23 signals), so the test can kill but not confirm; 72h and the 5% OI tail were fixed a priori, not
optimised; the -20% stop exit at the bar low is a conservative bound.
