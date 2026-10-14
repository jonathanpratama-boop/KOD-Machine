# E4 v2: the fade under a realistic short model, with one regime condition (KOD-GLOBAL-E4-v2)

Frozen before any v2 number; machine-readable in `protocol.json`; every field not restated
here is v1's (`../PROTOCOL.md`). **Designed from v1's discovery table** (`../REPORT.md`): a
second design on discovery data, declared as such. Validation (2023) was not read and remains
the single test; the holdout is sealed in code.

**What v1 showed.** Two trades in three win, the median gain is 6-9%, every plan lost money in
2021 and nearly every plan made money in 2022, and the worst 1% of trades lost more than the
whole position, partly through a redenomination (COCOS 2021-01-16, 1000:1) that is not a trade
and partly through real squeezes that no close-based exit prevents.

**What changes.**

1. *Short model.* Liquidation at +100% on the session high (an isolated-margin perpetual at 1x:
   the loss is the sold notional plus fees and carry, and intraday spikes liquidate). A session
   whose close/reference ratio is beyond 10x inside the trade is a redenomination or a bad print;
   the trade is `EXCLUDED_DATA_JUMP`, for the rule and the baselines alike.
2. *Regime.* The four v1 detectors are joined by `_BEAR` variants: the same flag only when BTC's
   close is below its 50-session mean at the signal close. One pre-specified proxy, the most
   ordinary one, no threshold search.
3. *Tail criterion.* v1's 1st-percentile rule cannot be met under liquidation (one liquidation in
   a hundred trades puts it at -100%). v2 bounds the tail by the 5th percentile (>= -50%) and the
   liquidated share (<= 2%).

**Unchanged.** Markets (crypto first on the same panel; v1's precondition stands), costs and
carry, the 36 plans (8 detectors: 288 runs), the harness, the periods, the per-year rule, the
hit-rate rule (>= 50%), scored >= 200, p < 0.05 against matched random shorts, the selection
rule, one validation run (scored >= 100, same criteria), the consequences.

**Claims.** Historical research. A pass is one year under assumed costs, carry, liquidation and
daily-bar fills, after a second design pass on discovery. Nothing here is prospective
performance, entry permission, or a promise of reliability.
