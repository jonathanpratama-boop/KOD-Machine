# Quant-grade roadmap (2026-10-20)

## Built and tested (this branch)
| Piece | Where | Status |
|---|---|---|
| Trial register and multiple-testing correction (Holm, BH, Bonferroni hurdles) | idxsig/multiple_testing.py, research/QUANT_GRADE/trials/ | done; 19 counted tests, 285 variants, none significant |
| Rank-IC, walk-forward ridge combination (embargoed), Newey-West statistics, factor alpha | idxsig/quant.py | done; 10 unit tests, planted-signal and no-lookahead tests |
| Market-impact cost model and break-even capacity | idxsig/quant.py | done; assumed constants (5 bp half-spread, impact 0.7) |
| Seven-feature engine run with an independent verifier | research/QUANT_ENGINE_2005_2019/ | done; verified; result FAIL, NON-EVIDENCE |

## Not doable without you (nothing here has been bought, requested or run)
1. **Survivorship-free prices and point-in-time fundamentals.** This is the largest gap: every US result on this branch
   uses today's listings only. Needed: daily prices including delisted and renamed securities with correct historical
   identities, and fundamentals as they were known on each date. Vendors that sell this at retail scale exist
   (for example Norgate Data, Sharadar via Nasdaq Data Link, or CRSP/Compustat through a university); prices, terms and
   redistribution limits must be checked before any purchase (an unverified estimate is tens of dollars a month for
   prices). Spending needs your explicit authorisation; I will not buy or sign up for anything.
2. **Measured spreads and intraday bars.** Needs the Alpaca keys or equivalent (see research/INTRADAY_PROBE: probe_v2.py is written
   and corrected but has not been run) and eToro account facts (entity, commission in the trade ticket, API eligibility).
3. **Live paper trading against real quotes.** The paper ledgers record decisions and score them on daily bars. A quote-aware
   version must store the bid and ask at decision time and fill against them. It needs a quote source with a key (point 2)
   and your decision on which broker's quotes count as executable. No real order is ever placed.

## Standing rules for the next test
- Pre-register before looking; run once; add a file to research/QUANT_GRADE/trials/ either way.
- The primary result must reach t >= 3.0 (3.6 where many plans or models are searched), after costs and factors.
- A survivor-only dataset can fail a test but cannot confirm one; label it.
- Candidate for its own pre-registered test: short-term (1-month) reversal, which was the only per-feature IC beyond a
  seven-way Bonferroni bar in the engine run (IC -0.023, NW t = -3.45). It is a known microstructure effect, usually
  concentrated in small, expensive-to-trade stocks, and it was not a gate, so it is a lead, not a result.
