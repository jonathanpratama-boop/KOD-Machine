# MSCI_DELETION_OOT_v1: independent verification of the one run (2026-11-01)

One independent auditor with fresh context checked `run/`. No repo file was modified; only panel rows 2025-02-24 ..
2026-10-06 were used (re-drawing the harness's controls necessarily rebuilds its trailing features, as the harness
does). Scratch work: `/tmp/verify_msci_oot/`. **Verdict: VERIFIED; NOT_CONFIRMED reproduces and is robust.**

- **Trades.** Every scored trade in the primary (46), S1 (45) and S2 (46) files recomputes from panel closes with
  identical dates and prices (net within 4.4e-16); no registry action in any hold; the three rolled exits (MDKA, GOTO,
  KPIG, held by lower-limit locks) reproduce under an independent rule. Entry sessions equal MSCI's implementation dates
  except May 2025, where IDX was closed on 29-30 May and the harness correctly used 28 May (tracker volume peaks there).
  No entry falls on or before 2025-02-21. WIKA (suspended), BREN and CUAN (locked limit-up at the implementation close)
  are correctly unscored.
- **Prices.** For all 51 deleted names the panel equals Yahoo on 382 of 382 sessions (a consistency check only: these
  rows come from Yahoo). Dated news quotes independently confirm GOTO, APIC, TCPI, FILM, UNVR, AMRT and DSSA. GOTO's
  -40% is real: it sat at the Rp50 floor from May 2026 until IDX lowered the floor to Rp1 on 28 Sep 2026 in the middle of
  the hold, then fell through daily lower-limit locks to 30. Some trade-date closes (APIC 610, TCPI 2210/1620, FILM
  800/625, DSSA 492/795) are confirmed only by Yahoo.
- **Control-pool artifact.** A partial Yahoo adjustment of COCO on 2026-06-29 enters 42 May 2026 control draws at
  -70.7%; it inflates the mean excess by about 0.3 points (+4.53% vs +4.23%). O2 and the verdict are unaffected.
- **Statistics, account, gates.** All 179 reported numbers reproduce; the bootstrap reproduces exactly and agrees with an
  independent one; the account reproduces (IDR 160.0m -> 129.52m, -19.05%; P&L without the top 3 winners -IDR 45.45m).
  Gates: O0 PASS, O1 FAIL (-4.19%), O2 PASS (+4.53%), O3 FAIL; NOT_CONFIRMED. Robust: mean net -3.39% without GOTO,
  -2.86% without GOTO and KPIG; the account still ends below its start without Aug 2026.
- **Post-hoc (labelled; not part of the protocol).** The equal-weight liquid IDX market (median daily value >= IDR 1bn)
  fell -8.07% net of the same costs over the trade windows, against the deletions' -4.19%: market-adjusted +3.89% mean,
  +4.80% median, 61% of trades ahead (+1.85% against the JCI). The relative gain is concentrated in Feb 2025, Feb 2026
  and May 2026; deletions lagged the market in May 2025, Aug 2025, Nov 2025 and Aug 2026. For an unleveraged spot buyer
  the falling market more than offset it.
