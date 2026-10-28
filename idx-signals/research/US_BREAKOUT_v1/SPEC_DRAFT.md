# US_BREAKOUT_v1: specification draft (not frozen, not run)

A draft for review. Nothing below has been computed on prices, and the experiment must not be run
until the open decisions in section 6 are settled and a frozen `protocol.json` is committed beside
this file (any later change is a new file, not an edit).

## 1. Question

After a US common stock closes strictly above its highest close of the previous 60 sessions, does
a long position bought at the next open, under the 5% stop rule, earn a positive average net
return after costs, and beat matched baseline entries run through the same execution, within a
maximum holding period of five sessions?

## 2. Signal (decision after the close of session s)

- `close[s] > max(close[s-60 .. s-1])`, strict, on the split-adjusted series. Adjusted closes keep
  a name's own ratios consistent across splits, so no unit conversion enters the comparison.
- Requires 60 prior sessions in which the name was listed and traded, and a bar on s with volume.
- Uses only bars through the close of s (causal source, as for every rule in `idxsig/rules`).
- No other filter is part of the signal. The eligibility screens in section 3 are listed separately
  so they can be reported with and without.

## 3. Universe and eligibility (proposed; to be fixed before any statistic)

- US repair panel (`build-us-repair-panel`, format `panel-global-v3-reconciled`) for the chosen
  window, so that every provider split event of a panel name has exactly one verification record.
- As-traded signal close at least $5, and FILL-B-v2 capacity of at least 10 x the planned shares.
- Names with unresolved split records are excluded **only** in a labelled sensitivity run. The
  primary result keeps them, because exclusion is decided by records dated after the signal
  (see `research/E2/repair_v3/SELECTION_NOTE.md`).

## 4. Execution: EXEC-US-v1 (`idxsig/exec_us.py`), unchanged except one parameter

| Step | Rule |
|---|---|
| Invalidation (first) | the breakout level `max(close[s-60 .. s-1])`, as traded at s, floored to the cent |
| Permitted entry | `min(floor(stop / 0.95), floor(close[s] x 1.10))`: the stop is never more than 5% below the entry |
| Entry | buy at the opening print of s+1 only if `stop < open <= permitted entry`; otherwise rejected, no later fill |
| Size | at the permitted entry: `min(1% x equity / (entry - stop + costs), 20% x equity / entry, 10% x capacity)`, whole shares; hypothetical equity $10,000 |
| Stop | resting sell-stop from the fill: at the stop when the low reaches it, at the open on a gap through it |
| Time exit | market-on-close at the close of the 5th session counting the entry session as the first (`ExecSpec(exit_after_sessions=4)`) |
| Costs | `profiles.US` fees plus the price-tier cost at each fill's as-traded price |

The only change from the default spec is `exit_after_sessions=4`. That is a different spec
(different `spec_sha256`) and is recorded as such.

## 5. Evaluation (proposed)

- Primary: average and median net return per filled trade, the fill and rejection counts by
  reason, and the share of signals the 5% rule rejects.
- Baseline: matched entries (same session, same price tier and liquidity quintile, names not
  signalling) run through the same execution with the same invalidation definition.
- Approval (APPROVAL-v2): p < 0.05 against the baseline, average net > 0 and above the baseline,
  at least 200 filled trades, evidence run pinned by run id and configuration sha256.
- Windows: discovery and validation periods fixed in advance and disjoint. A breakout rule has no
  parameters to fit, so the validation period is the result. The discovery period is only for
  checking the pipeline.

## 6. Dependencies and open decisions (to settle before running)

Data
- **Window coverage.** The verified repair panel covers 2020-01-02 to 2023-12-29. Split
  verification (`us_splits-*`) exists for events after 2023-01-03, and share-count
  corroboration is permitted only through 2023-12-29. Any other window needs its own schedule,
  coverage file and reconciled panel.
- **Survivorship.** The universe is the 2026-10-08 Nasdaq Trader listing. Names delisted before
  then are absent, which biases a long breakout test upwards. A point-in-time listing source is
  not available without a paid subscription, so the bias must be reported, not removed.
- **Dividends.** Prices are split-adjusted, not dividend-adjusted. Returns are price returns.
- **Daily bars only.** No intraday path: whether the stop or a new high came first on a session
  that touched both cannot be known (the engine assumes the stop first, which is conservative).
  There are no halt or LULD records and no opening-auction size.

Execution
- **Baseline invalidation.** Matched baseline names have no breakout level. Their invalidation must
  be defined (for example, their own prior 60-session closing high, or the entry minus 5%)
  before running, or the baseline is not comparable.
- **Stop slippage.** A stop fill at exactly the stop level is optimistic on fast days. A slippage
  assumption (for example, half the session range below the stop) needs fixing in advance, with
  a stress run.
- **Overlap.** Decide whether a name can signal again while held (proposal: no; skip with a status).
- **Opening-print size.** Capacity is 10% of the 20-session median volume, not the opening auction.
  The auction may be much smaller, so this is unverified.

Governance
- Paper scoring of this rule would go through PAPER-POLICY-v4 and `paper-score-v4` unchanged.
  A detector entry in `idxsig/rules` is needed (a new rule id and version; no existing rule edited).
- The quarantine is outcome-dependent, so primary and sensitivity runs are both reported.
