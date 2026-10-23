"""Gate B: upgrading a real v1 workspace, transactional migrations, separate identity, immutable observations, one cutoff policy and calculation lineage."""

from datetime import date
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from kod import earnings
from kod.workstation import calculations, financials, migrations
from kod.workstation.financials import FinancialRepository, Period, ResolvedFigure
from kod.workstation.policy import DAY_END, STRICT, AsOfPolicy, eligibility
from kod.workstation.services import ResearchService
from kod.workstation.store import DB_NAME, SCHEMA_VERSION, Store

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
V1_TABLES = ("securities", "objects", "documents", "observations", "events", "event_revisions", "notes", "annotations", "jobs")
NOW = "2026-10-23T12:00:00Z"


def v1_workspace(root: Path) -> Path:
    """Rebuild the real v1 workspace (see fixtures/README.md) in `root`."""
    manifest = json.loads((FIXTURES / "v1_workspace_objects.json").read_text())
    dump = gzip.decompress((FIXTURES / "v1_workspace.sql.gz").read_bytes())
    assert hashlib.sha256(dump).hexdigest() == manifest["dump_sha256"]
    root.mkdir(parents=True)
    db = sqlite3.connect(root / DB_NAME)
    db.executescript(dump.decode())
    db.execute(f"PRAGMA user_version={manifest['user_version']}")
    db.commit()
    db.close()
    for sha, rel in manifest["objects"].items():
        target = root / "objects" / sha[:2] / sha
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    return root


def table_rows(path: Path, tables=V1_TABLES) -> dict:
    db = sqlite3.connect(path)
    try:
        return {t: sorted(tuple(r) for r in db.execute(f"SELECT * FROM {t}")) for t in tables}
    finally:
        db.close()


class TempCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)


