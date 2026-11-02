# LLM_ARM_v1 — forward-only test of an LLM reasoning layer (frozen 2026-11-02, before the first call is scored)

**Question.** Does an LLM call (Claude, reading only public context available at the call time) add information beyond
KOD's numeric models about which flagged spikes will run or fade?

**Why forward-only.** The model's training data ends before these events, so a call on a live event cannot know the
outcome. Historical backtests of the LLM layer are contaminated and are not allowed.

**Unit.** Each live KOD candidate that already has a sealed speculation set (`paper/speculations.jsonl`), called before
its entry cutoff (the set's own s+1 window). The call is written to `calls.jsonl`, committed and RFC 3161 timestamped
before the market opens on s+1.

**Call fields.** `call` = BACK / AVOID / ABSTAIN; probabilities for the set's own statements (RUN30_5: a close in
s+1..s+5 >= 1.30x the signal close; FADE10_5: the frozen plan's net return <= -10%; BEATS_TWINS_5); reasons; sources
consulted; whether it agrees with KOD's numeric decision.

**Scoring (fixed now).** Each call is scored on the speculation register's own resolutions of the same set: Brier score
of the LLM's probabilities against the register's prior and against LEARNER's forecast for the same statements, and the
paired 5-day outcome of BACK vs AVOID calls. Calls that merely agree with KOD carry little information; the informative
sample is where the LLM disagrees, and it is reported separately.

**Look.** First look at 60 scored calls; the LLM layer is kept only if its Brier score beats both the prior and LEARNER
(paired, one-sided 95%) and BACK beats AVOID net of costs. Reported whether positive or negative. Paper only.
