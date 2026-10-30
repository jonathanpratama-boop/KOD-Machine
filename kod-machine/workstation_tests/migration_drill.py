"""Migration and recovery drill on a real populated v1 workspace, through the command line.

    python3 workstation_tests/migration_drill.py --v1 <v1 workspace directory> --work <empty scratch directory>

The v1 workspace is copied first and never touched. On the copy: upgrade (the 'reindex' command opens and migrates it), check that every v1 security,
document, object hash, note and annotation is unchanged and still renders; add filed history, a scenario, a thesis and a decision packet; make a backup;
restore it into a new directory; check that the restored workspace holds the same records, that the packet's stored SHA-256 verifies and that it
reproduces there. Prints a JSON report and exits non-zero on any failed check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def inventory(root: Path) -> dict:
    db = sqlite3.connect(root / "workstation.sqlite3")
    try:
        q = lambda sql: [tuple(r) for r in db.execute(sql)]  # noqa: E731
        return {
            "securities": q("SELECT id, ticker, venue, cik FROM securities ORDER BY id"),
            "documents": q(
                "SELECT id, sha256, filename, source_url, published_at FROM documents ORDER BY id"
            ),
            "notes": [
                (i, hashlib.sha256(r.encode()).hexdigest(), hashlib.sha256(m.encode()).hexdigest())
                for i, r, m in q("SELECT id, result, markdown FROM notes ORDER BY id")
            ],
            "annotations": q(
                "SELECT id, note_id, thesis, invalidation, review_condition, created_at FROM annotations ORDER BY id"
            ),
            "objects": q("SELECT sha256, bytes FROM objects ORDER BY sha256"),
        }
    finally:
        db.close()


def cli(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "kod.workstation", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.work.exists() and any(args.work.iterdir()):
        raise SystemExit("--work must be empty")
    args.work.mkdir(parents=True, exist_ok=True)
    report, checks = {"steps": []}, []

    def check(name, ok, detail=None):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    source_db = sqlite3.connect(args.v1 / "workstation.sqlite3")
    report["v1_user_version"] = source_db.execute("PRAGMA user_version").fetchone()[0]
    source_db.close()
    original = inventory(args.v1)
    original_bytes = hashlib.sha256((args.v1 / "workstation.sqlite3").read_bytes()).hexdigest()
    work = args.work / "migrated"
    shutil.copytree(args.v1, work)

    upgraded = cli("reindex", "--data-dir", str(work))
    report["steps"].append(
        {
            "reindex": upgraded.stdout.strip().splitlines(),
            "exit": upgraded.returncode,
            "stderr": upgraded.stderr[-500:],
        }
    )
    check("upgrade command succeeded", upgraded.returncode == 0, upgraded.stderr[-300:])
    db = sqlite3.connect(work / "workstation.sqlite3")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    migrations = db.execute(
        "SELECT version, name FROM schema_migrations ORDER BY version"
    ).fetchall()
    observations = db.execute("SELECT COUNT(*) FROM financial_observations").fetchone()[0]
    db.close()
    from kod.workstation import migrations as migration_defs

    check("schema at the latest version", version == migration_defs.LATEST, version)
    check(
        "every migration recorded",
        [m[0] for m in migrations] == list(range(1, migration_defs.LATEST + 1)),
        migrations,
    )
    check(
        "safety copy of the v1 database kept",
        any((work / "migration-backups").glob("workstation-v1-*.sqlite3")),
    )
    check("release figures recorded as observations", observations > 0, observations)
    check("v1 records unchanged after upgrade", inventory(work) == original)
    check(
        "the v1 source workspace was not modified",
        hashlib.sha256((args.v1 / "workstation.sqlite3").read_bytes()).hexdigest()
        == original_bytes,
    )

    from fastapi.testclient import TestClient
    from kod.workstation import decisions, scenarios, thesis
    from kod.workstation.policy import DAY_END, AsOfPolicy
    from kod.workstation.services import ResearchService
    from kod.workstation.store import Store
    from kod.workstation.web import create_app

    client = TestClient(create_app(work, offline=True, testing=True))
    pages = [client.get(f"/note/{nid}").status_code for nid, *_ in original["notes"]]
    exports = [client.get(f"/note/{nid}/export.json").status_code for nid, *_ in original["notes"]]
    check(
        "v1 notes render and export",
        set(pages) == {200} and set(exports) == {200},
        {"pages": pages, "exports": exports},
    )
    client.close()

    sources = {
        (s["ticker"], s["kind"]): s
        for s in json.loads((ROOT / "examples/companyfacts/SOURCES.json").read_text())
    }
    imported = {}
    for sid, ticker, venue, cik in original["securities"]:
        facts, subs = sources.get((ticker, "companyfacts")), sources.get((ticker, "submissions"))
        if not facts:
            continue
        result = cli(
            "import-companyfacts",
            "--data-dir",
            str(work),
            "--ticker",
            ticker,
            "--companyfacts",
            str(ROOT / "examples/companyfacts" / facts["fixture"]),
            "--source-url",
            facts["url"],
            "--observed-at",
            facts["observed_at"],
            "--submissions",
            str(ROOT / "examples/companyfacts" / subs["fixture"]),
            "--submissions-url",
            subs["url"],
        )
        imported[ticker] = result.returncode
        check(f"filed history imported for {ticker}", result.returncode == 0, result.stderr[-300:])

    service = ResearchService(Store(work), clock=lambda: "2026-10-23T12:00:00Z")
    nvda = next(s for s in service.store.securities() if s["ticker"] == "NVDA")
    treat = {
        "stock_compensation": "expensed_in_margin",
        "leases": "operating_cost_in_margin",
        "convertibles": "none_outstanding",
        "noncontrolling_interests": "none",
        "tax_losses": "none_material",
    }
    version = scenarios.save_assumptions(
        service,
        nvda["id"],
        "base",
        {
            "horizon_years": 5,
            "base": {"revenue": "215938000000", "fiscal_year_end": "2026-01-25"},
            "currency": "USD",
            "valuation_date": "2026-10-23",
            "revenue_growth": "0.2",
            "operating_margin": "0.55",
            "cash_tax_rate": "0.15",
            "depreciation_rate": "0.015",
            "capex_rate": "0.03",
            "nwc_rate": "0.1",
            "discount_rate": "0.1",
            "terminal_growth": "0.03",
            "terminal_roic": "0.3",
            "treatments": treat,
        },
        "drill: illustrative assumptions",
    )
    tv = decisions.save_thesis(
        service,
        nvda["id"],
        "Drill thesis",
        "Drill statement.",
        [
            thesis.comparison(
                {"kind": "change", "key": "revenue_yoy"},
                "<",
                {"kind": "constant", "value": "20", "unit": "percent"},
                "Review if revenue growth < 20%",
            )
        ],
        "drill",
    )
    policy = AsOfPolicy.parse("2026-10-23T12:00:00Z", "observed", DAY_END)
    packet = decisions.save_packet(
        service,
        nvda["id"],
        policy,
        "as_reported",
        "Drill question",
        "drill choice",
        "drill rationale",
        tv["id"],
    )
    check(
        "packet reproduces before backup", decisions.reproduce(service, packet["id"])["reproduced"]
    )
    migrated_state = inventory(work)

    backup = cli("backup", "--data-dir", str(work), "--to", str(args.work / "backup"))
    check("backup command succeeded", backup.returncode == 0, backup.stderr[-300:])
    restored_dir = args.work / "restored"
    restore = cli("restore", "--from", str(args.work / "backup"), "--data-dir", str(restored_dir))
    check("restore command succeeded", restore.returncode == 0, restore.stderr[-300:])
    check(
        "restore refuses an existing directory",
        cli(
            "restore", "--from", str(args.work / "backup"), "--data-dir", str(restored_dir)
        ).returncode
        != 0,
    )
    check(
        "restored records equal the migrated workspace", inventory(restored_dir) == migrated_state
    )
    restored = ResearchService(Store(restored_dir), clock=lambda: "2026-10-23T12:00:00Z")
    stored = decisions.packet(restored, packet["id"])
    check(
        "packet SHA-256 verifies after restore", stored["packet_sha256"] == packet["packet_sha256"]
    )
    check(
        "packet reproduces in the restored workspace",
        decisions.reproduce(restored, packet["id"])["reproduced"],
    )
    check(
        "assumption version survives restore",
        scenarios.assumption_version(restored, version["id"])["version"] == 1,
    )
    client = TestClient(create_app(restored_dir, offline=True, testing=True))
    check(
        "restored dossier and packet pages render",
        client.get(f"/company/{nvda['id']}/dossier").status_code == 200
        and client.get(f"/packet/{packet['id']}").status_code == 200,
    )
    client.close()

    report.update(
        {
            "checks": checks,
            "passed": all(c["ok"] for c in checks),
            "counts": {k: len(v) for k, v in original.items()},
            "observations_after_upgrade": observations,
            "imported": imported,
        }
    )
    print(json.dumps(report, indent=1, default=str))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
