# Decision 2026-10-28 (owner): consolidate every branch into the main branch; keep PAPER-POLICY-v4 live

Owner's words: "integrate this to just one repository if its doable and better". Asked how, the owner chose: merge all
open work into the main branch (`claude/idx-signals-test-repo-ds0jw7`), finished experiments with negative results
included; and, for PR #3, merge its code but keep PAPER-POLICY-v4 in force.

Merged (history kept, merge commits, no force-push): PR #5 (E3 US retention protocol), PR #3 (US pipeline, EXEC-US,
PAPER-POLICY-v5 defined but not in force), US_BREAKOUT_v1, PR #7 (E4 short side), PR #8 (E5-CEILING), E6, EXIT-ATR-v1,
E7 feasibility, E8, PR #9 (guidance revision), PR #13 (Company Decision Dossier), PR #14 (release reader v4), PR #15
(Speculation Register v1), and the MOVERS_NOW / sensors branch (`claude/hopeful-hypatia-ktzpog`). PR #11 (earnings
note) and the analyst workbench were already in the main branch.

Not merged, on purpose: `moonshot-tools` (the owner's instruction: do not modify it) and `data-archive` (7.7 GB of
archived inputs in Git LFS, kept as a separate backup branch). Every other branch stays on GitHub as it was.

What changed in behaviour: nothing in the daily paper routines. Checked on the real 2026-10-27 IDX, US and crypto
inputs: the merged code makes the same scans and the same decisions as before; the only difference is that the US
decisions' reason now cites PR #3's equivalent rerun of the 2023 US validation (20261008T165454Z: -0.97% vs -0.75%,
p 0.62) as the latest evidence run.

Conflicts resolved: two modules named `idxsig/guidance.py` (E10 keeps the path; PR #9's moves to
`idxsig/guidance_revision.py`, see `idx-signals/research/GUIDANCE_REVISION_v1/CONSOLIDATION_NOTE.md`); requirements
(both sides, with PR #9's `pandas<3`, needed by `exchange_calendars==4.5.6`); `RUNS.jsonl` (both appended lines kept, in
order); the append-only list (both new logs); comments and CLI arguments (both sides).

Switching the live routines to PAPER-POLICY-v5 later is a one-line change (`POLICY_ID` in `idx-signals/idxsig/paper.py`)
and would be a new decision.
