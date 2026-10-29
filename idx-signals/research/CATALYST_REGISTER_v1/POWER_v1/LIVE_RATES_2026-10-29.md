# Live sensor rates, read 2026-10-29 (read-only; no ledger written; `live_rates.py`)

EDGAR as of 2026-10-29 ~08:00 UTC. These days are before FORM4's window (it starts with filings dated 2026-10-29), so
nothing here is sealed or scored; this checks POWER_v1's assumed event rates against the live feeds.

| Filing date | Form 4 filings | Purchase events (FORM4 rules) | In the US scan universe | Sharp (top exec or USD 100-500k), before the dilution and routine rules |
|---|---|---|---|---|
| 2026-10-26 | 288 | 5 | 5 | 3 |
| 2026-10-27 | 335 | 9 | 8 | 3 |
| 2026-10-28 | 236 | 10 | 10 | 7 |

- FORM4: about 8 events a day in the universe, about 2,000 a year at 252 sessions, above POWER_v1's 1,482.
- FORM4_SHARP before its two abstention rules: about 4.3 a day, about 1,100 a year, above the 500 assumed.
- 8-K Item 3.02 filer entries in the current feed: 16 on 2026-10-27, 8 on 2026-10-28 (before the universe filter).
- Original Schedule 13D in the current feed: 3 on 2026-10-28.

Three days are a small sample; the register's own batches will give the real rate from 2026-10-30.