class V1UpgradeTests(TempCase):
    def test_a_populated_v1_workspace_upgrades_with_everything_retained(self):
        root = v1_workspace(self.base / "v1")
        before = table_rows(root / DB_NAME)
        self.assertEqual(len(before["notes"]), 4)
        self.assertEqual(len(before["annotations"]), 2)
        store = Store(root)
        self.assertEqual((store.migration["from"], store.migration["to"], store.migration["applied"]), (1, SCHEMA_VERSION, list(range(2, SCHEMA_VERSION + 1))))
        self.assertEqual(table_rows(root / DB_NAME), before)                     # every v1 row is byte-for-byte unchanged
        copy = Path(store.migration["safety_copy"])
        self.assertEqual(table_rows(copy), before)
        with sqlite3.connect(copy) as check:
            self.assertEqual(check.execute("PRAGMA user_version").fetchone()[0], 1)
        check.close()
        db = sqlite3.connect(root / DB_NAME)
        recorded = db.execute("SELECT version, checksum FROM schema_migrations ORDER BY version").fetchall()
        db.close()
        self.assertEqual(recorded[0], (1, hashlib.sha256(migrations.V1_DDL.encode()).hexdigest()))
        self.assertEqual(recorded[0][1], "f274262de50045d18c7efcf685b85c59be5fe7688226c41461764a3770409f53")  # the v1 DDL as released at 0281272
        # Old links keep working: notes, annotation history, sources and their integrity.
        for note in store.notes():
            self.assertEqual(store.note(note["id"])["markdown"], next(r for r in before["notes"] if r[0] == note["id"])[5])
        self.assertEqual([a["thesis"] for a in store.annotations(store.notes()[-1]["id"]) + store.annotations(store.notes()[0]["id"])].count("Data center demand persists"), 1)
        for doc in store.documents():
            self.assertEqual(hashlib.sha256(store.raw(doc["id"])).hexdigest(), doc["sha256"])

    def test_identity_is_split_without_changing_security_ids_or_backdating_aliases(self):
        store = Store(v1_workspace(self.base / "v1"))
        for sec in store.securities():
            ident = store.identity(sec["id"])
            self.assertEqual(ident["listing_id"], sec["id"])
            self.assertEqual((ident["cik"], ident["venue"], ident["trading_currency"]), (sec["cik"], sec["venue"], sec["currency"]))
            ticker = next(a for a in ident["aliases"] if a["id_type"] == "ticker")
            self.assertEqual((ticker["value"], ticker["valid_from"], ticker["valid_to"]), (sec["ticker"], None, None))
            self.assertEqual(ticker["evidence"]["validity"], "unknown; not backdated")
        # A listing that later learns its CIK gets a new mapping version; the earlier one is kept.
        acme = store.upsert_security("ACME", "Acme", cik=None)
        first = store.identity(acme["id"])["issuer_id"]
        store.upsert_security("ACME", "Acme", cik="1234")
        with store._connection() as db:
            mapped = [r["issuer_id"] for r in db.execute("SELECT issuer_id FROM security_identity WHERE security_id=? ORDER BY id", (acme["id"],))]
        self.assertEqual(len(mapped), 2)
        self.assertEqual(mapped[0], first)
        self.assertNotEqual(mapped[1], first)

    def test_preserved_releases_are_indexed_into_observations_after_upgrade(self):
        store = Store(v1_workspace(self.base / "v1"))
        service = ResearchService(store, clock=lambda: NOW)
        first = service.index_documents()
        self.assertEqual(first["documents"], 8)                                  # four current and four earlier releases; headers are not releases
        self.assertGreater(first["observations"], 100)
        self.assertEqual(service.index_documents(), {"documents": 0, "observations": 0, "skipped": []})   # idempotent
        nvda = next(s for s in store.securities() if s["ticker"] == "NVDA")
        policy = AsOfPolicy.parse("2024-11-20T22:00:00Z", "public")
        revenue = [o for o in FinancialRepository(store).observations(nvda["id"], "revenue", policy) if o.period.fiscal_label == "Q3 FY25" and o.basis == "GAAP"]
        self.assertEqual({(o.value, o.unit, o.scale, o.currency) for o in revenue}, {(Decimal("35082000000"), "currency", 10**6, "USD")})
        self.assertEqual(revenue[0].period.end_date, "2024-10-27")                 # stated by the release headline
        self.assertEqual(revenue[0].accession, "0001045810-24-000315")
        self.assertIn("table", revenue[0].evidence)

    def test_backup_and_restore_after_the_upgrade(self):
        store = Store(v1_workspace(self.base / "v1"))
        ResearchService(store, clock=lambda: NOW).index_documents()
        note = store.notes()[0]
        store.annotate(note["id"], "after upgrade", "", "")
        backup = store.backup(self.base / "backup")
        restored = Store.restore(backup, self.base / "restored")
        tables = V1_TABLES + ("issuers", "listings", "identifier_aliases", "security_identity", "periods", "financial_observations", "schema_migrations")
        self.assertEqual(table_rows(restored.path, tables), table_rows(store.path, tables))
        self.assertEqual(restored.annotations(note["id"])[0]["thesis"], "after upgrade")
        self.assertEqual(json.loads((backup / "BACKUP.json").read_text())["schema_version"], SCHEMA_VERSION)

    def test_a_v1_backup_restores_into_an_upgraded_workspace_and_stays_unchanged(self):
        root = v1_workspace(self.base / "v1")
        backup = self.base / "v1-backup"
        shutil.copytree(root, backup)
        files = {DB_NAME: hashlib.sha256((backup / DB_NAME).read_bytes()).hexdigest()}
        for path in (backup / "objects").rglob("*"):
            if path.is_file():
                files[path.relative_to(backup).as_posix()] = path.name
        (backup / "BACKUP.json").write_text(json.dumps({"schema_version": 1, "app_version": "KOD-WORKSTATION-v1", "files": files}))
        frozen = hashlib.sha256((backup / DB_NAME).read_bytes()).hexdigest()
        restored = Store.restore(backup, self.base / "restored")
        self.assertEqual(restored.migration["from"], 1)
        self.assertEqual(len(restored.notes()), 4)
        self.assertEqual(hashlib.sha256((backup / DB_NAME).read_bytes()).hexdigest(), frozen)


class MigrationSafetyTests(TempCase):
    def test_a_failing_migration_rolls_back_and_leaves_v1_intact(self):
        root = v1_workspace(self.base / "v1")
        before = table_rows(root / DB_NAME)
        with mock.patch("kod.workstation.identity.backfill", side_effect=RuntimeError("simulated failure")):
            with self.assertRaisesRegex(ValueError, "migration 2 .* failed and was rolled back; the database remains at v1"):
                Store(root)
        db = sqlite3.connect(root / DB_NAME)
        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='issuers'").fetchone())
        db.close()
        self.assertEqual(table_rows(root / DB_NAME), before)
        self.assertEqual(Store(root).migration["to"], SCHEMA_VERSION)              # the next start, without the fault, upgrades normally

    def test_a_broken_later_migration_is_rolled_back_whole(self):
        path = self.base / "fresh.sqlite3"
        migrations.ensure_schema(path, "test")
        broken = migrations.MIGRATIONS + (migrations.Migration(SCHEMA_VERSION + 1, "broken", "CREATE TABLE half_done(x INTEGER);\nCREATE TABLE half_done(x INTEGER);\n"),)
        with self.assertRaises(migrations.MigrationError):
            migrations.ensure_schema(path, "test", broken)
        db = sqlite3.connect(path)
        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
        self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='half_done'").fetchone())
        db.close()

    def test_a_newer_or_different_schema_is_refused_without_change(self):
        root = self.base / "ws"
        Store(root)
        db = sqlite3.connect(root / DB_NAME)
        db.execute("PRAGMA user_version=99")
        db.commit()
        db.close()
        frozen = (root / DB_NAME).read_bytes()
        with self.assertRaisesRegex(ValueError, "newer than this application"):
            Store(root)
        self.assertEqual((root / DB_NAME).read_bytes(), frozen)
        other = self.base / "other"
        Store(other)
        db = sqlite3.connect(other / DB_NAME)
        db.execute("UPDATE schema_migrations SET checksum='0' WHERE version=2")
        db.commit()
        db.close()
        with self.assertRaisesRegex(ValueError, "differs from this application"):
            Store(other)


