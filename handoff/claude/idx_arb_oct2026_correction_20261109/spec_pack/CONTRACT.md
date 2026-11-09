# Interface contract: October 2026 IDX auto-rejection correction

Audience: the test authors and the reference implementer. Read together with SPEC_FINAL.md, which holds the market facts.
This contract says what the corrected `idx-signals/idxsig/market.py` must do. It says nothing about how.
Written 2026-11-09 by a party who is neither a test author nor an implementer of record.

## 0. Scope and constraints

- Only `idx-signals/idxsig/market.py` changes (plus documentation). `idxsig/execution.py`, `idxsig/paper.py`, every other
  module, and every existing test except the one named in section 7 stay byte-identical. The tests must pass with those
  other modules unmodified. Reason: several of those files are byte-pinned by frozen research records.
- Python 3.12 or 3.13, numpy, pandas, `unittest`. No network, no real data, no new dependency.
- `limits()` models the regular boards (Main, Development, New Economy). The price data has no board field.
  `special_limits()` models the 10% special-monitoring board and is unchanged.
- Dates: `limits()` selects its rule by the calendar date of each element of `days`. Weekends and holidays are legal
  inputs. No session calendar is consulted anywhere.

## 1. Schedule that `limits(ref, days)` must implement

| calendar date | behaviour |
|---|---|
| before 2019-07-29 | `ValueError` (unchanged) |
| 2019-07-29 through 2026-10-18 | unchanged: every output is identical to the current behaviour. This includes 2026-09-28 to 2026-10-18 (ARB 15% above Rp10, Rp1-10 band, minimum price Rp1) |
| 2026-10-19 | ARB 7% of the reference for references above Rp10 (rounded as in SPEC_FINAL section 5); Rp1-10 band unchanged (ARA = ref + 1, ARB = ref - 1, floored at 1); minimum price Rp1; ARA unchanged. For references of Rp11 to Rp14 nothing is specified (SPEC_FINAL U5): do not assert it |
| 2026-10-20 through 2026-12-31 | as 2026-10-19, except references of Rp11 to Rp14 (integers 11, 12, 13, 14): ARB = reference - 1 (a nominal Rp1 move), ARA unchanged (35%) |
| after 2026-12-31 | section 3 |

Notes for the Rp11-14 rule: it concerns the integer references 11, 12, 13, 14. A reference strictly between 10 and 11, or between 14
and 15, is not a valid price; behaviour for such references is unspecified and must not be asserted.

## 2. Names and signatures

Unchanged (their behaviour and signatures must not change):
`limits(ref, days) -> (ara, arb)` (positional-compatible, vectorised), `special_limits(ref)`, `tick_size`, `floor_tick`,
`ceil_tick`, `band_pct`, `TICK_BANDS`, `TICK_TOP`, `BANDS`, `SPECIAL_BOARD_PCT`, `LOT_SIZE`, `Fees`, `RULES_START`,
`regime_index(days)` (still raises `ValueError` before `RULES_START`), `regime_labels()`, the `Regime` dataclass with its five
existing positional fields (an extra optional field with a default is allowed, but tests must not rely on it).

`limits` input and output shapes: `ref` is an array-like of floats; `days` is an array-like convertible to `datetime64[D]`;
the two are broadcast-compatible. `Market.build` passes two 2-D arrays of shape (tickers, sessions); a one-element pair is how
the existing tests call it. The outputs are two float arrays of the broadcast shape. A single call may mix dates from different
regimes element by element.

`regime_labels()` returns a list of dicts. Every dict keeps exactly the keys `start` (ISO string), `arb_flat`, `floor`,
`small_abs`, `label`. For every regime that starts on or before 2026-09-28 the dict is identical to today's (same values).
Existing labels must not change: frozen reports are keyed by those label strings.

## 3. After the last confirmed date: an explicit, labelled convention

SPEC_FINAL section 9: no rule is confirmed for any date after 2026-12-31. The correction must not present an unconfirmed rule
as fact, and must not stop the daily jobs. New public names in `idxsig.market`:

