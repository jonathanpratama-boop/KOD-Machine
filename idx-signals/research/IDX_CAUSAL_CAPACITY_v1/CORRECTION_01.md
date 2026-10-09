# IDX_CAUSAL_CAPACITY_v1: correction 01

This appends corrections to `RESULTS.md`, which is frozen and stays as it was. The numbers here
are measured by `research/EXEC_US_v2/fill_c_feasibility.py`, and the measurements are in
`research/EXEC_US_v2/fill_c_feasibility.json`.

## 1. FILL-C-v1 does include the signal session's volume

`RESULTS.md` says, under Limits, that "A 20-session median ignores the signal day's own surge in
volume". That is wrong. FILL-C-v1's window is the 20 sessions up to **and including** the signal
session (`close_capacity` uses `[s − 19, s]`), so the signal day is in it. The correct statement
is that the signal day's surge is one of 20 values in a median, so it barely moves the median.
For limit-up names, capacity therefore stays near the quieter preceding sessions. A rule
weighting the signal day more heavily would be a different model, and none was run.

## 2. FILL-C-v1 sizes causally but does not establish that the fill was feasible

Hermes reproduced the problem. FILL-C-v1 checks the planned size against capacity known at the
decision, and never checks the entry session itself. A synthetic order for 10,000 shares is
scored `EXITED` on an entry session that traded 1,000 shares in total.
`tests/test_contract.py::Liquidity::test_legacy_fill_c_still_reproduces_hermes_case` keeps that
behaviour on record. FILL-C-v1 is not changed, so its recorded run still reproduces.

Measured on the recorded rerun `20261009T050040Z`, 251 scored rule trades:

| | Count |
|---|---:|
| Shares above the entry session's entire volume | 0 |
| Shares above 10% of the entry session's volume | 4 (the largest took 31.3% of the session) |
| Median share of the entry session | 0.08% |

Removing those 4 trades moves the average net return from −3.64% to −3.57%. That is a
descriptive bound, not a rerun: a feasible model would also change the overlap rule and the
baselines. The conclusion of `RESULTS.md` does not change. The rule loses money and fails every
approval condition. As a check of the measurement, the fill model A evidence run has no scored
trade above 10% of its entry session, which is how A is defined.

Whole-session volume is itself only an upper bound for a closing-auction fill. Neither A nor C
observes the auction's volume.

## 3. Status of the recommendation

`RESULTS.md` recommended `--fill-model C` for new IDX research. That recommendation is
withdrawn. C plans causally but can score infeasible fills. New work goes through a contract
that separates the planned order from its realised fill. For US this is EXEC-US-v2
(`research/EXEC_US_v2/CONTRACT.md`). No IDX equivalent exists, and the old IDX strategy is not
being pursued further.
