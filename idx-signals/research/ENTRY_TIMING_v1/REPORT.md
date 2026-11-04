# ENTRY_TIMING_v1: when to buy a US +30% spike

Question (owner, 2026-10-30): "what about 5 day buy? Don't buy makes sense too. But when to buy?"

## What was tried
120 rules on period A (2026-04..10): buy 1 to 6 sessions after the spike, hold 1, 3, 5, 10 or 20 sessions, on all
spikes, KOD's kept two thirds, its safest third, or its flagged third. 0.6% round-trip cost. Exploratory.

## Result
- **No rule had a lower bound above zero, even on A, where it was picked.** 0 of 120.
- The frozen pick (buy next open, sell same close, all spikes: +0.73% mean on A, median -1.3%) **lost on B**:
  mean -0.83%, median -2.3%, 42.6% winners, lower bound -2.0%. NOT CONFIRMED.
- Disclosure: this exact rule's B number was already reported in FILTER_BUY_v1 (H1, all, typical). The protocol
  named the 5-day groups as seen but missed that one; the confirmation is therefore not unseen.
- Typical (median) trades lose in every rule. Means above zero come from a few huge runners.
- Flagged names after their dump (buy 3 days later, hold 10): mean +12.8% but median -22% and 19% winners: a
  lottery ticket, not a rule.

## Plain answer
There is no reliable time to buy these spikes. KOD's value is the other side: telling you which ones not to touch
(FILTER_BUY_v1: the flagged third lost 6-8% over 5 days in both periods). Survivorship flatters every buy number here.
