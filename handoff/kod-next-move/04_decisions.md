# Decisions made vs questions still open

## Decided (by whom, when)

| Decision | By | Evidence |
|---|---|---|
| Phase 1 is read-only; no repo file changed, no harness run, no network pull beyond ≤6 FMP probes | this session, workflow prompt | `workflow/kod-next-move.js` RULES block |
| PR #3's paper policy is renamed **PAPER-POLICY-v5** in the local merge; base keeps PR #6's v4 | this session (proposed, not pushed) | `02_session_log.md`, `bundles/pr3-merge-resolution.patch` |
| v5 refuses to decide IDX while a validated E3 pair exists (raises), rather than choosing how a no-chase plan meets the 5% rule | this session (proposed) | `tests/test_policy_versions.py` in the merge |
| Daily paper routines continue unchanged under base-branch PAPER-POLICY-v4; no entry has ever been approved | standing | ledger at `e635e22` |
| Top-3 for adversarial refutation = #4 skeptic, #1 new-family, #2 structure (judge mean ≥ 43) | workflow (deterministic from judge scores) | `outputs/ranking.json` |
| The G3 collector investigation (Hermes steps 1–3) is blocked on the owner running `scripts/g3_provenance_audit.sh` on the Mac or pushing G3 to a branch | this session | G3 code exists in no branch of this repo |

## Open — owner's call (do not decide for the owner)

1. **Merge PR #7 (E4)?** Green, mergeable. If yes, it lands before any E5 work that clones `e4.py` / needs the US-crypto holdout guard.
2. **Push the PR #3 merge (`0ce21f0`, v5 naming)?** Needs the owner's permission to push to `claude/us-pipeline-v1`; Ace must re-review the merge result. If PR #7 merges first, this merge must be redone onto the new base (expect conflicts again in `execution.py`/`cli.py`).
3. **Accept the v5 name and the `e3_rule` refusal semantics?** Alternative: fold the US 5% rule into base v4 as a v5 that also carries the E3 rule.
4. **Push `claude/us-breakout-v1`?** Local only; the bundle preserves it.
5. **Which Phase-2 experiment to run** — pending the synthesis; the judges favour #4 (ceiling/kill test) then #1 (pre-spike family); Judge 2 wants #3 (KOD feed) as a parallel infrastructure track. The owner said "execute now", which authorises implementation on a new branch but not a push of that branch or a PR without asking.
6. **Reuse of 2023 as validation** for a new family: every proposal declares 2023 as once-seen; the owner should confirm this is acceptable (the alternative is prospective-only validation, which takes months).

## Open — technical, to be settled before a freeze

- Fixes demanded by the #4 refuters (see `03_proposals_and_evidence.md`, items 1–8) — the synthesis is expected to incorporate them; verify it did.
- Whether `panel-20261013T194245Z` (IDX, pinned by E3) must be rebuilt from the mirror manifest (network) or the on-disk `panel-20261007T225823Z` fallback is acceptable for a new protocol.
- Whether `kod-machine/var/kod.db` (committed) can carry any daily feed at all, or a separate store is needed (Judge 3 and the kod reader both flag growth of 3–4 MB/day).
