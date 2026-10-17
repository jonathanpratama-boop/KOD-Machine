# Calendar portability correction

GitHub CI found that the calendar library’s default date range did not cover the requested 2026 test dates. The scheduler now requests explicit dates from source minus one day through decision plus 90 days. A regression test simulates an older host-default calendar range. Trading rules, thresholds, original source data, decision timestamps and all seven NO_SIGNAL records are unchanged.

The original implementation freeze remains intact at commit `2afc156`. The correction is recorded in `CALENDAR_REPAIR.json`. Verify this head with:

```sh
python3 research/GUIDANCE_REVISION_v1/verify_current.py
```

This verifier checks the original module/test identities from the original Git commit, every frozen input, the original decision chain and AMD source result, and the corrected code identities and explicit session schedule. The old `run_first_decision.py --verify` intentionally requires its original module hash; use it only on the original commit. No event or return was rerun.
