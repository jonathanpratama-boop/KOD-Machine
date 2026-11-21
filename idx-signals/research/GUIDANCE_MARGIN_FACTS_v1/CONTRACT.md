# GUIDANCE_MARGIN_FACTS_v1 — offline fact contract

Version 1, 16 November 2026. Development only. This qualifies source-bound facts, not trades. It calls no model, schedules no usage, opens no prices and claims neither an edge nor LLM superiority. Historical examples are development fixtures, never a holdout.

## APIs and statuses

`qualify(pair)` returns `{"status": ..., "reasons": [...], "derived": ...}`. Status is `FACTS_READY`, `MISSING`, `INCOMPARABLE`, or `UNVERIFIED`. Reasons are human-readable strings. Derived is null unless FACTS_READY. Extra diagnostic output is allowed. A missing required input must never yield FACTS_READY. Known incompatibility takes precedence over missing input, which takes precedence over unverified input. Report all observed blockers, not only the winning status.

Contradictory integrity evidence raises `ValueError`: wrong supplied hash, invalid span, nonfinite/boolean numerical value, reversed range, negative spread, mismatched numeric token, invalid supplied timestamp/chronology, unknown provided schema or enum. Missing values are not malformed provided values: they produce a non-ready status. A non-object pair is ValueError. No unknown is silently zero or false.

`record_revision(record, path)` validates and appends to the existing paper hash-chain ledger format, returning the appended chained record. It qualifies `record.fact_pair` and stores the result under `qualification`; callers may not supply or override that result. Non-ready observations are allowed; integrity-invalid records are not. All validation and append decisions happen under an exclusive file lock. No old line is rewritten.

## Exact pair schema

Required top-level fields: `schema_version` = `guidance-margin-facts/v1`; nonempty `event_id`; `purpose` = `development`; `current`; `prior`; `external`; `clocks`. Unknown extra fields may be retained but cannot override required meanings.

Each document requires:

* `issuer_cik`: digit string, compared numerically so leading zeroes do not change identity.
* `period_start`, `period_end`: ISO dates, start before end; both documents must have identical dates.
* `period_kind`: FULL_YEAR. A supplied different period is INCOMPARABLE.
* `basis`: GAAP or ADJUSTED; `definition_id`: specific nonempty accounting definition. Both must match. An adjusted label without its precise definition is insufficient.
* `perimeter_id`: nonempty consolidated-company perimeter identity; must match across documents and be externally verified.
* `source`: fields below.
* `revenue` plus exactly one of `operating_profit` or `operating_margin`: metric objects below. Both profit and margin present is ValueError; neither is MISSING. EPS, EBITDA, net income, gross profit, FCF or segment NOI are incompatible substitutes, not accepted profit fields.

Required source fields: nonempty `id`, `url`, `raw_text`, `sha256`, `locator`; `representation` = `retained_excerpt`; `published_at`; `received_at`. URL identifies the source, locator identifies table/page/row. Hash is lowercase SHA256 of the exact UTF-8 raw_text. It proves retained-text integrity, not issuer authenticity. Offsets refer to this retained text, not an unretained original page. Short identified excerpts are sufficient for offline fixtures; do not falsely label their hash as a whole-document hash. Publication is a known publisher clock, not proof that no earlier channel existed. Receipt is actual KOD receipt, not a date inferred from a filename or earnings call.

Metric shape:

```json
{"form":"range", "unit":"USD_MILLIONS", "qualifier":"exact",
 "low":{"value":100,"start":0,"end":3},
 "high":{"value":120,"start":4,"end":7}}
```

Forms: `point` uses a `point` number object; `range` uses `low` and `high`; `center_spread` uses `center` and `spread`, yielding bounds center ± spread. Each number object has finite numeric `value` (not bool) and integer character offsets `start`, `end`, with 0 <= start < end <= len(raw_text). These are Unicode character offsets, not UTF-8 byte offsets. After trimming whitespace, removing optional dollar sign, commas and trailing percent sign, and interpreting enclosing parentheses as negative, the exact slice must parse to value. Do not infer unprinted multipliers. A complete source with mismatched hash/token/span raises ValueError; absent source/text/hash/number/span is MISSING. Numeric agreement does not prove semantic entailment; metric binding remains externally reviewed.

