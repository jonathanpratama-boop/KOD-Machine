# IDX regular-market auto rejection spec, pass A (as of 2026-11-09)

Caveat: the primary PDFs (idx.co.id decree texts) returned HTTP 403. The only official primary text read was the IDX web page https://www.idx.id/en/products-services/trading-hours-and-mechanism/ (no date shown on page; it cites Kep-00158/BEI/10-2026, so it reflects the post-2026-10-20 state). Everything else is news / law-firm / broker secondary reporting. No decree text was read.

## 1. Timeline (WIB trading days, inclusive). Boards: Main / Development / New Economy ("MDN") unless stated

| Period | Rp1-10 | Rp11-14 | Rp15-200 | >200-5,000 | >5,000 | Min price | Confidence |
|---|---|---|---|---|---|---|---|
| through Fri 2026-09-25 | n/a (min price 50) | n/a | (Rp50-200) ARA 35% / ARB 15% | 25% / 15% | 20% / 15% | Rp50 | medium (news only; Kep-00003/BEI/04-2025 of 2025-04-08 is the revoked prior decree) |
| Mon 2026-09-28 to Fri 2026-10-16 (Kep-00136/BEI/09-2026, dated 2026-09-21) | ARA Rp1 / ARB Rp1 | ARA 35% / ARB 15% | 35% / 15% | 25% / 15% | 20% / 15% | Rp1 | high (many sources agree; Katadata, Jakarta Globe, BCA Sekuritas/IQPlus, Pluang) |
| Mon 2026-10-19 only (Kep-00157/BEI/10-2026) | Rp1 / Rp1 | 35% / 7% | 35% / 7% | 25% / 7% | 20% / 7% | Rp1 | medium-high (Bernama/The Star, Republika, Tempo, Pluang). Effective date 19 Oct per The Star, Bareksa, Pluang |
| Tue 2026-10-20 to Thu 2026-12-31 (Kep-00158/BEI/10-2026, replaces 00157) | Rp1 / Rp1 | 35% / Rp1 | 35% / 7% | 25% / 7% | 20% / 7% | Rp1 | high for the table (IDX page + Bareksa + Republika). Valid "until 31 Dec 2026, subject to evaluation" |
| 2027-01-01 onward | announced in Sept: symmetric ARB = ARA (Rp1-10 stays Rp1; 11-200: 35/35; 200-5000: 25/25; >5000: 20/20) | | | | | Rp1 | LOW / unresolved: announced before the October changes; no official post-2026 text found; Pluang says BEI has not confirmed |

Other boards (from IDX page, current state, from Kep-00158 era; date ranges not independently dated):
- Acceleration and Special Monitoring/Watchlist boards: Rp1-10 ARA Rp1 / ARB Rp1; above Rp10 10% / 10%. The Oct changes did not touch these (Bareksa: "follow their own Auto Rejection rules").
- ETF and REIT (DIRE): same as MDN table, without the volume condition (IDX page). Whether the 7% ARB / Rp11-14 Rp1 applies to ETF/REIT: page says "same as Main Board structure"; not independently confirmed.
- DINFRA (Kep-00137/BEI/09-2026, Rule II-O): before: min Rp50, 10%/10%. From 2026-09-28: Rp1-10 Rp1/Rp1, above Rp10 10%/10% (Katadata, Media Indonesia). IDX page: same as Acceleration.
- Warrants (IDX page): first day order >= underlying last price; afterwards Rp1-9 upper Rp10, none lower listed; >9-200 50%/50%; >200-5000 40%/40%; >5000 30%/30%. Effective-date history unknown.

Tick (price fraction) table, IDX page citing Kep-00158/BEI/10-2026: <Rp200: Rp1 (max step 10); 200-<500: Rp2 (20); 500-<2,000: Rp5 (50); 2,000-<5,000: Rp10 (100); >=5,000: Rp25 (250). Invezgo repeats it. Whether the table was the same before 2026-09-28 is not verified by a dated source (no sign of change in any article). Page also says: "The maximum price step should not exceed the percentage of Auto Rejection limit" and step values are fixed for the trading day, adjusting next day if the close falls in a different range.

## 2. Rounding and reference price
- Reference price, IDX page: "The Reference Price used to set the upper and lower limit ... determined based on: Previous price; Theoretical price of corporate action result; initial price for first listing; fair value determined by the business appraiser." (idx.id page, undated). So reference = previous price (page does not say "closing price"). Not stated in source: how previous price is defined if no trade (unresolved).
- Rounding direction: NOT stated in any source I could read. Evidence only: Pluang (2026-10-21 update) quotes "Batas aktual mengikuti pembulatan fraksi harga di sistem JATS" and gives Rp6,000 ARB "about Rp5,580 before tick rounding". Bisnis/Nafan: "mekanisme pembulatan yang ditetapkan BEI". News: BBCA ARB at Rp4,820 (-6.86%) on 2026-10-19 which implies prior close 5,175 (inferred, not stated) and 7% = 4,812.75 rounded UP to 4,820 on a Rp10 tick. This is consistent with "ARB rounded up, ARA rounded down" (the conventional reading, and what I use below), but it is inference. Mark every rounded cell as convention-dependent.
- Which tick applies when the limit price lies in a different tick band than the reference is not stated.

