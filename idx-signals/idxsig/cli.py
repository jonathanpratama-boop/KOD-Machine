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
    p_fu = sub.add_parser("fetch-us", help="Nasdaq Trader listing + Yahoo daily bars for every US common stock")
    p_fu.add_argument("--start", default="2020-01-01")
    p_fb = sub.add_parser("fetch-binance", help="Binance spot daily klines for every USDT pair (delisted included)")
    p_fb.add_argument("--start", default="2020-01-01")
    p_ua = sub.add_parser("us-actions", help="US split schedule from a Yahoo pull, each event checked against SEC")
    p_ua.add_argument("--raw-manifest", required=True)
    p_ua.add_argument("--effective-after", required=True, help="events effective on a later session (ISO date)")
    p_ua.add_argument("--universe-end", required=True, help="names whose first bar is on or before this date")
    p_ua.add_argument("--user-agent", default=None,
                      help="SEC asks for a contact in the User-Agent (default: $IDXSIG_SEC_USER_AGENT)")
    p_ua.add_argument("--cache-dir", help="reuse a cache of SEC responses (data/raw/sec/<stamp>)")
    p_ua.add_argument("--offline", action="store_true", help="answer only from --cache-dir")
    p_ua.add_argument("--recheck", help="an earlier us_splits-*.json: re-search only its unaccepted split rows, wider")
    p_rp = sub.add_parser("build-us-repair-panel", help="E2-US repair panel: causal preprocessing, as-traded "
                                                         "unit factors, retrospective QA flags")
    p_rp.add_argument("--manifest", required=True, help="the original yahoo_us raw manifest")
    p_rp.add_argument("--schedule", required=True, help="a us_splits-*.json manifest from us-actions")
    p_rp.add_argument("--end", required=True, help="read nothing after this date into the panel")
    p_rp.add_argument("--coverage", help="a us_splits-coverage-*.json manifest from us-coverage")
    p_sh = sub.add_parser("us-share-check", help="corroborate post-window split records with SEC cover-page share counts")
    p_sh.add_argument("--schedule", required=True, help="a us_splits-*.json from the current text verifier")
    p_sh.add_argument("--raw-manifest", required=True)
    p_sh.add_argument("--window-end", required=True)
    p_sh.add_argument("--user-agent", default=None)
    p_sh.add_argument("--cache-dir")
    p_sh.add_argument("--offline", action="store_true")
    p_uc = sub.add_parser("us-coverage", help="search SEC for splits the provider did not record (large jumps)")
    p_uc.add_argument("--raw-manifest", required=True)
    p_uc.add_argument("--start", required=True)
    p_uc.add_argument("--end", required=True)
    p_uc.add_argument("--user-agent", default=None)
    p_uc.add_argument("--cache-dir")
    p_uc.add_argument("--offline", action="store_true")
    p_gp = sub.add_parser("build-global-panel", help="build a US or crypto panel from a pull manifest")
    p_gp.add_argument("--market", choices=("US", "CRYPTO"), required=True)
    p_gp.add_argument("--manifest", required=True)
    p_ca = sub.add_parser("build-ca-registry", help="classify every reference reset in the panel (new registry file)")
    p_ca.add_argument("--panel", help="panel manifest (default: latest)")
    sub.add_parser("rules", help="list rules and their state")
    p_run = sub.add_parser("run", help="run a rule over the full universe vs random entries")
    p_run.add_argument("--rule", required=True)
    p_run.add_argument("--market", choices=("IDX", "US", "CRYPTO", "CRYPTO_CLOSE"), default="IDX",
                       help="market profile (lots, costs, price limits, entry at open or close); CRYPTO_CLOSE is the "
                            "crypto profile with entry at the close of t+1 (E5 latency-pessimistic sensitivity)")
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
    p_run.add_argument("--ca-mode", choices=("registry", "exclude", "value_preserving", "adjusted"), default="registry",
                       help="registry (default): scale shares only through verified splits / stock dividends; "
                            "exclude, value_preserving: earlier modes, for reproducing older runs")
    p_run.add_argument("--ca-registry", help="corporate-action registry manifest (default: latest)")
    p_run.add_argument("--controls-version", choices=("v2", "v1", "v3"), default="v2",
                       help="matched-control features (v1 reproduces runs before hardening v2; v3 adds a volatility "
                            "quintile ahead of market_cap, E5)")
    p_run.add_argument("--lookahead-cuts", type=int,
                       help="sample N prefixes instead of the exhaustive check (faster, not a proof)")
    p_run.add_argument("--panel", help="panel manifest (default: latest)")
    p_run.add_argument("--allow-dirty", action="store_true", help="record a run from uncommitted code (flagged)")
    p_run.add_argument("--no-commit", action="store_true", help="write the run but do not git-commit it")
    p_run.add_argument("--units", choices=("panel", "as_traded"), default="panel",
                       help="as_traded: sizing, cost tiers and price bands at the price traded that session "
                            "(needs a repair panel with unit_factor)")
    p_run.add_argument("--fill-model", choices=("A", "B", "C"), default="A",
                       help="A: original (entry-session final volume, ex post); B: decision-time capacity "
                            "(open entries); C: FILL-C-v1, decision-time capacity for closing-auction entries")
    p_run.add_argument("--entry-rule", choices=("fixed", "confirm", "pullback", "unlock"),
                       help="execution plan entry (default: the rule's frozen plan, else fixed)")
    p_run.add_argument("--entry-window", type=int, help="sessions after the signal a conditional entry may trigger")
    p_run.add_argument("--exit-rule", choices=("fixed", "stop_ref", "first_down"),
                       help="execution plan exit (default: the rule's frozen plan, else fixed)")
    p_run.add_argument("--side", choices=("long", "short"),
                       help="execution plan side (default: the rule's frozen plan, else long); short needs an "
                            "open-entry market profile (US, CRYPTO)")
    p_run.add_argument("--holdout-final", action="store_true",
                       help="the one pre-registered IDX holdout evaluation (otherwise the holdout is refused)")
    p_run.add_argument("--quarantine", choices=("none", "unit_schedule"), default="none",
                       help="unit_schedule: leave out names whose split records SEC does not corroborate")
    sub.add_parser("verify-runs", help="check that no past run was edited or removed")
    sub.add_parser("e1-discovery", help="experiment E1, discovery period (writes research/E1/discovery/)")
    p_ps = sub.add_parser("paper-scan", help="prospective paper scan of the session that last closed (no orders)")
    p_ps.add_argument("--manifest", help="a recent-bars manifest for the market (default: pull now)")
    p_ps.add_argument("--commit", action="store_true", help="commit the records and push (GitHub receipt)")
    p_sc = sub.add_parser("paper-score", help="score paper decisions whose window has ended")
    p_sc.add_argument("--manifest", help="a recent-bars manifest for the market (default: pull now)")
    p_sc.add_argument("--commit", action="store_true")
    p_sc.add_argument("--rescore", action="append", default=[], metavar="DECISION_ID",
                      help="score again and append as a revision linked to the earlier outcome (needs --reason)")
    p_sc.add_argument("--reason", help="why the earlier outcome is revised")
    for p_ in (p_ps, p_sc):
        p_.add_argument("--market", choices=("IDX", "US", "CRYPTO"), default="IDX")
    sub.add_parser("paper-verify", help="check the paper ledger's hash chain and timestamp tokens")
    for name, helptext in (("e3-reproduce", "experiment E3 precondition: re-run the recorded E1 trading runs on E3's data"),
                           ("e3-discovery", "experiment E3 discovery: every (detector, plan) pair through the harness"),
                           ("e3-validation", "experiment E3 validation: the frozen pair on 2023, as a recorded run")):
        p_e3 = sub.add_parser(name, help=helptext)
        if name == "e3-discovery":
            p_e3.add_argument("--accept-deviation", action="store_true",
                              help="proceed although a precondition run did not reproduce identically (recorded)")
    for name, helptext in (("e4-reproduce", "experiment E4 precondition: re-run the recorded E2 trading run on E4's data"),
                           ("e4-discovery", "experiment E4 discovery: every (detector, plan) pair, short side"),
                           ("e4-validation", "experiment E4 validation: the frozen pair on 2023, as a recorded run")):
        p_e4 = sub.add_parser(name, help=helptext)
        p_e4.add_argument("--market", choices=("CRYPTO", "US"), default="CRYPTO")
        p_e4.add_argument("--protocol", choices=("v1", "v2"), default="v1", help="research/E4 protocol version")
        if name == "e4-discovery":
            p_e4.add_argument("--accept-deviation", action="store_true",
                              help="proceed although the precondition run did not reproduce identically (recorded)")
    for name, helptext in (("e5-reproduce", "experiment E5 precondition: re-run the market's recorded run on E5's panel"),
                           ("e5-discovery", "experiment E5 discovery: stage 1 (information) then stage 2 (execution)"),
                           ("e5-freeze", "experiment E5 freeze: write discovery/model.json into moonshot_e5.py literals"),
                           ("e5-validation", "experiment E5 validation: the frozen arms on 2023, as recorded runs")):
        p_e5 = sub.add_parser(name, help=helptext)
        p_e5.add_argument("--market", choices=("IDX", "US", "CRYPTO"), required=True,
                          help="CRYPTO_CLOSE is reached as a sensitivity inside CRYPTO, never as a market here")
        p_e5.add_argument("--protocol", choices=("v1", "v1.1"), default="v1",
                          help="research/E5/protocol.json (v1, frozen) or research/E5/v1.1/protocol.json (the audit "
                               "addendum); stage outputs go under the protocol's directory")
        if name == "e5-discovery":
            p_e5.add_argument("--accept-deviation", action="store_true",
                              help="proceed although the precondition run deviates beyond the accepted tolerance "
                                   "(both sides on record)")
    for name, helptext in (("e2-discovery", "experiment E2 discovery for one market"),
                           ("e2-validation", "experiment E2 validation of a market's frozen detector")):
        p_e2 = sub.add_parser(name, help=helptext)
        p_e2.add_argument("--market", choices=("US", "CRYPTO"), required=True)
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
    elif args.cmd == "fetch-us":
        from .sources import us_universe, yahoo

        tickers, universe = us_universe.fetch()
        print(universe)
        print(yahoo.fetch(tickers, prefix="yahoo_us", suffix="", start=args.start, sleep=0.1, workers=6))
    elif args.cmd == "fetch-binance":
        from .sources import binance

        print(binance.fetch(start=args.start))
    elif args.cmd == "us-actions":
        import os

        from . import us_actions

        agent = args.user_agent or os.environ.get("IDXSIG_SEC_USER_AGENT")
        if not agent:
            print("error: set --user-agent or IDXSIG_SEC_USER_AGENT (SEC requires a contact)", file=sys.stderr)
            return 2
        print(us_actions.build_schedule(Path(args.raw_manifest), agent, args.effective_after, args.universe_end,
                                        Path(args.cache_dir) if args.cache_dir else None, args.offline,
                                        recheck=Path(args.recheck) if args.recheck else None))
    elif args.cmd == "build-us-repair-panel":
        from . import global_panel

        print(global_panel.build_us_repair(Path(args.manifest), Path(args.schedule), args.end,
                                           Path(args.coverage) if args.coverage else None))
    elif args.cmd == "us-share-check":
        import os

        from . import us_actions

        agent = args.user_agent or os.environ.get("IDXSIG_SEC_USER_AGENT")
        if not agent:
            print("error: set --user-agent or IDXSIG_SEC_USER_AGENT (SEC requires a contact)", file=sys.stderr)
            return 2
        print(us_actions.build_share_corroboration(Path(args.schedule), Path(args.raw_manifest), args.window_end, agent,
                                                   Path(args.cache_dir) if args.cache_dir else None, args.offline))
    elif args.cmd == "us-coverage":
        import os

        from . import us_actions

        agent = args.user_agent or os.environ.get("IDXSIG_SEC_USER_AGENT")
        if not agent:
            print("error: set --user-agent or IDXSIG_SEC_USER_AGENT (SEC requires a contact)", file=sys.stderr)
            return 2
        print(us_actions.build_coverage(Path(args.raw_manifest), agent, args.start, args.end,
                                        Path(args.cache_dir) if args.cache_dir else None, args.offline))
    elif args.cmd == "build-global-panel":
        from . import global_panel

        print(global_panel.build(args.market, Path(args.manifest)))
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
        from .backtest import HoldoutSealed, RunConfig, run
        from .panel import load
        from .provenance import sha256_file
        from .results import DirtyTreeError, write_run

        try:
            rules.get(args.rule)
        except rules.RuleNotProvided as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.market == "IDX":
            df, meta, manifest = load(Path(args.panel) if args.panel else None)
            meta["_manifest_sha256"] = sha256_file(manifest)
        else:
            from . import global_panel
            from .profiles import PROFILES

            prof = PROFILES[args.market]
            # a profile variant (CRYPTO_CLOSE) shares its market's panel: load by the profile's market, not its key
            df, meta = global_panel.load(Path(args.panel) if args.panel else global_panel.latest(prof.market))
            args.ca_mode, args.notional, args.fee_buy, args.fee_sell = "adjusted", prof.notional, prof.fee_buy, prof.fee_sell
        cfg = RunConfig(market=args.market,
            rule_id=args.rule, start=args.start, end=args.end, holding_days=args.holding_days,
            entry_lag=args.entry_lag, notional=args.notional, max_participation=args.max_participation,
            fee_buy=args.fee_buy, fee_sell=args.fee_sell, overlap=args.overlap, random_draws=args.draws,
            seed=args.seed, data_end_exit=args.data_end_exit, ca_mode=args.ca_mode,
            lookahead_cuts=args.lookahead_cuts, controls_version=args.controls_version,
            units=args.units, fill_model=args.fill_model, quarantine=args.quarantine,
            entry_rule=args.entry_rule, entry_window=args.entry_window, exit_rule=args.exit_rule, side=args.side,
            holdout_final=args.holdout_final,
        )
        registry = None
        if args.ca_mode == "registry" and args.market == "IDX":
            from . import corporate_actions

            try:
                registry = corporate_actions.load(Path(args.ca_registry) if args.ca_registry else None,
                                                  panel_sha256=meta["sha256"])
            except (FileNotFoundError, corporate_actions.RegistryMismatch) as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
        try:
            output = run(cfg, df, meta, ca_registry=registry)
        except HoldoutSealed as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
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
    elif args.cmd in ("e3-reproduce", "e3-discovery", "e3-validation"):
        from . import corporate_actions, e3
        from .panel import load
        from .provenance import MANIFESTS
        from .results import code_state

        proto, proto_sha = e3.protocol()
        if code_state()["dirty"]:
            print("error: commit idxsig/ first so the results name the code that produced them", file=sys.stderr)
            return 2
        if "PENDING" in proto["data"]["panel_manifest"] or "PENDING" in proto["data"]["registry_manifest"]:
            print("error: research/E3/protocol.json does not name its panel and registry manifests yet", file=sys.stderr)
            return 2
        try:
            df, meta, _ = load(MANIFESTS / proto["data"]["panel_manifest"])
            registry = corporate_actions.load(MANIFESTS / proto["data"]["registry_manifest"], panel_sha256=meta["sha256"])
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        stage = args.cmd.split("-", 1)[1]
        try:
            if stage == "reproduce":
                result = e3.run_reproduce(df, meta, registry, e3.E3_DIR / "reproduce", proto, proto_sha)
            elif stage == "discovery":
                result = e3.run_discovery(df, meta, registry, e3.E3_DIR / "discovery", proto, proto_sha,
                                          accept_deviation=args.accept_deviation)
            else:
                result = e3.run_validation(df, meta, registry, e3.E3_DIR / "validation", proto, proto_sha)
        except (RuntimeError, FileExistsError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, default=str))
    elif args.cmd in ("e4-reproduce", "e4-discovery", "e4-validation"):
        from . import e4, global_panel
        from .provenance import MANIFESTS
        from .results import code_state

        proto, proto_sha = e4.protocol(version=args.protocol)
        if code_state()["dirty"]:
            print("error: commit idxsig/ first so the results name the code that produced them", file=sys.stderr)
            return 2
        mk = args.market
        if mk not in proto["markets"] or "PENDING" in proto["markets"][mk]["panel_manifest"]:
            print(f"error: research/E4/protocol.json does not name a panel manifest for {mk}", file=sys.stderr)
            return 2
        try:
            df, meta = global_panel.load(MANIFESTS / proto["markets"][mk]["panel_manifest"])
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        stage = args.cmd.split("-", 1)[1]
        out = e4.market_dir(mk, args.protocol) / stage
        try:
            if stage == "reproduce":
                result = e4.run_reproduce(df, meta, out, proto, proto_sha, mk)
            elif stage == "discovery":
                result = e4.run_discovery(df, meta, out, proto, proto_sha, mk, accept_deviation=args.accept_deviation)
            else:
                result = e4.run_validation(df, meta, out, proto, proto_sha, mk)
        except (RuntimeError, FileExistsError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, default=str))
    elif args.cmd in ("e5-reproduce", "e5-discovery", "e5-freeze", "e5-validation"):
        from . import e5
        from .provenance import MANIFESTS
        from .results import code_state

        e5.use_protocol(e5.E5_DIR / "protocol.json" if args.protocol == "v1" else e5.E5_DIR / args.protocol / "protocol.json")
        proto, proto_sha = e5.protocol()
        if code_state()["dirty"]:
            print("error: commit idxsig/ first so the results name the code that produced them", file=sys.stderr)
            return 2
        mk = args.market
        stage = args.cmd.split("-", 1)[1]
        out = e5.stage_dir(mk, stage)
        try:
            if stage == "freeze":
                result = e5.run_freeze(out, proto, proto_sha, mk)
            else:
                spec = proto["markets"][mk]
                if "PENDING" in spec["panel_manifest"]:
                    print(f"error: research/E5/protocol.json does not name a panel manifest for {mk}", file=sys.stderr)
                    return 2
                registry = None
                if mk == "IDX":
                    from . import corporate_actions
                    from .panel import load
                    from .provenance import sha256_file

                    df, meta, manifest = load(MANIFESTS / spec["panel_manifest"])
                    meta["_manifest"] = manifest.name
                    meta["_manifest_sha256"] = sha256_file(manifest)
                    registry = corporate_actions.load(MANIFESTS / spec["registry_manifest"], panel_sha256=meta["sha256"])
                else:
                    from . import global_panel

                    df, meta = global_panel.load(MANIFESTS / spec["panel_manifest"])
                if stage == "reproduce":
                    result = e5.run_reproduce(df, meta, registry, out, proto, proto_sha, mk)
                elif stage == "discovery":
                    result = e5.run_discovery(df, meta, registry, out, proto, proto_sha, mk,
                                              accept_deviation=args.accept_deviation)
                else:
                    result = e5.run_validation(df, meta, registry, out, proto, proto_sha, mk)
        except (RuntimeError, FileExistsError, FileNotFoundError, ValueError, KeyError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, default=str))
    elif args.cmd in ("e2-discovery", "e2-validation"):
        from . import e1, global_panel
        from .profiles import PROFILES
        from .results import code_state
        from .rules import moonshot_g

        proto_path = e1.PKG_ROOT / "research" / "E2" / "protocol.json"
        proto, _ = e1.protocol(proto_path)
        manifest = global_panel.MANIFESTS / proto["markets"][args.market]["panel_manifest"]
        if code_state()["dirty"]:
            print("error: commit idxsig/ first so the results name the code that produced them", file=sys.stderr)
            return 2
        df, meta = global_panel.load(manifest)
        study = e1.Study(df, meta, protocol_path=proto_path, profile=PROFILES[args.market], family_module=moonshot_g)
        out = e1.PKG_ROOT / "research" / "E2" / args.market
        if args.cmd == "e2-discovery":
            print(json.dumps(e1.run_discovery(study, out / "discovery"), indent=2))
        else:
            rule = moonshot_g.selected(args.market)
            if rule is None:
                print(f"error: no frozen detector for {args.market} (moonshot_g.SELECTED)", file=sys.stderr)
                return 2
            print(json.dumps(e1.run_validation(study, rule, out / "validation"), indent=2, default=str))
    elif args.cmd in ("paper-scan", "paper-score"):
        import os

        from . import paper

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        mk = args.market
        manifest = Path(args.manifest) if args.manifest else None
        extra = []
        if args.cmd == "paper-score" and manifest is None:
            due = paper.due(mk, rescore={d: "" for d in args.rescore})
            if not due:
                print(f"no {mk} decision can have completed its window yet; nothing pulled, nothing recorded")
                return 0
            print(f"{len(due)} {mk} decision(s) due: pulling bars")
        if manifest is None:
            from datetime import date, timedelta

            from .provenance import MANIFESTS
            from .sources import binance, us_universe, yahoo

            if mk == "IDX":
                manifest = yahoo.fetch(paper.active_tickers(), days=paper.HISTORY_DAYS, prefix="yahoo_recent")
            elif mk == "US":
                tickers, universe = us_universe.fetch()
                extra.append(MANIFESTS / universe)
                manifest = yahoo.fetch(tickers, days=paper.HISTORY_DAYS, prefix="yahoo_us_recent", suffix="",
                                       sleep=0.1, workers=6)
            else:
                start = (date.today() - timedelta(days=paper.HISTORY_DAYS)).isoformat()
                manifest = binance.fetch(start=start, only_trading=True, prefix="binance_recent")
        stamper = RFC3161Timestamper()
        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "paper-scan":
            out = paper.scan(manifest, validation=paper.validation_evidence(mk), market=mk,
                             quotes=paper.binance_quotes if mk == "CRYPTO" else None)
            if paper.already_scanned(out["scan"]["session"], mk):
                print(f"{mk} session {out['scan']['session']} is already scanned (no new session since: holiday or "
                      f"data not yet updated); nothing recorded")
                return 0
            written = paper.record_scan(out, stamper)
            print(json.dumps({k: out["scan"][k] for k in ("scan_id", "session", "result", "candidates_ranked")}, indent=2))
            for dcs in out["decisions"]:
                print(f"  #{dcs['rank']} {dcs['instrument']['ticker']}: {dcs['decision']} ({dcs['reason']})")
            message = f"paper scan {out['scan']['scan_id']}: {out['scan']['result']}"
        else:
            if args.rescore and not args.reason:
                print("error: --rescore needs --reason", file=sys.stderr)
                return 2
            verify = None
            if mk == "US":
                from . import us_actions
                from .provenance import RAW, utc_stamp as _stamp

                client = us_actions.SecClient(os.environ.get("IDXSIG_SEC_USER_AGENT", us_actions.DEFAULT_USER_AGENT),
                                              RAW / "sec" / _stamp().replace("-", "").replace(":", ""))
                ciks = {}

                def verify(ev):
                    if not ciks:
                        ciks.update(us_actions.cik_map(client))
                    res = us_actions.verify_event(client, ciks, ev.ticker, ev.effective_session, ev.numerator,
                                                  ev.denominator, ev.kind)
                    return res["status"], res["evidence"]
            written, outcomes = paper.score_pending(manifest, stamper, market=mk, verify=verify,
                                                    rescore={d: args.reason for d in args.rescore})
            n_bad = sum(o.get("status") == "UNSCORABLE" for o in outcomes)
            print(f"scored {len(outcomes) - n_bad} decision(s), {n_bad} unscorable")
            for o in outcomes:
                print(f"  {o['decision_id']}: {o.get('status')} {o.get('decision_verdict') or o.get('reason')}")
            message = f"paper score {mk}: {len(outcomes)} outcome(s), {n_bad} unscorable"
        if args.commit and written:
            print(paper.commit_and_push([*written, manifest, *extra], message, trailer))
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
