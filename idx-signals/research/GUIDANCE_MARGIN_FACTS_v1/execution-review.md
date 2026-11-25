# Independent execution review — 16 November 2026

**Decision: hold the new trading-study build, but finish one corrected source
sample before closing Phase 1. The cloud transport repair has no blocking defect
identified in this review; fresh end-to-end collection remains its acceptance
test.**

## Research decision

The prior-test map supports a meaningful distinction: comparable operating-margin
guidance is different from E10's revenue-only revision. It does not establish
post-entry mispricing, a representative event rate, or exhaustive novelty while
the exact CONTRACT_MIN record is unavailable.

The first census correctly preserves 17 observed releases, zero strict pairs,
and three incompletely enumerated issuer windows. Its records distinguish EPS,
EBITDA, historical actuals and quarter forecasts from the intended fact. Those
are useful source findings. But selecting the first 20 numeric CIKs imposes an
obvious issuer-age bias and includes several financial companies for which this
operating-margin definition is a poor fit. It is not a sufficient basis to call
the wider fact scarce or to conclude that no viable evidence timetable exists.
Even if the 17 observations were independent random draws—which they are not—
zero successes would leave a one-sided 95% upper prevalence of about 16.2%.
The observed zero therefore does not resolve the practical rate question.

**Required correction within already-authorized tasks 05–06:** one fixed,
source-only sample across the remaining E10 issuer list, with unchanged metric
and calendar window. This is availability sampling, not a price-outcome search.
The rule was written before roster construction in
`source-census-v2-selection.md`; the resulting 40 issuers are saved in
`source-census-v2-roster.json`. SHA-256 ranking with a declared, unchanged salt
removes the explicit low-CIK preference. It does not remove the parent universe's
historical liquidity and survivor limitations. Retain missing, acquired or
inactive issuers without replacement. Report the new 40 separately from the
original 20 and the targeted examples.

Complete this one correction, then make the build/hold decision. No change to
EPS, EBITDA, FCF, the window or the sampling salt is justified by zeros. If the
corrected sample still lacks sufficient usable disclosures or source coverage,
hold the build with that specific limitation. Do not label it a failed trading
strategy. If it contains usable pairs, verify the latest prior and accounting
basis before using them as availability evidence; a positive source example is
not an executable trade or evidence of an edge.

## Runtime repair

Inspected `cloud-repair/provider_recovery.py` against the retained original
transport function and independently reran all nine behavioral test methods.
They pass. The reviewed overlay:

- preserves each failed HTTP response and does not invent successful observations;
- makes ordinary 5xx failures retryable with bounded delay, rather than writing
  a permanent missing-telemetry stop;
- preserves actual access/rate stops, Retry-After handling, existing reported
  weight checks and operator pauses;
- counts waiting against the request deadline and sends no request when the
  wait exhausts that deadline;
- resets delay after successful recovery and propagates network exceptions.

No blocking behavior regression was identified from this bounded review. This
does not independently prove full collector recovery, concurrency behavior under
all loads, or off-host publication. The parent must verify advancing actual
minute records, current engine processing, the absence of a fresh error latch,
and current backup/dashboard data. Starting the service, a passing unit test,
or an old backup timestamp is insufficient. Preserve the original outage and
frozen study clocks; do not backfill or relabel gaps as repaired.

## Acceptance wording

Use “collector recovered” only after the operational observations above. Use
“new study on hold pending completion of the corrected source census” until the
remaining Phase 1 evidence is read. Do not mark all 40 implementation/research
tasks complete or imply future outcomes already exist.

## Decision after the corrected census — 16 November 2026

**GO for a narrow offline source/fact prototype and a draft source-qualification
protocol. HOLD the unattended trading-study launch. Do not close the economic
hypothesis.** This supersedes the provisional “complete the corrected census”
instruction above; that census has now been completed.

