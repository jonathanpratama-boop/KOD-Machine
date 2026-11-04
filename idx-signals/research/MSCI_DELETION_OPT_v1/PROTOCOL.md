# MSCI_DELETION_OPT_v1: a bounded, exploratory holding-period study of the MSCI Indonesia deletion trade

Written 2026-11-01, before any result of this study was computed, in answer to the owner's optimisation brief ("build and
execute a disciplined optimisation study, spot buying first ... don't treat one failed config as proof the idea fails,
and don't tweak until green"). Simulation only: no orders, accounts, paid data or credentials. Nothing is published
remotely until the owner approves. Code: `opt.py` (`--feasibility`, `--freeze`, `--run`), rendered by `report.py`;
tests: `tests/test_msci_deletion_opt.py`. `protocol.json` pins these files, both earlier MSCI studies' frozen files and
protocols, and the git tree of `idxsig/`.

## 1. Audit summary and the family chosen

Three families were audited read-only (scratch: `/tmp/opt_audit.json`). Labels: **failed config** (one frozen rule lost),
**evidence against the hypothesis** (the mechanism itself looks absent), **untested idea**.

| Family | What the evidence says | Label | Decision |
|---|---|---|---|
| Crypto pre-move ranking / admission (ADMISSION_v1, holdout) | At the owner's ~0.8% round trip every arm lost in 2023 and 2024-26. Score vs net return: Spearman about 0. Rank 1 is the worst rank. PAXG (a gold token) is rank 1 on 150 of 365 days. Probabilities were miscalibrated (12% predicted, 3-4% realised). | Evidence against selection; costs alone sink it | Stop on history. Only the pre-2020 backcast or prospective data are clean. |
| Crypto liquidation rebound (LIQ_REBOUND_v1) | Mean was negative before costs (-1.2% gross). It was worse than random entries and than drops without an open-interest collapse. Cascades kept falling about 22 hours and the 2023 screen did not replicate. | Evidence against the mechanism | Stop. Delayed-entry and no-stop ideas were seen after the fact. |
| MSCI Indonesia deletions (MSCI_DELETION_v1, OOT_v1) | +14.0% per trade on the discovery reviews (Nov19..Nov22), but -4.2% out of time. Excess over matched controls was positive in both periods (+11.1%, +4.5%). The out-of-time loss coincides with the equal-weight liquid market falling -8.1% over the same 20-session windows (post-hoc figure, `MSCI_DELETION_OOT_v1/VERIFICATION.md`). | Failed config (20-session spot hold); mechanism not refuted | **Chosen.** One lever, below. |

Ace's cash-tender acquisition census is not duplicated. Futures and hedged variants are a separate study (owner's
brief: no leverage to rescue a spot signal).

## 2. Diagnosis, and why a shorter hold could help (stated before testing; hypotheses)

The brief's diagnosis categories for the MSCI deletion trade:

- **Exits / holding period:** the leading suspect. Passive trackers sell in the implementation-day closing auction
  whatever the price. The academic literature on index deletions describes a temporary price concession that mostly
  reverses within days, not weeks. A 20-session hold keeps the reversal but adds about 20 sessions of unhedged IDX
  market exposure. Out of time, the equal-weight liquid market fell about 8% over the same windows (post hoc, in
  `MSCI_DELETION_OOT_v1/VERIFICATION.md`).
- **Timing:** entry is already in the forced-selling auction, the economically right point. It is not changed.
  Entry one session later is a stress (S1), not an option.
- **Selection:** the flow-intensity idea (passive selling as a share of normal volume) is untested and would need
  passive-weight estimates. It is not in this study.
- **Costs:** 0.15%/0.25% (Stockbit level, including the 0.1% sell tax) is small against a multi-percent concession.
  Doubled fees and one tick per side are stresses.
- **Allocation:** v1's account (equal slots, at most 25% and IDR 40m each, cash otherwise) is kept unchanged.
- **Data / evidence:** the event tables hold 111 deletion events in the 19 non-sealed reviews that have deletions; 99
  are scored at holds up to 10 (fewer after excluding Nov23, section 4). That is a small sample. The prices after
  2025-02-21 come from Yahoo.

Ex-ante expectation: shorter holds keep most of the concession's reversal and cut the market exposure roughly in
proportion to the hold. The risk is that the reversal is slower than the market drift, or that it is noise.

**Contamination, stated plainly.** Every review used here was inspected before, at holds 5, 20 and 60 and with entry one
session later. That showed the next-session close averaging +3.3% (development) and +4.2% (out of time) above the
auction price, and the relative effect mostly in by session 5. This rationale is therefore not independent of the data.
Any result is **EXPLORATORY**. In particular, if the walk-forward picks a hold of 1-3 sessions, gates W2, W4, W7 and W8
are close to settled by what was already seen: a CANDIDATE would then be the expected outcome and would add little new
support.

