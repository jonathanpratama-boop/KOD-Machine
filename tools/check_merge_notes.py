#!/usr/bin/env python3
"""Fail a push whose merges into the default branch change code without a merge note.

Rule (handoff/KOD_FIX_PLAN.md, Fix 4; handoff/merges/README.md): every merge into the default
branch that changes code or configuration adds handoff/merges/<YYYY-MM-DD>-<slug>.md answering the
owner's six questions (handoff/merges/TEMPLATE.md). CI runs this on pushes to the default branch.

What is checked, on the first-parent line of the range (the commits that landed on the branch):
  * Only merge commits (more than one parent). Non-merge commits are never checked, so the daily
    paper bots' log appends always pass.
  * Exempt: a merge made before the check existed, that is, a proper ancestor of its
    introduction: the first commit in the range head's history that adds
    tools/check_merge_notes.py (or the commit given as --since-commit). Every other merge is
    checked, also one made after the check went live on a copy of the branch that predates it.
  * Exempt: a sync merge, whose merged-in commits were all on the branch already at BASE, as in
    the merge a `git pull` makes after a rejected push (the paper bots do not merge today).
  * A note is needed when the merged-in diff (first parent to merge) touches any path outside
    PAPER_LOGS and handoff/merges/.
  * The note is added by the merge's own diff (in the merge commit or on the merged branch), or by
    a non-merge commit in the same range; one note satisfies one merge.
  * Both count only what is new to the branch since BASE: a changed path whose content equals
    BASE's, and a note that BASE already has, are left out. So a merge made on a stale copy of the
    branch (first parent older than BASE) neither needs a note for code that reached the branch
    before the push nor reuses a note that an earlier merge added.
  * A note is a Markdown file (*.md) added under handoff/merges/ other than README.md and
    TEMPLATE.md; other files there, such as an image a note links to, are not notes.
  * A note is valid when its name is a calendar date plus a lowercase slug, and each of Q1..Q6 has
    exactly one "Answer:" line (yes, no or n.a.) and one filled "Evidence:" line; Q4 answers yes
    and has one "Architect:" line. A question starts at a line that begins with its label, as a
    Markdown heading ("## Q1.") or plain ("Q1."); any other heading ends it. Every note offered
    for a merge is validated as it stands at the range head, so a commit pushed with the merge
    can still correct it.

Exit status: 0 pass; 1 a merge lacks a valid note (each problem is a GitHub ::error naming the file
to add or fix); 2 the range or the introduction cannot be resolved, or invalid arguments.

Not claimed: squash merges, rebase merges, fast-forwards and direct pushes create no merge commit
and are not seen. A sync merge is taken to bring nothing new, so code written in the merge commit
itself, or a feature branch that merged the default branch in and was pushed as the default
branch, passes without a note, as a direct push would. The answers are the architect's
statements: the check verifies that they are given, not that they are true, and it does not
check that the merge commit message names the architect. A failed run records the problem; it
does not undo the push. Standard library only: CI runs it before installing requirements.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
import sys

from check_append_only import APPEND_ONLY
import ci_push

TOOL = "tools/check_merge_notes.py"
NOTE_DIR = "handoff/merges/"
NOT_NOTES = frozenset({NOTE_DIR + "README.md", NOTE_DIR + "TEMPLATE.md"})
NOTE_NAME = re.compile(r"handoff/merges/(\d{4}-\d{2}-\d{2})-[a-z0-9]+(?:[._-][a-z0-9]+)*\.md")
# The daily paper bots' logs: the append-only logs of the paper and registry trees, plus the
# TREND_CORE ledger that .github/workflows/trend_core_paper.yml appends to.
PAPER_LOGS = frozenset(
    path for path in APPEND_ONLY if path.startswith(("idx-signals/paper/", "kod-machine/registry/"))
) | {"handoff/fresh-eyes-2026-11-01/paper/ledger.jsonl"}
QUESTIONS = (
    "Were the tests written by a different agent than the code?",
    "Does every parser of outside data have a real-sample test?",
    "Does every study pass the look-ahead check?",
    "Did the architect approve it?",
    "Could the owner actually trade this, and could the result change what the owner does?",
    "Does it alert the owner when it breaks?",
)
ANSWERS = ("yes", "no", "n.a.")
QUESTION = re.compile(r"(?:#{1,6}\s+)?Q(\d+)(?!\w)")
FIELD = re.compile(r"(Answer|Architect|Evidence):(.*)")
PLACEHOLDER = re.compile(r"<.*>")


def code_paths(paths: list[str]) -> list[str]:
    """The paths that make a merge need a note: all but paper logs and merge notes."""
    return [path for path in paths if path not in PAPER_LOGS and not path.startswith(NOTE_DIR)]


def name_problem(path: str) -> str | None:
    match = NOTE_NAME.fullmatch(path)
    if match is None:
        return (
            "the name is not handoff/merges/<YYYY-MM-DD>-<slug>.md "
            "(slug: lowercase letters, digits, '.', '_', '-')"
        )
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return f"the date {match.group(1)} is not a calendar date"
    return None


def note_problems(text: str) -> list[str]:
    """Why `text` does not answer the six questions; empty when it is a valid note."""
    sections: dict[int, list[str]] = {}
    problems = []
    current = None
    for line in text.splitlines():
        match = QUESTION.match(line)
        if match is None:
            if line.startswith("#"):
                current = None  # any other heading ends the question
            elif current is not None and line.strip():
                current.append(line.strip())
            continue
        current = None
        number = int(match.group(1))
        if not 1 <= number <= len(QUESTIONS):
            problems.append(f"Q{number} is not one of Q1..Q6")
        elif number in sections:
            problems.append(f"Q{number} appears more than once")
        else:
            current = sections[number] = []
    for number, question in enumerate(QUESTIONS, 1):
        if number not in sections:
            problems.append(f"Q{number} is missing ({question})")
        else:
            problems += [f"Q{number}: {p}" for p in _answer_problems(number, sections[number])]
    return problems


def _answer_problems(number: int, lines: list[str]) -> list[str]:
    fields = ("Answer", "Architect", "Evidence") if number == 4 else ("Answer", "Evidence")
    expected = (
        "Q4 has one Answer: line, one Architect: line and one Evidence: line"
        if number == 4
        else "a question has one Answer: line and one Evidence: line"
    )
    values: dict[str, list[str]] = {field: [] for field in fields}
    problems = []
    for line in lines:
        match = FIELD.fullmatch(line)
        if match is None or match.group(1) not in values:
            problems.append(f"unexpected line {line!r} ({expected})")
        else:
            values[match.group(1)].append(match.group(2).strip())
    for field, found in values.items():
        if len(found) != 1:
            problems.append(f"needs exactly one {field}: line, found {len(found)}")
        elif not found[0] or PLACEHOLDER.fullmatch(found[0]):
            problems.append(f"{field}: is not filled in")
        elif field == "Answer" and found[0].lower() not in ANSWERS:
            problems.append(f"Answer: {found[0]!r} is not one of yes, no, n.a.")
        elif field == "Answer" and number == 4 and found[0].lower() != "yes":
            problems.append(
                "the architect must approve a merge into the default branch (Answer: yes)"
            )
    return problems


@dataclass(frozen=True)
class Note:
    path: str
    commit: str  # the commit whose diff adds the note; the note is read at the range head


class Introduction:
    """The check's introduction; a merge that is a proper ancestor of it is exempt."""

    def __init__(self, since_commit: str | None, head: str):
        self._head = head
        self._commits: list[str] | None = None
        self._explicit = since_commit is not None
        if since_commit is not None:
            sha = ci_push.commit_sha(since_commit)
            if sha is None:
                raise ci_push.RangeError(
                    f"--since-commit {since_commit!r} is not a commit in this repository"
                )
            self._commits = [sha]

    @property
    def label(self) -> str:
        shas = ", ".join(commit[:12] for commit in self.commits())
        if self._explicit:
            return f"--since-commit {shas}"
        noun = "commit" if len(self.commits()) == 1 else "commits"
        return f"the {noun} that added {TOOL} ({shas})"

    def commits(self) -> list[str]:
        if self._commits is None:  # found lazily: a push without merges never needs it
            # -m also reports a merge that adds the file itself; a merge that only carries an
            # earlier addition descends from it and is dropped, leaving the earliest additions.
            log = ci_push.git("log", "-m", "--diff-filter=A", "--format=%H", self._head, "--", TOOL)
            found = list(dict.fromkeys(log.split()))
            if not found:
                raise ci_push.RangeError(
                    f"no commit in the history of {self._head[:12]} adds {TOOL}; "
                    "pass --since-commit"
                )
            self._commits = [
                commit
                for commit in found
                if not any(
                    other != commit and ci_push.is_ancestor(other, commit) for other in found
                )
            ]
        return self._commits

    def exempts(self, merge: str) -> bool:
        """True for a merge made before the check: a proper ancestor of an introduction commit."""
        return any(
            merge != commit and ci_push.is_ancestor(merge, commit) for commit in self.commits()
        )


