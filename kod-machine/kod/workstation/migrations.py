"""Ordered, transactional schema migrations for the workstation database.

Each migration runs in one SQLite transaction together with its PRAGMA user_version change: a failure rolls back and leaves the database at the previous
version, untouched. Before a database that already holds data is migrated, a consistent copy is written to <data>/migration-backups/ (never deleted by this
code). A database newer than this application, or one whose recorded migrations differ from this code, is refused; it is never rebuilt or emptied.

Migration 1 is the v1 workstation schema exactly as released (KOD-WORKSTATION-v1). Later migrations only add tables, indexes and triggers.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3
from typing import Callable

from ..hashing import utc_now
from . import identity as identity_model

# The v1 schema, verbatim. Its SHA-256 is recorded when a v1 database is upgraded.
V1_DDL = """
CREATE TABLE securities (
 id TEXT PRIMARY KEY, ticker TEXT NOT NULL, name TEXT NOT NULL, cik TEXT,
 venue TEXT NOT NULL, currency TEXT NOT NULL, association TEXT NOT NULL,
 watched INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
 UNIQUE(ticker, venue)
);
CREATE TABLE objects (sha256 TEXT PRIMARY KEY, bytes INTEGER NOT NULL);
CREATE TABLE documents (
 id TEXT PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id),
 sha256 TEXT NOT NULL REFERENCES objects(sha256), filename TEXT NOT NULL,
 source_url TEXT NOT NULL, published_at TEXT, published_basis TEXT NOT NULL,
 observed_at TEXT NOT NULL, role TEXT NOT NULL, association TEXT NOT NULL,
 provider TEXT NOT NULL, external_id TEXT, extraction_status TEXT NOT NULL,
 metadata TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX documents_security ON documents(security_id, observed_at DESC);
