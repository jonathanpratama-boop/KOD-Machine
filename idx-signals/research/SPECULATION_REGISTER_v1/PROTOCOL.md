# Speculation Register v1 (KOD-SPEC-REGISTER-v1)

Frozen before the first speculation was sealed. Machine-readable in `protocol.json`; every
record names that file's SHA-256. Nothing here is a trade: the register never places an order,
never changes a paper decision, runs no plan the owner has retired, and never touches a sealed
holdout.

## Why: speculative design applied to the paper ledger

Speculative design builds artifacts from possible futures so that the present can be judged
against them. The paper ledger already does half of this: a decision is written before the
future arrives and scored when it does. But each decision carries one future (the frozen plan,
five sessions, +30% or not) and one verdict. After three weeks of scans the ledger says the same
thing every day: detection works, the plan does not, PASS. Every other future the name might
have had goes unrecorded, there is no matched yardstick beside the plan's own paper trade, and
the only data that could grade KOD's foresight without contamination, the data that does not
exist yet, is thrown away.

The register keeps that data. On every scan day, before the entry, it seals a **speculation
set** for each candidate: a cone of dated, falsifiable statements about the next five and
twenty sessions, each with the probability the frozen evidence gives it; the frozen plan applied
to the candidate and to five matched twins drawn from the same scan; and a tag. When the future
arrives, each statement is graded (Brier) and the plan is scored against its twins. The future
is the one sample that was never searched.

This is positive by design. The ledger's daily PASS becomes evidence that accumulates: how good
KOD's foresight is (calibration), which futures actually arrive and how often (base rates that no
record holds today, for the names and for their twins), and a prospective matched measurement of
the frozen line. No backtest is run, no discovery data is re-mined, no retired entry gets a new
variant.

Three tenses, as the method asks:
- **past**: the priors come only from frozen records (the 2023 validation runs and results);
- **present**: a set is sealed before its entry cutoff, hash-chained, stamped by two RFC 3161
  authorities and pushed, so its content and its time are provable;
- **future**: resolution reads bars that did not exist when the set was sealed, through the
  paper scorer's unit rules.

## What the owner's decisions allow, and what this protocol therefore contains

`handoff/decisions/2026-10-17_retire_G2_RET30_crypto_entry.md`: "no further exit, sizing or
filter variants are run on this entry. The daily paper scans may keep logging these days as
detections (descriptive only)." `handoff/decisions/2026-10-22_close_US_plus30_line_and_take_the_blueprint_next_step.md`:
"no further buy-side variant of this entry is run, including the delayed entry ... and a regime
filter. ... The daily paper scans keep logging these detections as descriptive records." E3
declares the IDX plan family exhausted on discovery and names prospective evidence as the only
route left.

So the register carries **one plan**, the frozen one (`BASE5`: the harness plan the 2023
validation scored, now measured on the future beside twins), and **no alternative plan**: no
longer hold, no confirmation entry, no stop, no regime-conditioned variant, no short. The cone's
statements describe the name's price path and the frozen plan's outcome; none computes the
return of a plan the owner retired. A pre-registered alternative plan would be a `v2` protocol,
written only if the owner reopens a line, with its own clock. The regime tag below is recorded as
scan metadata and nothing in v1 is reported conditional on it.

## Scope

| Market | Detector (frozen) | Decisions that get a set | Entry basis of the plan | Sealing cutoff |
|---|---|---|---|---|
| IDX | `MOONSHOT_E1_D1`, F1_ARA | every DECISION except NOT EXECUTABLE (names under Rp50) | the next session's close (closing auction; unfillable if not traded or locked at ARA) | 01:45 UTC of the entry session (before the pre-opening) |
| US | `MOONSHOT_E2_US_D1`, G2_RET30 | every DECISION except NOT EXECUTABLE | the next session's opening print | 13:30 UTC of the entry session |
| CRYPTO | `MOONSHOT_E2_CRYPTO_D1`, G2_RET30 | every DECISION except NOT EXECUTABLE (no live quote) | the Binance spot quote taken at sealing time, for the candidate and each twin (a twin without a quote cannot fill) | 02:00 UTC of the day after the signal day |

A set is sealed only if `sealed_at` is before its cutoff; a late set is not written (there is
no "late" record: the decision simply has no set, and the report counts it). The set binds the
DECISION's `record_hash`, the SCAN's `record_hash` and the scan's frozen features file hash.
Sets are written to `paper/speculations.jsonl`, a hash chain of the ledger's kind, stamped and
pushed in the same way; the file is append-only under `tools/check_append_only.py`.

