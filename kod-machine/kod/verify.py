"""`kod verify`: recompute every hash from the stored rows, check each anchor against git,
against its RFC 3161 tokens and, for strict records, against GitHub's server-side receipt.

Nothing here trusts a stored hash or a local clock. Card hashes are rebuilt from the case,
information set, critic and detector-evaluation rows; scan hashes from entry and evaluation
rows; evidence ids from the frozen objects and archived bytes; grade ceilings from the
evidence fields. Time comes from the external tokens and from GitHub, never the commit date.

A prospective case is AUTHORITATIVE for calibration only if it is a KOD-CARD-v3 STRICT card,
its hash is in its anchor commit (an ancestor of HEAD), and GitHub's earliest push-triggered
run for exactly that commit was created before the outcome window started. Anything else is
reported with its reason and excluded.
"""

from __future__ import annotations

import json

from . import evidence as ev
from .anchor import REGISTRY_FILES, GitAnchor, anchor_line
from .detectors import RULE_VERSION, evaluate
from .hashing import canonical, parse_ts, sha256_bytes, sha256_obj, sha256_text
from .ledger import (
    CARD_HASH_VERSION,
    HORIZONS,
    MIGRATIONS_DIR,
    OPEN_TOLERANCE,
    SCHEMA,
    Ledger,
    check_horizon_offsets,
    detector_source_sha,
    evidence_problems,
    freeze_card,
    freeze_scan,
    freeze_scan_entry,
    frozen_evaluations,
)
from .remote import LATE, MISMATCH, UNVERIFIED, VERIFIED, remote_status

LEGACY = "LEGACY_INTEGRITY"
ANCHOR_FAILED = "ANCHOR_NOT_PROVEN"
AUTHORITATIVE = "AUTHORITATIVE"


def anchor_holds(
    anchor: GitAnchor | None, row: dict | None, kind: str, record_id: str, sha: str
) -> tuple[bool, str]:
    """The frozen hash is in the anchor commit, which is in HEAD's history, and still in HEAD."""
    if row is None:
        return False, "hash is not anchored in git"
    if row["anchored_sha"] != sha:
        return False, f"anchors row holds {row['anchored_sha']}, rebuilt hash is {sha}"
    if anchor is None:
        return False, "git is not available"
    commit, path = row["git_commit"], row["registry_path"]
    record = next(
        (
            r
            for r in anchor.committed_records(commit, path)
            if r.get("kind") == kind and r.get("record_id") == record_id and r.get("sha256") == sha
        ),
        None,
    )
    if record is None:
        return False, f"anchor commit {commit[:12]} does not contain this hash in {path}"
    if not anchor.is_ancestor_of_head(commit):
        return False, f"anchor commit {commit[:12]} is not in the history of HEAD"
    if record not in anchor.committed_records("HEAD", path):
        return False, f"the registry line was removed from {path} after commit {commit[:12]}"
    return True, ""


def _rebuild_case_sha(ledger: Ledger, case: dict) -> str | None:
    sets = {
        r["horizon"]: json.loads(r["payload_json"])
        for r in ledger.rows("SELECT * FROM information_sets WHERE case_id = ?", (case["case_id"],))
    }
    if any(h not in sets for h in HORIZONS):
        return None
    critic = ledger.rows("SELECT * FROM critic_notes WHERE case_id = ?", (case["case_id"],))
    evals = ledger.rows("SELECT * FROM detector_evaluations WHERE case_id = ?", (case["case_id"],))
    return sha256_obj(
        freeze_card(
            case,
            sets,
            dict(critic[0]) if critic else None,
            case.get("card_hash_version"),
            frozen_evaluations(evals),
        )
    )


def _rebuild_scan_sha(ledger: Ledger, scan: dict) -> tuple[str | None, dict]:
    """Rebuild a scan's hash from its stored entry and evaluation rows. None when the stored
    entry count disagrees with the rows (an entry inserted or removed)."""
    version = scan.get("scan_hash_version")
    entry_shas = {}
    for row in ledger.rows("SELECT * FROM scan_entries WHERE scan_id = ?", (scan["scan_id"],)):
        evals = ledger.rows("SELECT * FROM scan_evaluations WHERE entry_id = ?", (row["entry_id"],))
        body = freeze_scan_entry(
            scan["scan_id"],
            {
                "symbol": row["symbol"],
                "venue": row["venue"],
                "flagged": bool(row["flagged"]),
                "reconstruction_status": row["reconstruction_status"],
                "facts": json.loads(row["facts_json"]),
            },
            frozen_evaluations(evals),
            version,
        )
        entry_shas[row["entry_id"]] = sha256_obj(body)
    if len(entry_shas) != scan["n_entries"]:
        return None, entry_shas
    return sha256_obj(freeze_scan(scan, entry_shas, version)), entry_shas


