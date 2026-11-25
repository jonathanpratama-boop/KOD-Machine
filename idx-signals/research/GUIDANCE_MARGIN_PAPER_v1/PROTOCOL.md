# Guidance margin paired paper pilot

## Question

Does adding an improvement in a company's full-year operating-margin guidance improve the results of a revenue-raise rule, at the same decision time and after the same assumed costs?

This is prospective paper research. It cannot send orders. Its first deliverable is a working, measured comparison within days of eligible decisions, not a promise of profit or statistical significance within days.

## Population and sources

The source population is the earnings releases observed in PRNewswire's earnings RSS feed. It is not all US filings or all public information. Poll approximately every ten minutes, retain each received feed/release and its receipt time, and deduplicate by release URL. SEC and GlobeNewswire access were unavailable from the server at setup; this limitation is explicit rather than disguised as an empty result.

Only USD instruments with an identified US ticker and CIK are eligible. The existing 16 October 2026 SEC ticker map is retained with its hash; unknown or conflicting identities need review. The wire's issuer archive supplies the prior-release inventory. Comparability and the latest prior mean within this declared wire-source coverage, not an exhaustive assertion about SEC or issuer disclosures elsewhere. Retain the inventory and any access failures.

At startup, releases published within the previous seven calendar days may be reviewed for **INITIAL_RECENT** enrollment. Later publications form **NEW_RELEASE**. Both enter only at future scheduled prices after their decisions are recorded. These cohorts are reported separately. Old development cases and any past price performance cannot become prospective results.

## Facts and review

Require a comparable, consolidated, full-year revenue level and either operating-profit level or operating-margin forecast in both the current and latest covered prior release. Use the midpoint of explicit ranges. Revenue growth alone, EPS, EBITDA, net income and segment profit do not substitute for these quantities.

The same issuer, fiscal period, currency, units, accounting definition and consolidation perimeter must be supported. A changed definition or acquisition scope is an exclusion unless a comparable restatement is explicitly supported. Unknown values remain unknown. Source quotations and numeric spans are checked against retained source text. A model cannot certify source authenticity simply by asserting it.

The API reads source text without price outcomes. A second source-only review checks the candidate and comparison. Where automated checks and the declared source inventory cannot support a pair, retain it as excluded or needing review; never invent a prior or set a missing quantity to zero. Clearly label model-reviewed facts. Any supervised correction records its actual review time and retains the original proposal.

All sources, extractions and decisions must precede the admission's scheduled entry. A received timestamp is when KOD actually obtained the document, not its publication timestamp. New facts cannot be inserted into an already sealed decision.

## Two paired policies

The revenue arm takes an eligible forecast whose midpoint is at least 1% above the prior midpoint. The revenue-plus-margin arm takes the same event only if its implied operating-margin midpoint also increases. Otherwise that arm stays in cash. The extra margin condition is the only difference.

Each arm starts with $10,000 of simulated cash. An event reserves a common $1,000 slot in both arms, including when one stays in cash, for the same holding window. At most ten slots can be active; both arms must have sufficient cash after realized losses. Only one active event per issuer is permitted. This prevents the filter from benefiting from a different opportunity queue or implicit borrowing. Cash earns zero in the comparison.

After the reviewed decision is sealed, entry is the next scheduled XNYS 09:30 open. Use the same next feasible session for both arms, including holidays. Reject sources that miss the declared age window. Use the observed daily open with an assumed 0.25% entry cost and the daily close with an assumed 0.25% exit cost. The entry price must be at least $2. These are modeled fills, not executable quotes or verified broker fees; market impact and fill uncertainty remain limitations. No leverage, shorts or real orders.

The primary holding period is 20 exchange sessions, counting entry day as session one. Show hypothetical net liquidation results at sessions 1, 3 and 5 as early descriptive observations. No stop or parameter tuning based on these results. Retain every missing entry, missing outcome and corporate-action exception. An unavailable scheduled entry never becomes a later, conveniently selected entry. A late terminal observation is not the scheduled session-20 result.

## Result reporting

Show source arrivals, successful retrievals, reviews, exclusions, unresolved cases, admissions, fills, missing marks and completed pairs. For each horizon show both arms' net dollar results on the same slots, the difference, and the number of paired events. Show the two publication cohorts separately. Zero observed trades means no trade evidence, not a zero-return finding.

The first operational review is 20 November 2026: did collection and extraction work, did eligible pairs arrive, and did the margin condition change decisions? Any 1/3/5-session results available then are descriptive. The first scored day follows the first actual entry; a date cannot be guaranteed before a qualifying event exists. The 20-session comparison matures later. Early peeking does not authorize a claim of proven edge; small samples, correlated issuers/dates, source coverage, model errors and modeled costs must remain visible.

This pilot assesses added information in the margin filter. It does not by itself isolate whether an LLM is better than every possible mechanical extractor, nor establish that the revenue rule or either account is profitable.

## Operation and credits

Run collection, API reading, admission, price marking and dashboard updates on the existing cloud server. Keep the old R2 study separate and running. Preserve a hash-chained decision journal and timestamp the policy before the first admission.

Use the already issued $57 promotional API credit for new disclosure reading and source-only verification, with request/usage receipts and conservative cost estimates. Avoid duplicate paid reads and repeated retries of unchanged failures. Reserve enough balance for an in-flight request and stop new paid calls before the benefit expires at 2026-12-03 13:41:10 UTC. Paid calls stop at the credit boundary; price scoring, existing positions and free collection continue. No credits are purchased. Spending the entire benefit is not a success metric.

Raw releases, raw model responses and the API key remain in private operational storage. Publish only code, the frozen policy, counts, modeled results and usage estimates through the existing dashboard/backup path.
