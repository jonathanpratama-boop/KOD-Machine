-- KOD ledger. Applied once. Append-only enforced by triggers.
-- A later schema change is a new migration, never an edit of this file.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  sha256 TEXT NOT NULL,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doctrine_versions (
  doctrine_sha TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  body TEXT NOT NULL,
  adopted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
  case_id TEXT PRIMARY KEY,
  opened_at TEXT NOT NULL,
  symbol TEXT NOT NULL,
  venue TEXT NOT NULL,
  call_type TEXT NOT NULL CHECK (call_type IN ('PROSPECTIVE', 'RETROSPECTIVE', 'SIMULATED')),
  doctrine_sha TEXT NOT NULL REFERENCES doctrine_versions(doctrine_sha),
  decision_cutoff TEXT NOT NULL,
  story_hypothesis TEXT NOT NULL,
  disposition TEXT NOT NULL CHECK (disposition IN ('INVESTIGATE', 'WATCH', 'REJECT')),
  card_sha TEXT NOT NULL,
  universe_id TEXT NOT NULL,
  reconstruction_status TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS information_sets (
  set_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  horizon TEXT NOT NULL CHECK (horizon IN ('T-30D', 'T-72H', 'T-24H')),
  cutoff TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  set_sha TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  UNIQUE (case_id, horizon)
);

CREATE TABLE IF NOT EXISTS detector_evaluations (
  eval_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  detector TEXT NOT NULL,
  rule_version TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('SIGNAL', 'NO_SIGNAL', 'INSUFFICIENT_DATA', 'UNAVAILABLE')),
  features_json TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  UNIQUE (case_id, detector, rule_version)
);

CREATE TABLE IF NOT EXISTS critic_notes (
  note_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(case_id),
  loss_path TEXT NOT NULL,
  missing_evidence TEXT NOT NULL,
  invalidation TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outcomes (
  outcome_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL UNIQUE REFERENCES cases(case_id),
  closed_at TEXT NOT NULL,
  window_label TEXT NOT NULL,
  window_return_pct REAL,
  outcome_label TEXT NOT NULL CHECK (outcome_label IN (
    'REPRICED_UP', 'REPRICED_DOWN', 'NO_REPRICE', 'UNKNOWN', 'CENSORED'
  )),
  source TEXT NOT NULL,
  card_sha_at_open TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT ''
);

CREATE TRIGGER IF NOT EXISTS cases_no_update
BEFORE UPDATE ON cases
BEGIN
  SELECT RAISE(ABORT, 'cases are append-only');
END;

CREATE TRIGGER IF NOT EXISTS cases_no_delete
BEFORE DELETE ON cases
BEGIN
  SELECT RAISE(ABORT, 'cases are append-only');
END;

CREATE TRIGGER IF NOT EXISTS sets_no_update
BEFORE UPDATE ON information_sets
BEGIN
  SELECT RAISE(ABORT, 'information_sets are append-only');
END;

CREATE TRIGGER IF NOT EXISTS sets_no_delete
BEFORE DELETE ON information_sets
BEGIN
  SELECT RAISE(ABORT, 'information_sets are append-only');
END;

CREATE TRIGGER IF NOT EXISTS evals_no_update
BEFORE UPDATE ON detector_evaluations
BEGIN
  SELECT RAISE(ABORT, 'detector_evaluations are append-only');
END;

CREATE TRIGGER IF NOT EXISTS evals_no_delete
BEFORE DELETE ON detector_evaluations
BEGIN
  SELECT RAISE(ABORT, 'detector_evaluations are append-only');
END;

CREATE TRIGGER IF NOT EXISTS notes_no_update
BEFORE UPDATE ON critic_notes
BEGIN
  SELECT RAISE(ABORT, 'critic_notes are append-only');
END;

CREATE TRIGGER IF NOT EXISTS notes_no_delete
BEFORE DELETE ON critic_notes
BEGIN
  SELECT RAISE(ABORT, 'critic_notes are append-only');
END;

CREATE TRIGGER IF NOT EXISTS outcomes_no_update
BEFORE UPDATE ON outcomes
BEGIN
  SELECT RAISE(ABORT, 'outcomes are append-only');
END;

CREATE TRIGGER IF NOT EXISTS outcomes_no_delete
BEFORE DELETE ON outcomes
BEGIN
  SELECT RAISE(ABORT, 'outcomes are append-only');
END;

CREATE TRIGGER IF NOT EXISTS doctrine_no_update
BEFORE UPDATE ON doctrine_versions
BEGIN
  SELECT RAISE(ABORT, 'doctrine versions are append-only');
END;

CREATE TRIGGER IF NOT EXISTS doctrine_no_delete
BEFORE DELETE ON doctrine_versions
BEGIN
  SELECT RAISE(ABORT, 'doctrine versions are append-only');
END;
