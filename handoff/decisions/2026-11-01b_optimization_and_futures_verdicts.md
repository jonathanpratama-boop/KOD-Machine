# Optimisation study and futures study, 2026-11-01: verdicts (both frozen, run once, independently verified)

Owner's requests:
- The optimisation brief: "build and execute a disciplined optimization study, spot buying first ... don't tweak until
  green ... You do not have permission to move the goalposts, hide failed trials or promise profit".
- "Keep trying until you have found a way to make the machine profitable in spot and futures. If old ways don't work,
  find new ways."

Constraints followed:
- Simulation only; no orders, accounts, paid data or credentials. No remote publication: every commit is local until
  the owner approves a push.
- No sealed dataset opened. Frozen protocols with RFC 3161 timestamps before each run, one run each, independent
  verification.
- Ace's cash-tender census and funding-carry work were not duplicated.

## Trial log of this round (every attempt)

| # | Study | Market | What was tested | Data | Verdict (verified) |
|---|---|---|---|---|---|
| 1 | `research/MSCI_DELETION_OPT_v1` | IDX spot, long only | One lever, the holding period after the forced-selling closing auction (1/2/3/5/10/20 sessions; 20 = the original rule), chosen by an expanding walk-forward on past reviews only; gates W0-W8 fixed in advance | 23 non-sealed MSCI reviews, all previously inspected, so **exploratory** | **EXPLORATORY_REJECT** |
| 2 | `research/VIX_BASIS_v1` | Cboe VIX futures | Sell the volatility insurance premium only when the curve is in contango: the published Simon-Campasano entry, short leg, unhedged, 20% notional, costs 0.065 points per side | 218 Cboe contracts; discovery 2006-2015, validation 2016-2023, never used by KOD; 2024-2026 sealed | **NOT_CONFIRMED** |

### 1. MSCI deletion holding period (spot)

- **Walk-forward choices.** Hold 20 at 11 of 16 deletion reviews, hold 10 at 5.
- **Walk-forward result.** +1.49% mean per trade, but a cluster-bootstrap lower bound of -3.77%. The account went
  IDR 160m to 191.7m against 173.4m for the 20-session baseline.
- **Failed gates:**
  - W2: the lower bound is below zero.
  - W4: the out-of-time block averaged -0.79%.
  - W5: the account is negative without its 3 best trades.
  - W6: with next-session entry the mean is -2.91%.
  - W8: hold 20, the most-selected hold, loses as a fixed rule.
- **Fragility.** The early hold-20 picks rest on one training review, Nov19 (3 trades).
- **The important finding.** Every fixed hold loses when entry slips one session past the implementation-day auction.
  Whatever the trade has lives only in that one auction fill.
- **Consequence under the frozen rules.** The family's search on history ends. No prospective protocol is licensed.

### 2. VIX futures basis (futures)

- **Discovery passed every gate:** +91% at 20% notional, drawdown -19%, 9 of 10 years up, bootstrap lower bound +1.2%.
  But 2006-2011 is the paper's own sample.
- **After publication (2016-2023):** +13.6% in eight years against the S&P 500's +137%. It ended USD 216 below its start
  with doubled costs (V4 fails), the bootstrap lower bound is -1.16%, the P&L without the 5 best positions is negative,
  and only 4 of 8 years were up.
- **Fragility.** The verdict depends on the one-session convention for days to settlement. The premium after
  publication is marginal at best.
- **The other arms are not candidates.** Choosing the best of them now would be selection on validation data.

## Exposures disclosed

- **MSCI study.** Every review was inspected before (labelled exploratory). Sealed-window panel rows fed trailing
  features and early out-of-time liquid-market membership. No return inside the sealed window was computed.
- **VIX study, before the freeze.** These were seen:
  - nine far-dated March 2020 back-month settlements, printed during a data-quality check;
  - validation-window short-signal counts, from the feasibility runs.
  Both are disclosed in `VIX_BASIS_v1/PROTOCOL.md` section 3.

## What remains untested (not evidence against anything)

- IDX archive fields never used as signals: daily foreign buy/sell volume, closing bid/offer queues, negotiated-market
  blocks (2019-07 .. 2023-12 is clean development data; 2024-01 .. 2025-02 is the sealed holdout). A scoping workflow
  (literature, counts-only coverage, candidate designs) is running.
- A hedged VIX basis (the paper's S&P hedge). A hedged MSCI-deletion relative trade. No IDX index future was verified
  for a retail account.
- S&P 500 deletions. Blocked: KOD's US panel only covers stocks still listed today.

## Decisions for the owner

1. **Publication.** 13 local commits on `claude/idx-signals-test-repo-ds0jw7` await your approval to push.
2. **MSCI Nov 2026 review.** It is announced 11 Nov 2026, effective 1 Dec, with implementation at the IDX close on 30 Nov.
   The frozen rules license no prospective log after a REJECT. A no-money prospective log of an auction-entry,
   short-hold rule would be a new, separately frozen hypothesis based on already-seen data. It would need your explicit
   go-ahead before 11 Nov.
3. **Holdouts.** No sealed holdout is requested: neither rule earned the right to spend one.
4. **Next study.** Proceed with the best-ranked design on the untouched IDX archive fields once scoping returns.
   The owner may redirect.
