# EXEC_US_v2_1: the contract after Ace's review of v2

Ace audited commit `21eb6aa` (EXEC-US-v2) and asked for changes before merge. Ace reproduced five
defects, none covered by the 233 tests that passed. This directory fixes them as EXEC-US-v2.1.
Each fix has a regression test that fails on the v2 code and passes now. The demonstration is
regenerated for the correct dates, against a stricter forward test.

`research/EXEC_US_v2/` is append-only and stays as the record of v2. Section 3 below corrects
what its README claimed.

## 1. Findings, fixes and regression tests

`regressions.py` runs each test against a scratch checkout of `21eb6aa` and against the current
code, and writes the results to `regressions.json`.

| Priority | Finding (Ace) | Cause in v2 | Fix in v2.1 | Test (`tests/test_contract.py`) | At `21eb6aa` | Now |
|---|---|---|---|---|---|---|
| P1 | Saved orders can trade the wrong stock; a rolling date window reports a new session as already processed | State held row and column numbers | State holds tickers and dates only. Rows are resolved by ticker in each download, and sessions are compared by date | `test_saved_orders_follow_the_ticker_not_the_row`, `test_a_rolling_window_download_is_not_already_processed` | ERROR: the $100 order filled against the $50 stock; "session 2024-01-31 already processed" | PASS |
| P1 | A provider's split re-adjustment corrupts holdings: false stop, artificial loss | Quantities and stops were stored on the adjusted-price basis of the download that created them | Stored as traded in a named session, and carried forward through F[from] / F[today] of the current download. No adjusted basis is stored | `test_a_split_readjusted_download_keeps_the_holding` | FAIL: `STOP_GAP_AT_OPEN` on the split day, instead of the time exit with the holding doubled | PASS |
| P2 | Sizing understates costs across fee tiers | Exit cost taken at the entry price's tier | Risk per share = worst over the band of p × (1 + buy cost at p) − stop × (1 − sell cost at the stop). Tier boundaries inside the band are checked, and the reservation uses the same candidates | `test_planned_risk_covers_the_exit_cost_tier_at_the_stop` | FAIL: lost $106.08 against $99.96 planned | PASS |
| P2 | Exits can fill on a zero-volume day | The exit guard checked only for a finite close | "Traded" means listed, volume above zero and a finite close. No stop or time exit fills otherwise, and the hold still counts the session | `test_no_exit_on_a_session_without_trades` | FAIL: a `STOP` triggered by a stale low on a zero-volume day | PASS |
| P2 | The demo includes an extra session | `full.slice(lo, hi + 1)`, but `bounds()` already returns an exclusive end | `window()` uses the exclusive end, and the demo exits non-zero unless it processed exactly the declared sessions | `DemoWindow.test_demo_window_ends_on_the_declared_session` | The v2 trace processed 2023-09-25 .. **2023-10-23**, 21 sessions, against a declared 2023-10-20 | PASS. The v2.1 trace processes 2023-09-25 .. 2023-10-20, 20 sessions |

The tests reproduce Ace's numbers exactly: $106.08 against $99.96, and the 21st session
2023-10-23. All of these rules are contract rules, so the version is now `EXEC-US-v2.1`. A state
saved under v2 is refused.

## 2. Demonstration (regenerated)

```sh
cd idx-signals && python3 research/EXEC_US_v2_1/demo.py   # about 5 minutes; exit 0 only if every check passes
```

It writes `TRACE.md` (readable), `trace.json` (machine-readable, with the forward ledger) and
`tests.txt`.

Ace's point was that replay and forward agreeing on one frozen dataset does not establish
correctness. So forward mode now gets a **different simulated download every day**:

- **Rolling window:** the last 120 sessions only, so every row and column index shifts daily.
- **Shuffled rows:** a seeded shuffle each day.
- **Re-adjusted prices:** history is put on that day's split basis, as a provider does after
  every split.

All 20 downloads contained names whose basis differed from the stored panel's.

| Check | Result |
|---|---|
| Sessions processed | 2023-09-25 .. 2023-10-20, **20**, as declared |
| Replay vs forward account state | **identical**, sha256 `704c5638…` both ways |
| Signals, by ticker and invalidation | identical every day (110) |
| Forward saw a bar after the session it scored | never |
| Contract tests | 24 run, 0 failures |