CREATE TABLE observations (
 id INTEGER PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
 observed_at TEXT NOT NULL, recorded_at TEXT NOT NULL
);
CREATE TABLE events (
 id TEXT PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id),
 external_id TEXT NOT NULL, form TEXT NOT NULL, title TEXT NOT NULL,
 source_url TEXT NOT NULL, published_at TEXT, published_basis TEXT NOT NULL,
 observed_at TEXT NOT NULL, document_id TEXT REFERENCES documents(id), metadata TEXT NOT NULL,
 UNIQUE(security_id, external_id)
);
CREATE TABLE event_revisions (
 event_id TEXT NOT NULL REFERENCES events(id), content_sha256 TEXT NOT NULL,
 payload TEXT NOT NULL, recorded_at TEXT NOT NULL, PRIMARY KEY(event_id,content_sha256)
);
CREATE INDEX events_security ON events(security_id, published_at DESC);
CREATE TABLE notes (
 id TEXT PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id),
 current_document_id TEXT NOT NULL REFERENCES documents(id),
 comparison_document_id TEXT REFERENCES documents(id), result TEXT NOT NULL,
 markdown TEXT NOT NULL, as_of TEXT NOT NULL, mode TEXT NOT NULL,
 created_at TEXT NOT NULL, app_version TEXT NOT NULL
);
CREATE INDEX notes_security ON notes(security_id, created_at DESC);
CREATE TABLE annotations (
 id INTEGER PRIMARY KEY, note_id TEXT NOT NULL REFERENCES notes(id), thesis TEXT NOT NULL,
 invalidation TEXT NOT NULL, review_condition TEXT NOT NULL, created_at TEXT NOT NULL,
 author TEXT NOT NULL DEFAULT 'local_user'
);
CREATE TABLE jobs (
 id INTEGER PRIMARY KEY, provider TEXT NOT NULL, scope TEXT NOT NULL, status TEXT NOT NULL,
 message TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT, new_count INTEGER NOT NULL
);
CREATE INDEX jobs_provider_scope ON jobs(provider,scope,id DESC);
"""

V2_DDL = """
CREATE TABLE schema_migrations (
 version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL,
 applied_at TEXT NOT NULL, app_version TEXT NOT NULL
);
CREATE TABLE issuers (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, cik TEXT UNIQUE,
 association TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE instruments (
 id TEXT PRIMARY KEY, issuer_id TEXT NOT NULL REFERENCES issuers(id),
 class_name TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE listings (
 id TEXT PRIMARY KEY, instrument_id TEXT NOT NULL REFERENCES instruments(id),
 venue TEXT NOT NULL, trading_currency TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE identifier_aliases (
 id INTEGER PRIMARY KEY, subject_kind TEXT NOT NULL CHECK(subject_kind IN ('issuer','instrument','listing')),
 subject_id TEXT NOT NULL, id_type TEXT NOT NULL, value TEXT NOT NULL,
 valid_from TEXT, valid_to TEXT, observed_at TEXT NOT NULL, evidence TEXT NOT NULL, recorded_at TEXT NOT NULL,
 UNIQUE(subject_kind, subject_id, id_type, value, observed_at)
);
CREATE INDEX identifier_aliases_value ON identifier_aliases(id_type, value);
CREATE TABLE security_identity (
 id INTEGER PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id),
 listing_id TEXT NOT NULL REFERENCES listings(id), instrument_id TEXT NOT NULL REFERENCES instruments(id),
 issuer_id TEXT NOT NULL REFERENCES issuers(id), basis TEXT NOT NULL, recorded_at TEXT NOT NULL
);
CREATE INDEX security_identity_security ON security_identity(security_id, id DESC);
CREATE TABLE metric_definitions (
 metric TEXT NOT NULL, version INTEGER NOT NULL, label TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('flow','instant','per_share','ratio','count')),
 additive INTEGER NOT NULL CHECK(additive IN (0,1)), unit_family TEXT NOT NULL, description TEXT NOT NULL,
 PRIMARY KEY(metric, version)
);
CREATE TABLE periods (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, start_date TEXT, end_date TEXT, instant_date TEXT,
 fiscal_label TEXT, duration_days INTEGER
);
CREATE TABLE financial_observations (
 id TEXT PRIMARY KEY, provider TEXT NOT NULL,
 issuer_id TEXT REFERENCES issuers(id), security_id TEXT REFERENCES securities(id),
 concept TEXT NOT NULL, taxonomy TEXT NOT NULL, metric TEXT, metric_version INTEGER,
 raw_value TEXT NOT NULL, value TEXT NOT NULL, unit TEXT NOT NULL, scale INTEGER,
 currency TEXT, currency_basis TEXT, period_id TEXT NOT NULL REFERENCES periods(id),
 basis TEXT NOT NULL, context TEXT NOT NULL, dimensions_available INTEGER NOT NULL,
 accession TEXT, form TEXT, filed TEXT, amendment INTEGER,
 source_document_id TEXT REFERENCES documents(id), source_sha256 TEXT NOT NULL, evidence TEXT NOT NULL,
 published_at TEXT, publication_date TEXT, publication_precision TEXT NOT NULL, publication_basis TEXT NOT NULL,
 observed_at TEXT NOT NULL, recorded_at TEXT NOT NULL, parser_version TEXT NOT NULL, mapping_version TEXT NOT NULL,
 flags TEXT NOT NULL,
 FOREIGN KEY(metric, metric_version) REFERENCES metric_definitions(metric, version)
);
CREATE INDEX financial_observations_issuer ON financial_observations(issuer_id, metric, period_id);
CREATE INDEX financial_observations_security ON financial_observations(security_id, metric, period_id);
CREATE INDEX financial_observations_document ON financial_observations(source_document_id);
CREATE TRIGGER financial_observations_no_update BEFORE UPDATE ON financial_observations
BEGIN SELECT RAISE(ABORT, 'financial observations are immutable; record a new interpretation instead'); END;
CREATE TRIGGER financial_observations_no_delete BEFORE DELETE ON financial_observations
BEGIN SELECT RAISE(ABORT, 'financial observations are immutable; record a new interpretation instead'); END;
CREATE TABLE calculations (
 id TEXT PRIMARY KEY, formula TEXT NOT NULL, formula_version TEXT NOT NULL,
 subject_kind TEXT NOT NULL, subject_id TEXT NOT NULL, policy TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('ok','missing','conflicted','incompatible','not_applicable','invalid')),
 value TEXT, unit TEXT NOT NULL, reasons TEXT NOT NULL, evidence TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX calculations_subject ON calculations(subject_kind, subject_id, formula);
CREATE TABLE calculation_inputs (
 calculation_id TEXT NOT NULL REFERENCES calculations(id), role TEXT NOT NULL,
 input_kind TEXT NOT NULL CHECK(input_kind IN ('observation','calculation','assumption')), input_id TEXT NOT NULL,
 PRIMARY KEY(calculation_id, role, input_kind, input_id)
);
CREATE INDEX calculation_inputs_input ON calculation_inputs(input_kind, input_id);
CREATE TRIGGER calculations_no_update BEFORE UPDATE ON calculations
BEGIN SELECT RAISE(ABORT, 'calculations are immutable; record a new version instead'); END;
CREATE TABLE calculation_supersessions (
 old_id TEXT NOT NULL REFERENCES calculations(id), new_id TEXT NOT NULL REFERENCES calculations(id),
 reason TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(old_id, new_id)
);
CREATE TABLE analyst_records (
 id TEXT PRIMARY KEY, subject_kind TEXT NOT NULL, subject_id TEXT NOT NULL, record_type TEXT NOT NULL,
 value TEXT NOT NULL, rationale TEXT NOT NULL, author TEXT NOT NULL, created_at TEXT NOT NULL,
 supersedes TEXT REFERENCES analyst_records(id)
);
CREATE INDEX analyst_records_subject ON analyst_records(subject_kind, subject_id, record_type, created_at DESC);
"""


V3_DDL = """
CREATE TABLE assumption_sets (
 id TEXT PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id), model TEXT NOT NULL,
 scenario TEXT NOT NULL CHECK(scenario IN ('bear','base','bull')), name TEXT NOT NULL,
 created_at TEXT NOT NULL, author TEXT NOT NULL, UNIQUE(security_id, model, scenario, name)
);
CREATE TABLE assumption_versions (
 id TEXT PRIMARY KEY, assumption_id TEXT NOT NULL REFERENCES assumption_sets(id), version INTEGER NOT NULL CHECK(version >= 1),
 assumptions TEXT NOT NULL, rationale TEXT NOT NULL, author TEXT NOT NULL, created_at TEXT NOT NULL,
 supersedes TEXT REFERENCES assumption_versions(id), UNIQUE(assumption_id, version)
);
CREATE INDEX assumption_versions_set ON assumption_versions(assumption_id, version DESC);
CREATE TRIGGER assumption_versions_no_update BEFORE UPDATE ON assumption_versions
BEGIN SELECT RAISE(ABORT, 'assumption versions are immutable; save a new version'); END;
CREATE TRIGGER assumption_versions_no_delete BEFORE DELETE ON assumption_versions
BEGIN SELECT RAISE(ABORT, 'assumption versions are immutable; save a new version'); END;
CREATE TABLE price_imports (
 id TEXT PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id), document_id TEXT REFERENCES documents(id),
 source_kind TEXT NOT NULL CHECK(source_kind IN ('manual','csv')), meta TEXT NOT NULL, coverage TEXT NOT NULL,
 rows INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE price_observations (
 id TEXT PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id), observed_on TEXT NOT NULL,
 session TEXT NOT NULL, timezone TEXT NOT NULL, currency TEXT NOT NULL,
 open TEXT, high TEXT, low TEXT, close TEXT NOT NULL, volume TEXT,
 adjustment TEXT NOT NULL CHECK(adjustment IN ('raw','split_adjusted','total_return')), source TEXT NOT NULL,
 source_kind TEXT NOT NULL CHECK(source_kind IN ('manual','csv')), feed_coverage TEXT NOT NULL,
 published_at TEXT NOT NULL, publication_basis TEXT NOT NULL, observed_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
 import_id TEXT REFERENCES price_imports(id)
);
CREATE INDEX price_observations_security ON price_observations(security_id, observed_on);
CREATE TRIGGER price_observations_no_update BEFORE UPDATE ON price_observations
BEGIN SELECT RAISE(ABORT, 'price observations are immutable; record a new observation instead'); END;
CREATE TRIGGER price_observations_no_delete BEFORE DELETE ON price_observations
BEGIN SELECT RAISE(ABORT, 'price observations are immutable; record a new observation instead'); END;
"""


V4_DDL = """
CREATE TABLE theses (
 id TEXT PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id), title TEXT NOT NULL,
 created_at TEXT NOT NULL, author TEXT NOT NULL, UNIQUE(security_id, title)
);
CREATE TABLE thesis_versions (
 id TEXT PRIMARY KEY, thesis_id TEXT NOT NULL REFERENCES theses(id), version INTEGER NOT NULL CHECK(version >= 1),
 statement TEXT NOT NULL, conditions TEXT NOT NULL, rationale TEXT NOT NULL, author TEXT NOT NULL, created_at TEXT NOT NULL,
 supersedes TEXT REFERENCES thesis_versions(id), UNIQUE(thesis_id, version)
);
CREATE TRIGGER thesis_versions_no_update BEFORE UPDATE ON thesis_versions
BEGIN SELECT RAISE(ABORT, 'thesis versions are immutable; save a new version'); END;
CREATE TRIGGER thesis_versions_no_delete BEFORE DELETE ON thesis_versions
BEGIN SELECT RAISE(ABORT, 'thesis versions are immutable; save a new version'); END;
CREATE TABLE thesis_reviews (
 id TEXT PRIMARY KEY, thesis_version_id TEXT NOT NULL REFERENCES thesis_versions(id), condition_id TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('triggered','not_triggered','unresolved')), policy TEXT NOT NULL, view TEXT NOT NULL,
 trace TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX thesis_reviews_version ON thesis_reviews(thesis_version_id, created_at DESC);
