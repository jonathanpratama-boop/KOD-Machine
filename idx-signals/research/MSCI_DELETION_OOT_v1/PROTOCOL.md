# MSCI_DELETION_OOT_v1: out-of-time replication of MSCI_DELETION_v1 on the reviews after the sealed IDX holdout

Written 2026-11-01, after MSCI_DELETION_v1's one run (PROMISING on development data, 2019-2023) and before any return of
this replication was looked at. Simulation only. Code: `oot.py` (`--feasibility`, `--freeze`, `--run`), events:
`collect.py` -> `build_events.py` -> `events_all.csv` (MSCI's own 2025-2026 lists, `ticker_map.csv`). `protocol.json`
pins these, all of MSCI_DELETION_v1's pinned files and the git tree of `idxsig/`.

## 1. Why this test, and why it is allowed
MSCI_DELETION_v1 passed its frozen gates on 2019-2023 development data, which makes it a candidate for validation, not
proof. Its gain is concentrated in the 2019-2020 reviews. This is the one out-of-time replication of the frozen rule on
data never used for this question. The window, 2025-02-24 .. 2026-10-06, is the post-holdout segment of the same pinned
IDX panel. It is not sealed: KOD used it before for other questions (IDX_INSIDER_NEWS_OOT, MOVERS_NOW_v1), so its prices
are not pristine, but no MSCI-deletion return has been computed on it. The sealed IDX holdout (2024-01-02 ..
2025-02-21, which holds the 2024 reviews) is not evaluated: no 2024 review is fetched, and every entry falls after it.
Matching features at the first out-of-time sessions use trailing prices from inside the sealed window, as in
IDX_INSIDER_NEWS_OOT; no return or outcome inside it is computed.

## 2. The rule (unchanged)
Exactly MSCI_DELETION_v1's: names MSCI deletes from the MSCI Indonesia Standard index (exits and downward migrations) or
Small Cap index (exits), bought in the closing auction of the implementation session, sold in the closing auction 20
sessions later (or the first later session where a sale is possible); KOD's IDX harness with capacity checked at IDR 40m,
0.15%/0.25% costs, registry corporate actions; matched controls with every name MSCI changed in the review excluded;
v1's account (slots fixed before the auction, each at most 25% of equity and IDR 40m, cash otherwise, from IDR 160m);
stresses S1 (entry one session later) and S2 (one tick per side); descriptive holds 5 and 60. The code that does all of
this is v1's frozen module, imported unchanged.

## 3. Events
Seven scheduled reviews, Feb 2025 .. Aug 2026 (implementation sessions 2025-02-28 .. 2026-08-31). Parsed from MSCI's
public lists with a page-break-aware parser (blocks can continue after a page footer); every list's counts match MSCI's
summary row, and the parser reproduces all 34 v1 lists exactly. 51 deletions (36 Small Cap exits, 8 Standard exits, 7
downward migrations; one upward migration excluded). May 2026 holds 19 (MSCI's free-float treatment of several
large holders, after it froze Indonesian additions in January 2026). WIJAYA KARYA is listed as a Small Cap deletion in
both Feb 2025 and May 2025: IDX suspended WIKA on 18 Feb 2025 (bond and sukuk payment default), between MSCI's
announcement and implementation, so MSCI postponed the deletion under its suspension rule and announced it again in May;
WIKA was still suspended then. Both events stay as MSCI published them; the stock did not trade on either implementation
date, so the harness cannot score them (SKIP_NOT_TRADED). MSCI also cancelled one Nov 2025 addition (TINS, on IDX's
full-call-auction board) after publishing the list; no deletion's classification uses it.

Names are mapped to IDX codes by hand. An independent pre-freeze check confirmed all 77 rows (52 deletions, 25
additions) against Indonesian news of each review (Bisnis, Katadata, CNBC Indonesia, Fortune IDN, RCTI+ and others),
re-parsed all 21 PDFs with its own parser (counts match MSCI's summary rows, rows equal events_all.csv exactly), and
confirmed the dates: no code changed. The truncated MSCI name BANK PEMBANGUNAN DAERAH is BJBR (not BJTM); MNC LAND and
MNC TOURISM INDONESIA are both KPIG (renamed in June 2025).

## 4. Pass/fail (frozen)
- O0 sample: at least 15 scored deletion trades with matched controls, from at least 4 reviews; else INCONCLUSIVE.
- O1: mean net trade return > 0.
- O2: mean excess over matched controls > 0.
- O3: v1's account ends above its start.
- **Verdict:** CONFIRMED if O0-O3 all pass; CONFIRMED_STRONG if also the review-cluster bootstrap one-sided 95% lower
  bound of the mean excess is > 0; INCONCLUSIVE if O0 fails; otherwise NOT_CONFIRMED. One run, no variants. A
  NOT_CONFIRMED result means the development finding did not replicate and the rule is not taken further. A CONFIRMED
  result licenses a prospective paper log of the next MSCI reviews with a kill rule; it is still not proof of future
  profit (MSCI's treatment of Indonesia is changing: additions frozen since January 2026, reclassification proposed with a
  decision by 30 June 2027; IDX short selling restarted in October 2026 for a few names).

## 5. Feasibility (counts only, before the freeze)
`FEASIBILITY.json`: 51 deletions, all mapped to the panel; 46 EXITED, 2 not traded, 2 locked at the upper limit at
entry, 1 skipped for liquidity; all 7 reviews have a scored trade. No return was printed or saved.

## 6. Known limits
Yahoo-sourced prices after the IDX mirror ends (the panel's post-2025-02-21 rows), modelled closing-auction fills,
between-review MSCI changes missing, a sample of 7 reviews (clusters), development-era survivorship does not apply here
(the panel lists delisted names in this segment as far as Yahoo carries them; unverified).