RELEASE = (ROOT / "examples" / "earnings_demo" / "current_q3fy25pr.htm").read_bytes()
HEADERS = (ROOT / "examples" / "earnings_demo" / "current_0001045810-24-000315-index-headers.html").read_bytes()
URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000315/q3fy25pr.htm"


class ObservationTests(TempCase):
    def setUp(self):
        super().setUp()
        self.store = Store(self.base / "ws")
        self.service = ResearchService(self.store, clock=lambda: NOW)
        self.sec = self.store.upsert_security("NVDA", "NVIDIA Corporation", cik="1045810")

    def ingest(self, **kw):
        return self.service.ingest(self.sec["id"], RELEASE, "q3fy25pr.htm", URL, sec_headers=HEADERS, retrieved_at="2026-10-22T14:40:11Z", **kw)

    def test_observations_are_immutable_and_reingest_is_idempotent(self):
        doc = self.ingest()
        count = self.store.observation_count(doc["id"])
        self.assertGreater(count, 20)
        self.assertEqual(self.ingest()["id"], doc["id"])
        self.assertEqual(self.store.observation_count(doc["id"]), count)
        with self.store._connection() as db:
            oid = db.execute("SELECT id FROM financial_observations LIMIT 1").fetchone()[0]
        for sql in ("UPDATE financial_observations SET value='1' WHERE id=?", "DELETE FROM financial_observations WHERE id=?"):
            with self.assertRaisesRegex(sqlite3.DatabaseError, "immutable"):
                with self.store._connection() as db:
                    db.execute(sql, (oid,))

    def test_a_new_parser_version_adds_an_attributable_interpretation(self):
        doc = self.ingest()
        old = self.store.observation_count(doc["id"])
        with mock.patch.object(earnings, "PARSER_VERSION", "KOD-EARNINGS-PARSER-test"):
            self.service.index_documents()
            self.assertEqual(self.store.observation_count(doc["id"], "KOD-EARNINGS-PARSER-test"), old)
        self.assertEqual(self.store.observation_count(doc["id"]), 2 * old)

    def test_values_keep_their_raw_text_and_base_units(self):
        self.ingest()
        policy = AsOfPolicy.parse("2024-11-21T00:00:00Z", "public")
        eps = [o for o in FinancialRepository(self.store).observations(self.sec["id"], "eps_diluted", policy) if o.basis == "GAAP" and o.period.fiscal_label == "Q3 FY25"]
        self.assertEqual({(o.raw_value, o.value, o.unit, o.scale) for o in eps}, {("0.78", Decimal("0.78"), "currency/share", 1)})
        with self.store._connection() as db:
            self.assertEqual({r[0] for r in db.execute("SELECT typeof(value) FROM financial_observations")}, {"text"})


def obs(value, published, end="2024-09-30", observed="2026-01-01T00:00:00Z", publication_date=None, oid=None, kind="quarter", basis="GAAP"):
    p = Period("per_" + end + kind, kind, None, end, None, None, None)
    return financials.FinancialObservation(oid or f"fob_{value}_{published}", "test", "iss", "sec", "Revenue", "t", "revenue", 1, str(value), Decimal(value), "currency",
                                           10**6, "USD", "TABLE_STATEMENT", p, basis, "consolidated", None, None, None, None, None, "0" * 64, {}, published,
                                           publication_date, "second" if published else "date", "test", observed, observed, "p", "m", ())


