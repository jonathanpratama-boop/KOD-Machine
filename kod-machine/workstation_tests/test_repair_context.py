"""Behavioral regressions for repeat revisions and source-bound scenario context."""

import json
import sqlite3
from unittest.mock import patch
from workstation_tests.test_stabilization import Case, CASE, META
from kod.workstation import calculations, decisions, dossier, migrations, scenarios, thesis
from kod.workstation.policy import AsOfPolicy, DAY_END


def _import_prices_in_process(root, source, start, ready):
    from kod.workstation.store import Store
    from kod.workstation.services import ResearchService

    service = ResearchService(Store(root), clock=lambda: "2024-12-01T12:00:00Z")
    sid = service.store.securities()[0]["id"]
    ready.wait(timeout=15)
    for close in range(start, start + 5):
        scenarios.add_manual_price(
            service, sid, "2024-11-29", str(close), {**META, "source": source}
        )


class RevisionSequences(Case):
    def test_repeated_reversions_and_retry_at_one_timestamp(self):
        policy = AsOfPolicy.parse("2024-12-02T00:00:00Z", "observed", DAY_END)
        sid = self.sec["id"]
        for value in (100, 101, 100, 101, 100, 101, 100):
            result = scenarios.add_manual_price(self.service, sid, "2024-11-29", str(value), META)
            self.assertEqual(result["added"], 1)
            self.assertEqual(scenarios.price_at(self.service, sid, policy)["close"], str(value))
            retry = scenarios.add_manual_price(self.service, sid, "2024-11-29", str(value), META)
            self.assertEqual(retry["added"], 0)
        self.assertEqual(len(scenarios.price_list(self.service, sid)), 7)
        self.assertEqual(
            [p["seq"] for p in scenarios.price_list(self.service, sid)], list(range(7, 0, -1))
        )

    def test_concurrent_processes_have_one_durable_order_and_independent_series(self):
        import multiprocessing

        context = multiprocessing.get_context("spawn")
        ready = context.Barrier(2)
        workers = [
            context.Process(
                target=_import_prices_in_process, args=(self.store.root, source, start, ready)
            )
            for source, start in [("feed A", 100), ("feed B", 200)]
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=30)
            if worker.is_alive():
                worker.terminate()
                worker.join()
            self.assertEqual(worker.exitcode, 0)
        rows = scenarios.price_list(self.service, self.sec["id"])
        self.assertEqual([r["seq"] for r in rows], list(range(10, 0, -1)))
        for source, close in [("feed A", "104"), ("feed B", "204")]:
            self.assertEqual(next(r for r in rows if r["source"] == source)["close"], close)


