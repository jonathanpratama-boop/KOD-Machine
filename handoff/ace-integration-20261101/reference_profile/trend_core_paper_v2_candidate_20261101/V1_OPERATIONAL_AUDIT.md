# TREND_CORE v1 operational audit — 2026-11-01

Inspected remote HEAD `48d18b8ecae67bdeeb07a47f1772903a5381782b` in
`jonathanpratama-boop/KOD-Machine`, default `claude/idx-signals-test-repo-ds0jw7`.

**Verdict: functioning signal logger, not an implemented paper account.**
SMA10/40 may remain a historical research candidate; its independent per-asset 0/1
backtest does not validate a volatility-targeted pooled account or its kill rules.

## Verified operation

`.github/workflows/trend_core_paper.yml` has cron `41 2 * * *` (02:41 UTC), manual
dispatch, serialized runs, and `contents: write`. Manual Actions run
[41293156436](https://github.com/jonathanpratama-boop/KOD-Machine/actions/runs/41293156436)
succeeded on `e6a6b5f416594140915cddbf4111f9de8e1d0976`; logs confirm repository write
permission and bot commit `150440aacaadbdfbe948186fcf7b6e849245dadf`. This is manual
success, not evidence that cron has fired. Workflow registry GET was rejected by the
connector allowlist, so enabled state could not be independently read; no bypass.

No order-placement/exchange-credential path or Claude API invocation appeared in the
inspected workflow/dependencies. This supports deterministic logging without Claude
inference, not a verified zero infrastructure bill. No private billing was inspected.
Current-HEAD checks run 41293292988 was still running at this agent's 09:35 cutoff;
the coordinating audit subsequently verified all four jobs passed. Ordinary CI is
not semantic acceptance of the new paper account. No CI was triggered by this audit.

## Defects and evidence

- Protocol executes day-t signals from t+1 midnight, but the workflow fetches prior-day
  archives at 02:41 and first rows were logged at 09:24. That midnight is a historical
  reference, not an executable future fill. No P&L is calculated, so this is a latent
  execution-contract defect, not an assertion that fabricated profit was recorded.
- `paper/log_decision.py` independently computes min(1,.015/sigma20) per coin. Raw
  targets can sum to2; there is no shared-cash cap implementation. No actual account
  exists, so this is not proof that leverage was deployed.
- No simulated fills, quantities, initial cash, fee debits, cash/NAV, returns, peak,
  drawdown or 90-day-Sharpe kill. `HOLD` is previous signal comparison, not actual
  holdings. Changing volatility can require a rebalance despite unchanged LONG.
- Four ledger rows contain two unique symbol/date decisions (Oct31 BTC and ETH).
  All hash links validate. Manual run appended the duplicates; HEAD `48d18b8` then
  added a skip guard. Existing rows are preserved exactly in the companion snapshot.
- Protocol SHA256 matches `PINS.json`: e48ddf92c37ec51ea3ba53aecfa0562f1e99d5939dbb365e6e1e9da1816b8812.
  Protocol/pins/initial rows first entered Git together in e6a6b5f. Internal
  pinned_utc09:24:07 and logged_utc09:24:18 are not independent preregistration proof.
- Code/runtime dependencies are not pinned or verified; daily input bytes/hash receipts
  are not retained. Existing `tools/check_append_only.py` excludes this directory;
  bot commits use `[skip ci]`; the paper workflow checks neither chain nor pins.
- Only final data date is checked, not clean contiguous history. Whole skipped runs
  leave no MISSED record; MISSED rows lack logged_utc; internal daily fetch gaps can
  affect rolling windows; git push has no conflict/retry recovery.

## Repair status / authority boundary

The sibling local v2 candidate implements a new synthetic-only account slice and
preserves all original v1 bytes. Separate duplicate metadata references line3→1 and
line4→2. None of these historical observations becomes a retrospective fill.
Live source capture and workflow activation remain unsupported/not performed. A new
forward account must use its real future decision/observation clock after separate
adapter acceptance. Ninety days can test implementation, not establish an edge.

No workflow was edited/paused/deleted/rerun, no remote file was written, no orders
were placed. The repository decision note leaves Moonshot-task retention open; it
is not proof of a pause and not authorization for this assistant to pause anything.

Sources: pinned commit files `handoff/fresh-eyes-2026-11-01/paper/`, workflow above,
`tools/check_append_only.py`, `backtests/run_t1_t5.py`, `backtests/lib.py`; Actions
job124808421270 logs and exact path commit history. No raw 2024+ bars were read.
