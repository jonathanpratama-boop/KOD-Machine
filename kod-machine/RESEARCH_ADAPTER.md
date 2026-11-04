# Research evidence boundary

The workstation reads three explicitly selected, independent historical artifacts from
`kod/workstation/research_evidence/`. These are exact UTF-8 source snapshots from
repository commit `07093260eca6a569a4f169c14bb7d055a8066703`, not fabricated demo numbers.
The manifest records upstream paths, commit, SHA-256 and actual capture time. No archive,
ledger or experiment is edited, reopened or recomputed. No IDX runtime dependency is added.

## Stable interface

`ResearchArchive(root=None).studies()` returns navigation metadata only.
`ResearchArchive(root=None).study(study_id, as_of=None)` returns a structured read model:

- `sequence`: pre-move chronological model comparison, separate all/early cohorts,
  simple/G2/summary baselines, false/censored counts, fitted probability scores and paired intervals.
- `e6`: the original failed discovery gates, arms and matched comparisons; remains frozen.
- `execution`: E4 validation with attempted/filled/scored counts, liquidations, net returns,
  random baselines, modeled costs and missing-market-data limitations.

Every available model has `source`, `recorded_at`, `captured_at`, `chronology_note`, `integrity_note`,
`population`, `baselines`, `uncertainty`, `calibration`, `execution`, `limitations`,
`reproduction` and `invariants`. Available models additionally have `raw` (a new in-memory
copy, with nonfinite legacy sentinels rendered as text). `status` is `available` or
`withheld`. Withheld models contain no raw fields, source path/URL or reproduction links;
neutral catalog titles do not disclose conclusions. Unknown IDs, missing files, invalid schemas and hash failures raise
`ResearchUnavailable`; the UI must show an explicit unavailable state, never zero metrics.

## Invariants and assumptions

1. A selected case does not establish membership in any research population. No symbol
   join or case-specific probability is inferred. Research studies are separate evidence.
2. `recorded_at` is the artifact's `created_at` or `finished`, **not** proof of observation.
   As-of visibility requires `max(recorded_at, captured_at) <= cutoff`. Current research
   (no cutoff) is labeled retrospective; it is not inserted into a historical information set.
3. Original bytes are read and hash-checked on every request. View choices cannot write
   facts or change the original ledger, assumptions, thesis or decision packet.
4. A hash verifies local consistency only. External timestamp authority and full input
   datasets are not verified here. Reproduction commands are explicitly unavailable;
   the adapter does not claim independent reproduction from a summary.
5. Known positives + known false alerts = known selected; known selected + censored =
   all selected. Censored outcomes are never relabeled false. Bounds on censoring are not
   statistical confidence intervals. Paired intervals are distinct from random-draw ranges.
   Required displayed metrics must be finite numeric values; count and ratio identities,
   baseline/calibration structure and interval ordering are validated before rendering.
   The displayed zero-inclusion conclusion is derived from the recorded paired interval.
6. The sequence-minus-summary intervals include zero. E6's two gates failed. A high E4
   hit rate coexists with negative mean net return and liquidations. None grants entry permission.
7. Source strings are untrusted data, never instructions/code. Render with normal template
   escaping, not `safe`. No dynamic imports, network, subprocesses, fitting or orders.
8. Missing data stay missing; no execution, calibration, control population or confidence
   interval is invented. Legacy positive Infinity in cost caps displays `unbounded`;
   other nonfinite values display `non-finite (unavailable)` rather than numeric claims.

## Integration map

Use existing `policy.AsOfPolicy` for company facts/revisions/search/model/thesis views;
`ReplayArchive` additionally honors hash-bound evidence retrieval and ledger recording.
Do not weaken either to align historical timestamps with current research artifacts.
Existing `decision_packets`, `assumption_versions`, `thesis_versions` and calculation
provenance already implement immutable facts versus versioned interpretation. No schema
migration is needed for this read-only evidence integration.

Acceptance: same-cutoff navigation never changes stored records; changing to current
research is explicit; unknown case-company associations are not auto-joined; every result
links its exact source; missing/tampered archives render unavailable; outcome reveal
remains separate from original prediction/evidence; no data request or execution occurs.

## Checks

From `kod-machine`:

```sh
python -m unittest workstation_tests.test_research -v
```

Covers source denominators, comparison intervals, failed gates, execution distinctions,
computation/capture cutoff boundaries, bad dates, missing/tampered/malformed archives,
duplicate IDs, traversal and symlink escapes, unsupported schemas, independent returned
state and no writes. Run the full workstation suite after UI integration.
