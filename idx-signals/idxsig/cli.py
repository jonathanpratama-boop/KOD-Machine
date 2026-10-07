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
    p_ca = sub.add_parser("build-ca-registry", help="classify every reference reset in the panel (new registry file)")
    p_ca.add_argument("--panel", help="panel manifest (default: latest)")
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
    p_run.add_argument("--ca-mode", choices=("registry", "exclude", "value_preserving"), default="registry",
                       help="registry (default): scale shares only through verified splits / stock dividends; "
                            "exclude, value_preserving: earlier modes, for reproducing older runs")
    p_run.add_argument("--ca-registry", help="corporate-action registry manifest (default: latest)")
    p_run.add_argument("--controls-version", choices=("v2", "v1"), default="v2",
                       help="matched-control features (v1 reproduces runs before hardening v2)")
    p_run.add_argument("--lookahead-cuts", type=int,
                       help="sample N prefixes instead of the exhaustive check (faster, not a proof)")
    p_run.add_argument("--panel", help="panel manifest (default: latest)")
    p_run.add_argument("--allow-dirty", action="store_true", help="record a run from uncommitted code (flagged)")
    p_run.add_argument("--no-commit", action="store_true", help="write the run but do not git-commit it")
    sub.add_parser("verify-runs", help="check that no past run was edited or removed")
    sub.add_parser("e1-discovery", help="experiment E1, discovery period (writes research/E1/discovery/)")
    p_ps = sub.add_parser("paper-scan", help="prospective paper scan of the session that last closed (no orders)")
    p_ps.add_argument("--manifest", help="a yahoo_recent manifest (default: pull now)")
    p_ps.add_argument("--commit", action="store_true", help="commit the records and push (GitHub receipt)")
    p_sc = sub.add_parser("paper-score", help="score paper decisions whose window has ended")
    p_sc.add_argument("--manifest", help="a yahoo_recent manifest (default: pull now)")
    p_sc.add_argument("--commit", action="store_true")
    sub.add_parser("paper-verify", help="check the paper ledger's hash chain and timestamp tokens")
    p_v = sub.add_parser("e1-validation", help="experiment E1, validation of the frozen detector")
    p_v.add_argument("--rule", required=True, help="must equal rules/moonshot_e1.SELECTED, committed")
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
        for manifest in sorted(MANIFESTS.glob("ca_registry-*.json")):
            from . import corporate_actions

            try:
                corporate_actions.load(manifest)
                print(f"{manifest.name}: OK")
            except (FileNotFoundError, RuntimeError) as exc:
                print(f"{manifest.name}: {exc}")
                bad += 1
        return 1 if bad else 0
    elif args.cmd == "build-ca-registry":
        from . import corporate_actions
        from .execution import Market
        from .panel import load

        df, meta, manifest = load(Path(args.panel) if args.panel else None)
        reg, summary = corporate_actions.build(Market.from_panel(df), meta)
        summary["inputs"]["panel_manifest"] = manifest.name
        path = corporate_actions.write(reg, summary)
        print(json.dumps({k: summary[k] for k in ("rows", "by_status", "by_type", "share_scaled")}, indent=2))
        print(path)
    elif args.cmd == "rules":
        from . import rules

        from .rules.audit import audit_module

        failed = 0
        for rule_id, rule in sorted(rules.registry().items()):
            problems = audit_module(rule.module)
            failed += bool(problems)
            print(f"{rule_id} {rule.version} {rule.kind} hold={rule.holding_days} sha={rule.sha256[:12]} "
                  f"source-audit={'passed' if not problems else f'FAILED ({len(problems)})'}")
            for problem in problems:
                print(f"  {problem}")
        for rule_id in rules.pending():
            print(f"{rule_id} PENDING: rule text not supplied")
        return 1 if failed else 0
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
            seed=args.seed, data_end_exit=args.data_end_exit, ca_mode=args.ca_mode,
            lookahead_cuts=args.lookahead_cuts, controls_version=args.controls_version,
        )
        registry = None
        if args.ca_mode == "registry":
            from . import corporate_actions

            try:
                registry = corporate_actions.load(Path(args.ca_registry) if args.ca_registry else None,
                                                  panel_sha256=meta["sha256"])
            except (FileNotFoundError, corporate_actions.RegistryMismatch) as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
        output = run(cfg, df, meta, ca_registry=registry)
        try:
            run_dir = write_run(output, allow_dirty=args.allow_dirty, commit=not args.no_commit)
        except DirtyTreeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print((run_dir / "REPORT.md").read_text(encoding="utf-8"))
    elif args.cmd in ("e1-discovery", "e1-validation"):
        from . import e1
        from .panel import load
        from .rules import moonshot_e1
        from .results import code_state

        df, meta, manifest = load()
        proto, _ = e1.protocol()
        if manifest.name != proto["data"]["panel_manifest"]:
            print(f"error: E1 is registered on {proto['data']['panel_manifest']}, not {manifest.name}", file=sys.stderr)
            return 2
        if code_state()["dirty"]:
            print("error: commit idxsig/ first so the results name the code that produced them", file=sys.stderr)
            return 2
        study = e1.Study(df, meta)
        if args.cmd == "e1-discovery":
            print(json.dumps(e1.run_discovery(study, e1.E1_DIR / "discovery"), indent=2))
        else:
            if moonshot_e1.SELECTED != args.rule:
                print(f"error: {args.rule} is not the frozen detector (moonshot_e1.SELECTED = "
                      f"{moonshot_e1.SELECTED})", file=sys.stderr)
                return 2
            print(json.dumps(e1.run_validation(study, args.rule, e1.E1_DIR / "validation"), indent=2, default=str))
    elif args.cmd in ("paper-scan", "paper-score"):
        import os

        from . import paper

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        manifest = Path(args.manifest) if args.manifest else None
        if manifest is None:
            from .sources import yahoo

            manifest = yahoo.fetch(paper.active_tickers(), days=paper.HISTORY_DAYS, prefix="yahoo_recent")
        stamper = RFC3161Timestamper()
        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "paper-scan":
            out = paper.scan(manifest, validation=paper.validation_evidence())
            written = paper.record_scan(out, stamper)
            print(json.dumps({k: out["scan"][k] for k in ("scan_id", "session", "result", "candidates_ranked")}, indent=2))
            for dcs in out["decisions"]:
                print(f"  #{dcs['rank']} {dcs['instrument']['ticker']}: {dcs['decision']} ({dcs['reason']})")
            message = f"paper scan {out['scan']['scan_id']}: {out['scan']['result']}"
        else:
            written, outcomes = paper.score_pending(manifest, stamper)
            print(f"scored {len(outcomes)} decision(s)")
            message = f"paper score: {len(outcomes)} outcome(s)"
        if args.commit and written:
            print(paper.commit_and_push([*written, manifest], message, trailer))
    elif args.cmd == "paper-verify":
        from . import paper

        problems = paper.verify_all()
        print("paper-verify: " + ("OK" if not problems else f"{len(problems)} problems"))
        for p_ in problems:
            print(f"  {p_}")
        return 1 if problems else 0
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
