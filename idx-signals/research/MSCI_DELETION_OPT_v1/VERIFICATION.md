# MSCI_DELETION_OPT_v1: independent verification of the one run (2026-11-01)

Three independent verifiers with fresh context, each with their own code, re-derived the run. Sealed rows
(2024-01-02 .. 2025-02-21) were dropped immediately after loading and never printed. No repo file was modified. Scratch
work: `/tmp/verify_opt_trade/`, `/tmp/verify_opt_walkforward/`, `/tmp/verify_opt_benchmarks/`.

**Verdict: VERIFIED. EXPLORATORY_REJECT reproduces exactly, five gates fail independently (W2, W4, W5, W6, W8), and no
bug produced it.**

## What was checked

- **Trades.**
  - All 465 studied trades at holds 1, 2, 3, 5 and 10 (base plan) were recomputed from the pinned panel and registry:
    status, dates and prices exact, net within 1e-9. This includes 10 exits rolled past lower-limit locks.
  - The same holds for every other plan and hold: base hold 20 (93), S1 (552), S2 (558), S3 (558) and Nov23 (120).
  - S1 enters one session later. S3 uses fees of 0.30%/0.50%.
  - The hold-20, S1/S2 hold-20 and hold-5 files are bit-identical to the two frozen studies' committed files (12/12).
  - No registry corporate action falls inside any scored trade, so that path is unexercised here.
- **Dates.** No date in any trade or walk-forward file falls in the sealed window. No studied trade is EXIT_DATA_END or
  INCOMPLETE; INCOMPLETE occurs only for the excluded Nov23 at hold 20. The purge holds under all four plans.
- **Walk-forward, account and gates.** These were rebuilt from the trade files:
  - 285/285 selection items, all 19 picks, most-selected 20 with counts {20: 11, 10: 5}, and the in-sample choice of 5;
  - W0's 74 trades in 16 reviews;
  - the four walk-forward frames, cell-identical;
  - 3,222 compared items and all 108 TRIALS.csv rows (largest relative difference 4.5e-12);
  - gates W0-W8 and the verdict, identical.
  - W2's lower bound stays negative under other bootstrap seeds (-3.69% to -3.96%).
- **Liquid-market returns.**
  - 404/404 values computable without sealed rows match to within 1.7e-16. Feb25's 24 values need sealed-window
    traded value and could not be recomputed under the data rule.
  - The development buy-and-hold benchmark (-12.96%) matches to the last digit.
  - The out-of-time benchmark reproduces to within 0.2-1.9 points (+18.68% against +18.47%). The gap comes only from
    the first three blocks' membership, which depends on sealed-window rows, as PROTOCOL section 3 discloses.
- **Report.** REPORT.md is byte-identical to `report.py`'s output. All 290 table cells and every number in the text
  match the verifiers' recomputation.

## Findings recorded (protocol-conformant; they do not change the verdict)

1. **The hold-20 picks rest on one review.**
   - All 13 hold-20 picks from Nov20 to Feb25 depend on Nov19 alone. That review has 3 scored trades at 25% weight,
     with BWPT +37.6% at hold 20, including +13.6% on its exit day.
   - Dropping Nov19 flips every one of those picks to hold 10.
   - This comes from the data, amplified by v1's concentrated sizing and a training set with only two deletion
     reviews at the start.
2. **Edge smoothing decided Aug26.**
   - Hold 20, an edge of the grid, is averaged over 2 values; interior holds over 3. At Aug26 this overrode the raw
     best hold (10) in favour of 20, and Aug26's eleven hold-20 trades averaged -13.8%.
   - As a counterfactual only: with hold 10 at Aug26, W4 and W5 would pass, but W8 would still fail and the verdict
     would still be REJECT.
3. **Every fixed hold fails the next-session-entry stress (S1).** The outer S1 mean net is negative at all six holds.
   What the trade has rests entirely on the implementation-day closing-auction fill, the +3.3% / +4.2% next-session
   reversal already seen. Missing that one auction removes it. PROTOCOL section 2's expectation that a 1-3 session
   hold would make a candidate likely was therefore over-optimistic: W6 was structurally hard to pass.
4. **Clarifications to REPORT.md.** REPORT.md is committed and append-only, so they are made here:
   - **The "in-sample choice: 5" line is not an endorsement.** Under PROTOCOL section 6, a REJECT licenses no
     prospective protocol and ends this family's search on history.
   - **The fixed-hold table does not validate anything.** It includes the four training-only reviews in its "all_23"
     scope, and every fixed hold fails S1. None of those rows is validated.
   - **"Sealed reviews not computed" is precise but incomplete.** No 2024 review was computed. Sealed-window panel
     rows did feed trailing features, listing age and liquid-market membership at the first out-of-time sessions
     (PROTOCOL section 3).
   - **W7's name says more than it measures.** It measures return relative to an equal-weight basket that cannot be
     shorted, not hedged or incremental value.
   - **W3's whole margin comes from five reviews.** The walk-forward and baseline accounts are identical through
     Feb25; W3's margin comes entirely from the five out-of-time reviews held 10 sessions.
   - **The out-of-time panel is survivor-only.** Its Yahoo segment drops names delisted after 2025-02-21, which biases
     the out-of-time liquid-market figures upward.
5. **Smaller points.**
   - `check_purge` runs only on the base plan at hold 20. The verifiers checked S1, S2 and S3 themselves and found no
     violation.
   - Exposure uses the nominal hold, and S2's fees column excludes the tick, as disclosed.

## What the result means

Within the frozen procedure, shortening the hold did not rescue the MSCI deletion trade. The selector, using only the
past, mostly kept the 20-session hold, and the result failed five gates. The descriptive pattern is that fixed short holds
were positive in both blocks, but only when bought in the implementation-day auction and never with a one-session delay.
That pattern was already seen before this study, so it is not validated by it. By the frozen rules this ends the
family's search on history.
