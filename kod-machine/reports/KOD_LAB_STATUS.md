# KOD lab status

Doctrine SHA-256: `246deb4a63c8168622e86cccecf04101801f2e1bf4d8c765396f3e277c294f0e`
Calibration: **NOT_STARTED**
Entry permission: false

Prospective closed cases are the only rows that can validate a detector.
Promotion floor: 30 closed prospective cases with complete coverage.

## Counts

- Cases: 4
- Prospective open: 1
- Prospective closed (scored): 0
- Retrospective (hypothesis only): 2
- Simulated (excluded): 1

## Detector table (prospective closed only)

| Detector | Evaluated | Signals | Signal then repriced up | Insufficient | Status |
|---|---:|---:|---:|---:|---|
| — | 0 | 0 | 0 | 0 | UNVALIDATED |

## Case cards

### PROSPECTIVE

- `KOD-P-TEMPLATE-001` TEMPLATE WATCH → OPEN [EMPTY]
  - Hypothesis: Replace this card before any real name. A prospective case must be opened before the outcome window, with facts frozen and a critic loss path.
  - Signals: COVERAGE_INCOMPLETE

### RETROSPECTIVE

- `KOD-R-NVDA-20230524` NVDA INVESTIGATE → REPRICED_UP [PARTIAL_PUBLIC]
  - Hypothesis: A dated earnings print was the scheduled information event. The lab question is whether anything in the prior 30 days, other than the known date, was a weak tell. This card does not reconstruct the full information set.
  - Signals: DATED_CATALYST_KNOWN, COVERAGE_INCOMPLETE
- `KOD-R-SMCI-202408` SMCI WATCH → REPRICED_DOWN [PARTIAL_PUBLIC]
  - Hypothesis: Failure case, not a winner study. After a long AI-server repricing, a delayed filing became the information that mattered. The lab question is whether the prior bullish narrative still had a mechanism in primary documents at the cutoff.
  - Signals: DATED_CATALYST_KNOWN, NARRATIVE_WITHOUT_MECHANISM, COVERAGE_INCOMPLETE

### SIMULATED

- `KOD-S-PIPELINE-001` SIM REJECT → REPRICED_UP, window +40.0% [SIMULATED]
  - Hypothesis: Pipeline fixture. Must never enter the prospective or retrospective scientific tally.
  - Signals: DATED_CATALYST_KNOWN, NARRATIVE_WITHOUT_MECHANISM, COVERAGE_INCOMPLETE

## What this report is not

A retrospective winner is not evidence that a detector works. Coverage on the seed
cases is PARTIAL_PUBLIC, not a complete archive. No name here is a recommendation.
