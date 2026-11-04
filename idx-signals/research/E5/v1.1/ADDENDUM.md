# E5-CEILING addendum v1.1 (KOD-GLOBAL-E5-v1.1): audit corrections, frozen before the corrected runs

**What this is.** Two defects found by Codex's independent review of the published v1 result (draft PR #8, head
`d0ce9ba`) are corrected here, with the smallest change that fixes each, and the discovery stages are re-run from the
same pinned panels under the same parameters. This is an audit correction chosen after the v1 results were seen. It is
not fresh independent validation, and nothing here grants trading permission. The v1 files under `research/E5/<MARKET>/`
are preserved unchanged; the corrected outputs go under `research/E5/v1.1/<MARKET>/`.

**Finding A, discovery boundary.** v1's label eligibility required t and t+5 inside the period, but the plan window exits
at the close of t+6, and the discovery study kept validation rows. Flags on the last eligible session (IDX 2022-12-23,
US 2022-12-22, CRYPTO 2022-12-26) and their matched controls were therefore scored with the first post-period close.
Witness: INPS, Arm A, 2022-12-23. Correction: the study holds the period's sessions only; a flag's plan window counts
only when its exit session is inside the period, flags and controls alike; label eligibility is unchanged; both
denominators are written to `stage1.json` under `eligibility`. Reach in v1: at most one session of flags per market.

**Finding B, listing age.** v1 counted `age` from the first present column of the current window, so every name listed
before the window start had the same window-relative age and a window start past a listing changed same-date age ranks
and scores beyond the warm-up. Correction: `execution.Market` carries `listed_before` (sessions a name was listed before
the window's first session, counted on the full pinned panel and carried through every slice), `rules.RuleView` exposes
it, and `moonshot_e5` takes it as an explicit input and refuses to run without it. The count is left-censored at the
pinned panel's first session (IDX 2019-07-29), which is declared, not invented. This changes a feature DEFINITION, not
the feature list, and changes every E5 rule hash (`protocol.json` `addendum.rule_sha_v1` vs `rule_sha_v1.1`).

**Not changed.** Thresholds, alpha, learner, feature list, plans, periods, seeds, draws, gates, markets and panels are
identical to v1. No threshold, significance level, feature, model, plan or subgroup was tuned.

**Disclosed, not fixed.** The controls' listing-age bucket is window-dependent in the same way and is left as recorded,
because the matched baselines of the recorded runs depend on it (Stage 0 must still reproduce them). Overlapping plan
windows on adjacent sessions remain only partly addressed by the session-cluster bootstrap.

Code commit `53447ca`. Regression tests: `tests/test_e5_rules.py ListingAgeTests`, `tests/test_e5.py
PlanWindowEligibilityTests`. The freeze of this addendum is the commit that adds this directory.