```python
RULES_CONFIRMED_THROUGH == datetime.date(2026, 12, 31)
class RulesUnconfirmedWarning(UserWarning): ...
def unconfirmed(days) -> numpy.ndarray   # bool; True where day > RULES_CONFIRMED_THROUGH; accepts what limits() accepts for `days`
```

Behaviour of `limits(ref, days)` when at least one element of `days` is after `RULES_CONFIRMED_THROUGH`:

a. It does not raise because of the date.
b. It emits `RulesUnconfirmedWarning` (through the `warnings` module) in every such call. With `warnings.simplefilter("always")`
   active, at least one warning of that category is recorded. In a call where every date is on or before 2026-12-31 it emits none
   of that category.
c. For those elements the returned ARA and ARB equal the values for the same reference price on 2026-12-31: the last confirmed
   rule is carried forward. Example: `limits(1000, "2027-01-04")` gives ARB 930 (the announced symmetric lower limit, 750, is NOT
   applied) and ARA 1250.
d. `regime_index(days)` for dates after 2026-12-31 returns the index of a dedicated last entry of `REGIMES` that starts on
   2027-01-01, whose label contains the substring `UNCONFIRMED`; `regime_labels()` lists it last with `start == "2027-01-01"`.
   Reports keyed by regime therefore separate the unconfirmed period.
e. Choice rationale (documentation only, not tested): carrying the 7% rule forward is the cautious choice for exits, because a
   narrower lower limit locks more closes than an eventual reversion would. It is a modelling convention, not a claim about the exchange.

Tests of (c) must live in a class whose name and docstring say it tests a convention, not a rule.

## 4. Market-level behaviour (`idxsig.execution.Market.build`, code unchanged)

```python
Market.build(tickers, dates, close, prev, high, low, volume, value, present,
             listed_shares=None, opens=None, price_limits=True, listed_before=None)
```
Arrays are (n_tickers, n_sessions); `dates` is a 1-D array of session dates; `prev` is the reference price. Helper constructors for
synthetic markets exist in `tests/support.py` (`flat_market`, `rebuild`).

Because `Market.build` derives its lock flags from `limits()`, after the correction (with `price_limits=True`):

- `lock_down[n, d]` is True exactly when the bar is tradeable (present, volume > 0, close > 0), the reference `prev` is finite and
  positive, `close < prev`, and either `close <= ARB(prev, date)` or the existing thin-bar rule fires at the 10% special-board lower
  limit. A bar is thin when it is one-price (high == low == close) or, before 2026-09-28, priced below Rp50. Avoid one-price bars in
  tests of the regular limit, or include them on purpose.
- `lock_up` is not affected by the correction on any date (the ARA side is unchanged).
- Required flips, with a regular (not one-price) bar: reference 1000 and close 930 is not locked on 2026-10-16 (ARB 850) and is
  locked on 2026-10-19 and 2026-10-20 (ARB 930); close 931 is not locked on any of the three dates; close 900 is not locked on
  2026-10-16 and is locked on 2026-10-19. Reference 14 and close 13 is not locked on 2026-10-16 (ARB 12) and is locked on
  2026-10-20 (ARB 13); reference 12 and close 11 is locked on both dates.
- With `price_limits=False` (US, crypto), `lock_up` and `lock_down` are all False for every date, including dates after 2026-12-31,
  and building does not raise. A `RulesUnconfirmedWarning` may or may not be emitted in that case; tests must not depend on it.
- With `price_limits=True` and bars dated after 2026-12-31, building does not raise.

## 5. Execution-level example (`idxsig.execution.execute`)

Existing API; see `tests/test_execution.py` (`one`, `test_exit_locked_at_arb_rolls_forward`) and `tests/support.py`. The corrected
rule must show up in a trade: a position whose scheduled exit session falls on 2026-10-19 and closes at the 7% lower limit (reference
1000, close 930) does not exit that session. The exit rolls to the next sellable session (`rolled_sessions == 1`) and the realised net
return uses that later session's close. The same price pattern with the exit session on 2026-10-16 (ARB 15%, limit 850) does not roll
(`rolled_sessions == 0`). Include a Rp11-14 variant for 2026-10-20 versus 2026-10-16. Explain each example in a docstring.

