# VIX_BASIS_v1: independent verification of the one run (2026-11-01)

Three independent verifiers with fresh context, each with their own code, re-derived the run from the raw Cboe files.
No repo file was modified. Scratch work: `/tmp/verify_vix_signals/`, `/tmp/verify_vix_account/`, `/tmp/verify_vix_bench/`.

**Verdict: VERIFIED. NOT_CONFIRMED reproduces exactly and is not an artefact of a bug or bad data.**

## What was checked

- **Inputs.**
  - All 220 raw files match the manifest's sha256.
  - The 6 pinned files match `protocol.json`.
  - `RESULT.json` records the hash of `protocol.json`.
  - No date of 2024-01-01 or later, and none on 2015-04-03, appears in any of the 32 run files (43,696 date cells).
- **Data handling.** All 8 cleaning counts were recomputed exactly with independent parsers: 1,485 sealed rows, 488
  zero settlements replaced by the close, 336 zero rows, 2,426 rescaled, 9 Good Friday 2015 rows, 529 idle, 1
  implausible, and 3,890 VIX days that are not VX sessions.
  - All 216 full contracts end on Cboe's rule date. The Good Friday set is 2008-02, 2014-03, 2019-03 and 2022-03.
  - Switching the idle or plausibility filter off leaves the front and days-to-settlement unchanged on every
    2006-2023 decision day.
  - The 2007-03-26 rescale is continuous: F/VIX is 1.03 on 2007-03-23 and 1.02 on 2007-03-26.
- **Signals and trades.**
  - Discovery: 2,517 decision days, 655 short-signal days, 121 contracts used. Validation: 2,012 days, 97 contracts.
  - Every primary segment matches bit for bit: 193 in discovery, 196 in validation. That covers dates, contract,
    prices (all raw settlements), lag, 5-session exits, continuation flags, costs, notional and P&L.
- **All 8 arms in both windows.**
  - Re-simulated by two verifiers: 1,959 segments and 22,645 daily equity marks match.
  - All 220 summary items match within 1e-10, including every calendar-year return and the bootstrap lower bounds
    bit for bit.
  - The B1, D1 and R1 rules hold.
- **Benchmarks.** The SPX price index returned +61.09% in discovery (max drawdown -56.78%) and +136.99% in validation
  (-33.92%). Both are exact.
- **Gates.** All 11 reproduce.
  - Discovery D0-D6 pass: 106 positions; account 19,134 (P&L without the top 5 is 4,838); mean +3.21% with a lower
    bound of +1.20%; drawdown -19.1%; S1 16,534, S2 20,063; N1 17,289, N2 16,745; 9 of 10 years up.
  - Validation V1-V3 pass: account 11,362, mean +0.79%, drawdown -16.9%.
  - **V4 fails**: with doubled costs the validation account ends at 9,784.20, USD 215.80 below its start.
- **Adversarial.** The 5 worst validation positions are real events: Sep 2016, May 2019, Omicron in Nov 2021, Apr 2022,
  and Jun 2016 before Brexit. So are the 5 best. No bad print was found in 1,309 traded prices or 4,913 near-contract
  settlements; the only flags are Feb 2018, which is genuine, when the primary arm was flat.

## Findings recorded, not changing the verdict

1. **The verdict is fragile to one convention.**
   - The code counts days to settlement as the sessions after the decision day, up to and including the settlement
     day. That matches the literature's "business days until settlement", but PROTOCOL section 2 does not spell it
     out.
   - Counting one session more would have given V4 PASS (S1 validation 10,027) and a CONFIRMED verdict. Counting one
     session fewer would have made the primary validation mean negative and its drawdown about -36%.
   - The frozen code governs and the verdict stands. This sensitivity is itself evidence that the post-publication
     edge is marginal.
2. **Validation is weak beyond what V1-V4 test.**
   - The bootstrap lower bound of the mean is -1.16%, P&L without the 5 best positions is USD -1,373, only 4 of 8
     years were up, and the payoff ratio is 0.91.
   - Even a V4 pass would have rested on a positive mean alone. Break-even cost is about 0.12 points per side, against
     the 0.065 assumed.
3. **Float ties at the threshold.** An exact roll of 0.10 on 2011-05-31 counts as "above 0.10" in binary floating
   point, so the discovery short-signal count is 654, not 655. No primary trade changes. At 0.05, two float ties opened
   2 extra N1 discovery positions (end equity 17,289 against 17,227 with exact arithmetic); D5 still passes.
4. **R1 (descriptive).** The continuation count's numerator uses equity marked at the same day's settlement. Marking at
   the previous settlement changes one discovery count (16,185 to 16,180). PROTOCOL section 6's "0, 1 or 2 contracts"
   holds only at the starting equity: R1 held 3 contracts in 26 discovery segments.
5. **Cosmetic and immaterial.**
   - Three settlements used in trades are 0.005-0.015 points below the day's reported low; this fits settlement
     rounding.
   - B1's last validation segment is a zero-length continuation closed at the window end.
   - Discovery's deepest drawdown (-19.1%) is still open on its last session (2015: -15.1%).

## What the result means

Selling VIX futures in contango earned a real premium in the paper's own sample and through 2015: 9 of 10 years up,
+91% at 20% notional, drawdown -19%. After publication the same frozen rule earned +13.6% over eight years. It failed
with doubled costs, beat cash only narrowly and trailed holding the S&P 500 by a wide margin. Either the premium has been
largely arbitraged away since about 2016, or what remains needs a hedge or a cheaper venue this test did not have. The
other arms are not candidates: picking the best one now, for example the 0.05 threshold at +57%, would be a new
hypothesis chosen on validation data.
