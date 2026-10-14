# E5-CEILING (KOD-GLOBAL-E5-v1) — DRAFT protocol, not yet frozen

`research/E5/protocol.json` is the protocol; this file states it in prose and records the freeze. The code
that runs it is `idxsig/e5.py` (every parameter is read from `protocol.json`; `e5.PROTOCOL_KEYS` lists each
key and the stage that reads it), the rule family is `idxsig/rules/moonshot_e5.py`, the CLI is
`python3 -m idxsig e5-reproduce | e5-discovery [--accept-deviation] | e5-freeze | e5-validation --market IDX|US|CRYPTO`.

**Freeze record.** `frozen_before_analysis` is `false` in this draft. The freeze is one commit of
`protocol.json` (with `frozen_before_analysis: true`) and this file under `research/E5/` (append-only), made
before any Stage-0 statistic; its commit hash and the file's sha256 are written here at that time:

    freeze commit: PENDING
    protocol.json sha256 at freeze: PENDING

Every stage output carries `protocol_sha256` of the committed file and `code.commit`.

## Question and null

At the close of session t, does any pre-registered combination of daily-bar features carry tradeable
DIRECTION for sessions t+1..t+5 over the full evaluable universe, beyond matched controls, or is the lab's
validated detection (F1_ARA 9.3x, G2_RET30 5.4x / 4.6x matched-random lift) variance detection that cannot
be traded? Secondary: does multi-session pre-move structure (volume creep, quiet range, volatility
contraction, re-base), including the KOD-DET-v0 VOLUME_CREEP_PRICE_QUIET definition, carry +30% information?

Null: no daily-bar combination separates the coming +30% moves from the coming large down-moves; rankers
trained on U and D select the same high-variance names; the paired plan-window excess of their flags over
matched controls is <= 0 in every market and every discovery year.

By the lab's own prior the likely outcome is a null, and the null is the valuable result.

## Family (one ranker per market and arm, two descriptive detectors)

* Module `idxsig/rules/moonshot_e5.py`, long only, holding 5 sessions. Candidate rule ids
  `E5_CAND_<MARKET>_<ARM>`, `E5_CAND_A0_CREEP_QUIET`, `E5_CAND_A1_CREEP_QUIET_NR`; after the freeze
  `MOONSHOT_E5_<MARKET>_D1` for the selected arm.