Account at the close of 2023-10-20: cash $3,751.88, reserved $5,845.79, equity $9,597.68.
Outcomes, out of 110 signals:

| Outcome | Count |
|---|---:|
| Unfilled: open above the limit | 76 |
| Filled | 17 |
| Partial | 2 |
| Rejected: size zero | 6 |
| Rejected: insufficient cash | 2 |
| Unfilled: not traded | 3 |
| Orders still working after the last session | 4 |

One real split was carried through. SPRC had a 1-for-26 reverse split between its 2023-09-27
decision and the entry, so the 6,436 shares ordered became 247 at the open. Its split schedule
is not verified, and the trace labels it.

This is still mechanics only: a few weeks of an already-rejected detector. It is not evidence of
profitability.

**What changed from the v2 trace, on the same sessions:**
- The three signals of 2023-10-23 are gone.
- XRTX (2023-10-20) is now an order still working, not a fill on 2023-10-23.
- Share counts move by under 1% where the exit-tier cost changed the risk per share. They mostly
  rise, because the exit cost is now taken at the lower stop price.
- ICU (2023-10-19) has 15% fewer shares (1,849 → 1,562). That is Ace's tier finding on real data:
  limit $1.02, stop $0.978. The stop is below the $1 tier boundary, so its sell cost is 1.5%, not
  0.5%. Risk per share rises from $0.0522 to $0.0618, and risk is the binding limit.
- Realised P&L over the trades that exited: −$440.66 (v2, 21 sessions) → −$402.32 (v2.1, 20 sessions).
- No ordinary stop exit lost more than its planned risk.

## 3. Corrections to `research/EXEC_US_v2/README.md`

- **"Every criterion PASS" overstated readiness.** Criteria 3, 5 and 5.1 held only for one
  frozen data layout. Saved state broke under a reordered, windowed or re-adjusted download.
  Sizing under-counted the exit cost across tiers. Exits could fill on sessions without trades.
- **The v2 demonstration processed 21 sessions, not the 20 declared** (it ran to 2023-10-23).
  Its account figures (cash $6,233.37, equity $9,559.34) describe that window, under the v2 rules.
- The v2 merge-preservation proof, the audit-gap witnesses and the FILL-C feasibility
  measurement are not affected. They do not depend on the contract's state handling.

## 4. Acceptance criteria (re-marked)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| A1 | Each of Ace's five findings fixed | PASS | Section 1 table |
| A2 | A regression test reproducing each failure: fails on `21eb6aa`, passes now | PASS | `regressions.json`. For the demo window, the evidence is the recorded v2 trace (21 sessions) and v2.1's (20) |
| A3 | Demonstration regenerated for the declared dates | PASS | `trace.json`: `window_matches_declaration: true`. The demo exits non-zero otherwise |
| A4 | Replay and forward agree when downloads change row order, date window and split basis | PASS | Section 2 |
| A5 | Earlier criteria still met: legacy unchanged; append-only; v2 records preserved | PASS | `check_append_only --all` OK; `verify-runs` and `paper-verify` OK; v2 files untouched |
| A6 | Connected to the scheduled paper workflow | NOT DONE (out of scope) | The routines still run PAPER-POLICY-v4. Switching needs a new paper policy version, which is your decision |

## 5. Limitations, and what has not been independently verified

- **Not reviewed:** nobody has independently reviewed v2.1. Ace's reproductions are re-implemented
  here from his description; I did not have his scripts.
- **The download simulation is mine.** It rebuilds each day's download from one stored panel:
  window, row order and split basis. It does not reproduce a real provider's quirks: late
  corrections, delisted names vanishing, or partial days.
- **The split ratio must be in the download's unit factors.** A provider that re-adjusts prices
  without a matching split record in the schedule would still corrupt units. Names without a
  verified schedule are labelled, not blocked.
- **Missing history:** a download that no longer contains the last processed session fails the
  scan (`MISSING_HISTORY`) rather than guessing the units.
- **Assumptions unchanged from v2:** daily bars cannot show auction liquidity, intraday order,
  stop slippage or settlement. Stale-data detection still needs the caller to supply the
  expected session.
