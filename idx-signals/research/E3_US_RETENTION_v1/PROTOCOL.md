# E3-US-RETENTION-v1: one-session retention before entry

Status: implementation-ready experimental specification plus tested decision-policy core.
No historical E3 execution run, matched-control result, or profitability estimate exists yet.
Freeze this document and policy before any E3 return evaluation. Source review base:
`994d299b993799037836245214219b6d5b9cd5b0`. This is an exploratory execution hypothesis,
proposed after seeing E2 validation failures; it is not an untouched validation result.

## One hypothesis

After the unchanged G2_RET30 flag at the close of session t, requiring the close of t+1
to retain the spike-day close separates some durable repricings from immediate reversals.
Buy at the regular-session open of t+2 only when C(t+1) >= C(t). Waiting may miss the
largest continuations and may worsen gap exposure. Those are costs of the hypothesis,
not reasons to change its threshold after seeing the results.

No parameter search, alternate retention thresholds, catalyst classifier, shorting,
new detector, take-profit optimisation or stop optimisation is included.

## What the existing evidence does and does not show

Read these frozen sources, not the obsolete original E2 estimates:

- `research/E2/repair_v2/REVIEW.md` and `results.json`.
- `research/E2/repair_v3/SELECTION_NOTE.md` and `results.json`.
- `results/runs/20261008T113137Z_MOONSHOT_E2_US_D1_v1/` (v2 fill A).
- `results/runs/20261008T113335Z_MOONSHOT_E2_US_D1_v1/` (v2 fill B).
- `results/runs/20261008T115656Z_MOONSHOT_E2_US_D1_v1/` (v3 fill B).
- `research/E2/protocol.json`, `idxsig/rules/moonshot_g.py`, `idxsig/execution.py`,
  `idxsig/controls.py`, `idxsig/profiles.py`, and `idxsig/backtest.py`.

The v2 trade-file diagnostics below include only EXITED rows. SKIP_OVERLAP rows retain
counterfactual returns in the CSV and MUST NOT be treated as scored trades. EXIT_DATA_END,
if present in later sources, must be included with its declared valuation sensitivity.

| Archived run | Scored | Gross mean | Net mean | Mean cost drag | Net median |
|---|---:|---:|---:|---:|---:|
| v2 A | 516 | -1.3921% | -2.2264% | 0.8343 pp | -4.2651% |
| v2 B | 438 | -0.9433% | -1.6907% | 0.7474 pp | -3.6461% |
| v3 B | 536 | -0.0952% | -0.9730% | 0.8779 pp | -4.2651% |

V2 B matched random averages -0.2996%, a 1.3911 pp shortfall. V3 B matched random
averages -0.7481%, a 0.2249 pp shortfall. V3 is a later sensitivity analysis, not evidence
that v2 was profitable. It releases 222 quarantined names, adds 193 signals, and changes
the studied population. Do not attribute the change entirely to better execution.

**Post-spike reversal:** gross as well as net returns are negative in these scored
samples; negative medians and win rates around 42-43% support an unfavourable typical
path with a positive tail. Detection's maximum forward close is a different target
from realised next-open-to-time-exit return. A price can hit a temporary high and still
produce a losing trade at the fixed exit. These files do not establish exactly when
the reversal occurs.

**Adverse selection:** G2 deliberately buys after a >=30% daily move. Its entrants are
not ordinary names; matched controls address some price/liquidity/risk differences but
do not measure temporary attention, offerings, catalyst quality, sector or free float.
The v2 B matching report has about 75.9% full matching; market cap is unknown for every
name, despite being listed among matching fields. Reversal is a measured price outcome;
information-based adverse selection is a plausible mechanism, not demonstrated causation.

**Execution:** A gates opening fills using final entry-day volume. B already replaces
that capacity input with known trailing volume, but still uses a daily bar to infer an
opening print. Neither daily bars nor 10% of daily median shares establish opening-auction
depth. Gap timing, LULD halts and spread costs are unmeasured. Cost drag matters, but
removing all assumed costs would not make v2 B's average return positive. No quantitative
decomposition of the control shortfall into gap, intraday reversal and later decay has
yet been reproduced. Different A/B samples prevent a clean causal A-versus-B comparison.