## 3. Data-exposure map

| Segment | Dates (entry sessions) | Reviews (with deletions) | Status for this question |
|---|---|---|---|
| Development | 2019-11-26 .. 2023-08-31 | 16 scheduled reviews Nov19..Aug23 (11 with deletions). Nov23 is excluded (section 4) | Inspected (MSCI_DELETION_v1: holds 5/20/60, S1, S2) |
| Sealed IDX holdout | 2024-01-02 .. 2025-02-21 | Feb24, May24, Aug24, Nov24 | No 2024 review list is fetched, and no trade, control or benchmark return for a position inside the window is computed. Using it for this question needs the owner's specific permission and spends it |
| Out of time | 2025-02-28 .. 2026-08-31 | 7 reviews Feb25..Aug26 (51 events) | Inspected (MSCI_DELETION_OOT_v1: holds 5/20/60, S1, S2) |
| Prospective | from MSCI's Nov 2026 review (announcement about 10-11 Nov 2026, implementation 30 Nov 2026) | - | Unseen; the only clean data without the owner's permission |

The sealed window's panel rows are loaded, as in MSCI_DELETION_OOT_v1: the trailing features at the first out-of-time
sessions (20-session volatility, momentum and traded value, the 60-session drawdown), the 60-session listing-history
requirement and listing-age bucket (presence rows) that decide control eligibility and liquid-market membership, and
the Feb25 liquid-market membership (20-session traded value) read prices, volumes and presence from it. What is never computed is a trade, control or
benchmark return for a position inside it. No unused historical evaluation data remains, so the
walk-forward below is a **discipline device**, not a validation.

## 4. The search (frozen)

- **One lever:** holding period H ∈ {1, 2, 3, 5, 10, 20} sessions after the implementation-close entry. That is 6
  configurations; H = 20 is the original rule and the **baseline**.
- **Fixed:** events (MSCI's own lists, both studies' `events_all.csv`), entry in the implementation-session closing
  auction, KOD's IDX harness (FILL-C capacity at IDR 40m and 10% participation, auto-rejection limits, registry
  corporate actions, `data_end_exit = last_close`), costs 0.15%/0.25%, 200 matched-control draws (seed 20261101) with
  every name MSCI changed in the review excluded, and v1's account (start IDR 160m).
- **Plans:** base, S1 (entry one session later), S2 (one tick per side), S3 (fees doubled to 0.30%/0.50%). That is 24
  harness runs per segment. Every one is in the trial log.
- **Nov23 excluded.** Its 20-session baseline hold runs past 2023-12-29 into the sealed window (INCOMPLETE). It would
  count as cash at hold 20 but as a real result at holds 1-10, which would bias both the selection and the comparison
  with the baseline. It is dropped from selection and evaluation, so every hold is compared on the same reviews
  (pre-freeze review finding).
- **Walk-forward (expanding, by review):**
  - The 23 remaining non-sealed scheduled reviews are taken in calendar order. The first 4 (Nov19..Aug20) only train.
  - Before each outer review k (19 outer reviews, Nov20..Aug26; 16 of them have a deletion), the hold is chosen on
    reviews 1..k-1 only.
  - The criterion is the log growth of v1's account at each H, averaged with its grid neighbours (anti-brittleness).
    The maximum is chosen, ties go to the shorter hold, and the review is held in cash if no smoothed value is positive.
  - That choice is applied to review k. Outer results never feed back into an earlier choice.
  - Purge: every trade at the longest hold must have exited before the entry of the next review that has a deletion
    (checked in code).
  - The hold the same procedure picks on all 23 reviews is reported, labelled in-sample, for a prospective protocol
    only.
  - The run aborts if any studied trade (a review in the order above, any plan and hold) is EXIT_DATA_END (scored at
    its last traded close because the name has no row at the window's end) or INCOMPLETE (its hold runs past the
    data). The feasibility counts show none in the base plan.
- **Selection is on account economics,** not on hit rate. Reported for every configuration and scope:
  - average win and loss, payoff ratio, expectancy per trade;
  - excess over matched controls, return over the equal-weight liquid IDX market;
  - account end, drawdown at review exits, P&L without the top 3 winners;
  - capital per review, nominal-hold exposure, turnover and fees per year.

## 5. Benchmarks

