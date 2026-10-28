# Experiment E4: the fade, on the short side (KOD-GLOBAL-E4-v1)

Frozen before any analysis. The machine-readable protocol is `protocol.json`; every result
file records its SHA-256. Code: `idxsig/e4.py` (study), `idxsig/rules/moonshot_e4.py`
(candidate detectors and, after the freeze, the selected pair), `idxsig/execution.py` (the
short side: `side="short"`, `SHORT_EXITS`, open-based conditional entries), `tests/test_plans.py`
and `tests/test_e4.py`.

**Why.** E2 found that a big up day marks names with a fat right tail, and that buying them
loses: after a G2_RET30 flag the median five-session move was about -10% against 0% for matched
names, in US equities and crypto alike (and on IDX for F1_ARA), and the long hit rate was 31-36%.
The other side of that finding is a short with a hit rate near two thirds before costs, and a
tail: the minority that keeps running can double, and an uncapped short then loses more than it
risked. E3 showed that no long-side plan rescues the IDX detector. E4 asks whether the short side,
with a squeeze stop, is a trade.

**Question.** Is there a plan from a fixed family under which shorting the signals of the E2
family's already-ran detectors earns a positive average net return after fees, slippage and
carry, beats matched random shorts executed under the same plan, wins more often than it loses,
keeps its tail bounded, and does so in every discovery year?

**Markets.** Crypto first (`panel_crypto-20261013T205803Z`: Binance USDT pairs including delisted
ones, rebuilt from the same source as E2's panel; the short is a perpetual-futures short at the
spot reference price, funding assumed 0.05% per day against the short, 0.1% fee + 0.1% slippage
per side). US second, under the E2 repair panel once rebuilt from the archived inputs, with a
borrow assumed at 0.3% per session; its manifest name is written into the protocol before any US
statistic. IDX is out of scope: no retail short, and the harness's short side is not modelled
under auto-rejection limits. **Precondition:** the recorded E2 trading run for the market is
re-run on E4's panel with its original (long) configuration; identical = REPRODUCED, anything
else DEVIATES and discovery runs only with `--accept-deviation`, recorded.

**Detectors.** G2_RET30 (D1), G1_RET20_CLOSEHIGH, G10_RET15_CLOSEHIGH, G7_MOMENTUM5_30: the four
already-ran members of the E2 family, code copied into `moonshot_e4.py` and checked against the
original by test. No rule outside the E2 family is admitted.

**Plans.** 3 entries x 3 exits x 4 holding periods = 36 rows per detector (6 of them duplicates:
with hold 1 every exit is the fixed exit), 144 runs per market:

| Entry (at an open) | |
|---|---|
| fixed | sell short at the open of s+1 |
| confirm | the first open in s+1..s+3 below the signal close (the fade has begun) |
| pullback | the first open in s+1..s+3 above the signal close (into a bounce) |

| Exit (at a close) | |
|---|---|
| fixed | buy back at the close of the holding_days-th session after entry |
| stop_high | the first close at or above the signal session's high (the squeeze stop), else fixed |
| first_up | the first close above its own reference price (an up day), else fixed |

Holding periods 1, 2, 3, 5 sessions. Carry is charged per session held. A name that stops
trading is bought back at its last traded close, as E2's longs were sold.

**Harness.** As E2's recorded runs: market profile costs, notional 5,000, at most 10% of the
entry session's volume (fill model A, ex post, labelled), split-adjusted source prices, overlap
skipped, 200 matched and 200 same-session random draws executed on the same side and plan, seed
20261007, prefix-first causal signals.

**Periods.** As E2: discovery 2020-07-01 .. 2022-12-31, validation 2023, holdout 2024 onward.
The holdout is sealed in code for every market now (`backtest.GLOBAL_HOLDOUT`): the harness
refuses a US or crypto detector run that touches 2024 unless `--holdout-final` names it as the
one final test, which E4 never does.

**Selection, on discovery only.** Admissible if scored trades >= 200, average net return > 0,
one-sided p < 0.05 against matched random shorts, average net return > 0 in each discovery year
with at least 50 scored trades (2020 from July, 2021 the bull market, 2022 the bear market), hit
rate >= 50%, and the 1st percentile of trade returns >= -50%. The highest average net return
wins; ties by more scored trades, then grid order. The whole table is published, with D1's
original plan mirrored to the short side as the reference row. The winner is written into
`moonshot_e4.SELECTED` and committed before any validation number exists.

**Validation.** One recorded harness run of the frozen pair on 2023. Pass if scored >= 100,
average net return > 0, p < 0.05 against matched random shorts, hit rate >= 50% and the 1st
percentile >= -50%. The median, fill rate, the same-session baseline and the worst trades are
reported, not judged.

**Consequence.** A pass lets a new paper policy version underwrite paper SHORT ON TRIGGER
decisions for the pair in that market, each scored prospectively; a fail leaves the policy
unchanged and this family exhausted. No real orders, no entry permission, and no promise of
reliability: a high hit rate with an unbounded tail is a losing strategy, which is why the tail
is a criterion.
