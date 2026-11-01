# MSCI_DELETION_v1: is a spot buyer paid for absorbing index trackers' forced selling of MSCI Indonesia deletions?

Written 2026-11-01, before any return of this rule was looked at. Simulation only. Code: `msci_deletion.py` (modes
`--feasibility`, `--freeze`, `--run`), events: `collect.py` -> `build_events.py` -> `events_all.csv` (from MSCI's own PDFs and
`ticker_map.csv`), tests: `tests/test_msci_deletion.py`. `protocol.json` pins the hashes of all of these and of the harness.

## 1. Constraints and place in the search
Owner, 2026-10-31: unleveraged spot buying only, cash allowed, no shorting, margin or perpetual carry; manageable
frequency; venue the owner can use. IDX shares via Stockbit are real exchange-listed shares (KSEI custody). This is the
second experiment of this edge search: LIQ_REBOUND_v1 (crypto, forced deleveraging) FAILED and was independently
confirmed; a crypto trend rule was researched and not run (weak post-2018 evidence, too few switches to test, tape-only).

## 2. Hypothesis, payer, falsifier
- **Mechanism.** At an MSCI review's implementation close, funds tracking MSCI Indonesia (inside MSCI EM and ACWI
  mandates) must sell every deleted name, whatever the price. The concentrated selling is absorbed at a concession that
  reverses once it is over (Grossman & Miller 1988; the asymmetric index effect: deletion price falls are temporary,
  Chen, Noronha & Singal 2004, JF).
- **Who pays.** Passive trackers and closet indexers (index turnover cost, Petajisto 2011). Broker estimates put the passive
  share of Indonesia's MSCI free-float capitalisation at about 13-14%.
- **Why it could persist in Indonesia.** Short selling was banned on IDX from 2 March 2020 until a staged restart in
  October 2026 (a handful of LQ45 names), so nobody could pre-position against deletions; domestic arbitrage capital is
  thin; foreign-ownership limits and thin books for small caps.
- **Evidence before the test (moderate, old, cross-country).** MSCI Standard changes in 38 countries 2000-2015 (Chen, Shiu
  & Wei, EFMA 2017; 48 Indonesian deletions in the sample): deletions fall 6.25% from announcement to the implementation
  close, rebound +1.02% and +0.53% on the next two days and fully recover by 60 sessions (+1.48% cumulative from the
  announcement). Hacibedel & van Bommel (MSCI EM 1996-2004): partial reversal. Counter-evidence: Chakrabarti et al.
  (MSCI 1998-2001) find no reversal for deletions; the US index effect has largely disappeared since 2010 (Greenwood &
  Sammon 2025); Indonesian theses are small and mixed. All of it is gross of costs.
- **Observable before entry.** MSCI's dated public list, published about ten IDX sessions before the implementation
  close, names every deletion and the implementation date.
- **What disproves it.** No net gain after Stockbit-level costs, no gain over matched non-event stocks bought at the same
  close (G1, G2), or a result that depends on a few trades or on buying exactly in the auction (G3, G4).

## 3. Prior KOD work (duplicate check)
Never tested. KOD's CATALYST_REGISTER_v1 family IDX_INDEX logs IDX's own index reviews (IDX30, LQ45, IDX80)
prospectively and descriptively from the 2 November 2026 review, "reported, never tested"; MSCI is not in it. The
pre-catalyst program (handoff/precatalyst-program/PROGRAM_v1.md, row 2) listed MSCI/FTSE Indonesia rebalancing as a
candidate without a test. Additions are not tested here: MSCI has frozen all Indonesian additions since 27 January 2026,
so an addition rule could not be traded going forward. Deletions continue under the freeze.

