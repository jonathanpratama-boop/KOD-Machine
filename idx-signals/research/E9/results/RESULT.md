# E9 catalyst split: result (US stocks, discovery 2020-07..2022-12, run once)

**Overall: NEGATIVE.**
- **Q1, does an SEC filing known before the open separate continuation from fade? INCONCLUSIVE.**
  DOCUMENTED minus UNDOCUMENTED is +1.99 points of net return per trade (95% -1.83 to +6.00).
- **Q2, is buying DOCUMENTED movers on the E2 plan profitable in this historical test? UNPROFITABLE.**
  The mean net is -1.07% per trade (95% -3.76 to +2.07), and it is negative in every year.

This is a historical discovery test. It is not prospective performance.

## Trades by class
Buy at the next open; sell at the close of the 5th session after entry. Net of the harness cost tiers and
the SEC fee.

| | DOCUMENTED | UNDOCUMENTED | DILUTION |
|---|---|---|---|
| Trades | 644 | 1,337 | 223 |
| Mean net (95%) | **-1.07%** (-3.76 to +2.07) | **-3.06%** (-6.14 to +0.40) | **-2.80%** (-9.44 to +6.05) |
| Median net | -4.47% | -9.57% | -11.57% |
| Win rate (95%) | 41.5% (37.7 to 45.3) | 33.0% (30.5 to 35.6) | 33.2% (27.3 to 39.6) |
| Average win / average loss | +23.0% / -18.1% | +32.3% / -20.5% | +37.8% / -23.0% |
| Trades at +20% net or more | 14.8% | 12.4% | 12.6% |
| Worst trade | -87.5% | -88.9% | -78.2% |
| Excess over matched controls (95%) | -0.93 (-3.47 to +1.93) | -3.51 (-6.16 to -0.42) | -2.62 (-9.28 to +6.27) |
| Mean net with +0.5% cost per side | -2.05% | -4.02% | -3.77% |
| Mean net by signal year, 2020 / 2021 / 2022 | -2.00 / -0.37 / -1.06% | -1.72 / -4.58 / -2.25% | -0.67 / -3.57 / -3.21% |
| Names eToro lists today | -0.91% (604 trades) | -3.57% (1,239) | -3.12% (213) |

All 2,251 scored signals, any class: mean -2.19%, median -8.03%, win rate 35.4%, and 2.47 points per trade
below their matched controls.

## Acceptance criteria
| Criterion | Holds? |
|---|---|
| C1: at least 150 trades in each of DOCUMENTED and UNDOCUMENTED (644 / 1,337) | yes |
| C2: DOCUMENTED mean net positive in each year | no (negative in all three) |
| C3: DOCUMENTED lower 95% bound positive | no (-3.76%) |
| C4: lower 95% bound of DOCUMENTED minus UNDOCUMENTED positive | no (-1.83) |
| C5: DOCUMENTED excess over matched controls positive | no (-0.93) |
| C6: DOCUMENTED positive under the cost stress | no (-2.05%) |

## The separation in detail (reported, never deciding)
| DOCUMENTED minus UNDOCUMENTED | Estimate | 95% |
|---|---|---|
| Mean net (the primary) | +1.99 | -1.83 to +6.00 |
| Excess over matched controls | +2.58 | -1.18 to +6.49 |
| Mean net, each net clipped at the pooled 1st / 99th percentile (-59.8%, +121.7%) | +3.39 | +0.81 to +6.01 |
| Win rate | +8.5 points | +3.3 to +13.5 |
| Median | +5.1 | |
| Cost stress | +1.97 | -1.82 to +5.94 |
| Unit bound (top tier for the 669 names with unverified units) | +2.11 | -1.69 to +6.06 |
| Names eToro lists today | +2.66 | -1.00 to +6.55 |
| By year: 2020 / 2021 / 2022 | -0.28 / +4.22 / +1.20 | |

**What this means.** A filing does separate the *typical* trade. Spikes with nothing behind them lose more
often and lose more:
- the win rate is 8.5 points lower;
- the median is 5.1 points lower;
- the clipped mean is 3.4 points lower.

