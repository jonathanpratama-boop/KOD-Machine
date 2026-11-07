# Prospective comparison check — 8 November 2026

The owner requested that each new signal be compared with coins selected before
its result, with the check shown on the existing one-page dashboard.

The existing R2 engine already freezes up to five controls in its append-only
EVENT record, using the recorded pre-event momentum and liquidity inputs. This
check reuses that original selection; it creates no second selector or signals.

The assessment start is recorded once in PROSPECTIVE_CHECK.json. Earlier ONE is
excluded from this prospective tally, because its result was already known.
Every later signal remains visible, including signals without usable controls.
For this check, use the one-minute arm and common 24-hour exit throughout, not
whichever timing arm looks best afterward. Costs remain the same for the event
and controls. A completed pair requires every member of the fixed control basket
to have its recorded outcome; missing entries or results are never zero returns.

Before scoring, verify that the basket agrees with its original EVENT ledger
record, carries the original reference clock, and precedes the outcome records.
Show comparison names and selection time as soon as the signal is available.
At completion show KOD's net return, the controls' mean net return, and their
difference. Accumulate beating/behind/tied counts and mean/median difference.
Show distinct signal dates without calling correlated signals independent.
No luck probability, significance pass, automatic trading permission, threshold
change, extra acquisition, or extension of R2 is introduced.

The existing 15-minute comparison service exports the check. The existing
private backup service then publishes DASHBOARD.html and DASHBOARD_RESULTS.json
using its existing repository-scoped identity. A small additive post-step locks
the existing backup Git index and can stage only those two files. Existing
backup manifests, acquisition, frozen code, and research records are untouched.
Publication errors are logged independently and cannot stop the collector.
The latest downloadable dashboard is updated automatically; an already-open
downloaded HTML copy remains a dated snapshot. Other studies retain their own
source timestamps until their usual data refresh.
