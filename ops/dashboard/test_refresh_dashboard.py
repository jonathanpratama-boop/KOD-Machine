"""Independent dashboard freshness checks, written from the API contract.

All inputs are synthetic. No network or production files are accessed.
"""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import refresh_dashboard as refresh
from refresh_dashboard import render_dashboard, resolve_source_ref, refresh_snapshot, paper_book_views, source_manifest

SOURCE_TIME = "2026-11-07T03:00:00Z"
CLOUD_TIME = "2026-11-13T07:22:00Z"
CHECK_TIME = "2026-11-13T07:23:00Z"
TEMPLATE = '<script id="kod-data">__KOD_DATA__</script>'


def snapshot(built_at=SOURCE_TIME, commit="source-commit"):
    return {"build": [{"built_at": built_at, "kod_commit": commit}],
            "experiments": [{"id": "OLD_RESULT", "as_of": SOURCE_TIME, "resolved": 28}]}


def embedded(html):
    return json.loads(html.removeprefix('<script id="kod-data">').removesuffix("</script>"))


class RenderDashboard(unittest.TestCase):
    def test_new_cloud_data_does_not_make_old_source_look_rebuilt(self):
        data = snapshot()
        results = {"as_of": CLOUD_TIME, "independent_events": 1}
        status = {"status": "STALE", "checked_at": CHECK_TIME, "error": "source unavailable"}
        before = deepcopy((data, results, status))
        rendered = embedded(render_dashboard(data, TEMPLATE, results, status))
        self.assertEqual(rendered["build"][0]["built_at"], SOURCE_TIME)
        self.assertEqual(rendered["build"][0]["kod_commit"], "source-commit")
        self.assertEqual(rendered["build"][0]["cloud_refreshed_at"], CLOUD_TIME)
        self.assertEqual(rendered["experiments"], data["experiments"])
        self.assertEqual(rendered["source_refresh"], status)
        self.assertEqual((data, results, status), before)

    def test_optional_refresh_status_preserves_source_clock(self):
        rendered = embedded(render_dashboard(snapshot(), TEMPLATE, {"as_of": CLOUD_TIME}))
        self.assertEqual(rendered["build"][0]["built_at"], SOURCE_TIME)
        self.assertEqual(rendered["build"][0]["cloud_refreshed_at"], CLOUD_TIME)

    def test_ambiguous_or_absent_template_marker_is_rejected(self):
        for template in ("<p>No data marker</p>", "__KOD_DATA____KOD_DATA__"):
            with self.subTest(template=template), self.assertRaises(ValueError):
                render_dashboard(snapshot(), template, {"as_of": CLOUD_TIME})


