# Handoff: FRESH_EYES_v1 and TREND_CORE_PAPER_v1 (state as of 2026-11-01, 09:40 UTC)

Written for the next agent (Ace) taking over KOD-Machine research. Self-contained; read this before anything else in this
folder.

## 1. Where things stand

- **Core hypothesis changed.** The +30%-in-1-to-5-sessions spot-long detector line is no longer the machine's core. The core
  candidate is slow trend following (SMA 10/40, long or cash) on BTC and ETH spot on Binance. Owner decision:
  `handoff/decisions/2026-11-01b_…` and `2026-11-01c_…`.
- **Evidence base.** FRESH_EYES_v1 (`backtests/PROTOCOL.md`, pinned in commit 5b3d7c2 before any return was read; run once;
  audited in `backtests/AUDIT.md`). One mechanism passed at Binance costs: ETH SMA 10/40 (validation 2023-01 to 2026-09:
  Sharpe 1.15 against 0.65 for holding ETH; maximum drawdown 37% against 68%). BTC SMA 10/40 was a near-pass (Sharpe 1.12
  against 1.16; drawdown 37% against 53%). Funding carry, altcoin cross-sectional momentum and hourly mean reversion failed.
  Full tables: `backtests/RESULT.md`. Narrative and reasoning: `FRESH_EYES_VERDICT.md`.
- **Paper trial running.** TREND_CORE_PAPER_v1 (`paper/PAPER_PROTOCOL.md`, hash in `paper/PINS.json`). First signal date
  2026-10-31: CASH for both coins. Ledger: `paper/ledger.jsonl` (append-only, hash-chained, one line per coin per UTC day).
- **Automation.** `.github/workflows/trend_core_paper.yml` runs daily at 02:41 UTC on GitHub Actions (no Claude usage),
  fetches the Binance Vision daily files, runs `paper/log_decision.py`, and commits the ledger line. Tested once by manual
  dispatch on 2026-11-01 (run 41293156436, success). `log_decision.py` is idempotent: a signal date already in the ledger is
  skipped.

## 2. Open work, in priority order

1. **Exchange rule-change event register (approved research line).** Freeze a dated protocol before reading any
   announcement text or price (requirements are listed in `handoff/decisions/2026-11-01c_…`, item 2). The lab's earlier
   announcement work (`idx-signals/research/BINANCE_ANN_1M`, `BINANCE_ANN_1S`, `BINANCE_ANN_1S_HOLDOUT`) holds a catalog
   fetcher and parser that can be reused; note that the futures-launch event type it tested has largely disappeared since 2025.
2. **Watch the paper ledger.** Check weekly that the workflow committed a line for every day, that no line was back-filled,
   and that the kill criterion (25% drawdown, or 90-day Sharpe below zero) has not fired. Do not change the rule or the risk
   layer; any change is a new protocol.
3. **Audit corrections not yet folded into code.** In `backtests/run_t2_t3_t4.py`, a symbol's last bar should be its last bar
   with positive volume (Binance Vision publishes frozen zero-volume bars after delisting), and T4a should be run standalone
   rather than as a subset of T4b. The audit re-ran both and no verdict changed; fix them before reusing the engine.
4. **Two Moonshot scheduled tasks are still enabled** ("Moonshot pre-open scan (v3)" and "Moonshot post-close log (v3)"). The
   owner approved pausing them but the platform refused the change from this session; the owner is disabling them manually.
   The weekly review is already disabled.

## 3. Rules that must hold

- Paper only. No exchange credentials, no orders, no deposits.
- Freeze before results: protocol written and hashed before any return is read; run once; a failure is reported as it is.
- The lab's sealed crypto holdout (2024-01-01 onward) is recorded as largely spent; FRESH_EYES_v1 tuned nothing on it. New
  tests on 2023+ data must state that it has been seen by the lab.
- LLM output never enters a position or a size. LLMs may parse text into registers that a frozen rule reads.
- Append-only records are enforced by `.githooks/pre-commit` and CI (`git config core.hooksPath .githooks` once per clone).

## 4. Known limits

- A 90-day paper record cannot confirm a Sharpe-1 strategy (the standard error of a 90-day Sharpe is about 2). It can catch
  implementation errors and show the rule runs as frozen.
- The ETH TSMOM (T1b) pass depends on the re-evaluation phase (three of five phases pass); SMA 10/40 has no such dependence and
  is the rule carried into paper.
- At eToro's 1% a side, the SMA 10/40 rule still trades (about five round trips a year) but no longer beats buy-and-hold on
  Sharpe for either coin. Binance is the venue of record.
- Growth arithmetic (T6): reaching 10x within a year with better-than-even odds and without a 50% drawdown first requires a
  strategy near Sharpe 3 at about 5x leverage; the validated edge is about Sharpe 1.1-1.2.

## 5. Where the data is

Raw Binance Vision files are not in git. Manifests with sha256 per file are in `backtests/manifests/`. To rebuild:
`python3 backtests/fetch_binance_vision.py fetch <spot|um> <klines|fundingRate> <symbols-file|ALL_USDT> [interval] [start YYYY-MM]`
with `BINANCE_RAW` set to a directory outside the repo. The full pull used on 2026-11-01 was about 46,000 files.
