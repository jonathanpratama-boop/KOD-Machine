# VIX_BASIS_v1: sell VIX futures only when the futures curve pays for crash insurance (futures study, simulation only)

Written 2026-11-01, before any strategy return was computed, after the owner's message "keep trying until you have found
a way to make the machine profitable in spot and futures". Separate from the spot work, as the owner's optimisation brief
asks ("futures and leverage later as separate studies; don't use leverage to rescue a spot signal"). Simulation only: no
orders, accounts, paid data or credentials, and nothing is published remotely until the owner approves. Code:
`collect.py` (Cboe public files -> `data/manifests/cboe_vx-20261101T081634Z.jsonl`) and `vix_basis.py`
(`--feasibility`, `--freeze`, `--run`); tests `tests/test_vix_basis.py`.

## 1. Mechanism (who pays, why it persists, what is observable, what would disprove it)

- **Who pays.** Holders of equity portfolios buy VIX futures, VIX calls and long-VIX exchange-traded products as crash
  insurance. Long-VIX products also roll their futures daily, buying the next contract and selling the near one. In
  calm markets this demand keeps VIX futures above the spot VIX they converge to at settlement (contango). A seller
  collects that premium as the futures drift down to spot.
- **Evidence before this test (literature, not KOD data).**
  - Simon and Campasano (working paper 2012; *Journal of Derivatives* 2014), on 2006-2011: the VIX futures basis did not
    forecast changes in spot VIX but did forecast VIX futures returns. They read this as a harvestable premium.
  - Their baseline rule: sell (buy) the nearest VIX future with at least 10 trading days to settlement when the daily
    roll is above 0.10 (below -0.10) points, hold 5 trading days, hedged with mini-S&P futures. This summary comes from
    secondary sources; the paper's full text was not re-read.
  - Eraker and Wu (*JFE* 2017) and Whaley (2013) document persistently negative returns to long VIX futures and long-VIX
    notes.
- **Why it can persist.** It is payment for bearing crash risk. VIX futures can rise 50-100% within days, and margin
  calls force sellers out at the worst time. That limits how much capital arbitrages the premium away.
- **Pre-entry observables.** Each session's front settlement F, spot VIX and trading days to settlement, giving the daily
  roll (F - VIX) / days. All are known at that day's close; the trade happens at a later session's settlement.
- **Disproof.** The test fails if, after costs, shorting in contango loses money or does not beat cash, if one crash
  wipes out years of premium (drawdown gate), or if the result disappears out of sample: validation 2016-2023 starts
  after the paper was public.

Not duplicated: Ace's crypto perpetual funding-carry simulator (a different instrument and premium) and the
cash-tender census.

## 2. The rule (frozen)

The entry rule (10-day front, 0.10 threshold, 5-session hold) is the paper's as summarised above, not tuned. The
sizing, costs, lag, the unhedged short-only form and every gate threshold are this study's own choices, fixed here
before any result.

- **Front contract:** the nearest monthly VX contract with at least 10 trading days to its final settlement and a
  settlement that day. Days to settlement count scheduled sessions. An unscheduled closure counts as a session only for
  decisions made before it became known: Ford's day of mourning (2007-01-02, announced Thu 28 Dec 2006) and Hurricane
  Sandy (2012-10-29/30, announced over the weekend).
- **Daily roll:** (F − VIX close) / trading days to settlement.
- **Signal:** on a day whose roll is above +0.10 points, sell that front contract at the settlement `lag` sessions later
  (lag = 1), and buy it back at settlement 5 sessions after entry.
- **Continuation:** at a 5-session exit, if the decision `lag` sessions earlier is the same side in the same contract,
  the position continues with no exit or entry cost and is resized to equity (at no cost for fractional sizing).
  Otherwise it is closed (cost) and may reopen (cost).
- **Window edges:** no position is opened on a window's last session. A position still open at a window's end is closed
  at its last settlement with a cost.
- **What a "trade" is.** A **position**: a fresh entry plus its cost-free continuations, closed once with a cost. The
  gates count and test positions. A position's return is its P&L over the notional it opened with. That is the P&L
  the account books, since continuations are resized to equity and not reinvested. Segments are also reported.
- **Short leg only and unhedged.** The paper's long leg (roll below -0.10) is a descriptive arm. Its S&P hedge is not
  modelled: that is an untested idea for a later study.