**Data:** the 2026 survivor universe omits earlier delistings; shared bias need not cancel
between events and controls. V3 explicitly finds outcome-correlated split quarantine:
later reverse-split names were disproportionately poor performers. Excluding them on
later verification status is a selection problem, not simply a conservative cost rule.
No split evidence does not prove no split. Provider adjustments, missing prints,
delisting losses, missing share counts and parser limits remain.

## Locked entry, sizing and exit

1. Obtain original G2 flags from the frozen E2 detector through its causal prefix path.
   Record origin session t before examining t+1. Do not recompute eligibility from
   winners, maximum forward return or corporate-action verification outcomes.
2. Use the exchange session calendar. At close t+1, require an actual observed close
   C(t+1) >= C(t), in consistent split-adjusted units. No forward filling, best day
   among several days, extra breakout or fresh G2 requirement. Failed retention is
   a recorded abstention. Missing confirmation data is UNRESOLVED, not a profitable skip.
3. Primary notional is $5,000. At each arm's decision close, require this to be no more
   than 1% of the median of the preceding 20 observed session dollar volumes, including
   the decision session. Dollar volume is consistent adjusted close x adjusted volume;
   present zero-trade days count as zero. Missing/invalid histories refuse a plan with
   an explicit reason. This ex-ante research capacity assumption is common to every
   new arm and is not inferred from outcomes. It avoids split-unit-dependent share
   capacity, but does not prove an opening order can be filled.
4. Submit a market-on-open paper order for t+2; no entry-day close or final volume may
   decide capacity, entry permission or sizing. Quantity is fixed at decision time from
   verified as-traded decision-close units, including the assumed buy-cost reserve.
   Reconcile shares across splits using archived evidence. Price the fill using a
   timestamped opening print. Do not use a future opening price to invent a pre-open
   share quantity. For missing units, use the fractional economic $5,000 shadow return
   and cost bounds; flag whole-share executability UNRESOLVED. Shadow results alone
   cannot satisfy the executable-advantage gate.
5. Historical daily-bar open is a labelled proxy only. Without a timestamped print,
   classify the simulated trade PROXY_FILL. A absent open/known suspension is NO_FILL;
   ambiguous missing data is UNRESOLVED. Never replace it with a later convenient fill.
   Actual print timing after 09:30 must be recorded in a measured-fill confirmation run.
6. Preserve the legacy time-exit convention: target close = entry session index + 5,
   hence t+7 for this policy, versus t+6 for original next-open. Record the session
   indices and dates to eliminate off-by-one interpretations of 'five sessions'.
   A scheduled market-on-close exit must use verified prints in the executable run.
   Carry halted positions to the first executable exit and report duration and loss.
   Missing exits/delistings require recovery evidence and a zero-recovery sensitivity;
   they must not disappear from reported returns. This experiment has no tuned stop or
   profit target. It is not an entry-eligible plan under Jonathan's live trading doctrine.
7. One position or pending order per ticker. Process origins chronologically. Suppress
   later origins until the scheduled/actual exit; log suppressed origins separately.
   Apply the identical rule to every arm and control path. No leverage or shorting.

## Costs and population sensitivity

Primary historical cost schedule retains US profile rates per side: < $1: 1.5%; $1-5:
0.5%; $5-20: 0.15%; >= $20: 0.05%, with 0.00278% model sale fee. Match the existing
code's boundaries exactly (1, 5, 20 enter the next tier). These represent assumed spread,
slippage and charges, not observed quotes or a claim about the correct historical SEC fee.
Entry and exit each use their own session's as-traded price. Apply costs to actual traded
value. Run a doubled spread/slippage stress with the sale fee unchanged.

