"""The merge-note rule blocks unexplained code merges, and never a paper bot's log append."""

from __future__ import annotations

from pathlib import Path
import re
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(TOOLS), str(TOOLS / "ci_tests")]

import check_merge_notes as notes  # noqa: E402
import ci_scope  # noqa: E402
from git_fixture import ZERO_SHA, Repo  # noqa: E402

TEMPLATE = (TOOLS.parent / "handoff/merges/TEMPLATE.md").read_text(encoding="utf-8")
INTRO = "tools/check_merge_notes.py"
LEDGER = "idx-signals/paper/ledger.jsonl"
RULES = "idx-signals/idxsig/rules.py"
NOTE = "handoff/merges/2026-11-04-feature.md"


def filled(answer: str = "n.a.") -> str:
    """TEMPLATE.md with every placeholder answered, as the architect would leave it."""
    text = TEMPLATE.replace("Answer: yes | no | n.a.", f"Answer: {answer}")
    return re.sub(r"(?m)^(Evidence|Architect): <.*>$", r"\1: recorded in the fixture", text)


def without(text: str, start: str, end: str) -> str:
    return text[: text.index(start)] + text[text.index(end) :]


class NoteFormatTests(unittest.TestCase):
    def test_filled_template_is_a_valid_note(self):
        for answer in ("yes", "no", "n.a.", "Yes", "N.A."):
            with self.subTest(answer=answer):
                self.assertEqual(notes.note_problems(filled(answer)), [])

    def test_template_as_committed_is_not_a_note(self):
        problems = notes.note_problems(TEMPLATE)
        self.assertEqual({p.split(":")[0] for p in problems}, {f"Q{n}" for n in range(1, 7)})
        self.assertIn("Q1: Answer: 'yes | no | n.a.' is not one of yes, no, n.a.", problems)
        self.assertIn("Q4: Architect: is not filled in", problems)

    def test_missing_question_is_named(self):
        text = without(filled(), "## Q5.", "## Q6.")
        self.assertEqual(
            notes.note_problems(text),
            [
                "Q5 is missing (Could the owner actually trade this, and could the result change "
                "what the owner does?)"
            ],
        )

    def test_answer_must_be_yes_no_or_na(self):
        text = filled().replace("Answer: n.a.", "Answer: maybe", 1)
        self.assertEqual(
            notes.note_problems(text), ["Q1: Answer: 'maybe' is not one of yes, no, n.a."]
        )

    def test_each_question_has_exactly_one_filled_evidence_line(self):
        evidence = "Evidence: recorded in the fixture"
        q2 = filled().index("## Q2.")
        cases = {
            "": "Q2: needs exactly one Evidence: line, found 0",
            f"{evidence}\n{evidence}": "Q2: needs exactly one Evidence: line, found 2",
            "Evidence:": "Q2: Evidence: is not filled in",
            "Evidence: <one line>": "Q2: Evidence: is not filled in",
        }
        for replacement, problem in cases.items():
            with self.subTest(replacement=replacement):
                text = filled()
                text = text[:q2] + text[q2:].replace(evidence, replacement, 1)
                self.assertEqual(notes.note_problems(text), [problem])

    def test_architect_must_approve_and_be_named(self):
        q4 = filled().index("## Q4.")
        cases = {
            ("Answer: yes", "Answer: no"): (
                "Q4: the architect must approve a merge into the default branch (Answer: yes)"
            ),
            ("Architect: recorded in the fixture\n", ""): (
                "Q4: needs exactly one Architect: line, found 0"
            ),
        }
        for (old, new), problem in cases.items():
            with self.subTest(change=old):
                text = filled()
                text = text[:q4] + text[q4:].replace(old, new, 1)
                self.assertEqual(notes.note_problems(text), [problem])

    def test_unexpected_lines_and_repeated_questions_are_rejected(self):
        text = filled().replace("Answer: n.a.", "**Answer:** n.a.", 1)
        self.assertEqual(
            notes.note_problems(text),
            [
                "Q1: unexpected line '**Answer:** n.a.' (a question has one Answer: line and "
                "one Evidence: line)",
                "Q1: needs exactly one Answer: line, found 0",
            ],
        )
        repeated = filled() + "\n## Q3. Again?\nAnswer: yes\nEvidence: twice\n"
        self.assertEqual(notes.note_problems(repeated), ["Q3 appears more than once"])
        self.assertEqual(
            notes.note_problems(filled() + "\n## Q7. Extra?\n"), ["Q7 is not one of Q1..Q6"]
        )

    def test_free_text_outside_the_questions_and_heading_levels_are_allowed(self):
        text = filled().replace("## Q6.", "### Q6:") + "\n## Notes\nAnything, any length.\n"
        self.assertEqual(notes.note_problems(text), [])

    def test_plain_q_labels_mark_questions_as_headings_do(self):
        plain = re.sub(r"(?m)^## (Q\d)", r"\1", filled())
        self.assertIn("\nQ1. Were the tests written by a different agent", plain)
        self.assertEqual(notes.note_problems(plain), [])
        self.assertEqual(
            notes.note_problems(plain.replace("Answer: n.a.", "Answer: maybe", 1)),
            ["Q1: Answer: 'maybe' is not one of yes, no, n.a."],
        )

    def test_note_names_carry_a_calendar_date_and_a_lowercase_slug(self):
        self.assertIsNone(
            notes.name_problem("handoff/merges/2026-11-04-claude-hopeful-hypatia-ktzpog.md")
        )
        for path, problem in (
            ("handoff/merges/2026-11-31-x.md", "the date 2026-11-31 is not a calendar date"),
            ("handoff/merges/notes.md", "the name is not handoff/merges/<YYYY-MM-DD>-<slug>.md"),
            ("handoff/merges/2026-11-04-Fix_34.md", "the name is not"),
            ("handoff/merges/old/2026-11-04-x.md", "the name is not"),
        ):
            with self.subTest(path=path):
                self.assertIn(problem, notes.name_problem(path))


