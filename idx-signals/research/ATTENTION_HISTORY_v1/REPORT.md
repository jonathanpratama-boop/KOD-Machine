# ATTENTION_HISTORY_v1: result (one look, 2026-10-30)

Protocol `protocol.json` (frozen 2026-10-29), run once by `run.py` over 2,094,273 r/wallstreetbets posts from 1,520 days
(2019-11-01..2023-12-29; every day file hashed in `results/REDDIT_MANIFEST.json`). Every number below is in
`results/RESULT.json`. Counted trial `ATTENTION_HISTORY_v1_result.json`, the result of the PENDING registration (one trial).

**Question.** On the 6,225 US stocks that closed 30% or more higher in 2020-2023, do four features of r/wallstreetbets
attention (posts naming the ticker in the five days before, on the spike day before the close, the spike-day surge over
the prior month, a has-mention flag) add out-of-time discrimination to LEARNER v2.4's 33 features? Fit 2020-21 and score
2022; fit 2020-22 and score 2023.

## Decision (Holm over two, paired AUC gain over v2.4's features, Brier gain beside it)

| Statement | AUC: v2.4 features -> with ATTN | Gain [95%] | 2022 | 2023 | Brier gain | Verdict |
|---|---|---|---|---|---|---|
| next session closes 10% lower, on its own | 0.624 -> 0.627 | +0.003 [-0.001, +0.006] | +0.003 | +0.003 | +0.0006 | **DOES NOT ADD** (p 0.052, Holm 0.104) |
| 5-session plan ends 10% down, on its own | 0.613 -> 0.616 | +0.003 [-0.001, +0.006] | +0.005 | +0.001 | +0.0006 | **DOES NOT ADD** (p 0.075, Holm 0.104) |

The block alone discriminates barely above chance (AUC 0.50 to 0.54 across folds and statements).

## What the data showed

- **Coverage is far lower than the plan's sample suggested.** Any post naming the ticker from five days before through
  the spike day: 13% of events in 2020, 34% in 2021, 14% in 2022, 10% in 2023. The plan's 43% came from 23 sampled
  events weighted toward 2021 and matched without the frozen `$`-rule for jargon and shouting titles. In the two scored
  years, nine spikes in ten had no post at all.
- **The sign is the expected one.** The spike-day surge over the prior month carries a positive coefficient for the
  next-session dump in both folds (+0.20, +0.21): a burst of posts on the spike day goes with a dump the next day, as the
  attention-reversal literature says. It is simply too rare and too weak, at this coverage, to move the ranking.
- **2021 was fit-only by design.** The meme-stock year, where attention was densest, chose nothing and was scored on
  nothing; the test asked whether attention helps in ordinary years, and it does not.

## What it does not show

- **That attention never matters.** Titles only, one subreddit, a third-party archive; comments, other forums and the
  2021 regime were not tested.
- **A worse model.** The gain is positive but inside the noise; v2.4 is unchanged either way.

## Use

Per the protocol, the block does not become a candidate for v2.5; nothing in LEARNER v2.4, any ledger, register or
routine changes. PLAN_v2's decision 3 (whether the nightly run may read the Reddit archive) is moot. The downloaded day
files stay in the git-ignored cache, hashed, in case a later study (comments, the 2021 regime, other attention sources)
needs them.
