# Timing pass: compatibility-preserving tidy

Status: mechanical cleanup completed and equivalence checks passed. The maintained
scope is 62 Python files: 52 reformatted and 10 already formatted. Eleven
byte-pinned source/configuration files remained unchanged.

## Scope and preservation

The baseline is commit `c2e9c54ba85c591c2ed5628295159335667a1b84`, tree
`275056dbd51cac951b3c26cb413c9106c2cf2819`, with 5,269 blob entries. The local checkout
reconstructs that exact signed commit and all original tree objects. Original downloaded
files were checked against their Git blob IDs. Missing archival payloads remain sparse
tree references; they have not been replaced by empty files or reconstructed content.

`tools/live_code_style.json` is an exact allow-list of maintained first-party files.
`ruff.toml` supplies the only formatter/linter policy, pinned to Ruff 0.14.3. Frozen
research, historical handoffs, vendor code and byte-pinned implementations are excluded.
The formatter wrapper rejects path escapes, symlinks, missing paths and any pinned file
that enters the managed list.

An important compatibility finding: `idxsig.runtime.account.bundle_pins()` includes the
bytes of `runtime/account.py` itself, and journal replay checks those pins. Formatting
that file would invalidate prior journals even if its Python behavior were unchanged.
It is therefore preserved byte-for-byte, together with its vendored dependencies and
the pinned pre-move, stock-account and crypto-account implementations. The style
manifest records their SHA-256 values and checks them before and after formatting.

No existing module, function, experiment, detector, profile or historical path has been
renamed in this pass. The new ID registry is a future compatibility mechanism; it does
not relabel historical records or invent migration entries.

## Mechanical-only proof procedure

1. Commit logic, regression tests and this style tooling before formatting.
2. Run `python tools/check_tidy_equivalence.py --output <new-before.json>`.
3. Run `python tools/check_live_style.py --format` in a separate mechanical change.
4. Run `python tools/check_tidy_equivalence.py --baseline <before.json> --output <new-after.json>`.
5. Require identical Python abstract syntax trees for every managed file, identical
   fixed-clock synthetic snapshot bytes, unchanged preserved-source hashes, and successful
   replay of the original pre-tidy journal using the post-tidy code.
6. Run the release/integrity checks and commit the mechanical change separately.

The golden tool uses a fixed generated-at timestamp for the synthetic runtime snapshot.
Real elapsed-time observations and golden-report creation times remain real; they are
not part of the deterministic economic snapshot comparison. Both reports retain their
original runtime directories so old journals are actually read after formatting.

## Verification boundaries

Tree/blob identity establishes that archived files were preserved. It does not establish
that every RFC 3161 token has been cryptographically verified. Full token and signed-data
availability, unsupported formats, and exact verification counts belong in
`HISTORY_INTEGRITY.md` and the integrity reports. No unavailable payload is counted as a pass.

## Final results

The mechanical commit is
[`50ef4379243ca1edb8e729bb2ebdfe6826980700`](https://github.com/jonathanpratama-boop/KOD-Machine/commit/50ef4379243ca1edb8e729bb2ebdfe6826980700),
with tree `d24fef076aaa3750da9ceeed19646ee30cc8a1ae`. The separately committed
pre-tidy tree is `72c862e7f7f63df810f4c6277f6e15d27eff301d`.

| Check | Before / after result |
| --- | --- |
| Python abstract syntax trees | All 62 identical; zero differing fields |
| Fixed-input economic snapshot | Byte-for-byte identical |
| Snapshot SHA-256 | `1472e134bbc1e9c5538c0c1994cfa532734a64220eee203fd5c5eeb4dbf3c58b` on both sides |
| Pre-tidy journal read by post-tidy code | Passed |
| Byte-pinned implementations/configuration | All 11 unchanged |
| Formatter and linter | 62 files accepted; all checks passed |
| Original protected Git tree entries | All 4,080 unchanged; zero changes |
| Alias migration entries | Zero; original public names and paths retained |

Two docstring indentation changes were separated into an earlier documentation
commit because their literal strings change the Python syntax tree. A new test's
clock fixture was also cleaned up before the final equivalence boundary. Neither
change is concealed inside the mechanical-only comparison.

Local commits were published through the repository connector. Publication
recreated commit metadata, so local and published commit IDs differ; every
published file tree was checked against the corresponding local tree. The tree
identities and comparisons, not an assumed equality of commit IDs, bind the
tested files to the published branch.

No profitability claim follows from formatting equivalence, historical
preservation or successful software tests.
