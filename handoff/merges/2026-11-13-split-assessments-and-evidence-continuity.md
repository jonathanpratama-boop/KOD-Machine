# Split assessments and evidence continuity

Owner-directed repair and integration, 13 November 2026. Base default commit
`b836c8d516275d37b6dee3f6990d206b15868278`.

## Change and evidence

Import the final content of Fable's SPLIT_REVISIONS_v1 revision 3
(`2655eff305f5da2cb90221f4b6249e898484a3ca`, original base `134f58f9a0b335400c5fd24843767d6b862cfdb0`).
This adds dated split assessments and a corrected paper-book view. An additional independently reproduced case
showed that a readable list containing only unrelated splits could restore a confirmed false spike. The added
supporting-event check records that refresh as incomplete. Coherent new price evidence can still reverse a finding.

The integration applies the final patch to the current default tree. Fable's original branch and bundles retain its
intermediate handoff edits. The incoming frozen research files are introduced once, with their original results and
timestamp tokens, avoiding the three intermediate handoff modifications that failed the source branch's history check.

## Owner's six questions

1. **Independent tests.** Fable supplied independently authored split-rule tests. A separate acceptance reviewer
   wrote six further evidence-continuity regressions before this repair. All 215 targeted tests pass against the
   integrated implementation, including the original date-correction cases. The module also passes pinned ruff 0.14.3.
2. **Real input.** The existing fixture covers 178 saved real-case observations. A fresh normal Yahoo chart read on
   13 November independently reproduced SMX as a real post-split move and GOVX/SLXN as artifacts. Current evidence
   and initial assessment publication are recorded in the operational closeout accompanying this merge.
3. **Look-ahead.** This is a descriptive correction to measurement. Assessments retain their actual recording time,
   and the historical-cutoff view uses only assessments available before each entry cutoff. Frozen strategies and
   completed outcomes retain their original clocks and values.
4. **Architect review.** Codex performed the owner-requested integration and obtained independent acceptance of
   the additional repair. Remote required checks must pass on the final merge candidate before merge.
5. **Trading relevance.** Corrected statistics prevent split artifacts from distorting conclusions. In the supplied
   frozen snapshot, the corrected US spike mean remains negative and behind its comparison basket. This repair
   supplies trustworthy measurement for that decision.
6. **Failure reporting.** The normal US sealing hook records missing-data and receipt failures. Existing paper
   verification validates the assessment ledger. The dashboard closeout exposes source freshness and refresh errors.
   External stopped-alert delivery remains a separately identified verification gap until an actual receipt exists.

Follow-through requires the current assessment ledger, the resulting report, and the dashboard's source revision to
be published and checked. Test counts alone do not establish that a scheduled publishing cycle completed.