class PaperLogScopeTests(unittest.TestCase):
    def test_every_forecast_log_is_a_paper_log(self):
        self.assertTrue(ci_scope.FORECAST_LOGS <= notes.PAPER_LOGS)
        self.assertIn("handoff/fresh-eyes-2026-11-01/paper/ledger.jsonl", notes.PAPER_LOGS)

    def test_code_configuration_and_other_records_need_a_note(self):
        paths = [
            LEDGER,
            "kod-machine/registry/opens.jsonl",
            "handoff/merges/README.md",
            RULES,
            ".github/workflows/checks.yml",
            "idx-signals/paper/code.py",
            "idx-signals/data/corporate_actions/manual.csv",
            "idx-signals/results/RUNS.jsonl",
            "handoff/KOD_FIX_PLAN.md",
        ]
        self.assertEqual(notes.code_paths(paths), paths[3:])


class WorkflowTests(unittest.TestCase):
    def test_merge_note_step_runs_last_in_integrity_and_after_a_failed_step(self):
        workflow = (TOOLS.parent / ".github/workflows/checks.yml").read_text(encoding="utf-8")
        integrity = workflow[
            workflow.index("\n  integrity:\n") : workflow.index("\n  code-tests:\n")
        ]
        last_step = integrity.split("\n      - ")[-1]
        self.assertIn(
            'python3 tools/check_merge_notes.py --push "$BEFORE" "$GITHUB_SHA"', last_step
        )
        self.assertIn("if: ${{ !cancelled() && github.event_name == 'push' && ", last_step)


