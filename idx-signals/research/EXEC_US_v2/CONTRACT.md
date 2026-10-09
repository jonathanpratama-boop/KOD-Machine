# EXEC-US-v2: the trading contract

One contract for US daily-bar strategies, used by historical replay and by forward paper scoring.
The code is `idxsig/contract.py` and its tests are `tests/test_contract.py`.

Both modes call `Account.step` once per session, on data through that session only.
- **Replay** (`contract.replay`) steps through a stored panel.
- **Forward** (`contract.forward_step`) steps through the data available that day. It restores
  the account from the JSON state saved after the previous day.

Neither mode has its own trading rule. Any change to a rule below needs a new
`CONTRACT_VERSION`. A saved state made under a different contract is refused.

**Legacy behaviour is unchanged, under its own versions:**
- EXEC-US-v1 (`exec_us.py`), used by PAPER-POLICY-v4 and the scheduled US paper scans.
- Backtest fill models A, B, B2 and C (`execution.py`).

**Units.** The panel is split-adjusted. As-traded = adjusted × F, where F comes from the split
schedule. Every price and share count in a record is as traded in the session named beside it.

## Parameters (hypothetical account; `ContractSpec`, sha256 printed in every trace)

| Parameter | Value |
|---|---|
| Entry-to-invalidation distance at the permitted entry | at most 5% |
| Chase limit | entry no higher than signal close × 1.10 |
| Maximum hold | 5 sessions, the entry session counting as 1 |
| Account | $10,000 cash; no leverage, no shorting, no margin |
| Planned loss at the stop | at most 1% of equity; costs included, gaps excluded |
| Position at the permitted entry | at most 20% of equity |
| Planned value | at most 10% of the 20-session median traded value (USD) |
| Filled shares | at most 10% of the entry session's whole volume (an upper bound) |
| Stop slippage | 0, assumed |

## Timeline for a signal at the close of session s

1. **Decision.** Made after the close of s, using completed bars through that close. The scan
   has three outcomes, recorded as different events:
   - `SIGNALS`: one or more names qualified.
   - `NO_SIGNAL`: the scan ran and nothing qualified.
   - `FAILED`: the inputs could not be established. This covers stale data (the latest bar is
     not the expected session), missing data, a hash mismatch or an error.

   A failed scan makes no decision. Orders already working, and stops on held positions, are
   still processed, because a broker would still execute them.
2. **Invalidation first.** The strategy supplies the stop from data through s, floored to the
   tick. It is never moved to make an entry fit.
   - It becomes actionable once the entry fills, from the entry session onward.
3. **Permitted entry.** `limit = min(floor(stop / 0.95), floor(signal close × 1.10))`, so the stop
   is at most 5% below any accepted fill.
   - The distance is measured at the permitted entry, not at the signal close. Both distances
     are recorded.
   - If no price is above the stop and within both limits, the result is `REJECTED_NO_PLAN`.
4. **Size.** Equity is cash plus reservations plus positions marked at the close of s.
   - Risk per share = (limit − stop) + limit × (buy cost + sell cost), both at the limit.
   - Shares = floor of the smallest of:
     - 1% × equity / risk per share;
     - 20% × equity / limit;
     - 10% × the 20-session median traded value / limit.
   - The binding limit is recorded. If no whole share fits, the result is `REJECTED_SIZE_ZERO`.
   - **One sizing rule.** The size is cut to the binding limit, and a signal is rejected only
     below one share. Traded value is in dollars, so a split inside the window changes nothing.
     This replaces both legacy rules: the backtest's fixed notional with rejection, and the paper
     plan's share-count capacity.
5. **Several signals on one session.** Priority goes to the higher 20-session median traded
   value, then the ticker, in alphabetical order.
   - Each order reserves `shares × limit × (1 + the highest buy cost a fill inside the band can
     carry)`. Cost tiers rise as the price falls, so that is the cost at the stop.
   - If free cash covers fewer shares, the order is cut and flagged `cash_limited`. If it
     covers none, the result is `REJECTED_INSUFFICIENT_CASH`. Cash can never go negative.
   - A name already held, or with an order working, is `REJECTED_ALREADY_HELD`.
