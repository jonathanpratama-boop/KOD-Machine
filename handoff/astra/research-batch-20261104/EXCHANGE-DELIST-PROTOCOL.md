# KOD batch 01 — exchange delisting warning test, v1

Status: exploratory historical research; no orders, shorts, leverage, strategy promotion or changes to existing experiments.

## Hypothesis and decision
An official announcement removing an asset from all Binance spot trading creates a dated loss of market access and liquidity. The prediction is that the affected asset underperforms an equal-weight BTC/ETH benchmark over the next 24 hours after a feasible one-hour processing delay. This tests a warning/avoidance signal, not a profitable short or a buy strategy. It does not assert forced sales or identify who sold.

The practical question is whether KOD should spend further research effort validating this warning for an already considered/held asset. It does not assume the owner would otherwise buy all affected assets. Cash versus hypothetical buying is descriptive only.

## Frozen source and event definition
Use official Binance CMS Delisting catalog 161, every available article page, in release-time order. Retain raw responses, errors, reported total, duplicates and catalog coverage. Before this protocol, only catalog identifier/name/count (446 reported articles) was observed; no announcement titles, bodies or prices were inspected for this test. Current catalog counts can change.

Candidate titles must say Binance will delist named assets, and must not identify only futures contracts, margin, leveraged tokens, isolated trading pairs, removal of spot trading pairs, or migration/swap/rebranding. Candidate article bodies must explicitly confirm cessation of all spot trading pairs for the affected asset. A generic remove/delist keyword is insufficient. Save every candidate and exclusion with its reason. Strict ticker identity: each target must be explicitly named in the article and have an exact historical <TICKER>USDT spot archive. Names without explicit symbols require review and remain unresolved. No symbol substitution based on returns. Later coin migrations are not silently joined.

Release timestamp is the CMS publication timestamp. Record that later edits and original first availability may be unverifiable. Separate announcement from effective delisting. Explicit UTC effective datetime must be at least 24 hours after the entry; earlier or unknown deadline is structurally ineligible, never a negative price outcome. Cancellation or corrections known before entry invalidate eligibility; later changes are retained as outcomes, not deleted. Historical current-page revisions limit point-in-time validity and are disclosed.

Development: announcements 2020-01-01 through 2022-12-31 UTC. Fixed-rule temporal validation: 2023-01-01 through 2023-12-31 UTC. No 2024+ outcomes loaded. These historical years have been used in other KOD studies; neither segment is an untouched global holdout. No horizon, threshold or universe changes after results. Later-period articles remain inventory only.

## Frozen measurement
Entry proxy: first full UTC hour strictly after announcement (floor(timestamp/hour)+1 hour), representing up to one hour of processing delay. No pre-announcement entry. Require a completed positive-volume target bar before publication hour. Exit: close of the 24th hourly bar starting at entry (entry+23h). Require all 24 completed hourly bars, positive price and positive volume at entry/exit. Missing or malformed required bars are unresolved, not zero returns, wins or exclusions silently dropped.

Compare target simple return to the equal-weight simple returns of BTCUSDT and ETHUSDT over exactly the same timestamps. Fixed majors control broad market movement but do not match altcoin size/liquidity/distress; no causal claim. No control resampling. Primary effect: target return minus benchmark return, predicted negative. Keep gross relative effect distinct from costs.

Costs are assumptions, not verified account tariffs: hypothetical target spot round-trip costs 0.30% total (0.15% per side, prior approved Binance model), with owner-friction stress 2.00% total. Target net = gross minus assumed cost. No fee is deducted to make the primary negative-relative forecast easier to pass. Notional-free arithmetic is not executable portfolio performance; order book, size, product access and real fills remain unknown.

## Analysis and gates
One row per article ID / explicit target. Deduplicate identical identity and release, retain provenance. If repeated notices for a target have overlapping 24-hour windows, retain first by release/id for primary scoring and flag later duplicates. Group all target rows by UTC announcement date to avoid treating simultaneous assets as independent. Primary statistic is event-weighted mean paired excess. Fixed bootstrap: sample whole announcement-date clusters with replacement, 10,000 replicates, seed 20261104, percentile interval.

Report development and validation separately. A warning merits forward testing only if each has >=30 scored target events, >=10 distinct announcement dates, no unresolved primary candidate, negative mean paired excess and the upper bound of a 98.333333% two-sided interval is below zero. This interval reserves family-wise error for the batch's three hypotheses (0.05/3); no side experiment can rescue a failed primary. Small samples give INSUFFICIENT_EVIDENCE, not PASS. A significant result is historical association and only eligibility for a future paper test, never validation of a trade.

Before price outcomes: two independent reviewers must agree on every primary event's asset, publication time, effective deadline and all-spot-delisting classification, and review a fixed sample of 20 rejected articles (earliest sorted release/id from development/validation). Any candidate ambiguity is unresolved. Freeze and hash the approved event register before reading outcomes. Do not add more titles or tune the parser to improve returns.

Stop early on source coverage, identity or availability failures. Report exactly what was tested and what remains blocked. Reuse existing verified Binance archive loader and raw checksums; independent arithmetic/source review after computation. No continuous scanner or future alert is claimed by this finite run.