## 3. Rp1-10 band
- IDX page: Main/NewEconomy/Development Rp1.00-10.00: Upper AR Rp1, Lower AR Rp1, Volume column ">50,000 Lot or >5% of listed shares". Quote: "Volume >50,000 Lot or >5% of listed shares". No footnote explains it. The same band for Acceleration/Watchlist/DINFRA has no volume condition.
- Meaning: NOT explained by any source I read. A search-engine summary said orders above 50,000 lots or 5% of listed shares (whichever smaller) are rejected, but that is unverified (no quote). Treat as: unresolved whether it is (a) an order-size rejection limit, or (b) a condition on when the Rp1 limit applies. Pluang says Rp1-10 limit is a fixed Rp1 nominal, "not a percentage".
- Rp1 limit is nominal: ARA = ref + 1, ARB = ref - 1 (floored at min price Rp1).

## 4. Source log
| Fact | URL | Type | Date | Quote (gloss) |
|---|---|---|---|---|
| Current AR table, ticks, ref price, 50,000 lot column, cites Kep-00158 | https://www.idx.id/en/products-services/trading-hours-and-mechanism/ | official IDX web page | undated (post 2026-10-20) | "Volume >50,000 Lot or >5% of listed shares" |
| Min price Rp50 -> Rp1 effective 2026-09-28; IDX statements | https://en.antaranews.com/news/432809/idx-to-lower-minimum-stock-price-to-rp1-starting-sept-28 | news (Antara) | 2026-09-25 | Hendrik: "ready to implement the removal of the Rp50 minimum price ... Monday, Sept. 28" |
| Kep-00136/BEI/09-2026 dated 2026-09-21, revokes Kep-00003/BEI/04-2025 (2025-04-08); table; symmetric from 2027-01-01 | https://katadata.co.id/finansial/bursa/6ab0fe985f085/harga-minimum-saham-jadi-rp-1-mulai-pekan-depan-auto-rejection-disesuaikan | news | 2026-09-21 | Rp11-200: 35%/15% until 31 Dec; from 1 Jan 2027 ARB 35% |
| Transitional ARB 15% to 12-31; symmetric 2027-01-01 | https://jakartaglobe.id/business/idx-removes-rp-50-stock-price-floor-sets-new-minimum-at-rp-1 | news | 2026-09-21 | "restore symmetric limits January 1, 2027" |
| Same; Kep-00136 (II-A) and Kep-00137 (II-O) | https://www.emitennews.com/news/bei-rombak-aturan-ara-dan-arb-jadi-simetris-mulai-tahun-depan ; https://bcasekuritas.co.id/latest-news/news/bei-harga-saham-terendah-rp1-berlaku-efektif-mulai-28-september | news / broker (IQPlus) | 2026-09-21/22 | Rp1-10 Rp1/Rp1; >10-200 35/15; 2027 symmetric |
| Katadata 2027 detail | https://katadata.co.id/finansial/bursa/6ab34046799dd/bei-ubah-aturan-batas-bawah-harga-saham-arb-jadi-35-apa-dampak-ke-investor | news | 2026-09-23 | "ketentuan ARB akan dibuat simetris dengan ARA pada masing-masing rentang harga" (ARB made symmetric with ARA in each range) |
| Kep-00157: ARB 15%->7% from 2026-10-19 to 2026-12-31, subject to review | https://www.thestar.com.my/business/business-news/2026/10/19/indonesia-stock-exchange-cuts-share-price-decline-limit-to-7 | news (Bernama) | 2026-10-19 | "until 31 December 2026 ... subject to review" ; Rp1-10 keep Rp1 |
| Kep-00158 replaces 00157, effective 2026-10-20 to 2026-12-31, table | https://www.bareksa.com/berita/saham/2026-10-20/bei-ubah-lagi-aturan-arb-mulai-20-oktober-saham-rp11rp14-dibatasi-turun-rp1 ; https://ekonomi.republika.co.id/berita/tn6s16370/bursa-efek-indonesia-perbarui-ketentuan-auto-reject-bawah-untuk-saham-harga-rendah | news | 2026-10-20 | "Kebijakan ini berlaku mulai 20 Oktober hingga 31 Desember 2026" (applies 20 Oct to 31 Dec 2026) |
| Rounding hint, examples, 2027 not confirmed | https://pluang.com/akademi/berita-analisis/saham-rp1-aturan-ara-arb-baru | broker education | 2026-10-06 header / updated 10-21 | "Batas aktual mengikuti pembulatan fraksi harga di sistem JATS" |
| Lexology/HBT law firm summary (403, only via search snippet): permanent AR in 2026 Trading Rules from 2027-01-01 | https://www.lexology.com/library/detail.aspx?g=4bf8f6d4-5139-4f76-9c3e-60ce0844a676 | law firm, snippet only | 2026-09 | not read |

