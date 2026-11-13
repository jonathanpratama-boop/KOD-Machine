# LLM_ARM_v1, addendum 1: how the frozen scoring sentence is computed

Written 2026-11-13 (UTC) by Claude (the author of most calls), BEFORE any Brier score, outcome rate or return of an
LLM_ARM call was computed or read by the author. `PROTOCOL.md` is unchanged. This file only fixes the readings that its
scoring and look sentences leave open, so that an interim view requested by the owner on 2026-11-13 and the frozen
first look use one rule. The code is `score_v1.py` beside this file; its sha256 is recorded in the stamped manifest.

Known before writing (structure only, no outcomes): 179 calls in `calls*.jsonl`; KOD's readiness audit
(`idxsig/llm_arm/audit.py`) counts 32 with complete BASE5 outcomes; one call disagrees with KOD (FROG, 2026-11-06);
LEARNER v2.2 (`paper/learner_v2.jsonl`) has a forecast sealed before the entry cutoff for all 179 sets; its published
values for `FADE10_5` and `BEATS_TWINS_5` differ from the register prior on 144 of them (its anchors follow live base
rates), so it is a distinct comparator.

## 1. Scored call

A call is scored when KOD's readiness audit classes it `complete_BASE5_outcomes`: valid, unique, linked to exactly one
sealed set, called inside the set's entry window, and the set has exactly one `BASE5` `RESOLVED` record whose cone holds
a boolean outcome for `RUN30_5`, `FADE10_5` and `BEATS_TWINS_5`. Calls on sets that are `UNRESOLVABLE`, not yet resolved,
or resolved without those three outcomes (a candidate that could not be bought) are counted and listed, not scored.

## 2. Brier scores

- Per statement: `(p - outcome)^2`, outcome 1 or 0.
- Per call: the mean over the three statements.
- The LLM's `p` is the call's `p`.
- The prior is the set's sealed cone prior (`paper/speculations.jsonl`), not the copy in the call.
- LEARNER is the `published` value of the same statement id in the last `LEARNER2_FORECAST` record for the set whose
  `made_at` is before the set's `entry_cutoff` (LEARNER v2.2, sealed). LEARNER v2.4 (`paper/learner_v3.jsonl`) is not
  used: it does not forecast these three statement ids. A set without such a record is left out of the LEARNER
  comparison only, and counted.

## 3. "Beats (paired, one-sided 95%)"

For each comparator, `d_i = Brier_LLM,i - Brier_comparator,i` over the scored calls. The LLM beats the comparator when
the mean of `d` is below 0 and a one-sided paired t-test of mean(d) < 0 has p <= 0.05 (Student t, n - 1 degrees of
freedom). Reported beside it and not part of the gate: a bootstrap that resamples whole signal sessions (10,000
resamples, seed 20261113), because calls on one session share one market day; a result where the two disagree is
reported as not robust.

## 4. "BACK beats AVOID net of costs"

The register's own BASE5 `candidate.trade.net_return` (costs included) for sets whose candidate was `TRADED`: the mean
over BACK calls must exceed the mean over AVOID calls. As written this is a point comparison; the number of calls in
each group is always reported, and with fewer than 5 traded BACK calls the comparison is reported as uninformative even
when it holds. ABSTAIN is reported separately.

## 5. The first look

The look is taken on the first night after which at least 60 calls are scored, on every call scored at that moment (no
truncation to exactly 60, which would need an arbitrary order among calls of one session). Any figure before that is an
interim view: it is reported, it decides nothing, and it does not change this rule.

## 6. Reported beside the gate

- The disagreement sample (`agrees_with_kod` false as recorded at call time), with the same statistics.
- Per-statement Brier scores and the mean BASE5 net return by call label.
- For US sets, the same returns split by the KOD paper book's plan (`paper/paper_book.jsonl`: `BUY_OK` or `DONT_BUY`),
  to show whether the LLM's labels sort outcomes beyond what KOD's own rule already does. Descriptive only.
