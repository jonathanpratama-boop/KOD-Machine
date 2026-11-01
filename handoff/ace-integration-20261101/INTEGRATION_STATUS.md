# Ace → KOD integration status (2026-11-01, local only)

Branch `integrate/trend-account-20261101` in worktree `/home/user/kod-integrate`. Not pushed, merged, deployed or
scheduled. Simulation only; no credentials, orders or network requests were used.

**Base and inputs.** The branch is based on remote tip `aa993e8` plus 14 local research commits (merge `d54104f`). The kit
is `KOD_Ace_Claude_integration_kit_20261101.zip`, sha256 `0bd94ffc241636f056b88db801b93a5e2ac9e8ff28e8d9ac40c79cce510f3881`.
All 55 entries of its `SHA256SUMS.txt` verified.

**Environment.** Python 3.13.16, numpy 2.5.3, pandas 3.0.5, exchange_calendars 4.5.6. Ace's evidence was produced on
Python 3.12, numpy 2.3.5 and pandas 2.2.3.

## What was integrated

| Component | How | Commit |
|---|---|---|
| Engineering repair v1.4 (crypto failed-fetch, quote validation, phase CAS, paper execution feasibility) | Consolidated patch `KOD-reviewed-integration-v1.4-from-7aad431.patch` (sha256 `95264ba3…503e`), applied with `git apply`. Its base `7aad431` is an ancestor of HEAD, and the 3 modified files were byte-identical to that base. All 18 affected files match `affected-files.json`. CRYPTO_ACCOUNT v1/v1.1 protocols are untouched; v1.2-v1.4 are added beside them | `a47d70e` |
| Trend paper-account v2 (shared cash, reservations, fills after decisions, fees, exposure normalisation, persistent kill, hash journal, locking) | Original bundle extracted unchanged into `paper_v2/` | `7990850` |
| Coinbase reference data adapter, plus the connected `run_once.py` path (adapter → v2 core signal and shared account → journal) | `reference_profile/` copied unchanged. The source is **OFF** by default | `7990850` |
| Historical shared-account proof | Original archive in `originals/` (sha256 `6ec9f6f8…3037`), plus extracted code, pins, summaries and audits in `historical/` (its 8 large derived journals live only in the archive) | `7990850` |

The v1 signal logger (`handoff/fresh-eyes-2026-11-01/paper/`) is unchanged. Its protocol, ledger, logger and pins match
Ace's preserved hashes, including the duplicated 2026-10-31 rows, which are classified by
`paper_v2/.../v1/DUPLICATE_AUDIT_METADATA.json` and never treated as fills. No frozen protocol, ledger or experiment
was edited. No integration code change to Ace's files was needed, so every hash pin and review clearance stays valid.

All three account profiles vendor the same reviewed core:
- `paper_candidate.py`, sha256 `dbda12d4…34c3`;
- the same cash accounting, sha256 `29688797…f8a6`.

The historical replay and the reference adapter differ from it only through their documented profile diffs
(`CORE_PROFILE_DIFF.patch`). They are one account contract:
- SMA 10/40;
- 20-return volatility targets, normalised down within shared cash;
- persistent 25% drawdown / negative 90-day Sharpe kill.

## Tests run in this checkout

`sh handoff/ace-integration-20261101/run_all_checks.sh` from the repo root passes end to end.

| Suite | Result |
|---|---|
| Repair-affected idx-signals tests (crypto account, concurrency, quote validation, valuation as-of, execution feasibility, paper account, crypto replay) | 113 OK |
| Trend paper v2 (18 author + 12 independent), normal and `-O` | 30 OK each |
| Two real-process races (duplicate fill observation; disjoint coin fills) | both replay-verified |
| Fixture demo run twice into the same directory | journals byte-identical on retry, so no duplicate fills |
| Reference adapter and `run_once` path, network blocked, normal and `-O` | 48 OK each |
| `run_once.py` with no flags | refuses (default OFF) and creates nothing |
| Historical proof, 13 author + 14 independent tests, normal and `-O` | 27 OK each |
| `verify_results.py` on the journals from the pinned archive | all 8 cases PASS; `RESULTS.json` sha256 `142c1074…324f` as published |
| Full idx-signals suite (`python3 -m unittest discover -s tests -t .`) | 1,262 tests, 8 errors, all outside the integration (see below) |

