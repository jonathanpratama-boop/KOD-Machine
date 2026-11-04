# Timing preparation and price context

`idxsig.timing_context` supplies deterministic, offline adapters to the timing
runtime. Its input schema is `schemas/timing_context_v1.schema.json`.
`build_timing_context(pack, as_of=...)` returns the calendar board, prepared event
branches, shadow quote checks and avoid-side observations as one immutable-ready
payload. It does not fetch sources, poll calendars, change an account or score a
new strategy trial. Raw evidence must be retained by the calling runtime.

## Boundaries and interfaces

| Component | Input | Output and clock | Existing contract preserved |
| --- | --- | --- | --- |
| Calendar | Versioned exact/window/date-only event, source receipt and evidence ID | UTC event projection at explicit cutoff | `catalysts.py` scientific families and original ledger unchanged |
| Prepared branches | Named calendar version, branches, preparation timestamp | Content-addressed preparation before event/window starts | Candidate `DETECTED` and research states are separate from entry permission |
| Cost profile | Versioned named assumptions and source/applicability status | Quote-currency fee model at the assessment cutoff | Existing account profile hash, fees, slippage, rounding and identity unchanged |
| Shadow quote | Decision availability, expiry, retained quote, cost profile | Observed/proxy/rejected/expired/unknown; no fill | Bid/ask spread counted once; old label opens never become fills |
| Avoid observations | Evidence-backed flags, exact availability and optional regime | PRESENT/ABSENT/UNKNOWN; no veto | No claim that all five flags are validated or independent |
| PREMOVE adapter | Original forecast and retained availability receipt | Original record hash/label plus separate execution clock | Original frozen forecast, universe, outcome label and trial untouched |

The code accepts only the current versions of these **new** schemas. It does not
reinterpret old records as the new schema. The legacy account adapter and PREMOVE
adapter consume original records without rewriting their bytes. Any future schema
change must add an explicit reader and migration tests; implicit guessing is not
supported.

## Calendar and preparation

Store the original IANA timezone, such as `America/New_York`, and an aware event
timestamp. Storage normalizes the timestamp to UTC. Date-only/unknown times never
create a fictional midnight event or exact due trigger. A window has explicit
start and end. An exact time cannot simultaneously declare a window.

Publication may be unknown; receipt must be known and at or before the cutoff.
Publication cannot follow receipt. Evidence IDs are declarations unless the
calling collector verifies original bytes. Revision `event:v2` must explicitly
supersede `event:v1`; the old event and preparation retain their own identities.
A changed event time does not rewrite the old prepared branches.

Branches permit `RESEARCH`, `NO_ACTION` or `RECHECK`. Preparation must precede the
event/window start and cannot consume an event receipt first obtained afterward.
Date-only events cannot establish exact pre-event preparation. The feature does
not claim that a scheduled event has occurred or that its result is known.

## Shadow executability

A shadow check uses a quote received after the forecast actually became available.
If request-start time exists, the request must also follow availability. The
source clock is checked separately where available; absence remains unknown.
Reject expired decisions, stale quotes, future receipts, source-clock conflicts,
crossed quotes, mismatched instruments/cost currencies/venues, and insufficient
displayed ask size when a hypothetical quantity is declared.

`OBSERVED` means an indicative quote passed these structural checks. It is not a
guaranteed fill or an eligibility state. `PROXY_ONLY` means the observed venue is
different from the owner's requested venue. `owner_venue_executable` is always
false in this adapter because neither broker access nor a fill has been verified.
`executable_at` is an indicative observation time accompanied by its explicit
`execution_basis`; `fill_at` remains null. An unavailable quote stays unknown.

Depth is explicitly `TOP_OF_BOOK_ONLY`. With no requested size, capacity remains
unknown. The instantaneous round-trip arithmetic illustrates fees and spread at
one observed quote; it does not forecast a future sale price. It is denominated
in the profile's quote currency and excludes account FX. If required cost inputs
are missing, the economic result is unknown. See `costs/README.md`.

The PREMOVE protocol's daily open remains its research label. The adapter uses a
separate caller-retained availability receipt and optional seal time; the receipt
must follow that seal. It checks the individual record hash and frozen membership,
but full chain and RFC 3161 verification remain with their existing verifiers.
It reads no outcome fields and grants no entry permission.

## Demonstration and validation

`context_fixture()` returns fixed synthetic input. It demonstrates pre-event
preparation, a post-availability proxy quote, rejection of a historical label-open
quote, and unknown avoid flags. Repeated evaluation is deterministic.

From `idx-signals`:

```bash
python -m unittest discover -s tests -p test_timing_context.py -v
```

The tests cover causal chronology, offsets, revisions, expiry, missing inputs,
cost double-counting, currency/venue mismatch, displayed-size limits, immutable
PREMOVE references, malformed context and deterministic aggregation. They do not
establish profitability or independent market evidence.
