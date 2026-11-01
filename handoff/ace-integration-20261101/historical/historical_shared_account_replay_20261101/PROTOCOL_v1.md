# HISTORICAL_SHARED_ACCOUNT_DAILY_v1 — frozen exploratory policy

Written2026-11-01 before opening historical archive rows or computing account returns.
Single canonical policy, subject to independent pre-outcome review. Review corrections
must be appended/pinned BEFORE outcome computation. Not a live-feed integration.

## Classification and scope

Retrospective exploratory replay on already-used BTCUSDT/ETHUSDT daily spot inputs;
NOT clean confirmation, new holdout, executable-quote validation, or real orders.
Use only existing local input_allowlist.json and its220 original ZIPs under
fresh_eyes_reproduction_20261101/raw. No network, new data, grid search, fitting,
parameter/range selection from outcomes, alternate strategy or publication.
Input allowlist SHA256 dcda45f36489eeb0b914cb8cb7ecf359178d3be386f4ac7abbc001821f72213d;
source manifest SHA256 6b5cbe0b8be894a82980cc5110fb7fc4a501b3b7cea3c2e3e66e1c8cc29dd629.
Metadata reports3332 consecutive daily bars per asset,2017-08-17 to2026-09-30.
Reverify exact bytes, ZIP members, schemas, UTC units/boundaries, OHLCV, duplicates,
gaps and cross-asset alignment before computing outcomes. Do not trust assert-only
checks under optimized Python. All old files and studies remain unchanged.

## Exact strategy/account invariants reused from reviewed v2

Start with10000 USDT shared research cash. Underlying spot only, no shorts/leverage,
interest, deposits, borrowing or FX. SMA10>40 using exactly40 consecutive closes;
20 log-return sample standard deviation; raw weight min(1,0.015/sigma) when long,
zero otherwise; nonpositive sigma while long rejects. Normalize weights down only
when their sum exceeds1. Holdings-derived rebalancing; total cash includes reserved,
free=total-reserved; no double spending. Gross marked exposure<=equity.

Costs: v2 named research scenario fee0.001/side, adverse slippage0.0005/side,
quantity precision8 decimal places, fees Decimal half-up cents. NOT asserted actual
Binance/eToro fees, increments, spread, tax or eligibility. Tax0 is an unverified
scenario assumption. No min-notional/product-rule data is available; those real
execution constraints remain unsupported. Reuse v2 Decimal buy/sell primitives and
account/risk/return functions via a separately versioned minimal daily-profile seam.
This is a NEW shared-cash contract versus old independently backtested per-asset0/1.

## Frozen daily timing / execution model (deliberately NOT quote parity)

All historical first-publication/arrival times are unknown. No invented receipt or
BBO/depth is asserted. Times below are MODEL times, not historic public timestamps.
A dayD close/volume is ASSUMED usable at D+1 00:01 UTC. Daily decision at D+1 00:01
therefore uses only completed closes throughD. The already-passed D+1 opening price
CANNOT fill that decision. Earliest fill reference is D+2 opening price: a full-
session delay, strictly later than decision. No subsecond timestamp fiction.

At each daily opening reference, atomically install both assets' opening marks,
evaluate aggregate risk, then process pending SELLs before BUYs, using actual
holdings/cash. The mark and subsequent fill bookkeeping share that opening model
time. Existing intents are strictly older; new kill liquidation intents made at
this opening cannot fill on it. They wait until a later daily opening observation.
Prices are explicit historical OPEN references, NOT bid/ask or promised trades.
Modeled BUY=open*(1+slip), SELL=open*(1-slip), with no invented order-book spread.

Synthetic capacity at opening dateT is0.1% of base volume from T-2, the latest daily
volume already available under the00:01 assumption BEFORE openingT. Never use T or
T-1 full-day volume to size an openingT fill. This lagged-volume participation cap
is an explicit modeled capacity, NOT observed available quantity/depth. Quantity
rounds down; partially filled IOC remainder cancels. No actual slippage guarantee.

Daily intent lifetime is48 hours (an explicit departure from the quote profile's
one hour, needed for the full-session delayed observation). Opening reference marks
retain v2's120-second modeled decision-freshness allowance; decision at00:01 is
within it. No fills at prior prices, missing opens, unobserved quotes or same-time
new intents. Missing data aborts validation; synthetic missing-cycle cases must
remain unknown rather than interpolated. Warm-up bars are not scored trading days.

## Risk / NAV / terminal policy

Initial peak includes initial10000. Sampled NAV=total cash+holdings*current opening
reference. All held marks must be present; otherwise full NAV unknown and no new
risk-increasing fills. Risk evaluates before and after modeled fills. Persistent
kill on observed drawdown>=25% or trailing90 daily simple returns' Sharpe<0, using
91 consecutive clean daily marks, identical v2 missing/zero-variance handling.
No reset/restart at year/split boundaries. Kill cancels buys; held positions remain
exposed until a STRICTLY LATER eligible modeled opening fill, including gaps and
partial capacity. No25%-loss stop-fill guarantee or intraday risk detection claim.

Record daily NAV at each opening AFTER eligible fills, then evaluate90-return
Sharpe. Daily baseline at first decision day opening starts with cash. First
signal day is the40th input close; first decision is next day00:01; first possible
fill is following day opening. Final observation is2026-09-30 OPEN only. No Sep30
close/volume or later return may affect a decision/fill/result. Preplan a flat-target
terminal decision at2026-09-29 00:01, executed no earlier than Sep30 opening. This
replaces that day's ordinary rebalance for every invested policy. Any capacity-
limited residual remains marked and is reported, never fabricated liquidated.

## Controls and reporting — same economic/accounting assumptions

Run exactly three policy labels, no alternatives:
1. TREND_V2_SHARED: strategy above plus persistent risk rules.
2. PASSIVE_50_50_RISK_MATCHED: buy-once50/50 targets at the same first decision time,
   then hold (no drift rebalancing), same persistent kills/costs/capacity/terminal exit.
   This is risk-overlaid passive exposure, NOT conventional unconstrained buy-and-hold.
3. CASH: shared cash held, zero interest; no invented fills or costs.

Same initial cash, date window, reference marks, transaction model and NAV accounting.
Report ending cash/holdings/NAV, growth/CAGR, daily-sampled drawdown with initial peak,
daily-return volatility/Sharpe, paid fees, modeled slippage dollars, fill counts,
absolute notional turnover, sum(daily traded notional / pre-fill opening NAV), kills
and first-trigger/modelled liquidation times, pending/residual positions and exposure.
Do not optimize after comparing controls. Whole-history results are primary; no
fresh-start subperiods. If old development/validation labels are shown, preserve
carried account/kill state and disclose reused data; do not call them confirmation.

For every account reconcile cash=initial+sum(fill cash changes), holdings=sum signed
fill quantities, fees=sum commissions, NAV=cash+marked holdings. Append-only event
IDs/hash chain, source/protocol/input hashes and deterministic replay must agree.
A linear offline writer may reuse existing event_hash/verify_chain primitives rather
than repeatedly reread the whole growing journal; it must preserve duplicate-ID,
state/result hash and final replay verification. This is an offline driver around
reviewed account mechanics, not a new optimized return-vector engine.

## Gate

No historical returns until independent protocol/code review and synthetic tests
pass. Freeze all source/protocol/data pins immediately before that run. Authorize
one canonical run only; failure fixes must be disclosed, never silently replace
outcomes. Only mocked tapes may be used before clearance. Network remains off.