- **Sizing:** notional = 20% of equity at entry and at each continuation. A 100% overnight futures jump then costs about
  20% of equity. That is not a maximum loss: a futures price can more than double, and no stop is used.
- **Costs per side:** one 0.05 tick plus USD 1.50 commission and fees per Mini VIX (VXM, USD 100 per point) contract,
  i.e. 0.065 points. Fills are at the daily settlement price.
- **Account:** USD 10,000 (about IDR 160m). Cash earns 0% on both sides; T-bill interest on collateral is not credited.

## 3. Data, windows and exposure

**Source.** Cboe's own public files: VX daily records per monthly contract (expiries Jan 2006 .. Feb 2024; 218 files),
and VIX and SPX daily closes.

**Data handling** (counts in `FEASIBILITY.json`):
- Rows dated 2015-04-03 (Good Friday) are dropped (9 rows). It was not a CFE business day: Cboe's notice of 26 Mar 2015
  booked trades from Thu 2 Apr 3:30 p.m. CT to Mon 6 Apr 3:15 p.m. CT to business day Mon 6 Apr, and no open interest
  changed that day. Found by a pre-freeze reviewer. It changes days-to-settlement on about 21 discovery decision days
  and the front on 2015-04-01.
- Every VX quote before 2007-03-26 was at 10× VIX and is divided by 10 (2,426 rows). The load then checks that no
  settlement is implausible against VIX (ratio outside 0.2-5, where a scaling error would land); a pre-rescale
  violation stops the run.
- A zero settlement with a positive close uses the close (488 rows, all in Jan-May 2013, all back months at least 41
  sessions before expiry).
- Rows with neither are dropped (336).
- Rows with no volume and no open interest are dropped (529): 518 rows before a contract's first trade or open
  interest, plus 11 interior idle rows (2012-10 and 2015-10 contracts), all at least 38 sessions from expiry.
- One isolated bad print is dropped: a 1.0 settlement on 2008-04-21 in the Feb 2009 contract, 209 sessions before
  expiry, after the contract had begun trading.
- With the idle and plausibility filters each switched off, the front contract and days-to-settlement are identical on
  every 2006-2023 decision day. An independent reviewer compared them day by day.
- Expiry is computed from Cboe's rule: the Wednesday 30 days before the next month's third Friday, or 30 days before the
  business day preceding that Friday when it is Good Friday (2008-02, 2014-03, 2019-03, 2022-03). The load asserts the
  rule equals every full contract's last row; all 216 match.
- The trading calendar is the VX trading dates plus the two unscheduled closures above. The VIX file also lists some
  exchange holidays (2022-2023), which are not sessions. One VX session has no VIX close (2018-12-05). The simulation
  steps only through days with both, so on that day a hold or lag spans one extra real session and the position is not
  marked.

**Windows.**
- **Discovery:** 2006-01-03 .. 2015-12-31. 2006-2011 is the paper's own sample, so discovery is in-sample for the
  literature.
- **Validation:** 2016-01-04 .. 2023-12-29. Post-publication. It is computed in the same run only if every discovery
  gate passes.
- **Sealed:** the US/crypto holdout 2024-01-01 .. 2026-12-31. 1,485 raw rows dated in it are dropped at parse time and
  never used. The Jan and Feb 2024 contracts use their rule settlement dates (17 Jan, 14 Feb 2024) for their 2023 rows.

**Exposure, disclosed.**
- No KOD study has used VIX futures or the VIX index (checked by searching the repo). The researcher's general knowledge
  of famous volatility events (2008, Aug 2011, Feb 2018, Mar 2020) is a contamination that cannot be removed.
- While writing the plausibility check, before the freeze, one diagnostic printed nine back-month settlements from the
  validation window (Aug-Nov 2020 contracts on 2020-03-12, 03-16 and 03-17) and their ratios to VIX (0.35-0.39). These
  contracts were 112-179 trading days from expiry, never fronts the rule could trade. That VIX spiked in March 2020 is
  public knowledge. No strategy return, P&L or front-contract statistic was computed or seen.
- The first feasibility runs also computed and showed two validation counts. The first is the number of validation
  sessions with a short signal under the primary rule (720, then 726 after the calendar fix). The second is the number of
  contracts used (97). They show how often the rule would be in the market in 2016-2023, though not with what result.
  `feasibility()` now counts signals in discovery only.

## 4. Arms, benchmarks, stresses (every one is reported)

