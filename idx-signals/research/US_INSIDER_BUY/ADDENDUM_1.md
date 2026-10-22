# Addendum 1 (2026-10-22): download address

PROTOCOL.md gave the zip address as `.../structureddata/data/form-345/<quarter>_form345.zip`; it returns HTTP 404. The SEC page lists them at
`https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/<quarter>_form345.zip` (links for 2020q3, 2020q4, 2021q1 and 2023q4 confirmed on the page). `fetch_form345_v2.py` overrides `ib_lib.URL` (ib_lib.py is a committed record and is not edited) and is what was run. Nothing else changes; no record had been downloaded and no return read.