CREATE TRIGGER thesis_reviews_no_update BEFORE UPDATE ON thesis_reviews
BEGIN SELECT RAISE(ABORT, 'recorded reviews are immutable'); END;
CREATE TABLE decision_packets (
 id TEXT PRIMARY KEY, security_id TEXT NOT NULL REFERENCES securities(id), question TEXT NOT NULL, policy TEXT NOT NULL, view TEXT NOT NULL,
 thesis_version_id TEXT REFERENCES thesis_versions(id), choice TEXT NOT NULL, rationale TEXT NOT NULL, review_date TEXT, review_condition TEXT,
 resolution_rule TEXT, packet TEXT NOT NULL, packet_sha256 TEXT NOT NULL, author TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX decision_packets_security ON decision_packets(security_id, created_at DESC);
CREATE TRIGGER decision_packets_no_update BEFORE UPDATE ON decision_packets
BEGIN SELECT RAISE(ABORT, 'decision packets are immutable; record a new decision'); END;
CREATE TRIGGER decision_packets_no_delete BEFORE DELETE ON decision_packets
BEGIN SELECT RAISE(ABORT, 'decision packets are immutable; record a new decision'); END;
"""


class MigrationError(RuntimeError):
    """A migration failed and was rolled back, or the database cannot be migrated by this code."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    ddl: str
    data: Callable | None = None

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.ddl.encode()).hexdigest()


