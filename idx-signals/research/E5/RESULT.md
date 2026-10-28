# E5-CEILING (KOD-GLOBAL-E5-v1) — result: NULL at the pre-registered gates

Historical research on assumed costs, daily-bar fills and a survivor-only US universe. 6 fits, 2 primaries,
nothing else searched. Nothing here is prospective performance; no probability or trade is asserted.

Protocol frozen in `e1e57af` (`FREEZE.md`); Stage 0 reproduced all three precondition runs (`06c2dda`);
discovery `5f51d92`. Per-market numbers are in `<MARKET>/discovery/{stage1,gates,summary}.json`.

| Market / arm | flags | names | E30 precision | lift vs matched | paired plan-window excess | cluster-bootstrap p | gate |
|---|---|---|---|---|---|---|---|
| IDX A (primary P1) | 968 | 345 | 0.212 | 3.92 | +0.0130 | 0.065 (α 0.025) | Stage 1 FAIL |
| IDX B (diagnostic) | 605 | 185 | 0.007 | 1.31 | +0.0040 | 0.011 | Stage 1 pass; Stage 2 FAIL (scored 9 < 200, net ≤ 0, paired net p 0.55) |
| US A (diagnostic) | 3939 | 1060 | 0.133 | 2.23 | −0.0228 | 0.996 | Stage 1 FAIL |
| US B (diagnostic) | 7717 | 1122 | 0.020 | 0.84 | −0.0189 | 0.996 | Stage 1 FAIL |
| CRYPTO A (diagnostic) | 676 | 232 | 0.179 | 1.30 | −0.0228 | 0.941 | Stage 1 FAIL |
| CRYPTO B (primary P2) | 505 | 201 | 0.149 | 0.96 | +0.0029 | 0.441 | Stage 1 FAIL |

KOD creep-quiet rows (A0, A1): lift vs matched 1.12 / 1.01 (IDX), 1.05 / 0.97 (US), 1.05 / 1.00 (CRYPTO);
the A1 lift CI never excludes 1 (a1_gate fails in every market).

Both primaries fail Stage 1, so the pre-registered consequence `consequences.stage_1_fails_in_both_primaries`
applies: daily-bar T-0 direction is not detectable by this learner over this feature list where it can be
measured; stop building tape-only detectors; the KOD tape feed is not stood up; the next protocol is
information timing (EDGAR 8-K acceptance) after the SEC reachability probe, which needs the owner's go.

Not run, and why: Stage 3 (`e5-freeze`) — no selected arm and the sidecar applies only to the
Stage-1-pass outcome, so the literals stay unset and no rule hash changes; Stage 4 (`e5-validation`) —
nothing admissible to validate. Observation, not a claim: IDX Arm A's detection lift (3.9) and positive
gross excess miss the gate only on the cluster-bootstrap p (0.065 vs 0.025); the gate is not relaxed.
