# LEARNER_v1: a self-learning layer that has to earn its confidence

Frozen 2026-10-29, before any outcome exists: no prediction in the Catalyst Register has resolved (the first window
ends 2026-11-27). `protocol.json` is normative; this file explains it. Owner instruction: "The machine should self
learn to understand how to triangulate a pre catalyst as accurately as possible and i want the machine to become
confident. I also want the machine to detect the catalyst based on accurate predictions, not being lucky that its going
up."

## What it does

The catalyst families stay frozen: their rules, priors and twins never change. Beside them, the learner reads every
sealed set and forecasts each of its cone statements, plus one joint statement, **TRIANGULATED**: the stated catalyst
happened *and* the stock beat its matched twins. It learns, from resolved outcomes only, how much each set's own
sealed features (the family, the filing's details, the stock's recent behaviour, the abstention rules) should move the
frozen prior. One model per statement, pooled across families, so evidence from insider buying can inform activist
filings and the reverse.

## How it becomes confident

Confidence is earned, not assumed. The learner keeps two numbers per forecast: its raw opinion, and the one it
publishes. The published forecast is the raw one shrunk toward the frozen prior by **alpha**:

- alpha is 0 until the learner's own earlier raw forecasts have beaten the frozen priors on outcomes that resolved
  *after* those forecasts were made;
- it reaches 1 only after 300 such resolved forecasts with a Brier skill of at least 5%;
- it falls back toward 0 if the skill disappears.

So on day one it publishes the frozen priors unchanged, and it says something different only when its track record
gives it the right to.

## Why it cannot be lucky

- **Twins remove the market.** A gain counts as EARNED only if the stock also beat its matched twins over the same
  horizon. If every stock rose, beating the twins is what separates skill from the tide. The report counts gains the
  market or sector carried as LUCKY.
- **The mechanism must happen.** For a family with a mechanism statement (the activist raising its stake, a second
  insider buying), a gain where the stated catalyst never came is LUCKY, not earned. TRIANGULATED is graded on both.
- **No peeking, provably.** Every forecast is sealed before the set's entry and records the hash of the model weights
  it used. `paper-verify` retrains from only the outcomes dated before the forecast and must reproduce that hash. A
  learner that saw the future would fail the check.
- **Heavy caution with little data.** A strong penalty keeps every adjustment near zero until many outcomes agree. On a
  perfectly clean synthetic pattern with 200 outcomes it moves only from 50% to about 69%.

## How it is judged

A pre-registered claim, scored only forward: per signal session, the published forecast's Brier score against the
frozen prior's, at the same looks and t >= 3 floor as every other test in the lab, with a futility stop from 240 pairs.
If it never beats the frozen priors, the record says so and the families are unaffected.

## What it never does

Change a family rule, prior, twin draw, resolution or ledger line; feed back into which sets the families seal; use an
outcome resolved after its forecast; place or simulate an order.

## Running it

```sh
python3 -m idxsig learner-forecast --commit   # after the catalyst-seal steps, before 09:15 New York
python3 -m idxsig learner-report              # rewrites paper/LEARNER.md
```