Keep the complete available survivor population, including split-quarantined names, in
all arms and control pools. Existing unit verification may narrow price-level uncertainty
but must not determine inclusion. For unresolved price units, price ratio returns use
the provider's consistent adjusted series; report provider-tier estimates plus the full
0.05%-1.5% per-side cost envelope. For the conservative excess-return bound charge the
rule the highest cost and controls the lowest cost for every ambiguous unit case. Also
give a unit-free matching sensitivity that omits price bands for ALL names, not just
losers. These bounds concern cost assumptions only: they do not validate a wrong price
series, split ratio, missing stock or fill. Invalid prices need explicit unresolved
coverage and evidence review. Do not silently winsorise, drop anomalies or use future
QA flags as decision inputs.

## Historical comparison design

Three same-origin arms are mandatory, with identical population, dollar capacity and costs:

- A: unconditional next-open entry t+1 (new common assumptions; not an overwrite of E2).
- B: unconditional delayed entry t+2 (at t+1, no retention condition).
- C: retained-close delayed entry t+2 (the single primary candidate).

C versus B isolates the retention gate. B versus A diagnoses the one-session delay.
These are ablations of one hypothesis, not three candidates to rank and tune.
Reproduce archived E2 B separately for reconciliation, under its original assumptions;
do not call differences under the new 1% dollar-capacity rule a reproduction.

For each original event at t, draw 200 matched random origins from other evaluable names
on t, using archived controls-v2 causal features and seed 20261007 + 1. Never choose
'non-events' using future returns. Save control identities before examining t+1. Apply
the same A/B/C gates, capacity, costs and exits to those origins. Maintain each control
draw's own overlap state; repeat control identities are allowed by the frozen sampling
method and their dependence must be accounted for. Report each matching relaxation,
unknown feature and event/control unresolved rate. 200 draws supply a comparison
distribution, not 200 independent market histories. Do not retrospectively rematch on
confirmation or future profitability to rescue a weak result.

Primary opportunity return is net dollars / $5,000 per original origin, with recorded
abstentions and definite no-fills assigned zero. Unresolved fills/exits receive explicitly
reported evidence bounds, never a convenient zero. Also report conditional filled-trade
mean, median, hit rate, downside tail, number of trades, abstention rate and capital-days.
Report portfolio exposure/cash usage; equal per-origin averages are not an account CAGR.

For mechanism diagnosis only, decompose each legacy filled trade's log gross return into
signal-close-to-next-open gap, entry-open-to-entry-close, and subsequent-close-to-exit.
Use the same constituent session dates and consistent adjusted units. Gap before entry
is missed/purchased repricing, not realised holding P&L. Tabulate the predeclared C>=C(t)
retained and failed groups, with missing groups shown separately. These descriptive
2023 summaries may explain losses but cannot select thresholds or count as fresh testing.

## Samples, statistics and sealed data

Implementation development uses synthetic data. Historical screening uses only
2020-07-01..2022-12-31, with earlier 2020 data solely for causal warm-up. Mask later rows
before detector construction, matching or planning. All entry/exit windows must end
inside the screening period. The original 2023 validation is spent: any replay there
is explicitly diagnostic and must not be presented as independent confirmation.
Do not open or evaluate 2024-01-01..2026-12-31 holdout data in this task.

Historical screening requires >=800 resolved executed C trades, >=200 unique tickers,
>=100 unique entry sessions and >=50 calendar weeks. These are minimum coverage gates,
not an assertion that statistical power is adequate. E2 B's roughly 31% trade-return
standard deviation gives about 837 independent observations for 80% power at a one-sided
5% test of a 3 pp mean effect; ticker/time clustering can require materially more.
Report achieved precision and the effective number of clusters. Smaller samples are
INCONCLUSIVE; do not relax gates or tune thresholds to obtain a passing sample.

