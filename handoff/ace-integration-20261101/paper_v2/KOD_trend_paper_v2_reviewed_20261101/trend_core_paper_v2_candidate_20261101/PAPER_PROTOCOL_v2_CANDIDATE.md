# TREND_CORE_PAPER_v2_CANDIDATE — offline implementation contract

Saved before implementation fixtures on 2026-11-01. Research candidate only. This is
NOT the independently backtested per-asset 0/1 SMA rule: portfolio normalization,
daily volatility resizing, actual-holdings rebalancing, execution and kill semantics
are a NEW contract. No profitability validation, live authorization or deployment.
Published v1 protocol, signals and backtest results are immutable and not imported
as trades. Initial cash is a required configurable research input (fixtures 1,000
and 10,000 units of the synthetic USDT cash currency), never a real account balance.

## Reuse and boundary
Reuse the existing local paper_cash_v1 Decimal cash/fill calculations and append /
hash-chain primitives, byte-for-byte vendored with source pins. Reuse its existing
cash convention: total cash includes reserved cash; free = total - reserved.
The remote paper_account.account_state was inspected but cannot be directly reused:
it values unknown marks at cost and hard-codes US execution/initial-cash rules.
contract.Account is also US opening-print specific. This small quote-event adapter
is not a new market-data backtester. Only synthetic, underlying BTCUSDT/ETHUSDT spot
observations are supported. Real/live/network/CFD/perpetual/FX adapters are rejected.
Production source capture, trusted clocks and external receipts remain unimplemented.

## Signal and allocation
Each coin requires exactly 40 distinct consecutive completed UTC calendar-day closes,
finite and positive, each with source hash and actual publication/receipt timestamps
not after decision time. Last day equals signal_date and closes before the decision.
SMA10 > SMA40 gives long. sigma20 is sample standard deviation of 20 log returns;
nonpositive sigma on a long signal rejects the decision rather than inventing size.
raw target = min(1, .015/sigma20), otherwise zero. Normalize both raw targets down
proportionally only when their sum exceeds 1. No leverage, borrowing or shorting.
One decision per signal date; actual UTC decision time and all input hashes are kept.
Latest fresh pre-decision quotes for both symbols and complete account NAV are needed.
Targets are based on decision-time bid-mark NAV, not a retrospective midnight open.
SELL quantity is excess actual holdings over target bid value. BUY budget is target
bid value minus actual bid-mark holdings, inclusive of fees/slippage. Sell intents
execute before buys; buy cash is reserved proportionally from actually available cash,
never from an assumed future sale. Partial/underfunded allocations may underweight.

## Quotes, fills, costs, quantities
Scenarios explicitly version fee fraction, extra slippage fraction, precision, quote
freshness (120 s), intent life (3600 s), daily-mark grace (300 s). These are research
assumptions, not asserted venue facts. Commission uses existing Decimal half-up cents
per fill; fractional units round down to scenario precision. Costs are cash debits.
Each input has canonical payload SHA256 and declared synthetic receipt timestamp.
Fill quotes must be strictly later than actual intent/decision time, received by now,
within quote freshness and before expiry; equal-time ordering is rejected. The prior
midnight open and the decision quote can never fill an intent. Buy at observed ask
plus scenario slippage, sell at bid minus scenario slippage, pay scenario fee. Quote
ask_qty / bid_qty is required and bounds the fill; missing quantity means NO FILL,
not infinite liquidity. Recorded size is a synthetic availability assumption, not
proof of exchange execution. First eligible known-size quote attempts IOC; remainder
and unused reservation cancel. Each quote is consumed at most once per intent.
Pending intents expire without fill. New decisions cancel superseded intents.

## NAV and risk
NAV = total cash + all actual holdings * eligible fresh bid marks. Reservations are
already in total cash and never added again. A missing/stale held mark makes entire
NAV unknown; it is never silently zero or carried at cost. Price-mark NAV is not a
claim every unit can liquidate at that bid. Cash-only NAV needs no quote. Nonnegative
cash and spot-only positive holdings imply aggregate marked gross / NAV <= 1.
Peak starts at initial equity and updates only on complete fresh NAV observations.
At drawdown >=25%, or negative trailing 90-return annualized Sharpe, persist KILLED.
Daily marks are one per UTC midnight boundary, captured within 300 seconds; later
attempts are MISSED_CUTOFF with unknown NAV, never historical reconstruction. Returns
require adjacent complete daily marks; 90 consecutive clean daily returns require 91
consecutive complete marks. Missing days reset eligibility. Sharpe = mean / sample
stdev * sqrt(365), rf=0. Zero variance: zero mean => undefined/no kill, negative mean
=> negative-infinity convention/kill, positive mean => positive-infinity convention;
no infinite/undefined value counts as a finite success statistic.
Kill is irreversible in this account. Cancel pending intents and create liquidation-
only sell intents for actual held quantities. Liquidation requires a strictly later
eligible bid/known-size observation; gaps and insufficient liquidity can leave residual
holdings. Continue marking unresolved holdings; never fabricate a stop price or force
cash. New entry decisions are blocked. Renew unfilled liquidation intents explicitly
on subsequent processing after expiry, still requiring a future observation.

## Persistence, gaps and corrections
Stable semantic operation/intent IDs; identical retry returns the original result;
same ID with changed payload is a hard error. One operation is one locked, fsynced
append containing command, deterministic result and state hash. Restart verifies chain,
pins and deterministic replay; torn/corrupt tails fail closed (no automatic truncation).
Missing-cycle records are separate and do not synthesize signals or fills. Consecutive
daily sample checks detect absent cycles even if no process ran to record the miss.
All events bind protocol/source/code pins and scenario hash. Self-recorded timestamps
and local hash chains are NOT external time attestation.
v1 duplicate rows remain byte-identical in a read-only snapshot. Separate audit metadata
identifies each line hash, duplicate key and canonical first occurrence; no rows deleted.

## Acceptance / integration hold
Synthetic tests cover both initial cash amounts, fees, actual-held rebalancing, causal
quote/quantity gates, reservations, unknown marks, first-day drawdown, persistent kill,
clean/missing/zero-variance Sharpe, retry conflicts, restart and tamper refusal.
Independent audit must review candidate implementation and failure cases. No remote
workflow edit, publication, integration into Mac/Claude, historical outcome rerun or
financial order is permitted by this candidate. A later adapter review and explicit
activation decision are required before any forward paper trial.
