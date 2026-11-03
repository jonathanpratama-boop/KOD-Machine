# Narrow prior-art/prose addendum

Inspected at pinned HEAD `48d18b8ecae67bdeeb07a47f1772903a5381782b`. Code/docs only; no new dataset reads, experiments or remote changes.

## Existing error-rate abstention was overlooked

The [new verdict, lines 116–119](https://github.com/jonathanpratama-boop/KOD-Machine/blob/48d18b8ecae67bdeeb07a47f1772903a5381782b/handoff/fresh-eyes-2026-11-01/FRESH_EYES_VERDICT.md#L116-L119) calls error-rate abstention unimplemented and cites PLAN_v2 rank 2. That plan proposed Learn then Test, which now exists:

- [`risk_control.py`](https://github.com/jonathanpratama-boop/KOD-Machine/blob/48d18b8ecae67bdeeb07a47f1772903a5381782b/idx-signals/idxsig/risk_control.py#L1-L65) implements exact-binomial wrong-call p-values and fixed-sequence threshold testing, stopping at the first failure and returning a certified threshold or None.
- [`call_cert.py`](https://github.com/jonathanpratama-boop/KOD-Machine/blob/48d18b8ecae67bdeeb07a47f1772903a5381782b/idx-signals/idxsig/call_cert.py#L104-L161) calls that implementation, recalibrates using previously resolved outcomes and makes no call if no threshold certifies. It sets wrong-call alpha=0.5 and delta=0.05, not a dollar-loss limit.
- An [October 29 study report](https://github.com/jonathanpratama-boop/KOD-Machine/blob/48d18b8ecae67bdeeb07a47f1772903a5381782b/idx-signals/research/CALL_CERT_v1/REPORT.md) and [October 30 shadow report](https://github.com/jonathanpratama-boop/KOD-Machine/blob/48d18b8ecae67bdeeb07a47f1772903a5381782b/idx-signals/paper/CALL_CERT.md) document the implemented workflow.

**Important distinction:** LTT wrong-call certification is not automatically the separately named general conformal risk control method, an adaptive conformal guarantee, a capital-preservation allocator, or a net-dollar-return guarantee. The code explicitly assumes calibration/future comparability; the study/report admit clustered events undermine the independent-binomial assumption. Existence of code and a historical check does not establish an unconditional live guarantee. Comparing a classification-error bound directly with trading cost also requires a payoff-aware risk definition and calibration, not just renaming the existing error metric.

Suggested correction: **“KOD already implements LTT-based wrong-call certification and abstention in a shadow report. Dependence-aware calibration and a separately specified, validated financial-risk policy remain open.”**

## Other scope corrections

- **All forty studies were the same +30%/1–5-session question:** contradicted by the existing 60-session US_INSIDER_BUY and SLOW_10K protocols, detailed in the main audit.
- **Venue constraints exclude every documented edge:** not supported by this finite review; the report's own ETH SMA eToro-cost aggregates contradict the specific cost-exclusion example. Separate venue limitations by mechanism instead of asserting universal impossibility.
- **“Capital preservation is solved by construction”:** the [risk controls listed](https://github.com/jonathanpratama-boop/KOD-Machine/blob/48d18b8ecae67bdeeb07a47f1772903a5381782b/handoff/fresh-eyes-2026-11-01/FRESH_EYES_VERDICT.md#L126-L132) are proposed mitigations, not a guarantee; the paper-account audit additionally finds key controls unimplemented. Use “risk-limiting design to implement and test.”
- **“No published system/study worldwide”:** [lines 111–115](https://github.com/jonathanpratama-boop/KOD-Machine/blob/48d18b8ecae67bdeeb07a47f1772903a5381782b/handoff/fresh-eyes-2026-11-01/FRESH_EYES_VERDICT.md#L111-L115) exceed the demonstrated search scope. Use “not identified in this review,” with search scope/date. This audit did not perform a new worldwide literature search.
