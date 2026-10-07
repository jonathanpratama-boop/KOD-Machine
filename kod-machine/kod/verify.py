"""`kod verify`: recompute every hash from the stored rows and check each anchor against git.

Nothing here trusts a stored hash. Card hashes are rebuilt from the case, information
set and critic rows; scan hashes from the entry rows. Each rebuilt hash must equal the
stored one, the outcome's copy, the anchors row, and the line committed to git.
"""

from __future__ import annotations

import json

from .anchor import GitAnchor
from .hashing import parse_ts, sha256_obj, sha256_text
from .ledger import (
    HORIZONS,
    MIGRATIONS_DIR,
    OPEN_TOLERANCE,
    SCHEMA,
    Ledger,
    freeze_card,
    freeze_scan,
    freeze_scan_entry,
)


def verify(ledger: Ledger, anchor: GitAnchor | None) -> dict:
    findings: list[dict] = []
    stats = {"cases": 0, "scans": 0, "scan_entries": 0, "anchors_verified": 0, "anchors_on_remote": 0}

    def fail(subject: str, message: str) -> None:
        findings.append({"level": "FAIL", "subject": subject, "message": message})

    def warn(subject: str, message: str) -> None:
        findings.append({"level": "WARN", "subject": subject, "message": message})

    anchors = {(r["kind"], r["record_id"]): dict(r) for r in ledger.rows("SELECT * FROM anchors")}

    def check_anchor(kind: str, record_id: str, sha: str, recorded_at: str, deadline: str | None, required: bool) -> None:
        subject = f"{kind.lower()} {record_id}"
        row = anchors.pop((kind, record_id), None)
        if row is None:
            (fail if required else warn)(subject, "hash is not anchored in git")
            return
        if row["anchored_sha"] != sha:
            fail(subject, f"anchors row holds {row['anchored_sha']}, rebuilt hash is {sha}")
            return
        if anchor is None:
            warn(subject, "git is not available; anchor commit not checked")
            return
        commit, path = row["git_commit"], row["registry_path"]

        def holds(records: list[dict]) -> bool:
            return any(
                r.get("kind") == kind and r.get("record_id") == record_id and r.get("sha256") == sha
                for r in records
            )

        if not holds(anchor.committed_records(commit, path)):
            fail(subject, f"anchor commit {commit[:12]} does not contain this hash in {path}")
            return
        if not anchor.is_ancestor_of_head(commit):
            fail(subject, f"anchor commit {commit[:12]} is not in the history of HEAD")
            return
        if not holds(anchor.committed_records("HEAD", path)):
            fail(subject, f"the registry line was removed from {path} after commit {commit[:12]}")
            return
        committed = anchor.commit_time(commit)
        if committed is None:
            fail(subject, f"anchor commit {commit[:12]} has no readable timestamp")
            return
        committed_at = parse_ts(committed)
        if deadline and committed_at >= parse_ts(deadline):
            fail(subject, f"anchor committed {committed}, not before the outcome window start {deadline}")
            return
        if abs(committed_at - parse_ts(recorded_at)) > OPEN_TOLERANCE:
            warn(subject, f"anchor commit time {committed} is more than {OPEN_TOLERANCE} from the ledger time {recorded_at}")
        stats["anchors_verified"] += 1
        if anchor.on_remote(commit):
            stats["anchors_on_remote"] += 1
        else:
            warn(subject, f"anchor commit {commit[:12]} is local only; push it so the timestamp is held outside this machine")

    # Schema and doctrine bodies are hashed when adopted; an edit after adoption is a rewrite.
    for row in ledger.rows("SELECT * FROM schema_migrations ORDER BY version"):
        if row["version"] == 1:
            body = SCHEMA
        else:
            matches = sorted(MIGRATIONS_DIR.glob(f"{row['version']:03d}_*.sql"))
            if not matches:
                fail(f"migration {row['version']}", "applied migration file is missing")
                continue
            body = matches[0].read_text(encoding="utf-8")
        if sha256_text(body) != row["sha256"]:
            fail(f"migration {row['version']}", "migration file was edited after it was applied")
    for row in ledger.rows("SELECT * FROM doctrine_versions"):
        if sha256_text(row["body"]) != row["doctrine_sha"]:
            fail(f"doctrine {row['doctrine_sha'][:12]}", "stored doctrine body does not hash to its id")

    outcomes = {r["case_id"]: dict(r) for r in ledger.rows("SELECT * FROM outcomes")}
    critics = {r["case_id"]: dict(r) for r in ledger.rows("SELECT * FROM critic_notes")}
    for case in ledger.rows("SELECT * FROM cases ORDER BY opened_at, case_id"):
        case = dict(case)
        stats["cases"] += 1
        subject = f"case {case['case_id']}"
        sets = {}
        for row in ledger.rows("SELECT * FROM information_sets WHERE case_id = ?", (case["case_id"],)):
            payload = json.loads(row["payload_json"])
            if sha256_obj(payload) != row["set_sha"]:
                fail(subject, f"information set {row['horizon']} does not hash to its stored set_sha")
            sets[row["horizon"]] = payload
        missing = [h for h in HORIZONS if h not in sets]
        if missing:
            fail(subject, f"missing information sets {missing}")
            continue
        version = case.get("card_hash_version")
        rebuilt = sha256_obj(freeze_card(case, sets, critics.get(case["case_id"]), version))
        if rebuilt != case["card_sha"]:
            fail(subject, f"stored card_sha {case['card_sha']} but the stored rows hash to {rebuilt}")
        outcome = outcomes.get(case["case_id"])
        if outcome and outcome["card_sha_at_open"] != case["card_sha"]:
            fail(subject, "outcome row carries a different card hash than the open")
        prospective = case["call_type"] == "PROSPECTIVE"
        if prospective:
            if version is None or not case.get("outcome_window_start"):
                fail(subject, "prospective case was opened without a pre-registered outcome window")
            else:
                opened = parse_ts(case["opened_at"])
                if abs(opened - parse_ts(case["decision_cutoff"])) > OPEN_TOLERANCE:
                    fail(subject, "opened more than 1 hour from its decision cutoff")
                if opened >= parse_ts(case["outcome_window_start"]):
                    fail(subject, "opened after its outcome window started")
                if outcome and parse_ts(outcome["closed_at"]) < parse_ts(case["outcome_window_end"]):
                    fail(subject, "closed before its outcome window ended")
        check_anchor(
            "CASE",
            case["case_id"],
            rebuilt,
            case["opened_at"],
            case.get("outcome_window_start") if prospective else None,
            required=prospective,
        )

    scan_outcomes = {r["entry_id"]: dict(r) for r in ledger.rows("SELECT * FROM scan_outcomes")}
    for scan in ledger.rows("SELECT * FROM scan_runs ORDER BY scanned_at, scan_id"):
        scan = dict(scan)
        stats["scans"] += 1
        subject = f"scan {scan['scan_id']}"
        entry_shas = {}
        for row in ledger.rows("SELECT * FROM scan_entries WHERE scan_id = ?", (scan["scan_id"],)):
            stats["scan_entries"] += 1
            body = freeze_scan_entry(scan["scan_id"], {
                "symbol": row["symbol"],
                "venue": row["venue"],
                "flagged": bool(row["flagged"]),
                "reconstruction_status": row["reconstruction_status"],
                "facts": json.loads(row["facts_json"]),
            })
            sha = sha256_obj(body)
            if sha != row["entry_sha"]:
                fail(subject, f"entry {row['symbol']} does not hash to its stored entry_sha")
            entry_shas[row["entry_id"]] = sha
            outcome = scan_outcomes.get(row["entry_id"])
            if outcome:
                if outcome["scan_sha_at_scan"] != scan["scan_sha"]:
                    fail(subject, f"outcome for {row['symbol']} carries a different scan hash")
                if parse_ts(outcome["closed_at"]) < parse_ts(scan["outcome_window_end"]):
                    fail(subject, f"outcome for {row['symbol']} was recorded before the window ended")
        if len(entry_shas) != scan["n_entries"]:
            fail(subject, f"scan_runs says {scan['n_entries']} entries, ledger holds {len(entry_shas)}")
        rebuilt = sha256_obj(freeze_scan(scan, entry_shas))
        if rebuilt != scan["scan_sha"]:
            fail(subject, f"stored scan_sha {scan['scan_sha']} but the stored rows hash to {rebuilt}")
        scanned = parse_ts(scan["scanned_at"])
        if abs(scanned - parse_ts(scan["decision_cutoff"])) > OPEN_TOLERANCE:
            fail(subject, "logged more than 1 hour from its decision cutoff")
        if scanned >= parse_ts(scan["outcome_window_start"]):
            fail(subject, "logged after its outcome window started")
        check_anchor("SCAN", scan["scan_id"], rebuilt, scan["scanned_at"], scan["outcome_window_start"], required=True)

    for (kind, record_id) in anchors:
        fail(f"{kind.lower()} {record_id}", "anchors row has no ledger record")

    return {
        "ok": not any(f["level"] == "FAIL" for f in findings),
        "stats": stats,
        "findings": findings,
    }


def render(result: dict) -> str:
    s = result["stats"]
    lines = [
        f"verify: {'OK' if result['ok'] else 'FAILED'}",
        f"cases {s['cases']}, scans {s['scans']} ({s['scan_entries']} entries), "
        f"anchors verified {s['anchors_verified']}, on a remote {s['anchors_on_remote']}",
    ]
    for f in result["findings"]:
        lines.append(f"{f['level']} {f['subject']}: {f['message']}")
    return "\n".join(lines)
