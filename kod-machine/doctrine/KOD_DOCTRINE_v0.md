# KOD Doctrine v0 — frozen 2026-10-08

Status: UNVALIDATED. This file is a research constitution, not a trading system.
Entry permission: false. A KOD disposition never authorizes a trade.

## What KOD is

KOD is a forensic laboratory for market repricing. It studies what information
existed before a large move, records a call before the outcome when the call is
prospective, and scores that call later. It does not predict stocks with a model.

ASTRA (Moonshot-Scanner, branch claude/loving-gauss-1o1ldm) already freezes
tape detectors (COMPRESSION, IGNITION, EQ_GAP) and blocks ENTRY_ELIGIBLE.
KOD does not edit those detectors and does not inherit their cohort. ASTRA runs
remain excluded from the authoritative v1 pilot until engine parity exists.

## Dispositions

Only three research dispositions exist:

- INVESTIGATE — enough public, time-stamped evidence to spend research time.
- WATCH — a mechanism is plausible but a named input is missing or the critic
  has a live kill path that is not yet decisive.
- REJECT — the critic's loss path is the base case, coverage is incomplete, or
  the claim depends on information that was not public at the cutoff.

INVESTIGATE is not entry permission. CONDITIONAL_READY and ENTRY_ELIGIBLE are
reserved words and must not appear as KOD dispositions.

## Time

Every case freezes three information sets against one decision cutoff:

- T-30D — what a diligent reader could have known 30 calendar days prior.
- T-72H — 72 hours prior.
- T-24H — 24 hours prior.

A fact may be stored only if its public-availability time is at or before that
horizon's cutoff. Newly found old information is labeled NEWLY_FOUND_OLD and
cannot support a prospective call. Missing is UNKNOWN, never a negative result
and never zero.

## Two ledgers, never mixed

- RETROSPECTIVE cases reconstruct past moves. They may generate detector
  hypotheses. They never count toward calibration.
- PROSPECTIVE cases are opened before the outcome window closes. The card hash
  is stored before any outcome row exists. Only these count.

SIMULATED rows exist for pipeline tests and are excluded from both scientific
tallies.

## Immutability

Cases, information sets, detector evaluations, critic notes and outcomes are
append-only. A loss cannot edit the call that preceded it. Doctrine changes
require a new version and a new SHA-256. Open cases stay bound to the doctrine
hash they were opened under.

## Detector promotion

A detector starts UNVALIDATED. It cannot be marked VALIDATED, and its
thresholds cannot be edited in place. Promotion requires a new rule version,
a pre-registered horizon, and at least 30 closed prospective cases in which
that detector was evaluated with complete coverage. Until that count exists,
the calibration status is NOT_STARTED.

## Critic gate

An INVESTIGATE card is refused unless a critic note states how the call loses:
the mechanism that fails, the missing evidence, and the pre-committed invalidation.
"Looks strong" is not a critic note.

## What this lab will not claim

- No continuous monitoring.
- No executable price, no fill, no MFE/MAE as profit.
- No reconstruction is complete. Public archives are partial. Each information
  set carries reconstruction_status.
- Corporate actions, survivorship and universe definition dominate small samples.
  A winner list without the non-events is not a detector study.
