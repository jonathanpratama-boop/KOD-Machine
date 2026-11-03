# KOD engineering checkpoint: reviewed v1.4 LOCAL, NOT ACTIVATED

2026-10-31. Not pushed, merged, deployed or activated. No real-money orders,
production ledger edits, profit claims or strategy training.

## Preferred candidate and provenance

See kod-integration-v1.4/README.md. The consolidated patch is based on exact
upstream 7aad4311eb89f713107c96659c2000034bfa9c10 of
jonathanpratama-boop/KOD-Machine, not on synthetic local Git history.
Apply EITHER its consolidated patch OR the five ordered patches, never both.
The source-only integration snapshot contains 140 files, not a complete clone.
All 18 affected final files match the reviewed candidate; 120 unaffected baseline
files retain upstream hashes. Original protocol history is preserved.

Initial repair snapshot source: 41b8eb398b900da4cf251efe3971e31dae044ec9;
rechecked intermediate upstream: 5eae447c1c16dcff3daf02da6bd6ee836069eaae.
Synthetic baseline 248b5d2f49985618dfdd8485c7816da3962f9e7a and local commits:
f2062b56d28cc42ba11133be3475a15ba7115c58 (v1.2),
a455362e7723121c3a7e9095afc6c9f88204424a (feasibility),
319012922c2d0f23e91398f8d01c0cafe7288a7e (filter evidence),
99ee3ab6c175241313810bfd57b0e1c4ddb82a3f (v1.3),
b40e0e6bb6e106d2d8871f86f8eaf2b4f7d567f5 (v1.4).
THIS SELECTED-SOURCE SYNTHETIC GIT HISTORY MUST NEVER BE PUSHED.

Prior patches and checkpoint-version-1 source/README/checksums remain under
patches/ and history/. Historical README statements apply only to that version;
this README and final integration manifests describe the latest candidate.

## Scope and evidence

v1.2 blocks new reservations after failed current quote fetch despite recent cache.
The isolated Decimal LIMIT/IOC feasibility estimator validates declared observed
filter/book inputs, explicit fees, partial displayed-depth fills and missing
required evidence. It has no authenticated or live order path.
v1.3 rejects malformed/nonfinite/nonpositive/crossed quotes at parser and injected
getter boundaries, without poisoning the quote ledger or unrelated symbols.
v1.4 adds expected-head CAS/recompute for state-derived cycle phases, a narrow
as-of valuation guard and positive-finite non-Boolean policy-price validation.
Committed receipt-pending events are not replayed. Frozen shared US engines and
predecessor protocols remain unchanged; correction notes identify limitations.

Independent focused review: 100 selected offline tests plus controlled stale
interleavings and actual multiprocess races preserve three-order/150-risk caps,
hash integrity and nonnegative free cash. Review phrase 'all 100 repository tests'
means that bounded selection, NOT the entire upstream suite.
Integration: 331 unique selected tests passed, including all 267 baseline IDs and
64 additions, with one explicit real-registry exclusion and 72 upstream test files
outside selection. A fresh extraction of the consolidated archive was hash-checked
against its 140-file manifest and reran those 331 tests successfully with socket
audit denial and sanitized environment. See fresh-extraction-verification/.
No full-suite, remote CI or production validation claim.

## Important limits

CAS retries stop after three conflicts: fail-closed exhaustion is possible under
contention; this is safety evidence, not guaranteed progress. All writers must
honor the callback contract. Whole-ledger reporting remains latest-known, not a
historical replay engine; future business events fail closed. The existing verifier
is not a complete retrospective risk audit for externally injected bad orders.

Public filter eligibility remains BLOCKED: documented reference-price fallback
returned HTTP 451 restricted location. No bypass, alternate-host workaround or
further reference access; absence of reference override was NOT established.
No real-market eligibility or fill success is claimed. Public observations and
feasibility estimates do not guarantee exchange acceptance or persistent liquidity.

The separate scheduled book collector terminated on runtime network policy after
4 attempts: 3 successes, 1 failure, 176 missing observations. The intended two-hour
observation did NOT complete and was not resumed. Original source/protocol, raw
public snapshots/error, stale status, reconciliation and read-only status-reader
amendment are preserved. Reader distinguishes BLOCKED from unexplained UNKNOWN/
STALE instead of presenting a dead collector as RUNNING. Its 19 offline tests passed.

CHECKSUMS.json covers all payload files except itself. Only selected engineering,
review and sanitized public evidence included; no .git, credentials, unrelated
tasks, private account records, research datasets or caches. Earlier Library
versions remain preserved under the same item identity.
