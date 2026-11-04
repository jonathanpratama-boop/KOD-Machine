# TIMING_CAPTURE_v1 — prospective operating instrumentation

Frozen engineering specification, 2026-11-04. Paper only. This specification
does not reopen the closed or conditionally closed early-entry research lanes.
No new historical outcome study, model fitting, threshold search, order, alert
subscription, or continuous monitor is authorized by this implementation.

## Scope and ordering

Commit this protocol before collecting a prospective record. Synthetic fixtures
and engineering regressions contain invented, explicitly labelled data. Every
explicit runtime attempt records its actual processing clock; recorded replay
cannot establish historical availability. Original economic cutoffs, IDs,
forecasts, daily strategy and research outcomes remain unchanged.

The operating cohort is the next 30 explicitly scheduled attempts with retained
membership and a declared observation profile. Thirty attempts diagnose process
delay; they are not 30 independent market regimes or a profitability sample.
An invocation with no declared schedule has UNKNOWN schedule latency. A failed,
blocked, partial, no-trigger or interrupted attempt remains in the denominator.
Retries have their own attempt ID and link to the original economic run ID.

## Components and contracts

1. **TIMING_ATTRIBUTION_v1:** actual local start, input receipt/read, feature
   readiness, detection, decision, executable observation and simulated fill.
   Publication, source time, earliest evidenced threshold crossing and logical
   historical references are distinct. Unknown stages remain null. No threshold
   crossing is inferred from a day high, future winner or synthetic replay.
2. **CLOCK_INTEGRITY_v1:** monotonic process durations, observed host clock status
   and offset where available, and source/local skew. No claimed NTP offset when
   the host provides none. Wall-clock reversal is an integrity failure, not
   negative latency or automatic clock correction. Explicit public decision
   batches may request RFC3161 anchors; failures remain visible. Local hashing
   alone is not independent time proof.
3. **INTRADAY_OBSERVATION_v1:** a caller-declared bounded Binance spot universe,
   1m/5m/15m completed bars, separate daily context, fixed public GET endpoints,
   raw response evidence, request/receipt times and per-symbol failures. One
   finite invocation per explicit schedule. No forecasts, signals or entries are
   introduced by these observations. Blocked providers are not circumvented.
4. **CATALYST_PREPARATION_v1:** dated, sourced events and scenario branches sealed
   before the event. Event revisions keep original versions. Unknown event time,
   publication time or economics stays unknown. Preparation latency can be
   measured; no economic success comparison is claimed without a later frozen
   experiment and complete comparison population.
5. **SHADOW_EXECUTABILITY_v1:** attach a post-availability quote to a frozen
   forecast/decision, preserving its earlier label reference. Check quote age,
   identity, venue, spread, size and declared cost profile. A proxy venue cannot
   establish eToro/Stockbit executability. Missing quotes, FX, owner access,
   liquidity or fees remain explicit blockers. No live order is created.
6. **AVOID_OBSERVATIONS_v1:** record source-backed flags and UNKNOWN values.
   Flags are hypotheses, not universal vetoes or a validated trading rule. The
   proposed 60-decision comparison is not launched by this pass. A separate
   frozen sampling/benchmark/horizon/cost protocol is required before launch.

## Analysis

Separate synthetic, replay and prospective records; separate detector versions,
venues, currencies and source clock semantics. Report attempts, failed/partial
coverage, unknown stages, median/p95/worst measured delays, observed source lag,
and paired stage-price drift only when identity/currency match. Report sampling
scope and quotation limitations with every comparison. A source without an
event timestamp has UNKNOWN event-to-receipt latency.

All timing and context records are append-only or immutable. Projection files
are replaceable only because they are regenerated from verified originals.
Interrupted writes must be detected or replayed idempotently. Existing account
snapshots and original outcome labels are not rewritten for timing telemetry.

## Exit and promotion

Completion means engineering tests, full before/after frozen-tree preservation,
an offline synthetic end-to-end example, verified recovery, and a documented
first-capture command. No automatic strategy promotion, continuous schedule or
live deployment follows. Reconsider the next detector only after the diagnostic
identifies the dominant avoidable delay and the owner's research close rule
allows the proposed information family.
