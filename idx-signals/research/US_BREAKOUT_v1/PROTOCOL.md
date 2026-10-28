# US_BREAKOUT_v1: protocol (frozen before any breakout return was computed)

`protocol.json` beside this file is the machine-readable form. It is frozen by the commit that
adds both files together with `idxsig/breakout.py` and `tests/test_breakout.py`; the runner
`run_experiment.py` records that commit and refuses to run from a dirty tree. Any change after the
first result is a new protocol version, not an edit. This replaces the open decisions in
`SPEC_DRAFT.md` section 6.

**Question.** After a US stock closes strictly above its highest close of the previous 60 sessions,
does buying at the next open under the 5% stop rule earn a positive average net return after costs,
and a higher one than matched non-breakout entries run through the same execution?

**Prior expectation, recorded now.** Most simple breakout rules show no edge after costs. A "no
edge" result is the likely one, and it is as acceptable as any other.

## Signal and eligibility

- Raw signal at session s: `close[s] > max(close[s-60..s-1])`, strict, on split-adjusted closes;
  60 listed-and-traded prior sessions; the name traded on s. Bars through s only.
- Eligible signal: raw signal, as-traded close at least $5, and a 20-session median traded value
  (listed sessions) of at least $1,000,000.
- Cooldown: a raw signal within 5 sessions after an earlier raw signal of the same name is
  skipped, whether or not the earlier one was eligible or filled.
- No other filter, parameter or look-back is tried.

## Execution: EXEC-US-v2.1 (`idxsig/contract.py`), unchanged

- Invalidation: the breakout level, `max(close[s-60..s-1])` as traded at s, floored to the tick.
- Everything else as in `research/EXEC_US_v2_1/CONTRACT.md`: permitted entry
  `min(floor(stop / 0.95), floor(close x 1.10))`; limit-on-open for the next session only;
  fill at most 10% of the entry session's whole volume (an assumption); resting stop; time exit at
  the close of the 5th session counting the entry session; US cost tiers.
- Each trade runs in its own fresh $10,000 account, so trades are independent and never compete
  for cash. A separate account-level run (one shared account, priority by liquidity) is reported
  as a descriptive realism check.
- A trade whose exit is not in the data is OPEN and excluded, in every arm.

## Matched baseline

- For every eligible signal, 10 controls are drawn (seed 20261009) from the same session and the
  same cell: price bucket ($5-10, $10-25, $25-100, $100+) x median-traded-value bucket
  (<$2M, $2-5M, $5-20M, $20-100M, $100M+). The pool is every eligible-by-price-and-liquidity name
  that traded on that session with 60 listed-and-traded prior sessions and no raw signal.
- A control gets the **stop distance of the signal it is matched to**: its invalidation is
  `close x (level / close)` of that signal. Entry band, sizing and rules are then identical.
- A signal with an empty cell is unmatched and excluded from the comparison, and counted.

## Windows

- **Validation (the result):** signal sessions 2023-01-03 .. 2023-12-29, run once. 2023 is the
  year the split schedule is verified (`panel-global-v3-reconciled`). Honest label: 2023 prices
  were used in earlier work on a different detector and in the execution demonstrations. This rule
  was not computed on them, and it has no fitted parameter.
- **Pipeline check only:** signal sessions 2022-01-03 .. 2022-03-31. Its split units are unverified.
  It is run to see that the code works, and it informs no decision.
- 2024 onwards is not read. The reserved holdout is not touched.

## Statistics (fixed)

- Per filled trade: net return after costs. Filled means FILLED or PARTIAL with an exit.
- Primary statistic D = mean net of filled signal trades minus the cell-weighted mean net of
  filled control trades, with weights = each cell's share of filled signal trades. A cell with no
  filled control drops its signal trades from both sides.
- Uncertainty: bootstrap over signal sessions (2,000 resamples, seed 20261009), one-sided
  p = share of resamples with D <= 0; 95% interval from the 2.5th to the 97.5th percentile.
- Also reported, descriptive: fill and rejection counts by reason for signals and controls,
  median, exit-reason mix, by-half-year D, and the account-level run.

## Sensitivity runs (fixed; reported either way)

- **S1:** names the panel lists as lacking a verified split schedule are removed from both arms.
  The primary keeps them, because exclusion rests on records dated after the signal.
- **S2:** stop slippage: a triggered stop fills 1% below the stop level (`stop_slippage = 0.01`),
  in both arms. The primary assumes none.
- **S3:** the liquidity floor raised to $5,000,000.

## Decision rule (fixed)

The rule **passes** only if all hold on the primary run:
1. at least 200 matched, filled signal trades;
2. mean net of filled signal trades is positive;
3. D > 0 with bootstrap p < 0.05 (APPROVAL-v2: significance, positive net and above baseline);
4. D > 0 in S1 and in S2.

Anything else is **no edge established**, including D > 0 with p >= 0.05. A pass would earn forward
paper scoring only: no approval, no real money. It would not be validated by this one window, and
its survivorship bias would be stated beside it.

## Known biases, stated now

- **Survivorship:** the universe is the 2026-10-08 listing, so names delisted since are absent.
  That flatters a long breakout test, and nothing here removes it.
- **No dividends** (price returns), **daily bars only**, no halt records, and the opening
  auction's size is unknown. Fills, stops and gap-down exits are assumptions as in the contract.
- **Not an independent test of the execution contract.** It shares one code path with the demo.