class ClassificationContext(Case):
    def scenario_thesis(self):
        return decisions.save_thesis(
            self.service,
            self.sec["id"],
            "scenario review",
            "The base case applies.",
            [
                thesis.comparison(
                    {
                        "kind": "scenario",
                        "scenario": "base",
                        "name": "default",
                        "measure": "per_share",
                    },
                    "<",
                    {
                        "kind": "constant",
                        "value": "100",
                        "unit": "currency/share",
                        "currency": "USD",
                    },
                    "Review the base case",
                    "base_value",
                )
            ],
            "fixture",
        )

    def submissions(self, sic):
        raw = json.dumps({"sic": sic, "sicDescription": "fixture"}).encode()
        return self.store.save_document(
            self.sec["id"],
            raw,
            "submissions.json",
            "https://data.sec.gov/submissions/CIK0000000001.json",
            published_at=None,
            published_basis="API snapshot",
            observed_at=self.now[0],
            role="metadata",
            association="verified_from_filing_metadata",
            provider="sec",
            external_id="submissions:1",
            extraction_status="metadata",
            metadata={"kind": "SEC submissions response"},
        )

    def test_same_second_classifications_follow_durable_recording_order(self):
        policy = AsOfPolicy.parse(self.now[0], "observed", DAY_END)
        sources = []
        for sic in ("3571", "6022", "3572", "6035", "3573", "3574", "3571", "6022", "3571"):
            sources.append(self.submissions(sic))
            selected = self.service.submissions_context(self.sec["id"], policy)
            self.assertEqual(selected["data"]["sic"], sic)
            self.assertEqual(selected["source"]["recording_seq"], len(sources))
        old = self.service.submissions_context(self.sec["id"], policy, legacy=True)
        self.assertEqual(old["source"]["document_id"], max(d["id"] for d in sources))
        public = self.service.submissions_context(
            self.sec["id"], AsOfPolicy.parse(self.now[0], "public", DAY_END)
        )
        self.assertEqual(public["source"]["document_id"], sources[0]["id"])

    def test_dossier_and_trace_use_requested_cutoff_with_source_lineage(self):
        a = self.submissions("3571")
        self.now[0] = "2024-12-02T12:00:00Z"
        v = scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "fixture")
        self.scenario_thesis()
        old_policy = AsOfPolicy.parse(self.now[0], "observed", DAY_END)
        old = scenarios.run_version(self.service, v["id"])
        self.now[0] = "2024-12-10T12:00:00Z"
        b = self.submissions("6022")
        policy = AsOfPolicy.parse(self.now[0], "observed", DAY_END)
        d = dossier.build(self.service, self.sec["id"], policy)
        trace = decisions._assumption_trace(self.service, v["id"], policy)
        self.assertEqual(d["scenarios"][0]["status"], "not_applicable")
        self.assertEqual(trace["result"]["status"], d["scenarios"][0]["status"])
        self.assertEqual(trace["source_context"], d["classification_context"])
        self.assertEqual(trace["source_context"]["document_id"], b["id"])
        self.assertEqual(
            scenarios.run_version(self.service, v["id"], policy=old_policy).calculation_id,
            old.calculation_id,
        )
        later = scenarios.run_version(self.service, v["id"], policy=policy)
        with self.store._connection() as db:
            lineage = calculations.lineage(db, later.calculation_id)
        self.assertEqual(
            lineage["source_documents"],
            [{"role": "business_classification", "document_id": b["id"], "sha256": b["sha256"]}],
        )
        self.assertEqual(old.calculation.detail["source_context"]["document_id"], a["id"])
        review = decisions.review(self.service, self.sec["id"], policy)
        evaluation = review["theses"][0]["evaluations"][0]
        operand = evaluation["trace"][0]["left"]
        self.assertEqual(evaluation["status"], "unresolved")
        self.assertEqual(
            operand["sources"]["assumption_trace"]["result"]["status"], d["scenarios"][0]["status"]
        )
        self.assertEqual(
            operand["sources"]["assumption_trace"]["source_context"], d["classification_context"]
        )

    def test_source_identity_changes_calculation_even_when_value_is_identical(self):
        self.submissions("3571")
        v = scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "fixture")
        policy = AsOfPolicy.parse("2024-12-30T00:00:00Z", "observed", DAY_END)
        one = scenarios.run_version(self.service, v["id"], policy=policy)
        self.now[0] = "2024-12-03T12:00:00Z"
        self.submissions("3572")
        two = scenarios.run_version(self.service, v["id"], policy=policy)
        self.assertEqual(one.valuation.per_share, two.valuation.per_share)
        self.assertNotEqual(one.calculation_id, two.calculation_id)

    def test_unknown_context_is_explicit_and_legacy_hash_recipe_still_available(self):
        v = scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "fixture")
        current = scenarios.run_version(self.service, v["id"])
        old = scenarios.run_version(self.service, v["id"], legacy=True)
        self.assertEqual(current.calculation.detail["source_context"]["availability"], "unknown")
        self.assertNotIn("context_version", old.calculation.detail)
        self.assertEqual(current.valuation.per_share, old.valuation.per_share)
        self.assertNotEqual(current.calculation_id, old.calculation_id)

    def test_legacy_packet_reproduction_dispatch_and_immutable_sources(self):
        self.submissions("3571")
        scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "fixture")
        self.scenario_thesis()
        policy = AsOfPolicy.parse(self.now[0], "observed", DAY_END)
        # Generate the old shape through explicit version dispatch, then exercise normal reader/reproduce.
        original = decisions._packet_body
        with patch.object(
            decisions,
            "_packet_body",
            side_effect=lambda *args, **kw: original(*args, schema=decisions.LEGACY_PACKET_SCHEMA),
        ):
            saved = decisions.save_packet(
                self.service, self.sec["id"], policy, "as_reported", "question", "watch", "fixture"
            )
        self.assertEqual(saved["packet"]["schema"], decisions.LEGACY_PACKET_SCHEMA)
        self.assertTrue(decisions.reproduce(self.service, saved["id"])["reproduced"])
        self.assertNotIn("classification_context", saved["packet"]["dossier"])
        trace = saved["packet"]["theses"][0]["evaluations"][0]["trace"][0]["left"]["sources"][
            "assumption_trace"
        ]
        self.assertNotIn("source_context", trace)
        self.assertTrue(decisions.packet(self.service, saved["id"])["packet_sha256"])

    def test_packet_replays_selected_price_and_classification_after_same_second_imports(self):
        source = self.submissions("3571")
        scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "fixture")
        self.scenario_thesis()
        decisions.save_thesis(
            self.service,
            self.sec["id"],
            "price review",
            "The price stays below the limit.",
            [
                thesis.comparison(
                    {"kind": "price", "measure": "latest_close"},
                    ">",
                    {
                        "kind": "constant",
                        "value": "100.5",
                        "unit": "currency/share",
                        "currency": "USD",
                    },
                    "Review the price",
                    "price_limit",
                )
            ],
            "fixture",
        )
        scenarios.add_manual_price(self.service, self.sec["id"], "2024-11-29", "100", META)
        policy = AsOfPolicy.parse(self.now[0], "observed", DAY_END)
        saved = decisions.save_packet(
            self.service, self.sec["id"], policy, "as_reported", "question", "watch", "fixture"
        )
        scenarios.add_manual_price(self.service, self.sec["id"], "2024-11-29", "101", META)
        self.submissions("6022")
        self.assertEqual(scenarios.price_at(self.service, self.sec["id"], policy)["close"], "101")
        self.assertEqual(
            saved["packet"]["source_membership"]["classification"]["document_id"], source["id"]
        )
        self.assertEqual(saved["packet"]["price"]["close"], "100")
        self.assertTrue(decisions.reproduce(self.service, saved["id"])["reproduced"])

    def test_packet_preserves_unknown_classification_and_absent_price_at_freeze(self):
        scenarios.save_assumptions(self.service, self.sec["id"], "base", CASE, "fixture")
        self.scenario_thesis()
        policy = AsOfPolicy.parse(self.now[0], "observed", DAY_END)
        saved = decisions.save_packet(
            self.service, self.sec["id"], policy, "as_reported", "question", "watch", "fixture"
        )
        self.submissions("6022")
        scenarios.add_manual_price(self.service, self.sec["id"], "2024-11-29", "101", META)
        self.assertEqual(
            dossier.build(self.service, self.sec["id"], policy)["scenarios"][0]["status"],
            "not_applicable",
        )
        self.assertTrue(decisions.reproduce(self.service, saved["id"])["reproduced"])

    def test_packet_replay_verifies_frozen_classification_bytes(self):
        source = self.submissions("3571")
        policy = AsOfPolicy.parse(self.now[0], "observed", DAY_END)
        saved = decisions.save_packet(
            self.service, self.sec["id"], policy, "as_reported", "question", "watch", "fixture"
        )
        self.store._object_path(source["sha256"]).write_bytes(b"corrupt source")
        with self.assertRaisesRegex(ValueError, "SHA-256|hash|integrity"):
            decisions.reproduce(self.service, saved["id"])


