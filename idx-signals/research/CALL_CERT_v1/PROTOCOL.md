# CALL_CERT_v1: can the machine certify how often its calls are wrong?

Frozen 2026-10-29, before any prediction was computed. `protocol.json` is normative; `run.py` is the one run.

**Question.** LEARNER v2.4 forecasts, for a US stock that just closed +30%, whether it closes 10% lower the next session on
its own. Learn then Test (Angelopoulos et al., arXiv 2110.01052) picks a calling threshold on resolved events so that, with
95% confidence, the share of wrong calls among the calls made is at most a stated level. Fitted on 2020-2021, certified on
2022; refitted through 2022, checked on 2023.

**Two calls per statement.** DUMP (the stock will dump), certified right at least half the time. SAFE (it will not),
certified wrong at most half as often as the base rate. Both for the headline (next session) and the companion (5 sessions).

**Verdicts.** CANNOT CERTIFY; HOLDS (2023 losing rate at most the certified level); BROKEN (significantly above it, 0.05
over four); or ABOVE ALPHA, NOT SIGNIFICANT. A certificate that holds makes the method a candidate for a shadow report on
v2.4's live ledger; v2.4's frozen calls are not changed.