class MergeHistoryTests(unittest.TestCase):
    def setUp(self):
        self.repo = self.new_repo()
        self.repo.commit("code and paper logs", {RULES: "RULE = 1\n", LEDGER: "{}\n"})
        self.intro = self.repo.commit("introduce the check", {INTRO: "# stand-in\n"})

    def new_repo(self) -> Repo:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Repo(Path(temp.name))

    def branch(self, name: str, files: dict[str, str], repo: Repo | None = None) -> None:
        """Commit `files` on a new branch off main, then return to main."""
        repo = repo or self.repo
        repo.git("checkout", "-q", "-b", name, "main")
        repo.commit(f"work on {name}", files)
        repo.git("checkout", "-q", "main")

    def check(self, *args: str, repo: Repo | None = None):
        return (repo or self.repo).run("check_merge_notes.py", *args)

    def errors(self, proc) -> list[str]:
        return [line for line in proc.stdout.splitlines() if line.startswith("::error ")]

    def test_bot_style_forecast_appends_pass(self):
        before = self.repo.head()
        self.repo.append(LEDGER, '{"scan": 1}\n')
        self.repo.commit("paper scan", {"idx-signals/paper/timestamps/a.freetsa.tsr": "token"})
        self.repo.append(LEDGER, '{"score": 1}\n')
        head = self.repo.commit("paper score")
        for args in (("--push", before, head), ("--push", ZERO_SHA, head)):
            with self.subTest(args=args[1]):
                proc = self.check(*args)
                self.assertEqual(proc.returncode, 0, proc.stdout)
                self.assertIn("no merge commits on the first-parent line", proc.stdout)

    def test_non_merge_commits_are_never_checked(self):
        before = self.repo.head()
        head = self.repo.commit("direct code commit", {RULES: "RULE = 2\n"})
        self.assertEqual(self.check("--push", before, head).returncode, 0)

    def test_code_merge_without_a_note_fails_and_names_the_file_to_add(self):
        before = self.repo.head()
        self.branch("feature/rules", {RULES: "RULE = 2\n"})
        merge = self.repo.merge("feature/rules", "Merge feature/rules")
        proc = self.check("--push", before, merge)
        self.assertEqual(proc.returncode, 1)
        [error] = self.errors(proc)
        self.assertIn(f"merge {merge[:12]} 'Merge feature/rules'", error)
        self.assertIn(f"changes code or configuration ({RULES})", error)
        self.assertIn("Add handoff/merges/2026-11-04-<slug>.md", error)
        self.assertIn("copy handoff/merges/TEMPLATE.md", error)

    def test_valid_note_on_the_branch_in_the_merge_or_pushed_with_it_passes(self):
        for where in ("branch", "merge", "follow-up"):
            with self.subTest(where=where):
                before = self.repo.head()
                name = f"feature/{where}"
                note = {f"handoff/merges/2026-11-04-{where}.md": filled()}
                code = {f"idx-signals/idxsig/{where}.py": "X = 1\n"}
                self.branch(name, {**code, **(note if where == "branch" else {})})
                head = self.repo.merge(name, f"Merge {name}", note if where == "merge" else None)
                if where == "follow-up":
                    head = self.repo.commit("merge note", note)
                proc = self.check("--push", before, head)
                self.assertEqual(proc.returncode, 0, proc.stdout)
                self.assertIn(f"note handoff/merges/2026-11-04-{where}.md", proc.stdout)

    def test_note_missing_a_question_fails(self):
        before = self.repo.head()
        self.branch(
            "feature/rules", {RULES: "RULE = 2\n", NOTE: without(filled(), "## Q3.", "## Q4.")}
        )
        merge = self.repo.merge("feature/rules", "Merge feature/rules")
        proc = self.check("--push", before, merge)
        self.assertEqual(proc.returncode, 1)
        [error] = self.errors(proc)
        self.assertTrue(error.startswith(f"::error file={NOTE},title=Merge note invalid::"))
        self.assertIn(f"(added by {merge[:12]}): Q3 is missing", error)

    def test_note_is_read_as_it_stands_at_the_head_of_the_push(self):
        before = self.repo.head()
        wrong = filled().replace("Answer: n.a.", "Answer: maybe", 1)
        self.branch("feature/rules", {RULES: "RULE = 2\n", NOTE: wrong})
        merge = self.repo.merge("feature/rules", "Merge feature/rules")
        self.assertEqual(self.check("--push", before, merge).returncode, 1)
        corrected = self.repo.commit("correct the merge note", {NOTE: filled()})
        proc = self.check("--push", before, corrected)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.repo.git("rm", "-q", NOTE)
        removed = self.repo.commit("remove the merge note")
        proc = self.check("--push", before, removed)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        [error] = self.errors(proc)
        self.assertIn(
            f"{NOTE} (added by {merge[:12]}): the note is missing at the head of the push "
            f"({removed[:12]}), where notes are read",
            error,
        )

    def test_one_note_covers_one_merge(self):
        before = self.repo.head()
        self.branch("feature/a", {"idx-signals/idxsig/a.py": "A = 1\n"})
        self.repo.merge("feature/a", "Merge feature/a")
        self.branch("feature/b", {"idx-signals/idxsig/b.py": "B = 1\n"})
        second = self.repo.merge("feature/b", "Merge feature/b")
        head = self.repo.commit("one note for two merges", {NOTE: filled()})
        proc = self.check("--push", before, head)
        self.assertEqual(proc.returncode, 1)
        [error] = self.errors(proc)
        self.assertIn(f"merge {second[:12]} 'Merge feature/b'", error)

    def test_files_other_than_markdown_beside_a_note_are_not_notes(self):
        before = self.repo.head()
        extras = {"handoff/merges/.gitkeep": "", "handoff/merges/2026-11-04-diagram.png": "PNG"}
        self.branch("feature/rules", {RULES: "RULE = 2\n", NOTE: filled(), **extras})
        merge = self.repo.merge("feature/rules", "Merge feature/rules")
        proc = self.check("--push", before, merge)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(f"OK, note {NOTE}\n", proc.stdout)

    def test_misnamed_note_is_rejected(self):
        before = self.repo.head()
        self.branch("feature/rules", {RULES: "RULE = 2\n", "handoff/merges/rules.md": filled()})
        merge = self.repo.merge("feature/rules", "Merge feature/rules")
        proc = self.check("--push", before, merge)
        self.assertEqual(proc.returncode, 1)
        [error] = self.errors(proc)
        self.assertIn(
            f"handoff/merges/rules.md (added by {merge[:12]}): the name is not "
            "handoff/merges/<YYYY-MM-DD>-<slug>.md",
            error,
        )

    def test_merge_on_a_stale_first_parent_counts_only_what_is_new_to_the_branch(self):
        stale = self.repo.head()
        earlier_note = "handoff/merges/2026-11-03-feature-one.md"
        self.branch(
            "feature/one", {"idx-signals/idxsig/one.py": "ONE = 1\n", earlier_note: filled()}
        )
        published = self.repo.merge("feature/one", "Merge feature/one")
        self.assertEqual(self.check("--push", stale, published).returncode, 0)
        two = "idx-signals/idxsig/two.py"
        cases = {  # what feature/two adds on top of `published`, and the expected result
            "code": ({two: "TWO = 1\n"}, 1, f"changes code or configuration ({two}) but adds no"),
            "noted": ({two: "TWO = 1\n", NOTE: filled()}, 0, f"OK, note {NOTE}\n"),
            "paper": ({}, 0, "no note needed: it changes only paper logs and merge notes"),
        }
        for kind, (files, code, expected) in cases.items():
            with self.subTest(kind=kind):
                self.repo.git("checkout", "-q", "-b", f"feature/two-{kind}", published)
                self.repo.append(LEDGER, f'{{"scan": "{kind}"}}\n')
                self.repo.commit(f"work on feature/two-{kind}", files)
                self.repo.git("checkout", "-q", "-b", f"stale-{kind}", stale)
                merge = self.repo.merge(f"feature/two-{kind}", f"Merge feature/two-{kind}")
                # The merged branch contains `published`, so the push is a fast-forward.
                self.repo.git("merge-base", "--is-ancestor", published, merge)
                proc = self.check("--push", published, merge)
                self.assertEqual(proc.returncode, code, proc.stdout)
                self.assertIn(expected, proc.stdout)
                self.assertNotIn(earlier_note, proc.stdout)
                self.repo.git("checkout", "-q", "main")

    def test_merge_of_paper_logs_and_notes_only_needs_no_note(self):
        before = self.repo.head()
        self.repo.git("checkout", "-q", "-b", "paper", "main")
        self.repo.append(LEDGER, '{"scan": 2}\n')
        self.repo.commit("paper scan on a branch", {"handoff/merges/README.md": "notes\n"})
        self.repo.git("checkout", "-q", "main")
        merge = self.repo.merge("paper", "Merge paper")
        proc = self.check("--push", before, merge)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("no note needed: it changes only paper logs and merge notes", proc.stdout)

    def test_sync_merge_of_commits_already_on_the_branch_needs_no_note(self):
        self.repo.git("checkout", "-q", "-b", "bot", "main")
        self.repo.append(LEDGER, '{"scan": 3}\n')
        bot_commit = self.repo.commit("paper scan whose push was rejected")
        self.repo.git("checkout", "-q", "main")
        self.branch("feature/rules", {RULES: "RULE = 3\n", NOTE: filled()})
        published = self.repo.merge("feature/rules", "Merge feature/rules")
        self.repo.git("checkout", "-q", "bot")
        synced = self.repo.merge("main", "Merge branch 'main' of origin")  # the bot's `git pull`
        self.assertIn(RULES, self.repo.git("diff", "--name-only", bot_commit, synced))
        proc = self.check("--push", published, synced)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("every merged commit was already on the branch", proc.stdout)

    def history_before_the_check(self, note: bool) -> tuple[Repo, dict[str, str]]:
        """A code merge before the check, one beside it, then the merge that brings it in."""
        repo = self.new_repo()
        shas = {"base": repo.commit("code", {RULES: "RULE = 1\n"})}
        self.branch("ancestor", {"idx-signals/idxsig/ancestor.py": "A = 1\n"}, repo)
        shas["ancestor"] = repo.merge("ancestor", "Merge ancestor")  # an ancestor of the check
        repo.git("checkout", "-q", "-b", "check", "main")
        shas["intro"] = repo.commit("introduce the check", {INTRO: "# stand-in\n"})
        repo.git("checkout", "-q", "main")
        self.branch("parallel", {"idx-signals/idxsig/parallel.py": "P = 1\n"}, repo)
        shas["parallel"] = repo.merge("parallel", "Merge parallel")  # not an ancestor of it
        shas["head"] = repo.merge("check", "Merge check", {NOTE: filled()} if note else None)
        return repo, shas

    def test_only_merges_that_are_ancestors_of_the_check_are_exempt(self):
        for note, failing in ((True, ["parallel"]), (False, ["parallel", "check"])):
            with self.subTest(note=note):
                repo, shas = self.history_before_the_check(note)
                proc = self.check("--push", shas["base"], shas["head"], repo=repo)
                self.assertEqual(proc.returncode, 1, proc.stdout)
                self.assertIn(
                    f"{shas['ancestor'][:12]} 'Merge ancestor': exempt: an ancestor of the commit "
                    f"that added {INTRO} ({shas['intro'][:12]})",
                    proc.stdout,
                )
                errors = self.errors(proc)
                self.assertEqual(len(errors), len(failing), proc.stdout)
                for error, merge in zip(errors, failing):
                    self.assertIn(f"'Merge {merge}' changes code or configuration", error)
                # As pushed in practice: 'Merge parallel' reached main before the check did, so
                # the push that brings the check in reads only its own merge.
                proc = self.check("--push", shas["parallel"], shas["head"], repo=repo)
                self.assertEqual(proc.returncode, 0 if note else 1, proc.stdout)

    def test_a_merge_made_on_a_clone_that_predates_the_check_is_checked(self):
        repo, shas = self.history_before_the_check(note=True)
        repo.git("checkout", "-q", "-b", "old", shas["base"])
        repo.commit("work on old, branched before the check", {"idx-signals/idxsig/old.py": "O\n"})
        repo.git("checkout", "-q", "-b", "clone", shas["base"])  # a clone still at base
        late = repo.merge("old", "Merge old after the check is live")
        synced = repo.merge("main", "Merge branch 'main' of origin")  # the pull before the push
        proc = self.check("--push", shas["head"], synced, repo=repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        [error] = self.errors(proc)
        self.assertIn(
            f"merge {late[:12]} 'Merge old after the check is live' changes code or "
            "configuration (idx-signals/idxsig/old.py)",
            error,
        )
        self.assertIn(
            "'Merge branch 'main' of origin': no note needed: every merged commit was already",
            proc.stdout,
        )

    def test_since_commit_sets_the_introduction_explicitly(self):
        repo, shas = self.history_before_the_check(note=True)
        for marker, exempt in ((shas["base"], []), (shas["head"], ["ancestor", "parallel"])):
            with self.subTest(marker=marker):
                proc = self.check(
                    "--push", shas["base"], shas["head"], "--since-commit", marker, repo=repo
                )
                failing = {"ancestor", "parallel"} - set(exempt)
                self.assertEqual(proc.returncode, 1 if failing else 0, proc.stdout)
                self.assertEqual(len(self.errors(proc)), len(failing))
                for merge in exempt:
                    self.assertIn(
                        f"'Merge {merge}': exempt: an ancestor of --since-commit {marker[:12]}",
                        proc.stdout,
                    )
                self.assertIn("'Merge check': OK, note", proc.stdout)  # the marker is checked
        # A marker outside the range head's history is allowed: ancestor is exempt, parallel not.
        before_the_check = f"{shas['base']}..{shas['parallel']}"
        proc = self.check("--range", before_the_check, "--since-commit", shas["intro"], repo=repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("'Merge ancestor': exempt", proc.stdout)
        [error] = self.errors(proc)
        self.assertIn("'Merge parallel' changes code", error)
        proc = self.check("--range", before_the_check, "--since-commit", "no-such", repo=repo)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("'no-such' is not a commit in this repository", proc.stdout)

    def test_missing_introduction_is_an_error_only_when_a_merge_is_found(self):
        repo = self.new_repo()
        before = repo.commit("code", {RULES: "RULE = 1\n"})
        repo.append(RULES, "RULE = 2\n")
        head = repo.commit("direct commit")
        self.assertEqual(self.check("--push", before, head, repo=repo).returncode, 0)
        self.branch("feature/rules", {RULES: "RULE = 3\n"}, repo)
        merge = repo.merge("feature/rules", "Merge feature/rules")
        proc = self.check("--push", before, merge, repo=repo)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(
            f"no commit in the history of {merge[:12]} adds {INTRO}; pass --since-commit",
            proc.stdout,
        )

    def test_introduction_is_found_in_the_range_head_history_not_at_the_checkout(self):
        repo = self.new_repo()
        base = repo.commit("code", {RULES: "RULE = 1\n"})
        self.branch("feature/rules", {RULES: "RULE = 2\n"}, repo)
        merge = repo.merge("feature/rules", "Merge feature/rules")
        repo.git("checkout", "-q", "-b", "later", "main")
        repo.commit("introduce the check on the checked-out branch", {INTRO: "# stand-in\n"})
        proc = self.check("--range", f"{base}..{merge}", repo=repo)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn(f"no commit in the history of {merge[:12]} adds {INTRO}", proc.stdout)

    def test_force_push_or_unknown_before_checks_only_the_head_commit(self):
        self.repo.git("checkout", "-q", "-b", "gone", self.intro)
        dropped = self.repo.commit("dropped by the force-push")
        self.repo.git("checkout", "-q", "main")
        self.branch("feature/rules", {RULES: "RULE = 2\n"})
        merge = self.repo.merge("feature/rules", "Merge feature/rules")
        for before, reason in (
            (dropped, "is not an ancestor of"),
            ("f" * 40, "is not in this clone"),
        ):
            with self.subTest(reason=reason):
                proc = self.check("--push", before, merge)
                self.assertEqual(proc.returncode, 1)
                self.assertIn(reason, proc.stdout)
                self.assertIn("reading only the head commit", proc.stdout)
        self.repo.append(LEDGER, '{"scan": 4}\n')
        head = self.repo.commit("paper scan after the force-push")
        self.assertEqual(self.check("--push", dropped, head).returncode, 0)

    def test_invalid_range_or_push_values_are_errors(self):
        self.branch("feature/rules", {RULES: "RULE = 2\n"})
        merge = self.repo.merge("feature/rules", "Merge feature/rules")
        for args, problem in (
            (("--range", f"{merge}..{self.intro}"), "is not an ancestor of"),
            (("--range", "main"), "--range must be BASE..HEAD"),
            (("--push", "main", merge), "before must be a 40-character commit id"),
        ):
            with self.subTest(args=args):
                proc = self.check(*args)
                self.assertEqual(proc.returncode, 2)
                self.assertIn(problem, proc.stdout)


if __name__ == "__main__":
    unittest.main()
