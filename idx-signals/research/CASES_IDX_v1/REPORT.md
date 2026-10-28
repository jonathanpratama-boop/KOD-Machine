# CASES_IDX_v1 report: twenty random IDX +30% moves, and what was visible three sessions before

Descriptive case study (not a counted test). Protocol, selection rule and classes committed before any case was drawn;
cases drawn at random (seed 20261027) from the 1,113 fast-rise episodes of 2021-22; evidence packs from the archived
exchange data; news searched by four independent researchers, each item kept with its URL and publication date
(`news/`). Classification in `classification.json`.

## Answer: 0 of 20 had a usable public tell three sessions before the move

| Class (frozen rules, in order) | Cases | Note |
|---|---|---|
| Telegraphed (explaining news public by J-3) | 0 | none found in any case |
| News shock (explaining news J-2 to J) | 1 | TRIS: strong Q3 results, reported on the day of the jump |
| Sector sympathy | 15 | the rule is uninformative: it fires on 2-66% of ordinary sessions (most sectors 25-35%) |
| Quiet build-up (volume or price flag at J-3) | 2 | SRAJ, SUPR; the volume flag fires on 28% of ordinary name-days, and SUPR's volume came while it fell 26% |
| Unexplained | 2 | SAFE, MTSM |

Read without the loose sector rule, the news side is clearer:

- **13 of 20: no company-specific explanation found at all**, before, on or after the move: NZIA, POLA, NICK, SAFE, CSIS,
  GLOB, MTSM, PGUN, SQMI, TNCA, SUPR, PTIS, BBRM. Mostly small, thin stocks; several carried exchange watch flags
  (SQMI negative-equity "E" notation, PTIS an unusual-market-activity notice issued during the move, MTSM suspended weeks
  earlier, SUPR a 0.04% free float).
- **3 of 20: the price moved before the explanation became public.** PLAN rose two days before signing a hotel
  management deal with Artotel, reported three weeks later. MMLP rose 69% in three days with "catalyst unknown"; a GoTo
  investor rumour surfaced a fortnight later, and the underlying stake change from May 2021 was not in public news.
  BEBS rose before its Q1 results (+523% profit) were reported.
- **3 of 20: explained on the day.** TRIS (results), BBYB (a digital-bank sector rebound) and BRIS (a same-day
  "digital transformation" narrative). SRAJ had rights-issue news two days before, which is not a plausible bullish
  catalyst.
- **0 of 20 corporate-action artefacts.**

With 20 cases, each share is known to about plus or minus 20 points.

## What it means for the machine

1. **Public information does not lead these moves.** Nothing was public three sessions out; at most it appeared on the
   day. This is the same finding as E9 and the Zealand case, now on a random sample of Indonesian moonshots.
2. **The dominant type is the unexplained move in a thin stock**: two thirds of the sample. That is the profile of
   coordinated trading ("gorengan"), where the only early trace would be who is buying, by broker. Test 30 showed the
   exchange's aggregate flows (foreign, queue, block) do not carry it. Broker-level data might.
3. **In three cases the price knew first.** That is information leaking ahead of disclosure, which by definition no
   public data shows in time.
4. **No new detector is justified by this sample.** The one input left that matches the dominant type is the broker
   summary (which broker accumulates before the move), and it needs the owner's Stockbit exports.

## Limits

News search reaches what is still online and indexed; "none found" is not proof of none (several pages were paywalled
or blocked). The classification of "plausibly explains" is judgement, recorded per case. The sector lists are a
2025-02 snapshot.
