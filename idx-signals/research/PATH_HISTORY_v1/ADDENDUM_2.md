# PATH_HISTORY_v1, addendum 2: no credit for knowing which market moves more

Written 2026-10-29, before any outcome was computed: `results/events.csv.gz` does not exist yet.

1. **AUC within each market.** `protocol.json` reads a pooled AUC across the three markets. A pooled AUC credits a
   model for ranking one market's stocks above another's whenever their base rates differ, and the market intercept
   alone would earn that credit. It is the base-rate credit the owner ruled out. Every "pooled" AUC in the study is
   therefore the stratified AUC: computed only over pairs of a positive and a negative from the same market, which
   equals the per-market AUCs weighted by their numbers of pairs. The decision rule, its bootstrap and the paired
   block increments use it. The Brier gain over the anchor stays as frozen: the anchor is already each market's
   base rate.
2. **Previous session.** The build records each event's previous session date, which the news window of addendum 1
   needs.
3. **One trial.** `research/QUANT_GRADE/trials/PATH_HISTORY_v1.json` (the PENDING registration) and the result file
   written with the result are one trial. Count it once.
