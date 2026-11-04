# Merge request for the architect

From Claude, 2026-11-04. Under `handoff/KOD_RULES.md` rule 10, only the architect merges code into the default branch
`claude/idx-signals-test-repo-ds0jw7`, and `tools/check_merge_notes.py` blocks a code merge whose note does not answer
Q4 "yes" with the architect's name. Claude therefore has **not** merged into the default branch. Everything below is
ready and verified; the architect decides.

## What to merge, in this order

| # | Branch | Content | Trial merge onto the default branch |
|---|---|---|---|
| 1 | `hermes/ignition-combo-holdout-v1` | Hermes 2 Nov research (append-only, `hermes/`) | clean |
| 2 | `hermes/nov3-studies-v1` | Hermes 3-4 Nov studies, clue ledger, judgment policy C1 | clean |
| 3 | `hermes/info-magnet-v0` | INFO_MAGNET locked plan and Upbit notices | clean |
| 4 | `codex/info-magnet-check-20261104` | INFO_MAGNET primary gate run (FAIL) | clean |
| 5 | `claude/hopeful-hypatia-ktzpog` | Claude's studies, Fixes 1-6, rules, close decision (`handoff/claude/FIXES_REPORT_20261104.md`) | to be run by the architect after 1-4 |

Branches 1 to 4 add research files only (160 files, all new). Branch 5 changes live code. One merge note can cover
the push if the architect merges all five in one push; otherwise one note per code merge.

## Checks already run on branch 5
See `handoff/claude/FINAL_CHECKS_20261104.txt` (full idx-signals, kod-machine, tools and ops suites, release gate,
style check, append-only range check). Review evidence per fix is in `handoff/claude/FIXES_REPORT_20261104.md`.

## Draft merge note (the architect copies it to `handoff/merges/<UTC date>-claude-hopeful-hypatia-ktzpog.md`,
reviews each answer, and fills Q4)

```
# Merge note: claude/hopeful-hypatia-ktzpog into claude/idx-signals-test-repo-ds0jw7

## Q1. Were the tests written by a different agent than the code?
Answer: no
Evidence: each fix's builder agent wrote its code and tests; separate reviewer agents attacked them and repair agents added tests (handoff/claude/FIXES_REPORT_20261104.md); rule 5 starts with the next change

## Q2. Does every parser of outside data have a real-sample test?
Answer: no
Evidence: the changed chrony parser has a real server sample (idx-signals/tests/fixtures/real/); ops/kod-watch reads server receipts and is tested on synthetic receipts only; backlog in handoff/claude/REAL_SAMPLE_INVENTORY.md

## Q3. Does every study pass the look-ahead check?
Answer: no
Evidence: the check (tools/check_no_lookahead.py) arrives in this merge; studies merged here were run before it existed; RESEARCH_CORRECTIONS_20261104 uses the causal evaluator

## Q4. Did the architect approve it?
Answer: yes
Architect: <architect's name>
Evidence: <where the approval is recorded>

## Q5. Could the owner actually trade this, and could the result change what the owner does?
Answer: n.a.
Evidence: infrastructure, rules and research records; the early-entry closure changes what the owner pursues, not a trade

## Q6. Does it alert the owner when it breaks?
Answer: no
Evidence: ops/kod-watch provides alerts once the operator installs it (ops/kod-watch/INSTALL.md); CI failures show on GitHub
```

## Prompt for the architect (owner pastes this)

> You are KOD's architect (handoff/AGENTS.md). Review handoff/claude/ARCHITECT_MERGE_REQUEST_20261104.md and
> handoff/claude/FIXES_REPORT_20261104.md on branch claude/hopeful-hypatia-ktzpog. If you approve, merge the five
> branches in the listed order into claude/idx-signals-test-repo-ds0jw7 with merge commits (no rebase, no squash: the
> experiment catalog cites commit hashes on these branches), add the merge note from the draft with your name in Q4,
> run the default branch's CI, and report the merge commit and CI result. If you do not approve, list the blocking
> reasons on branch claude/hopeful-hypatia-ktzpog in handoff/merges/REVIEW_<date>.md.
