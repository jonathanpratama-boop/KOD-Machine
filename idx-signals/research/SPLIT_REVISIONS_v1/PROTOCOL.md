# SPLIT_REVISIONS_v1: repair of split-unit tagging, and its effect on published results

Frozen 2026-11-12, before the implementation was written and before any outcome was read for the effect table.
Owner's instruction: "execute" (2026-11-12, session chat), on the repair with four outcomes set out by the independent
review of the same day. This is an engineering repair and a descriptive disclosure. It is not a strategy test.

## Why

`research/US_SPLIT_ARTIFACTS_v1` tags a sealed US set when a provider split event within ten days before the signal
would explain the recorded move. An audit of 2026-11-12 on repository commit `b0f65e8` (168 sealed US sets) found two
defects in that rule as it runs:

1. It does not know which session supplied the previous close. SMX (signal 2026-11-10, recorded +106%) is tagged
   `ARTIFACT_V11`, yet its previous bar, 2026-11-09, is the first session after the 1-for-2.8 split; both closes are in
   the same units. The issuer's Form 6-K states that adjusted trading began on 2026-11-09
   (https://www.sec.gov/Archives/edgar/data/0001940674/000149315226049929/ex99-1.htm).
2. Each set is tagged once, from the pull of the night. GOVX and SLXN (signal 2026-11-11) were tagged `INDETERMINATE`;
   the provider listed their 1-for-24 splits afterwards and re-based its history. Both are artifacts.

The ledger cannot take a correction as it stands: its validator reports a set that is flagged twice, its reader takes
every record that ever carried an artifact tag, and its hook skips any set already flagged.

## What changes, and what does not

Nothing frozen is edited. No detector, cone, plan, decision, cutoff, sealed set, protocol, or existing ledger line
changes. `paper/split_flags.jsonl`, the rule `SPLIT_ARTIFACT_V11`, its code and its tests stay as they are: they are
the record of what was tagged at the time.

Added:

1. A classifier, rule `SPLIT_UNITS_V1`, that uses the session of the previous bar and a later pull of the closes
   (`CONTRACT.md`, part A).
2. A second append-only ledger, `paper/split_assessments.jsonl`. Its first record for a set is the assessment made from
   the scan's own pull at sealing. Later records are reassessments; each names the record it supersedes.
3. A validator and readers that understand revisions, and that keep two histories apart: what was tagged before a set's
   entry cutoff, and what current evidence establishes.
4. The paper book's secondary section shows the books as frozen, as known at the time, and as corrected, side by side.
5. The nightly hook assesses newly sealed sets and reassesses recent ones from the pull of that night.

## Ledger writes

None on this branch. The live ledgers are written by the scheduled job on the default branch; a second writer would
fork their hash chains. The branch delivers a command that the architect runs once after merging, and a dry run that
prints what that command would append.

## Outcomes required

1. SMX (2026-11-10) is restored to the corrected view, and GOVX and SLXN (2026-11-11) are removed from it, each with
   the evidence used.
2. A legitimate reassessment passes validation, and every reader uses the assessment that applies to the view it
   shows.
3. A correction found later is never shown as a filter that was available before the trade.
4. Tests written by a different agent cover a genuine move after a split, a split reported late, and unresolved
   evidence. The next scheduled run can only be verified after the merge; this branch simulates it on recorded pulls.

## Effect table (descriptive, run once)

Question: by how much do the figures that KOD already publishes change when the sets that current evidence classes as
split artifacts are left out?

- Sets left out: those whose current assessment is `ARTIFACT_CONFIRMED` or `ARTIFACT_PROBABLE`. Unresolved sets stay in
  both columns and are counted.
- Figures: only statistics that a consumer's own report already prints at the commit this branch starts from, recomputed
  with that consumer's own code on the full set of records and on the reduced set. No new statistic, threshold, look or
  verdict.
- A consumer whose first scheduled look has not been taken is reported by count only.
- The table changes no verdict. A frozen verdict stays as frozen; the table sits beside it.
- Evidence for the assessments: the provider pull of 2026-11-12, 10:02 to 10:06 UTC (raw responses kept outside the
  repository; each response's SHA-256 is recorded), with later split events from the same day's per-ticker pull.

## Tests

Written by a different agent from `CONTRACT.md`, before it saw the implementation (house rule 5). The classifier is also
run against the 83 corporate-action challenge cases of the KODCHECK audit, which a different agent wrote from the same
rule text.

## Not done here

The merge. Any write to a live ledger. Verification of the next scheduled run. The two sets that stay unresolved (VCIG
2026-11-02, NUWE 2026-10-27). Any change to a strategy conclusion.