def _backfill_v2(db, now):
    identity_model.backfill(db, now)
    identity_model.seed_metric_catalog(db)


V5_DDL = """
DROP TRIGGER price_observations_no_update;
ALTER TABLE price_observations ADD COLUMN seq INTEGER;
UPDATE price_observations SET seq = rowid;
CREATE TRIGGER price_observations_no_update BEFORE UPDATE ON price_observations
BEGIN SELECT RAISE(ABORT, 'price observations are immutable; record a new observation instead'); END;
CREATE UNIQUE INDEX price_observations_seq ON price_observations(seq);
"""

V6_DDL = """
CREATE TRIGGER observations_no_update BEFORE UPDATE ON observations
BEGIN SELECT RAISE(ABORT, 'source observation events are immutable'); END;
CREATE TRIGGER observations_no_delete BEFORE DELETE ON observations
BEGIN SELECT RAISE(ABORT, 'source observation events are immutable'); END;
CREATE TABLE calculation_source_documents (
 calculation_id TEXT NOT NULL REFERENCES calculations(id),
 role TEXT NOT NULL, document_id TEXT NOT NULL REFERENCES documents(id),
 sha256 TEXT NOT NULL REFERENCES objects(sha256),
 PRIMARY KEY(calculation_id,role,document_id)
);
CREATE TRIGGER calculation_source_documents_no_update BEFORE UPDATE ON calculation_source_documents
BEGIN SELECT RAISE(ABORT, 'calculation source lineage is immutable'); END;
CREATE TRIGGER calculation_source_documents_no_delete BEFORE DELETE ON calculation_source_documents
BEGIN SELECT RAISE(ABORT, 'calculation source lineage is immutable'); END;
"""

MIGRATIONS = (
    Migration(
        1,
        "v1 workstation: securities, evidence objects, documents, events, notes, annotations, jobs",
        V1_DDL,
    ),
    Migration(
        2,
        "identity, immutable financial observations, periods, metric definitions, calculation lineage, analyst records",
        V2_DDL,
        _backfill_v2,
    ),
    Migration(3, "versioned scenario assumptions and immutable dated price observations", V3_DDL),
    Migration(
        4,
        "structured thesis versions, recorded condition reviews and immutable decision packets",
        V4_DDL,
    ),
    Migration(
        5,
        "explicit revision sequence on price observations (same-second corrections ordered by recording, not by id)",
        V5_DDL,
    ),
    Migration(
        6,
        "immutable source observation events and calculation classification source lineage",
        V6_DDL,
    ),
)
LATEST = MIGRATIONS[-1].version


