"""Append-only SQLite ledger. Updates and deletes are aborted by triggers."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .anchor import AnchorError, AnchorReceipt, GitAnchor
from .detectors import RULE_VERSION, evaluate
from .hashing import fmt_ts, parse_ts, sha256_obj, sha256_text, utc_now_dt

SCHEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
MIGRATIONS_DIR = Path(__file__).with_name("migrations")
ROOT = Path(__file__).resolve().parents[1]
DOCTRINE_PATH = ROOT / "doctrine" / "KOD_DOCTRINE_v0.md"
DOCTRINE_VERSION = "KOD-DOCTRINE-v0"

HORIZONS = ("T-30D", "T-72H", "T-24H")
CARD_HASH_VERSION = "KOD-CARD-v1"
SCAN_HASH_VERSION = "KOD-SCAN-v1"
# A prospective decision cutoff must sit within this distance of the moment the card is opened.
OPEN_TOLERANCE = timedelta(hours=1)
APPEND_ONLY_TABLES = (
    "cases",
    "information_sets",
    "detector_evaluations",
    "critic_notes",
    "outcomes",
    "doctrine_versions",
    "anchors",
    "scan_runs",
    "scan_entries",
    "scan_evaluations",
    "scan_outcomes",
)
HIT_LABELS = ("REPRICED_UP", "REPRICED_DOWN")


class LedgerError(RuntimeError):
    pass


def freeze_card(case: dict, information_sets: dict, critic: dict | None, version: str | None) -> dict:
    """The exact object whose SHA-256 is the card hash. Used at open and by `verify`."""
    if version is None:  # cards opened before migration 2
        return {
            "symbol": case["symbol"].upper(),
            "venue": case["venue"],
            "call_type": case["call_type"],
            "decision_cutoff": case["decision_cutoff"],
            "story_hypothesis": case["story_hypothesis"],
            "disposition": case["disposition"],
            "universe_id": case["universe_id"],
            "reconstruction_status": case["reconstruction_status"],
            "doctrine_sha": case["doctrine_sha"],
            "information_sets": {h: information_sets[h] for h in HORIZONS},
        }
    if version != CARD_HASH_VERSION:
        raise LedgerError(f"unknown card hash version {version}")
    window = None
    if case.get("outcome_window_start") or case.get("outcome_window_end"):
        window = {"start": case.get("outcome_window_start"), "end": case.get("outcome_window_end")}
    return {
        "card_hash_version": version,
        "case_id": case["case_id"],
        "symbol": case["symbol"].upper(),
        "venue": case["venue"],
        "call_type": case["call_type"],
        "decision_cutoff": case["decision_cutoff"],
        "outcome_window": window,
        "story_hypothesis": case["story_hypothesis"],
        "disposition": case["disposition"],
        "universe_id": case["universe_id"],
        "reconstruction_status": case["reconstruction_status"],
        "doctrine_sha": case["doctrine_sha"],
        "scan_entry_id": case.get("scan_entry_id"),
        "critic": None if not critic else {
            k: critic[k] for k in ("loss_path", "missing_evidence", "invalidation")
        },
        "information_sets": {h: information_sets[h] for h in HORIZONS},
    }


def freeze_scan_entry(scan_id: str, entry: dict) -> dict:
    return {
        "scan_id": scan_id,
        "symbol": entry["symbol"].upper(),
        "venue": entry["venue"],
        "flagged": bool(entry["flagged"]),
        "reconstruction_status": entry["reconstruction_status"],
        "facts": entry["facts"],
    }


def freeze_scan(header: dict, entry_shas: dict) -> dict:
    return {
        "scan_hash_version": SCAN_HASH_VERSION,
        "scan_id": header["scan_id"],
        "scanner": header["scanner"],
        "universe_id": header["universe_id"],
        "decision_cutoff": header["decision_cutoff"],
        "outcome_window": {"start": header["outcome_window_start"], "end": header["outcome_window_end"]},
        "hit_label": header["hit_label"],
        "rule_version": header["rule_version"],
        "entries": dict(sorted(entry_shas.items())),
    }


def check_prospective_timing(now: datetime, decision_cutoff: str, window: dict | None,
                             what: str, info_cutoffs: dict | None = None) -> tuple[str, str]:
    """Rule 1. The call is frozen within an hour of its cutoff, and before the outcome can start."""
    if not window or not window.get("start") or not window.get("end"):
        raise LedgerError(f"{what} refused: outcome_window.start and outcome_window.end are required")
    try:
        cutoff = parse_ts(decision_cutoff)
        start = parse_ts(window["start"])
        end = parse_ts(window["end"])
        horizon_cutoffs = {h: parse_ts(c) for h, c in (info_cutoffs or {}).items()}
    except ValueError as exc:
        raise LedgerError(f"{what} refused: {exc}") from exc
    gap = abs(now - cutoff)
    if gap > OPEN_TOLERANCE:
        raise LedgerError(
            f"{what} refused: decision_cutoff {fmt_ts(cutoff)} is {gap} from the actual open time "
            f"{fmt_ts(now)}; it must be within {OPEN_TOLERANCE}"
        )
    if cutoff >= start:
        raise LedgerError(f"{what} refused: decision_cutoff {fmt_ts(cutoff)} is not before the outcome window start {fmt_ts(start)}")
    if now >= start:
        raise LedgerError(f"{what} refused: the outcome window started at {fmt_ts(start)}, before the open at {fmt_ts(now)}")
    if end <= start:
        raise LedgerError(f"{what} refused: outcome window end {fmt_ts(end)} is not after its start {fmt_ts(start)}")
    for horizon, moment in horizon_cutoffs.items():
        if moment > cutoff:
            raise LedgerError(f"{what} refused: information set {horizon} cutoff {fmt_ts(moment)} is after the decision cutoff")
    return window["start"], window["end"]


class Ledger:
    def __init__(self, path: Path, anchor: GitAnchor | None = None, clock=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.anchor = anchor
        self.clock = clock or utc_now_dt
        self.last_receipt: AnchorReceipt | None = None
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        # MEMORY journal avoids a sandbox filesystem failure while creating triggers.
        # Committed rows still persist in the database file.
        self.conn.execute("PRAGMA journal_mode=MEMORY")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self._migrate()
        self.adopt_doctrine()

    def now(self) -> datetime:
        return self.clock().astimezone(timezone.utc).replace(microsecond=0)

    def _migrate(self) -> None:
        self.conn.executescript(SCHEMA)
        digest = sha256_text(SCHEMA)
        row = self.conn.execute(
            "SELECT version FROM schema_migrations WHERE version = 1"
        ).fetchone()
        if row is None:
            self.conn.execute(
                "INSERT INTO schema_migrations(version, sha256, applied_at) VALUES (1, ?, ?)",
                (digest, fmt_ts(self.now())),
            )
            self.conn.commit()
        for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
            version = int(path.name[:3])
            applied = self.conn.execute(
                "SELECT version FROM schema_migrations WHERE version = ?", (version,)
            ).fetchone()
            if applied:
                continue
            body = path.read_text(encoding="utf-8")
            self.conn.executescript(
                "BEGIN;\n" + body + "\n"
                f"INSERT INTO schema_migrations(version, sha256, applied_at) "
                f"VALUES ({version}, '{sha256_text(body)}', '{fmt_ts(self.now())}');\nCOMMIT;"
            )

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
                (digest, DOCTRINE_VERSION, body, fmt_ts(self.now())),
            )
            self.conn.commit()
        return digest

    @property
    def doctrine_sha(self) -> str:
        return self.adopt_doctrine()

    # -- cases --------------------------------------------------------------

    def open_case(self, card: dict) -> str:
        self._require_disposition(card)
        if card["disposition"] == "INVESTIGATE" and not card.get("critic"):
            raise LedgerError("INVESTIGATE refused: critic loss path is required")
        if card["disposition"] == "INVESTIGATE":
            self._require_critic(card["critic"])
        horizons = card.get("information_sets") or {}
        for horizon in HORIZONS:
            if horizon not in horizons:
                raise LedgerError(f"missing information set {horizon}")
        now = self.now()
        window = card.get("outcome_window") or None
        if card["call_type"] == "PROSPECTIVE":
            if self.anchor is None:
                raise LedgerError("prospective open refused: no git anchor is configured for this ledger")
            check_prospective_timing(
                now,
                card["decision_cutoff"],
                window,
                "prospective open",
                {h: horizons[h].get("cutoff", "") for h in HORIZONS},
            )
        elif window:
            try:
                if parse_ts(window["end"]) <= parse_ts(window["start"]):
                    raise LedgerError("outcome window end is not after its start")
            except (KeyError, ValueError) as exc:
                raise LedgerError(f"bad outcome_window: {exc}") from exc
        scan_entry_id = card.get("scan_entry_id")
        if scan_entry_id and not self.rows("SELECT 1 FROM scan_entries WHERE entry_id = ?", (scan_entry_id,)):
            raise LedgerError(f"unknown scan entry {scan_entry_id}")
        doctrine_sha = self.doctrine_sha
        case_id = card["case_id"]
        stored = {
            "case_id": case_id,
            "symbol": card["symbol"].upper(),
            "venue": card["venue"],
            "call_type": card["call_type"],
            "decision_cutoff": card["decision_cutoff"],
            "outcome_window_start": window["start"] if window else None,
            "outcome_window_end": window["end"] if window else None,
            "story_hypothesis": card["story_hypothesis"],
            "disposition": card["disposition"],
            "universe_id": card["universe_id"],
            "reconstruction_status": card["reconstruction_status"],
            "doctrine_sha": doctrine_sha,
            "scan_entry_id": scan_entry_id,
        }
        critic = card.get("critic") or None
        frozen = freeze_card(stored, horizons, critic, CARD_HASH_VERSION)
        card_sha = sha256_obj(frozen)
        opened_at = fmt_ts(now)
        self.last_receipt = None
        try:
            self.conn.execute(
                """
                INSERT INTO cases(
                  case_id, opened_at, symbol, venue, call_type, doctrine_sha,
                  decision_cutoff, story_hypothesis, disposition, card_sha,
                  universe_id, reconstruction_status, notes,
                  outcome_window_start, outcome_window_end, scan_entry_id, card_hash_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    opened_at,
                    stored["symbol"],
                    stored["venue"],
                    stored["call_type"],
                    doctrine_sha,
                    stored["decision_cutoff"],
                    stored["story_hypothesis"],
                    stored["disposition"],
                    card_sha,
                    stored["universe_id"],
                    stored["reconstruction_status"],
                    card.get("notes", ""),
                    stored["outcome_window_start"],
                    stored["outcome_window_end"],
                    scan_entry_id,
                    CARD_HASH_VERSION,
                ),
            )
            for horizon in HORIZONS:
                payload = horizons[horizon]
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
                        opened_at,
                    ),
                )
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
                        opened_at,
                    ),
                )
            if self.anchor is not None:
                line = {
                    "call_type": stored["call_type"],
                    "opened_at": opened_at,
                    "decision_cutoff": stored["decision_cutoff"],
                    "outcome_window_start": stored["outcome_window_start"],
                    "outcome_window_end": stored["outcome_window_end"],
                    "doctrine_sha": doctrine_sha,
                }
                self._anchor("CASE", case_id, card_sha, line, frozen)
        except sqlite3.IntegrityError as exc:
            self.conn.rollback()
            raise LedgerError(f"case {case_id} already exists; refusing rewrite") from exc
        except AnchorError as exc:
            self.conn.rollback()
            raise LedgerError(f"open refused: git anchor failed: {exc}") from exc
        except BaseException:
            self.conn.rollback()
            raise
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
                fmt_ts(self.now()),
            ),
        )
        self.conn.commit()

    def close_case(self, case_id: str, outcome: dict) -> None:
        row = self._require_case(case_id)
        claimed = outcome.get("card_sha")
        if not claimed:
            raise LedgerError("close refused: card_sha from the open is required")
        if claimed != row["card_sha"]:
            raise LedgerError("close refused: card hash does not match the frozen open")
        now = self.now()
        window_end = row["outcome_window_end"]
        if row["call_type"] == "PROSPECTIVE" and not window_end:
            raise LedgerError("close refused: prospective case has no pre-registered outcome window")
        if window_end and now < parse_ts(window_end):
            raise LedgerError(
                f"close refused: outcome window ends {window_end}; it is {fmt_ts(now)}"
            )
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
                fmt_ts(now),
                outcome["window_label"],
                outcome.get("window_return_pct"),
                outcome["outcome_label"],
                outcome["source"],
                row["card_sha"],
                outcome.get("notes", ""),
            ),
        )
        self.conn.commit()

    # -- scan log -----------------------------------------------------------

    def log_scan(self, scan: dict) -> str:
        """Rule 4. Every name a scanner evaluated is logged, flagged or not, opened or not."""
        if self.anchor is None:
            raise LedgerError("scan refused: no git anchor is configured for this ledger")
        for key in ("scan_id", "scanner", "universe_id", "decision_cutoff", "outcome_window", "hit_label"):
            if not scan.get(key):
                raise LedgerError(f"scan refused: {key} is required")
        if scan["hit_label"] not in HIT_LABELS:
            raise LedgerError(f"scan refused: hit_label must be one of {HIT_LABELS}")
        entries = scan.get("entries") or []
        if not entries:
            raise LedgerError("scan refused: a scan with no entries has no base rate")
        now = self.now()
        start, end = check_prospective_timing(now, scan["decision_cutoff"], scan["outcome_window"], "scan log")
        scan_id = scan["scan_id"]
        frozen_entries, entry_shas = {}, {}
        for entry in entries:
            for key in ("symbol", "venue", "reconstruction_status"):
                if not entry.get(key):
                    raise LedgerError(f"scan refused: entry {entry.get('symbol')!r} is missing {key}")
            if not isinstance(entry.get("flagged"), bool):
                raise LedgerError(f"scan refused: entry {entry['symbol']} needs flagged true or false")
            if not isinstance(entry.get("facts"), dict):
                raise LedgerError(f"scan refused: entry {entry['symbol']} needs a facts object")
            body = freeze_scan_entry(scan_id, entry)
            entry_id = f"{scan_id}:{body['symbol']}"
            if entry_id in frozen_entries:
                raise LedgerError(f"scan refused: {body['symbol']} appears twice")
            frozen_entries[entry_id] = body
            entry_shas[entry_id] = sha256_obj(body)
        header = {
            "scan_id": scan_id,
            "scanner": scan["scanner"],
            "universe_id": scan["universe_id"],
            "decision_cutoff": scan["decision_cutoff"],
            "outcome_window_start": start,
            "outcome_window_end": end,
            "hit_label": scan["hit_label"],
            "rule_version": RULE_VERSION,
        }
        frozen = freeze_scan(header, entry_shas)
        scan_sha = sha256_obj(frozen)
        scanned_at = fmt_ts(now)
        self.last_receipt = None
        try:
            self.conn.execute(
                """
                INSERT INTO scan_runs(scan_id, scanned_at, scanner, universe_id, decision_cutoff,
                  outcome_window_start, outcome_window_end, hit_label, rule_version, n_entries, scan_sha, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (scan_id, scanned_at, header["scanner"], header["universe_id"], header["decision_cutoff"],
                 start, end, header["hit_label"], RULE_VERSION, len(frozen_entries), scan_sha, scan.get("notes", "")),
            )
            for entry_id, body in frozen_entries.items():
                self.conn.execute(
                    """
                    INSERT INTO scan_entries(entry_id, scan_id, symbol, venue, flagged, reconstruction_status,
                      facts_json, entry_sha, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (entry_id, scan_id, body["symbol"], body["venue"], int(body["flagged"]),
                     body["reconstruction_status"], json.dumps(body["facts"], sort_keys=True),
                     entry_shas[entry_id], scanned_at),
                )
                latest = {"facts": body["facts"], "reconstruction_status": body["reconstruction_status"]}
                for result in evaluate({"T-24H": latest}):
                    self.conn.execute(
                        """
                        INSERT INTO scan_evaluations(eval_id, entry_id, detector, rule_version, status, features_json, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (f"{entry_id}:{result['detector']}:{result['rule_version']}", entry_id, result["detector"],
                         result["rule_version"], result["status"], json.dumps(result["features"], sort_keys=True),
                         scanned_at),
                    )
            line = {
                "scanner": header["scanner"],
                "scanned_at": scanned_at,
                "decision_cutoff": header["decision_cutoff"],
                "outcome_window_start": start,
                "outcome_window_end": end,
                "n_entries": len(frozen_entries),
                "n_flagged": sum(1 for b in frozen_entries.values() if b["flagged"]),
            }
            body = {"scan": frozen, "entries": frozen_entries}
            self._anchor("SCAN", scan_id, scan_sha, line, body)
        except sqlite3.IntegrityError as exc:
            self.conn.rollback()
            raise LedgerError(f"scan {scan_id} already exists; refusing rewrite") from exc
        except AnchorError as exc:
            self.conn.rollback()
            raise LedgerError(f"scan refused: git anchor failed: {exc}") from exc
        except BaseException:
            self.conn.rollback()
            raise
        self.conn.commit()
        return scan_sha

    def close_scan(self, payload: dict) -> int:
        scan_id = payload.get("scan_id")
        rows = self.rows("SELECT * FROM scan_runs WHERE scan_id = ?", (scan_id,))
        if not rows:
            raise LedgerError(f"unknown scan {scan_id}")
        scan = rows[0]
        if not payload.get("scan_sha"):
            raise LedgerError("scan close refused: scan_sha from the scan log is required")
        if payload["scan_sha"] != scan["scan_sha"]:
            raise LedgerError("scan close refused: scan hash does not match the frozen scan")
        now = self.now()
        if now < parse_ts(scan["outcome_window_end"]):
            raise LedgerError(f"scan close refused: outcome window ends {scan['outcome_window_end']}; it is {fmt_ts(now)}")
        n = 0
        try:
            for outcome in payload.get("outcomes") or []:
                entry_id = f"{scan_id}:{outcome['symbol'].upper()}"
                if not self.rows("SELECT 1 FROM scan_entries WHERE entry_id = ?", (entry_id,)):
                    raise LedgerError(f"scan close refused: {outcome['symbol']} was not in scan {scan_id}")
                try:
                    self.conn.execute(
                        """
                        INSERT INTO scan_outcomes(outcome_id, entry_id, closed_at, window_return_pct,
                          outcome_label, source, scan_sha_at_scan, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (f"{entry_id}:outcome", entry_id, fmt_ts(now), outcome.get("window_return_pct"),
                         outcome["outcome_label"], outcome["source"], scan["scan_sha"], outcome.get("notes", "")),
                    )
                except sqlite3.IntegrityError as exc:
                    raise LedgerError(f"scan close refused: {entry_id} already has an outcome or a bad label") from exc
                n += 1
        except BaseException:
            self.conn.rollback()
            raise
        self.conn.commit()
        return n

    # -- integrity ----------------------------------------------------------

    def assert_immutable(self) -> None:
        guards = {
            r["tbl_name"]: r["n"]
            for r in self.rows("SELECT tbl_name, COUNT(*) AS n FROM sqlite_master WHERE type = 'trigger' GROUP BY tbl_name")
        }
        for table in APPEND_ONLY_TABLES:
            if guards.get(table, 0) < 2:
                raise LedgerError(f"{table} is missing its append-only triggers")
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if not count:
                continue
            for statement in (f"DELETE FROM {table}", f"UPDATE {table} SET rowid = rowid"):
                try:
                    self.conn.execute(statement)
                except sqlite3.DatabaseError as exc:
                    if "append-only" not in str(exc):
                        self.conn.rollback()
                        raise
                    continue
                self.conn.rollback()
                raise LedgerError(f"{statement.split()[0].lower()} was allowed on {table}")
        self.conn.rollback()

    def rows(self, sql: str, params=()):
        return list(self.conn.execute(sql, params))

    def _anchor(self, kind: str, record_id: str, sha: str, line: dict, body: dict) -> None:
        receipt = self.anchor.anchor(kind, record_id, sha, line, body)
        self.conn.execute(
            """
            INSERT INTO anchors(anchor_id, kind, record_id, anchored_sha, git_commit, registry_path, anchored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (f"{kind}:{record_id}", kind, record_id, sha, receipt.commit, receipt.registry_path, receipt.committed_at),
        )
        self.last_receipt = receipt

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
