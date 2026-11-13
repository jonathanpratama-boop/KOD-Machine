# SPLIT_REVISIONS_v1: four simulated nights through the nightly hook

The scheduled job cannot run from a working branch. Here the function the job calls is run four times on a temporary ledger, against pulls built from the provider responses recorded on 2026-11-12. Night 1 is a reconstruction, not a recorded pull: for GOVX and SLXN the split event is removed and the earlier closes are divided by 24, which is the state the scan saw on 2026-11-11.

Check of the reconstruction against the sealed records:

| Ticker | Previous close sealed by the scan | Previous close in the reconstructed pull | Equal within 1% |
|---|---:|---:|---|
| GOVX | 0.112 | 0.112 | yes |
| SLXN | 0.109 | 0.109 | yes |

| Night | Pull | Records appended | Reassessments | Same night run twice adds | Validator problems | Left out, corrected | Left out, known at the time | Unresolved |
|---|---|---:|---|---:|---:|---:|---:|---:|
| 2026-11-11 | the scan's own pull: the provider does not list the split of GOVX and SLXN yet | 168 | none | 0 | 0 | 9 | 1 | 10 |
| 2026-11-12 | the provider now lists the split and shows re-based closes | 2 | GOVX 2026-11-11 to ARTIFACT_CONFIRMED; SLXN 2026-11-11 to ARTIFACT_CONFIRMED | 0 | 0 | 11 | 1 | 8 |
| 2026-11-13 | the provider returns no bars for GOVX | 1 | GOVX 2026-11-11 to NOT_ASSESSABLE | 0 | 0 | 11 | 1 | 8 |
| 2026-11-14 | the provider answers for GOVX again | 1 | GOVX 2026-11-11 to ARTIFACT_CONFIRMED | 0 | 0 | 11 | 1 | 8 |

Standing assessment of the named sets after each night:

| Night | Set | Assessment | Previous bar | Units |
|---|---|---|---|---|
| 2026-11-11 | SMX 2026-11-10 | REAL_MOVE_AFTER_SPLIT | 2026-11-09 | UNCHANGED |
| 2026-11-11 | GOVX 2026-11-11 | UNEXPLAINED_EXTREME_MOVE | 2026-11-10 | UNCHANGED |
| 2026-11-11 | SLXN 2026-11-11 | UNEXPLAINED_EXTREME_MOVE | 2026-11-10 | UNCHANGED |
| 2026-11-12 | SMX 2026-11-10 | REAL_MOVE_AFTER_SPLIT | 2026-11-09 | UNCHANGED |
| 2026-11-12 | GOVX 2026-11-11 | ARTIFACT_CONFIRMED | 2026-11-10 | PRE_SPLIT_CONFIRMED |
| 2026-11-12 | SLXN 2026-11-11 | ARTIFACT_CONFIRMED | 2026-11-10 | PRE_SPLIT_CONFIRMED |
| 2026-11-13 | SMX 2026-11-10 | REAL_MOVE_AFTER_SPLIT | 2026-11-09 | UNCHANGED |
| 2026-11-13 | GOVX 2026-11-11 | ARTIFACT_CONFIRMED | 2026-11-10 | PRE_SPLIT_CONFIRMED |
| 2026-11-13 | SLXN 2026-11-11 | ARTIFACT_CONFIRMED | 2026-11-10 | PRE_SPLIT_CONFIRMED |
| 2026-11-14 | SMX 2026-11-10 | REAL_MOVE_AFTER_SPLIT | 2026-11-09 | UNCHANGED |
| 2026-11-14 | GOVX 2026-11-11 | ARTIFACT_CONFIRMED | 2026-11-10 | PRE_SPLIT_CONFIRMED |
| 2026-11-14 | SLXN 2026-11-11 | ARTIFACT_CONFIRMED | 2026-11-10 | PRE_SPLIT_CONFIRMED |

Left out of the corrected view after night 4: ATYR 2026-10-30, ENLV 2026-10-28, GOVX 2026-11-11, MASK 2026-10-30, OMEX 2026-10-30, PARA 2026-10-28, SCAG 2026-10-28, SLXN 2026-11-11, TOPS 2026-11-09, WHLR 2026-10-30, XXII 2026-11-05.

Left out of the view as known at the time after night 4: SMX 2026-11-10.

Unresolved after night 4: ADIL 2026-10-28, GNTA 2026-11-02, HUBC 2026-11-03, NUWE 2026-10-27, OMH 2026-11-04, RCT 2026-11-06, SGRX 2026-10-30, VCIG 2026-11-02.
