# Experiment E3: execution plans for the IDX ARA detectors (KOD-IDX-E3-v1)

Frozen before any analysis. The machine-readable protocol is `protocol.json`; every result
file records its SHA-256. Code: `idxsig/e3.py` (study), `idxsig/rules/moonshot_e3.py`
(candidate detectors and, after the freeze, the selected pair), `idxsig/execution.py`
(`ENTRY_RULES`, `EXIT_RULES`: the plans), `tests/test_plans.py` and `tests/test_e3.py`.

**Why.** E1 froze F1_ARA (a close locked at the upper auto-rejection limit) as D1 and found it
detects repricings better than chance (precision 18.3% at +30% vs 1.96% for matched names in
2023, 9.3x) and loses money under the one plan the harness had: buy the next close, hold five
sessions (-4.06% net per trade vs -0.53% for matched random entries). The fills come when the
continuation fails; the names still locked at ARA cannot be bought. The paper policy has
passed on every candidate since. This experiment asks whether a different, pre-specified way of
entering and leaving changes that.

**Question.** Is there a plan from a fixed family under which the signals of the E1 family's
ARA detectors, traded through the same harness, earn a positive average net return and beat
matched random entries executed under the same plan?

**Data.** The IDX panel rebuilt from the pinned mirror commit (`bc0ac771`), TIER_1 only, and
its corporate-action registry; the manifest names are written into `protocol.json` when the
rebuild finishes and before any E3 statistic. **Precondition:** the two recorded E1 trading
runs (`20261008T000401Z`, fill model A; `20261009T050040Z`, fill model C) are re-run on this
data with their original configuration (`idxsig e3-reproduce`). Identical signals, scored
counts, status counts, average net return and matched-random mean = REPRODUCED. Anything
else is recorded as DEVIATES and discovery runs only with `--accept-deviation`, which is itself
recorded.

**Detectors.** F1_ARA (D1), F7_ARA_VOL3 (ARA and volume >= 3x median), F8_ARA_EARLY (ARA and
20-session return below +50%): the three ARA members of the E1 family, their code copied into
`moonshot_e3.py` (a rule module imports nothing from the package; a test checks the copy flags
exactly as the original). No rule outside the E1 family is admitted.

**Plans.** 4 entries x 3 exits x 3 holding periods = 36 per detector, 108 runs in all:

| Entry | |
|---|---|
| fixed | buy at the close of s+1 (the original model) |
| confirm | the first close in s+1..s+3 above the signal close (reference chain), traded, not locked at ARA |
| pullback | the first such close below the signal close |
| unlock | the first traded close in s+1..s+3 not locked at ARA |

| Exit | |
|---|---|
| fixed | the close of the holding_days-th session after entry (the original model) |
| stop_ref | the first close at or below the signal session's reference price (the level before the signal day), else fixed |
| first_down | the first close below its own reference price (a down day), else fixed |

Holding periods 2, 3, 5 sessions. A conditional entry that never triggers is no trade
(`SKIP_NO_TRIGGER`). Levels are compared on the reference chain, so a corporate-action reset is
never read as a move. A sale that lands on a session locked at ARB or untraded rolls forward,
as before. The default plan reproduces every earlier run byte for byte.

**Harness.** Lots, fees (0.15% / 0.25%), notional Rp 10,000,000, at most 10% of decision-time
capacity (FILL-C-v1), corporate-action registry, overlap skipped, 200 matched and 200
same-session random draws, seed 20261007, prefix-first causal signals. The same settings for
every run; the matched-random baseline executes the same plan.

**Periods.** As E1: discovery 2021-01-22 .. 2022-12-30, validation 2023, holdout 2024-01-02 ..
2025-02-21. The holdout is sealed in code: the harness refuses any detector window that
touches it unless `--holdout-final` is given, which E3 never gives.

**Selection, on discovery only.** Admissible if scored trades >= 200, average net return > 0,
one-sided p < 0.05 against matched random (200 draws; the floor is 0.005), and average net
return > 0 in each discovery year with at least 50 scored trades. Of the admissible pairs, the
highest average net return wins; ties by more scored trades, then grid order. The whole table
is published (`discovery/plans.csv`), with D1's original plan under fill model C as the
reference row. The winner is written into `moonshot_e3.SELECTED` and committed before any
validation number exists; `MOONSHOT_E3_D1` then carries the plan, so its rule hash covers it.
No admissible pair = no `MOONSHOT_E3_D1`, and the paper policy keeps PASS.

**Validation.** One recorded harness run of the frozen pair on 2023. Pass if scored >= 100,
average net return > 0 and p < 0.05 against matched random. Hit rate, median, fill rate and
the same-session baseline are reported, not judged.

**Consequence.** A pass lets `PAPER-POLICY-v4` underwrite a paper BUY ON TRIGGER for
`MOONSHOT_E3_D1` candidates, with the plan's own trigger and exit, each decision scored
prospectively by `paper-score`. A fail leaves the policy at PASS and this plan family
exhausted for these detectors. Either way, no real orders and no entry permission; the holdout
stays reserved for one final test after prospective evidence exists.

**Claims.** Historical research. 108 plans were searched on discovery and validation is the one
confirmatory test; a pass there is one year of one market under assumed costs and daily-bar
fills.
