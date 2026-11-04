# Concurrent KOD work

Each workstream owns one named branch and a declared set of live-code files.
Inspect the current remote head before publishing; never force-push or overwrite
another agent's branch. Frozen experiments, timestamp tokens and historical
records retain their original IDs, paths, bytes and clocks. Corrections are new
records. An alias does not rename historical evidence.

For this pass, `astra/timing-integration-20261104` owns new timing integration,
targeted causal-data fixes, integrity tooling, compatibility adapters and its
handoff documents. Existing Claude and Hermes studies remain owned by their
branches. Branch-only results are explicitly marked unavailable to default-branch
readers until a separately authorized integration is completed.

Local work is not evidence of publication. Publish an authorized work branch
with the source/protocol/evidence hashes and report the exact commit. No daemon,
local/cloud synchronization or new schedule is installed by this convention.
Do not assert access to a different agent's computer or silently upload its data.

## Architect (from 2026-11-04)

The owner's instruction of 2026-11-04 ("Do everything", on `handoff/KOD_FIX_PLAN.md`) adopts the house rules in
`handoff/KOD_RULES.md` and the proposed architect: **Astra**. The architect owns `handoff/astra/SYSTEM_MAP.md`,
approves and performs every code merge into the default branch with a merge note (`handoff/merges/`), and enforces
the rules. Other agents propose on their own branches. The daily paper bots keep pushing their own log paths directly.
The owner can name a different architect at any time by adding a dated decision record in `handoff/decisions/`.
Record: `handoff/decisions/2026-11-04_rules_and_architect.md`.