**Required behaviours, covered by the tests above.**
- **Quote failures and staleness.** A refused source stops with no retry and no account. Transport errors are reported,
  not echoed. A stale mark on another held symbol blocks buys. Unknown NAV propagates rather than defaulting to cost.
  A regressing source time fails closed.
- **Duplicate events.** A retry replays; a conflicting retry is refused. No quote fills twice. Duplicate headers are
  handled.
- **Concurrent runs.** The same operation is applied once, also across real processes.
- **Cash reconciliation.** Shared-cash conservation holds with all-in fees and partial fills.
- **Persistent stop state.** The kill persists across restarts with no automatic reset. Residual holdings are kept until
  a later sell observation can support their sale.

**The 8 full-suite errors are not caused by the integration.** They are in `tests.test_guidance_revision` (6) and
`tests.test_premove_evaluation` (2). Neither module imports anything the repair changed (`cli.py`, `crypto_account.py`,
`paper_execution_feasibility.py`).
- **Causes:** exchange_calendars 4.5.6 raises `NotSessionError` for XNYS 2026-10-15 and 2026-10-19 in calendar
  construction. pandas 3.0.5 raises `TypeError: Cannot cast DatetimeArray to dtype float64`.
- **Not reproduced on the base commit.** Re-running the two modules on `d54104f` was attempted but blocked: the disk
  allowance was full, and a shared `/tmp` clean-up was refused.
- **Left as found.** Tests were not edited to hide them.

## Historical account contract: what the integrated strategy is and is not

The integrated paper account is the **v2 shared-cash portfolio contract** (risk-sized, normalised targets on one cash
balance). It is not the standalone per-asset 0/1 SMA backtest of FRESH_EYES_v1. That backtest does not validate this
account policy, and this integration does not claim it does.

The frozen historical replay of this exact contract is preserved unchanged. Ending NAVs from USD 10,000:

| Window | Trend v2 shared | Passive, same kills | Buy-and-hold, no kill |
|---|---|---|---|
| Development 2017-09 .. 2023-01 | 20,593 | 17,844 | 24,501 |
| Validation 2023-01 .. 2026-09 | 12,377 | 15,038 | 36,220 |

- **The loss rule stopped trading early.** It killed the trend account on 2018-03-15 and on 2023-04-22 (negative 90-day
  Sharpe), and the account stayed in cash afterwards.
- **Validation:** the trend account trailed both passive controls.
- **Development:** the risk-matched passive control was capacity-limited to 45.31% exposure.

No parameter, risk rule or comparator was tuned in this integration.

## Blocked and remaining

- **Fresh public-data cycle: not attempted.** The only implemented live-data route is the Coinbase `--public-once`
  capture. Ace's one authorised attempt (2026-11-01T11:07Z) stopped with `URLError` before any response
  (`reference_profile/coinbase_reference_capture_20261101T1107/`). The kit states that its clearance is not renewed
  permission to retry, so no permitted public-data access exists for this path. A retry needs a new independent review
  clearance and your explicit go-ahead.
- **Not built (by design of the reviewed candidate):**
  - trusted receipt clock, raw-byte persistence and external anchoring for a forward trial;
  - venue lot and minimum-notional applicability for Binance USDT;
  - scheduler, missed-cycle monitoring and recovery;
  - a separate activation review.
  The existing GitHub workflow for v1 signal logging is unchanged and still only logs signals.
- **Audit corrections still to fold into `backtests/run_t2_t3_t4.py`** (zero-volume last bars; standalone T4a). Ace's
  handoff lists them as open. They change no verdict, and this task did not edit the frozen engine.
