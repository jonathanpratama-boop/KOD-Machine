# KOD-Machine, seen fresh: what works, what does not, and what to build next

> **Corrections (2026-11-02): see `ERRATA_20261102.md` in this folder.** In particular: the sizing is per coin, with no
> portfolio-volatility target (§6); the loss cap in §6 was never built; "validated" means "survived a frozen historical
> test", not "shown to make money".

Written 2026-11-01 (UTC) by the cloud session on the owner's instruction to study the machine and the field from a
wider perspective, to backtest the findings, and to lead without step-by-step approval. Everything below is either a
verified fact (with its source in this folder), a result of a frozen test run once today (`backtests/RESULT.md`,
audited in `backtests/AUDIT.md`), or an inference marked as such. No order was placed; no money moved.

## 1. Verdict

1. The lab is not failing because it is sloppy. It is failing because it has spent forty-odd rigorous tests on the one
   hypothesis class where edge is least available to a retail account (predicting +30% repricings and buying them
   spot within one to five sessions), under venue constraints (eToro at about 2% a round trip on crypto, no
   shorting, no perpetuals) that exclude every edge the literature documents. The loop is: hard hypothesis, honest
   test, failure, new detector, repeat. The remedy is to change the hypothesis class and the venue, not the rigour.
   Confidence: high.
2. Of the mechanisms with credible evidence, exactly one survived today's frozen tests on Binance's own data at
   Binance costs: slow trend following on the two majors. A 10/40-day moving-average rule on ETH kept Sharpe 1.15
   after costs in 2023-2026 against 0.65 for holding ETH, with a 37% maximum drawdown against 68%; on BTC the same
   rule had Sharpe 1.12 against 1.16 for holding BTC, with drawdown 37% against 53%. This is a drawdown-avoidance
   edge worth roughly Sharpe 1.0-1.2, which the literature calls the practical ceiling for crypto trend. It is not a
   growth engine. Confidence: medium (single frozen test, two correlated passes among twelve variants, random
   long/flat positions on BTC already earn Sharpe about 0.6).
3. Funding carry (7% a year in 2023-2026, down from 17-37% in 2020-2021), altcoin cross-sectional momentum (Sharpe
   0.3-0.5 since 2023, drawdowns above 60%), and hourly mean reversion after liquidation cascades (+0.78% a trade in
   2020-2022, zero since 2023) all failed their pre-set bars. Each was real once and has decayed or been arbitraged.
   Confidence: high that they failed as specified; medium that no variant would do better.
4. The ten-fold-in-a-year goal is a statement about leverage, not about edge. To reach 10x within a year with
   better-than-even odds and without a 50% drawdown first requires a Sharpe-3 strategy run at about 5x leverage.
   The best strategy validated here has Sharpe about 1.2; at 3x leverage it reaches 10x in a year on 27% of paths,
   suffers a 50% drawdown on 97% of them, and ends below half the starting capital on 29%. The same strategy at 1x
   to 2x has a median path of roughly 8-25x over four to five years, with 50%+ drawdowns on the way. Those are the
   numbers; they do not say the goal is impossible, they say what buys it and what it costs. Confidence: high (the
   arithmetic), medium (the Sharpe estimate it rests on).
5. LLMs have no demonstrated edge at forecasting prices or sizing positions. Every audited claim to the contrary has
   lost 50-72% of its reported return once the test window moved past the model's training cutoff, and the only
   live real-money experiments (Alpha Arena) lost money for most models. LLMs do have demonstrated advantages
   upstream of the trade: reading and classifying text at scale and consistently, generating and auditing research
   code, and running a disciplined research process. The machine should use them there and nowhere else.
   Confidence: high.

## 2. Why edges exist and why they die (the mechanism, in one page)

An edge is a payment from someone who must trade for a reason other than expected return. The payer and the reason
are the whole story; the pattern on the chart is the receipt.

