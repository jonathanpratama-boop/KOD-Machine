"""CLI for the IDX signal harness."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .provenance import DATA, MANIFESTS, check_files, latest_manifest, read_manifest

EXTRA_TICKERS = DATA / "universe" / "extra_tickers.csv"


def _sessions_from_one(text: str) -> int:
    """argparse type for --entry-lag: whole sessions, at least 1 (execution.ExecConfig enforces the same rule)."""
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(
            f"{value} is not allowed: a trade is entered at least one session after its signal"
        )
    return value


def _universe() -> list[str]:
    _, records = read_manifest(latest_manifest("idx_mirror"))
    tickers = {r["ticker"] for r in records if "ticker" in r}
    with EXTRA_TICKERS.open(newline="", encoding="utf-8") as fh:
        tickers |= {
            row["ticker"].strip().upper() for row in csv.DictReader(fh) if row["ticker"].strip()
        }
    return sorted(tickers)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="idxsig", description="IDX signal test harness. Research only."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch-idx-mirror", help="download the pinned IDX daily-summary mirror")
    p_y = sub.add_parser(
        "fetch-yahoo", help="download Yahoo daily history for every universe ticker"
    )
    p_y.add_argument("--out", help="raw directory (resumes if it exists)")
    sub.add_parser("build-panel", help="merge sources into the canonical panel")
    sub.add_parser(
        "verify-data", help="re-hash every raw file and the panel against their manifests"
    )
    p_fu = sub.add_parser(
        "fetch-us", help="Nasdaq Trader listing + Yahoo daily bars for every US common stock"
    )
    p_fu.add_argument("--start", default="2020-01-01")
    p_fb = sub.add_parser(
        "fetch-binance", help="Binance spot daily klines for every USDT pair (delisted included)"
    )
    p_fb.add_argument("--start", default="2020-01-01")
    for command in ("coinglass-check", "coinglass-pull"):
        cg = sub.add_parser(
            command, help="optional CoinGlass API access check or hashed crypto-context snapshot"
        )
        cg.add_argument(
            "--symbol", default="BTCUSDT", help="exact futures instrument identifier from CoinGlass"
        )
        cg.add_argument("--exchange", default="Binance")
        cg.add_argument("--interval", default="4h")
        cg.add_argument(
            "--datasets",
            default="price,rsi"
            if command.endswith("check")
            else "price,open_interest,funding,liquidations,long_short,rsi,macd",
            help="comma-separated endpoint names",
        )
        if command.endswith("pull"):
            cg.add_argument(
                "--limit", type=int, default=200, help="bounded window, 1-1000 bars per endpoint"
            )
            cg.add_argument(
                "--end", help="exclusive availability cutoff with timezone; default now"
            )
    for command in ("coinglass-report", "coinglass-verify"):
        cg = sub.add_parser(
            command, help="read and verify a saved CoinGlass snapshot without a key or network"
        )
        cg.add_argument("--manifest", required=True)
        if command.endswith("report"):
            cg.add_argument(
                "--asof", help="UTC observation cutoff; cannot backdate a later retrieval"
            )
            cg.add_argument("--max-age-intervals", type=int, default=2)
    p_ua = sub.add_parser(
        "us-actions", help="US split schedule from a Yahoo pull, each event checked against SEC"
    )
    p_ua.add_argument("--raw-manifest", required=True)
    p_ua.add_argument(
        "--effective-after", required=True, help="events effective on a later session (ISO date)"
    )
    p_ua.add_argument(
        "--universe-end", required=True, help="names whose first bar is on or before this date"
    )
    p_ua.add_argument(
        "--user-agent",
        default=None,
        help="SEC asks for a contact in the User-Agent (default: $IDXSIG_SEC_USER_AGENT)",
    )
    p_ua.add_argument("--cache-dir", help="reuse a cache of SEC responses (data/raw/sec/<stamp>)")
    p_ua.add_argument("--offline", action="store_true", help="answer only from --cache-dir")
    p_ua.add_argument(
        "--recheck",
        help="an earlier us_splits-*.json: re-search only its unaccepted split rows, wider",
    )
    p_rp = sub.add_parser(
        "build-us-repair-panel",
        help="E2-US repair panel: causal preprocessing, as-traded "
        "unit factors, retrospective QA flags",
    )
    p_rp.add_argument("--manifest", required=True, help="the original yahoo_us raw manifest")
    p_rp.add_argument(
        "--schedule", required=True, help="a us_splits-*.json manifest from us-actions"
    )
    p_rp.add_argument("--end", required=True, help="read nothing after this date into the panel")
    p_rp.add_argument("--coverage", help="a us_splits-coverage-*.json manifest from us-coverage")
    p_sh = sub.add_parser(
        "us-share-check",
        help="corroborate post-window split records with SEC cover-page share counts",
    )
    p_sh.add_argument(
        "--schedule", required=True, help="a us_splits-*.json from the current text verifier"
    )
    p_sh.add_argument("--raw-manifest", required=True)
    p_sh.add_argument("--window-end", required=True)
    p_sh.add_argument("--user-agent", default=None)
    p_sh.add_argument("--cache-dir")
    p_sh.add_argument("--offline", action="store_true")
    p_uc = sub.add_parser(
        "us-coverage", help="search SEC for splits the provider did not record (large jumps)"
    )
    p_uc.add_argument("--raw-manifest", required=True)
    p_uc.add_argument("--start", required=True)
    p_uc.add_argument("--end", required=True)
    p_uc.add_argument("--user-agent", default=None)
    p_uc.add_argument("--cache-dir")
    p_uc.add_argument("--offline", action="store_true")
    p_gp = sub.add_parser(
        "build-global-panel", help="build a US or crypto panel from a pull manifest"
    )
    p_gp.add_argument("--market", choices=("US", "CRYPTO"), required=True)
    p_gp.add_argument("--manifest", required=True)
    p_ca = sub.add_parser(
        "build-ca-registry", help="classify every reference reset in the panel (new registry file)"
    )
    p_ca.add_argument("--panel", help="panel manifest (default: latest)")
    sub.add_parser("rules", help="list rules and their state")
    p_run = sub.add_parser("run", help="run a rule over the full universe vs random entries")
    p_run.add_argument("--rule", required=True)
    p_run.add_argument(
        "--market",
        choices=("IDX", "US", "CRYPTO", "CRYPTO_CLOSE"),
        default="IDX",
        help="market profile (lots, costs, price limits, entry at open or close); CRYPTO_CLOSE is the "
        "crypto profile with entry at the close of t+1 (E5 latency-pessimistic sensitivity)",
    )
    p_run.add_argument("--start")
    p_run.add_argument("--end")
    p_run.add_argument("--holding-days", type=int)
    p_run.add_argument(
        "--entry-lag",
        type=_sessions_from_one,
        default=1,
        help="sessions between the signal close and the entry, at least 1",
    )
    p_run.add_argument("--notional", type=float, default=10_000_000.0)
    p_run.add_argument("--max-participation", type=float, default=0.10)
    p_run.add_argument("--fee-buy", type=float, default=0.0015)
    p_run.add_argument("--fee-sell", type=float, default=0.0025)
    p_run.add_argument("--overlap", choices=("skip", "allow"), default="skip")
    p_run.add_argument("--draws", type=int, default=200)
    p_run.add_argument("--seed", type=int, default=20261007)
    p_run.add_argument("--data-end-exit", choices=("last_close", "zero"), default="last_close")
    p_run.add_argument(
        "--ca-mode",
        choices=("registry", "exclude", "value_preserving", "adjusted"),
        default="registry",
        help="registry (default): scale shares only through verified splits / stock dividends; "
        "exclude, value_preserving: earlier modes, for reproducing older runs",
    )
    p_run.add_argument("--ca-registry", help="corporate-action registry manifest (default: latest)")
    p_run.add_argument(
        "--controls-version",
        choices=("v2", "v1", "v3", "v4"),
        default="v2",
        help="matched-control features (v1 reproduces runs before hardening v2; v3 adds a volatility "
        "quintile ahead of market_cap, E5; v4 is v3 with a window-invariant listing age, for "
        "future protocols: no recorded run uses it)",
    )
    p_run.add_argument(
        "--lookahead-cuts",
        type=int,
        help="sample N prefixes instead of the exhaustive check (faster, not a proof)",
    )
    p_run.add_argument("--panel", help="panel manifest (default: latest)")
    p_run.add_argument(
        "--allow-dirty", action="store_true", help="record a run from uncommitted code (flagged)"
    )
    p_run.add_argument(
        "--no-commit", action="store_true", help="write the run but do not git-commit it"
    )
    p_run.add_argument(
        "--units",
        choices=("panel", "as_traded"),
        default="panel",
        help="as_traded: sizing, cost tiers and price bands at the price traded that session "
        "(needs a repair panel with unit_factor)",
    )
    p_run.add_argument(
        "--fill-model",
        choices=("A", "B", "B2", "C"),
        default="A",
        help="A: original (entry-session final volume, ex post); B: FILL-B-v1 (mixed units, "
        "reproduction only); B2: FILL-B-v2 (entry-session units); C: FILL-C-v1, decision-time "
        "capacity for IDX closing-auction entries",
    )
    p_run.add_argument(
        "--entry-rule",
        choices=("fixed", "confirm", "pullback", "unlock"),
        help="execution plan entry (default: the rule's frozen plan, else fixed)",
    )
    p_run.add_argument(
        "--entry-window", type=int, help="sessions after the signal a conditional entry may trigger"
    )
    p_run.add_argument(
        "--exit-rule",
        choices=("fixed", "stop_ref", "first_down"),
        help="execution plan exit (default: the rule's frozen plan, else fixed)",
    )
    p_run.add_argument(
        "--side",
        choices=("long", "short"),
        help="execution plan side (default: the rule's frozen plan, else long); short needs an "
        "open-entry market profile (US, CRYPTO)",
    )
    p_run.add_argument(
        "--holdout-final",
        action="store_true",
        help="the one pre-registered IDX holdout evaluation (otherwise the holdout is refused)",
    )
    p_run.add_argument(
        "--void-extended",
        type=float,
        default=None,
        help="void rule: drop flags (and controls) on sessions more than this fraction above the prior 20-session median level, e.g. 0.10",
    )
    p_run.add_argument(
        "--quarantine",
        choices=("none", "unit_schedule"),
        default="none",
        help="unit_schedule: leave out names whose split records SEC does not corroborate",
    )
    sub.add_parser("verify-runs", help="check that no past run was edited or removed")
    sub.add_parser(
        "e1-discovery", help="experiment E1, discovery period (writes research/E1/discovery/)"
    )
    p_sn = sub.add_parser(
        "sensors",
        help="pull free public sensors (Bluesky accounts, StockTwits trending, EDGAR 8-K "
        "keywords, CoinGecko trending, Binance listings) into a hash-chained log; no orders",
    )
    p_sn.add_argument("action", choices=("pull", "verify"))
    p_sn.add_argument(
        "--handles", default="unusualwhales.bsky.social", help="Bluesky handles, comma-separated"
    )
    p_sn.add_argument(
        "--keywords", default=None, help="EDGAR 8-K full-text keywords, comma-separated"
    )
    p_sn.add_argument("--sources", default=None, help="subset of source names, comma-separated")
    p_sn.add_argument(
        "--commit", action="store_true", help="RFC 3161-stamp the records, commit and push"
    )
    p_ps = sub.add_parser(
        "paper-scan", help="prospective paper scan of the session that last closed (no orders)"
    )
    p_ps.add_argument(
        "--manifest", help="a recent-bars manifest for the market (default: pull now)"
    )
    p_ps.add_argument(
        "--commit", action="store_true", help="commit the records and push (GitHub receipt)"
    )
    p_sc = sub.add_parser("paper-score", help="score paper decisions whose window has ended")
    p_sc.add_argument(
        "--manifest", help="a recent-bars manifest for the market (default: pull now)"
    )
    p_sc.add_argument("--commit", action="store_true")
    p_sc.add_argument(
        "--max-age-hours",
        type=float,
        default=6.0,
        help="reuse the latest recent-bars pull if it is at most this old, instead of pulling the "
        "same bars again (0 = always pull now)",
    )
    p_sc.add_argument(
        "--rescore",
        action="append",
        default=[],
        metavar="DECISION_ID",
        help="score again and append as a revision linked to the earlier outcome (needs --reason)",
    )
    p_sc.add_argument("--reason", help="why the earlier outcome is revised")
    for p_ in (p_ps, p_sc):
        p_.add_argument("--market", choices=("IDX", "US", "CRYPTO"), default="IDX")
    sub.add_parser("paper-verify", help="check the paper ledger's hash chain and timestamp tokens")
    p_sp = sub.add_parser(
        "speculate",
        help="seal speculation sets (cone, plan, twins) for the latest paper decisions, "
        "before their entry cutoff (research/SPECULATION_REGISTER_v1)",
    )
    p_sp.add_argument(
        "--commit", action="store_true", help="commit the records and push (GitHub receipt)"
    )
    p_ss = sub.add_parser("speculate-score", help="resolve speculation windows that have ended")
    p_ss.add_argument(
        "--manifest",
        help="a recent-bars manifest for the market (default: the latest one if pulled "
        "within --max-age-hours, else pull now)",
    )
    p_ss.add_argument("--max-age-hours", type=float, default=8.0)
    p_ss.add_argument("--commit", action="store_true")
    for p_ in (p_sp, p_ss):
        p_.add_argument("--market", choices=("IDX", "US", "CRYPTO"), default="IDX")
    p_sr = sub.add_parser(
        "speculate-report", help="write paper/SPECULATIONS.md (statistics, calibration, cards)"
    )
    p_sr.add_argument("--cards", action="store_true", help="also print the latest sealed sets")
    p_sr.add_argument("--commit", action="store_true")
    p_cs = sub.add_parser(
        "catalyst-seal",
        help="seal Catalyst Register sets for a family's new events before their entry "
        "cutoff (research/CATALYST_REGISTER_v1)",
    )
    p_cs.add_argument(
        "--family",
        choices=("SEC13D", "SEC13D_V2", "IDX_INDEX", "DILUTION_8K", "FORM4", "FORM4_SHARP"),
        required=True,
        help="SEC13D_V2 runs after SEC13D, FORM4_SHARP after FORM4, in the same routine",
    )
    p_cs.add_argument(
        "--events",
        help="IDX_INDEX: the review's events file (research/CATALYST_REGISTER_v1/events/)",
    )
    p_cs.add_argument(
        "--dry-run", action="store_true", help="build and print the batch; append nothing"
    )
    p_cs.add_argument(
        "--commit", action="store_true", help="commit the records and push (GitHub receipt)"
    )
    p_ct = sub.add_parser(
        "catalyst-tag",
        help="seal DILUTION_RECENT tags for Speculation Register sets (US, IDX) "
        "before their entry cutoff",
    )
    p_ct.add_argument("--commit", action="store_true")
    p_cc = sub.add_parser(
        "catalyst-score", help="resolve Catalyst Register windows that have ended"
    )
    p_cc.add_argument("--market", choices=("US", "IDX"), required=True)
    p_cc.add_argument(
        "--manifest",
        help="a recent-bars manifest for the market (default: the latest one if pulled "
        "within --max-age-hours, else pull now)",
    )
    p_cc.add_argument("--max-age-hours", type=float, default=8.0)
    p_cc.add_argument("--commit", action="store_true")
    for name in (
        "learner-forecast",
        "learner2-forecast",
    ):  # LEARNER_v1 is withdrawn: both names seal LEARNER_v2
        p_lf = sub.add_parser(
            name,
            help="LEARNER_v2: seal the learner's forecasts for sets still before their cutoff "
            "(research/LEARNER_v2)",
        )
        p_lf.add_argument("--commit", action="store_true")
    for name in ("learner-report", "learner2-report"):
        p_lr = sub.add_parser(
            name, help="write paper/LEARNER_V2.md (earned confidence per kind, calls, beliefs)"
        )
        p_lr.add_argument("--commit", action="store_true")
    p_l3 = sub.add_parser(
        "learner3-forecast",
        help="LEARNER v2.4 (research/LEARNER_v2/protocol_v2_4.json): the one live "
        "challenger's forecast for every US speculation set still before its cutoff",
    )
    p_l3.add_argument("--commit", action="store_true")
    p_l3r = sub.add_parser("learner3-report", help="write paper/LEARNER_V3.md")
    p_l3r.add_argument("--commit", action="store_true")
    for command, helptext in (
        (
            "premove-shadow-forecast",
            "seal today's three-arm pre-move shortlists (research/PREMOVE_SHADOW_v1)",
        ),
        (
            "premove-shadow-score",
            "record the outcomes of sealed pre-move days whose five bars are complete",
        ),
        ("premove-shadow-report", "write paper/PREMOVE_SHADOW.md"),
    ):
        sub.add_parser(command, help=helptext).add_argument("--commit", action="store_true")
    for command, helptext in (
        (
            "paper-book-plan",
            "seal tonight's KOD paper-book plan (DONT_BUY/BUY_OK) for each new v2.4 forecast",
        ),
        (
            "paper-book-score",
            "record the five-session trade of every planned spike the register resolved",
        ),
        ("paper-book-report", "write paper/PAPER_BOOK.md"),
    ):
        sub.add_parser(command, help=helptext).add_argument("--commit", action="store_true")
    p_pas = sub.add_parser(
        "paper-account-sync",
        help="the KOD paper account (research/PAPER_ACCOUNT_v1): cancels, fills, exits, marks, "
        "then tonight's orders for both stop arms",
    )
    p_pas.add_argument("--manifest", help="a recent US bars manifest (default: the latest one)")
    p_pas.add_argument("--max-age-hours", type=float, default=6.0)
    p_pas.add_argument("--commit", action="store_true")
    sub.add_parser("paper-account-report", help="write paper/PAPER_ACCOUNT.md").add_argument(
        "--commit", action="store_true"
    )
    sub.add_parser(
        "crypto-account-sync",
        help="the crypto spot paper account (research/CRYPTO_ACCOUNT_v1): record spot quotes, then "
        "fills, exits, decisions and the mark",
    ).add_argument("--commit", action="store_true")
    p_pbc = sub.add_parser(
        "paper-book-confirm",
        help="the owner's BUY or SKIP on a planned spike, before its entry cutoff",
    )
    p_pbc.add_argument("ticker")
    p_pbc.add_argument("decision", choices=("BUY", "SKIP"))
    p_pbc.add_argument("--commit", action="store_true")
    p_l3f = sub.add_parser(
        "learner3-freeze",
        help="freeze each eligible planned learner evaluation once; report remains read-only",
    )
    p_l3f.add_argument("--commit", action="store_true")
    p_ig = sub.add_parser(
        "idea-grade",
        help="grade a chart idea written as a JSON spec (idxsig/idea_grader.py): random "
        "entries, the search family (SPA) and a later period; paper only",
    )
    p_ig.add_argument("spec", help="path to a JSON spec, or a list of specs")
    p_cc = sub.add_parser(
        "call-cert-report",
        help="write paper/CALL_CERT.md: certified next-day dump calls beside v2.4 "
        "(research/CALL_CERT_v1; shadow, changes nothing in v2.4)",
    )
    p_cc.add_argument("--commit", action="store_true")
    p_cr = sub.add_parser(
        "catalyst-report", help="write paper/CATALYSTS.md (statistics, looks, calibration, cards)"
    )
    p_cr.add_argument("--commit", action="store_true")
    p_ms = sub.add_parser(
        "micro-snapshot",
        help="side-car for a crypto scan: Binance book cost now and, once the day's "
        "path exists, 1-minute timelines (read only; changes no rule or ledger)",
    )
    p_ms.add_argument(
        "--scan-id", help="crypto scan id (default: the latest crypto scan with candidates)"
    )
    p_ms.add_argument("--no-book", action="store_true", help="timelines only (rebuild history)")
    p_ms.add_argument("--commit", action="store_true")
    p_mc = sub.add_parser(
        "micro-catch-up",
        help="build the missing 1-minute timelines of crypto candidates whose day is "
        "over by 26 h (also rebuilds history)",
    )
    p_mc.add_argument("--commit", action="store_true")
    sub.add_parser(
        "micro-report", help="statistics of the microstructure side-car and its integrity check"
    )
    p_gp2 = sub.add_parser(
        "guidance-paper",
        help="forward paper test of revenue guidance raises (dry run unless "
        "E10 passed and --record; never an order)",
    )
    p_gp2.add_argument("--day", help="filing day to scan, YYYY-MM-DD (default: yesterday)")
    p_gp2.add_argument(
        "--bootstrap",
        action="store_true",
        help="rebuild the guidance state from the 200 days before",
    )
    p_gp2.add_argument(
        "--record",
        action="store_true",
        help="append to paper/guidance/ledger.jsonl (needs E10 PASS)",
    )
    for name, helptext in (
        (
            "e3-reproduce",
            "experiment E3 precondition: re-run the recorded E1 trading runs on E3's data",
        ),
        (
            "e3-discovery",
            "experiment E3 discovery: every (detector, plan) pair through the harness",
        ),
        ("e3-validation", "experiment E3 validation: the frozen pair on 2023, as a recorded run"),
    ):
        p_e3 = sub.add_parser(name, help=helptext)
        if name == "e3-discovery":
            p_e3.add_argument(
                "--accept-deviation",
                action="store_true",
                help="proceed although a precondition run did not reproduce identically (recorded)",
            )
    for name, helptext in (
        (
            "e4-reproduce",
            "experiment E4 precondition: re-run the recorded E2 trading run on E4's data",
        ),
        ("e4-discovery", "experiment E4 discovery: every (detector, plan) pair, short side"),
        ("e4-validation", "experiment E4 validation: the frozen pair on 2023, as a recorded run"),
    ):
        p_e4 = sub.add_parser(name, help=helptext)
        p_e4.add_argument("--market", choices=("CRYPTO", "US"), default="CRYPTO")
        p_e4.add_argument(
            "--protocol", choices=("v1", "v2"), default="v1", help="research/E4 protocol version"
        )
        if name == "e4-discovery":
            p_e4.add_argument(
                "--accept-deviation",
                action="store_true",
                help="proceed although the precondition run did not reproduce identically (recorded)",
            )
    for name, helptext in (
        (
            "e5-reproduce",
            "experiment E5 precondition: re-run the market's recorded run on E5's panel",
        ),
        ("e5-discovery", "experiment E5 discovery: stage 1 (information) then stage 2 (execution)"),
        (
            "e5-freeze",
            "experiment E5 freeze: write discovery/model.json into moonshot_e5.py literals",
        ),
        ("e5-validation", "experiment E5 validation: the frozen arms on 2023, as recorded runs"),
    ):
        p_e5 = sub.add_parser(name, help=helptext)
        p_e5.add_argument(
            "--market",
            choices=("IDX", "US", "CRYPTO"),
            required=True,
            help="CRYPTO_CLOSE is reached as a sensitivity inside CRYPTO, never as a market here",
        )
        p_e5.add_argument(
            "--protocol",
            choices=("v1", "v1.1"),
            required=True,
            help="research/E5/v1.1/protocol.json (v1.1, the audit addendum: what this code implements) "
            "or research/E5/protocol.json (v1: refused here, it names the commit that runs it); "
            "stage outputs go under the protocol's directory",
        )
        if name == "e5-discovery":
            p_e5.add_argument(
                "--accept-deviation",
                action="store_true",
                help="proceed although the precondition run deviates beyond the accepted tolerance "
                "(both sides on record)",
            )
    for name, helptext in (
        ("e2-discovery", "experiment E2 discovery for one market"),
        ("e2-validation", "experiment E2 validation of a market's frozen detector"),
    ):
        p_e2 = sub.add_parser(name, help=helptext)
        p_e2.add_argument("--market", choices=("US", "CRYPTO"), required=True)
    p_v = sub.add_parser("e1-validation", help="experiment E1, validation of the frozen detector")
    p_v.add_argument(
        "--rule", required=True, help="must equal rules/moonshot_e1.SELECTED, committed"
    )
    args = parser.parse_args(argv)

    if args.cmd == "sensors":
        from . import paper
        from . import sensors as sensors_mod

        if args.action == "verify":
            problems = sensors_mod.verify()
            print("sensors verify: " + ("OK" if not problems else "; ".join(problems[:10])))
            return 0 if not problems else 1
        handles = tuple(h for h in args.handles.split(",") if h)
        keywords = (
            tuple(k.strip() for k in args.keywords.split(","))
            if args.keywords
            else sensors_mod.DEFAULT_KEYWORDS
        )
        sources = sensors_mod.default_sources(handles, keywords)
        if args.sources:
            keep = set(args.sources.split(","))
            sources = {k: v for k, v in sources.items() if k in keep}
        stamper = None
        if args.commit:
            from kod.timestamp import RFC3161Timestamper

            stamper = RFC3161Timestamper()
        out = sensors_mod.pull(sources, timestamper=stamper)
        print(
            json.dumps(
                {k: out[k] for k in ("stamp", "alerts_new", "counts", "errors", "head")}, indent=1
            )
        )
        if args.commit:
            files = [
                sensors_mod.LOG,
                sensors_mod.RAW / out["stamp"].replace("-", "").replace(":", ""),
                paper.TOKENS,
            ]
            msg = f"sensors pull {out['stamp']}: {out['alerts_new']} new alert(s)"
            print(paper.commit_and_push(files, msg, os.environ.get("IDXSIG_COMMIT_TRAILER", "")))
        return 0
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
        print(
            yahoo.fetch(
                tickers, prefix="yahoo_us", suffix="", start=args.start, sleep=0.1, workers=6
            )
        )
    elif args.cmd == "fetch-binance":
        from .sources import binance

        print(binance.fetch(start=args.start))
    elif args.cmd.startswith("coinglass-"):
        from . import coinglass
        from .sources.coinglass import CoinGlassClient, CoinGlassError

        try:
            if args.cmd == "coinglass-verify":
                document = coinglass.load_snapshot(args.manifest)
                print(
                    json.dumps(
                        {
                            "integrity": "OK",
                            "snapshot_id": document["snapshot_id"],
                            "datasets": {n: r["status"] for n, r in document["datasets"].items()},
                        },
                        indent=2,
                    )
                )
                return 0
            if args.cmd == "coinglass-report":
                context = coinglass.latest_context(
                    args.manifest, asof=args.asof, max_age_intervals=args.max_age_intervals
                )
                print(json.dumps(context, indent=2, allow_nan=False))
                return 0 if context["all_requested_ready"] else 2
            datasets = tuple(s.strip() for s in args.datasets.split(","))
            client = CoinGlassClient()
            if args.cmd == "coinglass-check":
                _, requests = coinglass._parameters(
                    args.symbol, args.exchange, args.interval, 2, datasets
                )
                results = {}
                for name, params in requests.items():
                    try:
                        response = client.request(name, **params)
                        coinglass.normalize_history(
                            name, response.data, params, response.metadata["observed_at"]
                        )
                        results[name] = {
                            "status": "accessible",
                            "returned_rows": len(response.data),
                        }
                    except CoinGlassError as exc:
                        results[name] = {
                            "status": "unavailable",
                            "reason": exc.kind,
                            "message": str(exc),
                            "http_status": exc.http_status,
                            "provider_code": exc.provider_code,
                        }
                print(json.dumps({"provider": "CoinGlass v4", "datasets": results}, indent=2))
                return 0 if all(r["status"] == "accessible" for r in results.values()) else 2
            manifest = coinglass.capture(
                client,
                symbol=args.symbol,
                exchange=args.exchange,
                interval=args.interval,
                limit=args.limit,
                datasets=datasets,
                end=args.end,
            )
            context = coinglass.latest_context(manifest)
            print(json.dumps(context, indent=2, allow_nan=False))
            document = coinglass.load_snapshot(manifest)
            return 0 if all(r["status"] == "ok" for r in document["datasets"].values()) else 2
        except (CoinGlassError, ValueError, OSError, KeyError, TypeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    elif args.cmd == "us-actions":
        import os

        from . import us_actions

        agent = args.user_agent or os.environ.get("IDXSIG_SEC_USER_AGENT")
        if not agent:
            print(
                "error: set --user-agent or IDXSIG_SEC_USER_AGENT (SEC requires a contact)",
                file=sys.stderr,
            )
            return 2
        print(
            us_actions.build_schedule(
                Path(args.raw_manifest),
                agent,
                args.effective_after,
                args.universe_end,
                Path(args.cache_dir) if args.cache_dir else None,
                args.offline,
                recheck=Path(args.recheck) if args.recheck else None,
            )
        )
    elif args.cmd == "build-us-repair-panel":
        from . import global_panel

        print(
            global_panel.build_us_repair(
                Path(args.manifest),
                Path(args.schedule),
                args.end,
                Path(args.coverage) if args.coverage else None,
            )
        )
    elif args.cmd == "us-share-check":
        import os

        from . import us_actions

        agent = args.user_agent or os.environ.get("IDXSIG_SEC_USER_AGENT")
        if not agent:
            print(
                "error: set --user-agent or IDXSIG_SEC_USER_AGENT (SEC requires a contact)",
                file=sys.stderr,
            )
            return 2
        print(
            us_actions.build_share_corroboration(
                Path(args.schedule),
                Path(args.raw_manifest),
                args.window_end,
                agent,
                Path(args.cache_dir) if args.cache_dir else None,
                args.offline,
            )
        )
    elif args.cmd == "us-coverage":
        import os

        from . import us_actions

        agent = args.user_agent or os.environ.get("IDXSIG_SEC_USER_AGENT")
        if not agent:
            print(
                "error: set --user-agent or IDXSIG_SEC_USER_AGENT (SEC requires a contact)",
                file=sys.stderr,
            )
            return 2
        print(
            us_actions.build_coverage(
                Path(args.raw_manifest),
                agent,
                args.start,
                args.end,
                Path(args.cache_dir) if args.cache_dir else None,
                args.offline,
            )
        )
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
        print(
            json.dumps(
                {k: summary[k] for k in ("rows", "by_status", "by_type", "share_scaled")}, indent=2
            )
        )
        print(path)
    elif args.cmd == "rules":
        from . import rules

        from .rules.audit import audit_module

        failed = 0
        for rule_id, rule in sorted(rules.registry().items()):
            problems = audit_module(rule.module)
            failed += bool(problems)
            print(
                f"{rule_id} {rule.version} {rule.kind} hold={rule.holding_days} sha={rule.sha256[:12]} "
                f"source-audit={'passed' if not problems else f'FAILED ({len(problems)})'}"
            )
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
            df, meta = global_panel.load(
                Path(args.panel) if args.panel else global_panel.latest(prof.market)
            )
            args.ca_mode, args.notional, args.fee_buy, args.fee_sell = (
                "adjusted",
                prof.notional,
                prof.fee_buy,
                prof.fee_sell,
            )
        cfg = RunConfig(
            market=args.market,
            rule_id=args.rule,
            start=args.start,
            end=args.end,
            holding_days=args.holding_days,
            entry_lag=args.entry_lag,
            notional=args.notional,
            max_participation=args.max_participation,
            fee_buy=args.fee_buy,
            fee_sell=args.fee_sell,
            overlap=args.overlap,
            random_draws=args.draws,
            seed=args.seed,
            data_end_exit=args.data_end_exit,
            ca_mode=args.ca_mode,
            lookahead_cuts=args.lookahead_cuts,
            controls_version=args.controls_version,
            units=args.units,
            fill_model=args.fill_model,
            quarantine=args.quarantine,
            entry_rule=args.entry_rule,
            entry_window=args.entry_window,
            exit_rule=args.exit_rule,
            side=args.side,
            holdout_final=args.holdout_final,
            void_extended=args.void_extended,
        )
        registry = None
        if args.ca_mode == "registry" and args.market == "IDX":
            from . import corporate_actions

            try:
                registry = corporate_actions.load(
                    Path(args.ca_registry) if args.ca_registry else None,
                    panel_sha256=meta["sha256"],
                )
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
            print(
                f"error: E1 is registered on {proto['data']['panel_manifest']}, not {manifest.name}",
                file=sys.stderr,
            )
            return 2
        if code_state()["dirty"]:
            print(
                "error: commit idxsig/ first so the results name the code that produced them",
                file=sys.stderr,
            )
            return 2
        study = e1.Study(df, meta)
        if args.cmd == "e1-discovery":
            print(json.dumps(e1.run_discovery(study, e1.E1_DIR / "discovery"), indent=2))
        else:
            if moonshot_e1.SELECTED != args.rule:
                print(
                    f"error: {args.rule} is not the frozen detector (moonshot_e1.SELECTED = "
                    f"{moonshot_e1.SELECTED})",
                    file=sys.stderr,
                )
                return 2
            print(
                json.dumps(
                    e1.run_validation(study, args.rule, e1.E1_DIR / "validation"),
                    indent=2,
                    default=str,
                )
            )
    elif args.cmd in ("e3-reproduce", "e3-discovery", "e3-validation"):
        from . import corporate_actions, e3
        from .panel import load
        from .provenance import MANIFESTS
        from .results import code_state

        proto, proto_sha = e3.protocol()
        if code_state()["dirty"]:
            print(
                "error: commit idxsig/ first so the results name the code that produced them",
                file=sys.stderr,
            )
            return 2
        if (
            "PENDING" in proto["data"]["panel_manifest"]
            or "PENDING" in proto["data"]["registry_manifest"]
        ):
            print(
                "error: research/E3/protocol.json does not name its panel and registry manifests yet",
                file=sys.stderr,
            )
            return 2
        try:
            df, meta, _ = load(MANIFESTS / proto["data"]["panel_manifest"])
            registry = corporate_actions.load(
                MANIFESTS / proto["data"]["registry_manifest"], panel_sha256=meta["sha256"]
            )
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        stage = args.cmd.split("-", 1)[1]
        try:
            if stage == "reproduce":
                result = e3.run_reproduce(
                    df, meta, registry, e3.E3_DIR / "reproduce", proto, proto_sha
                )
            elif stage == "discovery":
                result = e3.run_discovery(
                    df,
                    meta,
                    registry,
                    e3.E3_DIR / "discovery",
                    proto,
                    proto_sha,
                    accept_deviation=args.accept_deviation,
                )
            else:
                result = e3.run_validation(
                    df, meta, registry, e3.E3_DIR / "validation", proto, proto_sha
                )
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
            print(
                "error: commit idxsig/ first so the results name the code that produced them",
                file=sys.stderr,
            )
            return 2
        mk = args.market
        if mk not in proto["markets"] or "PENDING" in proto["markets"][mk]["panel_manifest"]:
            print(
                f"error: research/E4/protocol.json does not name a panel manifest for {mk}",
                file=sys.stderr,
            )
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
                result = e4.run_discovery(
                    df, meta, out, proto, proto_sha, mk, accept_deviation=args.accept_deviation
                )
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

        proto_path = (
            e5.E5_DIR / "protocol.json"
            if args.protocol == "v1"
            else e5.E5_DIR / args.protocol / "protocol.json"
        )
        proto, proto_sha = e5.protocol(proto_path)
        try:
            e5.check_implementation(
                proto, proto_path
            )  # refuses v1 here: a v1 label on v1.1 code (PR #8 review)
        except (RuntimeError, KeyError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        e5.use_protocol(proto_path)
        if code_state()["dirty"]:
            print(
                "error: commit idxsig/ first so the results name the code that produced them",
                file=sys.stderr,
            )
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
                    print(
                        f"error: research/E5/protocol.json does not name a panel manifest for {mk}",
                        file=sys.stderr,
                    )
                    return 2
                registry = None
                if mk == "IDX":
                    from . import corporate_actions
                    from .panel import load
                    from .provenance import sha256_file

                    df, meta, manifest = load(MANIFESTS / spec["panel_manifest"])
                    meta["_manifest"] = manifest.name
                    meta["_manifest_sha256"] = sha256_file(manifest)
                    registry = corporate_actions.load(
                        MANIFESTS / spec["registry_manifest"], panel_sha256=meta["sha256"]
                    )
                else:
                    from . import global_panel

                    df, meta = global_panel.load(MANIFESTS / spec["panel_manifest"])
                if stage == "reproduce":
                    result = e5.run_reproduce(df, meta, registry, out, proto, proto_sha, mk)
                elif stage == "discovery":
                    result = e5.run_discovery(
                        df,
                        meta,
                        registry,
                        out,
                        proto,
                        proto_sha,
                        mk,
                        accept_deviation=args.accept_deviation,
                    )
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
            print(
                "error: commit idxsig/ first so the results name the code that produced them",
                file=sys.stderr,
            )
            return 2
        df, meta = global_panel.load(manifest)
        study = e1.Study(
            df,
            meta,
            protocol_path=proto_path,
            profile=PROFILES[args.market],
            family_module=moonshot_g,
        )
        out = e1.PKG_ROOT / "research" / "E2" / args.market
        if args.cmd == "e2-discovery":
            print(json.dumps(e1.run_discovery(study, out / "discovery"), indent=2))
        else:
            rule = moonshot_g.selected(args.market)
            if rule is None:
                print(
                    f"error: no frozen detector for {args.market} (moonshot_g.SELECTED)",
                    file=sys.stderr,
                )
                return 2
            print(
                json.dumps(
                    e1.run_validation(study, rule, out / "validation"), indent=2, default=str
                )
            )
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
                print(
                    f"no {mk} decision can have completed its window yet; nothing pulled, nothing recorded"
                )
                return 0
            print(f"{len(due)} {mk} decision(s) due: pulling bars")
        if manifest is None:
            if args.cmd == "paper-score":
                manifest, extra = _manifest_for_score(mk, args.max_age_hours)
            else:  # paper-scan always scans freshly pulled bars
                manifest, extra = _pull_recent(mk)
        stamper = RFC3161Timestamper()
        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "paper-scan":
            out = paper.scan(
                manifest,
                validation=paper.validation_evidence(mk),
                market=mk,
                quotes=paper.binance_quotes if mk == "CRYPTO" else None,
            )
            if paper.already_scanned(out["scan"]["session"], mk):
                print(
                    f"{mk} session {out['scan']['session']} is already scanned (no new session since: holiday or "
                    f"data not yet updated); nothing recorded"
                )
                return 0
            written = paper.record_scan(out, stamper)
            if mk == "CRYPTO" and os.environ.get("IDXSIG_MICRO", "1") != "0":
                written = [*written, *_micro_sidecar(out["scan"]["scan_id"])]
            print(
                json.dumps(
                    {
                        k: out["scan"][k]
                        for k in ("scan_id", "session", "result", "candidates_ranked")
                    },
                    indent=2,
                )
            )
            for dcs in out["decisions"]:
                print(
                    f"  #{dcs['rank']} {dcs['instrument']['ticker']}: {dcs['decision']} ({dcs['reason']})"
                )
            message = f"paper scan {out['scan']['scan_id']}: {out['scan']['result']}"
        else:
            if args.rescore and not args.reason:
                print("error: --rescore needs --reason", file=sys.stderr)
                return 2
            verify = _sec_verifier() if mk == "US" else None
            written, outcomes = paper.score_pending(
                manifest,
                stamper,
                market=mk,
                verify=verify,
                rescore={d: args.reason for d in args.rescore},
            )
            n_bad = sum(o.get("status") == "UNSCORABLE" for o in outcomes)
            print(f"scored {len(outcomes) - n_bad} decision(s), {n_bad} unscorable")
            for o in outcomes:
                print(
                    f"  {o['decision_id']}: {o.get('status')} {o.get('decision_verdict') or o.get('reason')}"
                )
            message = f"paper score {mk}: {len(outcomes)} outcome(s), {n_bad} unscorable"
        if args.commit and written:
            print(paper.commit_and_push([*written, manifest, *extra], message, trailer))
    elif args.cmd == "paper-verify":
        from . import catalysts, paper, speculation

        from . import learner, learner2, learner3

        from . import crypto_account, paper_account, paper_book, premove_shadow

        problems = (
            paper.verify_all()
            + speculation.verify()
            + catalysts.verify()
            + learner.verify()
            + learner2.verify()
            + learner3.verify()
            + premove_shadow.verify()
            + paper_book.verify()
            + paper_account.verify()
            + crypto_account.verify()
        )
        print("paper-verify: " + ("OK" if not problems else f"{len(problems)} problems"))
        for p_ in problems:
            print(f"  {p_}")
        return 1 if problems else 0
    elif args.cmd == "crypto-account-sync":
        import os
        from datetime import datetime, timezone

        from . import crypto_account as ca, paper

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        cands = ca.candidates(paper.ledger_lines(paper.LEDGER))
        latest = max((d["signal_session"] for d in cands), default=None)
        written, stamper = [], RFC3161Timestamper()

        def append(recs, **kwargs):
            try:
                written.extend(paper.append(recs, path=ca.LEDGER, timestamper=stamper, **kwargs))
            except paper.ReceiptPendingError as exc:
                written.extend(exc.records)
                print(f"warning: {exc}")

        run = ca.cycle(
            cands,
            ca.fetch_quotes,
            lambda: datetime.now(timezone.utc),
            append,
            watch_extra=[ca.symbol_of(d) for d in cands if d["signal_session"] == latest],
        )
        for q in run["observed"]:
            if q["type"] == ca.QUOTE:
                print(
                    f"  quote {q['symbol']}: bid {q['bid']:g} ask {q['ask']:g} at {q['observed_at']}"
                )
            else:
                print(f"  no quote for {q['symbol']} at {q['attempted_at']}: {q['error']}")
        for r in run["events"]:
            what = r.get("status") or r.get("exit_reason") or r.get("reason") or r.get("order")
            print(f"  {r['type']} {r.get('symbol') or r['ticker']}: {what}")
        m = run["mark"]
        print(
            f"  mark {m['session']}: equity {m['equity']:,.2f} USDT (cash {m['cash']:,.2f}, "
            f"reserved {m['reserved']:,.2f}, realized {m['realized']:+,.2f})"
        )
        report = ca.write_report()
        if args.commit:
            tokens = [
                paper.TOKENS / f"{r['record_hash']}.{a}.tsr"
                for r in written
                for a in ("freetsa", "sectigo")
            ]
            n_quotes = sum(r["type"] == ca.QUOTE for r in run["observed"])
            print(
                paper.commit_and_push(
                    [ca.LEDGER, report, *[t for t in tokens if t.exists()]],
                    f"crypto account: {n_quotes} quote(s), "
                    f"{len(run['events'])} decision/fill record(s)",
                    os.environ.get("IDXSIG_COMMIT_TRAILER", ""),
                )
            )
        return 0
    elif args.cmd in ("paper-account-sync", "paper-account-report"):
        import os
        from datetime import datetime, timezone

        from . import paper, paper_account as acct, paper_account_report

        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "paper-account-report":
            path = paper_account_report.write_report()
            print(path.read_text(encoding="utf-8"))
            if args.commit:
                print(paper.commit_and_push([path], "paper account: report", trailer))
            return 0
        manifest, extra = (
            (Path(args.manifest), [])
            if args.manifest
            else _recent_manifest("US", args.max_age_hours)
        )
        bars_of, session, _ = acct.bars_from_manifest(manifest, _sec_verifier())
        recs = acct.sync(acct.lines(), None, bars_of, datetime.now(timezone.utc), session)
        for r in recs:
            if r["type"] == acct.MARK:
                print(
                    f"  {r['arm']} {r['session']}: equity ${r['equity']:,.2f} (cash ${r['cash']:,.2f}, "
                    f"realized ${r['realized']:+,.2f}, unrealized ${r['unrealized']:+,.2f})"
                )
            else:
                what = r.get("status") or r.get("exit_reason") or r.get("reason") or r.get("order")
                print(f"  {r['arm']} {r['ticker']}: {r['type']} {what}")
        if not recs:
            print("paper account: nothing new; nothing recorded")
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        try:
            stored = paper.append(recs, path=acct.LEDGER, timestamper=RFC3161Timestamper())
        except paper.ReceiptPendingError as exc:
            stored = exc.records
            print(f"warning: {exc}")
        report = paper_account_report.write_report()
        if args.commit:
            tokens = [
                paper.TOKENS / f"{r['record_hash']}.{a}.tsr"
                for r in stored
                for a in ("freetsa", "sectigo")
            ]
            n_orders = sum(r["type"] == acct.ORDER for r in recs)
            print(
                paper.commit_and_push(
                    [acct.LEDGER, report, *[t for t in tokens if t.exists()], *extra],
                    f"paper account: {len(recs)} record(s), {n_orders} new order(s)",
                    trailer,
                )
            )
        return 0
    elif args.cmd in (
        "paper-book-plan",
        "paper-book-score",
        "paper-book-report",
        "paper-book-confirm",
    ):
        import os
        from datetime import datetime, timezone

        from . import paper, paper_book as book

        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "paper-book-report":
            path = book.write_report()
            print(path.read_text(encoding="utf-8"))
            if args.commit:
                print(paper.commit_and_push([path], "paper book: report", trailer))
            return 0
        now = datetime.now(timezone.utc)
        if args.cmd == "paper-book-plan":
            recs = book.plan_records(now)
            message = f"paper book: {len(recs)} spike(s) planned"
            for r in recs:
                print(
                    f"  {r['ticker']} ({r['signal_session']}): dump tomorrow {r['dump_tomorrow']:.2f} -> {r['verdict']}"
                )
        elif args.cmd == "paper-book-score":
            recs = book.result_records()
            message = f"paper book: {len(recs)} trade(s) closed"
            for r in recs:
                net = f"{r['net_return']:+.2%}" if r["net_return"] is not None else r["reason"]
                print(f"  {r['ticker']}: {r['status']} {net}")
        else:
            try:
                recs = [book.confirm_record(args.ticker, args.decision, now)]
            except ValueError as exc:
                print(f"error: {exc}")
                return 2
            message = f"paper book: owner {args.decision} {recs[0]['ticker']}"
            print(f"  recorded: {args.decision} {recs[0]['ticker']} ({recs[0]['set_id']})")
        if not recs:
            print("paper book: nothing new; nothing recorded")
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        try:
            stored = paper.append(recs, path=book.LEDGER, timestamper=RFC3161Timestamper())
        except paper.ReceiptPendingError as exc:
            stored = exc.records
            print(f"warning: {exc}")
        report = book.write_report()
        if args.commit:
            tokens = [
                paper.TOKENS / f"{r['record_hash']}.{a}.tsr"
                for r in stored
                for a in ("freetsa", "sectigo")
            ]
            print(
                paper.commit_and_push(
                    [book.LEDGER, report, *[t for t in tokens if t.exists()]], message, trailer
                )
            )
        return 0
    elif args.cmd in ("premove-shadow-forecast", "premove-shadow-score", "premove-shadow-report"):
        import os

        from . import paper, premove_shadow as shadow

        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "premove-shadow-report":
            path = shadow.write_report()
            print(path.read_text(encoding="utf-8"))
            if args.commit:
                print(paper.commit_and_push([path], "pre-move shadow trial: report", trailer))
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        manifest, _ = _recent_manifest("CRYPTO", max_age_hours=6)
        if args.cmd == "premove-shadow-forecast":
            record = shadow.forecast(manifest)
            if record is None:
                print(
                    "pre-move shadow: this day is already sealed or outside the trial; nothing recorded"
                )
                return 0
            recs = [record]
            message = f"pre-move shadow trial: day {record['decision_date']} sealed (3 arms)"
            for arm in shadow.ARMS:
                print(
                    f"{arm}: " + ", ".join(x["ticker"] for x in record["shortlists"]["early"][arm])
                )
        else:
            recs = shadow.score(manifest)
            if not recs:
                print(
                    "pre-move shadow: no sealed day has its five outcome bars yet; nothing recorded"
                )
                return 0
            message = f"pre-move shadow trial: {len(recs)} day(s) resolved"
            for r in recs:
                print(f"{r['decision_date']}: resolved, {r['unknown']} candidate(s) unknown")
        try:
            stored = paper.append(recs, path=shadow.LEDGER, timestamper=RFC3161Timestamper())
        except paper.ReceiptPendingError as exc:
            stored = exc.records
            print(f"warning: {exc}")
        report = shadow.write_report()
        if args.commit:
            tokens = [
                paper.TOKENS / f"{r['record_hash']}.{a}.tsr"
                for r in stored
                for a in ("freetsa", "sectigo")
            ]
            paths = [shadow.LEDGER, report, *[t for t in tokens if t.exists()]]
            print(paper.commit_and_push(paths, message, trailer))
        return 0
    elif args.cmd in ("speculate", "speculate-score", "speculate-report"):
        import os
        from datetime import datetime, timezone

        from . import paper, speculation

        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "speculate-report":
            path = speculation.write_report()
            stats = speculation.statistics()
            for mk, m in stats["markets"].items():
                v = m["plan"]
                print(
                    f"{mk}: {m['n_sets']} sets, {m['sessions']} sessions. {speculation.PLAN}: {v['n_paired']} paired, "
                    f"diff {speculation._pct(v['mean_diff'])}, {v['verdict']}; PATH20 resolved {m['n_path20_resolved']}"
                )
            if args.cards:
                for s in [r for r in speculation.spec_lines() if r["type"] == "SPECULATION_SET"][
                    -12:
                ]:
                    print(speculation.card(s))
            print(path)
            if args.commit:
                print(paper.commit_and_push([path], "speculation register: report", trailer))
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        mk = args.market
        stamper = RFC3161Timestamper()
        if args.cmd == "speculate":
            now = datetime.now(timezone.utc)
            pending = speculation.pending_decisions(mk, now)
            if not pending:
                print(
                    f"{mk}: no decision awaiting a speculation set before its entry cutoff; nothing recorded"
                )
                return 0
            written, sets = speculation.seal(
                mk, now, stamper, quotes=paper.binance_quotes if mk == "CRYPTO" else None
            )
            for s in sets:
                print(speculation.card(s))
            print(f"sealed {len(sets)} set(s) for {mk}")
            message = f"speculation register: {len(sets)} set(s) sealed for {mk} {sets[0]['signal_session']}"
            extra = []
        else:
            todo = speculation.due(mk)
            if not todo:
                print(
                    f"no {mk} speculation window can have ended yet; nothing pulled, nothing recorded"
                )
                return 0
            manifest, extra = (
                (Path(args.manifest), [])
                if args.manifest
                else _recent_manifest(mk, args.max_age_hours)
            )
            verify = _sec_verifier() if mk == "US" else None
            written, outcomes = speculation.resolve_pending(manifest, mk, stamper, verify=verify)
            n_bad = sum(o.get("status") == "UNRESOLVABLE" for o in outcomes)
            print(
                f"resolved {len(outcomes) - n_bad} (set, window) pair(s), {n_bad} unresolvable, {len(todo) - len(outcomes)} still open"
            )
            for o in outcomes:
                pr = o.get("paired") or {}
                c = (o.get("candidate") or {}).get("status", "")
                cone = ", ".join(
                    f"{x['id']}={'?' if x['outcome'] is None else int(x['outcome'])}"
                    for x in o.get("cone", [])
                )
                print(
                    f"  {o['set_id']} {o['window']}: {o['status']} {c} {o.get('reason', '')}"
                    + (
                        f" net {pr['candidate_net']:+.2%} vs twins {pr['twins_mean_net']:+.2%}"
                        if pr
                        else ""
                    )
                    + (f" [{cone}]" if cone else "")
                )
            message = f"speculation register: {len(outcomes)} resolution(s) for {mk}, {n_bad} unresolvable"
            if written:
                written = [*written, manifest]
        if written:
            written.append(speculation.write_report())
        if args.commit and written:
            print(paper.commit_and_push([*written, *extra], message, trailer))
    elif args.cmd in ("learner-forecast", "learner-report", "learner2-forecast", "learner2-report"):
        import os
        from datetime import datetime, timezone

        from . import learner2, paper

        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd.startswith("learner-"):
            print("LEARNER_v1 is withdrawn (research/LEARNER_v1/ADDENDUM_1.md); running LEARNER_v2")
        if args.cmd.endswith("-report"):
            path = learner2.write_report()
            print(path.read_text(encoding="utf-8"))
            if args.commit:
                print(paper.commit_and_push([path], "learner v2: report", trailer))
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        recs = learner2.forecast_records(datetime.now(timezone.utc))
        if not recs:
            print("no sealed set awaiting a learner forecast before its cutoff; nothing recorded")
            return 0
        print(
            "  earned confidence: "
            + ", ".join(f"{k} {v['alpha']:.2f}" for k, v in recs[0]["gate"].items())
        )
        for r in recs:
            skill = {k: v for k, v in r["forecasts"].items() if v["kind"] != "ABSOLUTE"}
            shown = {
                k: v
                for k, v in skill.items()
                if v["call"]["side"] or abs(v["raw"] - v["anchor"]) >= 0.05
            }
            print(
                f"  {r['set_id']} ({r['ticker']}): {len(skill) - len(shown)} of {len(skill)} skill statements within "
                "0.05 of their anchors"
            )
            for stmt, fc in shown.items():
                c = fc["call"]
                why = "; ".join(f"{w['label']} {w['logit']:+.2f}" for w in fc["why"])
                print(
                    f"    {stmt}: anchor {fc['anchor']:.3f}, learner {fc['raw']:.3f} (90% {fc['raw_90'][0]:.2f}-"
                    f"{fc['raw_90'][1]:.2f}), published {fc['published']:.3f}"
                    + (
                        f"; {'LIVE' if c['live'] else 'shadow'} {c['side']} call: {c['thesis']}"
                        if c["side"]
                        else ""
                    )
                    + (f" [{why}]" if why else "")
                )
        written, _ = learner2.append(recs, RFC3161Timestamper())
        written.append(learner2.write_report())
        if args.commit:
            print(
                paper.commit_and_push(
                    written, f"learner v2: {len(recs)} forecast(s) sealed", trailer
                )
            )
    elif args.cmd in ("learner3-forecast", "learner3-report", "learner3-freeze"):
        import os
        from datetime import datetime, timezone

        from . import learner3, paper

        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "learner3-freeze":
            frozen = learner3.freeze_evaluations()
            print(f"{len(frozen)} planned evaluation/review record(s) appended")
            if args.commit and frozen:
                print(
                    paper.commit_and_push(
                        [learner3.evaluation.LEDGER],
                        "learner v2.4: freeze planned evaluations",
                        trailer,
                    )
                )
            return 0
        if args.cmd == "learner3-report":
            path = learner3.write_report()
            print(path.read_text(encoding="utf-8"))
            if args.commit:
                print(paper.commit_and_push([path], "learner v2.4: report", trailer))
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        recs, notes = learner3.forecast_records(datetime.now(timezone.utc))
        for n in notes:
            print("  " + n)
        if not recs:
            print(
                "no US speculation set awaiting a v2.4 forecast before its cutoff; nothing recorded"
            )
            return 0
        print(
            "  earned confidence: "
            + ", ".join(f"{k} {v['alpha']:.2f}" for k, v in recs[0]["gate"].items())
        )
        for r in recs:
            print("  " + learner3.one_line(r))
        written, _ = learner3.append(recs, RFC3161Timestamper())
        written.append(learner3.write_report())
        if args.commit:
            print(
                paper.commit_and_push(
                    written, f"learner v2.4: {len(recs)} forecast(s) sealed", trailer
                )
            )
    elif args.cmd == "idea-grade":
        from . import idea_grader

        print(idea_grader.grade_file(Path(args.spec)))
    elif args.cmd == "call-cert-report":
        import os

        from . import call_cert, paper

        path = call_cert.write_report()
        print(path.read_text(encoding="utf-8").split("## Live forecasts")[0])
        if args.commit:
            print(
                paper.commit_and_push(
                    [path],
                    "certified calls: shadow report",
                    os.environ.get("IDXSIG_COMMIT_TRAILER", ""),
                )
            )
    elif args.cmd in ("catalyst-seal", "catalyst-tag", "catalyst-score", "catalyst-report"):
        import os
        from datetime import datetime, timezone

        from . import catalysts, paper

        trailer = os.environ.get("IDXSIG_COMMIT_TRAILER", "")
        if args.cmd == "catalyst-report":
            path = catalysts.write_report()
            print(path.read_text(encoding="utf-8").split("## Latest sets")[0])
            if args.commit:
                print(paper.commit_and_push([path], "catalyst register: report", trailer))
            return 0
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kod-machine"))
        from kod.timestamp import RFC3161Timestamper

        now = datetime.now(timezone.utc)
        extra = []
        if args.cmd == "catalyst-seal":
            if args.family == "SEC13D":
                batch, sets = catalysts.sec13d_batch(now, catalysts.sec_client())
            elif (
                args.family in catalysts.FAMILY_MODULES
            ):  # later families (research/CATALYST_FAMILIES/<family>/)
                batch, sets = catalysts.family_module(args.family).batch(
                    now, catalysts.sec_client()
                )
            else:
                if not args.events:
                    print("catalyst-seal --family IDX_INDEX needs --events <file>")
                    return 2
                events = Path(args.events).resolve()
                batch, sets = catalysts.idx_index_batch(events, now)
                extra.append(events)
            for e in batch["events"]:
                print(
                    f"  {e.get('accession') or e.get('event_id')} {e.get('ticker') or '-'}: {e['status']}"
                    + (f" ({e['reason']})" if e.get("reason") else "")
                    + (f" {e['coverage']}" if e.get("coverage") else "")
                )
            for s in sets:
                print(catalysts.card(s))
            if batch.get("counts"):
                print("  not events: " + ", ".join(f"{k} {v}" for k, v in batch["counts"].items()))
            print(
                f"{args.family}: {len(batch['events'])} new event(s), {len(sets)} set(s) for entry {batch['entry_session']}"
            )
            side = batch.pop(
                "_side_file", None
            )  # FORM4: every filing read, bound into the batch by its sha256
            if args.dry_run:
                print("dry run: nothing appended")
                return 0
            if side:
                side_path = catalysts.PKG_ROOT / side[0]
                side_path.parent.mkdir(parents=True, exist_ok=True)
                side_path.write_bytes(side[1])
                extra.append(side_path)
            if not batch["events"] and args.family == "IDX_INDEX":
                print("no new event; nothing recorded")
                return 0
            written, _ = catalysts.append([batch, *sets], RFC3161Timestamper())
            message = f"catalyst register: {args.family} batch, {len(sets)} set(s) sealed for entry {batch['entry_session']}"
        elif args.cmd == "catalyst-tag":
            todo = catalysts.pending_tags(now)
            if not todo:
                print(
                    "no Speculation Register set awaiting a DILUTION_RECENT tag before its cutoff; nothing recorded"
                )
                return 0
            client = catalysts.sec_client() if any(s["market"] == "US" for s in todo) else None
            from .sensors import fetch as en_fetch

            tags = catalysts.dilution_tags(now, todo, client, en_fetch=en_fetch)
            for t in tags:
                print(
                    f"  {t['set_id']} {t['ticker']}: DILUTION_RECENT={t['value']} ({t['source']}) {t['evidence'][:3]}"
                )
            written, _ = catalysts.append(tags, RFC3161Timestamper())
            message = f"catalyst register: {len(tags)} DILUTION_RECENT tag(s)"
        else:
            mk = args.market
            todo = catalysts.due(mk)
            mech = catalysts.due(mk, mechanism=True)
            if not todo and not mech:
                print(
                    f"no {mk} catalyst window can have ended yet; nothing pulled, nothing recorded"
                )
                return 0
            written, outcomes = [], []
            if todo:
                manifest, extra = (
                    (Path(args.manifest), [])
                    if args.manifest
                    else _recent_manifest(mk, args.max_age_hours)
                )
                verify = _sec_verifier() if mk == "US" else None
                written, outcomes = catalysts.resolve_pending(
                    manifest, mk, RFC3161Timestamper(), verify=verify
                )
                for o in outcomes:
                    pr = o.get("paired") or {}
                    print(
                        f"  {o['set_id']} {o['window']}: {o['status']} {o.get('reason', '')}"
                        + (
                            f" net {pr['candidate_net']:+.2%} vs twins {pr['twins_mean_net']:+.2%}"
                            if pr
                            else ""
                        )
                    )
                print(f"resolved {len(outcomes)} of {len(todo)} due (set, window) pair(s)")
                if written:
                    written = [*written, manifest]
            if mech:  # mechanism statements: EDGAR (with the declared contact) or the register's own batches
                try:
                    client = catalysts.sec_client()
                except RuntimeError:
                    client = None
                    print("no SEC contact declared: mechanism statements that need EDGAR stay due")
                mw, mrecs, waiting = catalysts.resolve_mechanisms(mk, client, RFC3161Timestamper())
                for o in mrecs:
                    print(
                        f"  {o['set_id']} {o['window']}: "
                        + ", ".join(f"{c['id']}={c['outcome']}" for c in o["cone"])
                    )
                print(f"mechanism windows: {len(mrecs)} resolved, {len(waiting)} not gradable yet")
                written = [*written, *[w for w in mw if w not in written]]
                outcomes = [*outcomes, *mrecs]
            message = f"catalyst register: {len(outcomes)} resolution(s) for {mk}"
        if written:
            written.append(catalysts.write_report())
        if args.commit and written:
            print(paper.commit_and_push([*written, *extra], message, trailer))
    elif args.cmd in ("micro-snapshot", "micro-catch-up", "micro-report"):
        import os

        from . import microstructure, paper

        if args.cmd == "micro-report":
            problems = microstructure.verify()
            print(json.dumps(microstructure.summarize(), indent=1))
            print(
                "micro-report integrity: " + ("OK" if not problems else f"{len(problems)} problems")
            )
            for p_ in problems:
                print(f"  {p_}")
            return 1 if problems else 0
        if args.cmd == "micro-snapshot":
            scan_id = args.scan_id or (microstructure.crypto_scans() or [(None, None)])[-1][0]
            if scan_id is None:
                print("no crypto scan with candidates in the ledger")
                return 0
            files = microstructure.run_for_scan(scan_id, books=not args.no_book, timelines=False)
            message = f"microstructure side-car: book for {scan_id}"
        else:
            files = microstructure.catch_up()
            message = "microstructure side-car: timelines"
        print(f"wrote {len(files)} file(s)")
        if args.commit and files:
            print(
                paper.commit_and_push(files, message, os.environ.get("IDXSIG_COMMIT_TRAILER", ""))
            )
    elif args.cmd == "guidance-paper":
        import os
        from datetime import date, datetime, timedelta, timezone

        from . import guidance_paper as gp
        from .us_actions import SecClient, cik_map

        contact = os.environ.get("KOD_SEC_CONTACT", "").strip()
        if "@" not in contact:
            raise SystemExit(
                "error: set KOD_SEC_CONTACT to the owner's contact email (SEC fair-access policy)"
            )
        now = datetime.now(timezone.utc)
        day = date.fromisoformat(args.day) if args.day else (now - timedelta(days=1)).date()
        client = SecClient(
            f"KOD-Machine research {contact}",
            gp.PKG_ROOT / "data" / "raw" / "sec_guidance" / now.strftime("%Y%m%dT%H%M%SZ"),
        )
        universe = gp.etoro_us()
        ciks = {c: t for t, c in cik_map(client).items() if t in universe}
        print(f"universe: {len(ciks)} eToro-listed US stocks with a CIK")
        state = (
            gp.bootstrap(day, client.get, ciks)
            if args.bootstrap or not gp.STATE.exists()
            else gp.load_state()
        )
        decisions, events, state = gp.scan_day(day, state, client.get, ciks, now)
        records = gp.record(decisions, events, day, now, dry_run=not args.record)
        if args.record:
            gp.save_state(state)
        print(
            json.dumps(
                {
                    "day": day.isoformat(),
                    "dry_run": not args.record,
                    "events": len(events),
                    "decisions": [
                        {k: d[k] for k in ("ticker", "accession", "acceptance_ny")}
                        | {"level_change": d["event"]["level_change"]}
                        for d in decisions
                    ],
                    "records": len(records),
                },
                indent=1,
            )
        )
    elif args.cmd == "verify-runs":
        from .results import verify_runs

        problems = verify_runs()
        print("verify-runs: " + ("OK" if not problems else f"{len(problems)} problems"))
        for p in problems:
            print(f"  {p}")
        return 1 if problems else 0
    return 0


def _pull_recent(mk: str) -> tuple[Path, list]:
    """The paper cycle's data pull: ~200 days of bars for every active name of the market."""
    from datetime import date, timedelta

    from . import paper
    from .provenance import MANIFESTS
    from .sources import binance, us_universe, yahoo

    extra = []
    if mk == "IDX":
        manifest = yahoo.fetch(
            paper.active_tickers(), days=paper.HISTORY_DAYS, prefix="yahoo_recent"
        )
    elif mk == "US":
        tickers, universe = us_universe.fetch()
        extra.append(MANIFESTS / universe)
        manifest = yahoo.fetch(
            tickers,
            days=paper.HISTORY_DAYS,
            prefix="yahoo_us_recent",
            suffix="",
            sleep=0.1,
            workers=6,
        )
    else:
        start = (date.today() - timedelta(days=paper.HISTORY_DAYS)).isoformat()
        manifest = binance.fetch(start=start, only_trading=True, prefix="binance_recent")
    return manifest, extra


