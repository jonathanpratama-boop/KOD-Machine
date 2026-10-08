Hermes local candidate repair handoff v1
Base commit: 1420ee68ac1da2f063bfaf96a1bd374701f23a05

repo/ contains candidate source and tests, NOT a complete repository. Compare against the base and current Claude tree before merging; do not blindly overwrite newer changes. audit/ contains findings, protocol, limitations, missing-input inventory and execution evidence. No original market payloads are included.

Read audit/REPAIR_CHECKPOINT_v2.md first. Repair is partial, not production approved. New paper scoring path is opt-in; historical pipeline integration is incomplete. panel-global-v2 is not yet accepted by existing E1 admission. Original reproduce_source_findings.py targets legacy behavior and needs a separate version-aware adaptation. Preserve originals.

Recorded full suite: 130 tests passed. Re-run from idx-signals with its dependencies: python -m unittest discover -q. Tests are engineering evidence, not validation of historical returns. Exposure to post-2023 manifest QA examples is disclosed in the checkpoint. No holdout analysis is authorized.

MANIFEST.json hashes all delivered source/audit files. No GitHub push has been performed.
