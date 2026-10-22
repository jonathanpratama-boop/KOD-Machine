"""SQLite index, immutable evidence objects and local recovery.

This database is independent of the historical KOD registry and paper ledger.
Every method opens its own connection. Immutable objects are addressed by SHA-256.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import threading

from ..hashing import utc_now
from .domain import APP_VERSION, Security, SourceEnvelope, canonical, identity, publication, source_url, timestamp


SCHEMA_VERSION = 1
DB_NAME = "workstation.sqlite3"
DDL = """
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


class Store:
    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()
        self._validate_root(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.objects = self.root / "objects"
        if self.objects.is_symlink():
            raise ValueError("objects directory must not be a symlink")
        self.objects.mkdir(exist_ok=True)
        self.path = self.root / DB_NAME
        if self.path.is_symlink():
            raise ValueError("database must not be a symlink")
        self._lock = threading.RLock()
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            # Recheck the schema while holding the writer lock: concurrent first
            # launches must not both observe version zero and race CREATE TABLE.
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise ValueError("database schema is newer than this application")
            if version == 0:
                for statement in DDL.split(";"):
                    if statement.strip():
                        db.execute(statement)
                db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    @staticmethod
    def _validate_root(path):
        """Refuse accidental writes into the existing lab or source tree."""
        package = Path(__file__).resolve().parents[2]
        repository = package.parent
        protected = [package / name for name in ("var", "registry", "research", "tsa", "kod", "tests", "examples")]
        protected.append(repository / "idx-signals")
        parts = path.parts
        legacy_shape = any(part == "idx-signals" or
                           (part == "kod-machine" and i + 1 < len(parts) and parts[i + 1] in
                            {"var", "registry", "research", "tsa", "kod", "tests", "examples"})
                           for i, part in enumerate(parts))
        if legacy_shape or path in (package, repository) or any(path == p or p in path.parents for p in protected):
            raise ValueError("workstation data/backup/restore must stay outside protected lab and source paths")

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _row(row):
        if row is None:
            raise ValueError("record was not found")
        data = dict(row)
        for field in ("metadata", "result"):
            if field in data:
                data[field] = json.loads(data[field])
        return data

    def upsert_security(self, ticker, name, cik=None, venue="XNAS", currency="USD", association="user_asserted"):
        sec = Security(ticker, name, cik, venue, currency, association).validated()
        with self._connection() as db:
            previous = db.execute("SELECT * FROM securities WHERE ticker=? AND venue=?", (sec.ticker, sec.venue)).fetchone()
            if previous and previous["cik"] and sec.cik and previous["cik"] != sec.cik:
                raise ValueError("known CIK mismatch for this listing")
            sid = previous["id"] if previous else identity("sec", sec.ticker, sec.venue)
            assoc = sec.association
            if previous and previous["association"] == "verified_from_filing_metadata":
                assoc = previous["association"]
            db.execute("""INSERT INTO securities VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name,cik=COALESCE(excluded.cik,securities.cik),
                currency=excluded.currency,association=excluded.association,watched=1""",
                (sid, sec.ticker, sec.name, sec.cik, sec.venue, sec.currency, assoc, 1, utc_now()))
        return self.get_security(sid)

    def securities(self):
        with self._connection() as db:
            return [self._row(r) for r in db.execute("SELECT * FROM securities WHERE watched=1 ORDER BY ticker,venue")]

    def get_security(self, security_id):
        with self._connection() as db:
            return self._row(db.execute("SELECT * FROM securities WHERE id=?", (security_id,)).fetchone())

    def remove_watchlist(self, security_id):
        self.get_security(security_id)
        with self._connection() as db:
            db.execute("UPDATE securities SET watched=0 WHERE id=?", (security_id,))

    def _object_path(self, sha):
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("invalid evidence hash")
        path = self.objects / sha[:2] / sha
        if path.parent.is_symlink() or path.is_symlink():
            raise ValueError("evidence paths must not be symlinks")
        return path

    def _save_object(self, raw):
        sha = hashlib.sha256(raw).hexdigest()
        target = self._object_path(sha)
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError("evidence object failed hash integrity check")
            return sha
        descriptor, tmp = tempfile.mkstemp(prefix=".object-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return sha

    def save_document(self, security_id, raw: bytes, filename, source_url, published_at=None,
                      published_basis="unknown", observed_at=None, role="current", association="user_asserted",
                      provider="local", external_id=None, extraction_status="pending", metadata=None):
        self.get_security(security_id)
        published, pub_date = publication(published_at)
        observed = timestamp(observed_at or utc_now())
        info = dict(metadata or {})
        if pub_date:
            info["publication_date"], info["publication_precision"] = pub_date, "date"
        else:
            info.setdefault("publication_precision", "second" if published else "unknown")
        info.setdefault("parser_version", APP_VERSION)
        envelope = SourceEnvelope(security_id, raw, str(filename), source_url, published, str(published_basis), observed, role, association, provider, external_id)
        envelope.validate()
        safe_name = Path(str(filename).replace("\\", "/")).name[:200] or "document.htm"
        sha = self._save_object(raw)
        doc_id = identity("doc", security_id, provider, external_id or source_url, sha, role, published,
                          str(published_basis), info.get("publication_date"), association, info.get("parser_sha256"))
        with self._connection() as db:
            db.execute("INSERT OR IGNORE INTO objects VALUES (?,?)", (sha, len(raw)))
            db.execute("INSERT OR IGNORE INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (doc_id, security_id, sha, safe_name, source_url, published, str(published_basis), observed,
                        role, association, provider, external_id, extraction_status, canonical(info), utc_now()))
            db.execute("INSERT INTO observations(document_id,observed_at,recorded_at) VALUES (?,?,?)", (doc_id, observed, utc_now()))
        return self.document(doc_id)

    def documents(self, security_id=None):
        with self._connection() as db:
            where, args = ("WHERE d.security_id=?", (security_id,)) if security_id else ("", ())
            rows = db.execute(f"SELECT d.*,o.bytes FROM documents d JOIN objects o USING(sha256) {where} ORDER BY d.observed_at DESC,d.id", args)
            return [self._row(r) for r in rows]

    def document(self, document_id):
        with self._connection() as db:
            row = db.execute("SELECT d.*,o.bytes FROM documents d JOIN objects o USING(sha256) WHERE d.id=?", (document_id,)).fetchone()
            result = self._row(row)
            result["observation_count"] = db.execute("SELECT COUNT(*) FROM observations WHERE document_id=?", (document_id,)).fetchone()[0]
            result["last_observed_at"] = db.execute("SELECT MAX(observed_at) FROM observations WHERE document_id=?", (document_id,)).fetchone()[0]
            return result

    def raw(self, document_id):
        doc = self.document(document_id)
        try:
            raw = self._object_path(doc["sha256"]).read_bytes()
        except OSError as exc:
            raise ValueError("stored evidence object is missing or unreadable") from exc
        if hashlib.sha256(raw).hexdigest() != doc["sha256"] or len(raw) != doc["bytes"]:
            raise ValueError("stored evidence failed SHA-256 integrity verification")
        return raw

    def save_event(self, security_id, external_id, form, title, source_url, published_at=None,
                   published_basis="unknown", observed_at=None, document_id=None, metadata=None):
        self.get_security(security_id)
        if document_id and self.document(document_id)["security_id"] != security_id:
            raise ValueError("event document belongs to a different security")
        # Do not confuse this method's source_url argument with the validator.
        from .domain import source_url as valid_url
        valid_url(source_url)
        published, date_only = publication(published_at)
        info = dict(metadata or {})
        if date_only:
            info["publication_date"] = date_only
        eid = identity("event", security_id, str(external_id))
        observed = timestamp(observed_at or utc_now())
        if published and observed < published:
            raise ValueError("observation must not precede publication")
        values = (eid, security_id, str(external_id), str(form), str(title)[:500], source_url, published,
                  str(published_basis), observed, document_id, canonical(info))
        with self._connection() as db:
            payload = canonical(values)
            db.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)", values)
            db.execute("INSERT OR IGNORE INTO event_revisions VALUES (?,?,?,?)", (eid, hashlib.sha256(payload.encode()).hexdigest(), payload, utc_now()))
            db.execute("UPDATE events SET form=?,title=?,source_url=?,published_at=?,published_basis=?,document_id=?,metadata=? WHERE id=?",
                       (form, str(title)[:500], source_url, published, str(published_basis), document_id, canonical(info), eid))
            return self._row(db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone())

    def events(self, security_id=None):
        with self._connection() as db:
            where, args = ("WHERE security_id=?", (security_id,)) if security_id else ("", ())
            return [self._row(r) for r in db.execute(f"SELECT * FROM events {where} ORDER BY COALESCE(published_at,observed_at) DESC,id", args)]

    def save_note(self, security_id, current_document_id, comparison_document_id, result, markdown, as_of, mode):
        self.get_security(security_id)
        for doc_id in (current_document_id, comparison_document_id):
            if doc_id and self.document(doc_id)["security_id"] != security_id:
                raise ValueError("note source belongs to a different security")
        if mode not in ("observed", "public"):
            raise ValueError("mode must be observed or public")
        cutoff = timestamp(as_of)
        body = canonical(result)
        nid = identity("note", security_id, current_document_id, comparison_document_id, body, markdown, cutoff, mode, APP_VERSION)
        with self._connection() as db:
            db.execute("INSERT OR IGNORE INTO notes VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (nid, security_id, current_document_id, comparison_document_id, body, markdown, cutoff, mode, utc_now(), APP_VERSION))
        return self.note(nid)

    def notes(self, security_id=None):
        with self._connection() as db:
            where, args = ("WHERE security_id=?", (security_id,)) if security_id else ("", ())
            return [self._row(r) for r in db.execute(f"SELECT * FROM notes {where} ORDER BY created_at DESC,id", args)]

    def note(self, note_id):
        with self._connection() as db:
            return self._row(db.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone())

    def annotate(self, note_id, thesis, invalidation, review_condition):
        self.note(note_id)
        values = [str(v).strip() for v in (thesis, invalidation, review_condition)]
        if any(len(v) > 12000 for v in values):
            raise ValueError("each annotation field must be at most 12,000 characters")
        if not any(values):
            raise ValueError("provide at least one annotation field")
        with self._connection() as db:
            cursor = db.execute("INSERT INTO annotations(note_id,thesis,invalidation,review_condition,created_at) VALUES (?,?,?,?,?)", (note_id, *values, utc_now()))
            return self._row(db.execute("SELECT * FROM annotations WHERE id=?", (cursor.lastrowid,)).fetchone())

    def annotations(self, note_id):
        self.note(note_id)
        with self._connection() as db:
            return [self._row(r) for r in db.execute("SELECT * FROM annotations WHERE note_id=? ORDER BY id DESC", (note_id,))]

    def record_job(self, provider, scope, status, message, started_at=None, finished_at=None, new_count=0):
        start = timestamp(started_at or utc_now())
        finish = timestamp(finished_at) if finished_at else (None if str(status).lower() == "running" else utc_now())
        with self._connection() as db:
            cursor = db.execute("INSERT INTO jobs(provider,scope,status,message,started_at,finished_at,new_count) VALUES (?,?,?,?,?,?,?)",
                                (str(provider), str(scope), str(status).lower(), str(message)[:2000], start, finish, int(new_count)))
            return self._row(db.execute("SELECT * FROM jobs WHERE id=?", (cursor.lastrowid,)).fetchone())

    def jobs(self):
        with self._connection() as db:
            return [self._row(r) for r in db.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 200")]

    def health(self):
        # Query the complete history: a busy source must not displace another's
        # last successful check from an arbitrary UI job-list limit.
        with self._connection() as db:
            rows = [self._row(r) for r in db.execute("SELECT * FROM jobs ORDER BY id DESC")]
        found = {}
        for row in rows:
            key = row["provider"], row["scope"]
            current = found.setdefault(key, {**row, "last_attempt": row["started_at"], "last_success": None, "last_success_at": None})
            if current["last_success"] is None and row["status"] in ("success", "ok", "completed", "checked_empty"):
                current["last_success"] = current["last_success_at"] = row["finished_at"] or row["started_at"]
        return list(found.values())

    @staticmethod
    def _new_target(target):
        target = Path(target).expanduser().absolute()
        Store._validate_root(target.resolve())
        if target.exists() or target.is_symlink():
            raise ValueError("target already exists; choose a new directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target.resolve()

    def backup(self, target: Path):
        target = self._new_target(target)
        if target == self.root or self.root in target.parents:
            raise ValueError("backup target must be outside the active data directory")
        with self._lock, tempfile.TemporaryDirectory(prefix=".kod-backup-", dir=target.parent) as staging:
            stage = Path(staging)
            destination = sqlite3.connect(stage / DB_NAME)
            try:
                with self._connection() as source:
                    source.backup(destination)
                destination.execute("PRAGMA journal_mode=DELETE")
                destination.commit()
                hashes = [r[0] for r in destination.execute("SELECT sha256 FROM objects ORDER BY sha256")]
            finally:
                destination.close()
            files = {DB_NAME: hashlib.sha256((stage / DB_NAME).read_bytes()).hexdigest()}
            for sha in hashes:
                original = self._object_path(sha)
                data = original.read_bytes()
                if hashlib.sha256(data).hexdigest() != sha:
                    raise ValueError("cannot back up corrupt source evidence")
                relative = f"objects/{sha[:2]}/{sha}"
                dst = stage / relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                files[relative] = sha
            (stage / "BACKUP.json").write_text(canonical({"schema_version": SCHEMA_VERSION, "app_version": APP_VERSION, "created_at": utc_now(), "files": files}), encoding="utf-8")
            os.replace(stage, target)
        return target

    @classmethod
    def restore(cls, backup_dir: Path, target: Path):
        source = Path(backup_dir).expanduser().resolve()
        target = cls._new_target(target)
        try:
            manifest_path = source / "BACKUP.json"
            if manifest_path.is_symlink():
                raise ValueError("backup manifest must not be a symlink")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("backup manifest is missing or invalid") from exc
        if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
            raise ValueError("backup manifest must contain a files mapping")
        files = manifest["files"]
        if manifest.get("schema_version") != SCHEMA_VERSION or DB_NAME not in files:
            raise ValueError("unsupported or incomplete backup")
        for name, sha in files.items():
            if not isinstance(name, str) or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise ValueError("invalid backup file hash")
            if name != DB_NAME and not re.fullmatch(r"objects/[0-9a-f]{2}/[0-9a-f]{64}", name):
                raise ValueError("invalid backup path")
            path = source / name
            components = [source.joinpath(*Path(name).parts[:i]) for i in range(1, len(Path(name).parts) + 1)]
            if any(p.is_symlink() for p in components) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise ValueError("backup failed SHA-256 integrity verification")
        with tempfile.TemporaryDirectory(prefix=".kod-restore-", dir=target.parent) as staging:
            stage = Path(staging)
            for name in files:
                dst = stage / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / name, dst)
            # Validate database structure and every referenced evidence object
            # before moving the restored snapshot into its final new directory.
            check = sqlite3.connect(stage / DB_NAME)
            try:
                if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("backup database integrity check failed")
                if check.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise ValueError("backup database references are invalid")
                for (sha,) in check.execute("SELECT sha256 FROM objects"):
                    name = f"objects/{sha[:2]}/{sha}"
                    if name not in files or files[name] != sha:
                        raise ValueError("backup is missing a referenced evidence object")
            finally:
                check.close()
            os.replace(stage, target)
        return cls(target)
