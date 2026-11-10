# US_SPLIT_ARTIFACTS_v1, addendum 1 (2026-11-10, written AFTER the v1 run; disclosed as such)

## What v1 found and why it is kept

The frozen v1 run (`results/`, rule `RULE.md`, sha256 ae2af4c9…) classified 134 sets: 0 ARTIFACT_CONFIRMED,
3 ARTIFACT_PROVIDER_ONLY, 6 SPLIT_REAL_MOVE, 1 UNEXPLAINED_GAP, 3 UNKNOWN, 121 CLEAN. By its stop rule the question
closes as isolated cases. That result stays on record unchanged.

## A premise of v1 is false (found by inspecting the provider bars of the 13 non-CLEAN sets; no outcome read)

v1 assumed the provider adjusts every bar of a name for every split, so the fresh pull's own close ratio is
split-free. For 5 of the 6 SPLIT_REAL_MOVE sets (PARA, SCAG, ENLV, OMEX, TOPS) the provider has no close on the
session(s) around the split and its last close before that gap is still in pre-split units (TOPS: 0.32 on
2026-11-03, null 11-04 to 11-06, 3.15 on 11-09, with a 1:10 event dated 11-06). The fresh ratio therefore repeats
the split jump. ATYR is UNEXPLAINED_GAP only because the provider dates its 1:40 event a session before the signal
bar while the recorded previous close is older still.

## Corrected secondary classification (v1.1)

Not a replacement of v1; reported beside it.

- `k` = denominator / numerator of a provider split event effective in (signal_session - 10 calendar days,
  signal_session]; `r` = recorded `signal.close / signal.previous`.
- **ARTIFACT_V11**: some such event has `r / k - 1 < 0.30` and `|ln(r / k)| < |ln r|` (dividing by the split
  brings the recorded move closer to no move, and the split-adjusted move is not a +30% day).
- The SEC tier of that event is reported as found by us-actions-v2 (VERIFIED, RATIO_CONFIRMED, MENTION_ONLY,
  NO_EVIDENCE); it does not gate the class. Reason: the verifier's same-date requirement was built for scoring
  units, and several filings state the ratio with an effective date one session off the provider's.
- Sets with a huge recorded move and no provider event (VCIG +4,728%, a serial reverse splitter) stay
  INDETERMINATE: the provider lists no split, and v1.1 does not infer one from prices.

The 0.30 threshold is the detector's own. Nothing in v1.1 uses a return after the signal session.
