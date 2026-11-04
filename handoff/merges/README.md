# Merge notes

Every merge into the default branch that changes code or configuration adds one note in this folder,
answering the owner's six questions (`handoff/KOD_FIX_PLAN.md`, Fix 4). `tools/check_merge_notes.py`
runs on every push to the default branch and fails the `checks` run when such a merge has no valid note.

## Who writes the note

The architect: the one agent the owner names to approve and perform merges into the default branch
(`handoff/AGENTS.md`; a change of architect is a dated record in `handoff/decisions/`). The architect
writes the note before pushing the merge, names themself in Q4, and names themself in the merge commit
message. Other agents propose work on their own branches and do not merge into the default branch; the
daily paper bots push their own log appends directly and never merge.

## Naming and format

`handoff/merges/<YYYY-MM-DD>-<slug>.md`: the UTC date of the merge, and the merged branch as the slug with
`/` written as `-` (lowercase letters, digits, `.`, `_`, `-`). Example:
`2026-11-04-claude-hopeful-hypatia-ktzpog.md`. Every Markdown file added here other than `README.md` and
`TEMPLATE.md` is read as a note; other files, such as an image a note links to, are not.

Copy `TEMPLATE.md` and replace every placeholder. Each of Q1 to Q6 keeps exactly one `Answer:` line (`yes`,
`no` or `n.a.`) and one `Evidence:` line of one sentence. Q4 also keeps one `Architect:` line and must
answer `yes`: a merge the architect did not approve does not belong on the default branch. A question
starts at a line that begins with its label, as a heading (`## Q1.`) or plain (`Q1.`). Other lines inside
a question are rejected; free text may follow under a later heading such as `## Notes`, where no line may
begin with a label such as `Q2`.

## Where the note goes

In the merge commit itself, on the branch being merged, or in a non-merge commit pushed together with the
merge. One note satisfies one merge. A note pushed later does not change the failed run of the push that
lacked it: that run stays as the record.

## Exemptions (no note needed)

- **Non-merge commits** are never checked, so the daily paper bots' log appends always pass.
- **Paper logs and notes only:** a merge whose merged-in diff (first parent to merge) touches only the paper
  and forecast logs (`PAPER_LOGS` in the tool) and `handoff/merges/`.
- **Sync merges:** every commit the merge brings in was already on the default branch before the push, for
  example a paper bot's `git pull` after a rejected push.
- **Merges made before the check existed:** a merge that is an ancestor of the commit that added
  `tools/check_merge_notes.py`. Any other merge is checked, also one made after the check went live on a
  clone whose default branch predates it.

## The first merge that brings the check in

That merge is not an ancestor of the check's introduction, so it needs a note. Merge the integration
branch into the default branch with one `--no-ff` merge carrying the note. A fast-forward instead puts the
integration branch's own merges on the default branch's first-parent line, and each one that is not an
ancestor of the introduction then needs a note.

## Not covered

- Squash merges, rebase merges and fast-forwards create no merge commit and are not seen; the architect uses
  merge commits.
- The answers are the architect's statements; the tool checks that they are given, not that they are true.
- That the merge commit message names the architect is a convention, not checked.
- Branch protection on GitHub is outside the repository; a failed run records the problem, it does not
  undo the push.
