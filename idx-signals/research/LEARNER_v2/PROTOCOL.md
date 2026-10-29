# LEARNER_v2: a learner that can only be credited for telling sets apart

Frozen 2026-10-29, before any live outcome exists. No RESOLUTION record is in `paper/catalysts.jsonl`; the first H20
window ends 2026-11-27. `protocol.json` is normative and this file explains it. It replaces LEARNER_v1, whose claim was
withdrawn for the defects in `research/LEARNER_v1/ADDENDUM_1.md`.

Owner instructions, 2026-10-29:

> "The machine should self learn to understand how to triangulate a pre catalyst as accurately as possible and i want
> the machine to become confident. I also want the machine to detect the catalyst based on accurate predictions, not
> being lucky that its going up."

> "Make sure you engineer the self learning properly and make it fool proof."

## The idea in one paragraph

Every catalyst set carries statements that resolve later:

- **beats its twins:** the stock outperforms matched stocks over the window;
- **the catalyst comes:** for example, the activist raises the stake, or a second insider buys;
- **both together.**

The learner forecasts each one. It is graded against a **twin of itself that knows only base rates**, meaning how often
each statement comes true for each family. Its forecast is that base rate moved up or down by what this set looks like.
The moves are measured from the average live set sealed so far, so over the live population they cancel by
construction, and the learner can win only by putting the right sets above the base rate and the wrong ones below
it. That is triangulation, and luck and a rising market cannot fake it.

## What it learns from

- **Live outcomes.** Every resolved statement of every sealed set. One filing sealed by a parent and a child family
  counts once.
- **History (the warm start).** 5,587 events from three of this lab's own studies, with signal dates from 2020-07 to
  2023-11:
  - 1,065 activist 13D filings;
  - 2,964 insider purchases;
  - 1,558 dilution filings (8-K Item 3.02).

  The features are computed by the same code that reads a live set. History has its own base rates, so its
  survivor-only prices and analogue outcomes never reach the live anchor. It counts as much as **300 live outcomes per
  kind** and no more: about a year of the live record outweighs it. The file is pinned by sha256. The sealed holdouts
  (2024 onward) are never read.
- **Not covered by history:** the activist raising the stake (MECH_13DA_UP_60) and SEC13D_V2's triangulated statement.
  Before December 2024, 13D amendments have no structured cover page, so those learn from live outcomes only.

**What history already says**, with the weight capped:

- Insider buys in less liquid stocks are followed by a second insider buy more often: about -0.30 in logit per step of
  log liquidity, at 2.6 standard deviations.
- The relative effects are small and uncertain. The learner starts humble, as it should.

## What it looks at

Only fields sealed in the set, plus the sets sealed before it.

**The stock before the signal**, signed by the call's direction:

- the 1-, 5- and 20-session move;
- the distance from the 60-session high;
- volume against normal;
- where the close sat in the day's range;
- liquidity.

**The filing:**

- whether the family fired or abstained, and on which rule;
- the purchase size, a top executive buying, several insiders, and the lag from trade to filing;
- the holdings increase;
- the activist's stake, stated intent, and the intent words in Item 4;
- whether the filing landed during the session.

**Triangulation**, counted over the 90 days before the set on the same issuer:

- *repeat:* other events from the same source;
- *corroborate:* events from another source pointing the same way, for example insider buying after a 13D;
- *conflict:* events pointing the other way, for example a dilution filing.

## How it becomes confident

The learner publishes the anchor moved by **alpha** times its own move. Alpha is set per kind (relative, mechanism,
triangulated).

- alpha is **0 until proven**. It opens only when the lower edge of a **time-uniform confidence sequence** on its
  forward Brier gain over the anchor is above zero. The bound stays valid however often it is checked, so a daily look
  cannot let a lucky streak through except with 5% probability over the learner's whole life.
  - Measured in the tests: zero true skill opened the gate in 2 of 40 runs, checked after every one of 400 observations.
  - A learner with real skill opened it after a median of about 160 observations.
  - The bound used is its running maximum, which keeps the same guarantee, so proven skill stays proven while the
    bound's own noise wanders.
- alpha reaches 1 when that lower bound shows at least **2% Brier skill**.
- alpha **closes again** if the last 120 observations turn non-positive. It is also capped by their recent skill, so it
  follows an edge that fades.
- Below 30 observations it stays shut.

## Calls

A **BACK** call needs two things:

- the learner puts the set at least 0.4 in logit above its anchor (about 1.5 times the odds);
- it is 95% sure, after its own uncertainty about this set, that the set is above the anchor.

**AVOID** is the mirror.

- Until the gate opens, every call is a **shadow call**: sealed and scored, never published.
- A call goes **live** only when the published move clears the margin too.

Calls are scored on:

- hit rate against the anchor's rate on the same sets;
- the paired excess return over the twins;
- why each hit was earned:
  - *earned, the catalyst came:* the stock beat its twins and the mechanism happened;
  - *beat the twins, but no catalyst;*
  - *rose with the market but lost to the twins:* a miss, however good it looked.

## How it is judged

The claim is the learner's sealed raw forecasts beating the anchor. The statistic is the per-session mean Brier gain
on skill statements, with one-sided t. It uses the lab's looks (60 ... 1920 pairs) and the t >= 3 floor (3.75 at the
first look), with futility from 240. Absolute statements are never part of it. If it never beats the base rates, the
record says so, and the families are unaffected.

## No peeking, provably

Every forecast is sealed before the set's entry cutoff. It records:

- the set's features;
- the anchors;
- the raw and published values;
- the calls and the gates.

`paper-verify` retrains on the resolutions dated before each forecast and must reproduce every number within 1e-6. A
learner that saw a later outcome cannot pass. Because the check compares numbers rather than a hash, a different
floating-point library cannot raise a false alarm.

## Running it

```sh
python3 -m idxsig learner2-forecast --commit   # after the catalyst-seal steps, before 09:15 New York
python3 -m idxsig learner2-report              # rewrites paper/LEARNER_V2.md
```

`learner-forecast` and `learner-report`, the routines' old names, run v2 too.