## 4. Data and periods (audit)
- Events: MSCI Global Standard and Global Small Cap public review lists and review press releases, Nov 2019 .. Nov 2023,
  51 PDFs from app2.msci.com, pinned in `data/manifests/msci_lists-20261031T235555Z.jsonl`. `build_events.py` parses the
  "MSCI INDONESIA INDEX" block (additions/deletions) and the press release's announcement and implementation dates;
  MSCI gives names only, mapped to IDX codes by hand in `ticker_map.csv` (two MSCI renames, both on an unchanged IDX
  code: NUSANTARA PROPERTI INTL -> SURYA PERMATA ANDALAN = NATO; BANK BRISYARIAH -> BANK SYARIAH INDONESIA = BRIS). The
  parse is checked against MSCI's own per-country summary row in every list, migrations are matched on the IDX code,
  and `msci_deletion.py --freeze`/`--run` refuse unless the PDFs match their manifest and `events_all.csv` regenerates
  byte for byte. 46 deletions in discovery (8 reviews), 14 in 2023 (4 reviews); 3 upward migrations
  (Small Cap -> Standard) are not deletions. Changes MSCI makes between reviews (early IPO inclusions, mergers,
  suspensions) are not included; they are not freely available.
- Prices: KOD's pinned IDX panel (panel-20261007T225823Z, the IDX exchange mirror) and its corporate-action registry
  (ca_registry-20261007T230210Z). The panel CSV is parsed whole and every row after 2023-12-29 is dropped before any
  computation (the count dropped is recorded); the market built for the harness is checked to end by 2023-12-29.
- Survivorship of the control pool: before 2021-01-22 the panel lacks names that had already delisted (quality TIER_2),
  so the Nov 2019, May 2020 and Nov 2020 reviews (most discovery events) draw controls from survivors, which biases
  control means up and G2 toward FAIL. This is stated now and does not change the verdict whichever way it goes.
- **Already influenced research (development data):** IDX 2021-01..2022-12 (E1, E3, E5, LEAD_LADDER, FLOW_IDX and
  others); 2023 is an already-used validation year (E1 validation, IDX_DILUTION_v1 test, IDX capacity), here a one-time
  provisional screen; 2019-10..2020-12 was read by few studies.
- **Sealed / not read:** the IDX holdout 2024-01-02..2025-02-21 and everything after. Trades whose 20-session hold would
  need a 2024 price (the Nov 2023 review) are INCOMPLETE and unscored.

## 5. The rule (frozen)
- Events: names MSCI deletes from the MSCI Indonesia Standard index (exits and downward migrations to Small Cap) or from
  the MSCI Indonesia Small Cap index (exits), in every scheduled review Nov 2019 .. Nov 2022 (13 reviews, discovery; 8 of
  them have Indonesian deletions) and Feb .. Nov 2023 (4 reviews, screen).
- Entry: a buy in the closing auction of the implementation session, the last IDX session on or before MSCI's
  implementation date (the auction the trackers sell into). In the harness: posted 09:00 WIB that session, bought at its
  close (idx_events.signal_session, entry_lag 1).
- Exit: a sell in the closing auction 20 sessions after the entry, or at the first later session where a sale is
  possible (the harness's exit rule: the name trades and is not locked at the lower limit). A name that stops trading
  before then is scored at its last traded close (EXIT_DATA_END, counted; optimistic for distressed names); a hold that
  would need a price after 2023-12-29 is INCOMPLETE and unscored.
- Execution: KOD's IDX harness, unchanged (lots of 100 shares, auto-rejection limits, decision-time capacity FILL-C with a
  10% participation cap, registry-verified corporate actions; a trade held across a rights issue or an unverified reset
  is not scored). Capacity is checked at IDR 40m per trade, the largest position the account takes (25% of IDR 160m).
- Costs: 0.15% buy and 0.25% sell (Stockbit-level, including levies and the 0.1% sale tax), as in every KOD IDX study.
- Benchmarks: cash (0%); each event's matched controls from the harness (200 draws from names in the same price band,
  liquidity, market-cap, volatility, momentum, drawdown and listing-age buckets, bought at the same close under the same
  plan; when fewer than 5 names share every bucket the harness drops features one at a time, down to same-session only,
  and the match level is reported), with every name MSCI added to or deleted from the MSCI Indonesia Standard or Small
  Cap index in that review excluded from the controls. Continuing constituents whose weights change at the same close and
  Micro Cap changes are not in the public lists and are not excluded.
