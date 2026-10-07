-- Migration 3. Applied once, after 002. Never edited after release.
--
-- 1. Evidence objects: archived bytes and their provenance, cited by facts.
-- 2. External (RFC 3161) timestamp tokens per anchor.
-- 3. Detector evaluations may only be written in the same moment as the open (or scan)
--    they belong to. An evaluation added after the outcome is refused.

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,           -- SHA-256 of the archived bytes
  source_url TEXT NOT NULL,
  publisher TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  published_at TEXT NOT NULL,             -- publication time stated by the source
  published_at_basis TEXT NOT NULL,       -- where that time comes from
  retrieved_at TEXT NOT NULL,             -- when the bytes were fetched
  archive_url TEXT,                       -- independent archive capture, if any
  archived_at TEXT,                       -- that capture's time
  grade TEXT NOT NULL CHECK (grade IN ('A', 'B', 'C', 'D')),
  media_type TEXT NOT NULL,
  bytes INTEGER NOT NULL,
  stored_path TEXT NOT NULL,              -- registry path of the archived bytes
  metadata_path TEXT NOT NULL,            -- registry path of the frozen metadata
  evidence_sha TEXT NOT NULL,             -- SHA-256 of the frozen metadata object
  git_commit TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence
BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence
BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;

ALTER TABLE anchors ADD COLUMN timestamps_json TEXT;
-- NULL means the scan was hashed with the v1 recipe (evaluations not in the entry hash).
ALTER TABLE scan_runs ADD COLUMN scan_hash_version TEXT;

CREATE TRIGGER IF NOT EXISTS evals_frozen_at_open BEFORE INSERT ON detector_evaluations
WHEN NEW.recorded_at IS NOT (SELECT opened_at FROM cases WHERE case_id = NEW.case_id)
BEGIN SELECT RAISE(ABORT, 'detector evaluations are frozen at open; a later evaluation is refused'); END;

CREATE TRIGGER IF NOT EXISTS scan_evals_frozen_at_scan BEFORE INSERT ON scan_evaluations
WHEN NEW.recorded_at IS NOT (SELECT recorded_at FROM scan_entries WHERE entry_id = NEW.entry_id)
BEGIN SELECT RAISE(ABORT, 'scan evaluations are frozen at scan time; a later evaluation is refused'); END;
