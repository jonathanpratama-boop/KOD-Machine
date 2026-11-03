# CRYPTO_ACCOUNT_v1 — Correction 1 (rules v1.1)

**Found by:** Ace's audit of commit c650438, 2026-10-31.

**The defect (v1, code at commit b4aec00):** an order took the newest recorded quote of any age as its decision
price, and could fill on that same quote. If today's fetch failed, a ten-day-old quote could become the decision,
a fill stamped ten days before the order existed, and a holding deadline already in the past. A failed fetch left
no record. Reproduced on the v1 code: order made 2026-11-01T00:30Z on a quote from 2026-10-22T00:30Z, "filled"
2026-10-22T00:30Z, deadline 2026-10-27T00:30Z.

**Affected records:** none. Under v1 the account recorded 2 quotes, 2 PASS declines (BEAMX, SOPH) and 1 mark;
no order was placed. Every record stays as written.

**The correction (v1.1, `idxsig/crypto_account.py`, pinned by `protocol_v1_1.json`):**
- a failed fetch is recorded (`CRYPTO_QUOTE_ERROR`) and never replaced by an older quote;
- an order needs a quote observed within 5 minutes before it; otherwise `DECLINE NO_FRESH_QUOTE`, with the reason;
- a fill must come from a quote observed at or after the order was placed (never its decision quote), before it
  expires and not after the run's clock; the 5-day deadline runs from that fill;
- exits use quotes observed after the fill and not after the run's clock; a late time exit records how late;
- each run observes again right after placing orders, so a fill is real and same-run;
- `verify()` rejects stale decisions, fills outside the order's life, deadlines not from the fill, exits before the
  fill, stop exits above the stop and time exits before the deadline.

**Unchanged:** limits, sizing, fee, chase, stop distance, order life, hold, decision source; `protocol.json`
(byte-identical, kept as the v1 record; its code pin now differs from the file, by design); the stock account and
the existing crypto experiments.

**Tests:** `tests/test_crypto_account.py`, 15 cases including the failed fetch, the ten-day-old quote,
quotes from before the order or after the clock, failed fetches while an order lives, an exit waiting for a fresh
quote, and ledger checks for back-dated fills, deadlines not from the fill and early time exits.
