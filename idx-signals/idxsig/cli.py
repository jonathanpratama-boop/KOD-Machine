"""CLI for the IDX signal harness."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .provenance import DATA, MANIFESTS, check_files, latest_manifest, read_manifest

EXTRA_TICKERS = DATA / "universe" / "extra_tickers.csv"


def _universe() -> list[str]:
    _, records = read_manifest(latest_manifest("idx_mirror"))
    tickers = {r["ticker"] for r in records if "ticker" in r}
    with EXTRA_TICKERS.open(newline="", encoding="utf-8") as fh:
        tickers |= {row["ticker"].strip().upper() for row in csv.DictReader(fh) if row["ticker"].strip()}
    return sorted(tickers)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="idxsig", description="IDX signal test harness. Research only.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch-idx-mirror", help="download the pinned IDX daily-summary mirror")
    p_y = sub.add_parser("fetch-yahoo", help="download Yahoo daily history for every universe ticker")
    p_y.add_argument("--out", help="raw directory (resumes if it exists)")
    sub.add_parser("build-panel", help="merge sources into the canonical panel")
    sub.add_parser("verify-data", help="re-hash every raw file and the panel against their manifests")
    sub.add_parser("rules", help="list rules and their state")
    p_run = sub.add_parser("run", help="run a rule over the full universe vs random entries")
    p_run.add_argument("--rule", required=True)
    p_run.add_argument("--start")
    p_run.add_argument("--end")
    p_run.add_argument("--holding-days", type=int)
    p_run.add_argument("--entry-lag", type=int, default=1)
    p_run.add_argument("--notional", type=float, default=10_000_000.0)
    p_run.add_argument("--max-participation", type=float, default=0.10)
    p_run.add_argument("--fee-buy", type=float, default=0.0015)
    p_run.add_argument("--fee-sell", type=float, default=0.0025)
    p_run.add_argument("--overlap", choices=("skip", "allow"), default="skip")
    p_run.add_argument("--draws", type=int, default=200)
    p_run.add_argument("--seed", type=int, default=20261007)
    p_run.add_argument("--data-end-exit", choices=("last_close", "zero"), default="last_close")
    p_run.add_argument("--panel", help="panel manifest (default: latest)")
    p_run.add_argument("--allow-dirty", action="store_true", help="record a run from uncommitted code (flagged)")
    p_run.add_argument("--no-commit", action="store_true", help="write the run but do not git-commit it")
    sub.add_parser("verify-runs", help="check that no past run was edited or removed")
    args = parser.parse_args(argv)

    if args.cmd == "fetch-idx-mirror":
        from .sources import idx_mirror

        print(idx_mirror.fetch())
    elif args.cmd == "fetch-yahoo":
        from .sources import yahoo

        out = Path(args.out) if args.out else None
        print(yahoo.fetch(_universe(), out_dir=out))
    elif args.cmd == "build-panel":
        from .panel import build

        print(build())
    elif args.cmd == "verify-data":
        bad = 0
        for manifest in sorted(MANIFESTS.glob("*.jsonl")):
            problems = check_files(manifest)
            print(f"{manifest.name}: {'OK' if not problems else f'{len(problems)} problems'}")
            for p in problems[:20]:
                print(f"  {p}")
            bad += len(problems)
        for manifest in sorted(MANIFESTS.glob("panel-*.json")):
            from .panel import load

            try:
                load(manifest)
                print(f"{manifest.name}: OK")
            except (FileNotFoundError, RuntimeError) as exc:
                print(f"{manifest.name}: {exc}")
                bad += 1
        return 1 if bad else 0
    elif args.cmd == "rules":
        from . import rules

        for rule_id, rule in sorted(rules.registry().items()):
            print(f"{rule_id} {rule.version} {rule.kind} hold={rule.holding_days} sha={rule.sha256[:12]}")
        for rule_id in rules.pending():
            print(f"{rule_id} PENDING: rule text not supplied")
    elif args.cmd == "run":
        from . import rules
        from .backtest import RunConfig, run
        from .panel import load
        from .provenance import sha256_file
        from .results import DirtyTreeError, write_run

        try:
            rules.get(args.rule)
        except rules.RuleNotProvided as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        df, meta, manifest = load(Path(args.panel) if args.panel else None)
        meta["_manifest_sha256"] = sha256_file(manifest)
        cfg = RunConfig(
            rule_id=args.rule, start=args.start, end=args.end, holding_days=args.holding_days,
            entry_lag=args.entry_lag, notional=args.notional, max_participation=args.max_participation,
            fee_buy=args.fee_buy, fee_sell=args.fee_sell, overlap=args.overlap, random_draws=args.draws,
            seed=args.seed, data_end_exit=args.data_end_exit,
        )
        output = run(cfg, df, meta)
        try:
            run_dir = write_run(output, allow_dirty=args.allow_dirty, commit=not args.no_commit)
        except DirtyTreeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print((run_dir / "REPORT.md").read_text(encoding="utf-8"))
    elif args.cmd == "verify-runs":
        from .results import verify_runs

        problems = verify_runs()
        print("verify-runs: " + ("OK" if not problems else f"{len(problems)} problems"))
        for p in problems:
            print(f"  {p}")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