I read `feasibility-addendum-v2.md`, `census-v2-first20.json` and
`census-v2-last20.json`. The 40 selected issuers yielded 32 read earnings releases
and eight incomplete/calendar-only windows. Two explicit as-reported forecast
pairs were reconstructed. KTOS has an unresolved consolidation-perimeter change;
RBBN has an unresolved latest-prior completeness check. ADEA's derived
operating-profit identity remains a separate development example, outside the
explicit-pair count. These are not two fully eligible trading signals.

This is enough evidence that a specific economic fact exists and differs from
the revenue-only test. It also provides practical failure cases for development.
The initial no-build inference was too strong. The bounded sample does not
establish profitable capture or a reliable arrival rate, but neither uncertainty
requires abandoning an inexpensive, bounded offline implementation.

### Work justified now

1. Write the source-qualification specification: same issuer, fiscal period,
   currency, units, accounting basis and consolidation perimeter; explicit
   current/prior references; original excerpts; publication, receipt, extraction
   and decision clocks as separate fields. Define missing/incomparable states.
   A definition change must not become economic improvement.
2. Reuse existing source packets and append-only records. Implement a small
   adapter accepting retained raw source documents and typed fact responses;
   calculate revisions and margins deterministically. Preserve failed examples
   and full source identity. A historical document replay is development, not
   a new event or a live signal.
3. Validate and independently test the retained fixtures: useful explicit rows,
   GAAP/non-GAAP mismatch, EPS/EBITDA substitution, period mismatch, acquisition
   perimeter, missing prior, recast, stale/late response and duplicate delivery.
   Source-ID existence alone must not be called factual entailment.
4. Prepare the provider request/response recording interface and configuration,
   with fake responses for offline tests. Invoke a paid provider only after the
   actual authorized provider and usage decision exist. Do not call a hand-entered
   fixture an LLM extraction result.
5. Draft the prospective eligibility and comparison design, identifying what is
   still unresolved. Added economic information versus a revenue-only baseline
   measures the fact's value; it does not separately prove that an LLM extracts
   it better than a mechanical reader with access to the same information.

This does not justify a new portfolio engine, tuning/backtesting on prices,
recurring paid model calls, simulated live trades, or a profitability dashboard
tile. Use the existing account/execution machinery only after the input and
study contracts are settled. Status may honestly say “source prototype under
validation,” with development examples separated from live admissions.

### What actually blocks unattended launch

- A registered primary-source feed and current/prior lookup procedure must work
  from the deployment environment, with declared coverage and saved raw bytes.
  Initialize the latest known guidance state without treating old releases as
  new arrivals; then record newly observed disclosures and subsequent corrections.
  “Latest prior within verified source coverage” must have an explicit procedure,
  rather than an impossible claim to know every public statement everywhere.
- The extracted fields and their source support need accepted validation. KTOS's
  perimeter ambiguity and RBBN's prior uncertainty are test cases, not exceptions
  to silently waive for admission.
- The actual information sets, decision rule, execution/account assumptions and
  review conditions must be frozen and independently checked before any strategy
  outcome is evaluated. Source availability is not authorization to choose the
  trading policy after seeing returns.
- An unattended provider needs a selected model, working credentials, recorded
  usage and an authorized spending arrangement. A model-provider interface with
  no credentials is an offline component, not a running experiment.
- A real capture-to-record-to-status rehearsal must pass. Source/inference errors
  must remain visible and must not stop the existing R2 market collector.

**Historical KOD receipt is not a prerequisite for the prospective design.** We
cannot manufacture it and should not demand it for old development fixtures.
Future decisions must use their actual newly recorded receipt and completion
times. Earliest-public time may remain uncertain if the study claims capture
from KOD receipt rather than a proven news-speed advantage. This scope must be
stated before evaluation; an uncertain earlier release cannot support a claim
that KOD acted immediately after first publication.

The corrected source sample is now closed. Do the bounded offline work above;
do not initiate another issuer search to rescue the rate. Launch depends on the
concrete operational and scientific checks, not on inventing a count from this
six-week earnings-season sample or pretending a historical missing timestamp is
an insurmountable barrier to collecting future ones.