6. **Order.** BUY LIMIT ON OPEN at the limit, for the next session's opening print only. The
   unfilled remainder is cancelled after the print, and the stop is attached.
   - A split taking effect at the open converts the limit, stop and shares by the F ratio. The
     dollar value is unchanged.
7. **Entry session open.** The reservation is released. Then:
   - **No opening print** or no volume: `UNFILLED_NOT_TRADED`.
   - **Open above the limit** (an excessive gap): `UNFILLED_OPEN_ABOVE_LIMIT`, with the stop
     distance the fill would have had. There is no later fill, and no fill at the signal close.
   - **Otherwise the order fills** for `min(planned shares, floor(10% × the entry session's whole
     volume))`:
     - all of it is `FILLED`; part of it is `PARTIAL`; nothing is `UNFILLED_NO_LIQUIDITY`;
     - the open is the fill price, at the buy cost for that price;
     - **Assumed:** whole-session volume is an upper bound on what the opening auction could fill.
       The auction's own volume is not in a daily bar. Every fill carries this label
       (`fill_evidence`).
   - **Open at or below the stop.** The limit order fills, because a limit buy cannot be
     cancelled on information inside the auction. The attached stop then triggers at once.
     **Assumed:** it sells at that open (`STOP_AT_OPEN_ON_ENTRY`), so the round-trip cost is lost.
8. **Exits.** In each held session, checked in order:
   - **Gap.** After the entry session, an open at or below the stop sells at that open
     (`STOP_GAP_AT_OPEN`).
   - **Stop.** Otherwise a low at or below the stop sells at the stop (`STOP`). The fill happens
     after the open, which is the first print.
   - **Time exit.** Otherwise, at session 5 counting the entry session, a market-on-close order
     sells at the close (`TIME_EXIT_AT_CLOSE`). That order is placed in advance, so the fill is
     achievable.
   - **No trade.** A session in which the name did not trade fills nothing. The exit rolls to
     the next traded session (`TIME_EXIT_ROLLED`).
9. **Costs.** Fees plus the US price-tier cost, charged at each fill's as-traded price.
   - Proceeds are available at that session's close.
   - **Assumed:** no settlement delay.
10. **Balance.** Every event records cash and reservations after it. The account is marked at
    each close.

## Risk, kept separate

- **Planned stop distance:** at the limit, and at the actual fill (`stop_distance_at_fill`).
- **Planned account risk:** planned loss at the stop as a share of equity at the decision. It is
  at most 1%.
- **Planned risk at the fill:** filled shares × (max(fill − stop, 0) + round-trip costs).
- **Realised loss beyond the planned risk:** what a gap through the stop cost beyond the plan.
  It is never folded into "the 5% stop".

## Corporate actions

Splits are applied through F from the verified split schedule (`ca-reconcile-v1`): shares and
prices are converted between sessions, and dollar values are unchanged. Names the schedule
cannot verify are traded but labelled `units_verified: false` in the trace. The quarantine list
is itself outcome-dependent (built from later records), so it is not used to drop trades silently.

## Research window

`replay(..., permitted=(start, end))` refuses any session outside the window the evidence may use.
The demonstration uses 2023-01-03 .. 2023-12-29, the year the split schedule is verified. The
reserved holdout is not read.

## Not established by daily data (labelled wherever it matters)

- How much the opening auction could fill: whole-session volume is used as an upper bound.
- The price of a stop that triggers at the open, and stop slippage: assumed to be the open, or
  the stop level.
- The order of events inside a session.
- Settlement timing.

## Forward paper scoring

`forward_step(state, data_through_today, today's signals, expected session)` returns the new
state. The demonstration keeps it in a hash-chained daily ledger. If the scan missed sessions,
their fills and exits are processed from the data now available, and no decision is made for
them.

The scheduled paper routines still run PAPER-POLICY-v4 (EXEC-US-v1). Switching them to this
contract would be a new paper policy version, and that decision has not been taken here.
