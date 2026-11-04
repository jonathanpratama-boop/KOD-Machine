# ATTENTION_HISTORY_v1: does retail attention on r/wallstreetbets add to the next-day dump forecast?

Frozen 2026-10-29, before any attention feature was computed. `protocol.json` is normative; `build.py` downloads post titles,
`run.py` is the one run.

**Question.** On the 6,225 US stocks that closed 30% or more higher in 2020-2023 (LEARNER v2.4's warm start), do four
features of r/wallstreetbets attention add out-of-time discrimination to v2.4's own 33 features, for the next-session dump
and the 5-session dump? Research says attention-grabbing stocks are bought by individuals and the price pressure reverses
(Barber and Odean 2008; Da, Engelberg and Gao 2011).

**Features.** Posts naming the ticker in the five days before the spike, on the spike day before the close, the spike-day
surge over the prior month, and a has-mention flag. Whole-token, case-sensitive ticker match; short tickers, jargon and
shouting titles count only with a `$`.

**Same procedure as TA_HISTORY_v1.** Fit 2020-21 and score 2022; fit 2020-22 and score 2023; paired AUC gain, week-cluster
bootstrap, Holm over two, Brier gain beside it. A block that adds is a candidate for v2.5 at v2.4's first claim look.
