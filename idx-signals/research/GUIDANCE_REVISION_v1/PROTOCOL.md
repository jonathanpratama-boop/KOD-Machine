# GUIDANCE-REVISION-v1: first paper decision

Status: unvalidated research policy. Local shadow ledger only; no broker orders.

Question: can a comparable increase in an issuer's full-year revenue outlook be identified from source documents and turned into a fully specified paper decision at the actual decision time? This first operational cohort does not test profitability or represent the entire US market.

## Cohort and source selection

Reuse the seven continuing issuers from the ten-announcement access sample: AAL/CIK6201, MATX/CIK3453, ACU/CIK2098, ABT-Abbott/CIK1800, AEP/CIK4904, AXP/CIK4962, AMD/CIK2488. HES is not silently replaced: its old listed security ceased to exist and is excluded from this current operational cohort. Broker identity must agree with the issuer; an identical crypto ticker does not count.

At the first run, retrieve current SEC submissions for every cohort issuer. Retain every exact-form 8-K reporting Item 2.02 whose filing date is within seven calendar days before this protocol freeze, up to the freeze's UTC date. Retain older documents only to identify the most recent comparable prior guidance for the same fiscal year, looking back at most 400 days and fetching at most eight earlier Item 2.02 packages per issuer. Sort the current event inventory by SGML acceptance time, CIK and accession. Do not replace absent, inaccessible, duplicate, unchanged or negative events with a better example. Stop after the inventory is evaluated; do not search other issuers to force a buy.

The first run may evaluate recently disclosed information for a new decision today. Its acquisition is late and is explicitly marked BOOTSTRAP_EXISTING_INFORMATION. It earns no historical detection credit. Subsequent events acquired after freeze are marked FORWARD_ACQUISITION, with actual collection times. No historical 2024+ price panel or outcome is read. The existing ten 2021 announcements are extraction fixtures only, never performance observations.

## Feature

Only numeric full-year consolidated revenue guidance, in either a revenue level or a growth forecast over the same base year, qualifies. Compare the latest prior guidance actually available before the current release, including preliminary updates. Compare midpoints for closed numeric ranges. A point is a range of equal endpoints. Convert growth guidance to level factors (1 + growth/100), so a move from 37% to 50% growth is a 9.489% increase in forecast revenue, not a 13% stock-return forecast.

Require the same issuer, fiscal year, metric, currency, units, consolidation/business scope and growth base. EPS, quarterly guidance, production volumes, new fiscal-year forecasts without comparable priors, withdrawals, open-ended ranges, restated or acquisition-incomparable forecasts do not qualify. Classify them explicitly; ambiguity is REVIEW_REQUIRED. A positive revision is strictly greater than zero, with no fitted size threshold. Preserve unchanged and lowered cases as comparator observations. No +30% price filter, insider filter, technical ranker or consensus feed.

Extraction is a source-cited structured review, not an autonomous sentiment model: retain exact quotations, document paths/hashes, character spans and comparability fields. Numeric direction is computed, not supplied as an opinion. A reviewer must verify the latest-prior assertion; missing proof blocks a signal. A quote appearing in a document is evidence of content, not proof of economic interpretation.

## Clocks and paper entry

Interpret the SEC submission's own ACCEPTANCE-DATETIME as America/New_York, with the date-specific UTC offset. SEC acceptance is the conservative system source time, not an assertion of first press-release publication. Keep actual acquisition and review-completion times. Information available to this run is max(current/prior retrieval-completion, source acceptance, review completion). Add an explicit 15-minute processing allowance. Never backdate a decision or use an old quote as a new fill.

Candidate paper entry: first regular NYSE session's 09:45 ET strictly after that decision-ready time. Cancel if that scheduled entry is later than the second regular session after the current SEC acceptance. At that time require an account-eligible, verified underlying US stock at 1x, no financing, fresh bid/ask at most 60 seconds old, positive ordered prices and spread at most 0.50% of midpoint. Current closed-market quotes are references only. Entry is a newly observed ask plus 0.10% execution stress, valid for one minute; no retrospective fill and no pending broker order. If the collection misses the entry minute, record MISSED_ENTRY; do not reconstruct a fill later.

On weekends or before the entry time, record PAPER_WAIT with exact next conditions. Failed feature gives NO_SIGNAL; missing source gives DATA_BLOCKED; unavailable execution evidence gives EXECUTION_BLOCKED. These are complete paper decisions with zero filled exposure. They are not trades or wins.

## Exit, sizing and capital

Research account assumption: USD10,000, all cash at start, no leverage. This is a simulated account, not the owner's balance or accepted real-money loss budget. Max one position in this first operational cohort. Max 10% of equity notional and 0.5% equity planned loss including modeled fees. Enforce both and cash affordability.

Protective stop is 5% below entry, active only after an observed paper fill. No trailing rule and no take-profit in this policy. Fixed time exit at the close of the twentieth regular session counting the entry session as session one. It is a weeks-long guidance hypothesis, an explicit change from the old five-session experiments. A target is not invented to justify entry. Sell at the first observed valid bid after a stop trigger or time exit, minus 0.10% execution stress. A gap can exceed the planned stop loss. Missing quotes produce an unresolved exit, not an assumed stop-price fill. New halts, corporate actions and identity changes block mechanical scoring pending source review.

Primary cost assumption: USD2 commission on each side, actual observed bid/ask spread already included in entry/exit prices, plus 0.10% execution stress each side. Stress column adds another 0.25% each side. These are conservative model assumptions, not verified account-specific tariffs. A PAPER_WAIT can be recorded before exact broker product/stop support is verified; no fill can. Do not double count spread. Ordinary planned loss, full-notional gap exposure and fees are separate values. Mark open positions to valid bid and reserve cash at fill; no capital oversubscription.

## Evaluation and finish condition

Save a hash-bound protocol before current document bodies or outcomes are examined. Use a separate research ledger, reusing the existing paper-chain convention without changing the daily production paper ledger. Record all cohort source statuses, events and decisions. Freeze a decision before its entry/outcome. Duplicate accessions and issuer/fiscal-period episodes cannot generate duplicate positions.

First milestone: one complete, source-bound current paper decision with a signal or explicit rejection/blocker, actual decision time, future entry/expiry, fixed exit/risk policy, costs and zero or verified simulated exposure. A historical AMD fixture must also demonstrate the positive extraction path. This milestone does not require or permit fabricating a buy, a fill or a 20-session return today.

Positive, unchanged and lowered events will eventually be compared under the same declared entry/exit convention. Do not infer an edge from the first decision or first small batch. No historical outcome run, paid data purchase, parallel research family, schedule change, real order, parameter sweep or policy promotion is part of this milestone.
