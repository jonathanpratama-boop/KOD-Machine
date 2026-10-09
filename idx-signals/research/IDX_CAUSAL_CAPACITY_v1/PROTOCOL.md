# IDX_CAUSAL_CAPACITY_v1: protocol (frozen before the rerun)

**Question.** Did the ex-post capacity filter in fill model A change the E1 validation
evidence? The evidence is run `20261008T000401Z_MOONSHOT_E1_D1_v1.1` (MOONSHOT_E1_D1 v1.1,
validation year 2023). It is the run pinned for IDX in the paper policy.

**Why.** Under fill model A, a closing-auction entry is kept only if its shares are at most
10% of the entry session's final volume. That volume is known only after the auction the
order would take part in, and it includes that auction. In the evidence run, 248 of 1,042
rule attempts were skipped on this test (SKIP_LIQUIDITY). So were 117,102 matched-random
attempts.

## The new fill model: FILL-C-v1 (`fill_model="C"`)

The model applies to closing-price entries in panel units, which is what IDX uses.

- **Capacity.** Shares are at most `max_participation` (10%) of the median volume of the 20
  sessions up to and including the signal session. These sessions are known when the
  decision is made, after the signal close.
- **Listed sessions only.** A listed session without trades counts as 0. Sessions before
  listing are ignored.
- **Share units.** Each session's volume is put into entry-session shares using the registry
  factor: `volume[j] × reg_factor[entry] / reg_factor[j]`. Only verified splits, reverse
  splits and stock dividends scale shares. That is the same scaling the run already applies
  to held shares.
  - Assumption: a split's ratio and effective date are public before the entry session.
- **Unresolved resets.** If a reset the registry cannot verify falls after the window's first
  session and on or before the entry session, the units are unknown. The attempt gets the
  new status `SKIP_CAPACITY_UNKNOWN` and is not entered. A verified rights issue does not
  change share units.
- **Everything else is unchanged from fill model A.**
  - Entry needs the entry session to have traded, with its close not locked at ARA. Both are
    fill conditions of the closing auction, not sizing inputs.
  - Lots, fees, exits, corporate actions and the random and matched-random baselines all
    work as in A, and the baselines use the same execution.
- Fill model A stays unchanged, so the evidence run reproduces.

## The rerun

- **Inputs.** The same rule, panel (`9d3a0718…`), registry (`ca_registry-20261007T230210Z.json`),
  window (2023-01-02 .. 2023-12-29), holding period, fees, notional, overlap rule, seed
  20261007 and 200 draws as the evidence run. Only `--fill-model C` differs.
- **Holdout.** It is not read. 2024 onwards stays sealed.
- **Reproduction first.** Before the rerun, run fill model A in memory on the current code and
  confirm it reproduces the evidence run's rule trades and summary statistics. If it does
  not, stop and report.
- **Recording.** The rerun is appended to `results/runs/`. The evidence run is not edited.

## What is reported

1. Rule and matched-random results under C, next to A: fills, scored trades, hit rate,
   average and median net, difference from matched random, and the one-sided p.
2. The rule attempts whose status changes between A and C, by direction, with the average
   net of the trades entered only under A and of those entered only under C.
3. The count of `SKIP_CAPACITY_UNKNOWN`.

## How the result is read (fixed now)

The APPROVAL-v2 test (PR #3) needs all three: p < 0.05 against matched random, a positive
average net, and an average net above matched random.

- **C fails the test.** The conclusion is that the ex-post filter did not hide an edge. E1 D1
  stays negative evidence, and nothing else changes.
- **C passes the test.** That is not an approval. The 2023 year has now been examined twice,
  and the fill model was chosen after seeing the A result. Any use would need a new evidence
  run on data not yet read, and a new policy version. The holdout's single use belongs to the
  E1 protocol.
- **Either way.** If A and C differ materially, here meaning the rule's average net moves by
  more than 1 percentage point or p crosses 0.05, the report says so. The report then
  recommends that IDX research runs use C from now on.
