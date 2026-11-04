# EXEC_US_v2: shared execution milestone

Historical replay and forward paper scoring now run one versioned contract, EXEC-US-v2, with an
account, cash and priority. The contract is specified in `CONTRACT.md` and implemented in
`idxsig/contract.py`. It is demonstrated end to end on real data, and the two modes agree.

Mechanics only. Nothing here is evidence of profitability, and the reserved holdout was not read.

## One command

```sh
cd idx-signals && python3 research/EXEC_US_v2/demo.py      # about 5 minutes; exit 0 only if every check passes
```

It writes three files:

- `trace.json`: the machine-readable trace, including the forward ledger.
- `TRACE.md`: input → signal → planned order → fill or rejection → exit → costs → account balance,
  for every signal, plus the event log with cash after each event.
- `tests.txt`: the contract's 18 tests.

Supporting checks (from `idx-signals/`):

```sh
python3 research/EXEC_US_v2/preservation.py       # merge d62de40 kept both parents (content proof)
python3 research/EXEC_US_v2/fill_c_feasibility.py # Hermes's finding measured on the recorded FILL-C run
python3 research/EXEC_US_v2/audit_gaps.py         # each audit finding: fails before, passes now
python3 -m unittest tests.test_contract
```

## Pinned state

| | Commit |
|---|---|
| Base of PR #3 (`claude/idx-signals-test-repo-ds0jw7`) | `c09a27ac94fccf6a33f12a0ee07e33f88238ace5` |
| PR #3 before this milestone (merge of the base, CI green) | `d62de40c4b3f91140279276a64dcf5a7bccfe47a` |
| PR #3 head before that merge | `7774442f0df8960ccfe17311ac1f8561d497f13a` |
| Demonstration data | panel `panel_us_repair-20261008T114805Z` (sha256 in `trace.json`), sessions 2023-09-25 .. 2023-10-20 |

## Demonstration result (real data, labelled integration example)

- **Detector:** MOONSHOT_E2_US_D1 (already rejected by E2), with its invalidation at the signal
  low. It produced 113 signals over 20 sessions.
- **Replay vs forward:** the account states are byte-identical, sha256 `73ba1a25…` both ways. Signals
  are identical day by day. Forward mode never held a bar after the session it scored.
- **Outcomes:**

  | Outcome | Count |
  |---|---:|
  | Unfilled: open above the limit (gap) | 79 |
  | Filled | 18 |
  | Partial | 2 |
  | Rejected: size zero | 6 |
  | Rejected: insufficient cash | 2 |
  | Unfilled: not traded | 3 |
  | Still working at the end | 3 |