* Arm A scores `logit_U`; Arm B scores `logit_U - logit_D`.
* Features: the 41 columns of `moonshot_e5.FEATURE_ORDER` (18 ranked features, their squares, 5 binaries),
  the same order in every market. Conventions, as the merged module computes them (fix commit 8b94372):
  * rank = `(rank - 0.5) / n` with midrank ties among names present AND tradeable at the session, the pool
    masked by `present` before ranking (prefix-first); a NaN value ranks 0.5; the squared rank is its own
    column; binaries enter as 0/1.
  * `vol20` as `e1.Study._signals` (a present but untraded session is a zero log return); `vc10_60` with
    `min_periods` 8/10 and 45/60; `creep5v20` needs full 5/20 present windows; `rngr5` 5 of 5.
  * `rebase`: some s0 in [t-40, t-6] was a spike, pre = level(s0-1), peak = max level(s0..t),
    level(t) <= pre + 0.5 (peak - pre) and min level(t-4..t) >= pre; spike = (ret1 >= 0.30) | (lock_up &
    tradeable): on IDX a declared superset of the synthesis draft's lock_up-only definition.
  * binaries treat an undefined input as 0 (`not_repriced` is 0 when ret20 is NaN; `quiet` is 0 when any
    input is NaN).
  * `FEATURE_WARMUP = 60` (every feature NaN in the first 60 columns of a view), `DEBOUNCE = 5`,
    `WARMUP = 65` (`compute()` NaN in the first 65 columns). Every Study and harness window therefore starts
    65 sessions before its period (the synthesis draft's "60" was the feature warm-up alone).
  * debounce: a flag is the first session a name's state is True after 5 trailing sessions KNOWN to be
    False (column s reads s-5..s only); a NaN score is unknown, never "outside"; names outside the ranking
    pool (absent or untraded) have finite scores (ranks 0.5) and count as known-outside, so a name can flag
    on its first listed session (window-invariant, not look-ahead); an undefined A0/A1 fact is a known False
    state. Proof of causality and window invariance: `tests/test_e5_rules.py` (RankTests, FlagTests) and
    `tests/test_e5.py WindowInvariance`.
* A0_CREEP_QUIET = creep5v20 >= 1.5 AND quiet; A1_CREEP_QUIET_NR = A0 AND not_repriced; both debounced,
  reported as the KOD population row; A1 gets one Stage-2 harness run only if its discovery lift vs
  volatility-matched controls is >= 2.0 with one-sided p < 0.05.

## Learner

L2 logistic regression, numpy IRLS, 25 iterations from beta = 0, lambda = 1e-3 x n_rows_used, penalty on
the coefficients only; all positives (weight 1) plus a seeded 10% subsample of the negatives (weight 10),
seed 20261015, one generator per fit; 6 fits (3 markets x {U, D}). Threshold per arm = the discovery 99.5th
percentile of the arm's score over the market's evaluable discovery ticker-days, fixed once, never searched.
Constant columns (gap on IDX, ara off IDX) are tolerated by the ridge and reported per market.

## Labels

U = max level(t+1..t+5) / level(t) >= 1.30 on the reference chain (`e1.Study.level`). D on US and CRYPTO =
min level(t+1..t+5) / level(t) <= 1/1.30. D on IDX = rate-matched: the k-th smallest 5-session minimum ratio
over the evaluable discovery ticker-days, k = the U positives there, so P(D) = P(U) on discovery (IDX Arm B
is DIAGNOSTIC: ARB was 7% flat through all of discovery and changes 2023-06-05 and 2023-09-04; IDX arm
statistics are also reported by ARB regime). Labels need t+5 inside the period. Crypto unit resets
(close/prev >= 20 or <= 1/20) censor the labels of t-5..t of that name and the Stage-1 plan-window return
of any flag whose window contains the reset; the known cases to verify are listed in `protocol.json`
(COCOS 2021-01-23, DREP 2021-04-02, SUN 2021-06-18, LUNA 2022-05-31, VIDT 2022-11-09, BNX 2023-02-22,
QUICK 2023-07-21, BTCST 2021-03-19).

## Markets, panels, periods

| market | panel (manifest) | format | precondition run | status |
|---|---|---|---|---|
| IDX | `panel-20261007T225823Z.json` (9d3a0718...), registry `ca_registry-20261007T230210Z.json` | panel-v2 | `results/runs/20261009T050040Z_MOONSHOT_E1_D1_v1.1` | DECISIVE for Arm A (P1) |
| US | `panel_us_repair-20261008T114805Z.json` (8d3b7ce4...), units as_traded, quarantine none | panel-global-v2-units | `results/runs/20261008T115656Z_MOONSHOT_E2_US_D1_v1` | DIAGNOSTIC (survivor-only) |
| CRYPTO | `panel_crypto-20261008T003354Z.json` (3dc12749...), jump_ratio 10 | panel-global-v1 | `results/runs/20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1` | DECISIVE for Arm B (P2) |

CRYPTO_CLOSE (`profiles.CRYPTO_CLOSE`, entry at the close of t+1, fill model A, long only) is a sensitivity
inside the CRYPTO stage sharing CRYPTO's panel; never a top-level market. E3's newer IDX panel
`panel-20261013T194245Z` could not be rebuilt on this machine (the Yahoo raw files of its pull are absent,
no network pull), so the pinned run's own panel and registry are PRIMARY and Stage 0 is a true
reproduction. Each market entry carries its own `panel_format`; `e1.Study` resolves the keyword, then
`markets.<M>.panel_format`, then `data.panel_format`; `e5.py` passes the market's format as the keyword too.

Periods: discovery IDX 2021-01-22..2022-12-30, US/CRYPTO 2020-07-01..2022-12-31; validation IDX
2023-01-02..2023-12-29, US/CRYPTO 2023-01-01..2023-12-31; discovery years for the per-year gates IDX 2021,
2022; US/CRYPTO 2020 (from July), 2021, 2022. The top-level `periods` and `weak_signals` blocks are in the
E2 shape `e1.Study` reads (the union of the per-market periods; no `ign`). The holdout (IDX 2024-01-02..
2025-02-21, US/CRYPTO 2024 on) is never loaded: `e5.assert_within_validation` refuses any window end past
the market's validation end before a RunConfig or Study exists, and the harness refuses it again. The IDX
65-session warm-up before 2021-01-22 falls in TIER_2 and is used for features only.

## Plans (one per market, the recorded one, no plan search)

IDX next close -> 5th close, fill C primary, ca_mode registry, Rp10,000,000, lot 100, max participation
0.10; sensitivities: fill A, one IDX tick per side (`RunConfig.tick_cost`, additive, default off). US next
open -> 5th close, fill B primary, as-traded units, $5,000, profile cost tiers; sensitivities: fill A
as-traded, quarantine unit_schedule, +1.5% per side. CRYPTO next open -> 5th close, fill A, $5,000, 0.1%
fee + 0.1% tier per side, jump_ratio 10; sensitivities: participation 0.05 with doubled costs, entry at the
close of t+1 (CRYPTO_CLOSE). One extra run per arm with controls v2 is reported, never judged.

## Matched controls and the paired statistic

Trading stage: controls v3 (volatility quintile ahead of market_cap), 200 draws, seed 20261007; v2
reported. Detection stage: `e1.Study(pool_units="as_traded" on US, pool_version="v3")`, 200 draws per flag,
seed 20261008. Paired statistic: per flag (or trade) its outcome minus the mean outcome of its matched
controls, mean excess with a session-cluster bootstrap (`backtest.paired_excess`, 10,000 resamples, seed
20261015, one-sided p); any gate is NOT judged when n_clusters < 2. The harness's draw-distribution p is
reported, not judged.

## Stages

0. **reproduce** — each precondition run re-run from ITS recorded `summary.json` config on the pinned panel.
   REPRODUCED iff the rule side (signals, scored, status_counts, avg_net_return) is identical and the
   matched baseline is identical or within the one accepted deviation (controls.py bcb89f0, |diff| <= 0.001).
1. **information** (discovery, fill-independent) — fits, thresholds, debounced flags; plan-window return on
   the reference chain for flags and matched controls alike (entry level at the close of t+1 on IDX, open of
   t+1 on US/CRYPTO, exit level at the 5th close after entry; no fill, lot, lock or cost filter); AUC_U,
   AUC_D, E30/D30 precision and lift vs base and vs matched (cluster CI, draw p), directional ratio with a
   cluster-bootstrap CI, pre-move split (ret1 < 0.10 vs >= 0.10), the univariate matched-set AUC/lift table
   for every ranked and binary feature, the A0/A1 rows, the constant-column report, the IDX by-regime split.
   Gate to Stage 2: debounced flags >= 200 AND paired gross excess > 0 with cluster p < 0.025 AND excess > 0
   in every discovery year with >= 50 flags. Primaries P1 = IDX Arm A, P2 = CRYPTO Arm B (alpha 0.025 =
   Bonferroni over the two); everything else diagnostic.
2. **execution** (discovery) — only arms that passed Stage 1 (plus A1 if gated): `backtest.run` under the
   market plan with the primary fill model and controls v3, then `backtest.paired_excess` on the trades;
   every run (primary, each sensitivity, the v2 report) is one `plans.csv` row and one summary under
   `discovery/runs/<RunConfig market>/<arm>_<run>.json`. Admissible iff `e3.admissibility` verbatim AND
   paired NET excess p < 0.025 AND every judged sensitivity keeps rule-minus-matched > 0 AND admissibility
   holds on the subset of trades with exit-session participation <= 10%. In-flag break-even precision p* is
   a descriptive bound. The arms have no frozen literals yet: the runs inject `discovery/model.json` into the
   module tables in-process (`e5.literals_from`); its sha256 is in every row.
3. **freeze** — `e5-freeze` copies `discovery/model.json` into the `moonshot_e5.py` literal tables and sets
   SELECTED for the market; refuses if the market's literals are already set. A0/A1 recorded runs happen only
   after this commit, so their rule sha is the frozen one.
4. **validation** (2023) — refuses unless the module literals equal `model.json`; one `write_run`-recorded
   run per Stage-2-admissible arm (and the gated A1) plus its sensitivities. Pass iff scored >= 100 (US >=
   200), average net > 0, paired net excess p < 0.025, harness p < 0.05, sensitivities agree in sign,
   detection Wilson lower bound > the 2023 base rate. Claim level PROVISIONAL.

## Declared leaks, not fixed, search size, claims

2023 is once-seen for the univariate siblings of E5's features (the E1/E2 validation episode tables on disk
are named in `protocol.json`): any 2023 pass is PROVISIONAL and licenses only a prospective paper policy.
The legacy crypto panel carries two future-informed row deletions (declared, not rebuilt). Not fixed and
why: `protocol.json` `not_fixed_and_why`. Search size: 6 fits, 2 arms x 3 markets, 2 primaries, no
threshold/lambda/feature search. Claims: historical research on assumed costs, daily-bar fills and a
survivor-only US universe; nothing here is prospective performance; no real orders.

## Runtime note

`moonshot_e5.compute()` is about 12x `moonshot_g.features` and `rules.causal_signals` recomputes it per
session, so Stage-2 and validation harness runs use `lookahead_cuts = 12` (one full-window call checked
against 12 prefixes, deterministic); the module's own prefix-invariance tests are the proof of causality and
the setting is recorded in every run. Stage 0 keeps each recorded run's own setting.

## Freeze

Frozen on 2026-10-14 before any Stage-0 statistic. The freeze commit is the commit that adds this file
and `protocol.json` to branch `claude/e5-ceiling` (`git log --diff-filter=A -- idx-signals/research/E5/protocol.json`);
`frozen_before_analysis` is `true` in `protocol.json`, and every stage output records `protocol_sha256` of the
committed file. Review: orchestrator only (the three-lens reviewer workflow was skipped for budget); mechanical
guards at the freeze: `tests/test_e5.py` (35), the full suite (356), `idxsig verify-runs`, `idxsig rules`,
`tools/check_append_only.py --all`, all passing on commit `30a442f`.
