# EXIT-ATR-v1 (cloud run): protocol, frozen before any exit return is computed

`protocol.json` is binding and carries every hash. This page states the same rules in words.

**Question.** Does one volatility trailing stop improve the net returns of E2's crypto G2_RET30 signals,
entered at the next UTC day's open? Two separate answers are required: (1) does the trailing exit beat the
original exit on identical entries, and (2) is the resulting strategy profitable in this historical test.
This is exploratory evidence on previously examined history (E2 discovery, 2020-07-01..2022-12-31), not
validation. 2023 and the 2024+ holdout are not read.

**Why a cloud run.** Hermes's working files are uncommitted on the owner's Mac (`hermes/exit-atr-trail-v1`),
which this session cannot reach. This run rebuilds the same design from Hermes's archived files
(`hermes_archive/`, replayed from its chat export) and the repository's own data, in a separate folder so
nothing collides with the Mac work. Label: **"original E2 content identity unverified" does not apply
here**: this run uses E2's original daily panel `panel_crypto-20261008T003354Z.csv.gz` (sha256
`3dc12749…`, checked on every load), the exact file Hermes could not reach. The shared entry list rebuilt
from it reproduces Hermes's counts exactly (1,495 signals, 238 overlap skips, 1,257 attempted, 251,400
controls, same status and match-level counts).

## Entries (shared by both arms)
- E2 harness at commit `21345b1`, E2's recorded crypto run configuration, window 2020-07-01..2022-12-31:
  entry at the open of the day after the signal; 5,000 USDT notional, whole units, at most 10% of the entry
  day's volume; overlap skip decided by the ORIGINAL 5-session exit; 200 matched controls per attempted
  signal (controls v2, seed 20261007 + 1). An earlier ATR exit cannot create an entry.
- Scored in both arms: the original model's EXITED and EXIT_DATA_END trades. INCOMPLETE (holding period
  crosses 2022-12-31) and unfilled entries are not scored in either arm.

## Eligibility (identical for both arms, signals and controls; counts in `eligibility/ELIGIBILITY.json`)
1. Hourly bars exist for `<ticker>USDT` and the entry day's 00:00 bar is present.
2. ATR warm-up valid: 15 consecutive daily panel bars s-14..s (s = signal day), finite, high >= low > 0,
   close > 0, ATR > 0.
3. No overlap with a source-confirmed unit or asset change (COCOS, BTCST, DREP, SUN, VIDT redenominations;
   LUNA ticker reuse) between day s-14 and the original exit day. Exclusion, not unit correction.
UNFI 2022-06-07 (×5.5, no halt, no announcement) stays UNRESOLVED and in the main analysis.
Result: 1,181 common scored signal trades (307 coins); 245,455 eligible controls; every signal keeps at
least 26 eligible controls (median 200).

## Arm A: original exit
Sell at the close of the 5th session after entry, or the first later session where a sale is possible;
a coin that stops trading is sold at its last traded close (EXIT_DATA_END). Exactly E2's harness.

## Arm B: ATR trailing stop (`idxsig/exit_atr.py`)
- ATR = arithmetic mean of the 14 true ranges of daily bars s-13..s; the first uses the close of s-14.
  True range = max(high - low, |high - previous close|, |low - previous close|). Known at the signal close,
  frozen for the whole trade.
- Initial stop = entry price - 3 × ATR, active from the entry bar (00:00 of the entry day).
- After each completed hourly bar: highest = max(highest, bar high), starting from the entry price;
  stop = max(previous stop, highest - 3 × ATR), active only from the next bar. Never moves down.
  No take-profit.
- Fills: within a bar only the stop set before it applies. Open at or below the stop → sell at the open
  (STOP_GAP). Otherwise low at or below the stop → sell at the stop (STOP).
- Window: from the entry bar to the 23:00 bar of arm A's exit day (the original deadline, including any
  roll). A position never stopped leaves exactly as arm A does (same session, same price).
- Gaps (missing hours, including the nine exchange-wide outages): hold; no fill and no stop update
  while bars are missing; the first bar after a gap applies the gap rule above.
- Data ending early (TRUNCATED windows, EXIT_DATA_END trades): stops are checked through the last
  available bar; otherwise exit at arm A's price.
- Research boundary: hourly files after 2022-12 are never opened and no window passes 2022-12-31 23:00.

## Costs (same in both arms, per side, as E2 charges them: exit (1 - c) / (entry (1 + c)) - 1)
- Original (E2 reproduction): 0.2% (0.1% fee + 0.1% slippage).
- **Primary: 0.3%** (original + 10 bp slippage).
- Stress: 0.4% (original + 20 bp).

## Statistics
- Unit: common scored signal trade. Calendar-week bootstrap (ISO week of the entry date, UTC), 2,000
  resamples, seed 20261016, one fixed set of resampled weeks for every metric, 95% percentile interval.
  Dependence beyond a week (regimes, overlapping coins) is not modelled.
- Paired improvement = net B - net A per trade (primary costs).
- Matched-control excess = trade net minus the mean net of its eligible controls under the same exit.
- Reported: eligible and excluded counts; mean, median, win rate (net > 0; Wilson 95%), average win and
  loss, worst losses, holding hours; exit reasons; paired improvement; excess over controls; results by
  entry year; capital exposure; a portfolio P&L path (5,000 USDT per trade, unlimited capital, booked at
  exit) and its drawdown.
- Sensitivities (predefined, no others): stress costs; original costs; conservative gap fills (a stop
  triggered on the first bar after a gap fills at that bar's low); data-end at -100% (both arms, for
  positions still open when their data ends); UNFI excluded.

## Acceptance (from the task brief, unchanged)
RESEARCH-POSITIVE only if all hold, at primary costs unless stated:
- C1 at least 200 common scored trades;
- C2 arm B mean net > 0 in each discovery year, by entry year: 2020 (July–December), 2021 and 2022;
- C3 lower 95% bound of arm B mean net > 0;
- C4 lower 95% bound of the paired improvement > 0;
- C5 arm B's mean excess over matched controls using the same trailing exit > 0;
- C6 arm B mean net > 0 under stress costs.

## Verdicts (fixed now)
- Q1, trailing exit versus original exit: **Improves** if C4 holds; **Does not improve** if the paired
  mean is <= 0; otherwise **Inconclusive**.
- Q2, profitability of the resulting (arm B) strategy: **Profitable in this historical test** only if
  RESEARCH-POSITIVE; **Unprofitable** if arm B's mean net <= 0; otherwise **Inconclusive**.
- Overall: RESEARCH-POSITIVE, NEGATIVE (Q2 unprofitable) or INCONCLUSIVE. A smaller loss is an
  improvement, never a profit. Even RESEARCH-POSITIVE would need fresh prospective evidence.

## After the run
One run. No other ATR length, multiplier, take-profit, signal or market is tried after seeing results.
