# Instructions for labellers and reviewers (IDX_INSIDER_NEWS)

You are labelling Indonesian business-news items for a research study. For each item you get an item number, a title, the posting
time (WIB) and the first 700 characters of the article. Answer **only from the item text**: do not search the web, do not use what you
know about the company, its price or what happened later.

## Classes (exactly one per item)
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

## For each item return
- `item`: the item number you were given.
- `cls`: one of the classes above, exactly as written.
- `issuer_ticker`: the four-letter IDX code, upper case, of the company whose shares are bought (as printed in the title or body), or
  `null` if it is not printed or not clear. Use `null` for classes where no single company's shares are bought.
- `buyer`: at most twelve words naming the buyer or the buyer's role as the article states it (or `null`).
- `transaction_date`: the date the article gives for the purchase itself, as text (for example "9 Mei 2022"), or `null`.
- `confidence`: `high`, `medium` or `low`.

Return a JSON list with one object per item, nothing else, keys exactly `item`, `cls`, `issuer_ticker`, `buyer`, `transaction_date`,
`confidence`. Every item must appear once.
