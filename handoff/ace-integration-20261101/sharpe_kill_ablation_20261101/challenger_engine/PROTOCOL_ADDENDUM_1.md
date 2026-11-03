# Pre-outcome scope refinement1 (2026-11-01)

No raw historical rows opened or account returns computed. This explicitly
supersedes protocol v1's whole-history/no-reset reporting and three-policy count.
Parent requests two independent predeclared research accounts, not a continuously
pooled account. Each policy/partition starts fresh10000, with no reset after kill
WITHIN that partition. These starts are separate experiments, not a claimed real
account recapitalization or proof that a killed live strategy may resume.

Development: decision start2017-09-26 00:01, baseline opening2017-09-26, terminal
2023-01-01 opening. Data begin2017-08-17, so40 strictly earlier closes are unavailable
at the original study's Aug17 boundary; Aug17–Sep25 are warm-up only, not scored.
Validation: baseline2023-01-01 opening, first decision2023-01-01 00:01, terminal
2026-09-30 opening, using earlier2022 bars only for warm-up. These labels identify
previously reused data, not new untouched validation. No outcome-based date choice.
Each terminal flat-target decision is preplanned one day before its terminal open
at00:01. No final close/volume or later opening influences that partition.

Run four fixed policy labels per partition: TREND_V2_SHARED,
PASSIVE_50_50_RISK_MATCHED, CONVENTIONAL_50_50_BUY_HOLD_NO_KILL, CASH. Conventional
buy-and-hold uses the same initial/terminal timing, cash/fill/cost/capacity accounting,
but deliberately disables risk kills. It is descriptive context with a different
risk policy, never a reason to choose a different strategy after results.

Capacity is FROZEN ON EACH INTENT from a completed base-volume observation already
assumed available at intent creation. At midnightT, latest eligible volume isT-2;
at decision00:01T, volumeT-1 is eligible. Kill intents at midnight therefore useT-2,
not a volume published only later that minute. Partial residual kill orders receive
a new capacity only when a new later intent is legitimately created. This synthetic
capacity is not observed book liquidity. Never use future day's realized volume.

Preserve exact v2 rebalance sizing semantics: BUY budget (desired minus current
marked value) is fixed at decision; available shared cash is reserved/reallocated
as in v2 and affordable quantity is recomputed at the eligible future modeled fill
price. SELL quantity is fixed at decision and capped by actual holdings/capacity.
Do NOT recompute portfolio target weights/quantities at the future opening.
