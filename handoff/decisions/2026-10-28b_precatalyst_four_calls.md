# Decision 2026-10-28b (owner): the four calls of the pre-catalyst program

Asked the four calls of `handoff/precatalyst-program/PROGRAM_v1.md` section 7 ("in short, tell me what the four calls i
need to make"), the owner answered: "okay yeah just do all four i guess".

1. **Start the 13D test: yes.** `KOD-CATALYST-REGISTER-v1`, family SEC13D, frozen before the first set
   (`idx-signals/research/CATALYST_REGISTER_v1/`), registered in the trial register as pending; each look at 60, 120 and 240
   FIRE pairs is a counted test, the first being test 31. Code in a draft PR from `claude/catalyst-register-v1-20261028`.
2. **Log the IDX index review before 2 November: yes**, descriptive and not counted (family IDX_INDEX). The list comes
   from news articles, with sources and a confidence per change (`events/IDX_INDEX_2026-11-02.json`), because idx.co.id is
   blocked from the cloud container. If the owner has the IDX announcement itself, a corrected list is a new events file
   for the next review; this review's file is not edited once its sets are sealed.
3. **Tag dilution filings: yes.** `DILUTION_RECENT` tags for new US and IDX Speculation Register sets, sealed before each
   set's cutoff in `paper/catalysts.jsonl`; metadata only. The Speculation Register's frozen protocol and records are not
   touched.
4. **Short side of dilution: left open for a later, separate, pre-registered protocol.** Nothing is built or run now.
   Shorting the movers was outside the 2026-10-17 and 2026-10-22 retirement decisions; this keeps it a future option only.

Not changed: PAPER-POLICY-v4, the paper routines and their scheduled tasks, every earlier record. The new steps run when
the routines fire, from the feature branch's worktree, until the owner adds them to the routine prompts or merges the PR.
