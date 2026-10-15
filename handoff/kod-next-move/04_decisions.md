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

0. **After the E5 null (2026-10-14):** (a) DONE — `claude/e5-ceiling` pushed, draft PR #8 open (owner authorised 16:20 UTC; no merge); (b) authorise the SEC reachability probe (network) that the next protocol, information timing on EDGAR 8-K acceptance, is pre-registered to need; (c) confirm the pre-registered consequence stands: no tape-only detector building, no KOD tape feed.

1. **Merge PR #7 (E4)?** Green, mergeable. If yes, it lands before any E5 work that clones `e4.py` / needs the US-crypto holdout guard.
2. **Push the PR #3 merge (`0ce21f0`, v5 naming)?** Needs the owner's permission to push to `claude/us-pipeline-v1`; Ace must re-review the merge result. If PR #7 merges first, this merge must be redone onto the new base (expect conflicts again in `execution.py`/`cli.py`).
3. **Accept the v5 name and the `e3_rule` refusal semantics?** Alternative: fold the US 5% rule into base v4 as a v5 that also carries the E3 rule.
4. **Push `claude/us-breakout-v1`?** Local only; the bundle preserves it.
5. **Which Phase-2 experiment to run** — the synthesis recommends #4 E5-CEILING (amended). The session is proceeding with it on a local branch because the owner said "execute now"; the owner can still redirect. Not pushed, no PR, until authorised.
6. **Reuse of 2023 as validation** for a new family: every proposal declares 2023 as once-seen; the protocol labels any 2023 pass PROVISIONAL. The owner should confirm this is acceptable (the alternative is prospective-only validation, which takes months).
7. **Six owner decisions named by the synthesis (§6):** (a) merge PR #7; (b) authorise branch `claude/e5-ceiling` and its push; (c) accept that a 2023 pass is provisional and the holdout stays sealed; (d) authorise the IDX panel rebuild (no network — proceeding) and the SEC submissions probe (network — NOT proceeding without a go); (e) whether E6 (delayed-entry grid) runs in parallel (default: no); (f) confirm KPF-v1 waits for the A1 row (default: yes).

## Working assumption for Phase 2 (made by the session, reversible)

- PR #7 is **merged locally into the e5 worktree branch** (not on GitHub) so that `jump_ratio`, `GLOBAL_HOLDOUT`, `NEVER_ENTERED` and `e4.py` are available. If the owner declines PR #7, the E5 branch must drop that merge and port only the needed pieces.
- The E5 branch is local-only; nothing is pushed and no PR is opened until the owner authorises it.
- No network pulls (no SEC probe, no mirror clone); the IDX panel is rebuilt only from files on disk, else the pre-registered fallback panel is used.

## Open — technical, to be settled before a freeze

- Fixes demanded by the #4 refuters (see `03_proposals_and_evidence.md`, items 1–8) — the synthesis is expected to incorporate them; verify it did.
- Whether `panel-20261013T194245Z` (IDX, pinned by E3) must be rebuilt from the mirror manifest (network) or the on-disk `panel-20261007T225823Z` fallback is acceptable for a new protocol.
- Whether `kod-machine/var/kod.db` (committed) can carry any daily feed at all, or a separate store is needed (Judge 3 and the kod reader both flag growth of 3–4 MB/day).