## 5. Hand-computed boundary table (rounding convention: ARA floor to tick, ARB ceil to tick; tick from table by the limit price's own level; all cells marked * depend on that convention)
Rule sets: [OLD] 2026-09-25: min Rp50, ARB 15%. [R1] 09-28 and 10-16: Rp1-10 +/-1; >10 ARA 35/25/20 ARB 15%. [R2] 10-19: ARB 7% above Rp10 (incl. 11-14). [R3] 10-20 and 12-31: 11-14 ARB Rp1, rest 7%.
Band edges used: ARA 35% for Rp11-200 (IDX page: 11-14 and 15-200 both 35%), 25% for >200-5000 (so 5000 is 25%), 20% above 5000.

Ref 1: 09-25 N/A (below min). R1/R2/R3: ARA 2, ARB 1 (1-1=0 is below min price Rp1, so floor at 1; ambiguous whether ARB is "none" or 1).
Ref 10: 09-25 N/A. All later dates: ARA 11, ARB 9.
Ref 11: 09-25 N/A. R1: ARA 11*1.35=14.85 -> 14*; ARB 11*0.85=9.35 -> 10*. 10-19(R2): ARA 14*; ARB 11*0.93=10.23 -> 11* (no downside). 10-20/12-31(R3): ARA 14*; ARB 11-1=10.
Ref 14: 09-25 N/A. R1: ARA 18.9 -> 18*; ARB 11.9 -> 12*. R2 (10-19): ARA 18*; ARB 13.02 -> 14*. R3: ARA 18*; ARB 13.
Ref 15: 09-25 N/A. R1: ARA 20.25 -> 20*; ARB 12.75 -> 13*. R2/R3: ARA 20*; ARB 13.95 -> 14*.
Ref 16: 09-25 N/A. R1: ARA 21.6 -> 21*; ARB 13.6 -> 14*. R2/R3: ARA 21*; ARB 14.88 -> 15*.
Ref 100: OLD/R1: ARA 135, ARB 85 (85.0 exact). R2/R3: ARA 135, ARB 93 (exact).
Ref 200 (35% band): OLD/R1: ARA 270 (tick 2 above 200; exact), ARB 170. R2/R3: ARA 270, ARB 186 (exact).
Ref 201 (25% band): ARA 251.25 -> tick 2 -> 250*; ARB 15%: 170.85 -> tick 1 -> 171*; 7%: 186.93 -> 187*. (Same for OLD and R1; R2/R3 ARB 187.) Ambiguous: tick band of the limit vs reference. Ref 201 is itself not a valid tick (Rp2 step above 200) but included as asked.
Ref 5000 (25% band): ARA 6250 (tick 25, exact); ARB 15%: 4250 (exact), 7%: 4650 (exact).
Ref 5001 (20% band; not a valid tick, since step is 25): ARA 6001.2 -> 6000*; ARB 15%: 4250.85 -> tick 10 -> 4260*; 7%: 4650.93 -> 4660*. Ambiguous: band edge and non-tick reference.
Ref 10000: ARA 12000 (exact); ARB 15% 8500 (exact); 7% 9300 (exact).

Date summary: 2026-09-25 = OLD; 2026-09-28 = R1; 2026-10-16 = R1; 2026-10-19 = R2; 2026-10-20 = R3; 2026-12-31 = R3 (assuming no early change). Cells above give OLD/R1 values together because they are equal except where marked N/A or differing by band for Rp11-14.
If 2027 symmetric rule were applied (not established): ref 100 ARB 65, ref 11 ARB 35% -> 7.15 (crosses into the Rp1-10 band; ambiguous).

## 6. Not established
- Primary decree text (Kep-00136, 00137, 00157, 00158) not read (403). No official IDX announcement/press release number read.
- Rounding direction, tick-band selection at crossings, definition of "previous price" with no trade.
- Meaning of ">50,000 Lot or >5% of listed shares" in the Rp1-10 row.
- Rules from 2027-01-01: the symmetric plan predates 00157/00158; no official confirmation after October.
- Whether Kep-00157 truly became effective on 2026-10-19 (sources agree) and was replaced on 2026-10-20 (agree); intraday transition on 10-19/10-20 not examined.
- Acceleration/Watchlist/ETF/REIT/DINFRA/warrant effective dates and pre-2026-09-28 values; IPO first-day rules (Kontan hints at a pending change, not read).
- Whether the tick table changed in the window; whether the old regime (before 09-28) ARB 15% was uniformly applied (news says 35/15, 25/15, 20/15).
- Stockwatch framing "ARB for Rp11-Rp200 from 15% to 7%" matches; no contradicting evidence found for the 7% figure.
