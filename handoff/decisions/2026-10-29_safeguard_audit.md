# 2026-10-29: which safeguards protect the machine and which were holding it back

**Owner instruction:** "Make sure you engineer the self learning properly and make it fool proof. I want you to
understand what safeguard is hindering us and what is not. I also want you to make this machine very intelligent."

**Method.** Every safeguard in the lab is listed below, each with the failure it prevents and what it costs the
machine's ability to learn and reach verdicts. The verdict is one of three: **keep**, **fixed today** (it was
hindering, and the fix is in this commit), or **owner decision** (the cost is real and only the owner can trade it).

## Protects, at no cost to learning: keep

| Safeguard | Prevents | Cost |
|---|---|---|
| Hash-chained ledgers with RFC 3161 timestamps (`paper.append`, `verify_chain`) | rewriting a forecast after the fact | none |
| Append-only check (`tools/check_append_only.py`) and frozen `research/` | editing a protocol or result once written | corrections are addenda, not edits |
| Seal before entry (each set's `entry_cutoff`) | a prediction made after the price was known | none: it is what makes a record evidence |
| Session-closed guard (`paper.session_closed`) | a scan on a partial bar | none (it refused a premature IDX scan at 08:13 UTC today, correctly) |
| Matched twins | crediting a market-wide rise as skill | none: the only thing that separates skill from the tide |
| Frozen family rules and priors | learning that quietly rewrites the evidence it is judged on | none now that the learner sits beside the families |
| The learner's no-peeking verify | a learner trained on outcomes it could not have known | none (made robust today, below) |
| Paper only, no orders | losing money while the machine is unproven | none to learning |
| SEC contact inline only, secrets never printed | leaked credentials | none |

## Protects, at a real cost: keep, knowing the price

| Safeguard | Prevents | Cost | Verdict |
|---|---|---|---|
| Sealed holdouts (US and crypto 2024 onward; IDX 2024-01-02..2025-02-21) | the last untouched history being used up by tuning | the warm start stops at 2023, losing about 2.8 years of the most recent US data | **keep**: once spent it cannot be unspent, and it is the lab's only clean one-shot confirmation |
| t >= 3 floor at pre-registered looks (3.75 at the first) | false discoveries across the lab's many counted tests | slow verdicts: a standalone SEC13D verdict is about 17 years away at a 1% edge (POWER_v1) | **keep for verdicts; it no longer gates learning.** The arithmetic is solved by pooling (DOCUMENT_CLASS), not by lowering the bar. The learner's confidence has its own gate, below. |
| Futility stops | spending years on a dead idea | none | keep |
| "Do not tune the old IDX strategy"; retired "+30% day" entries | p-hacking a strategy that already failed | none for new work | keep |
| No paid data or new subscriptions without approval; no scraping X or Unusual Whales | spending money, breaking terms of service | excludes options-flow data, the best-documented pre-announcement signal (informed options trading before takeovers: Augustin, Brenner and Subrahmanyam, 2019), and licensed news | **owner decision** (below) |

## Was hindering: fixed today (research/LEARNER_v1/ADDENDUM_1.md, research/LEARNER_v2)

| What | Why it hindered | Fix |
|---|---|---|
| LEARNER_v1 judged against the sealed priors | it looked like a safeguard ("beat the priors") but rewarded base rates: on a register with no signal at all it scores 63% "skill" against 0.5 placeholders. A fake pass would have unlocked confidence the machine never earned | a climatology twin as the comparator; the learner's forecast is that base rate moved by centred slopes, so the only possible gain is telling sets apart (scored zero on the same world) |
| v1's confidence gate (n / 300 x skill / 5%) | too slow (300 forecasts however strong the evidence) and not luck-proof (a point estimate checked daily) | a time-uniform confidence sequence: opens when the evidence is real (median about 160 observations for a modest real edge in the tests), and luck clears it only 5% of the time over the machine's whole life |
| one confidence for every statement | a fake edge on one statement would unlock all of them | one gate per kind: relative, mechanism, triangulated |
| absolute statements (GAIN0, RUN30, FADE10) in the claim | credit for a rising market, the luck the owner ruled out | the anchor alone, never scored as skill |
| a filing sealed by a parent and a child family counted twice | evidence inflated, confidence earned early | each underlying event weighs once per statement |
| verify compared a hash of weights | a different floating-point library could flag an honest forecast as peeking and turn the routine red | verify reproduces every number within 1e-6 |
| learning only from live outcomes | nothing to learn from until 2026-11-27, little for a year | a pinned warm start: 5,587 events from 2020-2023, with their own intercepts, weighted as 300 live outcomes per kind at most |
| v2 scored no raw move at all (RUN30, FADE10) | a correct pump or pump-and-dump call could never earn credit. The owner: "I dont care if its gonna be a pump and dump. I just care if it gets it right, and its thesis on even a pump and dump or whatnot is right" | v2.1 (research/LEARNER_v2/ADDENDUM_1.md): the stock's own pump, dump and pump-and-dump are skill statements, each true only when most of its twins did not make the same move. Every call states its thesis and is RIGHT only when all of it came true. The Speculation Register's daily movers are read too |

## Hindering, still open: owner decisions

1. **Survivor-only prices** (free Yahoo data). Every historical long-side mean is biased upward: 48% of 13D filings in
   the kill test had no ticker in the panel. Feature effects are distorted too. The warm start's own intercepts and
   the weight cap contain the damage, but only a point-in-time database with delisted names fixes it (paid: CRSP,
   Norgate). It needs approval under the no-paid-data rule.
2. **Options flow and licensed news.** This is the largest data upgrade available for pre-catalyst detection. The
   learner takes new features without new architecture, but scraping is ruled out and a licensed feed costs money.
3. **Event rate.** This is not a safeguard but the real bottleneck now: each US family seals a few sets a day at
   most. Free additions that raise it:
   - the merger-agreement family (8-K Item 1.01), already the recommended next family;
   - 13G-to-13D switches;
   - Form 4 cluster detection across filings.

   Each gives the learner more outcomes with no new cost. Recommended next, unless the owner redirects.

## Not changed

Every frozen protocol, ledger line, family rule, prior and twin draw. The PAPER-POLICY versions. The sealed holdouts.
LEARNER_v1's two sealed forecasts, which keep verifying.
