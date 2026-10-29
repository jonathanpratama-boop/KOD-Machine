# UMA_IDX_v1: exchange-flagged IDX stocks (Unusual Market Activity), as reported by the press

`collect.py` (run once, 2026-10-29) reads every EmitenNews article with "uma" in its URL (199 articles, 2019-2026) and keeps
the stocks the article names as codes in its headline or URL: **106 labels on 95 stocks** (`labels.csv`, hashed in
`COLLECT.json`). A random spot-check of ten labels found all ten correct.

- **Why it matters:** UMA is the exchange itself flagging a stock's move as abnormal: a free, exchange-made label of IDX
  pumps and dumps. idx.co.id refuses this server (HTTP 403), so the press is the route.
- **How small it is:** the press reports a subset of IDX's notices; 106 labels are enough for description and a kill test,
  not for a learner.
- **It is ending.** EmitenNews (30 October 2026): from early November 2026 IDX stops suspending stocks and issuing UMA;
  it will suspend the specific securities accounts suspected of violations and announce publicly when an investigation
  starts. These labels are history; the live successor is that investigation notice. The same announcement removes
  High Shareholding Concentration (HSC) stocks from the IHSG weighting from November: a dated index catalyst.
- **Consequence for the paper plans:** the IDX plan's "a suspension or UMA notice before the entry close" condition will
  refer to notices that no longer exist; account suspensions and investigation notices are its replacement.

Not yet used in any test. A study on these labels is frozen separately before any price is read.
