# PATH_HISTORY_v1, addendum 3: pre-spike volatility, honest names, and the first build attempt

Written 2026-10-29, after the independent quantitative review of 7c9013a reached the lab and before any result of this
study was read.

## The first build attempt

The first run of `build.py` stopped on its first event with a type error: the register's cone carries one prior per
market, and the outcome grader expects the market's own. In memory it had simulated that one event's plan and its
twins' before stopping; nothing was written, printed or read. `results/events.csv.gz` does not exist. The fix resolves
the prior per market as the live register does (`speculation.build_set`); no outcome logic changes. Because committed
research files are never edited, the corrected scripts are `build2.py` and `evaluate2.py`, which supersede `build.py`
and `evaluate.py`; the originals stay as the record of the first attempt.

## Two features of block P1 change before anything is scored

The review's first-ranked addition is the stock's volatility *before* the spike and the spike measured in units of
it. P1's `vol20` as frozen was the 20-session standard deviation through the close of d, which the spike day
dominates: it is mostly the spike's own size again. It is replaced by:

- `vol20_pre`: the 20-session standard deviation of log returns through the close of d-1 (at least 15 returns);
- `spike_z`: the signal-day return divided by `vol20_pre`, capped at 50.

Everything else in P1 is unchanged. The context prior (CONTEXT) does not use either.

## Names

- The PATH labels are **twin-filtered paths**: the stock crossed the stated barrier and fewer than half of its twins
  did. A stock up 31% beside twins up 29% carries the label. The labels are what the live learner grades, frozen; the
  report calls them by this name and never "the market removed".
- `news` in block E_US means **an 8-K, 8-K/A, 6-K or 6-K/A with a filing date on the previous session or on d**.
  Absence is "no such filing", never "no news"; `has_edgar` records whether the stock's filings were read at all.
- `atm12m` is a **424B5 prospectus supplement in the previous 365 days**, a proxy. It is not an active at-the-market
  agreement and not evidence of sales that day; `shelf3y` is a shelf, not an agreement.
- `short_ratio` is FINRA's consolidated daily short-sale volume share, which includes market makers' short sales.
  The literature on short interest uses other data; this feature is a hypothesis.

## Interpretation, from the review

- AUC and the Brier gain are reported separately and are not interchangeable: a better Brier score can come from
  calibration alone. The decision rule asks for both.
- The study's time-to-confidence reading is conditional on an idealised learner; the gate simulations report shares
  of all runs, and a median is a median over all runs or it is not reported.