Use 10,000 pre-seeded calendar-block bootstrap replicates (seed 20261009, mean block
length 10 exchange sessions) on aggregated date P&L, retaining all origins on each sampled
date together. Include a ticker-cluster sensitivity. Bound unresolved P&L on identical
origins; preserve event/control pairings. Report the weaker confidence conclusion across
the two dependence treatments. This design is for the opportunity metric; conditional
means need their own resampled numerator/denominator, not a fixed trade count.

## Predeclared advance, reject and stop conditions

Advance from exploratory screening only if all are true:

1. Coverage gates pass and unresolved execution does not carry the result.
2. C has a conditional mean net return >=0.5% per resolved trade and its one-sided 95%
   lower confidence bound is >0; opportunity P&L is also positive with lower bound >0.
3. C minus matched-control C and C minus unconditional-delay B have positive opportunity
   excess-return lower bounds. Abstention alone can beat a losing baseline, so positive
   absolute net return is independently required.
4. The excess-return conclusion survives doubled costs and the conservative ambiguous
   unit envelope; removing the five largest positive C trades does not make mean net
   return negative. That removal is a robustness report, not a new tradable policy.
5. Measured-print, quote/cost and delisting evidence support executability. Daily-bar
   proxies alone can justify collecting those data, not declaring executable advantage.

Reject this exact candidate if sufficient evidence yields nonpositive conditional net
mean or nonpositive opportunity excess versus either primary comparator, or if a valid
cost/unit sensitivity destroys the advantage. If estimates are positive but confidence
or sample gates fail, label INCONCLUSIVE and collect independent data; do not claim
rejection proves every retention strategy impossible. Data corruption or differential
unresolved coverage is a blocked experiment, not a trading conclusion.

Passing exploratory historical gates justifies preregistering independent confirmation,
not live trading. Before any eventual one-shot holdout access, require an explicit
separate evaluation plan and authorization. Forward confirmation can instead begin on
2027-01-01, after the currently reserved holdout period, under a prospectively frozen
policy and immutable event ledger. Do not silently consume 2026 reserved dates.

## Implementation contract and reproducibility

`policy.py` implements only the timing/retention/dollar-capacity decision core.
`tests/test_e3_retention_policy.py` checks prefix invariance, missing sessions, failed
retention, unit rescaling, zero-volume histories and explicit entry/exit offsets.
It is deliberately not registered in `idxsig.rules` or the live paper policy.

Historical integration still must:

1. Extract and SHA-256-verify the archived repaired panel/input data in a disposable
   worktree using `data/archive/` instructions. The source tree does not contain the
   4,443,730-row panel; the GitHub connector can retrieve code and trade artifacts but
   does not supply this full input as an executable local panel here.
2. Freeze hashes of this protocol, policy, original E2 detector, panel manifest, costs,
   controls and environment BEFORE running screening outcomes. Use exclusive creation
   of a new experiment output directory. Never append outputs to an old E2 run.
3. Reuse causal detector prefix evaluation; feed frozen G2 flags into this core. Add
   measured/proxy fill handling, decision-fixed sizing, end-date restrictions, same-origin
   overlap and A/B/C opportunity ledgers without modifying production executors.
4. Save one row per arm/event/control origin: ticker, origin/decision/entry/exit timestamps,
   flag, retained close, eligibility and reason, capacity inputs, quote/print sources,
   sizing units/verification, cost assumptions/bounds, P&L, abstentions, overlaps and
   unresolved evidence. Export matched identities, input hashes and all exclusions.
5. Prove that changing future volume cannot change an earlier capacity/order decision;
   removing future sessions leaves earlier decisions unchanged; changing future QA or
   unit-verification outcomes cannot change population; control overlap is enforced;
   and inaccessible holdout data are never loaded. Verify baseline reconciliation before
   interpreting C. Validate result hashes and append-only checks.

The highest-value next experiment is this one-session retention test on a population
that is not selected by later split-verification outcomes. A clear, positive, cost-robust
absolute and control-adjusted result warrants independent confirmation. A nonpositive
or fragile result closes this execution hypothesis without changing the detector or
rewriting history. Software test success is not return evidence.