- **Cash** at 0% (IDR deposit interest is credited to neither side).
- **Equal-weight liquid IDX market under the same plan and window.** The liquid market is the names in the top quintile
  of 20-session median traded value at the signal session, excluding the review's MSCI-changed names, executed by the
  same harness. Only names that exit normally count (a name censored at a data end is left out). The trade's return
  minus this is its return relative to the market. That basket cannot be shorted, so it is not a hedged return; a
  hedged version would need a short index future and is not modelled here.
- **Liquid-market buy-and-hold over each block** (descriptive): the same equal-weight liquid market held from the
  block's first outer entry, rebalanced every 20 sessions, with costs charged once in and once out (this favours the
  benchmark). The development block stops at the excluded Nov23 review's entry session (2023-11-30). The out-of-time
  block runs to the window's end (2026-10-06), about a week past the last exit.
- **The H = 20 baseline** on the same outer reviews.

## 6. Promotion criteria (frozen before any result; the code's `gates()` governs)

- **W0** sample, a property of the data and not of the selector: the outer reviews hold at least 30 deletion trades
  scored with matched controls at every hold, from at least 10 outer reviews. Otherwise INCONCLUSIVE. An all-cash
  walk-forward therefore fails W1/W2, and one that holds cash most often fails W8; either is rejected, not called
  inconclusive.
- **W1** the walk-forward account ends above its start.
- **W2** walk-forward mean net trade return > 0, with its review-cluster bootstrap one-sided 95% lower bound > 0.
- **W3** the walk-forward account ends above the H = 20 baseline account on the same 19 outer reviews.
- **W4** walk-forward mean net > 0 in both blocks: development outer (Nov20..Aug23) and out of time (Feb25..Aug26).
- **W5** walk-forward account P&L without its 3 largest winning trades > 0.
- **W6** walk-forward mean net > 0 under S1, S2 and S3, with the holds selected under the base plan.
- **W7** walk-forward mean return relative to the equal-weight liquid market under the same plan and window > 0. That
  basket cannot be shorted, so this is a relative return, not a hedged one.
- **W8** not brittle: the most-selected hold (counted over the outer reviews with a deletion; ties go to the shorter
  hold, and a tie with cash counts as cash) and at least one grid neighbour both have positive outer mean net as fixed
  rules. It fails if cash was selected most often.
- **Verdict:**
  - EXPLORATORY_CANDIDATE if W0-W8 all pass; INCONCLUSIVE if W0 fails; otherwise EXPLORATORY_REJECT.
  - A candidate licenses only a frozen, paper-only prospective protocol from MSCI's Nov 2026 review (announcement
    11 Nov 2026, implementation close 30 Nov 2026), with a kill rule.
  - Whether to ask the owner to spend the sealed 2024 reviews is a separate decision. The earlier inspection would
    have to justify it, not this verdict.
  - It is never a live promotion and never evidence of future profit.
  - A reject or an inconclusive result ends this family's search on history.
  - One run. No other grid, plan, event set or window. The goalposts above are not moved after the run.

## 7. Known limits

- Closing-auction fills are modelled. Capacity is checked at IDR 40m. Exits are at closes, rolled past lower-limit
  locks by the harness.
- Drawdown is measured at review exits; intra-hold mark-to-market is not computed. Exposure uses the nominal hold.
- Prices after 2025-02-21 are Yahoo-sourced in the pinned panel. MSCI changes between reviews are missing.
- 23 reviews (clusters), several with no deletion.
- IDX settles T+2. A sale one session after a purchase is allowed and settles normally; no short sale is involved.
- MSCI's treatment of Indonesia is changing: additions frozen since January 2026, reclassification proposed with a
  decision by 30 June 2027. A past pattern is not a forecast.
- FILL-C sizes shares from the entry-session close, which is the closing-auction print itself. SKIP_LOT and
  SKIP_LIQUIDITY, and hence the account's slot count, therefore depend on the auction price rather than a pre-auction
  price. The frozen v1 code is reused unchanged, the effect is identical at every hold, and its direction is to drop
  the names with the largest concessions.
- No stop is used. Nothing here is a guaranteed maximum loss: a name can stay locked at its lower limit for several
  sessions, as GOTO and KPIG did out of time.

## 8. Feasibility (counts only, before the freeze)

`FEASIBILITY.json` has status and scored-trade counts per hold (5 control draws) and True/False flags that hold 20
(primary, S1, S2) and hold 5 reproduce the two frozen studies' committed trade files at 200 draws. These 12 files are
pinned. No return was printed.
- The first pass (`FEASIBILITY_pass1_repro_compare_bug.json`, kept) showed all flags False. The cause was a bug in the
  comparison of blank dates, not in the trades, and it was fixed.
- The file was regenerated after the pre-freeze review fixes.
