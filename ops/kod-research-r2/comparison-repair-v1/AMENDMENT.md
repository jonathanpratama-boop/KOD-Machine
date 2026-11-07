# Daily comparison-input repair — 7 November 2026

The owner requested repair of missing matched comparisons while keeping cloud
collection running. The original daily warmup and complete-hour assembly leave
the partial launch day absent. Requiring 30 complete preceding UTC days then
prevents the liquidity feature used for matching throughout the cohort.

Supply the preceding 30 completed Binance spot daily candles for each fixed
primary asset through the engine's existing `daily` input queue. Refresh when
that preceding-day window is incomplete. Retain the exact response, request and
receipt clocks in the existing acquisition archive. These are newly received
historical liquidity inputs, available only from their actual receipt onward.
They do not fill old minute/hour gaps, repair coverage, create old signals, or
change any earlier event/control selection. Earlier unavailable controls remain
unavailable. Matching still uses the same preceding-24-hour momentum, preceding
30-completed-day median liquidity, percentile distance and deterministic ties.

This adds no signal, threshold, exit rule, cost change, universe change, trading
order or new admission period. It requires no collector restart. SQLite serializes
the short input-enqueue transactions alongside normal engine transactions.

The archive also retains this amendment and the input worker's source bytes.
Existing automatic archive and engine-ledger backups include the new evidence.
For deterministic restoration, use `input_loader_with_comparisons` from the
archived worker with the original engine's `rebuild_from_exports`; it resolves
the new input identities from original archived daily responses. It fetches
nothing during restoration. All other inputs use the original recovery loader.

The results display reports completed 24-hour outcomes only. Pending, censored
and missing comparisons remain distinct. Four timing arms on one market event
remain one independent event. Modeled returns subtract the existing two
percentage point assumption; quoted prices are not confirmed fills.

The first daily refresh successfully received all 130 source responses, but its
request burst pushed the existing collector's conservative shared-IP weight
check over 300. That check wrote a provider-stop flag despite HTTP 200 (reported
weight 312), rather than an exchange denial. Preserve that flag and the gap,
resume the collector, and spread subsequent daily refresh requests one second
apart. Actual provider-denial handling continues to apply.