class PolicyTests(unittest.TestCase):
    def test_strict_and_day_end_policies(self):
        dated = {"published_at": None, "publication_date": "2024-11-20", "observed_at": "2024-11-20T23:00:00Z"}
        strict = AsOfPolicy.parse("2024-11-22T00:00:00Z", "public")
        self.assertEqual(eligibility(dated, strict), (False, ("publication_date_only_under_strict_policy",)))
        # A filing dated 20 November counts from 00:00 New York time on 21 November (05:00 UTC), never earlier.
        self.assertFalse(eligibility(dated, AsOfPolicy.parse("2024-11-21T04:59:59Z", "public", DAY_END))[0])
        self.assertTrue(eligibility(dated, AsOfPolicy.parse("2024-11-21T05:00:00Z", "public", DAY_END))[0])
        observed = AsOfPolicy.parse("2024-11-20T22:00:00Z", "observed")
        self.assertEqual(eligibility({"published_at": "2024-11-20T21:00:00Z", "observed_at": "2026-10-22T00:00:00Z"}, observed), (False, ("observed_after_cutoff",)))
        with self.assertRaises(ValueError):
            AsOfPolicy(date(2024, 1, 1), "public")  # not a timezone-aware datetime
        with self.assertRaises(ValueError):
            AsOfPolicy.parse("2024-11-20T22:00:00Z", "public", "made-up-policy")

    def test_a_later_amendment_never_changes_an_earlier_cutoff_view(self):
        original, amended = obs(100, "2024-11-01T21:00:00Z"), obs(105, "2025-02-01T21:00:00Z")
        early, late = AsOfPolicy.parse("2024-12-31T00:00:00Z", "public"), AsOfPolicy.parse("2025-03-01T00:00:00Z", "public")
        for view in ("as_reported", "latest"):
            eligible = [o for o in (original, amended) if eligibility(o.availability(), early)[0]]
            self.assertEqual(financials.resolve(eligible, early, view)[0].value, Decimal(100))
        both = [o for o in (amended, original) if eligibility(o.availability(), late)[0]]
        self.assertEqual(financials.resolve(both, late, "as_reported")[0].value, Decimal(100))
        self.assertEqual(financials.resolve(both, late, "latest")[0].value, Decimal(105))
        self.assertEqual(financials.resolve(both, late, "latest")[0].other_ids, (original.id,))

    def test_simultaneous_different_values_are_a_conflict_and_equal_ones_corroborate(self):
        policy = AsOfPolicy.parse("2025-03-01T00:00:00Z", "public")
        conflict = financials.resolve([obs(100, "2024-11-01T21:00:00Z", oid="a"), obs(101, "2024-11-01T21:00:00Z", oid="b")], policy)[0]
        self.assertEqual((conflict.status, conflict.value, set(conflict.observation_ids)), ("conflicted", None, {"a", "b"}))
        agree = financials.resolve([obs(100, "2024-11-01T21:00:00Z", oid="a"), obs(100, "2024-11-01T21:00:00Z", oid="b")], policy)[0]
        self.assertEqual((agree.status, agree.value), ("ok", Decimal(100)))


def figure(metric, value, end="2024-09-30", kind="quarter", basis="GAAP", unit="currency", currency="USD", scale=10**6, status="ok", label=None, oid=None):
    p = Period(f"per_{end}_{kind}_{label}", kind, None, end, None, label, None)
    return ResolvedFigure(metric, p, basis, unit, scale, currency, "consolidated", status, Decimal(value) if status == "ok" else None, (oid or f"fob_{metric}_{end}",), (),
                          "as_reported", () if status == "ok" else ("two values",))