No set is written for a decision whose entry has passed. The register starts with the first
scan after this protocol is committed. Nothing is backfilled: a speculation recorded after its
future is known is not a speculation. The register reads only bars pulled after each session; it
never opens a panel's holdout segment (IDX 2024-01-02 .. 2025-02-21; US and crypto 2024-01-01
onward stay sealed).

## The cone: statements and priors

Each set carries these statements about the candidate. A prior is taken only from a frozen
record and the record is named; where none exists the prior is the register's own running base
rate (the share of earlier resolved statements of that kind in the same market that came true),
0.5 while fewer than 20 have resolved. The prior used is written into the set at sealing time,
so no later information can change it. Every statement is also evaluated for each twin, so each
set yields the candidate's outcome and its twins' rate side by side.

| Id | Statement (closes on the reference chain; s = signal session) | Prior | Source | Resolves with |
|---|---|---|---|---|
| RUN30_5 | a close in s+1..s+5 is >= 1.30 x the signal close | IDX 0.1831, US 0.1537, CRYPTO 0.1846 | E30 precision in `research/E1/validation/result.json` (388e8111...), `research/E2/US/validation/result.json` (d7f05fcc...), `research/E2/CRYPTO/validation/result.json` (1b8c3bc4...) | BASE5 |
| FADE10_5 | the BASE5 net return is <= -10% | IDX 0.359, US 0.403, CRYPTO 0.511 | share of scored trades in the validation harness runs `20261009T050040Z_MOONSHOT_E1_D1_v1.1` (n 251), `20261008T115656Z_MOONSHOT_E2_US_D1_v1` (n 536), `20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1` (n 264) | BASE5 |
| GAIN0_5 | the BASE5 net return is > 0 | IDX 0.311, US 0.425, CRYPTO 0.314 | the same runs | BASE5 |
| BEATS_TWINS_5 | the BASE5 net return exceeds the median BASE5 net return of the twins that traded | 0.5 | the null; this rate moves away from 0.5 only if the signal carries information its twins lack | BASE5 |
| RUN30_20 | a close in s+1..s+20 is >= 1.30 x the signal close | running base rate | the register itself | PATH20 |
| DOUBLE_20 | a close in s+1..s+20 is >= 2.00 x the signal close | running base rate | the register itself | PATH20 |

Each resolved statement contributes a Brier term (prior - outcome)^2. The report shows, per
market and statement, the mean Brier of the register's priors beside 0.25 (an uninformed 0.5)
and beside the Brier of the running base rate, and the realised rate beside the twins' rate.
Foresight is good when the register's priors beat both references.

## The plan: BASE5, and the 20-session path

`BASE5` is the frozen plan: a long position of one unit, entered on the fixed basis above at
e = s+1, sold at the close of e+5, no stop (the 2023 validation runs had none; the paper
decision's own outcome in `ledger.jsonl` applies the policy's invalidation stop and is a
different record). Costs are the market profile's (`idxsig/profiles.py`: IDX 0.15% buy / 0.25%
sell; US the SEC fee plus the per-side tier at the price as traded; crypto 0.1% fee + 0.1%
slippage per side). An exit on a session where a sale is impossible (IDX: locked at ARB or
untraded; US and crypto: no bar) rolls to the next session where it is. A name whose bars end
before its exit, with the market's bars running at least 10 sessions past the target, is sold at
its last traded close (reason `data end`). Levels are compared on the reference chain
(cumulative close/previous), so a corporate-action reset is not read as a move. For crypto the
fixed entry is the sealing-time quote, where the harness used the next day's open; the
difference is recorded on every crypto set. The plan is applied identically to each twin (its own
signal close and fill conditions).

`PATH20` is not a plan: it is the 20-session window over which RUN30_20 and DOUBLE_20 are
graded, for the candidate and for each twin.

A crypto name with a close/previous ratio above 10 or below 0.1 inside its window is a
redenomination, not a move (the refuters' COCOS/DREP/LUNA/SUN/VIDT cases): the candidate's
resolution is UNRESOLVABLE with that reason; such a twin is dropped.

## Twins: five matched names per set

Drawn at sealing time from the scan's frozen features file, so the pool is exactly what the
scan saw. Pool: names fresh and eligible on the signal session, not flagged by the market's
selected detector, not a candidate of the scan, with a positive close (IDX: at least Rp50).
Matching, in priority order, on the scan's own features: price band (the profile's bands),
liquidity quintile (20-session median traded value, ranked within the pool), momentum tercile
(`ret20`), drawdown tercile (`dd60`). The deepest level with at least five other names is used
(all four; then without drawdown; then without momentum; then without liquidity; then the
whole pool); the level is recorded. Five distinct names are drawn without replacement with
`numpy.random.default_rng(seed)`, seed = the first 8 hex digits of
SHA-256("KOD-SPEC-REGISTER-v1:" + decision_id). The twins' signal-session close, reference
price, liquidity and features are written into the set so that resolution can reconcile their
units exactly as the paper scorer reconciles the candidate's.

