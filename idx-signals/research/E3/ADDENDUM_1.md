# E3 addendum 1: detection evidence at validation (before discovery)

Written after the precondition stage (`reproduce/`) and before any discovery statistic; the
protocol file itself is frozen by the commit guard, so this is a separate record.

**Added to the validation stage.** For the selected detector, E1's validation detection
metrics (precision at +30/50/100%, lift vs the base rate and vs matched random controls,
one-sided p, recall and lead time; `e1.Study.evaluate` on 2023 under KOD-IDX-E1-v1) are
computed once and written to `validation/detection.json`. The paper policy's detection gate
reads them for the E3 detector (for F1_ARA they coincide with E1's own `research/E1/validation/result.json`).
They are reported; they are not an E3 pass criterion, and they do not take part in selection.

**Precondition result, for the record.** Both recorded E1 runs reproduce on the rule side
exactly (signals 1,109; scored 407 and 251; identical status counts and average net returns
-4.059% and -3.636%). The matched-random baseline mean differs in the fourth decimal
(-0.5332% recorded vs -0.5342% now; -0.4404% vs -0.4400%). The control buckets are
cross-sectional per session, so the five sessions the panel gained since 2026-10-07 should not
move 2023 draws; the remaining candidates are the library versions (pandas 3.0.6 / numpy 2.5.4
here against pandas 2.2.3 / numpy 2.3.5 recorded) and the rebuilt registry (216 resets against
217). Discovery proceeds with `--accept-deviation`, recorded in `discovery/summary.json`.
Every E3 number is computed on the same panel, registry and library versions, so the
comparison within E3 (plan against plan, rule against its own baseline) is unaffected.