def check(commits: ci_push.CommitRange, introduction: Introduction) -> int:
    line = ci_push.first_parent_line(commits)
    merges = [(sha, parents) for sha, parents in line if len(parents) > 1]
    if not merges:
        print(f"merge notes: OK, no merge commits on the first-parent line of {commits}")
        return 0
    failures = 0
    waiting = []  # (label, merge, code paths) of merges that need a note pushed with them
    for merge, parents in merges:
        label = f"{merge[:12]} '{ci_push.subject(merge)}'"
        if introduction.exempts(merge):
            print(f"merge notes: {label}: exempt: an ancestor of {introduction.label}")
            continue
        if already_on_branch(parents, commits.base):
            print(
                f"merge notes: {label}: no note needed: every merged commit was already on the "
                f"branch at {commits.base[:12]}"
            )
            continue
        own = added_notes(parents[0], merge, commits.base)
        errors = [error for error in (note_error(note, commits.head) for note in own) if error]
        for error in errors:
            print(error)
        failures += len(errors)
        if own:
            if not errors:
                print(f"merge notes: {label}: OK, note {', '.join(note.path for note in own)}")
            continue
        needed = code_paths(new_to_branch(parents[0], merge, commits.base))
        if needed:
            waiting.append((label, merge, needed))
        else:
            print(
                f"merge notes: {label}: no note needed: it changes only paper logs and merge notes"
            )
    if waiting:
        failures += pair_range_notes(line, waiting, commits)
    if failures:
        print(f"merge notes: FAIL, {failures} problem(s) in {commits}")
        return 1
    print(f"merge notes: OK, {len(merges)} merge(s) on the first-parent line of {commits}")
    return 0


