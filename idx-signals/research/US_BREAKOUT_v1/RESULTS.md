# US_BREAKOUT_v1: results

**Verdict, by the rule frozen in `PROTOCOL.md`: NO EDGE ESTABLISHED.** Three of the four
decision conditions failed. Buying a US stock at the next open after it closes above its previous
60-session closing high lost money on average after costs. It did no better than matched entries
that were not breakouts.

This is a historical test on 2023. It is not prospective performance, and it is not approval
evidence. The protocol, signal code and tests were committed before any breakout return was
computed (`3f56bcf`), and the runner before any run (`6e13c9e`). The validation window was run
once. Results come from commit `6e13c9e`; protocol sha256 `0cb6a3df9f8b…`.

## Primary result: 2023-01-03 .. 2023-12-29

| | Breakout signals | Matched controls |
|---|---:|---:|
| Eligible signals | 12,995 | 129,589 drawn (10 per signal) |
| Filled and exited | 11,833 | 117,837 |
| Unfilled: open above the permitted entry | 1,012 | 9,941 |
| Rejected: size below one share | 32 | 256 |
| Still open at the end of the data (excluded) | 118 | 1,553 |
| Average net return per trade | **−0.180%** | −0.138% (weighted to the signals' cells) |
| Median net return | −0.562% | −0.545% |
| Hit rate (net > 0) | 19.9% | 20.6% |

- **D**, signals minus matched controls: **−0.042 percentage points**.
  - 95% interval, bootstrapped over 249 sessions: −0.115 to +0.035 pp.
  - One-sided p (D ≤ 0): 0.856.
  - The data do not distinguish breakouts from non-breakouts. The point estimate is slightly
    below zero, and the interval includes zero.
- The signals' own mean net: −0.18% (95% interval −0.31% to −0.04%). It is positive in no
  sensitivity run.
- Exit mix, signals: stop 56%, stop at the entry open 17%, stop through a gap 3%, time exit 24%.
  Controls look alike. A stop-based, five-session position with these costs loses a little
  whether or not a breakout preceded it.

## Decision rule

| Condition | Result |
|---|---|
| 1. At least 200 matched, filled signal trades | Met (11,833) |
| 2. Mean net of filled signal trades positive | **Not met** (−0.18%) |
| 3. D > 0 with bootstrap p < 0.05 | **Not met** (D = −0.04 pp, p = 0.86) |
| 4. D > 0 in both S1 and S2 | **Not met** (D < 0 in both) |

## Sensitivity runs (protocol-fixed, reported either way)

| Run | Filled signals | Signal mean net | Control mean net | D | p |
|---|---:|---:|---:|---:|---:|
| Primary | 11,833 | −0.180% | −0.138% | −0.042 pp | 0.856 |
| S1: only names with verified split schedules | 11,336 | −0.185% | −0.144% | −0.041 pp | 0.848 |
| S2: stops fill 1% below the stop level | 11,833 | −0.733% | −0.677% | −0.056 pp | 0.913 |
| S3: median traded value of at least $5M | 9,331 | −0.124% | −0.105% | −0.019 pp | 0.681 |

By half-year (descriptive): D = −0.07 pp in H1 (p 0.94) and −0.01 pp in H2 (p 0.59). The
conclusion is the same in every cut.

## The account-level run, and how not to read it

One shared $10,000 account, with the same signals, priority by liquidity, and no leverage, ended
the year at **$11,187** (about +11.9%). I did not use this for any decision, and it does not
change the verdict:
- It has no baseline. The matched controls lost money per trade, and 2023 was a rising market.
  The same account run on non-breakout entries was not computed, and I did not add it after
  seeing this.
- The account entered 950 of the 12,995 signals. Cash ran out, and 11,908 were rejected for
  insufficient cash. A different priority rule would pick different trades.
- It selects the most liquid names. Any edge there would have to be found in a pre-registered,
  separate test, and not from this number.

## Limits

- **One year, one rule.** The 2023 validation window is the only result. Nothing here estimates
  future performance.
- **Survivorship bias.** The universe is the 2026-10-08 listing, which flatters a long test. The
  result is negative even with that flattering bias.
- **Execution assumptions.** Daily bars cannot show auction liquidity, stop slippage or the order
  of events inside a session. They are assumptions from EXEC-US-v2.1. S2 stresses the stop only.
- **2023 is not an untouched year for the project.** Earlier work looked at its prices, on a
  different detector and in the execution demonstrations. This rule was not computed on them.
- **Controls inherit the signal's stop distance.** A different control design could give a
  different D, but the signals' own mean is negative, so only conditions 3 and 4 depend on it.
- **Pipeline check:** the first quarter of 2022 ran as a code check, as the protocol says (unverified
  units; `pipeline_check/`). It informed no decision, and I did not look at its statistics
  beyond the fact that the pipeline ran.
- **Not independently reviewed.**

## Reproduce

```sh
cd idx-signals
python3 research/US_BREAKOUT_v1/run_experiment.py validation   # about 2 minutes; refuses a dirty tree
```
The run writes `validation/summary.json` and `validation/trades.csv.gz`, and refuses to overwrite them.

## What follows

Nothing in this result earns forward paper scoring. The next step is not a parameter change to
this rule: a different lookback or holding period would be a new hypothesis with its own
pre-registered protocol and its own multiple-comparison cost. I have not tried any.