- **Account:** started at $10,000. At the end: cash $6,233.37, reserved $3,325.97, equity
  $9,559.34. These numbers describe mechanics on a few weeks of a rejected detector, nothing more.

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1.1 | Latest remote state inspected; base and working commits pinned | PASS | table above |
| 1.2 | Original experiments, FILL-C-v1 and their recorded results preserved | PASS | `preservation.json`: 52 recorded artifacts byte-identical to their parent; `verify-runs` OK; `check_append_only --all` OK |
| 1.3 | Corrections appended, not edited in | PASS | `IDX_CAUSAL_CAPACITY_v1/CORRECTION_01.md` (new file; `RESULTS.md` untouched) |
| 1.4 | PR #3 conflicts resolved by a non-force push; PR not merged; no policy changed | PASS | `d62de40` pushed fast-forward over `7774442`; CI green on it; PR #3 open; `POLICY_ID` unchanged |
| 1.5 | Preservation proven by content, not parent order or the guard | PASS | `preservation.py`: one-side files byte-identical. Both-side files have every added line present except 12 lines that only list fill models, which were combined by hand; the merged CLI and execution are run and accept all of A, B, B2 and C |
| 2.1 | Paper and backtest sizing reconciled into one explicit contract; legacy kept | PASS | `CONTRACT.md` §4 (cut to the binding limit, traded value in USD). `audit_gaps.json` witness: the same thin name is rejected by FILL-C (`SKIP_LIQUIDITY`) and sized by paper v4 (19 shares); EXEC-US-v2 has one rule. Legacy A/B/B2/C/EXEC-US-v1 tests still pass |
| 2.2 | Planned order separated from realised fill; rejected, unfilled and partial attempts kept | PASS | `test_entry_session_volume_bounds_the_fill`: Hermes's 10,000 vs 1,000 case gives PARTIAL 100. All non-fills are kept in `closed` with a reason, as in the demo outcome table |
| 2.3 | Whole-session volume labelled an upper bound, not auction liquidity | PASS | `fill_evidence` on every fill; `CONTRACT.md` "Not established" |
| 2.4 | The claim that FILL-C omits signal-day volume corrected | PASS | `CORRECTION_01.md` §1 |
| 2.5 | Historical effect of Hermes's finding measured, not asserted | PASS | `fill_c_feasibility.json`: 4 of 251 FILL-C trades exceed 10% of the entry session, 0 exceed the whole session; average −3.64% → −3.57% without them |
| 3 | Contract specifies decision time, order, invalidation, sizing, reservation, costs, slippage, gaps, missing data, exits, maximum hold, corporate actions, priority, cash, no leverage | PASS | `CONTRACT.md`; each rule is in `contract.py` |
| 3.1 | 5% measured at the permitted entry; incompatible entries rejected; stop never moved | PASS | `test_risk_distance_is_measured_at_the_permitted_entry_and_the_stop_never_moves`; `test_excessive_entry_gap...` |
| 3.2 | Planned stop distance, account risk and realised gap loss kept distinct | PASS | `test_planned_risk_account_risk_and_gap_loss_are_separate`; fields in every trace row |
| 3.3 | No execution at an already-observed close | PASS | `test_entry_at_next_open_time_exit_and_balance` (entry at the next open); the order is limit-on-open only |
| 4 | Input-hash binding, complete corporate-action reconciliation, research-window restriction, consistent share units, pinned approval and positive net all fail before and pass now | PASS, see note | `audit_gaps.json`: every listed test passes now and fails on the pre-fix commit. Behavioural witnesses on the pre-fix code itself: its approval lookup now picks the FILL-C rerun `20261009T050040Z` as IDX evidence (drift), and its predicate approves a losing strategy that beats a worse baseline at p = 0.01 |
| 4.1 | Historical impact measured, not claimed | PASS | Reconciliation: the v3 panel rebuilt byte-identical, so no effect (`US_PIPELINE_v1/checks.json`). B2: no rule trade changed. Approval drift: shown above. FILL-C: 2.5 |
| 5 | Executable demonstration of input → signal → order → fill or rejection → exit → costs → balance | PASS | `demo.py`, `TRACE.md`, `trace.json` |
| 5.1 | Replay and forward agree on identical inputs | PASS | `trace.json` `agreement` (all true); `test_forward_scoring_equals_replay_on_identical_inputs` |
| 5.2 | Tests: valid entry and exit; excessive gap; risk distance; insufficient capital; thin or absent liquidity; split between decision and execution; stale data; no signal; failed scan distinct from no signal | PASS | `tests/test_contract.py` (18 tests, `tests.txt`) |
| 6 | Scope: no IDX tuning, no new filters or hold search, no holdout, no rewritten results, no orders, ASTRA untouched, no production promotion | PASS | diff adds only `contract.py`, tests and research files; `check_append_only` OK |
| 7 | Handoff: push and PR link, command, trace, this table, limitations | PASS once pushed | see the PR #3 description |

**Note on 4.** For most of these tests, "fails before" is an import or attribute error: the
pre-fix code lacked the check entirely. That shows the check was absent, not that the old code
gave a wrong answer on that case. Wrong answers on the old code are shown separately, by the
witnesses for approval drift, the positive-net test and the sizing split. For reconciliation and
the research window, the historical effect was measured as none.

## Limitations, and what has not been independently verified

- **Not independently verified:**
  - Hermes's own reproduction script was not available to me. I reproduced the finding with my
    own synthetic case.
  - Nobody other than me has reviewed the contract or the demonstration.
- **Auction liquidity, intraday order, stop slippage and settlement** are not in daily bars.
  They are assumptions, labelled in `CONTRACT.md` and on every fill.
- **The scheduled US paper routine is not switched.** It still runs PAPER-POLICY-v4 (EXEC-US-v1).
  Forward scoring under EXEC-US-v2 is demonstrated on historical data truncated day by day, not
  on the live feed. Switching would be a new paper policy version, and that is not my decision.
- **Stale-data detection needs the caller to supply the expected session.** No exchange
  calendar is part of this contract.
- **Unit-unverified names are traded but labelled** (`units_verified: false`). In the
  demonstration, SPRC had a reverse split between decision and entry; the conversion was
  applied, but its schedule is not verified.
- **The open-below-the-stop model is conservative and assumed.** It fills and exits at the open,
  so the costs are lost. In the demonstration it accounts for 13 of the 20 filled or partial
  trades, because this detector fires on spikes that gap down the next day.
- The panel is survivor-only, has no dividends, and its split verification covers 2023 only.
