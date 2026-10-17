# E10 guidance revision (US): protocol

Written after the counts-only feasibility and the accuracy audit, before any price or return is read for
E10. `freeze.py` writes `protocol.json` with the sha256 of every input and of the code that runs and checks the
test; the runner refuses to start if any of them changed, and refuses a second run.

Historical discovery test, run once. Its result is never prospective performance. A PASS licenses a forward
paper test only: no real-money order, no change to ASTRA.

## The question, in three stages
1. **Will the stock move?** Not scored. A guidance raise is public news, not a forecast of a move.
2. **Can we capture it?** After an entry we could actually get (the first open after the release) and after
   costs, is there return left that similar stocks on the same dates did not earn? How much of the reaction
   happened before we could buy?
3. **Can the account carry it?** A USD 10,000 cash account, with slots, sizing and commissions, taking the
   trades as they come.

## Events (fixed before any price is read)
`feasibility_a1/events.csv.gz` (extraction v2, FEASIBILITY_AMENDMENT_1.md): earnings releases (8-K Item 2.02, EX-99) accepted 2020-07-01..2022-11-30 that
revise full-year revenue guidance against the same issuer's previous release with guidance of the same kind
for the same fiscal year. Classes: RAISE (level change >= +1%), CUT (<= -1%), MAINTAIN. Counts and the audit:
`feasibility_a1/FEASIBILITY.json`, `audit_partial/a1_audit/AUDIT.json`. Universe: the US repair panel
(`panel_us_repair-20261008T114805Z`), today's listings only.

## Trade (each event, every class)
- Entry: the open of the first session the release could be traded on (accepted by 09:15 New York time on a
  session day: that session; otherwise the next session).
- Tradable: as-traded entry open >= USD 2 and median traded value of the 20 sessions before entry >= USD 500k.
  One open trade per stock: a release whose entry falls inside an earlier trade's hold is skipped.
- Exit: the close of the 20th session (entry = session 1).
- Costs: per side 1.5% under USD 1, 0.5% USD 1-5, 0.15% USD 5-20, 0.05% above, on as-traded prices, plus
  the SEC fee (0.00278%) on sales.
- Controls: 200 draws with replacement from stocks on the same entry session in the same cost tier, liquidity
  quintile, 20-session momentum tercile and volatility tercile, without their own Item 2.02 release from 5
  sessions before entry to the exit (the least important bucket is dropped while fewer than 5 names match).
  Excess = the event's net minus the controls' mean net.
- Statistics: week-cluster bootstrap (ISO week of entry), 10,000 resamples, seed 20261017 (+10 per class).

## Gates (PASS only if all six hold, RAISE class)
- **G1** the 95% lower bound of the mean excess over controls is above 0.
- **G2** the mean net and the 1%/99%-clipped mean net are above 0.
- **G3** the mean excess of RAISE is above that of MAINTAIN.
- **G4** the mean net with an extra 0.5% per side is above 0.
- **G5** the mean excess is above 0 in each entry year (2020, 2021, 2022).
- **G6** account A ends above USD 10,000 and above its shadow account.

## Reported whatever the verdict (descriptive, not gates)
- Stage 2: pre-entry move (entry open / last close before the release - 1) and its excess over controls; the
  excess drift curve from the entry open to sessions 1, 2, 5, 10, 20, 40, 60 (an event leaves a horizon that
  ends after 2022-12-30); entry at the entry session's close (same exit); entry one session late; 5-session
  hold; 5% planned stop; mean gross return (cost drag).
- Stage 3: accounts A (10% of equity per trade, at most 10 positions, 20-session exit) and B (5% planned stop,
  1% of equity at risk = 20% positions, at most 5), each with a shadow account on each event's first control
  draw; USD 2 commission per order; final equity, annualised return, maximum drawdown, worst 21 sessions,
  exposure, trades taken and skipped, win rate, profit factor.
- CUT and MAINTAIN classes; RAISE minus CUT; RAISE events on eToro-listed stocks.

## How the result will be read (fixed now)
- **PASS**: the raise left return after an obtainable entry, costs and an account. Next step: a frozen forward
  paper rule on new releases from the live SEC feed; nothing real.
- **FAIL, with a large positive pre-entry excess and G1 failing**: the market prices the raise before an
  obtainable open; whatever edge exists sits in the minutes after the release, which daily bars cannot test.
- **FAIL, with G1-G5 holding and G6 failing**: return per trade exists but the account cannot carry it
  (slots, sizing, commissions, timing); the trade list says where.
- **FAIL otherwise**: full-year revenue guidance raises, as extracted, left nothing after an obtainable entry
  in 2020-2022.
No rerun after the result: any change is a new experiment with its own protocol.

## Limits
Survivor-only US universe (likely flattering); assumed costs, not measured spreads, and daily bars cannot prove
an opening fill; extraction error rate as audited; a single regime (2020-2022, including the 2022 drawdown);
2023 is already used and 2024 onward is sealed and never loaded.

## Runner and checks
`run_a1.py` (the single recorded run) writes `results/{RESULT.json, trades.csv.gz, accounts.csv.gz}`.
`verify_result.py` recomputes the decisive numbers with its own code. `run_test.py`'s `main()` was never
executed and is superseded; `run_full.py` is the stage 2/3 code `run_a1.py` runs (see its docstring for the one
fix it carries).