def already_on_branch(parents: list[str], base: str | None) -> bool:
    """True for a sync merge: every commit it brings in was already reachable from BASE."""
    if base is None:
        return False  # a head-only read cannot tell what the branch already had
    merged_in = ci_push.git("rev-list", "-n", "1", *parents[1:], f"^{parents[0]}", f"^{base}")
    return not merged_in.strip()


def pair_range_notes(
    line: list[tuple[str, list[str]]],
    waiting: list[tuple[str, str, list[str]]],
    commits: ci_push.CommitRange,
) -> int:
    """Give each waiting merge a note added by a non-merge commit in the range; count failures."""
    offered = [
        note
        for sha, parents in line
        if len(parents) <= 1
        for note in added_notes(parents[0] if parents else ci_push.EMPTY_TREE, sha, commits.base)
    ]
    failures, valid = 0, []
    for note in offered:
        error = note_error(note, commits.head)
        if error:
            print(error)
            failures += 1
        else:
            valid.append(note)
    for index, (label, merge, needed) in enumerate(waiting):
        if index < len(valid):
            print(
                f"merge notes: {label}: OK, note {valid[index].path} (pushed in "
                f"{valid[index].commit[:12]})"
            )
        else:
            print(missing_note(label, merge, needed))
            failures += 1
    return failures


def new_to_branch(
    old: str, new: str, base: str | None, *, added_only: bool = False, under: str = ""
) -> list[str]:
    """The paths `new` changes against `old` that it also changes against BASE.

    With added_only, the paths it adds against both, so a note BASE already has never counts.
    Against a first parent older than BASE the diff also shows what reached the branch between
    that parent and BASE; those paths match BASE and are dropped. A head-only read (no BASE)
    keeps every path.
    """
    paths = ci_push.changed_paths(old, new, added_only=added_only, under=under)
    if base is None:
        return paths
    new_paths = set(ci_push.changed_paths(base, new, added_only=added_only, under=under))
    return [path for path in paths if path in new_paths]


def added_notes(old: str, new: str, base: str | None) -> list[Note]:
    added = new_to_branch(old, new, base, added_only=True, under=NOTE_DIR)
    return [Note(path, new) for path in added if path.endswith(".md") and path not in NOT_NOTES]


def note_error(note: Note, head: str) -> str | None:
    """A ::error annotation when `note` is misnamed, or missing or incomplete at `head`."""
    problem = name_problem(note.path)
    if problem is not None:
        problems = [problem]
    elif not ci_push.git("ls-tree", "--name-only", head, "--", note.path).strip():
        problems = [
            f"the note is missing at the head of the push ({head[:12]}), where notes are read"
        ]
    else:
        try:
            problems = note_problems(ci_push.blob(head, note.path).decode("utf-8"))
        except UnicodeDecodeError:
            problems = ["the note is not UTF-8 text"]
    if not problems:
        return None
    message = f"{note.path} (added by {note.commit[:12]}): {'; '.join(problems)}"
    return ci_push.workflow_command("error", message, file=note.path, title="Merge note invalid")


def missing_note(label: str, merge: str, needed: list[str]) -> str:
    stamp = int(ci_push.git("log", "-1", "--format=%ct", merge))
    day = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
    shown = needed[0] + (f" and {len(needed) - 1} more" if len(needed) > 1 else "")
    message = (
        f"merge {label} changes code or configuration ({shown}) but adds no merge note. "
        f"Add handoff/merges/{day}-<slug>.md (copy handoff/merges/TEMPLATE.md; slug: the merged "
        "branch with '/' as '-') in the merge commit or on the merged branch, or in a commit "
        "pushed with the merge."
    )
    return ci_push.workflow_command("error", message, title="Merge note missing")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ci_push.add_range_arguments(parser)
    parser.add_argument(
        "--since-commit",
        metavar="SHA",
        help=f"the commit that introduced the check (default: the first to add {TOOL} in the "
        "range head's history)",
    )
    args = parser.parse_args(argv)
    try:
        commits = ci_push.resolve(args)
        introduction = Introduction(args.since_commit, commits.head)
        if commits.fallback:
            print(
                ci_push.workflow_command(
                    "notice",
                    f"merge notes: {commits.fallback}; reading only the head commit "
                    f"{commits.head[:12]}",
                )
            )
        return check(commits, introduction)
    except ci_push.RangeError as exc:
        print(
            ci_push.workflow_command(
                "error", f"merge notes: {exc}", title="Merge-note check could not run"
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
