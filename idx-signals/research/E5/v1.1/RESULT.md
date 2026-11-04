# E5-CEILING v1.1 (audit addendum) — corrected result: still NULL; one v1 Stage-1 pass was an artefact

Audit correction chosen after the v1 results were seen (Codex's independent review), not fresh independent validation.
Same pinned panels, parameters, seeds and gates as v1; only the two definitions in `ADDENDUM.md` changed. Code
commit `53447ca`, addendum freeze `5d7be0c`. v1 outputs unchanged under `research/E5/<MARKET>/`.

Stage 0 under v1.1: IDX, US, CRYPTO all REPRODUCED, matched baselines IDENTICAL (the market and rule-view
changes do not touch recorded runs).

## Original (v1) and corrected (v1.1), side by side

Paired = plan-window gross excess over matched controls, session-cluster bootstrap one-sided p (gate p < 0.025).

| Market / arm | Version | Label-eligible ticker-days | Plan-eligible ticker-days | Flags / with plan return | E30 precision | Lift vs matched | Paired excess [95 %] | p | Stage-1 gate | Stage 2 |
|---|---|---|---|---|---|---|---|---|---|---|
| IDX A (primary P1) | v1 | 323,304 | — (not enforced) | 968 / 968 | 0.212 | 3.92 | +0.0130 [−0.0034, +0.0306] | 0.065 | FAIL | not reached |
| IDX A (primary P1) | v1.1 | 323,304 | 322,576 | 969 / 969 | 0.212 | 3.91 | +0.0131 [−0.0046, +0.0311] | 0.074 | FAIL | not reached |
| IDX B (diagnostic) | v1 | 323,304 | — | 605 / 605 | 0.007 | 1.31 | +0.0040 [+0.0005, +0.0080] | 0.011 | **pass** | run: not admissible (9 scored) |
| IDX B (diagnostic) | v1.1 | 323,304 | 322,576 | 608 / 608 | 0.008 | 1.53 | +0.0021 [−0.0021, +0.0071] | 0.186 | **FAIL** | not reached |
| US A (diagnostic) | v1 | 2,670,089 | — | 3939 / 3939 | 0.133 | 2.23 | −0.0228 | 0.996 | FAIL | — |
| US A (diagnostic) | v1.1 | 2,670,089 | 2,665,465 | 3929 / 3915 | 0.133 | 2.23 | −0.0261 | 0.996 | FAIL | — |
| US B (diagnostic) | v1 | 2,670,089 | — | 7717 / 7717 | 0.020 | 0.84 | −0.0189 | 0.996 | FAIL | — |
| US B (diagnostic) | v1.1 | 2,670,089 | 2,665,465 | 7706 / 7682 | 0.019 | 0.84 | −0.0132 | 0.991 | FAIL | — |
| CRYPTO A (diagnostic) | v1 | 221,453 | — | 676 / 673 | 0.179 | 1.30 | −0.0228 | 0.941 | FAIL | — |
| CRYPTO A (diagnostic) | v1.1 | 221,453 | 221,137 | 675 / 672 | 0.194 | 1.41 | −0.0125 | 0.806 | FAIL | — |
| CRYPTO B (primary P2) | v1 | 221,453 | — | 505 / 505 | 0.149 | 0.96 | +0.0029 [−0.0229, +0.0288] | 0.441 | FAIL | — |
| CRYPTO B (primary P2) | v1.1 | 221,453 | 221,137 | 504 / 504 | 0.153 | 0.98 | +0.0035 [−0.0213, +0.0286] | 0.419 | FAIL | — |

KOD creep-quiet rows (A0, A1) use no age feature: flags, lifts and p-values are identical in v1 and v1.1
(A1 lift 1.01 / 0.97 / 1.00, every interval includes 1; a1_gate fails everywhere). Coefficients moved with the
age definition (max |Δ coef_U| IDX 0.106, CRYPTO 0.124, US 0.002); thresholds moved in the third decimal.

**Changed verdict:** IDX Arm B's Stage-1 pass in v1 (p 0.011) does not survive the corrected age definition
(p 0.186). Stage 2 therefore does not run for it in v1.1; its v1 Stage-2 row (9 scored, not admissible) stands as
a v1 record only. **Unchanged verdicts:** both primaries fail Stage 1; no arm is admissible; the a1 gate fails; the
pre-registered consequence of v1 still applies. Stage 3 (literal freeze) and Stage 4 (validation) were not run:
nothing selected, nothing to validate; 2023 untouched; holdout never loaded.

Finding A's reach was one session of flags per market (IDX 2022-12-23: A 1, B 1; US 2022-12-22: A 14, B 24;
CRYPTO 2022-12-26: none in the arms); its effect on every statistic is in the fourth decimal. Finding B is what
moved IDX B.

## Where the IDX primary fails (saved outputs only; nothing new was run)

| Step | IDX Arm A, 969 v1.1 flags (fill-independent) | Reproduced E1 run (the ara-type signal; fill evidence) | IDX Arm B, v1 Stage 2 |
|---|---|---|---|
| Signal | top 0.5 % of `logit_U`; flag-day return mean +26.5 %, 89 % of flags ≥ +20 % (a limit-up session) | E1 rule, 1109 signals | 614 signals |
| Movement before feasible entry (flag close → entry close t+1) | mean +5.2 %, median 0.0 %, 48 % positive (raw close, descriptive) | UNKNOWN (not computed) | UNKNOWN |
| Modeled fill / rejection | NOT RUN (Stage 2 not reached) | 251 scored of 1109: SKIP_ARA_LOCK 350, SKIP_LIQUIDITY 423, SKIP_NOT_TRADED 21, SKIP_NO_ENTRY_SESSION 15, SKIP_CAPACITY_UNKNOWN 2, INCOMPLETE 11 (FILL-C-v1, Rp 10 M, 10 % participation) | FILL-C: 9 scored of 614; plain close fill: 42 |
| Gross return, plan window t+1 → t+6 | mean +2.0 %, median −4.9 %; 37 % > 0; 35 % < −10 %; 11 % > +30 %; worst decile −33 %, best decile +51 %; matched +0.7 % | scored trades: gross mean −3.25 % | flags: +0.64 % vs matched +0.23 % |
| Costs | 0.15 % buy + 0.25 % sell = 0.40 % per round trip; one tick per side as sensitivity | net − gross ≈ −0.39 % | one-tick sensitivity: net −2.17 % (9 trades) |
| Modeled net return | NOT RUN | mean −3.64 %, median −5.9 %, hit rate 31 %; matched entries −0.44 % | −0.76 % (9 trades); plain close fill +0.33 % (42) |
| Concentrated losses | gross: 35 % of flags lose > 10 % | 36 % of trades lose > 10 %; worst decile mean −32 %, best +39 %; worst 10 % of trades = 36 % of total loss | UNKNOWN (trades not saved) |

**Why predicting a +30 % touch is not earning the trade's return.** The label is a path maximum inside t+1..t+5
measured from the flag close; the trade enters at the next close and exits at the sixth close. Three gaps sit in
between: the entry is on average 5 % above the flag close, so part of the touch is never bought; the exit is a
close after the touch, and the median flag closes 5 % below its entry; and the modeled fill selects against the
winners, because names still rising are locked or illiquid while names that stalled are fillable. Costs are
second-order next to these. Measured where stated; the last point is measured for the E1 signal and the IDX B
run, and is a hypothesis for Arm A, whose Stage 2 never ran.