def statements(ddl: str):
    """Split a DDL script into complete statements (trigger bodies contain semicolons)."""
    buffer = ""
    for line in ddl.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                yield buffer.strip()
            buffer = ""
    if buffer.strip():
        raise MigrationError("incomplete SQL statement in a migration: " + buffer.strip()[:80])


def _version(db) -> int:
    return db.execute("PRAGMA user_version").fetchone()[0]


def _has_data(db) -> bool:
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return any(
        db.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()
        for t in ("securities", "documents", "notes")
        if t in tables
    )


def _check_recorded(db, migrations, version):
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "schema_migrations" not in tables:
        return
    for row in db.execute("SELECT version, checksum FROM schema_migrations ORDER BY version"):
        known = next((m for m in migrations if m.version == row[0]), None)
        if known is None or known.checksum != row[1]:
            raise MigrationError(
                f"schema migration {row[0]} recorded in this database differs from this application's; refusing to continue (the database is unchanged)"
            )


def safety_copy(path: Path, version: int, now: str) -> Path:
    """A consistent copy of the database before it is migrated, kept beside it."""
    folder = path.parent / "migration-backups"
    folder.mkdir(exist_ok=True)
    stamp = now.replace(":", "").replace("-", "")
    target = folder / f"workstation-v{version}-{stamp}.sqlite3"
    n = 1
    while target.exists():
        n += 1
        target = folder / f"workstation-v{version}-{stamp}-{n}.sqlite3"
    source, copy = sqlite3.connect(path), sqlite3.connect(target)
    try:
        source.backup(copy)
    finally:
        copy.close()
        source.close()
    return target


def ensure_schema(path: Path, app_version: str, migrations=MIGRATIONS, now=utc_now) -> dict:
    """Bring the database at `path` to the latest schema. Returns {from, to, applied, safety_copy}."""
    latest = migrations[-1].version
    db = sqlite3.connect(path, timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        start = _version(db)
        if start > latest:
            raise MigrationError(
                f"database schema v{start} is newer than this application (v{latest}); use the KOD release that created it"
            )
        _check_recorded(db, migrations, start)
        report = {"from": start, "to": start, "applied": [], "safety_copy": None}
        if start == latest:
            return report
        if start > 0 and _has_data(db):
            report["safety_copy"] = str(safety_copy(path, start, now()))
        for migration in migrations:
            if migration.version <= start:
                continue
            db.execute("BEGIN IMMEDIATE")
            try:
                current = _version(db)  # another process may have migrated meanwhile
                if current >= migration.version:
                    db.execute("COMMIT")
                    continue
                if current != migration.version - 1:
                    raise MigrationError(
                        f"database is at v{current}; migration {migration.version} needs v{migration.version - 1}"
                    )
                for statement in statements(migration.ddl):
                    db.execute(statement)
                stamp = now()
                if migration.data:
                    migration.data(db, stamp)
                if migration.version >= 2:
                    if migration.version == 2:
                        first = migrations[0]
                        db.execute(
                            "INSERT OR IGNORE INTO schema_migrations VALUES (?,?,?,?,?)",
                            (
                                first.version,
                                first.name,
                                first.checksum,
                                "recorded at upgrade to v2 (applied before migration tracking)",
                                "KOD-WORKSTATION-v1",
                            ),
                        )
                    db.execute(
                        "INSERT INTO schema_migrations VALUES (?,?,?,?,?)",
                        (migration.version, migration.name, migration.checksum, stamp, app_version),
                    )
                db.execute(f"PRAGMA user_version={int(migration.version)}")
                db.execute("COMMIT")
            except Exception as exc:
                db.execute("ROLLBACK")
                if isinstance(exc, MigrationError):
                    raise
                raise MigrationError(
                    f"migration {migration.version} ({migration.name}) failed and was rolled back; the database remains at v{_version(db)}: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            report["applied"].append(migration.version)
        report["to"] = _version(db)
        if report["to"] < latest:
            raise MigrationError(f"database stopped at v{report['to']} of v{latest}")
        return report
    finally:
        db.close()
