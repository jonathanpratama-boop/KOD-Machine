-- Migration 4. Applied once, after 003. Never edited after release.
--
-- 1. Evidence objects v2 (KOD-EVIDENCE-v2): existence and content verification recorded
--    separately, publication time never inferred from retrieval time, mechanical grade
--    ceiling. The v1 `evidence` table stays for records made before this migration.
-- 2. Remote timestamp receipts: a server-side time from GitHub for the exact anchor commit.
-- 3. Detector versions: each rule version is bound to the SHA-256 of the detector source,
--    so changing detector code without a new rule version is refused.
-- 4. Card integrity level, detector code hash and frozen rule version per case (KOD-CARD-v3).

CREATE TABLE IF NOT EXISTS evidence_objects (
  evidence_id TEXT PRIMARY KEY,           -- SHA-256 of the frozen object (object_json)
  evidence_hash_version TEXT NOT NULL,
  object_json TEXT NOT NULL,              -- canonical frozen object; columns below are copies
  source_url TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('PRIMARY', 'SECONDARY', 'RETROSPECTIVE')),
  publisher TEXT NOT NULL,
  document_type TEXT NOT NULL,
  event_time TEXT,
  publication_time TEXT,                  -- NULL when unknown; never copied from retrieval_time
  retrieval_time TEXT NOT NULL,
  archive_time TEXT,
  as_of_cutoff TEXT NOT NULL,
  content_sha256 TEXT,
  archived_copy TEXT,
  evidence_grade TEXT NOT NULL CHECK (evidence_grade IN ('A', 'B', 'C', 'D')),
  grade_ceiling TEXT NOT NULL CHECK (grade_ceiling IN ('A', 'B', 'C', 'D')),
  existence_verified INTEGER NOT NULL CHECK (existence_verified IN (0, 1)),
  content_verified INTEGER NOT NULL CHECK (content_verified IN (0, 1)),
  metadata_path TEXT NOT NULL,
  timestamps_json TEXT NOT NULL DEFAULT '[]',
  git_commit TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  CHECK (evidence_grade >= grade_ceiling)  -- 'A' < 'B': a declared grade may not beat its ceiling
);

CREATE TRIGGER IF NOT EXISTS evidence_objects_no_update BEFORE UPDATE ON evidence_objects
BEGIN SELECT RAISE(ABORT, 'evidence objects are append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_objects_no_delete BEFORE DELETE ON evidence_objects
BEGIN SELECT RAISE(ABORT, 'evidence objects are append-only'); END;

CREATE TABLE IF NOT EXISTS remote_timestamp_receipts (
  receipt_id TEXT PRIMARY KEY,
  provider TEXT NOT NULL CHECK (provider IN ('GITHUB_ACTIONS')),
  record_kind TEXT NOT NULL CHECK (record_kind IN ('CASE', 'SCAN')),
  record_id TEXT NOT NULL,
  anchor_sha TEXT NOT NULL,
  repository TEXT NOT NULL,
  remote_event_id TEXT NOT NULL,          -- workflow run id
  remote_head_sha TEXT NOT NULL,
  remote_event TEXT NOT NULL,             -- 'push'
  remote_created_at TEXT NOT NULL,        -- GitHub's server-side created_at
  remote_url TEXT NOT NULL,
  response_sha256 TEXT NOT NULL,          -- SHA-256 of the API response it was read from
  fetched_at TEXT NOT NULL,
  verification_status TEXT NOT NULL CHECK (verification_status IN ('FETCHED_EXACT_MATCH'))
);

CREATE TRIGGER IF NOT EXISTS receipts_no_update BEFORE UPDATE ON remote_timestamp_receipts
BEGIN SELECT RAISE(ABORT, 'remote timestamp receipts are append-only'); END;
CREATE TRIGGER IF NOT EXISTS receipts_no_delete BEFORE DELETE ON remote_timestamp_receipts
BEGIN SELECT RAISE(ABORT, 'remote timestamp receipts are append-only'); END;

CREATE TABLE IF NOT EXISTS detector_versions (
  rule_version TEXT PRIMARY KEY,
  code_sha256 TEXT NOT NULL,
  source_path TEXT NOT NULL,
  adopted_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS detector_versions_no_update BEFORE UPDATE ON detector_versions
BEGIN SELECT RAISE(ABORT, 'detector versions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS detector_versions_no_delete BEFORE DELETE ON detector_versions
BEGIN SELECT RAISE(ABORT, 'detector versions are append-only'); END;

ALTER TABLE cases ADD COLUMN integrity_level TEXT;       -- NULL before v3
ALTER TABLE cases ADD COLUMN detector_code_sha256 TEXT;  -- NULL before v3
ALTER TABLE cases ADD COLUMN detector_rule_version TEXT; -- NULL before v3
ALTER TABLE scan_runs ADD COLUMN detector_code_sha256 TEXT;
