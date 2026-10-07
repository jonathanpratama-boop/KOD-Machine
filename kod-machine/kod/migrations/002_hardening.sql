-- Migration 2. Applied once, after schema.sql (migration 1). Never edited after release.
--
-- Adds the pre-registered outcome window and scan link to cases, the git anchor
-- receipts, and the scan log (every name a scanner evaluates, flagged or not).
-- Every new table is append-only.

ALTER TABLE cases ADD COLUMN outcome_window_start TEXT;
ALTER TABLE cases ADD COLUMN outcome_window_end TEXT;
ALTER TABLE cases ADD COLUMN scan_entry_id TEXT;
-- NULL means the card was hashed with the v0 recipe (before this migration).
ALTER TABLE cases ADD COLUMN card_hash_version TEXT;

CREATE TABLE IF NOT EXISTS anchors (
  anchor_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('CASE', 'SCAN')),
  record_id TEXT NOT NULL,
  anchored_sha TEXT NOT NULL,
  git_commit TEXT NOT NULL,
  registry_path TEXT NOT NULL,
  anchored_at TEXT NOT NULL,
  UNIQUE (kind, record_id)
);

CREATE TABLE IF NOT EXISTS scan_runs (
  scan_id TEXT PRIMARY KEY,
  scanned_at TEXT NOT NULL,
  scanner TEXT NOT NULL,
  universe_id TEXT NOT NULL,
  decision_cutoff TEXT NOT NULL,
  outcome_window_start TEXT NOT NULL,
  outcome_window_end TEXT NOT NULL,
  hit_label TEXT NOT NULL CHECK (hit_label IN ('REPRICED_UP', 'REPRICED_DOWN')),
  rule_version TEXT NOT NULL,
  n_entries INTEGER NOT NULL,
  scan_sha TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS scan_entries (
  entry_id TEXT PRIMARY KEY,
  scan_id TEXT NOT NULL REFERENCES scan_runs(scan_id),
  symbol TEXT NOT NULL,
  venue TEXT NOT NULL,
  flagged INTEGER NOT NULL CHECK (flagged IN (0, 1)),
  reconstruction_status TEXT NOT NULL,
  facts_json TEXT NOT NULL,
  entry_sha TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  UNIQUE (scan_id, symbol)
);

CREATE TABLE IF NOT EXISTS scan_evaluations (
  eval_id TEXT PRIMARY KEY,
  entry_id TEXT NOT NULL REFERENCES scan_entries(entry_id),
  detector TEXT NOT NULL,
  rule_version TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('SIGNAL', 'NO_SIGNAL', 'INSUFFICIENT_DATA', 'UNAVAILABLE')),
  features_json TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  UNIQUE (entry_id, detector, rule_version)
);

CREATE TABLE IF NOT EXISTS scan_outcomes (
  outcome_id TEXT PRIMARY KEY,
  entry_id TEXT NOT NULL UNIQUE REFERENCES scan_entries(entry_id),
  closed_at TEXT NOT NULL,
  window_return_pct REAL,
  outcome_label TEXT NOT NULL CHECK (outcome_label IN (
    'REPRICED_UP', 'REPRICED_DOWN', 'NO_REPRICE', 'UNKNOWN', 'CENSORED'
  )),
  source TEXT NOT NULL,
  scan_sha_at_scan TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT ''
);

CREATE TRIGGER IF NOT EXISTS anchors_no_update BEFORE UPDATE ON anchors
BEGIN SELECT RAISE(ABORT, 'anchors are append-only'); END;
CREATE TRIGGER IF NOT EXISTS anchors_no_delete BEFORE DELETE ON anchors
BEGIN SELECT RAISE(ABORT, 'anchors are append-only'); END;

CREATE TRIGGER IF NOT EXISTS scan_runs_no_update BEFORE UPDATE ON scan_runs
BEGIN SELECT RAISE(ABORT, 'scan_runs are append-only'); END;
CREATE TRIGGER IF NOT EXISTS scan_runs_no_delete BEFORE DELETE ON scan_runs
BEGIN SELECT RAISE(ABORT, 'scan_runs are append-only'); END;

CREATE TRIGGER IF NOT EXISTS scan_entries_no_update BEFORE UPDATE ON scan_entries
BEGIN SELECT RAISE(ABORT, 'scan_entries are append-only'); END;
CREATE TRIGGER IF NOT EXISTS scan_entries_no_delete BEFORE DELETE ON scan_entries
BEGIN SELECT RAISE(ABORT, 'scan_entries are append-only'); END;

CREATE TRIGGER IF NOT EXISTS scan_evals_no_update BEFORE UPDATE ON scan_evaluations
BEGIN SELECT RAISE(ABORT, 'scan_evaluations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS scan_evals_no_delete BEFORE DELETE ON scan_evaluations
BEGIN SELECT RAISE(ABORT, 'scan_evaluations are append-only'); END;

CREATE TRIGGER IF NOT EXISTS scan_outcomes_no_update BEFORE UPDATE ON scan_outcomes
BEGIN SELECT RAISE(ABORT, 'scan_outcomes are append-only'); END;
CREATE TRIGGER IF NOT EXISTS scan_outcomes_no_delete BEFORE DELETE ON scan_outcomes
BEGIN SELECT RAISE(ABORT, 'scan_outcomes are append-only'); END;