## Tag

`hot_day` = the number of names the selected detector flagged in this scan is above the median
of the previous twenty scans' counts in the same market (null while fewer than ten earlier scans
exist). Scan metadata, recorded for the record only; v1 reports nothing conditional on it (a
regime filter is a variant the owner has ruled out for the US line).

## Resolution

`speculate-score` resolves a window when the market's bars cover it (BASE5: s+6; PATH20: s+20),
one RESOLUTION record per (set, window), with the candidate's trade, every twin's trade, the
paired difference (candidate net minus the mean net of the twins that traded), and the cone
statements of that window with their outcomes, the twins' rate and the Brier terms. Bars go
through the scoring preprocessing (`causal-close-v2`; IDX `idx-yahoo-recent-v1`). Units follow
`paper-score-v3`: from the provider's split records after the signal session, each corroborated
by an SEC filing for US names, never from a change in price ratios; the recorded signal close
must reconcile with the scoring bars. A candidate whose units cannot be established makes the
resolution UNRESOLVABLE with the reason; such a twin is dropped from that resolution with the
reason. A correction is a new RESOLUTION whose `revises` names the earlier one's hash.

## Primary question and decision rule (fixed now)

For each market: **does the frozen plan's net return exceed its twins' prospectively?** This is
the question the 2023 validation answered with no; the register asks it again of the future,
with twins, and reports.

- Unit of analysis for inference: the signal session. Sets of one session are averaged first
  (candidates flagged on the same day share that day), then a one-sided t-test on the per-session
  mean paired differences (t = mean / standard error, df = sessions - 1).
- A look happens the first time the plan has >= 60 resolved sets with a paired difference from
  >= 15 signal sessions, and again at >= 120 and >= 240. The report may show running numbers at
  any time; only these looks carry a verdict.
- Family: one plan per market (a Holm adjustment over one member is the raw p).
- ELIGIBLE FOR OWNER REVIEW at a look if p < 0.05, t >= 3.0 (the project's standing hurdle,
  `research/QUANT_GRADE/ROADMAP.md`) and the plan's mean net return after costs is > 0.
  CONFIRMED if the next look also meets all three. FAIL at the 240 look if never eligible.
- Each look adds a new file to `research/QUANT_GRADE/trials/`
  (`SPECULATION_REGISTER_v1_<market>_BASE5_n<look>.json`) whatever the outcome.
- An eligible or confirmed result changes nothing by itself. It would be evidence for the owner
  to weigh against the retirement decisions; any change to the paper policy is the owner's and
  would be a new `PAPER-POLICY` version.

A set contributes a paired difference only when the candidate and at least one twin traded.

## Secondary, descriptive (no verdict)

Calibration per statement (Brier against the two references); realised base rates for the
candidates and for their twins (RUN30_20 and DOUBLE_20 are rates no record holds today); the
cone per market as it narrows; twin coverage; the candidate rate per session and, from it, the
projected sessions to each look. A "time to a verdict" projection for a hypothetical true effect
(2, 5 and 10 points per set) uses the per-session standard deviation of paired differences
observed so far (the validation runs' trade dispersion until 10 sessions have resolved); it is
a projection, labelled as such.

## What this protocol does not allow

- No plan, statement, prior, twin rule or threshold changes in v1. Anything new is `v2`, with
  its own clock, never applied to sets sealed under v1.
- No backfill, no retroactive sets, no re-sealing. No reading of any holdout.
- No tuning on the register's own resolutions before a look; the report's running numbers are
  for monitoring, not for choosing.
- No order, ever; no change to `PAPER-POLICY-v4` or to `ledger.jsonl`; no variant of a retired
  entry.

## Commands

```sh
python3 -m idxsig speculate --market US --commit          # after paper-scan, before the entry cutoff
python3 -m idxsig speculate-score --market US --commit    # after paper-score; reuses its bars
python3 -m idxsig speculate-report                        # paper/SPECULATIONS.md and the cards
python3 -m idxsig paper-verify                            # also checks speculations.jsonl and every cutoff
```