Revenue and operating profit use USD_MILLIONS in this narrow version. Direct operating margin uses PERCENT (12 means 12%, not 0.12). Other currencies/scales are INCOMPARABLE until explicitly normalized by a later contract. `qualifier` is exact, approximate, or ambiguous; ambiguous is INCOMPARABLE. Never fabricate a midpoint from “low end”, “at least”, or a verbal growth rate without an absolute denominator. Exact and approximate numerical bounds retain their qualifier.

## External attestations and clocks

Required external shape:

```json
{"attestor":"reviewer-or-inventory-id",
 "source_authenticity":"VERIFIED", "metric_binding":"VERIFIED",
 "prior_completeness":"VERIFIED", "latest_prior_source_id":"prior-document-id",
 "basis_comparable":"VERIFIED", "perimeter_comparable":"VERIFIED",
 "evidence_notes":"what source inventory and comparison were checked"}
```

Status fields accept VERIFIED, UNKNOWN, FAILED. UNKNOWN yields UNVERIFIED. FAILED authenticity, metric binding or prior completeness yields UNVERIFIED. FAILED basis/perimeter comparability yields INCOMPARABLE. Missing fields or empty attestor/notes yields MISSING. Latest prior source ID must equal the supplied prior source ID; disagreement is INCOMPARABLE. A known issuer/period/basis/definition/perimeter mismatch is INCOMPARABLE even if figures look attractive. Acquisition and accounting-recast cases must not quietly pass. These fields are **trusted external inputs**; arbitrary JSON cannot prove an exhaustive source search, and an LLM cannot self-certify it by writing VERIFIED.

`clocks` requires `extracted_at` and `decision_at`. All timestamps are timezone-aware ISO 8601. Null means known-unknown and yields UNVERIFIED; absent key means MISSING. Readiness requires prior publication < current publication; each publication <= its receipt; both receipts <= extraction <= decision. Invalid provided timestamps/reversed chronology raise ValueError. Actual future capture can satisfy this even though historical fixtures lack receipt clocks. Historical download time must not masquerade as historical signal availability. This module installs no collector.

## Derived quantities

Only FACTS_READY has derived values: `current_revenue_midpoint`, `prior_revenue_midpoint`, `current_margin_midpoint_pct`, `prior_margin_midpoint_pct`, `revenue_revision_pct`, `margin_revision_pp`. Midpoint is arithmetic mean of endpoints or supplied point/center. Both revenue midpoints must be positive, otherwise INCOMPARABLE. Profit can be negative. For profit fields: margin = 100 * profit midpoint / revenue midpoint. For direct margin: use its midpoint. Revenue revision = 100 * (current revenue midpoint / prior revenue midpoint − 1); margin revision = current minus prior percentage points. Negative and unchanged changes are valid observations. Do not compute percentage profit growth across zero.

Midpoint ratios are conventions, **not expected ratios** or confidence intervals. No joint distribution of revenue/profit is assumed. No positive-sign threshold, one-percent raise, trading policy, account engine or price-derived filter belongs here. Comparing a revenue-only fact with this added fact does not establish LLM superiority; that needs a non-LLM reader with the same information.

## Append-only corrections

Caller record fields: nonempty globally unique `id`, nonempty `event_id`, `revision_of` (null for first record, otherwise current event-head ID), timezone-aware `recorded_at`, and `fact_pair`. Event IDs must match. First record for an event requires null revision_of. Revisions must target the current head of that same event, not an unknown, another event or a stale head. Recorded time is actual correction-known/append time: at least the supplied decision time when known, and strictly later than prior head recorded_at. Newly learned evidence cannot be backdated into an old decision.

Verify the existing hash chain, identify event heads, check uniqueness/supersession/time, and append while holding the **same exclusive lock**. Reject corrupt chains, duplicate IDs, stale targets or nonadvancing time with ValueError and no added line. Concurrent writers revising one head cannot both succeed. Preserve all earlier record/source/clock bytes. Empty ledgers are valid. Failed operations leave their existing content unchanged. Reuse the repository's paper-chain format rather than introducing another ledger/account engine.

The returned record and serialized JSON line keep caller `id`, `event_id`, `revision_of`, `recorded_at`, `fact_pair` and computed `qualification` at top level, with the existing chain's top-level `prev_hash` and `record_hash`. Callers cannot choose chain hashes. This offline API makes no network timestamp/provider calls. An internally reversed fiscal period (start >= end) is an integrity contradiction and raises ValueError; two individually valid but different periods are INCOMPARABLE.