def calibration_eligibility(ledger: Ledger, anchor: GitAnchor | None, client) -> dict:
    """{case_id: {"status", "reason", "remote"}} for every PROSPECTIVE case, and the same for scans
    under key ("SCAN", scan_id)."""
    anchors = {(r["kind"], r["record_id"]): dict(r) for r in ledger.rows("SELECT * FROM anchors")}
    out = {}

    def judge(kind, record_id, sha, strict, deadline):
        if not strict:
            return {
                "status": LEGACY,
                "reason": "opened before KOD-CARD-v3 / STRICT integrity",
                "remote": None,
            }
        row = anchors.get((kind, record_id))
        ok, why = anchor_holds(anchor, row, kind, record_id, sha)
        if not ok:
            return {"status": ANCHOR_FAILED, "reason": why, "remote": None}
        remote = remote_status(
            client, row["git_commit"], deadline, ledger.receipts_for(kind, record_id)
        )
        if remote["status"] != VERIFIED:
            return {"status": remote["status"], "reason": remote["reason"], "remote": remote}
        return {"status": AUTHORITATIVE, "reason": "", "remote": remote}

    for case in ledger.rows("SELECT * FROM cases WHERE call_type = 'PROSPECTIVE'"):
        case = dict(case)
        strict = (
            case.get("card_hash_version") == CARD_HASH_VERSION
            and case.get("integrity_level") == ev.STRICT
        )
        sha = _rebuild_case_sha(ledger, case) if strict else case["card_sha"]
        if strict and sha != case["card_sha"]:
            out[case["case_id"]] = {
                "status": ANCHOR_FAILED,
                "reason": "stored rows no longer hash to the card",
                "remote": None,
            }
            continue
        out[case["case_id"]] = judge(
            "CASE", case["case_id"], sha, strict, case["outcome_window_start"]
        )
    for scan in ledger.rows("SELECT * FROM scan_runs"):
        scan = dict(scan)
        strict = scan.get("scan_hash_version") == "KOD-SCAN-v3"
        sha = scan["scan_sha"]
        if strict:
            sha, _ = _rebuild_scan_sha(ledger, scan)
            if sha != scan["scan_sha"]:
                out[("SCAN", scan["scan_id"])] = {
                    "status": ANCHOR_FAILED,
                    "remote": None,
                    "reason": "stored rows no longer hash to the scan",
                }
                continue
        out[("SCAN", scan["scan_id"])] = judge(
            "SCAN", scan["scan_id"], sha, strict, scan["outcome_window_start"]
        )
    return out


