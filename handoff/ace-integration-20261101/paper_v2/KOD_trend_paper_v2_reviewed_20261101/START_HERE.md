# KOD: keep the candidate; repair the paper contract

## Decision

**Keep ETH SMA10/40 as a historical research candidate, not independently confirmed
alpha. Treat TREND_CORE v1 as a signal logger, not an operational paper account.**
BTC SMA10/40 is WEAK under the published gate. The local v2 implementation below is
an actual functioning offline account slice, but a NEW pooled/risk-sized contract—
not the per-asset 0/1 backtest and not a production/forward trial.

## Audit findings that matter

- The eToro “neither coin beats buy-and-hold” claim contradicts the published ETH
  figures. Do not use that claim as proof a venue switch is necessary.
- Initial capital was omitted from backtest/simulation drawdown peaks. T3 has a
  future-total-history eligibility filter and target-to-target rather than holdings-
  based turnover. Existing T3/T4 disclosed corrections are not consistently present
  in published code/JSON. Frozen originals remain untouched; no raw outcomes rerun.
- “Sharpe 3 at 5x” is conditional simulation arithmetic, not a universal requirement.
  Touching 10x, finishing 10x and getting there before a drawdown differ. 4–5-year
  growth claims are not supported by a corresponding simulation.
- Paper v1 logged two BTC/ETH signal decisions twice; has no shared-cash account,
  fills, costs, NAV or kill implementation. Its historical next-day-midnight open
  precedes actual archive receipt/decision. A green job does not solve those gaps.

Read the included independent backtest, T2/T6 and paper operational audits for
source references, precise qualifications and what was NOT independently verified.

## What is now implemented locally

- Deterministic SMA10/40 and 20-return volatility with strict completed/consecutive
  bar/availability/hash checks; shared 1k/10k synthetic cash, targets normalized down
  when their sum exceeds 1, actual-holdings rebalancing, sell-before-buy sequencing.
- Explicit cash total/reserved/free; future-observation fills, scenario costs,
  quantity caps/unknown-liquidity refusal, no shorts/borrowing; complete NAV with
  missing marks propagated and increased-risk fills blocked while NAV is unknown.
- Initial-equity peak, persistent 25% DD / negative 90-return Sharpe kill, strictly
  future observed liquidation of actual held quantities, residual holdings retained.
- Append-only hash journal, stable retry IDs, replay/pin checks, operation locking,
  tested fsync-retry barriers, missing cycles, and preserved v1 duplicate metadata.
- Reused existing local paper_cash_v1 accounting/hash primitives rather than create
  a general market-data backtester. All executable acceptance inputs are synthetic.

Independent review found and reproduced three defects during development: missing-
NAV buy fills, cross-symbol sell-before-buy ordering, and an uncertain-fsync retry
without a new barrier. Each was repaired with regression coverage before delivery.
See the independent acceptance report/test receipts for final exact counts/hashes.

## Runnable path and next gate

Start with `trend_core_paper_v2_candidate_20261101/README.md`. The candidate/tests/demo
need only Python 3.12/POSIX. Historical-audit synthetic reproducers additionally need
NumPy/Pandas and NEVER invoke raw-market loaders. These are separate acceptance
tracks; passing one is not parity evidence for another.

**Unsupported, explicitly rejected:** live source adapters, external/trusted receipt
clocks, broker orders, CFDs/perpetuals/leverage, unknown-liquidity fills and backdated
executions. Trusted raw capture, venue applicability/quantity constraints, external
anchors, scheduler/storage/recovery/monitoring adapters and a separate activation
review are still needed before a real forward paper trial. No remote workflow,
Mac/Claude integration, scheduled-task pause or publication was performed.

Use this handoff as one reviewed engineering candidate. Do not import historical
v1 signal rows as trades, silently replace its protocol, or call 90 days of paper
logs proof of edge. No real-money trading is authorized.

## Final acceptance receipt

30 unit tests passed in normal and optimized Python (18 author + 12 independent),
plus two additional real-process race cases. Relocated bundle tests and repeated
synthetic demo passed. Both included audit reproducers ran using synthetic inputs /
published aggregates only. See VERIFICATION/receipt.json and independent REVIEW.md.

Run from bundle root:
```sh
python trend-independent-audit/run_combined.py
python -O trend-independent-audit/run_combined.py
python trend-independent-audit/multiprocess.py
python trend_core_paper_v2_candidate_20261101/demo.py --output-dir /tmp/trend-v2-demo
```
