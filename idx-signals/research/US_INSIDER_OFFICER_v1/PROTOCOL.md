# US_INSIDER_OFFICER_v1: do purchases by officers who are not board directors beat matched controls in 2023?

Written 2026-10-27, before any 2023 result of US_INSIDER_BUY was computed (its Stage 2 was never run; its Stage 1 failed G1 and G2).

## Where the rule came from (exploration, stated openly)
US_INSIDER_BUY Stage 1 (filings 2021-01-04 .. 2022-12-30, results_stage1/events_hold*.csv) split by filer type after the result was known.
Of seven splits looked at (n_owners, size, top_exec, officer, director, price band, lag), the largest was: the filer is an officer and not a
director. Hold 60: n 415, mean excess +5.85%, median +3.76%, t 4.6; 2021 +7.4%, 2022 +4.6%; hold 20 +3.7% (t 5.1); hold 120 +3.4% (t 2.1).
Directors who buy: +1.1% (t 1.8). Because the rule was picked after looking, Stage 1 is discovery only and proves nothing.

## The one test
- Events: US_INSIDER_BUY/events.csv, stage == 2 (filings 2023-01-03 .. 2023-09-29), officer True and director False. 180 events before mapping.
- Everything else unchanged from US_INSIDER_BUY: same panel (panel_us_repair-20261008T114805Z), entry next open after filing, 200 matched
  control draws per event, same costs, same week-cluster bootstrap (10,000 resamples, seed 20261203). Holds 20, 60 (primary), 120.
- Baseline: the matched controls. Excess = event net return minus mean control net return.

## Gates (hold 60; PASS only if both hold)
- **G1** mean excess > 0 with bootstrap t >= 1.65 (one-sided 5%, one pre-specified rule).
- **G2** mean excess >= 2.0%.

Reported whatever the verdict: holds 20 and 120, median, winsorised mean, hit rate, and the same statistics for all other 2023 insider events
(directors and director-officers) as a contrast. Run once. No rerun, no rule change after the result.

## Reading
- PASS: the officer-buy edge survived one out-of-sample year. Survivor-only prices push excess up, so it is a lead for a forward paper watch of
  new Form 4 filings, not a confirmed edge.
- FAIL: the Stage 1 split was noise or a 2021-2022 regime. Closed.

## Power note
About 150 scored events. If the true edge is +5.85% the expected t is near 2.8; if it is half that, near 1.4. A FAIL does not rule out a
small edge.
