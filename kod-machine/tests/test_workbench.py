"""Behavioral checks for the optional read-only analyst workbench.

All documents and numeric values below are synthetic test fixtures.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from kod.workbench import build_report


ROOT = Path(__file__).resolve().parents[1]
CUTOFF = "2026-10-22T12:00:00Z"


def security(identifier="SEC-1", **overrides):
    result = {
        "security_id": identifier,
        "issuer_id": "ISSUER-" + identifier,
        "ticker": "ACME",
        "venue": "XNAS",
        "currency": "USD",
    }
    result.update(overrides)
    return result


def observation(value, role="ACTUAL", **overrides):
    result = {
        "metric": "revenue",
        "role": role,
        "value": value,
        "unit": "million",
        "currency": "USD",
        "period": "FY2026",
        "source_quote": "value " + str(value),
    }
    result.update(overrides)
    return result


def document(identifier="DOC-1", **overrides):
    result = {
        "document_id": identifier,
        "event_id": "EVENT-1",
        "security_ids": ["SEC-1"],
        "source_kind": "PRIMARY",
        "publisher": "Synthetic Issuer",
        "source_url": "https://example.invalid/" + identifier,
        "source_family": "issuer",
        "published_at": "2026-10-22T09:00:00Z",
        "observed_at": "2026-10-22T09:01:00Z",
        "title": "Synthetic financing announcement",
        "text": "Capital raising announcement.",
        "observations": [],
    }
    result.update(overrides)
    if result["observations"] and "text" not in overrides:
        result["text"] = "Capital raising. " + "; ".join(
            entry["source_quote"] for entry in result["observations"]
        )
    return result


def bundle(*documents, securities=None):
    return {
        "schema_version": "KOD-WORKBENCH-v1",
        "synthetic": True,
        "securities": securities if securities is not None else [security()],
        "documents": list(documents),
    }


def consensus_document(value="100", **overrides):
    result = {
        "source_kind": "SECONDARY",
        "publisher": "Synthetic Analyst",
        "source_family": "analyst",
        "published_at": "2026-10-22T08:00:00Z",
        "observed_at": "2026-10-22T08:01:00Z",
        "observations": [observation(value, "CONSENSUS")],
    }
    result.update(overrides)
    return document("CONSENSUS", **result)


def cards(report):
    return report["search_results"]


def compare(report, metric="revenue"):
    return next(entry for entry in cards(report)[0]["comparisons"] if entry["metric"] == metric)


class WorkbenchTests(unittest.TestCase):
    def test_report_stays_a_research_view(self):
        report = build_report(bundle(document()), CUTOFF)
        self.assertEqual(report["schema_version"], "KOD-WORKBENCH-REPORT-v1")
        self.assertTrue(report["research_only"])
        self.assertFalse(report["entry_permission"])
        self.assertTrue(report["synthetic"])
        self.assertEqual(report["coverage"]["scope"], "INPUT_BUNDLE_ONLY")
        self.assertEqual(cards(report)[0]["preview_type"], "EXTRACTIVE_PREVIEW")

    def test_future_publication_text_is_not_searchable(self):
        future = document(
            "FUTURE",
            published_at="2026-10-22T13:00:00Z",
            observed_at="2026-10-22T13:01:00Z",
            text="leakword future result",
        )
        report = build_report(bundle(document(), future), CUTOFF, query="leakword")
        self.assertEqual(cards(report), [])
        self.assertEqual(report["coverage"]["documents_excluded"], 1)
        self.assertIn("published_after_cutoff", report["excluded_documents"][0]["reasons"])
        self.assertEqual(report["primary_disclosures"][0]["document_count"], 1)

    def test_future_observation_is_excluded_by_default(self):
        late = document("LATE", observed_at="2026-10-22T13:00:00Z", text="leakword")
        report = build_report(bundle(late), CUTOFF, query="leakword")
        self.assertEqual(cards(report), [])
        self.assertIn("observed_after_cutoff", report["excluded_documents"][0]["reasons"])

    def test_unknown_times_remain_unknown(self):
        report = build_report(
            bundle(document("PUB", published_at=None), document("OBS", observed_at=None)), CUTOFF
        )
        reasons = {d["document_id"]: d["reasons"] for d in report["excluded_documents"]}
        self.assertIn("publication_time_unknown", reasons["PUB"])
        self.assertIn("observation_time_unknown", reasons["OBS"])
        self.assertEqual(report["coverage"]["documents_eligible"], 0)

    def test_public_mode_is_explicit_reconstruction(self):
        data = bundle(document("LATE", observed_at="2026-10-23T13:00:00Z"))
        observed = build_report(data, CUTOFF)
        public = build_report(data, CUTOFF, mode="public")
        self.assertEqual(cards(observed), [])
        self.assertEqual(len(cards(public)), 1)
        self.assertEqual(public["mode"], "public")
        self.assertNotEqual(public["availability_basis"], observed["availability_basis"])
        self.assertTrue(public["warnings"])

    def test_public_mode_cannot_recover_unknown_publication(self):
        report = build_report(bundle(document(published_at=None)), CUTOFF, mode="public")
        self.assertEqual(cards(report), [])

    def test_naive_timestamps_are_rejected(self):
        with self.assertRaises(ValueError):
            build_report(bundle(document()), "2026-10-22T12:00:00")
        with self.assertRaises(ValueError):
            build_report(bundle(document(published_at="2026-10-22T09:00:00")), CUTOFF)

    def test_microseconds_are_not_truncated_at_cutoff(self):
        report = build_report(bundle(document(observed_at="2026-10-22T12:00:00.000001Z")), CUTOFF)
        self.assertEqual(cards(report), [])

    def test_exact_cutoff_is_inclusive(self):
        report = build_report(bundle(document(published_at=CUTOFF, observed_at=CUTOFF)), CUTOFF)
        self.assertEqual(len(cards(report)), 1)

    def test_observation_cannot_predate_document_publication(self):
        data = bundle(document(observed_at="2026-10-22T08:59:59Z"))
        for mode in ("observed", "public"):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                build_report(data, CUTOFF, mode=mode)

    def test_duplicates_retain_citations_and_declared_lineage(self):
        data = bundle(
            document("ONE", source_family="wire-A"),
            document("COPY", publisher="Republisher", source_family="wire-A"),
        )
        card = cards(build_report(data, CUTOFF))[0]
        self.assertEqual(card["document_count"], 2)
        self.assertEqual(card["unique_content_count"], 1)
        self.assertEqual(card["duplicate_count"], 1)
        self.assertEqual(len(card["citations"]), 2)
        self.assertEqual(card["declared_source_families"], ["wire-A"])
        self.assertNotIn("independent_confirmations", card)

    def test_unknown_source_lineage_is_visible(self):
        card = cards(build_report(bundle(document(source_family=None)), CUTOFF))[0]
        self.assertEqual(card["source_lineage_unknown_count"], 1)
        self.assertEqual(card["declared_source_families"], [])

    def test_duplicate_copies_do_not_inflate_relevance(self):
        original = document("ORIGINAL")
        other = document("OTHER", event_id="OTHER-EVENT", text="Quarterly operating update.")
        before = cards(build_report(bundle(original, other), CUTOFF, query="capital"))[0]
        after = cards(
            build_report(bundle(original, other, document("COPY")), CUTOFF, query="capital")
        )[0]
        self.assertEqual(before["relevance_score"], after["relevance_score"])

    def test_same_ticker_and_event_name_do_not_merge_securities(self):
        data = bundle(
            document("US"),
            document("ID", security_ids=["SEC-2"]),
            securities=[security(), security("SEC-2", venue="XIDX", currency="IDR")],
        )
        report = build_report(data, CUTOFF)
        self.assertEqual(len(cards(report)), 2)
        selected = build_report(data, CUTOFF, security_id="SEC-2")
        self.assertEqual([c["security_ids"] for c in cards(selected)], [["SEC-2"]])

    def test_unrecognized_security_and_duplicate_ids_are_rejected(self):
        for data in (
            bundle(document(security_ids=["MISSING"])),
            bundle(document(), document()),
            bundle(document(), securities=[security(), security()]),
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                build_report(data, CUTOFF)

    def test_primary_lane_is_not_erased_by_query(self):
        report = build_report(bundle(document()), CUTOFF, query="absentkeyword")
        self.assertEqual(cards(report), [])
        self.assertEqual(len(report["primary_disclosures"]), 1)

    def test_relevance_is_deterministic_and_totals_survive_limit(self):
        data = bundle(*(document("DOC-" + str(i), event_id="EVENT-" + str(i)) for i in range(3)))
        report = build_report(data, CUTOFF, query="capital", limit=1)
        self.assertEqual(len(cards(report)), 1)
        self.assertEqual(report["coverage"]["search_events_total"], 3)
        self.assertEqual(report["coverage"]["primary_events_total"], 3)
        self.assertEqual(
            report, build_report(copy.deepcopy(data), CUTOFF, query="capital", limit=1)
        )

    def test_build_report_does_not_mutate_inputs(self):
        data = bundle(document(observations=[observation("120")]), consensus_document())
        original = copy.deepcopy(data)
        build_report(data, CUTOFF)
        self.assertEqual(data, original)

    def test_report_hash_tracks_input_bundle_and_not_query_cutoff(self):
        data = bundle(document())
        report = build_report(data, CUTOFF)
        self.assertRegex(report["input_bundle_sha256"], r"^[a-f0-9]{64}$")
        another_view = build_report(data, "2026-10-22T11:00:00Z", query="capital")
        self.assertEqual(report["input_bundle_sha256"], another_view["input_bundle_sha256"])
        changed = copy.deepcopy(data)
        changed["documents"][0]["text"] += " Amended supplied content."
        self.assertNotEqual(
            report["input_bundle_sha256"], build_report(changed, CUTOFF)["input_bundle_sha256"]
        )

    def test_compatible_figures_produce_inspectable_surprise(self):
        report = build_report(
            bundle(document(observations=[observation("120")]), consensus_document()), CUTOFF
        )
        result = compare(report)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(float(result["difference"]), 20)
        self.assertEqual(float(result["difference_pct"]), 20)
        self.assertEqual(len(result["evidence"]), 2)

    def test_zero_and_negative_consensus_keep_explicit_convention(self):
        for estimate, expected in (("0", None), ("-100", 220)):
            with self.subTest(estimate=estimate):
                result = compare(
                    build_report(
                        bundle(
                            document(observations=[observation("120")]),
                            consensus_document(estimate),
                        ),
                        CUTOFF,
                    )
                )
                if expected is None:
                    self.assertIsNone(result["difference_pct"])
                    self.assertTrue(result["reason"])
                else:
                    self.assertEqual(float(result["difference_pct"]), expected)
                self.assertEqual(result["percent_basis"], "100*(actual-consensus)/abs(consensus)")

    def test_incompatible_units_currencies_and_periods_are_not_joined(self):
        for change in ({"unit": "thousand"}, {"currency": "IDR"}, {"period": "FY2025"}):
            data = bundle(
                document(observations=[observation("120")]),
                consensus_document(observations=[observation("100", "CONSENSUS", **change)]),
            )
            for result in cards(build_report(data, CUTOFF))[0]["comparisons"]:
                self.assertEqual(result["status"], "INSUFFICIENT_DATA")
                self.assertIsNone(result["difference"])

    def test_conflict_blocks_only_affected_metric(self):
        entries = [observation("120"), observation("121"), observation("10", metric="ebit")]
        expectations = [
            observation("100", "CONSENSUS"),
            observation("8", "CONSENSUS", metric="ebit"),
        ]
        report = build_report(
            bundle(document(observations=entries), consensus_document(observations=expectations)),
            CUTOFF,
        )
        conflict = compare(report)
        self.assertEqual(conflict["status"], "DATA_CONFLICT")
        self.assertIsNone(conflict["difference"])
        self.assertEqual(compare(report, "ebit")["status"], "OK")

    def test_future_numeric_observation_does_not_contaminate_comparison(self):
        data = bundle(
            document("NOW", observations=[observation("120")]),
            consensus_document(),
            document(
                "FUTURE",
                published_at="2026-10-22T13:00:00Z",
                observed_at="2026-10-22T13:01:00Z",
                observations=[observation("999")],
            ),
        )
        result = compare(build_report(data, CUTOFF))
        self.assertEqual(result["status"], "OK")
        self.assertEqual(float(result["actual"]), 120)

    def test_consensus_published_with_or_after_result_is_withheld(self):
        for publication, observed in (
            ("2026-10-22T09:00:00Z", "2026-10-22T09:01:00Z"),
            ("2026-10-22T10:00:00Z", "2026-10-22T10:01:00Z"),
        ):
            with self.subTest(publication=publication):
                data = bundle(
                    document(observations=[observation("120")]),
                    consensus_document(published_at=publication, observed_at=observed),
                )
                result = compare(build_report(data, CUTOFF))
                self.assertEqual(result["status"], "INSUFFICIENT_DATA")
                self.assertTrue(result["reason"])
                for field in ("actual", "consensus", "difference", "difference_pct"):
                    self.assertIsNone(result[field])

    def test_same_document_consensus_is_not_pre_release_evidence(self):
        data = bundle(document(observations=[observation("120"), observation("100", "CONSENSUS")]))
        result = compare(build_report(data, CUTOFF))
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result["difference"])

    def test_consensus_must_precede_earliest_current_actual_document(self):
        data = bundle(
            document("FIRST", observations=[observation("120")]),
            document(
                "LATER",
                published_at="2026-10-22T11:00:00Z",
                observed_at="2026-10-22T11:01:00Z",
                observations=[observation("120")],
            ),
            consensus_document(
                published_at="2026-10-22T10:00:00Z", observed_at="2026-10-22T10:01:00Z"
            ),
        )
        result = compare(build_report(data, CUTOFF))
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result["difference"])

    def test_invalid_numeric_values_and_false_citations_are_rejected(self):
        for value in (True, "NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_report(bundle(document(observations=[observation(value)])), CUTOFF)
        with self.assertRaises(ValueError):
            build_report(
                bundle(document(text="unrelated", observations=[observation("120")])), CUTOFF
            )

    def test_correction_is_current_only_after_it_becomes_available(self):
        original = document("ORIGINAL", observations=[observation("100")])
        correction = document(
            "CORRECTION",
            published_at="2026-10-22T11:00:00Z",
            observed_at="2026-10-22T11:01:00Z",
            replaces_document_id="ORIGINAL",
            observations=[observation("120")],
        )
        future = document(
            "FUTURE",
            published_at="2026-10-22T13:00:00Z",
            observed_at="2026-10-22T13:01:00Z",
            replaces_document_id="CORRECTION",
            observations=[observation("999")],
        )
        data = bundle(original, correction, future, consensus_document("110"))
        earlier = build_report(data, "2026-10-22T10:00:00Z")
        current = build_report(data, CUTOFF)
        self.assertEqual(float(compare(earlier)["actual"]), 100)
        self.assertEqual(float(compare(current)["actual"]), 120)
        self.assertEqual(cards(current)[0]["current_document_ids"], ["CONSENSUS", "CORRECTION"])
        self.assertEqual(cards(current)[0]["superseded_document_ids"], ["ORIGINAL"])
        self.assertEqual(len(cards(current)[0]["citations"]), 3)

    def test_invalid_correction_graphs_are_rejected(self):
        datasets = [
            bundle(document(replaces_document_id="DOC-1")),
            bundle(
                document("A", replaces_document_id="B"), document("B", replaces_document_id="A")
            ),
            bundle(document("A"), document("B", event_id="OTHER", replaces_document_id="A")),
            bundle(
                document("A"),
                document("B", security_ids=["SEC-2"], replaces_document_id="A"),
                securities=[security(), security("SEC-2")],
            ),
        ]
        for data in datasets:
            with self.subTest(data=data), self.assertRaises(ValueError):
                build_report(data, CUTOFF)

    def test_schema_mode_and_limits_are_validated(self):
        for data, kwargs in (
            (dict(bundle(document()), schema_version="UNKNOWN"), {}),
            (dict(bundle(document()), synthetic="true"), {}),
            (bundle(document()), {"mode": "unknown"}),
            (bundle(document()), {"limit": 0}),
            (bundle(document()), {"limit": True}),
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build_report(data, CUTOFF, **kwargs)

    def cli(self, directory, *args):
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, "-m", "kod.workbench", *args],
            cwd=directory,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_cli_json_markdown_and_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            input_path.write_text(json.dumps(bundle(document())), encoding="utf-8")
            args = ("--input", str(input_path), "--as-of", CUTOFF)
            output = self.cli(directory, *args)
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertTrue(json.loads(output.stdout)["research_only"])
            markdown = self.cli(directory, *args, "--format", "markdown")
            self.assertEqual(markdown.returncode, 0, markdown.stderr)
            self.assertIn("research", markdown.stdout.lower())
            self.assertIn("synthetic", markdown.stdout.lower())
            input_path.write_text("{invalid", encoding="utf-8")
            invalid = self.cli(directory, *args)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertTrue(invalid.stderr)
            self.assertNotIn("Traceback", invalid.stderr)

    def test_cli_does_not_create_database_or_mutate_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "registry").mkdir()
            (root / "registry" / "immutable.json").write_text('{"frozen":true}', encoding="utf-8")
            (root / "var").mkdir()
            (root / "var" / "kod.db").write_bytes(b"database sentinel")
            source = root / "bundle.json"
            source.write_text(json.dumps(bundle(document())), encoding="utf-8")

            def snapshot():
                return {
                    str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob("*")
                    if p.is_file()
                }

            before = snapshot()
            result = self.cli(directory, "--input", str(source), "--as-of", CUTOFF)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(snapshot(), before)

    def test_markdown_escapes_supplied_html_and_link_markup(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bundle.json"
            source.write_text(
                json.dumps(
                    bundle(
                        document(title="<script>bad</script>", text="[click](javascript:alert(1))")
                    )
                ),
                encoding="utf-8",
            )
            output = self.cli(
                directory, "--input", str(source), "--as-of", CUTOFF, "--format", "markdown"
            )
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertNotIn("<script>", output.stdout)
            self.assertNotIn("[click](javascript:alert(1))", output.stdout)

    def test_markdown_citation_has_clickable_source_link(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bundle.json"
            source.write_text(json.dumps(bundle(document())), encoding="utf-8")
            output = self.cli(
                directory, "--input", str(source), "--as-of", CUTOFF, "--format", "markdown"
            )
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertIn("[Synthetic Issuer](<https://example.invalid/DOC-1>)", output.stdout)

    def test_markdown_url_delimiters_and_controls_are_encoded(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bundle.json"
            data = bundle(document(source_url="https://example.invalid/doc>\n<script>x</script>"))
            source.write_text(json.dumps(data), encoding="utf-8")
            output = self.cli(
                directory, "--input", str(source), "--as-of", CUTOFF, "--format", "markdown"
            )
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertNotIn("<script>", output.stdout)
            self.assertNotIn("doc>\n<script>", output.stdout)
            self.assertIn(
                "https://example.invalid/doc%3E%0A%3Cscript%3Ex%3C/script%3E", output.stdout
            )


if __name__ == "__main__":
    unittest.main()
