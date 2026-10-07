"""Append-only SQLite ledger. Updates and deletes are aborted by triggers."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .hashing import sha256_obj, sha256_text, utc_now

SCHEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
DOCTRINE_PATH = ROOT / "doctrine" / "KOD_DOCTRINE_v0.md"
DOCTRINE_VERSION = "KOD-DOCTRINE-v0"


class LedgerError(RuntimeError):
    pass


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        # MEMORY journal avoids a sandbox filesystem failure while creating triggers.
        # Committed rows still persist in the database file.
        self.conn.execute("PRAGMA journal_mode=MEMORY")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self._migrate()
        self.adopt_doctrine()

    def _migrate(self) -> None:
        self.conn.executescript(SCHEMA)
        digest = sha256_text(SCHEMA)
        row = self.conn.execute(
            "SELECT version FROM schema_migrations WHERE version = 1"
        ).fetchone()
        if row is None:
            self.conn.execute(
                "INSERT INTO schema_migrations(version, sha256, applied_at) VALUES (1, ?, ?)",
                (digest, utc_now()),
            )
            self.conn.commit()

    def adopt_doctrine(self) -> str:
        body = DOCTRINE_PATH.read_text(encoding="utf-8")
        digest = sha256_text(body)
        existing = self.conn.execute(
            "SELECT doctrine_sha FROM doctrine_versions WHERE doctrine_sha = ?",
            (digest,),
        ).fetchone()
        if existing is None:
            self.conn.execute(
                "INSERT INTO doctrine_versions(doctrine_sha, version, body, adopted_at) VALUES (?, ?, ?, ?)",
                (digest, DOCTRINE_VERSION, body, utc_now()),
            )
            self.conn.commit()
        return digest

    @property
    def doctrine_sha(self) -> str:
        return self.adopt_doctrine()

    def open_case(self, card: dict) -> str:
        self._require_disposition(card)
        if card["disposition"] == "INVESTIGATE" and not card.get("critic"):
            raise LedgerError("INVESTIGATE refused: critic loss path is required")
        if card["disposition"] == "INVESTIGATE":
            self._require_critic(card["critic"])
        horizons = card.get("information_sets") or {}
        for horizon in ("T-30D", "T-72H", "T-24H"):
            if horizon not in horizons:
                raise LedgerError(f"missing information set {horizon}")
        doctrine_sha = self.doctrine_sha
        frozen = {
            "symbol": card["symbol"].upper(),
            "venue": card["venue"],
            "call_type": card["call_type"],
            "decision_cutoff": card["decision_cutoff"],
            "story_hypothesis": card["story_hypothesis"],
            "disposition": card["disposition"],
            "universe_id": card["universe_id"],
            "reconstruction_status": card["reconstruction_status"],
            "doctrine_sha": doctrine_sha,
            "information_sets": {
                h: horizons[h] for h in ("T-30D", "T-72H", "T-24H")
            },
        }
        card_sha = sha256_obj(frozen)
        case_id = card["case_id"]
        now = utc_now()
        try:
            self.conn.execute(
                """
                INSERT INTO cases(
                  case_id, opened_at, symbol, venue, call_type, doctrine_sha,
                  decision_cutoff, story_hypothesis, disposition, card_sha,
                  universe_id, reconstruction_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    now,
                    frozen["symbol"],
                    card["venue"],
                    card["call_type"],
                    doctrine_sha,
                    card["decision_cutoff"],
                    card["story_hypothesis"],
                    card["disposition"],
                    card_sha,
                    card["universe_id"],
                    card["reconstruction_status"],
                    card.get("notes", ""),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise LedgerError(f"case {case_id} already exists; refusing rewrite") from exc
        for horizon, payload in frozen["information_sets"].items():
            self.conn.execute(
                """
                INSERT INTO information_sets(set_id, case_id, horizon, cutoff, payload_json, set_sha, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{case_id}:{horizon}",
                    case_id,
                    horizon,
                    payload.get("cutoff", ""),
                    json.dumps(payload, sort_keys=True),
                    sha256_obj(payload),
                    now,
                ),
            )
        critic = card.get("critic")
        if critic:
            self.conn.execute(
                """
                INSERT INTO critic_notes(note_id, case_id, loss_path, missing_evidence, invalidation, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{case_id}:critic",
                    case_id,
                    critic["loss_path"],
                    critic["missing_evidence"],
                    critic["invalidation"],
                    now,
                ),
            )
        self.conn.commit()
        return card_sha

    def record_evaluation(self, case_id: str, detector: str, rule_version: str, status: str, features: dict) -> None:
        self._require_case(case_id)
        self.conn.execute(
            """
            INSERT INTO detector_evaluations(eval_id, case_id, detector, rule_version, status, features_json, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{case_id}:{detector}:{rule_version}",
                case_id,
                detector,
                rule_version,
                status,
                json.dumps(features, sort_keys=True),
                utc_now(),
            ),
        )
        self.conn.commit()

    def close_case(self, case_id: str, outcome: dict) -> None:
        row = self._require_case(case_id)
        if row["call_type"] == "PROSPECTIVE" and outcome.get("card_sha") not in (None, row["card_sha"]):
            raise LedgerError("prospective close refused: card hash does not match the frozen open")
        existing = self.conn.execute(
            "SELECT outcome_id FROM outcomes WHERE case_id = ?", (case_id,)
        ).fetchone()
        if existing:
            raise LedgerError("outcome already recorded; refusing rewrite")
        self.conn.execute(
            """
            INSERT INTO outcomes(
              outcome_id, case_id, closed_at, window_label, window_return_pct,
              outcome_label, source, card_sha_at_open, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{case_id}:outcome",
                case_id,
                utc_now(),
                outcome["window_label"],
                outcome.get("window_return_pct"),
                outcome["outcome_label"],
                outcome["source"],
                row["card_sha"],
                outcome.get("notes", ""),
            ),
        )
        self.conn.commit()

    def assert_immutable(self) -> None:
        for table in (
            "cases",
            "information_sets",
            "detector_evaluations",
            "critic_notes",
            "outcomes",
            "doctrine_versions",
        ):
            try:
                self.conn.execute(f"DELETE FROM {table}")
            except sqlite3.IntegrityError:
                continue
            except sqlite3.DatabaseError as exc:
                if "append-only" not in str(exc):
                    raise
                continue
            raise LedgerError(f"delete was allowed on {table}")

    def rows(self, sql: str, params=()):
        return list(self.conn.execute(sql, params))

    def _require_case(self, case_id: str):
        row = self.conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            raise LedgerError(f"unknown case {case_id}")
        return row

    @staticmethod
    def _require_disposition(card: dict) -> None:
        if card["disposition"] not in {"INVESTIGATE", "WATCH", "REJECT"}:
            raise LedgerError("illegal disposition; ENTRY_ELIGIBLE is reserved and not granted")
        if card["call_type"] not in {"PROSPECTIVE", "RETROSPECTIVE", "SIMULATED"}:
            raise LedgerError("illegal call_type")

    @staticmethod
    def _require_critic(critic: dict) -> None:
        for key in ("loss_path", "missing_evidence", "invalidation"):
            if not str(critic.get(key, "")).strip():
                raise LedgerError(f"critic note missing {key}")