- Account: each review, the slots are its deletions not skipped before the auction (lot, liquidity or capacity skips);
  each slot gets min(25%, 1/slots, IDR 40m / equity) of equity, so no position exceeds the size the harness checked; a
  slot whose trade is not scored stays in cash, as does the rest. Reviews never overlap, so the account compounds review
  by review from IDR 160m.

## 6. Stresses and descriptive outputs (declared)
- S1: entry at the close of the session after the implementation close (a missed auction).
- S2: one exchange tick per side added to the costs (the harness's tick_cost; matters for low-priced names).
- Descriptive only: holds of 5 and 60 sessions; results by deletion kind, by review and by match level; account curve;
  the account without its best review (the review with the highest mean net return removed entirely).

## 7. Pass/fail (frozen; discovery unless stated)
- G0 sample: at least 30 scored deletion trades with matched controls, from at least 6 reviews; else INCONCLUSIVE.
- G1 net edge: mean net trade return > 0 and its review-cluster bootstrap one-sided 95% lower bound > 0.
- G2 versus matched controls: mean excess (net minus the event's matched-control mean) > 0 and its review-cluster
  bootstrap one-sided 95% lower bound > 0.
- G3 account: ends above its start and its P&L without the 3 largest winning trades is > 0 (trades ranked by IDR P&L in
  the compounded account; the residual is the sum of the other trades' IDR P&L, not re-compounded).
- G4 stress: mean net trade return > 0 under S1 and under S2.
- G5 2023 screen: with at least 5 scored trades, their mean net return >= 0 (fewer: uninformative, flagged).
- **Verdict:** PROMISING only if G0-G5 all pass; INCONCLUSIVE if G0 fails; otherwise FAIL. PROMISING is a candidate for
  validation, never proof: it licenses a prospective paper log of the next MSCI reviews (Feb, May, Aug, Nov 2027 and any
  2026 review not yet implemented) with a kill rule, and asking the owner about reading the sealed IDX holdout once. FAIL
  or INCONCLUSIVE ends this rule (no other hold, entry or event set).
- Bootstrap clusters are reviews (8 in discovery), so the interval is wide; May 2020 holds 20 of the 46 discovery events.
  Where this text and the pinned code differ, `msci_deletion.py` governs.

## 8. Feasibility (counts only, before this protocol was frozen)
`FEASIBILITY.json` (capacity at IDR 40m): discovery 46 deletions, 46 mapped, 40 EXITED (5 skipped for liquidity, 1 not
traded), all 8 reviews with a scored trade; 2023: 14 deletions, 7 EXITED, 6 INCOMPLETE (the Nov 2023 hold would cross
into the holdout), 1 not traded. The first pass at IDR 10m (42 EXITED, 3 liquidity skips) is kept as
`FEASIBILITY_pass1_before_review.json`. No return was printed or saved in either.

## 9. Known limits
Development data with a small, clustered sample (8 reviews; May 2020 follows the COVID low, a strong rebound, which the
matched controls are there to absorb); closing-auction fills are modelled by the harness, not observed; between-review
MSCI changes are missing; Stockbit fees are the KOD IDX profile, not a measured statement; forward relevance depends on
MSCI's treatment of Indonesia (additions frozen since January 2026; reclassification to Standalone proposed, decision by
30 June 2027) and on the short-selling restart, which may let arbitrageurs pre-position.

## 10. Pre-freeze review (record)
Two independent reviewers checked the study before the freeze, without computing any return. Events and timing: all 132
event rows reproduce from the PDFs, counts match MSCI's summary rows, dates match the press releases and the lists, all
60 deletion name-to-code mappings were confirmed against independent sources, implementation sessions and the
control exclusion are correct; notes only. Code and specification: one blocker (the account sized positions up to IDR
40m while capacity had been checked at IDR 10m: fixed by checking capacity at IDR 40m and capping positions at it), one
should-fix (harness modules imported but not pinned: fixed by pinning them and the git tree of `idxsig/`), and notes
(slots fixed before the auction, review list, wording of controls, exit rule, holdout guard, survivorship, match
levels, EXIT_DATA_END, G3 definition, input reproduction, tests), all applied above.
