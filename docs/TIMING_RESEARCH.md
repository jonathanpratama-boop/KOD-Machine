# Timing research: attribution first, one new hypothesis at a time

Status on 4 November 2026: **connected timing instrumentation implemented; no new market-data study run; no entry permission**.
The source reports below were read and their copied bytes verified against Git blob hashes. Their underlying per-event
results have not been independently recomputed in this engineering release. Original detectors, logs, protocols,
results, failures and holdout exposure remain intact.

## What Hermes actually found

Sources are preserved in [research_sources/hermes_20261104](research_sources/hermes_20261104/manifest.json), with full
commit refs, source paths and byte hashes. Hermes branch inspected: `c7c84127e94b6debf691d321fa553377dc4af575`.

| Finding | Reported evidence | Consequence |
| --- | --- | --- |
| Faster detection found more big moves but did not solve entry | IGNITION_SCAN_v0: 5,267 events; median +13.9% already before entry; 72h mean net −4.1%, controls −1.0%; +30% touch 17.5% vs 3.9% | A higher touch rate is not an executable edge. Measure what is lost before detection and after decision separately. |
| Combining trend clues did not validate | COMBO holdout A: n=968, mean +1.10%, reported 95% interval [−1.30%, +3.52%], median −7.98%. B: n=830, +1.21%, interval [−1.39%, +3.91%], median −7.33%. Both FAIL | Do not tune SMA/Fibonacci/sentiment combinations again on 2023–26 and call them new confirmation. |
| Avoid-side context may help | All holdout ignitions −2.95%, same-period all random controls −0.47%; combo improves over buy-all but typical trade still loses | A context warning can be useful without becoming a buy signal. It needs a prospective incremental test. |
| Catalyst attribution was weak | Only 7/40 sampled ignitions had a candidate pre-move catalyst; no confirmed hour-level timestamps in the sample, shallow searches | Missing explanation is UNKNOWN, not evidence of manipulation or informed accumulation. |

The COMBO protocol used TP50/14d with no stop and 0.3% costs per side. It is **not** an implementation of the owner's
1–5-session selective-repricing mandate or its planned maximum 5% structural stop. Its historical next-hour open and
hour-high TP assumptions also do not prove achievable prospective fills. The reported `beats_random` criterion allowed
a difference lower bound above −2 percentage points; it is not proof of superiority above zero. The source log's
"CONFIRMED" label would not by itself grant live eligibility in KOD.

Two related sources at `f26fcce828714bebaa4afd3b8563b1ba7312f501` narrow the options:

- ATTENTION_LEAD_v1 full-universe report: 1,473 attention events, excess 20-session return +0.10%, t=0.24,
  reported 95% interval [−0.65%, +0.92%]; locked verdict **NO USABLE LEAD**. The smaller subset is secondary.
- TIMING_NARROWING note: approximately 80% of the excess move in the tested Binance futures-launch announcement
  sample arrived inside the announcement minute. This is one event family, not a theorem that all news or every
  pre-event signal is untradeable. Its eToro cost example is a historical assumption, not a verified current fee quote.

## Primary next experiment: attribute the delay before choosing a new detector

Update: normal runtime processing and paper intents now emit linked timing
records automatically. Bounded intraday observation, context preparation and
post-availability quote assessments are implemented beside the original daily
logic. See `handoff/astra/TIMING_BUILD.md`. The standalone command below remains
available for compatible historical diagnostic input. The proposals later in
this document remain hypotheses, subject to the existing early-entry close rule;
this engineering pass does not authorize a new historical or prospective
strategy comparison.

Use `python -m idxsig.timing_research attempts.json` from `idx-signals`. This deterministic offline command emits
stage delays, known/unknown denominators, and separate detector/evidence cohorts. Input is `{as_of, records}`;
each record requires a generated `id`, `detector_version`, `evidence_kind` (`synthetic`, `recorded`, `prospective`),
`universe_snapshot_id`, and `evidence_id`. Timestamp fields are ISO 8601 with timezone:
`published_at`, `received_at`, `detected_at`, `decision_at`, `executable_at`, `fill_at`.
They may be null. Publication is optional for independent tape discovery. Local elapsed time is not independent
proof that an observation was available prospectively. The command never imputes missing delays and never uses outcome
fields to select the queue. It rejects future timestamps, reversed chronology and duplicate attempt identities.

