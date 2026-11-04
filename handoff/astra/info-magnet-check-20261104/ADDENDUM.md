# INFO_MAGNET fast primary-gate operationalization v1

Frozen before inspecting historical price outcomes for this run, 4 November 2026. This is an additive implementation of the pending exploratory pilot, under the owner's instruction to accelerate the actual opportunity test. It does not modify Hermes's original plan or claim that its previously unspecified primary endpoint had already been locked.

Original branch: b04d31d5af7e34fa2f8e016bfffa8db1ab7ba13b. Original PLAN.md SHA-256: 92758d1df735862c193c27ccbf7bf9d6231e34055742233f2cdce2458d89809c. The original plan is exploratory; previous KOD studies already saw historical market prices. A positive result here can support the owner's next prospective paper gate, not a validated live strategy.

## Fixed primary question

For Upbit KRW listing notices, can entry at the first full hour after publication outperform five contemporaneously eligible random Binance spot-USDT instruments over a 24-hour holding period after charging the event trade the owner's assumed 2% round-trip friction?

24 hours is selected now, before price inspection, from the original plan's 6/24/72-hour choices. It matches a one-day catalyst holding period and is not selected from outcomes. 6 and 72 hours are descriptive secondary endpoints; they cannot rescue a failed primary endpoint. This accelerated run answers the primary tradability gate rather than pretending to reproduce every original leakage, mood, ignition-overlap and reaction diagnostic.

## Notices and population

Use only the 41 already-published raw Upbit pages plus the published 9–12 redownload. Never require a new live Upbit request. A title must contain the original plan's literal `마켓 디지털 자산 추가`. Extract uppercase alphanumeric ticker tokens inside parentheses, excluding market labels KRW/BTC/USDT. Preserve all notices and exclusions. Unique event = notice ID plus ticker. Exact duplicate page copies do not create new events. Conflicting versions or unparsed likely-primary titles require review and are not silently dropped to obtain a pass.

Use first_listed_at with its retained KST offset, converted to UTC; an offset-free source time is interpreted as Asia/Seoul and flagged. Primary = notice includes KRW market. Other BTC/USDT listings remain descriptive. No token alias, redenomination, 1000-prefix or current instrument substitution is inferred.

Primary historical notice window begins 2020-01-01 UTC. Price-data cutoff is 2026-11-01 00:00 UTC, the end of the last fully elapsed calendar month before this run. An event is mature only if its primary exit is no later than that cutoff. Later notices remain visible as outside this frozen mature window. Entry is floor(publication UTC hour)+1 hour, including publication exactly on the hour. Exit uses the close of the 24th hourly bar after that entry (entry+23h bar). A quote, top-of-hour open and no-lookahead feasibility are assumed historical proxies, not executable broker fills.

## Eligibility and data

Use Binance's official spot monthly 1h archives and official .CHECKSUM files. Both millisecond and post-2025 microsecond timestamps must be handled explicitly. Keep raw ZIPs outside git, checksums, actual fetch times, manifest, source URLs and errors. Historical symbol enumeration comes from the archive directory, including delisted names, rather than today's survivors.

A target/control is measurable as already trading before the notice only if it has a complete hourly bar immediately before the notice hour. This is a conservative archive-availability condition, not proof that every other coin was economically unavailable. Absence proved by archive metadata is UNMEASURABLE, not a zero return. Network/checksum/schema failures are unresolved evidence and cannot become eligibility exclusions. Eligibility never depends on the later exit bar or its return. A missing later entry/exit remains unresolved, not a reason to resample or remove a loser.

Controls: enumerate all historical archive symbols ending in USDT, remove the exact predeclared stable/fiat/leveraged/security exclusions in EXCLUSIONS.json, remove the event ticker, and shuffle with a deterministic SHA-256-derived seed from `20261104|event_id`. Take the first five with evidenced pre-notice-hour availability, without replacement. Do not replace a selected control because its later outcome is unavailable. This avoids screening controls by future performance or requiring a full six-year panel. There is no liquidity/volume winner filter. The static product exclusions are not guaranteed to classify every historical token perfectly; report this limitation.

## Returns, costs, uncertainty and decision

Gross event/control return = exit hourly close / entry hourly open - 1. Original pilot net event return = gross - 0.006. Owner-cost net event return = gross - 0.02. These are explicit additive return-point friction assumptions, not current authenticated account fees, and exclude additional spread/slippage/FX. Conservative paired excess = event gross - mean(five control gross returns) - event round-trip friction. Controls are a gross opportunity benchmark; charging the same cost to both sides would cancel the cost and fail to test the owner's friction hurdle.

Keep one row per event with its controls, failures and exclusions. Estimate the mean across event rows. Confidence interval: 10,000 nonparametric bootstrap resamples of UTC notice-date clusters, resampling the number of distinct dates with replacement and retaining all event rows in each sampled date; event-weighted mean within each replicate. Seed 20261104. Report percentile 2.5/97.5 bounds. Same-asset dependence across different dates is not fully modeled; this remains an exploratory pilot. No subgroup, threshold or holding-period search is permitted after outcomes.

Primary gate can pass only if: at least 30 measurable primary events; no unresolved primary candidate caused by parsing/revision/data/outcome/control failures; mean owner-cost event return is above zero; and the 95% lower bound of mean owner-cost paired excess is above zero. Separately report the original 0.6% cost result. A failure or unresolved run must not be relabelled a validated opportunity system. A pass supports only the previously specified prospective paper logging decision; no funded order or automatic strategy promotion follows.

## Execution and closeout

First publish this addendum and exclusions before reading price outcomes. Preserve the freeze commit and hashes in the result. Then execute the runner against archived notices and targeted event/control windows. Do not wait for the unrelated 30-slot cloud collector. Produce the result, exact denominator, coverage/error ledger, manifest and short decision now. Publish new work on its own branch; do not overwrite Hermes's branch or frozen server code.