def verify(ledger: Ledger, anchor: GitAnchor | None, timestamper=None, client=None) -> dict:
    findings: list[dict] = []
    stats = {
        "cases": 0,
        "scans": 0,
        "scan_entries": 0,
        "evidence": 0,
        "evidence_v2": 0,
        "anchors_verified": 0,
        "anchors_externally_timestamped": 0,
        "anchors_on_remote": 0,
        "remote_receipts_verified": 0,
        "authoritative_prospective": 0,
    }

    def fail(subject: str, message: str) -> None:
        findings.append({"level": "FAIL", "subject": subject, "message": message})

    def warn(subject: str, message: str) -> None:
        findings.append({"level": "WARN", "subject": subject, "message": message})

    anchors = {(r["kind"], r["record_id"]): dict(r) for r in ledger.rows("SELECT * FROM anchors")}

    def check_anchor(
        kind: str,
        record_id: str,
        sha: str,
        recorded_at: str,
        required: bool,
        decision_cutoff: str | None = None,
        deadline: str | None = None,
    ) -> None:
        subject = f"{kind.lower()} {record_id}"
        row = anchors.pop((kind, record_id), None)
        if row is None:
            (fail if required else warn)(subject, "hash is not anchored in git")
            return
        if anchor is None:
            warn(subject, "git is not available; anchor not checked")
            return
        ok, why = anchor_holds(anchor, row, kind, record_id, sha)
        if not ok:
            fail(subject, why)
            return
        stats["anchors_verified"] += 1
        commit, path = row["git_commit"], row["registry_path"]
        record = next(
            r
            for r in anchor.committed_records(commit, path)
            if r.get("kind") == kind and r.get("record_id") == record_id and r.get("sha256") == sha
        )
        verified = []
        for token in json.loads(row.get("timestamps_json") or "[]"):
            blob = anchor.committed_file(commit, token["path"])
            if blob is None:
                fail(
                    subject,
                    f"{token['authority']} timestamp token {token['path']} is not in commit {commit[:12]}",
                )
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
                fail(
                    subject,
                    "no verified external timestamp; the git commit date alone is not evidence of time",
                )
            else:
                warn(
                    subject,
                    "no external timestamp; only the git commit date, which the committer controls",
                )
        else:
            stats["anchors_externally_timestamped"] += 1
            stamp = external.isoformat().replace("+00:00", "Z")
            if decision_cutoff and abs(external - parse_ts(decision_cutoff)) > OPEN_TOLERANCE:
                fail(
                    subject,
                    f"externally timestamped {stamp}, more than {OPEN_TOLERANCE} from its decision cutoff",
                )
            if deadline and external >= parse_ts(deadline):
                fail(
                    subject,
                    f"externally timestamped {stamp}, not before its outcome window start {deadline}",
                )
            if abs(external - parse_ts(recorded_at)) > OPEN_TOLERANCE:
                (fail if required else warn)(
                    subject,
                    f"ledger time {recorded_at} is more than {OPEN_TOLERANCE} from the external timestamp {stamp}",
                )
            committed = anchor.commit_time(commit)
            if committed and abs(parse_ts(committed) - external) > OPEN_TOLERANCE:
                warn(
                    subject,
                    f"git commit date {committed} disagrees with the external timestamp {stamp}",
                )
        if anchor.on_remote(commit):
            stats["anchors_on_remote"] += 1
        else:
            warn(subject, f"anchor commit {commit[:12]} is local only; push it")

    # Schema, doctrine and detector source are hashed when adopted; an edit after adoption is a rewrite.
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
            fail(
                f"doctrine {row['doctrine_sha'][:12]}",
                "stored doctrine body does not hash to its id",
            )
    detector_versions = {
        r["rule_version"]: r["code_sha256"] for r in ledger.rows("SELECT * FROM detector_versions")
    }
    if (
        RULE_VERSION in detector_versions
        and detector_versions[RULE_VERSION] != detector_source_sha()
    ):
        fail(
            f"detector {RULE_VERSION}",
            "kod/detectors.py changed after this rule version was adopted; "
            "a changed detector must be a new RULE_VERSION",
        )

    # v1 evidence (before migration 4): archived bytes must still hash to the id.
    evidence_rows = ledger.evidence_rows()
    for evidence_id, row in sorted(evidence_rows.items()):
        stats["evidence"] += 1
        subject = f"evidence {evidence_id[:12]}"
        if anchor is None:
            continue
        data = anchor.committed_file("HEAD", row["stored_path"])
        if data is None or sha256_bytes(data) != evidence_id:
            fail(
                subject,
                f"archived bytes at {row['stored_path']} are missing or no longer hash to the evidence id",
            )
        meta = anchor.committed_file("HEAD", row["metadata_path"])
        if meta is None or sha256_obj(json.loads(meta)) != row["evidence_sha"]:
            fail(subject, f"frozen metadata at {row['metadata_path']} is missing or was edited")

    # v2 evidence objects: id, frozen file, bytes, tokens, and the grade ceiling, all recomputed.
    objects = ledger.evidence_objects()
    for evidence_id, row in sorted(
        (r["evidence_id"], dict(r)) for r in ledger.rows("SELECT * FROM evidence_objects")
    ):
        stats["evidence_v2"] += 1
        subject = f"evidence {evidence_id[:12]}"
        obj = json.loads(row["object_json"])
        if ev.evidence_id(obj) != evidence_id:
            fail(subject, "frozen object no longer hashes to its evidence id")
            continue
        for column in (
            "evidence_grade",
            "grade_ceiling",
            "source_type",
            "publication_time",
            "as_of_cutoff",
            "content_sha256",
        ):
            if row[column] != obj[column]:
                fail(subject, f"column {column} disagrees with the frozen object")
        if (
            bool(row["existence_verified"]) != obj["existence_verified"]
            or bool(row["content_verified"]) != obj["content_verified"]
        ):
            fail(subject, "verification flags disagree with the frozen object")
        ceiling = ev.grade_ceiling(
            obj["source_type"],
            parse_ts(obj["publication_time"]) if obj["publication_time"] else None,
            parse_ts(obj["as_of_cutoff"]),
            obj["existence_verified"],
            obj["content_verified"],
        )
        if ceiling != obj["grade_ceiling"] or obj["evidence_grade"] < ceiling:
            fail(
                subject,
                f"grade {obj['evidence_grade']} is not supported: its fields allow at most {ceiling}",
            )
        if anchor is None:
            continue
        committed = anchor.committed_file("HEAD", row["metadata_path"])
        if committed is None or json.loads(committed) != {"evidence_id": evidence_id, **obj}:
            fail(subject, f"frozen object at {row['metadata_path']} is missing or was edited")
        if (
            obj["content_sha256"]
            and obj["archived_copy"]
            and not obj["archived_copy"].startswith("http")
        ):
            data = anchor.committed_file("HEAD", obj["archived_copy"])
            if data is None or sha256_bytes(data) != obj["content_sha256"]:
                fail(
                    subject,
                    f"archived copy {obj['archived_copy']} is missing or no longer matches content_sha256",
                )
        methods = obj["verification_method"]
        if "EXTERNAL_TIMESTAMP_RECEIPT" in methods.values():
            ok_times = []
            for token in json.loads(row["timestamps_json"] or "[]"):
                blob = anchor.committed_file("HEAD", token["path"])
                if blob is None or timestamper is None:
                    continue
                try:
                    when = timestamper.verify(
                        token["authority"], blob, obj["content_sha256"].encode("ascii")
                    )
                except Exception as exc:
                    fail(subject, f"{token['authority']} content timestamp does not verify: {exc}")
                    continue
                if when <= parse_ts(obj["as_of_cutoff"]):
                    ok_times.append(when)
            if not ok_times:
                (fail if timestamper is not None else warn)(
                    subject,
                    "EXTERNAL_TIMESTAMP_RECEIPT claimed but no token verifies at or before the as-of cutoff",
                )

    eligibility = calibration_eligibility(ledger, anchor, client)
    outcomes = {r["case_id"]: dict(r) for r in ledger.rows("SELECT * FROM outcomes")}
    for case in ledger.rows("SELECT * FROM cases ORDER BY opened_at, case_id"):
        case = dict(case)
        stats["cases"] += 1
        subject = f"case {case['case_id']}"
        sets = {}
        for row in ledger.rows(
            "SELECT * FROM information_sets WHERE case_id = ?", (case["case_id"],)
        ):
            payload = json.loads(row["payload_json"])
            if sha256_obj(payload) != row["set_sha"]:
                fail(
                    subject, f"information set {row['horizon']} does not hash to its stored set_sha"
                )
            sets[row["horizon"]] = payload
        missing = [h for h in HORIZONS if h not in sets]
        if missing:
            fail(subject, f"missing information sets {missing}")
            continue
        version = case.get("card_hash_version")
        rebuilt = _rebuild_case_sha(ledger, case)
        if rebuilt != case["card_sha"]:
            fail(
                subject, f"stored card_sha {case['card_sha']} but the stored rows hash to {rebuilt}"
            )
        outcome = outcomes.get(case["case_id"])
        if outcome and outcome["card_sha_at_open"] != case["card_sha"]:
            fail(subject, "outcome row carries a different card hash than the open")
        prospective = case["call_type"] == "PROSPECTIVE"
        eval_rows = ledger.rows(
            "SELECT * FROM detector_evaluations WHERE case_id = ?", (case["case_id"],)
        )
        if version in ("KOD-CARD-v2", CARD_HASH_VERSION):
            late = [r["detector"] for r in eval_rows if r["recorded_at"] != case["opened_at"]]
            if late:
                fail(subject, f"detector evaluations recorded after the open: {late}")
            now_status = {(r["detector"], r["rule_version"]): r["status"] for r in evaluate(sets)}
            for r in eval_rows:
                key = (r["detector"], r["rule_version"])
                if (
                    r["rule_version"] == RULE_VERSION
                    and key in now_status
                    and now_status[key] != r["status"]
                ):
                    fail(
                        subject,
                        f"{r['detector']} {r['rule_version']} now evaluates {now_status[key]}, "
                        f"frozen {r['status']}: the rule was edited without a new version",
                    )
        if version == CARD_HASH_VERSION:
            frozen_version = case["detector_rule_version"]
            if any(r["rule_version"] != frozen_version for r in eval_rows):
                fail(
                    subject,
                    "an evaluation carries a rule version other than the one frozen in the card",
                )
            if detector_versions.get(frozen_version) != case["detector_code_sha256"]:
                fail(
                    subject,
                    f"frozen detector code {case['detector_code_sha256'][:12]} is not the source bound "
                    f"to {frozen_version}",
                )
            for problem in ev.citation_problems(
                sets, objects, case["integrity_level"], parse_ts(case["opened_at"])
            ):
                fail(subject, problem)
        elif version == "KOD-CARD-v2":
            for problem in evidence_problems(sets, evidence_rows, require_all=prospective):
                fail(subject, problem)
        elif prospective:
            warn(
                subject,
                "prospective card opened before evaluations were frozen into the hash; it is not scored",
            )
        for problem in check_horizon_offsets(case["decision_cutoff"], sets):
            (fail if prospective else warn)(subject, problem)
        if prospective:
            if version is None or not case.get("outcome_window_start"):
                fail(subject, "prospective case was opened without a pre-registered outcome window")
            else:
                opened = parse_ts(case["opened_at"])
                if abs(opened - parse_ts(case["decision_cutoff"])) > OPEN_TOLERANCE:
                    fail(subject, "opened more than 1 hour from its decision cutoff")
                if opened >= parse_ts(case["outcome_window_start"]):
                    fail(subject, "opened after its outcome window started")
                if outcome and parse_ts(outcome["closed_at"]) < parse_ts(
                    case["outcome_window_end"]
                ):
                    fail(subject, "closed before its outcome window ended")
        check_anchor(
            "CASE",
            case["case_id"],
            rebuilt,
            case["opened_at"],
            required=prospective,
            decision_cutoff=case["decision_cutoff"] if prospective else None,
            deadline=case.get("outcome_window_start") if prospective else None,
        )
        if prospective:
            _report_eligibility(subject, eligibility[case["case_id"]], fail, warn, stats)

    scan_outcomes = {r["entry_id"]: dict(r) for r in ledger.rows("SELECT * FROM scan_outcomes")}
    for scan in ledger.rows("SELECT * FROM scan_runs ORDER BY scanned_at, scan_id"):
        scan = dict(scan)
        stats["scans"] += 1
        subject = f"scan {scan['scan_id']}"
        version = scan.get("scan_hash_version")
        entry_shas = {}
        for row in ledger.rows("SELECT * FROM scan_entries WHERE scan_id = ?", (scan["scan_id"],)):
            stats["scan_entries"] += 1
            evals = ledger.rows(
                "SELECT * FROM scan_evaluations WHERE entry_id = ?", (row["entry_id"],)
            )
            if version in ("KOD-SCAN-v2", "KOD-SCAN-v3") and any(
                e["recorded_at"] != row["recorded_at"] for e in evals
            ):
                fail(subject, f"entry {row['symbol']} has evaluations recorded after the scan")
            body = freeze_scan_entry(
                scan["scan_id"],
                {
                    "symbol": row["symbol"],
                    "venue": row["venue"],
                    "flagged": bool(row["flagged"]),
                    "reconstruction_status": row["reconstruction_status"],
                    "facts": json.loads(row["facts_json"]),
                },
                frozen_evaluations(evals),
                version,
            )
            sha = sha256_obj(body)
            if sha != row["entry_sha"]:
                fail(subject, f"entry {row['symbol']} does not hash to its stored entry_sha")
            entry_shas[row["entry_id"]] = sha
            outcome = scan_outcomes.get(row["entry_id"])
            if outcome:
                if outcome["scan_sha_at_scan"] != scan["scan_sha"]:
                    fail(subject, f"outcome for {row['symbol']} carries a different scan hash")
                if parse_ts(outcome["closed_at"]) < parse_ts(scan["outcome_window_end"]):
                    fail(
                        subject, f"outcome for {row['symbol']} was recorded before the window ended"
                    )
        if len(entry_shas) != scan["n_entries"]:
            fail(
                subject,
                f"scan_runs says {scan['n_entries']} entries, ledger holds {len(entry_shas)}",
            )
        rebuilt = sha256_obj(freeze_scan(scan, entry_shas, version))
        if rebuilt != scan["scan_sha"]:
            fail(
                subject, f"stored scan_sha {scan['scan_sha']} but the stored rows hash to {rebuilt}"
            )
        if (
            version == "KOD-SCAN-v3"
            and detector_versions.get(scan["rule_version"]) != scan["detector_code_sha256"]
        ):
            fail(subject, "frozen detector code is not the source bound to the scan's rule version")
        scanned = parse_ts(scan["scanned_at"])
        if abs(scanned - parse_ts(scan["decision_cutoff"])) > OPEN_TOLERANCE:
            fail(subject, "logged more than 1 hour from its decision cutoff")
        if scanned >= parse_ts(scan["outcome_window_start"]):
            fail(subject, "logged after its outcome window started")
        check_anchor(
            "SCAN",
            scan["scan_id"],
            rebuilt,
            scan["scanned_at"],
            required=True,
            decision_cutoff=scan["decision_cutoff"],
            deadline=scan["outcome_window_start"],
        )
        _report_eligibility(
            subject, eligibility[("SCAN", scan["scan_id"])], fail, warn, stats, scan=True
        )

    for kind, record_id in anchors:
        fail(f"{kind.lower()} {record_id}", "anchors row has no ledger record")

    # The other direction: every call anchored in git must still be in the ledger. Without this a
    # losing case could be deleted from the database (rows and triggers) and simply vanish.
    if anchor is not None:
        present = {
            ("CASE", r["case_id"]): r["card_sha"]
            for r in ledger.rows("SELECT case_id, card_sha FROM cases")
        }
        present.update(
            {
                ("SCAN", r["scan_id"]): r["scan_sha"]
                for r in ledger.rows("SELECT scan_id, scan_sha FROM scan_runs")
            }
        )
        for kind, name in REGISTRY_FILES.items():
            for rec in anchor.committed_records("HEAD", anchor.rel(anchor.registry_dir / name)):
                if rec.get("kind") != kind:
                    continue
                key = (kind, rec.get("record_id"))
                if key not in present:
                    fail(
                        f"{kind.lower()} {rec.get('record_id')}",
                        f"anchored in git ({name}) but missing from the ledger",
                    )
                elif present[key] != rec.get("sha256"):
                    fail(
                        f"{kind.lower()} {rec.get('record_id')}",
                        f"ledger hash differs from the one anchored in {name}",
                    )

    return {
        "ok": not any(f["level"] == "FAIL" for f in findings),
        "stats": stats,
        "findings": findings,
        "eligibility": {str(k): v["status"] for k, v in eligibility.items()},
    }


