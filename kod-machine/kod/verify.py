"""`kod verify`: recompute every hash from the stored rows and check each anchor against git
and against its external timestamps.

Nothing here trusts a stored hash or a local clock. Card hashes are rebuilt from the case,
information set, critic and detector-evaluation rows; scan hashes from the entry and
evaluation rows; evidence ids from the archived bytes. Each rebuilt hash must equal the
stored one, the outcome's copy, the anchors row and the line committed to git. Time comes
from the RFC 3161 tokens: a prospective card must carry a token that verifies against the
pinned authority certificates, dated within an hour of its decision cutoff and before
its outcome window. The git commit date is reported but never relied on.
"""

from __future__ import annotations

import json

from .anchor import GitAnchor, anchor_line
from .detectors import RULE_VERSION, evaluate
from .hashing import parse_ts, sha256_bytes, sha256_obj, sha256_text
from .ledger import (
    CARD_HASH_VERSION,
    HORIZONS,
    MIGRATIONS_DIR,
    OPEN_TOLERANCE,
    SCAN_HASH_VERSION,
    SCHEMA,
    Ledger,
    check_horizon_offsets,
    evidence_problems,
    freeze_card,
    freeze_scan,
    freeze_scan_entry,
    frozen_evaluations,
)


def verify(ledger: Ledger, anchor: GitAnchor | None, timestamper=None) -> dict:
    findings: list[dict] = []
    stats = {"cases": 0, "scans": 0, "scan_entries": 0, "evidence": 0, "anchors_verified": 0,
             "anchors_externally_timestamped": 0, "anchors_on_remote": 0}

    def fail(subject: str, message: str) -> None:
        findings.append({"level": "FAIL", "subject": subject, "message": message})

    def warn(subject: str, message: str) -> None:
        findings.append({"level": "WARN", "subject": subject, "message": message})

    anchors = {(r["kind"], r["record_id"]): dict(r) for r in ledger.rows("SELECT * FROM anchors")}

    def check_anchor(kind: str, record_id: str, sha: str, recorded_at: str, required: bool,
                     decision_cutoff: str | None = None, deadline: str | None = None) -> None:
        subject = f"{kind.lower()} {record_id}"
        row = anchors.pop((kind, record_id), None)
        if row is None:
            (fail if required else warn)(subject, "hash is not anchored in git")
            return
        if row["anchored_sha"] != sha:
            fail(subject, f"anchors row holds {row['anchored_sha']}, rebuilt hash is {sha}")
            return
        if anchor is None:
            warn(subject, "git is not available; anchor not checked")
            return
        commit, path = row["git_commit"], row["registry_path"]
        record = next(
            (r for r in anchor.committed_records(commit, path)
             if r.get("kind") == kind and r.get("record_id") == record_id and r.get("sha256") == sha),
            None,
        )
        if record is None:
            fail(subject, f"anchor commit {commit[:12]} does not contain this hash in {path}")
            return
        if not anchor.is_ancestor_of_head(commit):
            fail(subject, f"anchor commit {commit[:12]} is not in the history of HEAD")
            return
        if record not in anchor.committed_records("HEAD", path):
            fail(subject, f"the registry line was removed from {path} after commit {commit[:12]}")
            return
        stats["anchors_verified"] += 1

        verified = []
        for token in json.loads(row.get("timestamps_json") or "[]"):
            blob = anchor.committed_file(commit, token["path"])
            if blob is None:
                fail(subject, f"{token['authority']} timestamp token {token['path']} is not in commit {commit[:12]}")
                continue
            if timestamper is None:
                warn(subject, "no timestamp verifier configured; tokens not checked")
                continue
            try:
                verified.append(timestamper.verify(token["authority"], blob, anchor_line(record)))
            except Exception as exc:
                fail(subject, f"{token['authority']} timestamp token does not verify: {exc}")
        external = min(verified) if verified else None
        if external is None:
            if required:
                fail(subject, "no verified external timestamp; the git commit date alone is not evidence of time")
            else:
                warn(subject, "no external timestamp; only the git commit date, which the committer controls")
        else:
            stats["anchors_externally_timestamped"] += 1
            stamp = external.isoformat().replace("+00:00", "Z")
            if decision_cutoff and abs(external - parse_ts(decision_cutoff)) > OPEN_TOLERANCE:
                fail(subject, f"externally timestamped {stamp}, more than {OPEN_TOLERANCE} from its decision cutoff")
            if deadline and external >= parse_ts(deadline):
                fail(subject, f"externally timestamped {stamp}, not before its outcome window start {deadline}")
            if abs(external - parse_ts(recorded_at)) > OPEN_TOLERANCE:
                (fail if required else warn)(
                    subject, f"ledger time {recorded_at} is more than {OPEN_TOLERANCE} from the external timestamp {stamp}"
                )
            committed = anchor.commit_time(commit)
            if committed and abs(parse_ts(committed) - external) > OPEN_TOLERANCE:
                warn(subject, f"git commit date {committed} disagrees with the external timestamp {stamp}")
        if anchor.on_remote(commit):
            stats["anchors_on_remote"] += 1
        else:
            warn(subject, f"anchor commit {commit[:12]} is local only; push it")

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

    # Evidence: the archived bytes must still hash to the id that cards cite.
    evidence_rows = ledger.evidence_rows()
    for evidence_id, ev in sorted(evidence_rows.items()):
        stats["evidence"] += 1
        subject = f"evidence {evidence_id[:12]}"
        if anchor is None:
            warn(subject, "git is not available; archived bytes not checked")
            continue
        data = anchor.committed_file("HEAD", ev["stored_path"])
        if data is None or sha256_bytes(data) != evidence_id:
            fail(subject, f"archived bytes at {ev['stored_path']} are missing or no longer hash to the evidence id")
        meta = anchor.committed_file("HEAD", ev["metadata_path"])
        if meta is None or sha256_obj(json.loads(meta)) != ev["evidence_sha"]:
            fail(subject, f"frozen metadata at {ev['metadata_path']} is missing or was edited")
        if not anchor.is_ancestor_of_head(ev["git_commit"]):
            fail(subject, f"evidence commit {ev['git_commit'][:12]} is not in the history of HEAD")

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
        eval_rows = ledger.rows("SELECT * FROM detector_evaluations WHERE case_id = ?", (case["case_id"],))
        rebuilt = sha256_obj(freeze_card(case, sets, critics.get(case["case_id"]), version, frozen_evaluations(eval_rows)))
        if rebuilt != case["card_sha"]:
            fail(subject, f"stored card_sha {case['card_sha']} but the stored rows hash to {rebuilt}")
        outcome = outcomes.get(case["case_id"])
        if outcome and outcome["card_sha_at_open"] != case["card_sha"]:
            fail(subject, "outcome row carries a different card hash than the open")
        prospective = case["call_type"] == "PROSPECTIVE"
        if version == CARD_HASH_VERSION:
            late = [r["detector"] for r in eval_rows if r["recorded_at"] != case["opened_at"]]
            if late:
                fail(subject, f"detector evaluations recorded after the open: {late}")
            now_status = {(r["detector"], r["rule_version"]): r["status"] for r in evaluate(sets)}
            for r in eval_rows:
                key = (r["detector"], r["rule_version"])
                if r["rule_version"] == RULE_VERSION and key in now_status and now_status[key] != r["status"]:
                    fail(subject, f"{r['detector']} {r['rule_version']} now evaluates {now_status[key]}, "
                                  f"frozen {r['status']}: the rule was edited without a new version")
        elif prospective:
            warn(subject, "prospective card opened before evaluations were frozen into the hash; it is not scored")
        offsets = check_horizon_offsets(case["decision_cutoff"], sets)
        for problem in offsets:
            (fail if prospective else warn)(subject, problem)
        for problem in evidence_problems(sets, evidence_rows, require_all=prospective and version == CARD_HASH_VERSION):
            fail(subject, problem)
        for horizon in HORIZONS:
            for ids in (sets[horizon].get("evidence") or {}).values():
                for evidence_id in ids if isinstance(ids, list) else []:
                    ev = evidence_rows.get(evidence_id)
                    if ev and parse_ts(ev["recorded_at"]) > parse_ts(case["opened_at"]):
                        fail(subject, f"cites evidence {evidence_id[:12]} recorded after the open")
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
            "CASE", case["case_id"], rebuilt, case["opened_at"], required=prospective,
            decision_cutoff=case["decision_cutoff"] if prospective else None,
            deadline=case.get("outcome_window_start") if prospective else None,
        )

    scan_outcomes = {r["entry_id"]: dict(r) for r in ledger.rows("SELECT * FROM scan_outcomes")}
    for scan in ledger.rows("SELECT * FROM scan_runs ORDER BY scanned_at, scan_id"):
        scan = dict(scan)
        stats["scans"] += 1
        subject = f"scan {scan['scan_id']}"
        version = scan.get("scan_hash_version")
        entry_shas = {}
        for row in ledger.rows("SELECT * FROM scan_entries WHERE scan_id = ?", (scan["scan_id"],)):
            stats["scan_entries"] += 1
            evals = ledger.rows("SELECT * FROM scan_evaluations WHERE entry_id = ?", (row["entry_id"],))
            if version == SCAN_HASH_VERSION and any(e["recorded_at"] != row["recorded_at"] for e in evals):
                fail(subject, f"entry {row['symbol']} has evaluations recorded after the scan")
            body = freeze_scan_entry(scan["scan_id"], {
                "symbol": row["symbol"],
                "venue": row["venue"],
                "flagged": bool(row["flagged"]),
                "reconstruction_status": row["reconstruction_status"],
                "facts": json.loads(row["facts_json"]),
            }, frozen_evaluations(evals), version)
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
        rebuilt = sha256_obj(freeze_scan(scan, entry_shas, version))
        if rebuilt != scan["scan_sha"]:
            fail(subject, f"stored scan_sha {scan['scan_sha']} but the stored rows hash to {rebuilt}")
        scanned = parse_ts(scan["scanned_at"])
        if abs(scanned - parse_ts(scan["decision_cutoff"])) > OPEN_TOLERANCE:
            fail(subject, "logged more than 1 hour from its decision cutoff")
        if scanned >= parse_ts(scan["outcome_window_start"]):
            fail(subject, "logged after its outcome window started")
        check_anchor("SCAN", scan["scan_id"], rebuilt, scan["scanned_at"], required=True,
                     decision_cutoff=scan["decision_cutoff"], deadline=scan["outcome_window_start"])

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
        f"cases {s['cases']}, scans {s['scans']} ({s['scan_entries']} entries), evidence {s['evidence']}, "
        f"anchors verified {s['anchors_verified']}, externally timestamped {s['anchors_externally_timestamped']}, "
        f"on a remote {s['anchors_on_remote']}",
    ]
    for f in result["findings"]:
        lines.append(f"{f['level']} {f['subject']}: {f['message']}")
    return "\n".join(lines)