class SourceRef(unittest.TestCase):
    def test_explicit_study_branch_survives_default_branch_refresh(self):
        params = {"ref": "fable/completed-study", "path": "results/result.json"}
        before = deepcopy(params)
        self.assertEqual(resolve_source_ref(params, "new-default-head"), "fable/completed-study")
        self.assertEqual(params, before)

    def test_unspecified_or_empty_ref_uses_authoritative_default(self):
        for params in ({}, {"ref": ""}):
            with self.subTest(params=params):
                self.assertEqual(resolve_source_ref(params, "new-default-head"), "new-default-head")

    def test_invalid_ref_type_is_rejected(self):
        for value in (123, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_source_ref({"ref": value}, "new-default-head")


class RefreshSnapshot(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / "data.json"
        self.status = Path(self.directory.name) / "refresh.json"
        self.old_bytes = (json.dumps(snapshot(), indent=3) + "\n").encode()
        self.target.write_bytes(self.old_bytes)

    def test_success_publishes_source_version_and_clock_from_builder(self):
        new_data = snapshot("2026-11-13T06:00:00Z", "new-source-commit")
        before = deepcopy(new_data)
        result = refresh_snapshot(lambda: new_data, self.target, self.status, CHECK_TIME)
        self.assertEqual(json.loads(self.target.read_text()), new_data)
        self.assertEqual(result["status"], "CURRENT")
        self.assertEqual(result["checked_at"], CHECK_TIME)
        self.assertEqual(result["source_built_at"], "2026-11-13T06:00:00Z")
        self.assertEqual(result["kod_commit"], "new-source-commit")
        self.assertEqual(json.loads(self.status.read_text()), result)
        self.assertEqual(new_data, before)

    def test_failed_build_keeps_exact_old_bytes_and_reports_staleness(self):
        def failed_build():
            raise RuntimeError("GitHub source unavailable")

        result = refresh_snapshot(failed_build, self.target, self.status, CHECK_TIME)
        self.assertEqual(self.target.read_bytes(), self.old_bytes)
        self.assertEqual(result["status"], "STALE")
        self.assertEqual(result["checked_at"], CHECK_TIME)
        self.assertEqual(result["source_built_at"], SOURCE_TIME)
        self.assertIn("GitHub source unavailable", result["error"])
        self.assertEqual(json.loads(self.status.read_text()), result)

    def test_incomplete_build_is_never_published_as_current(self):
        no_experiments = snapshot()
        no_experiments["experiments"] = []
        invalid = [None, [], {}, {"build": []}, {"build": [{}]}, snapshot(commit=""), snapshot(built_at=""),
                   no_experiments]
        for new_data in invalid:
            with self.subTest(new_data=new_data):
                result = refresh_snapshot(lambda: new_data, self.target, self.status, CHECK_TIME)
                self.assertEqual(result["status"], "STALE")
                self.assertEqual(result["source_built_at"], SOURCE_TIME)
                self.assertEqual(self.target.read_bytes(), self.old_bytes)

    def test_failed_first_build_does_not_invent_prior_source_time(self):
        self.target.unlink()
        result = refresh_snapshot(lambda: None, self.target, self.status, CHECK_TIME)
        self.assertEqual(result["status"], "STALE")
        self.assertIsNone(result["source_built_at"])
        self.assertFalse(self.target.exists())

    def test_unreadable_previous_snapshot_does_not_invent_prior_source_time(self):
        invalid_bytes = b"interrupted old json {"
        self.target.write_bytes(invalid_bytes)
        result = refresh_snapshot(lambda: None, self.target, self.status, CHECK_TIME)
        self.assertEqual(result["status"], "STALE")
        self.assertIsNone(result["source_built_at"])
        self.assertEqual(self.target.read_bytes(), invalid_bytes)


class SourceManifest(unittest.TestCase):
    def test_missing_optional_study_preserves_authoritative_and_other_studies(self):
        def source_git(path, *args):
            if args[0] == "rev-parse":
                if args[-1] == "origin/missing-study":
                    raise RuntimeError("unknown study ref")
                return "sha-for-" + args[-1]
            return "origin/main=backup-head"

        registry = {"experiments": [{"params": {}}, {"params": {"ref": "origin/present-study"}},
                                    {"params": {"ref": "origin/missing-study"}}]}
        with mock.patch.object(refresh, "git", side_effect=source_git):
            got = source_manifest("kod", "backups", "origin/default", registry)
        self.assertEqual(got["kod_refs"]["origin/default"], "sha-for-origin/default")
        self.assertEqual(got["kod_refs"]["origin/present-study"], "sha-for-origin/present-study")
        self.assertIsNone(got["kod_refs"]["origin/missing-study"])
        self.assertEqual(got["missing_study_refs"], ["origin/missing-study"])

    def test_missing_authoritative_default_aborts_source_build(self):
        with mock.patch.object(refresh, "git", side_effect=RuntimeError("default unavailable")):
            with self.assertRaisesRegex(RuntimeError, "default unavailable"):
                source_manifest("kod", "backups", "origin/default", {"experiments": []})


class PublishedPaperViews(unittest.TestCase):
    def report(self, unresolved=True):
        lines = ["Generated 2026-11-12T23:57:48Z."]
        if unresolved:
            lines.append("2 are unresolved and stay in every view.")
        for book in ("KOD", "ALL", "AVOIDED", "OWNER"):
            for view in ("As frozen", "Known at the time", "Corrected"):
                lines.append(f"| {book} | {view} | 91 | 2 | 1 | $-80 | -4.02% |")
        return "\n".join(lines)

    def test_complete_published_views_preserve_report_date_and_values(self):
        got = paper_book_views(self.report(), "source-at-fixed-commit")
        self.assertEqual(got["status"], "PUBLISHED")
        self.assertEqual(len(got["rows"]), 12)
        self.assertEqual(got["report_generated_at"], "2026-11-12T23:57:48Z")
        self.assertEqual(got["unresolved_count"], 2)
        self.assertEqual(got["rows"][0], ["KOD", "As frozen", "91", "2", "1", "$-80", "-4.02%"])
        self.assertEqual(got["source"], "source-at-fixed-commit")

    def test_missing_or_duplicate_view_is_never_shown_as_complete(self):
        report = self.report()
        missing = "\n".join(report.splitlines()[:-1])
        extra = report + "\n" + report.splitlines()[-1]
        replacement = "\n".join(report.splitlines()[:-1] + [report.splitlines()[-2]])
        for text in (missing, extra, replacement):
            with self.subTest(text=text):
                got = paper_book_views(text, "source")
                self.assertEqual(got["status"], "NOT_PUBLISHED")
                self.assertEqual(got["rows"], [])

    def test_missing_unresolved_count_remains_unknown(self):
        got = paper_book_views(self.report(unresolved=False), "source")
        self.assertEqual(got["status"], "PUBLISHED")
        self.assertIsNone(got["unresolved_count"])


class PublishedInputHealth(unittest.TestCase):
    message = "The latest US scan has unscanned names; full input coverage cannot be claimed."
    assessed = "2026-11-12T23:01:44.792234Z"

    def banner(self):
        return (
            "## US forecast input health\n\n"
            f"**PARTIAL_INPUT — {self.message}**\n\n"
            f"- Assessed {self.assessed}; latest US scan session: 2026-11-12.\n"
        )

    def test_authoritative_warning_survives_before_corrected_views_exist(self):
        report = "# Paper book\n\n" + self.banner() + "\nGenerated 2026-11-12T23:01:44Z.\n"
        got = paper_book_views(report, "published-report-at-fixed-commit")
        self.assertEqual(got["status"], "NOT_PUBLISHED")
        self.assertEqual(got["rows"], [])
        self.assertEqual(got["input_health"], {
            "status": "PARTIAL_INPUT", "message": self.message, "assessed_at": self.assessed,
        })

    def test_warning_is_independent_of_complete_corrected_table(self):
        report = self.banner() + "\n" + PublishedPaperViews().report()
        got = paper_book_views(report, "source")
        self.assertEqual(got["status"], "PUBLISHED")
        self.assertEqual(got["input_health"]["status"], "PARTIAL_INPUT")
        self.assertEqual(got["input_health"]["message"], self.message)

    def test_missing_health_banner_never_means_healthy(self):
        for report in ("", PublishedPaperViews().report(), "## US forecast input health\nNo assessment yet.\n"):
            with self.subTest(report=report):
                self.assertEqual(paper_book_views(report, "source")["input_health"], {
                    "status": None, "message": None, "assessed_at": None,
                })

    def test_status_and_assessment_outside_health_section_are_ignored(self):
        fake = "**PARTIAL_INPUT — unrelated note**\n- Assessed 2001-01-01T00:00:00Z; irrelevant.\n"
        for report in (
            "# Paper book\n" + fake,
            "## US forecast input health\nNothing published.\n## Results\n" + fake,
            "## US forecast input health\nNothing published.\nGenerated 2026-11-12T23:01:44Z.\n" + fake,
        ):
            with self.subTest(report=report):
                self.assertEqual(paper_book_views(report, "source")["input_health"], {
                    "status": None, "message": None, "assessed_at": None,
                })

    def test_missing_assessment_time_stays_unknown(self):
        got = paper_book_views("## US forecast input health\n**BLOCKED — Forecast data unavailable.**\n", "source")
        self.assertEqual(got["input_health"], {
            "status": "BLOCKED", "message": "Forecast data unavailable.", "assessed_at": None,
        })


if __name__ == "__main__":
    unittest.main()
