# E9 catalyst split: frozen protocol (discovery test, run once)

Frozen before any E9 return is computed. Machine-readable twin: `protocol.json`, with the sha256 of every
input and of the code that runs the test.

Feasibility history (counts only, no return at any point):
- The first check (`feasibility/`, amendments 1-2) was **NO-GO**: the EDGAR JSON acceptance time mixes two
  conventions.
- Amendment 3 takes every time that can change a class from the filing's own archive header.
- The second check (`feasibility_a3/`) passed. All 1,942 class-relevant headers were retrieved. Entered
  trades: 644 DOCUMENTED, 1,384 UNDOCUMENTED and 223 DILUTION, over 126, 130 and 95 ISO weeks.
- Each amendment was dated and committed before its check ran.

## Question
Among US stocks that close up 30% or more in a day (frozen E2 detector G2_RET30, rule
`MOONSHOT_E2_US_D1`), do moves backed by an SEC information filing that was public **before the next open**
continue better than moves with no filing? Do moves with a dilution filing do worst? Mechanism: disclosed
information is repriced gradually (drift); an unexplained move is order-flow pressure that reverses.

## Trades (identical for every class)
The harness itself (`idxsig.backtest.run`), with E2's recorded US configuration and only the window and
`quarantine="none"` changed (`entries/entries_meta.json`). Buy at the open of the session after the signal.
Sell at the close of the 5th session after entry. 5,000 USD per trade. Fill model B: at most 10% of the
median as-traded volume known at the decision, and the entry session must trade. Per-side costs at the
as-traded price: 1.5% under $1, 0.5% for $1-5, 0.15% for $5-20, 0.05% above $20, plus the SEC fee on
sales. A signal while the same name is still held is skipped (the original exit decides). Signal sessions
2020-07-01..2022-12-31 (discovery). 2023 was examined in E2 and is not used. 2024 onward is sealed.

## Classes (frozen in `feasibility_a3/classes.csv.gz`; the rules are in FEASIBILITY_SPEC.md)
A filing counts if its archive header's acceptance time (New York) is after 16:00 on the session before the
signal and at or before 09:15 on the entry session (amendment 3). First match wins:
1. DILUTION: a registration or prospectus form, or an 8-K item 3.02;
2. DOCUMENTED: 8-K, 6-K, 10-Q, 10-K, 20-F, 40-F, SC 13D, tender offer and merger forms;
3. UNDOCUMENTED: neither.

**Sample.** Scored trades (EXITED or EXIT_DATA_END) in DOCUMENTED, UNDOCUMENTED or DILUTION, whose issuer
has a fetched filing on or before the session before the signal. Without such a filing, today's
ticker-to-issuer map cannot be confirmed for the event date. Those rows are excluded and counted, and a
sensitivity includes them. NO_CIK, NO_SEC_DATA, NO_HEADER and NO_ENTRY_SESSION rows are excluded and
counted.

## Statistics
Mean net return per trade. 95% intervals from a calendar-week cluster bootstrap (ISO week of the entry
session, 2,000 resamples, seed 20261018). One fixed set of resampled weeks serves every interval, so a
class mean and a difference between classes see the same weeks. Win rate is net > 0, with a Wilson 95%
interval. Excess is a trade's net minus the mean net of its matched controls under the same plan (controls
v2, 200 draws, seed 20261008, from the shared entry list).

## Verdicts (fixed now)
**Q1: does a filing known at entry separate continuation?** DOCUMENTED minus UNDOCUMENTED mean net:
- SEPARATES if the lower 95% bound is above 0;
- DOES_NOT_SEPARATE if the difference is 0 or below;
- INCONCLUSIVE otherwise.

**Q2: is buying DOCUMENTED movers on this plan profitable in this historical test?**
- PROFITABLE_IN_THIS_HISTORICAL_TEST if every criterion C1-C6 holds;
- UNPROFITABLE if the DOCUMENTED mean net is 0 or below;
- INCONCLUSIVE otherwise.

**RESEARCH-POSITIVE** needs all of:
- C1: at least 150 scored DOCUMENTED and 150 scored UNDOCUMENTED trades;
- C2: DOCUMENTED mean net above 0 in each of 2020, 2021 and 2022 (signal year);
- C3: lower 95% bound of the DOCUMENTED mean net above 0;
- C4: lower 95% bound of DOCUMENTED minus UNDOCUMENTED above 0;
- C5: DOCUMENTED mean excess over matched controls above 0;
- C6: DOCUMENTED mean net above 0 with an extra 0.5% cost per side.

Overall: RESEARCH-POSITIVE; else NEGATIVE if Q2 is UNPROFITABLE or Q1 is DOES_NOT_SEPARATE; else
INCONCLUSIVE.

## Reported, never deciding
- Robustness of the mean:
  - DOCUMENTED minus UNDOCUMENTED with every net clipped at the pooled sample's 1st and 99th percentiles;
  - the difference in medians;
  - the difference in win rates (each with the week bootstrap where an interval is given).
- Unit bound: the 1.5% top tier on both sides for the 669 names whose as-traded units the panel could not
  verify.
- Names eToro lists today (the owner's broker; its list is current, so names it dropped are absent).
- 20-session secondary: the same entries held 20 sessions.
- DILUTION minus UNDOCUMENTED.
- UNDOCUMENTED split by whether an information filing arrived within 4 days after the cutoff (hindsight
  diagnostic: unknowable at entry).
- Excluded rows included.
- Results by year.
- Exposure: 5,000 USD per trade against 100,000 USD of capital (20 slots), no compounding, P&L at exit.
  Reports the maximum number of open positions, sessions above 20 positions, total P&L, and the maximum
  drawdown in USD and as a share of capital.

## Limits stated before the result
- Discovery data only.
- The universe is today's listings (survivor-only). Names that delisted after a +30% day are absent, so
  they cannot be given a worst-case outcome: the panel never saw them. The note proposing E9 offered that
  treatment, and this panel cannot deliver it. Survival likely flatters both classes' means. Its effect on
  the difference between classes is not known.
- Daily bars cannot prove an opening fill.
- eToro's spreads and its execution at the open are not modelled beyond the cost tiers and the stress.
- Any positive result is a historical research result, never prospective performance. Before any money it
  needs a frozen prospective paper test, or a once-only run on a sealed 2024+ panel that is not yet built.
- No parameter (window, horizon, class rule, cost) is changed after the result. A failure is reported as
  it is.

## Execution
`python3 research/E9/run_test.py` once, on a clean tree, checking every frozen hash. It writes
`results/RESULT.json` and `results/trades.csv.gz`. `research/E9/verify_result.py` then recomputes the
decisive numbers independently from `results/trades.csv.gz`.
