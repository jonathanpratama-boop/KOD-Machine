# MSCI_DELETION_v1: independent verification of the one run (2026-11-01)

Two independent auditors with fresh context checked `run/` after it completed. Neither modified a repo file or parsed
any IDX panel row dated 2024-01-02 or later (both dropped 600,920 rows after 2023-12-29 by date string before parsing,
matching RESULT.json). **Verdict of both: CONFIRMED, no discrepancy.** Scratch work: `/tmp/verify_msci_trades/`,
`/tmp/verify_msci_audit/`.

## 1. Trades against raw closes and an external source
- All 23 pinned files match protocol.json; protocol.json, panel and registry hashes match RESULT.json.
- All 141 scored trades (primary, S1, S2; 40 discovery + 7 screen each) recomputed from the pinned panel's closes:
  entry and exit dates 141/141, prices exact, net returns within 5e-16 using the harness formula
  net = F x exit/entry x (1 - 0.0025 - tick_out) / (1 + 0.0015 + tick_in) - 1. No exit rolled, no registry action
  inside any hold, no EXIT_DATA_END trade. Every entry session is MSCI's implementation date (an IDX session in all 11
  deletion reviews).
- Every daily close in every event window (entry - 45 days .. exit + 10 days) matches Yahoo Finance (.JK) on 3,001
  ticker-days for 53 tickers: same sessions, constant per-ticker ratio, so no unadjusted corporate action. The largest
  winners (KREN 69 -> 142, SSMS 690 -> 1,285, BBTN 760 -> 1,240, KRAS, BWPT, TINS, ISAT, DMMX) are real prints; news
  confirms the KREN (cooling-down suspension lifted, buyback) and BBTN (Tapera regulation) paths. SRIL's 2020 closes
  could not be checked externally (no reachable source carries them).
- No winner closed at the lower limit on entry; seven other entries did (buying into a lower-limit lock is fillable).
  IDR 40m was at most 0.56% of the entry-day traded value for the winners; the most crowded trade was PPRO (11.6%,
  Rp50 floor, net -0.40%). Closing-auction volume itself is not in daily data.
- Cash dividends are excluded by design (price returns), which understates some trades (e.g. PTBA's June 2020 dividend
  of 16.8% of the entry price).

## 2. Accounting, statistics and gates
- 513 summary values recomputed from the trade files, 0 mismatches; both review-cluster bootstraps reproduce with the
  frozen seed; every account figure reproduces (discovery IDR 160m -> 262.81m, drawdown at review exits -4.18%, P&L
  without the top 3 winners +IDR 42.21m; without the best review, May 2020: IDR 215.05m).
- Gates G0-G5 recomputed: all PASS; verdict PROMISING mechanically correct. The G1 lower bound does not depend on the
  seed (exact bootstrap over all 8^8 resamples: +1.34%; 50 other seeds: +1.04% .. +1.57%).
- protocol.json's G3 text ("equal weight per review, at most 25% per name") omits the code's IDR 40m cap and
  decision-time slots; G3 passes under every plain reading as well (end equity IDR 253m .. 272m).
- Label note: the 2023 account reports reviews_traded = 4 although Nov 2023 had slots and no scored trade.

## 3. Post-hoc diagnostics (labelled as such; they do not change the frozen verdict)
- **It is a 2019-2020 effect.** Nov 2019, May 2020 and Nov 2020 (24 trades): mean net +24.2%, median +17.5%, excess
  +17.8%. The 2021-2022 reviews (16 trades): mean net -1.3%, median -2.0%, excess +1.1% (lower bound -1.6%).
- Without May 2020: net +6.0% (median -0.5%), excess +4.4%; G1's lower bound would be negative and G3 would fail.
- Without the 3 largest trades: net +8.3%, excess +5.2%. Winsorised at 10/90: net +10.6%.
- Treating each review as one observation: net p = 0.051 (sign-flip 0.078), excess p = 0.033; 5 of 8 reviews have
  positive mean excess.
- Not market beta: the equal-weight IDX market rose +6.3% over the 2019-2020 windows against +24.2% for the deletions;
  beta-adjusted, about +17%.
- The 2023 screen's +8.9% is one stock (DMMX +69%); the other six trades average -1.1%.

**What a skeptic should conclude:** the arithmetic, the data and the verdict are sound, but the evidence is effectively
one regime (the 2019-2020 reviews, above all the mass May 2020 deletion after the COVID low). The finding is a
candidate, and the decisive test is the out-of-time replication (MSCI_DELETION_OOT_v1), frozen before it is run.