The two intervals that are reported both exclude zero. The pre-registered mean difference stays
unresolved, because both classes have extreme tails, real ones from the 2020-2022 meme years (HKD +1,025%,
BNGO +844% and AMC +501% in five sessions). The deciding fact is the other one: **documented movers still
lose money**. They lose in the median trade, in every year, against their matched controls and under
stress. There is no post-news drift here to buy.

## Other diagnostics
- **DILUTION minus UNDOCUMENTED** after 5 sessions: +0.26 (95% -6.79 to +9.13). After 20 sessions, DILUTION
  movers average -10.92% (95% -17.88 to -3.20). That is 11.34 points below their matched controls, with a
  median of -18.9%.
- **20-session secondary.**
  - DOCUMENTED -1.68% (median -8.58%).
  - UNDOCUMENTED shows +16.25%, but that rests on one data artifact. CHRD's signal on 2020-11-11 entered
    the old Oasis Petroleum shares at $0.17. The panel's price history then continues with the shares
    issued after its bankruptcy reorganisation, which shows +22,212% in 20 sessions, while the old shares
    were cancelled. Without the five largest values the UNDOCUMENTED 20-session mean is -3.77%, and its
    median is -15.69%.
  - The 5-session primary is not affected: CHRD's 5-session trade is -31.5%.
- **UNDOCUMENTED, split by hindsight.** Moves where an information filing arrived within 4 days after the
  cutoff did worse: -6.39% over 301 trades, against -2.09% over 1,036 without one.
- **Including the 47 UNDOCUMENTED rows** whose issuer had no filing before the window: DOCUMENTED minus
  UNDOCUMENTED is +1.54.

## Money and exposure (DOCUMENTED only)
Model: 5,000 USD per trade, 100,000 USD of capital, no compounding.
- 644 trades over 2.5 years.
- 6.2 positions open on average, 28 at most. More than 20 were open on 8 sessions.
- Total P&L: -34,330 USD (-34% of capital).
- Maximum drawdown: -71,769 USD (-72% of capital).

All classified signals together: 2,204 trades, -270,058 USD, up to 81 positions at once.

## How it was run
- **Feasibility.** The first check was NO-GO (`feasibility/`): EDGAR's JSON acceptance time is true UTC
  for some issuers and New York time converted to UTC twice for others. Amendment 3 (`85b23b0`) took
  every class-relevant time from the filing's own SGML header. The second check was GO (`feasibility_a3/`):
  2,966 headers were retrieved, including all 1,942 that can change a class. No return was computed at
  any point before the freeze.
- **Freeze.** The protocol was frozen at `c93c50e` with the sha256 of 25 inputs and code files, and pushed
  before the run.
- **The run.** `run_test.py` ran once, in 31 minutes. Results were committed as written (`2f1109d`).
- **Reproduction.** The harness's trades equal the shared entry list. Repeating its steps reproduces its
  nets and the 623,200 control entries. The control pooled mean equals the harness baseline exactly
  (0.199%), and the cost formula reproduces every net.
- **Verification.** `verify_result.py` recomputed every decisive number from `trades.csv.gz`, with its own
  tier lookup and its own bootstrap: VERIFIED. The largest difference is 3.7e-11.

## Limits
- Discovery data only.
- Today's listings only: names that delisted are absent, and that likely flatters every class.
- Daily bars cannot prove an opening fill.
- eToro's spreads are modelled only by the cost tiers and the stress.
- The as-traded units of 669 names are unverified (bounded above).

None of these could turn a class that loses in its median trade, every year, into a profitable one.

## Next action (owner decision)
Retire "buy the open after a +30% day" as a US trading entry, as was done for crypto on 2026-10-17. Even
the best available definition of "really bullish", an SEC information filing published before the next
open, loses after costs. The daily scans are unaffected: US candidates are already PASS. Retiring it
stops further filter, exit or sizing variants on buying after the move.
