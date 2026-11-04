# Expert-gap fixes: what changed and how it was verified

Branch `claude/hopeful-hypatia-ktzpog`, 2026-11-04. Plan: `handoff/KOD_FIX_PLAN.md`. Owner instruction: "Do everything
and i want you to follow the neatness of Ace, or even neater." Base: `d607c3250` (default branch `dbb27ea5c` merged in).

Method. Five builders worked in isolated git worktrees, one fix each. Two adversarial reviewers per fix tried to break
it (one for correctness, one for history safety and neatness). A repair agent fixed every blocking finding, and a
recheck agent confirmed each repair. 25 agents in total, none failed. The integrator (Claude) merged the five fix
branches, resolved two conflicts in `tools/live_code_style.json` (kept every new entry, sorted) and wrote the one
deliverable a subagent could not write (the corrected-runs report).

## Results

| Fix | Branch | Review outcome | What it delivers |
|---|---|---|---|
| 1 Clock parser | `fix/1-clock-parser-v2` | Accepted; 10 nits, all repaired | `idxsig/runtime/chrony.py` parser `CHRONY_TRACKING_CSV_V2` reads field 4 (real offset 0.002434953 s, not the reference time 1793795343.59). Old records still verify byte for byte and now report `OFFSET_FIELD_DEFECT_V1` with the corrected value. Real server sample fixture in `idx-signals/tests/fixtures/real/`. Inventory: `handoff/claude/REAL_SAMPLE_INVENTORY.md` |
| 2 Look-ahead check | `fix/2-lookahead-check` | Blocked twice, repaired, rechecked: accepted | `idxsig/lookahead.py` (truncation and scramble checks), `tools/check_no_lookahead.py`, `docs/LOOKAHEAD_CHECK.md`. Leaky toy studies fail, clean twins pass |
| 2b Corrected studies | `fix/2b-corrected-runs` | Blocked (report missing); report written by the integrator | NEIGHBOURS_v1 and PRESSURE_v1 corrected runs, one each: all three verdicts **CONFIRMED** (`idx-signals/research/RESEARCH_CORRECTIONS_20261104/REPORT.md`) |
| 3 and 4 CI rules | `fix/34-ci-rules` | Blocked twice, repaired, rechecked: accepted | `tools/check_shared_data.py` (warning only, on new study files), `tools/check_merge_notes.py` (blocks a code merge into the default branch without a six-question note; bots exempt), `handoff/merges/` |
| 4 and 5 Rules | (direct commits) | — | `handoff/KOD_RULES.md`, architect section in `handoff/AGENTS.md`, `handoff/decisions/2026-11-04_rules_and_architect.md`, `docs/PROTOCOL_TEMPLATE.md` (feasibility gate), `handoff/HUMAN_REVIEW_BRIEF.md` |
| 6 Alerts | `fix/6-watch-kit` | Accepted; 12 nits, all repaired | `ops/kod-watch/`: read-only dead-man's switch and daily line, systemd units, 41 stdlib tests, `INSTALL.md` for Ace (step 0 checks the existing `kod-guard` timer first) |
| Close | (direct commits) | Two independent checks | INFO_MAGNET verified (`handoff/claude/INFO_MAGNET_VERIFICATION.md`); early-entry research **CLOSED** (`handoff/decisions/2026-11-04_early_entry_closed.md`); parking lot `handoff/timing/IDEA_PARKING_LOT.md` |


**Update after PR #24 (merged into the default branch the same day):** the default branch fixed the same chrony defect
independently in `idxsig/runtime/clock.py` (parser `CHRONY_TRACKING_CSV_14_V1`, which also reports an error bound).
When merging the default branch back, Claude kept that parser and removed its own `runtime/chrony.py` so KOD has one
chrony reader. The real server sample and its test (`tests/test_clock_real_sample.py`) now check `clock.py`.

Final verification of the integrated branch: `handoff/claude/FINAL_CHECKS_20261104.txt`.

## Decisions left for the owner or the operator

1. **Architect: Ace or Astra.** Recorded as Astra for now; earlier conversations called Ace the architect.
2. **Protect `idx-signals/tests/fixtures/real/`** by adding it to the frozen paths in `tools/check_append_only.py`
   (real samples should never change). Not done without approval.
3. **Alert kit choices** for Ace to confirm at install: 60-second grace with the :12 slot timer (or 300 s with :16);
   the slot check judges the latest slot; the daily line is read in the monitoring service's event log.

## Known limits, stated plainly
- The production cohort keeps running `dbb27ea5c`, whose verifier reads field 3. Do not point the new timing writers at
  the production cohort's directory while it runs; verify mixed journals with the new code.
- The timing board still shows the stored (wrong) clock value for old records; the corrected value is in the
  integrity diagnostics only. A display fix is a follow-up.
- Only 3 of 37 outside-data parsers have a real-sample test (the inventory lists them). Rule 6 now requires one for new
  parsers; the backlog is listed, not fixed.
- The look-ahead check proves a study's past decisions do not depend on later rows. It cannot prove a data source was
  really available at the time.
- The first default-branch push of the shared-data check will print about 239 warnings over existing study scripts.
  They are warnings only.
- The CI step conditions were checked by tests and YAML parsing, not yet in a real GitHub Actions run.
- Every fix's code and tests were written by the same builder agent, then attacked by different agents. Rule 5
  (different authors) starts with the next change.
