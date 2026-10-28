# IDX_DILUTION_v1 ERRATA_1 (2026-10-27, after the recorded run)

A per-trade review of the 15 scored 2023 trades (hold 60) found:

1. **The split filter leaks.** IDX updates listed_shares 9 to 15 sessions after a split or stock dividend takes effect, so the same-day price test in
   dl_lib.py cannot see the price reset. Two of the 15 trades are not issuance: IMPC (11:1 stock split, registry VERIFIED_CORROBORATED,
   2023-06-19) and FMII (stock dividend, registry VERIFIED_CORROBORATED, 2023-07-07). Their excess was +1.7% and +14.1%, so the leak worked
   against the recorded result, not for it. Without them the 13 remaining trades average about -17%; this is descriptive only and does not
   replace the recorded verdict. The same leak is likely present in the 2019-2022 exploration and was not checked.
2. **The losses are price moves, not artifacts.** None of the 12 losing trades had an IDX reference-price reset inside its holding window, so no
   unadjusted corporate action produced them.
3. **Concentration.** 12 of 15 trades lost against their controls. Dropping the two worst trades moves the mean from -13.7% to -9.0%; dropping the
   two best moves it to -20.6%.

A corrected event rule (exclude any rise within 20 sessions after a registry split or stock dividend) is a new experiment with its own protocol,
not a rerun of this one.