class CalculationTests(TempCase):
    def test_growth_requires_a_compatible_earlier_period_and_a_positive_base(self):
        cur, prior = figure("revenue", 120), figure("revenue", 100, end="2023-09-30")
        ok = calculations.growth(cur, prior)
        self.assertEqual((ok.status, ok.value, ok.unit), ("ok", Decimal(20), "percent"))
        self.assertEqual(calculations.growth(prior, cur).status, "incompatible")                      # not earlier
        self.assertEqual(calculations.growth(cur, figure("revenue", 400, end="2023-12-31", kind="12 months")).status, "incompatible")
        self.assertEqual(calculations.growth(cur, figure("revenue", 100, end="2023-09-30", basis="NON-GAAP")).status, "incompatible")
        self.assertEqual(calculations.growth(cur, figure("revenue", 100, end="2023-09-30", currency="CAD")).status, "incompatible")
        self.assertEqual(calculations.growth(cur, figure("revenue", 100, end="2023-09-30", scale=None)).status, "incompatible")
        self.assertEqual(calculations.growth(cur, figure("revenue", -5, end="2023-09-30")).status, "not_applicable")
        self.assertEqual(calculations.growth(cur, None).status, "missing")
        self.assertEqual(calculations.growth(cur, figure("revenue", 0, end="2023-09-30", status="conflicted")).status, "conflicted")
        labelled = calculations.growth(figure("revenue", 120, end=None, label="Q3 FY25"), figure("revenue", 100, end=None, label="Q3 FY24"))
        self.assertEqual(labelled.status, "ok")
        self.assertEqual(calculations.growth(figure("revenue", 120, end=None, label="Q3 FY25"), figure("revenue", 100, end=None, label="Q3 2024")).status, "incompatible")

    def test_margins_need_profit_over_revenue_and_change_in_points(self):
        m_now = calculations.operating_margin(figure("operating_income", 30), figure("revenue", 120))
        m_then = calculations.operating_margin(figure("operating_income", 20, end="2023-09-30"), figure("revenue", 100, end="2023-09-30"))
        self.assertEqual((m_now.status, m_now.value), ("ok", Decimal(25)))
        self.assertEqual(calculations.operating_margin(figure("net_income", 30), figure("revenue", 120)).status, "incompatible")
        self.assertEqual(calculations.operating_margin(figure("operating_income", 30), figure("revenue", 120, end="2023-09-30")).status, "incompatible")
        change = calculations.point_change(m_now, m_then)
        self.assertEqual((change.status, change.value, change.unit), ("ok", Decimal(5), "percentage points"))
        self.assertEqual(calculations.cash_conversion(figure("operating_cash_flow", 10), figure("net_income", -3)).status, "not_applicable")
        self.assertEqual(calculations.cfo_minus_capex(figure("operating_cash_flow", 10), figure("capex", 4)).value, Decimal(6))

    def test_recorded_lineage_cycles_and_staleness(self):
        store = Store(self.base / "ws")
        service = ResearchService(store, clock=lambda: NOW)
        sec = store.upsert_security("NVDA", "NVIDIA Corporation", cik="1045810")
        service.ingest(sec["id"], RELEASE, "q3fy25pr.htm", URL, sec_headers=HEADERS, retrieved_at="2026-10-22T14:40:11Z")
        policy = AsOfPolicy.parse("2024-11-21T00:00:00Z", "public")
        figures = {(f.metric, f.basis, f.period.fiscal_label): f for f in financials.resolve(FinancialRepository(store).observations(sec["id"], None, policy), policy)}
        result = calculations.growth(figures[("revenue", "GAAP", "Q3 FY25")], figures[("revenue", "GAAP", "Q3 FY24")])
        self.assertEqual(result.status, "ok")
        self.assertEqual(round(result.value, 2), Decimal("93.61"))
        with store._connection() as db:
            cid = calculations.record(db, result, "security", sec["id"], policy, NOW)
            self.assertEqual(calculations.record(db, result, "security", sec["id"], policy, NOW), cid)
            tree = calculations.lineage(db, cid)
            self.assertEqual({i["node"]["raw_value"] for i in tree["inputs"]}, {"35082", "18120"})
            self.assertEqual({i["role"] for i in tree["inputs"]}, {"current", "prior"})
            self.assertEqual(tree["policy"], policy.as_dict())
            self.assertEqual(tree["stale"], [])
        with store._connection() as db:
            fake = calculations.CalculationResult("echo", "v1", "ok", Decimal(1), "percent", (("x", "calculation", "calc_missing"),), (), ())
            with self.assertRaisesRegex(ValueError, "not recorded"):
                calculations.record(db, fake, "security", sec["id"], policy, NOW)
            # A calculation that consumed `cid` cannot become an input of `cid`.
            child = calculations.CalculationResult("echo", "v1", "ok", Decimal(1), "percent", (("x", "calculation", cid),), (), ())
            child_id = calculations.record(db, child, "security", sec["id"], policy, NOW)
            # Content addressing cannot create a loop; simulate a corrupted database (inside this test transaction only) to prove the guard.
            db.execute("INSERT INTO calculation_inputs VALUES (?,?,?,?)", (cid, "loop", "calculation", child_id))
            with self.assertRaises(calculations.CycleError):
                calculations.record(db, calculations.CalculationResult("echo", "v2", "ok", Decimal(1), "percent", (("x", "calculation", cid),), (), ()), "security", sec["id"], policy, NOW)
            db.rollback()
        with mock.patch.object(earnings, "PARSER_VERSION", "KOD-EARNINGS-PARSER-next"):
            service.index_documents()
        with store._connection() as db:
            self.assertTrue(any("newer interpretation" in r for r in calculations.stale_reasons(db, cid)))
            self.assertEqual(db.execute("SELECT value FROM calculations WHERE id=?", (cid,)).fetchone()[0], calculations._decimal_string(result.value))


if __name__ == "__main__":
    unittest.main()