def _report_eligibility(subject, judged, fail, warn, stats, scan=False) -> None:
    status = judged["status"]
    if status == AUTHORITATIVE:
        stats["remote_receipts_verified"] += 1
        if not scan:
            stats["authoritative_prospective"] += 1
    elif status == MISMATCH:
        fail(subject, f"{status}: {judged['reason']}")
    elif status in (UNVERIFIED, LATE, ANCHOR_FAILED):
        warn(subject, f"{status}: {judged['reason']}; excluded from authoritative calibration")
    elif status == LEGACY and not scan:
        warn(subject, f"{status}: {judged['reason']}; excluded from authoritative calibration")


def render(result: dict) -> str:
    s = result["stats"]
    lines = [
        f"verify: {'OK' if result['ok'] else 'FAILED'}",
        f"cases {s['cases']}, scans {s['scans']} ({s['scan_entries']} entries), evidence v1 {s['evidence']}, "
        f"evidence v2 {s['evidence_v2']}, anchors verified {s['anchors_verified']}, externally timestamped "
        f"{s['anchors_externally_timestamped']}, on a remote {s['anchors_on_remote']}, GitHub receipts verified "
        f"{s['remote_receipts_verified']}, authoritative prospective cases {s['authoritative_prospective']}",
    ]
    for f in result["findings"]:
        lines.append(f"{f['level']} {f['subject']}: {f['message']}")
    return "\n".join(lines)
