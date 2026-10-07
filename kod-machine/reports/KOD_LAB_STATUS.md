# KOD lab status

Doctrine SHA-256: `246deb4a63c8168622e86cccecf04101801f2e1bf4d8c765396f3e277c294f0e`
Calibration: **NOT_STARTED**
Entry permission: false

Prospective closed cases are the only rows that can validate a detector.
Promotion floor: 30 closed prospective cases with complete coverage.

## Counts

- Cases: 3
- Prospective open: 0
- Prospective closed (scored): 0
- Prospective closed but unscored (evaluations not frozen at open): 0
- Retrospective (hypothesis only): 2
- Simulated (excluded): 1
- Scanned names logged: 0 (flagged 0: opened 0, not opened 0)
- Scanned names closed: 0; past window and still unclosed: 0

## Detector table (prospective closed only)

Hit rate when the detector fired, when it was evaluated and did not fire, and the base
rate over both. Lift = signal hit rate / base rate. No no-signal cases means no lift.

| Detector | Hit = | Signal n | Signal hit rate | No-signal n | No-signal hit rate | Base rate | Lift | Insufficient | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| — | — | 0 | — | 0 | — | — | — | 0 | UNVALIDATED |

## Scan log (every scanned name, flagged or not, opened or not)

No scans logged.

## Case cards

### PROSPECTIVE

None.

### RETROSPECTIVE

- `KOD-R-NVDA-20230524` NVDA INVESTIGATE → REPRICED_UP [PARTIAL_PUBLIC]
  - Hypothesis: A dated earnings print was the scheduled information event. The lab question is whether anything in the prior 30 days, other than the known date, was a weak tell. This card does not reconstruct the full information set.
  - Evidence: 0 of 12 known facts cite archived evidence
  - Signals: DATED_CATALYST_KNOWN, COVERAGE_INCOMPLETE
- `KOD-R-SMCI-202408` SMCI WATCH → REPRICED_DOWN [PARTIAL_PUBLIC]
  - Hypothesis: Failure case, not a winner study. After a long AI-server repricing, a delayed filing became the information that mattered. The lab question is whether the prior bullish narrative still had a mechanism in primary documents at the cutoff.
  - Evidence: 0 of 17 known facts cite archived evidence
  - Signals: DATED_CATALYST_KNOWN, NARRATIVE_WITHOUT_MECHANISM, COVERAGE_INCOMPLETE

### SIMULATED

- `KOD-S-PIPELINE-001` SIM REJECT → REPRICED_UP, window +40.0% [SIMULATED]
  - Hypothesis: Pipeline fixture. Must never enter the prospective or retrospective scientific tally.
  - Evidence: 0 of 21 known facts cite archived evidence
  - Signals: DATED_CATALYST_KNOWN, NARRATIVE_WITHOUT_MECHANISM, COVERAGE_INCOMPLETE

## What this report is not

A retrospective winner is not evidence that a detector works. Coverage on the seed
cases is PARTIAL_PUBLIC, not a complete archive. No name here is a recommendation.
