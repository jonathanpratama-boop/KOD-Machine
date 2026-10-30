"""Local launch, deterministic demo, bounded refresh and recovery commands."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def default_data_dir() -> Path:
    return Path(
        os.environ.get(
            "KOD_WORKSTATION_DATA_DIR",
            str(Path(__file__).resolve().parents[3] / "runtime" / "workstation"),
        )
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m kod.workstation",
        description="Local single-user analyst workstation. No orders or paid model calls.",
    )
    sub = ap.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("demo", "Replay four preserved real company releases offline"),
        ("serve", "Start the local research interface"),
        ("refresh", "Explicitly refresh recent SEC filings for the watchlist"),
        ("backup", "Create a consistent backup in a new directory"),
        ("restore", "Restore a backup into a new data directory"),
        (
            "reindex",
            "Record financial observations for preserved releases that have none from this parser version",
        ),
        (
            "import-companyfacts",
            "Import a preserved SEC companyfacts response (and optionally the submissions response) for a watchlist company",
        ),
        ("dossier", "Print a company dossier (Markdown or JSON) at an information cutoff"),
        ("search", "Search preserved sources eligible at an information cutoff"),
    ):
        parser = sub.add_parser(name, help=help_text)
        parser.add_argument("--data-dir", type=Path, default=default_data_dir())
        if name == "serve":
            parser.add_argument("--port", type=int, default=8765)
            parser.add_argument("--offline", action="store_true")
        if name == "demo":
            parser.add_argument(
                "--serve", action="store_true", help="Start the offline interface after replay"
            )
            parser.add_argument("--port", type=int, default=8765)
        if name == "refresh":
            parser.add_argument("--ticker", help="Optional one existing watchlist ticker")
            parser.add_argument(
                "--filed-history",
                action="store_true",
                help="refresh the SEC companyfacts filed history (and submissions) instead of the recent-filings list",
            )
        if name in ("dossier", "search"):
            parser.add_argument(
                "--as-of", help="information cutoff (timezone-aware ISO time); default now"
            )
            parser.add_argument("--mode", choices=("observed", "public"), default="observed")
            parser.add_argument(
                "--policy",
                choices=("day-end", "strict"),
                default="day-end",
                help="day-end: a filing date counts from the end of that day (New York); strict: exact times only",
            )
        if name == "dossier":
            parser.add_argument("--ticker", required=True)
            parser.add_argument("--view", choices=("as_reported", "latest"), default="as_reported")
            parser.add_argument("--question")
            parser.add_argument("--format", choices=("md", "json"), default="md")
        if name == "search":
            parser.add_argument("query")
            parser.add_argument("--ticker")
            parser.add_argument(
                "--period", help="a release's reported period label, e.g. 'Q3 FY25'"
            )
            parser.add_argument("--limit", type=int, default=10)
        if name == "import-companyfacts":
            parser.add_argument(
                "--ticker", required=True, help="an existing watchlist ticker with a CIK"
            )
            parser.add_argument(
                "--companyfacts",
                type=Path,
                required=True,
                help="saved response (.json or .json.gz)",
            )
            parser.add_argument(
                "--source-url", required=True, help="the data.sec.gov URL it was retrieved from"
            )
            parser.add_argument(
                "--observed-at",
                required=True,
                help="when it was actually retrieved (timezone-aware ISO time); never backdate",
            )
            parser.add_argument("--submissions", type=Path)
            parser.add_argument("--submissions-url")
        if name == "backup":
            parser.add_argument("--to", type=Path, required=True)
        if name == "restore":
            parser.add_argument("--from", dest="backup_dir", type=Path, required=True)
    args = ap.parse_args(argv)
    from .services import ResearchService
    from .store import Store

    try:
        if args.command == "restore":
            restored = Store.restore(args.backup_dir, args.data_dir)
            print("Restored into new directory:", restored.root)
            return 0
        store = Store(args.data_dir)
        if store.migration["applied"]:
            print(
                f"Upgraded the workspace schema from v{store.migration['from']} to v{store.migration['to']}; a copy of the earlier database is at "
                f"{store.migration['safety_copy'] or '(new workspace)'}"
            )
        service = ResearchService(store)
        if args.command == "reindex":
            done = service.index_documents()
            print(json.dumps(done))
            return 0 if not done["skipped"] else 2
        if args.command in ("dossier", "search", "import-companyfacts"):
            return _research_command(args, store, service)
        if args.command == "backup":
            print("Backup created:", store.backup(args.to))
        elif args.command == "refresh":
            from .sources import refresh_security

            selected = [
                s
                for s in store.securities()
                if not args.ticker or s["ticker"] == args.ticker.upper()
            ]
            if not selected:
                raise ValueError("No matching watchlist company; add one in the application first.")
            success = True
            for security in selected:
                if args.filed_history:
                    from .sources import SourceUnavailable, refresh_companyfacts

                    try:
                        job = {
                            "status": "success",
                            "message": refresh_companyfacts(service, security["id"])["message"],
                        }
                    except (SourceUnavailable, ValueError) as exc:
                        job = {"status": "failed", "message": str(exc)}
                else:
                    job = refresh_security(service, security["id"])
                success = success and job["status"] == "success"
                print(
                    json.dumps(
                        {
                            "ticker": security["ticker"],
                            "status": job["status"],
                            "message": job["message"],
                        }
                    )
                )
            return 0 if success else 2
        elif args.command == "demo":
            from .demo import seed_demo

            notes = seed_demo(service)
            print(f"Replayed {len(notes)} historical notes. Data directory: {store.root}")
            for note in notes:
                print("  note/" + note["id"])
            if not args.serve:
                print(
                    "Open with: python3 -m kod.workstation serve --offline --data-dir "
                    + str(store.root)
                )
                return 0
        if args.command == "serve" or (args.command == "demo" and args.serve):
            if not 1024 <= args.port <= 65535:
                raise ValueError("Choose a local port from 1024 to 65535.")
            try:
                import uvicorn
                from .web import create_app
            except ImportError as exc:
                raise ValueError(
                    "Install optional workstation dependencies: python3 -m pip install -r requirements-workstation.txt"
                ) from exc
            offline = args.command == "demo" or args.offline
            print(
                f"KOD Workstation: http://127.0.0.1:{args.port} · "
                + ("offline" if offline else "explicit SEC refresh enabled")
            )
            uvicorn.run(
                create_app(store.root, offline=offline, service=service),
                host="127.0.0.1",
                port=args.port,
                access_log=False,
                log_level="warning",
            )
        return 0
    except (ValueError, OSError) as exc:
        print("workstation error:", str(exc), file=sys.stderr)
        return 2


def _security(store, ticker):
    found = [s for s in store.securities() if s["ticker"] == ticker.upper()]
    if len(found) != 1:
        raise ValueError(f"no single watchlist company with ticker {ticker.upper()}")
    return found[0]


def _read(path: Path) -> bytes:
    import gzip

    raw = path.read_bytes()
    return gzip.decompress(raw) if path.suffix == ".gz" else raw


def _research_command(args, store, service) -> int:
    from .policy import DAY_END, STRICT, AsOfPolicy
    from .domain import timestamp

    if args.command == "import-companyfacts":
        sec = _security(store, args.ticker)
        coverage = service.import_companyfacts(
            sec["id"],
            _read(args.companyfacts),
            args.source_url,
            observed_at=args.observed_at,
            submissions=_read(args.submissions) if args.submissions else None,
            submissions_url=args.submissions_url,
        )
        print(
            json.dumps(
                {
                    k: coverage[k]
                    for k in (
                        "observations",
                        "added",
                        "absent_metrics",
                        "unmapped_units",
                        "business_type",
                    )
                },
                indent=1,
            )
        )
        return 0
    policy = AsOfPolicy.parse(
        timestamp(args.as_of or service.clock()),
        args.mode,
        {"day-end": DAY_END, "strict": STRICT}[args.policy],
    )
    if args.command == "dossier":
        from . import dossier

        d = dossier.build(
            service, _security(store, args.ticker)["id"], policy, args.view, args.question
        )
        print(
            json.dumps(d, indent=1, ensure_ascii=False)
            if args.format == "json"
            else dossier.render_markdown(d)
        )
        return 0
    from . import search

    result = search.search(
        store,
        service.archive,
        args.query,
        policy,
        [_security(store, args.ticker)["id"]] if args.ticker else None,
        args.period,
        limit=args.limit,
    )
    cov = result["coverage"]
    print(
        f"{cov['matches']} matches in {cov['documents_searched']} eligible sources at {policy.as_dict()['cutoff']} ({policy.mode}, {policy.policy_version}); "
        f"excluded {cov['excluded'] or 'none'}"
    )
    for r in result["results"]:
        print(
            f"- [{r['ticker']} {r['period'] or 'period unresolved'} · {r['filename']} · passage {r['passage_index']} · score {r['score']:.2f}] "
            + "".join(s["text"] for s in r["snippet"])
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
