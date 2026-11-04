# Historical compatibility and timestamp integrity

Engineering review on 2026-11-04; base repository commit
`c2e9c54ba85c591c2ed5628295159335667a1b84`. No historical record, path,
experiment identifier, stored hash, certificate or timestamp token is renamed.

## Interfaces and ownership

| Organ / module | Input → output | Clock / invariant | Regression coverage |
| --- | --- | --- | --- |
| Immune system: `tools/check_append_only.py` | Git trees/index → violations | No clock inference; frozen files fixed, log prefixes exact | `tools/ci_tests/test_append_only_guard.py` |
| Memory: `kod.ids` | Name + information cutoff + alias map → original name | UTC effective time; original IDs never become aliases | `kod-machine/tests/test_ids.py` |
| Integrity census: `tools/check_history_integrity.py` | Original files, hash manifests, TSA tokens → verification and coverage report | Signature time distinct from local receipt; missing payloads explicit | `tools/ci_tests/test_history_integrity.py` |
| Nervous system: `idxsig.runtime.time_anchor` | Explicit prospective decision batch → immutable payload, independent tokens, attempt receipts | Monotonic request duration; authority's actual time retained on retry | `idx-signals/tests/test_time_anchor.py` |
| Linked evidence: `idxsig.runtime.timing_evidence` | Timing attempts and retained sidecars → required-object integrity and coverage | Membership owner, clock raw output, original capture and input/output contexts must reconcile | `idx-signals/tests/test_timing_evidence.py` |
| Existing cryptographic verifier: `kod.timestamp` | Original bytes + token + pinned trust chain → authority time | OpenSSL RFC3161 verification; no local-clock substitution | Existing `kod-machine/tests/test_timestamp.py`, plus invalid-token test above |

## Verified fixes

The old append-only guard read newline-separated Git status text. Git quotes an
unusual path such as a filename containing a newline, so that name could evade
its prefix match. It also converted a failed `git show` into empty bytes. The
guard now uses NUL-separated status records and fails on unreadable old blobs.
The complete `kod-machine/registry/` namespace is protected, with named
append-only logs still allowed to grow. `registry/ids/ID_MAP.jsonl` is also
append-only. No currently stored registry path was found outside the old named
prefixes; broader protection covers future record kinds.

Reproduction before the patch:
`python -m unittest discover -s tools/ci_tests -p 'test_append_only_guard.py' -v`
ran six tests with four failures (newline path, new registry kind, ID map rewrite,
failed blob read). The same six tests passed after the patch.

The alias registry is intentionally empty. `kod.ids.resolve(name, at=...)` is
available for a future alias at a reader's input boundary. Old names continue to
work unchanged, so no import shims or signed-record migrations are required.
Legacy unversioned alias rows are read as schema v1; new rows must use v1.
Aliases cannot be rebound, chained, made effective retroactively by a reader,
or used to read a path outside the repository. Eight compatibility tests passed.

## Coverage of before/after verification

The initial remote tree listed 4,080 protected files/logs. At the initial byte
snapshot, 423 original payloads were available locally. The first audit compared
all 423 successfully; the other 3,657 remain `UNAVAILABLE` for a *local byte*
comparison. Comparing original and resulting Git blob IDs is a separate
preservation proof and must not be described as cryptographic token verification.

That first audit found nine supported manifest claims verified, 239 unavailable
claims/manifests and one unsupported layout. All 2,133 enumerated timestamp
tokens were unavailable in the initial sparse checkout. The report status was
`PARTIAL`, with no detected mismatches. Hydrating more original bytes can increase
coverage; the tool never downloads data or reconstructs missing original tokens.

The final local audit, repeated after additional hash-verified fixture hydration,
remained `PARTIAL` with zero failures: 423 original protected payloads verified
and 3,657 unavailable against the initial byte snapshot; nine manifest claims
verified, 242 unavailable claims/manifests and three unsupported layouts; 2,133
timestamp tokens unavailable for local cryptographic verification. Newly
available manifest bytes exposed more individual claims, so these manifest
coverage counts need not match the first audit's container-level count. A file
unavailable in the original snapshot cannot acquire a retrospective before/after
byte verification merely by becoming available later.

`tools/check_history_integrity.py` reads supported JSON/JSONL manifest layouts,
recomputes original paper-record hashes before associating digest-named tokens,
uses original canonical KOD registry lines, and supports detached file tokens.
The existing domain verifiers still check ledger chains, card schemas, anchor
ancestry and trading-forecast chronology. A verified signature alone does not
establish that a forecast preceded its outcome or that a trade was feasible.
Ten audit tests passed, including missing data, unsupported layouts, changed
records, bad signatures, path traversal and exclusive report publication.

## Prospective timestamp integration

`anchor_batch(root, payload, enabled=False, stamper=None)` is inert by default.
An explicit prospective invocation stores the canonical original payload by its
SHA256 and keeps tokens and attempt receipts in separate files. Existing tokens
are never overwritten. A failed request retains the decision; a late retry keeps
the authority's later time. `verify_anchor` performs offline verification.

When `decision_at` and `outcome_window_start` are supplied, the result reports
the authority delay and whether the verified stamp preceded the outcome window.
Missing dependency, certificate, token or payload cannot become `VERIFIED`.
Eight anchor tests passed. One uses the real offline OpenSSL verifier to reject
an invalid token; fixture stampers test routing and retries. The final two-capture
regression mocks the timestamp authority and blocks network access. An earlier
run of that existing integration test used the timestamp-enabled default before
the mock was added, so external timestamp requests may have been attempted. The
available test output does not establish whether any authority was reached; no
claim of zero external timestamp requests is made for the whole engineering pass.
Market data in these regressions came from synthetic fixtures. No prospective
public-market collection or live order was performed by this test work.

The linked-evidence verifier separately prevents a valid timing-journal hash
from concealing deleted membership, clock or capture files. Generated IDs require
their exact retained objects; child source requests may share their recorded
parent's membership. Captures are checked through the intraday raw-evidence
verifier. Context outputs are rebuilt from their preserved input, including
source and cost declarations. `links.context_id` makes context deletion
detectable; old unlinked context files can be checked while present but have no
independent deletion proof. Legacy external universe IDs remain explicitly
unverified declarations. Twelve linked-evidence tests passed, including deleted
memberships, wrong owners, symlinks, nested raw-data tampering and changed cost
outputs. The combined anchor and linked-evidence suite passed twenty tests.

## Remaining limits

- Full historical cryptographic verification needs original token and payload
  bytes, including records intentionally outside the checkout and Git LFS data.
- Unknown manifest schemas stay `UNSUPPORTED`; add a documented adapter before
  using them as integrity evidence.
- Alias resolution does not assert record existence. Readers adopting a future
  alias must pass their actual historical cutoff; stored signed payloads remain
  unmodified.
- Timestamp-authority outage does not authorize backdating or synthetic receipt
  replacement. A decision with no timely verified stamp retains that limitation.
- Certificates may expire or authorities may change. Preserve original pins and
  add an explicitly versioned trust policy rather than replacing old certificate
  bytes. This pass does not change the existing RFC3161 trust policy.