- **primary:** the rule above.
- **Stresses:**
  - S1: costs doubled to 0.13 points per side.
  - S2: two-session lag.
- **Brittleness:** N1 entry threshold 0.05, N2 entry threshold 0.15.
- **Descriptive:**
  - D1 both sides (the paper's long leg added, unhedged).
  - B1 always short: the front contract with no basis filter. It rolls to a new front only at a 5-session exit, so it
    can hold the old contract up to 5 sessions after the front changes (never past its expiry). It separates the premium
    itself from the filter's value.
  - R1 whole contracts: the primary rule with whole VXM contracts at USD 10,000, round(20% of equity / (F × 100)), no
    position when that rounds to zero.
    - It is applied over the whole window as if VXM had always existed.
    - The count is sized from prices known before the fill: the decision-day settlement for a new position, the
      previous session's settlement for a continuation.
    - A continuation that changes the count pays the per-contract cost on the difference. One that rounds to zero
      closes the position with a cost.
- **Benchmarks:**
  - cash (0%);
  - the SPX price index held through the window (no dividends, no costs; context only, a different risk).
- **Reported per arm:**
  - positions and segments, mean and median net position return on notional, win rate, average win and loss, payoff
    ratio;
  - account end and CAGR;
  - daily marked-to-market maximum drawdown, worst day, years positive and return by year;
  - exposure (share of sessions in a position), turnover and costs per year;
  - P&L without the 5 best positions;
  - bootstrap of the mean position return, clustering positions by entry month (10,000 draws, seed 20261103).

## 5. Gates (frozen; the code's `discovery_gates()`, `validation_gates()` and `verdict()` govern)

**Discovery.**
- **D0** at least 40 positions; otherwise INCONCLUSIVE.
- **D1** the account ends above its start, and its P&L without the 5 largest winning positions is > 0.
- **D2** mean net position return > 0, with its entry-month cluster bootstrap one-sided 95% lower bound > 0.
- **D3** daily maximum drawdown shallower than -35%.
- **D4** the account ends above its start under both S1 and S2.
- **D5** the account ends above its start at both N1 and N2.
- **D6** the account rises in at least 6 of the 10 years.

**Validation** (only if D0-D6 pass).
- **V1** the account ends above its start.
- **V2** mean net position return > 0.
- **V3** daily maximum drawdown shallower than -35%.
- **V4** the account ends above its start with doubled costs.

**Verdict and what each outcome licenses.**
- FAIL if any D gate fails (INCONCLUSIVE if D0 fails).
- CONFIRMED if all D and V gates pass.
- NOT_CONFIRMED if discovery passes and validation does not.
- CONFIRMED licenses only a prospective paper log and asking the owner whether to spend the sealed 2024-2026 holdout. It
  is never a live order and never evidence of future profit.
- One run; no other parameters afterwards.

## 6. Venue and product structure (not verified; stated so nobody assumes it)

- **Exchange futures, and fractional contracts.** The simulation assumes Cboe exchange futures through a regulated
  futures broker, and the account curve assumes fractional contracts throughout.
  - Cboe's Mini VIX futures (VXM, USD 100 per point) launched in August 2020. Cboe also listed an earlier mini VIX
    contract for a period; its dates are not verified here.
  - The standard VX is USD 1,000 per point, about a USD 20,000 notional.
  - At USD 10,000 and 20% sizing, a real account holds 0, 1 or 2 whole VXM contracts at any date. Arm R1 shows that case.
    Margin increases during spikes are not modelled.
  - The VXM spread and fees are assumed, not measured.
  - Whether the owner is eligible for a futures account (for example at a broker accepting Indonesian residents) is not
    verified.
- **eToro.** eToro's VIX instrument is a contract for difference with the broker, not an exchange future and not
  ownership of anything. Its financing and spread terms would differ from this model. It is not what is simulated
  here.

## 7. Known limits

- Fills at the settlement price (Cboe offers trade-at-settlement on VX; not verified for VXM).
- Daily data: an intraday spike between settlements is not seen, so a stop could not be modelled honestly even if one
  were wanted.
- The 2024 calendar for the two sealed-expiry contracts is approximated (US weekdays minus 1 Jan and 15 Jan 2024; exact
  for those weeks).
- The literature sample overlaps discovery.
- No S&P hedge.
- `run()` writes `run/` only at the end; an interrupted run leaves no output and may be restarted.
