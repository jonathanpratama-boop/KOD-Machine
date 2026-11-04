# Candidate research workflow

The runtime retains every detection in its queue. The analyst adds a versioned
assessment to that exact candidate ID. This changes the research view; it never
submits an order or grants entry permission. The shared paper trend account uses
its own frozen policy and does not consume analyst assessments as buy signals.

Run commands from `idx-signals` using the runtime environment described in
`RUNTIME.md`:

```bash
python -m idxsig.runtime --root ../runtime/kod status
python -m idxsig.runtime --root ../runtime/kod assess --assessment assessment.json
python -m idxsig.runtime --root ../runtime/kod verify
```

Use a candidate ID shown by `/candidates`, `/candidate/{id}` or the current
`snapshot.json`. The assessment cutoff must be on or after that detection and no
later than the completed runtime cutoff. Collect/run a new explicit cycle before
adding newer evidence. `recorded_at` is the actual local recording time; entering
an earlier information cutoff does not establish a prospective forecast.

An illustrative **synthetic-only** assessment shape follows. Replace IDs, times
and declarations with the actual retained evidence before using it for research.

```json
{
  "candidate_id": "COPY_THE_RETAINED_CANDIDATE_ID",
  "state": "RESEARCHED",
  "as_of": "2026-11-02T00:00:20Z",
  "owner": "analyst",
  "reason": "Review whether peer participation explains the observed rise",
  "mechanism": "Group repricing hypothesis; causality remains unestablished",
  "counterarguments": ["The same broad-market move could explain both assets"],
  "evidence": [{
    "id": "demo:source-1",
    "source": "synthetic://retained-fixture",
    "available_at": "2026-11-02T00:00:10Z",
    "observed_at": "2026-11-02T00:00:10Z",
    "statement": "Synthetic peers rose in the same observation window"
  }],
  "blockers": ["No validated selective-repricing entry policy"],
  "clearing_evidence": ["A frozen prospective study with executable net returns"],
  "expires_at": "2026-11-03T00:00:00Z",
  "recheck_at": "2026-11-02T12:00:00Z",
  "plan": null,
  "change_kind": "CHANGED_INFERENCE",
  "supersedes": null
}
```

Evidence requires an ID, a source reference, availability time, observation time
and statement. Availability cannot follow observation, and observation cannot
follow the assessment cutoff. These are **analyst declarations**. The workflow
checks structure and chronology; it does not fetch the source or certify its
truth. Dataset validation and source verification remain separate work.

| State | Meaning and enforced boundary |
|---|---|
| `DETECTED` | Retained observation; mechanism can remain unknown. |
| `RESEARCHED` | Evidence, competing explanation and exact expiry recorded. Essential unknowns remain blockers. |
| `CONDITIONAL_READY` | Analyst declares all essential prerequisites and a complete bounded plan; only a named future result, quote or trigger remains. Entry permission stays false. |
| `ENTRY_ELIGIBLE` | Refused: this runtime has no approved selective-repricing entry policy. |
| `REJECTED` | Reason retained. Reopening requires changed evidence and an explicit revision; another opinion alone is insufficient. |
| `EXPIRED` | Exact deadline has passed. The original episode cannot be reopened; a new detection belongs to a new candidate. |

To revise, copy the most recent assessment ID into `supersedes`. The revision
receives a new ID and monotonically increasing version. Its cutoff cannot move
backwards. `change_kind` must be `NEW_EVENT`, `PRICE_OR_CONDITION_CHANGE`,
`CORRECTED_INPUT`, `NEWLY_FOUND_OLD_INFORMATION` or `CHANGED_INFERENCE`.
An identical request is idempotent: retries return the first record without
another journal append.

Conditional readiness follows `RESEARCHED`. It requires no essential blockers,
a known mechanism, and a `plan` containing:

- `side: "LONG"`; `entry_lower`, `entry_upper`, `protective_price`, `loss_budget`,
  `ordinary_loss`, `stress_loss`, `gap_loss`, `round_trip_cost_fraction` as finite
  nonnegative numbers or decimal strings. Structural protection must be below
  the lower entry bound and within 5% of the upper entry bound. A positive loss
  budget must cover declared ordinary loss. Stress and gap loss cannot be lower
  than ordinary loss. Costs are a separate declared assumption, not a guarantee.
- Nonempty `trigger`, `invalidation`, `protection_basis`, `target_action`,
  `cancellation` and `horizon` descriptions.
- `essential_evidence`: a mapping from each of `identity`, `broker_product_access`,
  `risk_budget`, `economics`, `structural_protection`, `depth_spread_costs`,
  `broker_orders`, `monitoring`, `cash_alternatives` to a retained evidence ID
  listed in the assessment.
- `pending_conditions`: one or more objects with a `kind` of `FUTURE_RESULT`,
  `QUOTE` or `TRIGGER` and a named `condition`.

These checks establish a complete declaration, not a verified trading edge,
real brokerage protection, current holdings or permission to act. A five-percent
planned price distance is not a hard loss cap; costs and gaps may exceed it.

`candidate_assessments.jsonl` is append-only, sequenced and hash chained. The
current dashboard is deterministically projected from the immutable cycle and
verified assessments. Original detection data remains under `detector_record`;
earlier assessments remain in the journal. At expiry, the displayed state becomes
`EXPIRED` with an explicit `expiry_projection`; the original assessment is not
rewritten. A torn or altered journal fails closed. Restore a verified backup
rather than editing or truncating it.

An interrupted runtime cycle blocks new assessments until that cycle is resumed.
The workstation shows a failed latest attempt above the last verified snapshot,
including a warning if account commands may have partially completed. Loading a
page never executes the cycle or mutates the account.