class MigrationAndRecovery(Case):
    def test_lineage_migration_preserves_existing_migration_checksums_and_rows(self):
        import tempfile
        from pathlib import Path
        from kod.workstation.domain import APP_VERSION
        from kod.workstation.store import Store

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "old"
            root.mkdir()
            # Use the exact filename used by Store, without constructing a new-schema store first.
            from kod.workstation.store import DB_NAME

            path = root / DB_NAME
            migrations.ensure_schema(path, APP_VERSION, migrations=migrations.MIGRATIONS[:5])
            db = sqlite3.connect(path)
            before = db.execute(
                "SELECT version, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
            db.close()
            store = Store(root)
            self.assertEqual(store.migration["applied"], [6])
            with store._connection() as db:
                after = [
                    tuple(row)
                    for row in db.execute(
                        "SELECT version, checksum FROM schema_migrations WHERE version<=5 ORDER BY version"
                    )
                ]
            self.assertEqual(before, after)
            self.assertEqual(Store(root).migration["applied"], [])

    def test_backup_restore_preserves_repeated_revisions_and_lineage(self):
        import tempfile
        from pathlib import Path
        from kod.workstation.store import Store
        from kod.workstation.services import ResearchService

        sid = self.sec["id"]
        source = ClassificationContext.submissions(self, "3571")
        version = scenarios.save_assumptions(self.service, sid, "base", CASE, "fixture")
        result = scenarios.run_version(self.service, version["id"])
        with self.store._connection() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM calculation_source_documents")
        for v in (100, 101, 100, 101, 100):
            scenarios.add_manual_price(self.service, sid, "2024-11-29", str(v), META)
        with tempfile.TemporaryDirectory() as temp:
            backup = self.store.backup(Path(temp) / "backup")
            restored = Store.restore(backup, Path(temp) / "restored")
            # restore returns a Store (current API).
            if not isinstance(restored, Store):
                restored = Store(Path(temp) / "restored")
            other = ResearchService(restored, clock=self.service.clock)
            self.assertEqual(
                scenarios.price_list(self.service, sid), scenarios.price_list(other, sid)
            )
            with restored._connection() as db:
                lineage = calculations.lineage(db, result.calculation_id)
            self.assertEqual(lineage["source_documents"][0]["sha256"], source["sha256"])
            self.assertEqual(restored.raw(source["id"]), self.store.raw(source["id"]))
