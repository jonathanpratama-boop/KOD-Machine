# Architect decision: October 2026 IDX lower-limit correction

Date: 2026-11-09 UTC
Architect: Astra, acting through Codex in Jonathan's KOD review chat
PR: https://github.com/jonathanpratama-boop/KOD-Machine/pull/29
Reviewed implementation: 558fe7daa265f8189857db715bf61c462e143e0f
Reviewed base: 04927b3c4e87ff3fafb6172d8c0185210b7af3b4

## Decision

Approve the focused correction and merge before today's reported 10:17-10:20 UTC IDX routine. Do not pause the scan or the cloud experiment. This corrects the paper simulator's rule schedule; it does not approve a strategy or a real trade.

The current [IDX mechanism table](https://www.idx.id/en/products-services/trading-hours-and-mechanism/) was read again during this review: regular boards use 7% downside above Rp14 and Rp1 at Rp11-14. The [October 20 notice republished by BCA Sekuritas](https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-kembali-batas-bawah-auto-rejection-efek-bersifat-ekuitas) confirms the October 19 and 20 changes and the December 31 expiry. The decree bodies were not independently read. The PR's disclosed board and rounding limitations remain.

## Narrow exception for the pinned rules module

Approve only the reviewed change to `idx-signals/idxsig/market.py`:
- Before SHA-256: `e9e9328af46a871d6a8bc929ab10889f071bcdbef4be6d85f6fe1d26bd2f9cbc`.
- After SHA-256: `f1b35cb0f4e07fb9e57d0d47d8c5ae390da815b6b9265640eb55cda3014c036b`.

This is a dated addendum to the pin discussion in `handoff/claude/LINT_CLEANUP_20261104.md` and the corresponding `ruff.toml` comment. Those historical texts are not rewritten.

MSCI_DELETION_v1, MSCI_DELETION_OPT_v1 and MSCI_DELETION_OOT_v1 retain their original protocols, hashes and stored results. Their hash guards must continue to reject the updated checkout. Reproduction requires their pinned historical code and original inputs; this approval does not make reproduction impossible and does not authorize updating a frozen hash or bypassing its guard. Other already-stale pins are not repaired here. No exception is granted for `execution.py` or `paper.py`.

## January and existing scorer behavior

Accept the explicit UNCONFIRMED carry-forward and warning as an interim paper-model convention. It is not evidence that 7% applies in 2027, and any outcome using it is conditional on that assumption. Verify the exchange's effective rule before relying on 2027 IDX results. Do not add a raising guard to the shared limit function: it is also called by US and crypto processing.

Leave the legacy scorer's locked-horizon behavior in place for this correction. Its missing outcomes can bias reported averages; the 37 surviving corrected trades must not be compared with the original 40 as a clean performance improvement or deterioration. Any future repair requires its own explicit scorer version and preserved originals.

## Verification and evidence boundaries

- GitHub checks on the reviewed head: integrity, code-tests, workstation and aggregate checks passed.
- Independently ran all five market test modules on Python 3.12.15, NumPy 2.3.5 and pandas 2.2.3: 197 tests passed.
- Two additional read-only reviewers found no blocking code or impact-bookkeeping defect.
- Independently recounted the committed impact tables: 11 shifted exits plus 3 unscorable outcomes out of 93 ledger outcomes; 9 of 14 catalyst resolutions; 1 of 23 speculation resolutions.
- Compared base/head Git trees: all 5,270 blobs under paper records, research and the KOD registry, plus execution.py and paper.py, are unchanged.
- No fresh replay from raw prices was performed in this architect review. The Nov 6 payloads are not committed; harnesses refer to the builder's scratch paths. Their preservation outside scratch remains an evidence-storage follow-up.
- The 14 ledger differences depend on the existing close-at-limit lock convention and absent board membership. The final-bar replay also has separately disclosed differences from the original scoring pulls.

## Operational boundary

The revised default branch is the code handoff. The next IDX routine must fetch that branch before scoring and retain its usual scan. The schedule is reported in the repository and builder's handoff; its account scheduler is not directly accessible in this review. Do not claim the upcoming run executed until its ledger/commit receipt exists.

Historical ledger/register rows are not rescored or replaced by this approval. The committed correction report remains beside them. Automatic exchange-rule drift alerts are not present; a warning in a job log is not owner-delivery verification.
