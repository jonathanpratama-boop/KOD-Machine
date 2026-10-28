# Consolidation note (2026-10-28)

When this experiment's branch (`codex/guidance-revision-v1`, PR #9) was merged into the main branch, the main branch
already had a different module at `idx-signals/idxsig/guidance.py`: the E10 guidance extractor, frozen by
`research/E10/protocol.json`. Two frozen records cannot share one path, so on the main branch:

- E10's `idxsig/guidance.py` stays where E10 froze it, unchanged.
- This experiment's module lives at `idx-signals/idxsig/guidance_revision.py`, byte for byte the version frozen in
  `CALENDAR_FINAL_REPAIR.json` (SHA-256 `32816a4a6868bec5921855d3fcfa71aab6764a0b7e469b7ee39dd7dfb9f5f99e`).
  `tests/test_guidance_revision.py` imports it under that name.

Nothing in this directory was edited (it is append-only). The scripts here (`run_first_decision.py`,
`verify_current.py`, `verify_final.py`) import `idxsig.guidance` and check its hash at the old path, so they verify only
on the experiment's own branch, which stays on GitHub unchanged: `git checkout codex/guidance-revision-v1`, then run
them as before. The daily paper routines do not use this module.