def _manifest_for_score(mk: str, max_age_hours: float) -> tuple[Path, list]:
    """paper-score's bars: the pull the scan just made if it is recent enough, else a fresh pull.
    The routine runs paper-scan and then paper-score minutes apart; pulling the same ~33 MB of bars twice
    filled the disk. max_age_hours <= 0 keeps the old behaviour (always pull)."""
    if max_age_hours and max_age_hours > 0:
        return _recent_manifest(mk, max_age_hours)
    return _pull_recent(mk)


def _recent_manifest(mk: str, max_age_hours: float) -> tuple[Path, list]:
    """The latest recent-bars manifest of the market if it was pulled within `max_age_hours`, else a new pull.
    Lets the speculation register reuse the bars paper-score just pulled instead of pulling them again."""
    from datetime import datetime, timezone

    from .provenance import latest_manifest

    prefix = {"IDX": "yahoo_recent", "US": "yahoo_us_recent", "CRYPTO": "binance_recent"}[mk]
    try:
        latest = latest_manifest(prefix)
        stamp = datetime.strptime(latest.stem.rsplit("-", 1)[1], "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
        if datetime.now(timezone.utc) - stamp <= __import__("datetime").timedelta(
            hours=max_age_hours
        ):
            return latest, []
    except (FileNotFoundError, ValueError, IndexError):
        pass
    return _pull_recent(mk)


def _sec_verifier():
    """A split-event verifier against SEC filings, as paper-score uses (needs IDXSIG_SEC_USER_AGENT)."""
    import os

    from . import us_actions
    from .provenance import RAW, utc_stamp as _stamp

    client = us_actions.SecClient(
        os.environ.get("IDXSIG_SEC_USER_AGENT", us_actions.DEFAULT_USER_AGENT),
        RAW / "sec" / _stamp().replace("-", "").replace(":", ""),
    )
    ciks = {}

    def verify(ev):
        if not ciks:
            ciks.update(us_actions.cik_map(client))
        res = us_actions.verify_event(
            client, ciks, ev.ticker, ev.effective_session, ev.numerator, ev.denominator, ev.kind
        )
        return res["status"], res["evidence"]

    return verify


def _micro_sidecar(scan_id: str) -> list:
    """Book cost for the new crypto scan's candidates, then the timelines that are due (idxsig.microstructure). Read
    only: it changes no rule and no ledger line, and a failure here must never stop the paper cycle."""
    try:
        from . import microstructure

        files = [*microstructure.run_for_scan(scan_id, timelines=False), *microstructure.catch_up()]
        return list(dict.fromkeys(files))
    except Exception as exc:  # noqa: BLE001
        print(f"warning: microstructure side-car skipped: {exc}", file=sys.stderr)
        return []


if __name__ == "__main__":
    raise SystemExit(main())
