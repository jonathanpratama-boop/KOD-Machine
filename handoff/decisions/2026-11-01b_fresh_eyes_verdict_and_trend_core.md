# Decision 2026-11-01b (owner's mandate, applied by the session): fresh-eyes review, frozen edge tests, trend core on paper

**Owner's instruction (2026-11-01, paraphrased from the brief):** study what works and fails for people building AI and LLM
trading machines; study the mechanism of edge; look at Binance spot and perpetuals, not only eToro; backtest the findings;
make the machine one system; take the lead without step-by-step approval; do not claim the ten-fold goal is impossible but
say what it takes; capital preservation and the ten-fold goal both matter; exits and range behaviour to be studied.

**What was done (all in `handoff/fresh-eyes-2026-11-01/`):**
1. Three literature reviews by independent sub-agents (LLM trading evidence 2023-2026; crypto edge evidence 2018-2026; retail
   bot autopsy incl. psychology and operational security), filed with sources.
2. A pre-registered protocol (FRESH_EYES_v1, sha256 pinned in commit 5b3d7c2 before any return was read) testing trend, funding
   carry, altcoin momentum, hourly mean reversion, exits and growth arithmetic on Binance's bulk archive (775 perpetual symbols
   including delisted ones; BTC/ETH spot from 2017). Run once. Independent code audit: engine correct, verdicts unchanged.
3. Result: slow trend on the majors is the one mechanism that survives Binance costs (ETH SMA 10/40 PASS, Sharpe 1.15 vs 0.65
   for holding; BTC near-pass). Funding carry, altcoin momentum and hourly mean reversion FAIL in 2023-2026. The trailing stop
   is not the best exit. Ten-fold in a year needs Sharpe about 3 at about 5x leverage; the validated edge is Sharpe about 1.2.
4. A paper protocol (TREND_CORE_PAPER_v1, hash pinned) with a volatility-targeted risk layer and a pre-registered kill criterion;
   the first daily decision (signal date 2026-10-31: CASH for BTC and ETH) is logged; a GitHub Actions workflow appends one
   line per coin per UTC day without using Claude usage.

**Decisions applied (default unless the owner overrides):**
- The moonshot-detector line (+30% in 1-5 sessions, spot long) is no longer the machine's core hypothesis. Existing frozen
  trials (PREMOVE_SHADOW_v1, the catalyst registers) run to their frozen ends unchanged.
- Research venue of record for crypto is Binance (spot and USDT perpetuals), not eToro; at eToro costs the validated rule no
  longer beats buy-and-hold on Sharpe.
- The one new research line is an exchange rule-change event register (delistings, margin and leverage tier changes), the
  family in which the lab's only earlier PASS lived and which has a named payer. It gets its own dated protocol before any
  data is read.
- LLMs read, classify, code, audit and document; deterministic code decides, sizes and executes; the owner holds the mandate
  and the kill switch. No LLM output enters a position decision.

**Not done, and why:** no access to the owner's laptop folders or to scheduled-task creation was granted by the platform
during this session, so the daily log runs in GitHub Actions instead; no real order, credential or deposit was touched.

**Owner decisions still open:** whether to run the paper trial for 90 days before any live allocation (the protocol's bar);
whether to keep the three daily Moonshot scheduled tasks and the daily crypto paper scan running on Opus, which spend
Claude usage every weekday; whether to fund an exchange-notice register study next.
