# IDX_INSIDER_NEWS: labelling and audit procedure

Written 2026-10-21 and committed before any article has been labelled and before any price or return is computed for these
events. Historical research only; no orders. This file fixes what the labellers see, what they decide, and the audit that
decides whether the labelled events are good enough to study (the same discipline as `research/E10/AUDIT_PROCEDURE.md`).

## What the study is about (for context; the protocol itself is written after the audit)
Indonesian business news (EmitenNews) reports, almost daily, that someone "borong" (bought up) or "serok" (scooped) shares of a
listed company. Some of these are open-market purchases by the company's own directors, commissioners or controlling
shareholders; others are option exercises, rights subscriptions, fund flows, stake purchases between companies, sales or
denials. Whether the first kind is followed by return that an ordinary buyer could still collect is the question. Reading these
in Bahasa and telling them apart is the part a language model can do at scale.

## Candidates and what a labeller sees
`articles.csv.gz` (`fetch_articles.py`): articles whose slug has a purchase-like word and an IDX ticker code, 2021-2023 (the
IDX holdout from 2024-01-02 is never touched). A labeller sees, per article: an item number, the title, the posting date and
time (WIB) and the first 700 characters of the body. **No price, no return, no ticker list, no later fact.**

## Classes (exactly one per article)
- `INSIDER_BUY`: a director, commissioner, controlling shareholder (*pengendali*, *pemegang saham pengendali*), or a person or
  company the article presents as belonging to or controlled by them (family, holding company, "bos", "taipan"), bought shares
  of **the listed company named in the headline**, in the market or in a negotiated/block deal, with their own money. Repeat
  buying ("lagi", "kembali") counts. The article need not give the price.
- `OPTION_OR_RIGHTS_EXERCISE`: shares obtained by exercising MESOP/ESOP/management options or warrants, subscribing to a rights
  issue (*HMETD*, *right issue*), a share award, or at a stated discount to market through such a programme, even if the buyers
  are directors.
- `OUTSIDE_INVESTOR_BUY`: a person or institution that is not presented as management or controller (a fund, bank, securities
  firm, foreign investor, a named famous investor, a corporate investor that is not the controller) buys shares of the company.
- `COMPANY_ACQUIRES_STAKE`: a listed company or group buys or raises a stake in another company (an acquisition, a subsidiary,
  an associate), where the headline is about the deal rather than a person buying the listed company's shares.
- `BUYBACK`: a company buys back its own shares (or asks approval to).
- `SELL`: a sale, disposal, divestment or placement of shares by anyone.
- `DENIAL_OR_RUMOR`: a denial, clarification or rumour about buying or selling.
- `MARKET_FLOW`: aggregate buying or selling across stocks (foreign net buy, "top gainers", recommendations, market wrap-ups).
- `OTHER`: anything else.

## What else a labeller returns
`issuer_ticker`: the four-letter IDX code, upper case, of the company whose shares are bought (as printed in the headline or
body), or `null` if it is not printed or not clear. `buyer`: at most twelve words naming the buyer or the buyer's role as the
article states it. `transaction_date`: the date the article gives for the purchase itself (as text, e.g. "9 Mei 2022"), or
`null`. `confidence`: `high`, `medium` or `low`. Labellers are told not to search the web, not to use any outside knowledge of
the company, and to answer from the item text only.

## The audit (decides GO)
`audit_sample.py` (seed 20261022) draws 45 items the labeller called `INSIDER_BUY` and 45 items it called anything else (uniformly
among the other classes' items). Two reviewers, separate model sessions that share no context with the labellers or with each
other, label the 90 items from scratch with the same instructions and **without seeing the labeller's class**.
`audit_score.py` then reports, per reviewer:
- **precision** = among the 45 items the labeller called `INSIDER_BUY`, the share the reviewer also calls `INSIDER_BUY` with the same
  `issuer_ticker`;
- **missed** = among the 45 other items, the share the reviewer calls `INSIDER_BUY` (a recall warning; informational);
- agreement (Cohen's kappa) between the reviewer and the labeller over all 90 items, and between the two reviewers.
**GO** only if the lower reviewer's precision is at least 85% **and** at least 150 labelled `INSIDER_BUY` events (confidence high or
medium, ticker present) fall in 2021-02-15 .. 2023-11-30. A labelling round that fails the audit may be repeated with a revised
instruction only if the revision is committed first and a new audit sample is drawn; every round is kept.
