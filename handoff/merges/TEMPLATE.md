# Merge note: <merged branch> into <default branch>

<!--
Copy to handoff/merges/YYYY-MM-DD-slug.md: the UTC date of the merge, and the merged branch as the
slug with "/" written as "-" (lowercase letters, digits, ".", "_", "-"). Replace every placeholder.
Each question keeps exactly one Answer line (yes, no or n.a.) and one Evidence line; Q4 also keeps
one Architect line and must answer yes. Free text may follow under a later heading such as Notes.
tools/check_merge_notes.py reads this format; handoff/merges/README.md explains who writes it.
-->

## Q1. Were the tests written by a different agent than the code?
Answer: yes | no | n.a.
Evidence: <one line: who wrote the code, who wrote the tests, and in which commits>

## Q2. Does every parser of outside data have a real-sample test?
Answer: yes | no | n.a.
Evidence: <one line: the real-sample fixtures, or n.a. when no parser of outside data changed>

## Q3. Does every study pass the look-ahead check?
Answer: yes | no | n.a.
Evidence: <one line: the look-ahead check result for each study, or n.a. when no study changed>

## Q4. Did the architect approve it?
Answer: yes
Architect: <name of the architect who approved and performed this merge>
Evidence: <one line: where the approval is recorded>

## Q5. Could the owner actually trade this, and could the result change what the owner does?
Answer: yes | no | n.a.
Evidence: <one line: the venue, the round-trip cost and the decision it changes, or why not>

## Q6. Does it alert the owner when it breaks?
Answer: yes | no | n.a.
Evidence: <one line: which alert fires, or why nothing can break unnoticed>