## 6. What tests must not do

- Assert any exchange rule for a date after 2026-12-31, or any symmetric lower limit for such dates (convention only, section 3).
- Assert any ARB on 2026-10-19 for a reference of Rp11 to Rp14 (SPEC_FINAL U5).
- Assert ETF, REIT, IPO, rights or warrant limits, a last-session date, or a holiday fact.
- Assert the order-volume rule together with price limits.
- Read raw price data, use the network, or depend on the order of tests.

## 7. One existing test must change

`idx-signals/tests/test_market.py`, in `AutoRejectionScheduleTests.test_april_2025_and_september_2026`, asserts
`lim(1000, "2027-01-04") == (1250, 750)`. That encodes an unconfirmed reversion as fact; section 3 supersedes it. Remove that
assertion from this test. Test 1 owns this edit. Any 2027 expectation belongs in the convention class.

## 8. Required coverage (author 1 for limits-level, author 2 for behaviour-level; overlaps are fine)

1. Dates: 2026-09-25 (before the Rp1 reform; context only), 2026-09-28, 2026-10-16 (Fri), 2026-10-17 (Sat), 2026-10-18 (Sun),
   2026-10-19, 2026-10-20, 2026-12-31, 2027-01-01, 2027-01-04.
2. Low-price boundaries: references 1, 2, 10, 11, 12, 13, 14, 15, 16 under each confirmed regime (except the P2 cells of U5).
3. Percentage-band boundaries: 199, 200, 201 (daggered, not a valid price), 202; 4990, 5000, 5001 (daggered), 5025.
4. Tick rounding: ARA floors, ARB ceils, on the valid-price grid of the limit price's own band. Include the own-band crossing rows
   (references 500, 4990, 5001, 5025) in a class labelled REPORTED, and all 20 observed anchors of SPEC_FINAL section 8, table-driven.
5. Board distinctions: `special_limits` (10%, Rp1-10 band) unchanged; the thin-bar rule in `Market.build` (a one-price bar 10% below
   the reference is locked on 2026-10-16 via the special-board limit, a regular bar at the same price is not).
6. Expiry: section 3, including the mixed-date call (dates around 2026-12-31 and 2027-01-04 in one call) and the warning category.
7. A property test against an exact-rational oracle written from SPEC_FINAL section 5 only (use `fractions.Fraction`): every valid
   reference price from Rp1 to Rp600,000, for the dates 2026-10-16, 2026-10-19 and 2026-10-20, excluding the U5 cells.
   Disagreements are information: report them, do not weaken the oracle to hide them.
8. Vector semantics: a 2-D (tickers, sessions) call with mixed regimes, shape preserved.
9. Regression guard (golden master): outputs for 2019-07-29 through 2026-10-18 equal the current module's. Capture the values from
   the unmodified module in your workspace before anything changes, for a grid of references (include every band edge and tick edge)
   and about 40 dates covering every regime and every regime start date; store them as a JSON fixture under
   `idx-signals/tests/fixtures/` and assert against it.
10. Market-level flips and the execution examples of sections 4 and 5.

## 9. Files, style, reporting

- Author 1: `idx-signals/tests/test_market_oct2026.py` (+ the fixture, + the edit of section 7).
- Author 2: `idx-signals/tests/test_market_oct2026_exec.py`.
- `unittest` classes; docstrings in the repo's style ("Guards against: ..."); every class that mixes confirmed and reported facts
  is split so that CONFIRMED and REPORTED facts live in separate classes. Pass `ruff check` with the repository `ruff.toml`
  (rules E4, E7, E9, F; ruff 0.14.3 is installed at the path in your brief). Deterministic, no network, each file under 30 seconds.
- Run your tests against the unmodified code in your workspace. New-behaviour tests will fail there; regression guards will pass.
  Report which is which.
- Report: files written; test count per class; which tests fail on the unmodified code and why; any ambiguity or error you found in
  SPEC_FINAL.md or this contract; and every path you opened outside your workspace and the spec pack (there should be none).
