"""Local launch, deterministic demo, bounded refresh and recovery commands."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def default_data_dir() -> Path:
    return Path(os.environ.get("KOD_WORKSTATION_DATA_DIR",
                               str(Path(__file__).resolve().parents[3] / "runtime" / "workstation")))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m kod.workstation",
                                 description="Local single-user analyst workstation. No orders or paid model calls.")
    sub = ap.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("demo", "Replay four preserved real company releases offline"),
        ("serve", "Start the local research interface"),
        ("refresh", "Explicitly refresh recent SEC filings for the watchlist"),
        ("backup", "Create a consistent backup in a new directory"),
        ("restore", "Restore a backup into a new data directory"),
    ):
        parser = sub.add_parser(name, help=help_text)
        parser.add_argument("--data-dir", type=Path, default=default_data_dir())
        if name == "serve":
            parser.add_argument("--port", type=int, default=8765)
            parser.add_argument("--offline", action="store_true")
        if name == "demo":
            parser.add_argument("--serve", action="store_true", help="Start the offline interface after replay")
            parser.add_argument("--port", type=int, default=8765)
        if name == "refresh":
            parser.add_argument("--ticker", help="Optional one existing watchlist ticker")
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
        service = ResearchService(store)
        if args.command == "backup":
            print("Backup created:", store.backup(args.to))
        elif args.command == "refresh":
            from .sources import refresh_security
            selected = [s for s in store.securities() if not args.ticker or s["ticker"] == args.ticker.upper()]
            if not selected:
                raise ValueError("No matching watchlist company; add one in the application first.")
            success = True
            for security in selected:
                job = refresh_security(service, security["id"])
                success = success and job["status"] == "success"
                print(json.dumps({"ticker": security["ticker"], "status": job["status"], "message": job["message"]}))
            return 0 if success else 2
        elif args.command == "demo":
            from .demo import seed_demo
            notes = seed_demo(service)
            print(f"Replayed {len(notes)} historical notes. Data directory: {store.root}")
            for note in notes:
                print("  note/" + note["id"])
            if not args.serve:
                print("Open with: python3 -m kod.workstation serve --offline --data-dir " + str(store.root))
                return 0
        if args.command == "serve" or (args.command == "demo" and args.serve):
            if not 1024 <= args.port <= 65535:
                raise ValueError("Choose a local port from 1024 to 65535.")
            try:
                import uvicorn
                from .web import create_app
            except ImportError as exc:
                raise ValueError("Install optional workstation dependencies: python3 -m pip install -r requirements-workstation.txt") from exc
            offline = args.command == "demo" or args.offline
            print(f"KOD Workstation: http://127.0.0.1:{args.port} · " + ("offline" if offline else "explicit SEC refresh enabled"))
            uvicorn.run(create_app(store.root, offline=offline, service=service),
                        host="127.0.0.1", port=args.port, access_log=False, log_level="warning")
        return 0
    except (ValueError, OSError) as exc:
        print("workstation error:", str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
