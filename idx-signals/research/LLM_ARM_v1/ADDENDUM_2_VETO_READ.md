# LLM_ARM_v1, addendum 2: a read of the LLM's vetoes on KOD's BUY_OK names (descriptive, decides nothing alone)

Written 2026-11-13 (UTC), BEFORE any listed set had a BASE5 outcome (checked on the register at data-branch commit
`c48e9fa19`: 0 of the 107 sets below had any BASE5 record). `PROTOCOL.md` and addendum 1 are unchanged. Proposed by
Claude for the owner's question "does an LLM improve trading decisions over KOD's existing rules"; the owner may
discard it. Code: `veto_read.py` beside this file, frozen with this text.

Why: `agrees_with_kod` compares each call with the scan's decision (PASS, no buy), and the LLM disagreed once in 179
calls. KOD's paper book, however, marks most planned spikes `BUY_OK`, and the paper account acts on that list. On the
107 `BUY_OK` names called from 2026-11-05 to 2026-11-12 the LLM said AVOID 82 times, ABSTAIN 24 and BACK once. Those
are the calls where the LLM would change a trading decision KOD actually makes.

Disclosed: the author of most calls has seen next-session (NEXT1) resolutions of some of these names in the nightly
logs. No five-session outcome existed.

## The read (fixed now)

- **Population:** the US sets with a paper-book plan `BUY_OK` (`paper/paper_book.jsonl`) and an LLM_ARM call, signal
  sessions 2026-11-05 to 2026-11-12: exactly 107 sets, listed by `veto_read.py` from the call files. Later sets are not
  added; they can form a separate read.
- **Outcome:** the register's own BASE5 `candidate.trade.net_return` (costs included). Sets not `TRADED`, `UNRESOLVABLE`
  or still open are counted and left out.
- **Groups:** VETO = the LLM said AVOID. KEEP = the LLM said ABSTAIN or BACK.
- **Reported:** n and mean net return of all `BUY_OK` trades (KOD's book), of KEEP (the LLM-filtered book) and of VETO;
  KEEP minus VETO, with a one-sided p from a bootstrap that resamples whole signal sessions (10,000, seed 20261113) and
  Welch's t beside it.
- **When:** on the first nightly run after which every listed set is resolved or unresolvable, or on 2026-11-27 with
  whatever is resolved then, whichever comes first.
- **Meaning, fixed now:** the LLM veto earns a prospective trading test only if KEEP beats VETO by at least 5 points of
  mean net return with one-sided p <= 0.05. Otherwise this read gives no evidence that the LLM improves KOD's trading
  decisions, and the LLM stays in its reading and classifying role (decision 2026-11-01b). Either way, a KEEP book with a
  negative mean is still a losing book: the read compares filters, it does not make spikes profitable.