Retain every scheduled attempt, detections beyond the display limit, no-triggers, rejected candidates, partial coverage,
failed requests and missing quotes. Store provider membership and the scheduled scan opportunity before outcomes.
For tape events, separately record the earliest **observable** threshold crossing, whether a completed bar or quote
established it, and the receipt time. A day-high/time-of-peak cannot stand in for an executable price or chronology.

The first question is whether late entry is caused by (a) an inherently late threshold, (b) collection schedule,
(c) analyst delay, or (d) unavailable execution/liquidity. Each requires a different change. If the threshold consumes
most of the move, shaving software milliseconds does not address the result. If the actionable quote is gone before a
scheduled decision, reject the trade rather than reconstruct a historical fill. Begin with the next 30 scheduled runs;
this is a bounded operational diagnostic, not 30 independent market regimes or a profitability sample.

## Speculations worth testing, in order

These are **proposed hypotheses, not frozen strategies**. Register the exact universe, cutoff, schedule, feature definition,
thresholds, horizon, costs, controls and analysis before collecting outcomes. The harness above is implemented;
these detectors are not implemented or validated by that fact.

1. **Earlier ignition with the original detector as a fixed comparator.** Observe smaller moves on completed intraday
   bars and measure whether additional lead time survives realistic decision delay and fees. Preregister one early
   threshold and one horizon, not a grid. Compare both detectors over the same retained opportunity universe, including
   early false alarms that never become the old +10%/3h ignition. Also compare same-time random liquid coins matched
   using pre-decision trend/liquidity/volatility. An early detector cannot be evaluated only on eventual winners or on
   eventual original-detector events. Keep a schedule compatible with actual operation; no continuous monitoring is
   introduced by this protocol. If available data or the approved schedule cannot observe the proposed interval,
   status is DATA_REQUIRED, not an executable lead.
2. **Participation as an avoid-side signal.** Freeze a self-excluded peer definition from pre-decision data and compare
   isolated versus group-supported early moves. Adjust for the asset's own prior trend and common market return;
   group strength must add something beyond those controls. Test retention after the executable quote over the same
   exact horizon. No implied cash transfer, coordinated intent or manipulation label. This specifically addresses
   runner-versus-fader separation; existing US 20-day evidence cannot validate crypto 1–5-day execution.
3. **Scheduled catalysts with prewritten branches.** For a narrow event family with a known calendar and measurable
   economics, prepare the mechanism, scenarios and invalidation before publication, then require the actual result
   and a feasible current quote. Compare observed decision latency against unprepared analysis. The first endpoint
   is decision quality and feasibility, not headline reaction speed. This cannot rescue the already-failed Binance
   launch sample simply by calling it a new strategy.

## Stop rules and valid inference

Use one primary net endpoint at one exact common deadline, with matched control and cash alternatives, costs once,
quote-age/spread/liquidity assumptions and the owner's structural protection constraints. Keep UNKNOWN and CENSORED
outcomes in denominators; report failed fills, partial coverage and excluded opportunities separately. Unknown stop/target
ordering from an OHLC bar is CENSORED. Peak gain is not profit. Independent daily blocks and market episodes matter;
thousands of correlated coin observations do not create thousands of independent regime changes.

Earlier data and 2023–26 trend/momentum outcomes are already exposed. They may be used for declared exploratory
engineering; they are not a fresh holdout. After one preregistered specification, use a genuinely later prospective
cohort, report all attempts and intervals, and stop if feasible net improvement over the frozen comparator is absent.
Changing a threshold after outcomes creates a new detector version and future cohort. Do not run all three ideas as a
search for the best historical winner. None of these diagnostics or proposals authorizes orders or starts a trial silently.