| Edge class | Who pays and why | Why it decays | Status in these tests |
|---|---|---|---|
| Trend following on liquid majors | Late movers, forced sellers in downtrends, under-reaction to regime change | Needs trends; dies in long ranges; crowding compresses but rarely kills it at monthly horizons | Survived (ETH PASS, BTC near-pass); value is in missing the crashes, not catching the rallies |
| Funding carry | Leveraged longs paying for upside in booms | Arbitrage capital (Ethena, basis funds) crowds it toward the risk-free rate | Failed the 8% bar in 2023-2026 (7% gross) |
| Liquidation-cascade reversal | Liquidated positions sold at any price | Market makers and faster bots now absorb the flow within seconds to minutes | Worked 2020-2022 at 4h horizon; zero since 2023 |
| Altcoin momentum | Attention-chasing retail | Jump risk on shorts, delistings, a universe that lost 69% in 2025 | Failed; one good year (2020) |
| Announcement reactions (the lab's one earlier PASS) | Anyone slower than two seconds after a listing article | The event type itself disappeared (29 a year in 2020-2023, 4 in 2025, 0 in 2026) | Could not be retested; opportunity gone |
| Index deletions, filings, insider buys (the lab's other lines) | Passive funds and slow readers | Thin event counts: years to a verdict at retail event rates | Not confirmed out of time |

Three rules follow. First, an edge that cannot name its payer is a pattern, not an edge; support-and-resistance
bounces, rejection wicks and "smart money concepts" have no identified payer and no peer-reviewed evidence (the one
systematic test found liquidity sweeps predict continuation, not reversal). Second, the faster the edge, the faster
it dies: anything settled in seconds to hours belongs to market makers now. Third, the slower the edge, the fewer
the events, so the longer the wait for a verdict; the lab's own power arithmetic (`handoff/decisions/2026-10-29_arithmetic.md`)
shows single-family event edges taking years to confirm at retail rates. The habitable zone for a retail account is
daily-to-weekly signals on liquid instruments, where costs are survivable, events are plentiful, and market makers
are not competing.

## 3. Entries, exits and the trailing stop

The owner asked that exits be studied, and that a trailing stop not be assumed best. The evidence agrees.

- Exits mattered less than entries. Holding the Donchian entry fixed, no exit rescued ETH in 2023-2026 (Sharpe -0.03
  to 0.49 across four exits against 0.65 for buy-and-hold); the entry rule, not the exit, decided the result.
- The 2 x ATR trailing stop was not the best exit in three of four coin-periods. A wide signal-based exit (the 10-day
  channel) or a fixed 5% initial stop plus the channel exit did as well or better. A 10-day time exit was worst.
- This matches Kaminski and Lo: a stop adds value only when returns trend at the stop's horizon; at hourly to daily
  horizons Bitcoin mean-reverts, which is exactly where tight stops destroy value. The 26-year equity exit study
  found the tightest trailing stop was the worst exit despite winning most often.
- "Range of bounces" and rejection: the best formal test (14,919 rules, four coins) ranked support-resistance the
  worst class with breakeven costs of 8-16 basis points, below Binance's round trip. Channel breakouts, the opposite
  bet, were the best class. The machine should trade breakouts and avoid fading levels.
- The right design is therefore: enter on a slow trend rule; size by volatility so that the position, not the stop,
  controls the loss; exit on the opposite signal or a wide fixed stop; never a tight trail. Inference: high confidence.

## 4. What LLMs do better than humans, what humans do better, and how to join them

Evidence-backed LLM advantages: extracting and classifying information from text at scale (news, filings,
exchange notices) more consistently than human annotators; producing research code quickly; applying a protocol
without fatigue; stating calibrated intervals (better than human surveys in one study). Evidence-backed LLM
weaknesses: numerical forecasting, over-extrapolating recent returns, locking onto priors, overtrading when given
discretion, and training-data contamination that makes any backtest inside the model's training window worthless.

Human advantages that still matter: deciding what question is worth asking, recognising when a market has changed
character, refusing to trade, and owning the risk. The retail base rate (Barber and Odean; the Taiwan day-trader
study) is that humans over-trade, sell winners early, and keep trading after losses; the machine's job is to make
those actions impossible rather than merely unwise.

Division of labour for KOD, as a design rule: the LLM reads, classifies, codes, audits and documents; deterministic
code decides, sizes and executes; the human sets the mandate, approves protocols, and holds the kill switch. The LLM
never decides a position size or an entry. This is the configuration the two 2025-2026 audit papers recommend and
the one the lab already practises in its research loop; it has not yet been applied to a live rule.

## 5. What has not been built, and what "new" can honestly mean

Nothing tested today is an invention; each is a published mechanism checked on Binance data with the lab's
discipline, and the fact that a rigorous retail lab had never run them is itself the finding. Three things remain
genuinely under-built in the field and are feasible for this machine. None is a guaranteed edge; each is a specific,
testable claim with a named payer.

1. **Exchange rule-change events as forced flow.** Binance publishes delistings, margin-tier and leverage changes,
   and collateral-ratio changes with timestamps. Each forces holders or leveraged traders to act on a schedule
   (the April 2025 ACT crash followed a leverage-tier change). The lab's announcement line found its only PASS in
   this family and lost it when launch announcements dried up; delisting and margin notices have not dried up.
   Who pays: holders forced out and market makers withdrawing quotes. LLM role: parse the notices into a structured,
   timestamped register. Open gap: no published study on Binance delisting or margin-change drift at daily horizon.
2. **LLM-as-extractor, classical allocator, evaluated only post-cutoff.** No published system has done this with a
   dynamic survivorship-free universe and real costs; the audit papers say it is the right shape. For KOD the
   natural text universe is exchange notices and project disclosures in markets with thin coverage (including
   Bahasa-language IDX disclosures, where no LLM trading study exists at all). Open gap: unreplicated.
3. **Abstention with a guaranteed error rate.** Conformal risk control (`handoff/github-finds/PLAN_v2.md`, rank 2)
   turns "no trade" from a judgement into a statistical guarantee: trade only when the model's error bound at the
   chosen confidence is below the cost. It is a capital-preservation technology, not an alpha, and the lab's own
   evidence says abstention is where its low losing rate will come from. Not yet implemented anywhere in KOD.

What "new" cannot honestly mean is a signal that turns Sharpe 1 into Sharpe 3 by cleverness. The historical record
of retail-built strategies (Quantopian's 888 algorithms, QuantConnect's alpha distribution, the 73% median live
haircut on bank strategies) says the population edge is near zero and that the backtest Sharpe barely predicts the
live one. The machine that survives is the one that budgets for that haircut.

## 6. Capital: preserving it, and the 1K to 10K question

Preservation is solved by construction, not by prediction: volatility-targeted sizing (daily portfolio volatility
1-2%), a hard daily and weekly loss cap enforced outside the strategy code, no leverage above 1.5x on a Sharpe-1
strategy, a pre-registered kill criterion (for example a 25% drawdown or a 90-day Sharpe below zero), and trade-only
API keys in a sub-account holding only the capital at risk. These are the features the behavioural evidence says
work because they remove the operator from the loop at the moment the operator is least reliable.

Growth is then arithmetic. From `backtests/RESULT.md` T6: at Sharpe 1.2 and 1x, USD 1,000 has a median of about
USD 1,700 after a year and a 19% chance of a 50% drawdown; at 2x, median about USD 1,950 with a 79% chance of a 50%
drawdown and a 15% chance of touching 10x; at 3x, a 27% chance of 10x, a 97% chance of halving on the way, and a 29%
chance of ending below USD 500. The honest statements are these: the 10x goal in a short period is a leveraged
lottery on a Sharpe-1 edge; the 10x goal over four to five years is the median outcome of the same edge at 1x-2x
with drawdowns the owner must be able to sit through; and nothing in this folder or the literature offers a
Sharpe-3 retail strategy to make the short version a calculation rather than a bet. If the owner wants to keep the
short version alive, the defensible structure is a core (trend on majors at 1x-1.5x) plus a capped satellite
(at most 10-20% of capital, funded only from core profits) for the leveraged attempt, so that the lottery ticket
cannot take the account with it. Inference: high confidence in the structure, medium in the figures.

## 7. The machine as one system

The lab already has the hard parts: hashed data manifests, frozen protocols, append-only records, causal signal
construction, matched controls, external timestamps, CI that refuses edits, a paper ledger with a hash chain. What
it lacks is a live rule worth running through that pipeline. The proposal is to keep every piece and change what
flows through it:

1. Data: Binance Vision bulk archive (already wired today; manifests in `backtests/manifests/`), extended daily.
2. Research loop: today's engine (`backtests/lib.py`, audited) for daily and weekly rules, alongside the existing
   idxsig harness for event studies. Every new rule enters through a dated protocol with its hash pinned first.
3. Signal layer: deterministic rules only (today: SMA 10/40 on ETH and BTC spot). LLM output never enters a
   position decision; it may populate event registers that a frozen rule then reads.
4. Risk layer, outside the strategy code: volatility targeting, caps, kill criterion, abstention as a first-class
   output. `backtests/signal_today.py` already prints CASH for both coins as of the 2026-10-31 close.
5. Paper loop: the existing crypto paper routine logs the daily state of the frozen rule for 90 days before any
   real order is considered; the pass bar for going live is written now, not after.
6. Venue: Binance (0.3% a round trip on spot), not eToro (2%): at eToro costs the validated rule no longer beats
   buy-and-hold on Sharpe for either coin.

## 8. Decision and next step

Decision for the owner (default applied unless overridden): stop the moonshot-detector line as the machine's core;
adopt slow trend on BTC/ETH spot on Binance as the core candidate; treat the 10x ambition as a capped satellite to be
designed only after the core has 90 days of paper record; pursue the exchange-notice event register as the one new
research line, because it is the family where the lab's only PASS lived and it has a named payer.

One primary next step: freeze a paper-trading protocol for the ETH and BTC SMA 10/40 rule (volatility-targeted to
1.5% daily, 1x maximum, kill at 25% drawdown or 90-day Sharpe below zero), pin its hash, and log the first daily
decision from `backtests/signal_today.py` into the paper ledger. Definition of done: protocol committed with hash,
first 30 consecutive daily decisions logged without a missed day. Timebox: the protocol tonight; the 30 days by
2026-12-01. Trigger to reconsider: the paper record fails its own bar, or a frozen exchange-notice register study
passes its pre-set gate.

## Sources and files

- `research/01_LLM_TRADING_EVIDENCE.md`, `research/02_CRYPTO_EDGE_EVIDENCE.md`, `research/03_RETAIL_BOT_AUTOPSY.md`
  (literature reviews with URLs).
- `backtests/PROTOCOL.md` (frozen; sha256 in `PINS.json`, pinned in commit 5b3d7c2), `backtests/RESULT.md`,
  `backtests/AUDIT.md`, `backtests/results_*.json`, `backtests/manifests/`.
- Lab history: `handoff/BLUEPRINT.md`, `handoff/decisions/`, `idx-signals/research/`.
