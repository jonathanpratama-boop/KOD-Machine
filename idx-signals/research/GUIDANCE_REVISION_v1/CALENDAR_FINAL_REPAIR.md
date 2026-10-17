# Final calendar compatibility repair

The first calendar-range repair did not resolve CI: GitHub installed pandas 3, while the calendar4.5.6 implementation and passing local environment use pandas2 date-resolution behavior. Core requirements now constrain pandas to >=2,<3. Explicit source-to-exit date bounds remain. Their trading sessions are used directly, avoiding a second bounds check that rejects weekend/holiday endpoints. A regression test covers a weekend start and end.

The original protocol, source inputs, seven cash decisions and historical AMD fixture remain unchanged. No market outcome was rerun. Earlier code repair notes are retained.

**Current verification command:**

```sh
python3 research/GUIDANCE_REVISION_v1/verify_final.py
```

This checks the original code identities from commit2afc156, all original frozen evidence, source inventory, original ledger/report, AMD extraction and current corrected module/test/dependency identities. Previous verifiers remain valid only for their corresponding historical commits.
