# IDX equity auto-rejection (ARA / ARB): reconciled, test-ready specification (v2, for test authors)

Prepared 2026-11-09 by the reconciler, from two independent research passes (A with leads, B blind), a legal-basis pass for 2027, and my own primary-source checks.

Scope: IDX equity securities on the Regular Market and Cash Market, trading sessions Mon 2026-09-28 to 2026-12-31, plus the status of 2027-01-01 onward. Nothing after 2026-11-09 is known.

**Revision v2 (2026-11-09), after an independent review of v1 against raw price bars (all changes are about market facts):**

1. U5 is downgraded to UNRESOLVED, contradicted by observation. v1 derived "on Mon 2026-10-19, reference Rp11-14, ARB = reference (no downside)". Two real bars contradict every candidate formula (see U5). Do not assert any ARB for 2026-10-19 with a reference price of Rp11-14. The ARA for those references is still asserted (35%).
2. The own-band tick choice (U3) has more support than v1 said (see U3); it stays in the REPORTED test class.
3. Section 9 (2027 onward) is rewritten: the symmetric tables are removed so that nobody asserts them; tests must not assert any exchange rule for dates on or after 2027-01-01.
4. "Official" is used loosely in some v1 text: the decree PDFs were never read. The evidence is the IDX web page, IDX press releases as reposted by brokers, and press reports.

## 0. Read this first

**Independence.** No code under /home/user was read. Every statement below comes from web sources fetched on 2026-11-09. The calculator that generated the numeric tables was written from the rules in this file only.

**What is official, and what is not.** The decree PDFs on idx.co.id (including the in-force Rule II-A, Kep-00158/BEI/10-2026) return HTTP 403 in this environment and were NOT obtained. I tried the in-force Rule II-A PDF once with the standard fetch tool (HTTP 403); a second attempt with a browser-style header was refused by the session's policy and I did not pursue it. Official material that WAS read directly:

1. IDX web page "Trading hours and mechanism", https://www.idx.id/en/products-services/trading-hours-and-mechanism/ . I downloaded the raw HTML and parsed its tables, so merged cells (`rowspan`) are known rather than guessed. The page cites Kep-00158/BEI/10-2026 and reflects the state after 2026-10-20. It carries no date.
2. IDX regulation register, https://www.idx.id/id/peraturan/peraturan-bei/ . It lists the in-force Rule II-A as "II-A Kep-00158/BEI/10-2026" (attachment 1,420 KB, file name suffix 261020), Rule II-O as Kep-00137/BEI/09-2026, Rule II-X as Kep-00140/BEI/09-2026 and Rule II-V as Kep-00084/BEI/10-2019. Kep-00136 and Kep-00157 are not listed any more (inference: each later decree re-issues the whole rule).
3. The IDX press releases of 19 Oct and 20 Oct 2026 as reposted by IQPlus on BCA Sekuritas.

**Grades.**

- CONFIRMED: read in an official IDX source above, or reported consistently by two or more independent sources, or reproduced by two or more independent observed market prices.
- REPORTED: one non-official source, or a direct inference from CONFIRMED facts (the inference is stated).
- UNRESOLVED: no adequate source, or sources conflict.

**Marker.** A dagger after a reference price (201†, 5001†) means the price is not a valid price on the tick table (for example 201 is odd above Rp200). Such a reference can only arise from a theoretical price after a corporate action. It is included because boundary tests like such values.

## 1. Dated period table

Dates are WIB trading-session dates, inclusive. Weekend dates (09-26/27, 10-17/18) have no sessions.

| ID | Sessions | Instrument | Grade |
|---|---|---|---|
| P0 (context only) | up to and including Fri 2026-09-25 | Kep-00003/BEI/04-2025, dated 2025-04-08, in force since then; revoked by Kep-00136 | CONFIRMED |
| P1 | Mon 2026-09-28 to Fri 2026-10-16 | Kep-00136/BEI/09-2026, dated Mon 2026-09-21, effective Mon 2026-09-28 ("phase 1", valid to 2026-12-31). Companion Kep-00137/BEI/09-2026 for DINFRA (Rule II-O) | CONFIRMED |
| P2 | Mon 2026-10-19 only (one session) | Kep-00157/BEI/10-2026, dated 2026-10-19, replaces Kep-00136 | CONFIRMED |
| P3 | Tue 2026-10-20 to 2026-12-31 | Kep-00158/BEI/10-2026, dated 2026-10-20, replaces Kep-00157; "berlaku mulai 20 Oktober hingga 31 Desember 2026" | CONFIRMED |
| P4 | 2027-01-01 onward | none confirmed (see section 9) | UNRESOLVED |

Date lookup:

```
session_date <= 2026-09-25                -> P0 (context only)
2026-09-28 <= session_date <= 2026-10-16  -> P1
session_date == 2026-10-19                -> P2
2026-10-20 <= session_date <= 2026-12-31  -> P3
session_date >= 2027-01-01                -> UNRESOLVED (first possible session: Mon 2027-01-04)
```

Whole-session effect (REPORTED; decree text unread). Kep-00157 was released early on Monday 10-19 before the open (Fortune, published 08:53 WIB: "Senin dini hari"; CNN Indonesia 09:05 "mulai hari ini"), and BBCA hit the new limit "saat pembukaan" (Katadata, 10:43). Kep-00158 was reported at 08:16 to 08:34 WIB on Tuesday 10-20, before the 08:45 pre-opening session (Maybank, RCTI+, Beritasatu). Treat each effective date as a full-session change, with no intraday split.

Validity wording. P2 and P3 are both described as valid until 31 December 2026 and "akan dievaluasi kembali mengikuti perkembangan pasar" (BCA/IQPlus, Antara, Bareksa, Republika, RCTI+). OJK Chair Friderica Widyasari Dewi repeated on 2026-11-05 that the 7% ARB applies only to 31 December 2026 (Wartaekonomi and Bisnis, 2026-11-06).

Last P3 session (REPORTED, single source). Tirto, seen only through a search summary, lists Thu 2026-12-31 as an IDX holiday together with 12-24 and 12-25. If right, the last P3 session is Wed 2026-12-30. The holiday calendar was otherwise not checked.

## 2. Rules by board group and price band

Band edges are on the reference price (section 3). "Rp1" in the Rp1-10 rows and in the Rp11-14 ARB cell is a nominal rupiah amount, not a percentage (section 6). ARA = upper limit, ARB = lower limit.

### 2.1 Main, Development and New Economy boards (Papan Utama, Pengembangan, Ekonomi Baru)

| Reference-price band | P0 (to 09-25) | P1 (09-28 to 10-16) | P2 (10-19) | P3 (10-20 to 12-31) |
|---|---|---|---|---|
| Rp1-10 | not tradable (minimum price Rp50) | ARA +Rp1 / ARB -Rp1 | ARA +Rp1 / ARB -Rp1 | ARA +Rp1 / ARB -Rp1 |
| Rp11-14 | not tradable | 35% / 15% | 35% / 7% | 35% / -Rp1 (nominal) |
| Rp15-200 | (Rp50-200) 35% / 15% | 35% / 15% | 35% / 7% | 35% / 7% |
| above Rp200 to Rp5,000 | 25% / 15% | 25% / 15% | 25% / 7% | 25% / 7% |
| above Rp5,000 | 20% / 15% | 20% / 15% | 20% / 7% | 20% / 7% |

Grades: P0 CONFIRMED (Katadata "previous rule" table; older IDX page copy on BCA FAQ; April 2025 reports). P1 CONFIRMED (Katadata, Maybank, Cermati, NH Korindo, Jakarta Globe, BCA/IQPlus; decree number and date given). P2 CONFIRMED (Bareksa, Antara, Fortune, Kontan; OJK 2026-11-05; 351 stocks hit the 7% ARB on 10-19 per CNBC Indonesia). P3 CONFIRMED (IDX web page table; Bareksa, Republika, RCTI+, Beritasatu, IQPlus repost of the IDX release).

Rp11-14 and Rp15-200 are one band (Rp11-200, 35%) in P1 and P2. The IDX page splits them in P3 only because the ARB differs.

Board scope of the October decisions. Kep-00158's release says the adjustment applies to Papan Utama, Papan Pengembangan and Papan Ekonomi Baru, and that Papan Akselerasi and Papan Pemantauan Khusus "tetap mengikuti" their own rules (BCA/IQPlus, RCTI+, Beritasatu, Bareksa; CONFIRMED). The Kep-00157 articles read do not name boards (REPORTED: same scope).

### 2.2 Acceleration board and Special Monitoring (Watchlist) board

| Reference-price band | ARA / ARB (all of P0 to P3) |
|---|---|
| Rp1-10 | +Rp1 / -Rp1 |
| above Rp10 | 10% / 10% |

CONFIRMED for the current state (IDX page row "Acceleration Board and Watchlist Board") and for P0 (older IDX page copy on BCA FAQ shows the same rows). The October decisions did not touch these boards (IDX release wording, repeated by BCA/IQPlus, Republika, RCTI+, Bareksa and Beritasatu). The IDX page calls the second board "Watchlist Board"; Indonesian releases call it "Papan Pemantauan Khusus".

### 2.3 ETF and REIT (DIRE)

IDX page, current state: same structure as section 2.1 P3. Rp1-10: +Rp1 / -Rp1; Rp11-14: 35% / -Rp1; a row printed "Rp11 to Rp200" (typo for Rp15-200): 35% / 7%; above Rp200 to Rp5,000: 25% / 7%; above Rp5,000: 20% / 7%.

Grades: P3 REPORTED (official page, undated, one row has a typo). P0 CONFIRMED: 35/25/20 up and 15% down, as for section 2.1 (older IDX page copy on BCA FAQ, read directly; April 2025 reports, seen through search summaries, say the 15% ARB covered ETF and DIRE). P1 and P2 UNRESOLVED: no dated source. By continuity P1 would equal section 2.1 P1; P2 is unknown (the 19 Oct articles do not mention ETF or DIRE). Maybank's statement that ETF, DIRE and DINFRA are all 10% / 10% is wrong for ETF and DIRE (see section 11). ETF/DIRE/DINFRA tick is Rp1 (Maybank, REPORTED).

### 2.4 DINFRA units (Rule II-O, Kep-00137/BEI/09-2026)

Rp1-10: +Rp1 / -Rp1. Above Rp10: 10% / 10%. CONFIRMED (Katadata, Maybank, NH Korindo, hukumonline, IDX page). Effective Mon 2026-09-28 for the Rp1-10 band (before: minimum Rp50, 10% / 10%). Unchanged by the October decisions.

### 2.5 Rights and warrants (not needed for equity tests)

IDX page: rights show no limits. Warrants: first day, buy price at or above the underlying's last price, no lower limit; later days Rp1-9 upper Rp10, above Rp9 to Rp200 50%/50%, above Rp200 to Rp5,000 40%/40%, above Rp5,000 30%/30%. REPORTED. Minimum price for rights and warrants was Rp1 before and after 2026-09-28 (NH Korindo).

### 2.6 Order-volume auto rejection (separate from the price limits)

The IDX auto-rejection table has a "Volume" column whose single cell reads ">50,000 Lot or >5% of listed shares". In the raw HTML that cell is `rowspan="21"`, and the table has exactly 21 data rows, so it spans every row (all board groups, rights, warrants). It is a table-wide order-volume limit, not a condition of the Rp1-10 band. Maybank and Cermati add "whichever is smaller" and say the rule is unchanged by the Rp1 reform. Meaning: an order larger than 50,000 lots (1 lot = 100 shares) or larger than 5% of the listed shares, whichever is smaller, is rejected. CONFIRMED (scope from the IDX HTML; "whichever is smaller" from two broker pages). Price-limit tests should ignore it.

### 2.7 Market scope

Regular Market and Cash Market (Pasar Reguler, Pasar Tunai): hukumonline, Bareksa, Antara, NH Korindo. CONFIRMED. The minimum price changed in those two markets only (NH Korindo: rights and warrants were already Rp1; HBT Law, through a search summary, says the same for negotiated-market equities).

## 3. Reference price and band selection

- The IDX page says the reference price used to set the upper and lower limits in the regular market is based on: the previous price; the theoretical price after a corporate action; the initial price of a first listing; or a fair value set by a business appraiser (POJK 35/POJK.04/2020). CONFIRMED.
- "Previous price" is the previous trading day's closing price (Brights; calcuid; Katadata's BBCA report uses the 10-16 close as the 10-19 reference). REPORTED. What counts as the previous price after a day without trades is not stated (UNRESOLVED, U8).
- The band is chosen by the reference price, not by the order price or the limit price. REPORTED (inference; consistent with every anchor in section 8).
- Edges as printed by IDX: "IDR1.00 to IDR10.00", "IDR11.00 to IDR14.00", "IDR15.00 to IDR200.00", ">IDR200.00 to IDR5,000.00", ">IDR5,000.00". So Rp200 is in the 35% band, Rp5,000 is in the 25% band, Rp5,001 is in the 20% band. CONFIRMED.
- On a regime change day the new limits are applied to that session's reference price, which is the previous close set under the old regime. Example: the 10-19 limit is 7% of the 10-16 close. CONFIRMED (BBCA: 10-16 close Rp5,175, 10-19 ARB Rp4,820).

## 4. Tick table and minimum price

| Price | Tick (price fraction) | Maximum price step |
|---|---|---|
| below Rp200 | Rp1 | Rp10 |
| Rp200 to below Rp500 | Rp2 | Rp20 |
| Rp500 to below Rp2,000 | Rp5 | Rp50 |
| Rp2,000 to below Rp5,000 | Rp10 | Rp100 |
| Rp5,000 and above | Rp25 | Rp250 |

CONFIRMED (IDX page, which cites Kep-00158; the same table appears in the older IDX page copy citing Kep-00196/BEI/12-2024, in Maybank citing PR 083/BEI.SPR/09-2026, and Cermati says the ticks are unchanged by the reform). The tick table is therefore the same in P0 to P3.

A price p is valid if p is a whole number of rupiah, p is at least the minimum price, and p is a multiple of the tick of p's own band. So valid prices run ..., 198, 199, 200, 202, ..., 498, 500, 505, ..., 1995, 2000, 2010, ..., 4990, 5000, 5025, ...

Minimum price (Regular and Cash markets): Rp50 through 2026-09-25, Rp1 from Mon 2026-09-28. CONFIRMED (Antara, Katadata, hukumonline, NH Korindo, many others).

## 5. Calculation rule (normative for the tests)

Inputs: reference price R (valid price), minimum price m (50 in P0, otherwise 1), and the rule row for R from section 2.

```
valid(p)   : p is an integer >= 1 and p % tick(p) == 0          # tick(p) from section 4
ARA_raw    : percentage row a -> R * (1 + a)       nominal row -> R + 1
ARA        : largest valid price <= ARA_raw                     # floor onto the valid-price grid
ARB_raw    : percentage row b -> R * (1 - b)       nominal row -> R - 1
ARB        : max(m, smallest valid price >= ARB_raw)            # ceil onto the valid-price grid
accepted   : ARB <= order_price <= ARA   (and order_price >= m, and the volume rule of section 2.6)
```

- Use exact decimal or rational arithmetic. The percentages are exact (R * 35 / 100); binary floats are unsafe on the many .5 and .25 values.
- Floor/ceil is taken on the grid of valid prices, so the tick that applies is the tick of the candidate limit price's own band, not the reference price's band. Example: R = 5,175 (tick 25) with a 7% ARB has raw 4,812.75, which lies in the tick-10 band, so ARB = 4,820, not 4,825.
- Direction is set by what the limit means: an order priced beyond the limit is rejected, so the ARA can never exceed R*(1+a) and the ARB can never be below R*(1-b).
- Grade for floor/ceil with own-band tick: CONFIRMED for the direction (20 of 20 observed prices in section 8; 6 of them clearly differ under round-to-nearest, and a seventh, BABY, differs only if ties round up). REPORTED, with added support, for the own-band tick choice: BBCA 2026-10-19 (reference 5,175 observed on the 10-16 close, ARB 4,820 observed); a reviewer's check of raw price bars found that using the tick of the reference price instead would produce prices that are not valid prices on the tick table (BBCA ARB 4,825 where the tick is 10). The decree wording on rounding was not read.

Consequences that tests may rely on (derived, REPORTED where marked in section 10):
- With a 7% ARB, R = 11 to 14 gives a formula value of ARB = R (7% of Rp14 is only Rp0.98 and the ARB rounds up). This is the evident reason Kep-00158 replaced the 7% by a nominal Rp1 for Rp11-14. It is a formula result only: on 2026-10-19 observed closes contradict it (U5), so no test may assert it as market behaviour.
- With a 7% ARB, R = 15 gives ARB = 14 (-6.67%); R = 25 gives 24 (-4%).
- With a 15% ARB at the old Rp50 floor (P0), R = 50 to 58 gives ARB = 50 (no downside).

## 6. The Rp1-10 band and the Rp11-14 nominal ARB

- In the Rp1-10 band ARA and ARB are a fixed Rp1 from the reference price, not a percentage (pass B's reading of Bareksa 2026-09-22 and Bloomberg Technoz 2026-09-21: "bukan persentase"; Cermati "+-Rp1 dari Acuan Harga"; NH Korindo's DINFRA wording "more than Rp1.00 above or below the Reference Price"; the IDX page row "IDR1.00 / IDR1.00"). CONFIRMED.
- ARA = R + 1; ARB = R - 1, floored at the minimum price Rp1. R = 1 gives ARA 2 and ARB 1 (no downside). R = 10 gives ARA 11 (a price in the next band) and ARB 9. The floor at Rp1 follows from two separate rejection conditions (price below the minimum price; price more than Rp1 from the reference); the ARB for R = 1 was not observed directly (U4, REPORTED).
- Same in P1, P2 and P3. CONFIRMED (every October article says Rp1-10 stays at Rp1).
- Rp11-14 in P3: ARB is a nominal Rp1, so ARB = R - 1 (11 to 10, 12 to 11, 13 to 12, 14 to 13); ARA stays 35%. CONFIRMED: Bareksa headline "Dibatasi Turun Rp1", Ajaib "Turun Maksimal Rp1", Fortune ("serupa dengan kebijakan ARB pada saham Rp1-Rp10"), and the notation "Rp1" in the IDX table, identical to the Rp1-10 row. Some headlines (Katadata "Saham Rp 14 Bisa Turun ke Rp 1", Pasardana, Periskop) can be misread as an absolute price floor of Rp1. That reading makes no sense for the stated purpose and contradicts the sources above; it is rejected (U14).
- Before 2026-09-28 the Rp1-10 band did not apply to Main, Development and New Economy stocks (minimum price Rp50); it applied only to the Acceleration and Special Monitoring boards (Cermati).

## 7. Boundary-example tables (generated with exact arithmetic)

Rule sets: P0 = to 09-25 (minimum price 50, ARB 15%); P1 = 09-28 to 10-16; P2 = 10-19; P3 = 10-20 to 12-31 (section 2.1). Each cell shows the raw value, the rounding step and the result in bold; ARB cells also show the realised move from R. "tick t" is the tick of the rounded result's own band.

### 7.1 Per-date quick reference, ARA / ARB (Main, Development, New Economy)

| Ref (R) | 2026-09-25 (P0, context) | 2026-09-28 (P1) | 2026-10-16 (P1) | 2026-10-19 (P2) | 2026-10-20 (P3) | 2026-12-31 or last session (P3) |
|---|---|---|---|---|---|---|
| 1 | n/a | 2 / 1 | 2 / 1 | 2 / 1 | 2 / 1 | 2 / 1 |
| 10 | n/a | 11 / 9 | 11 / 9 | 11 / 9 | 11 / 9 | 11 / 9 |
| 11 | n/a | 14 / 10 | 14 / 10 | 14 / not asserted (U5) | 14 / 10 | 14 / 10 |
| 14 | n/a | 18 / 12 | 18 / 12 | 18 / not asserted (U5) | 18 / 13 | 18 / 13 |
| 15 | n/a | 20 / 13 | 20 / 13 | 20 / 14 | 20 / 14 | 20 / 14 |
| 16 | n/a | 21 / 14 | 21 / 14 | 21 / 15 | 21 / 15 | 21 / 15 |
| 50 | 67 / 50 | 67 / 43 | 67 / 43 | 67 / 47 | 67 / 47 | 67 / 47 |
| 100 | 135 / 85 | 135 / 85 | 135 / 85 | 135 / 93 | 135 / 93 | 135 / 93 |
| 200 | 270 / 170 | 270 / 170 | 270 / 170 | 270 / 186 | 270 / 186 | 270 / 186 |
| 201† | 250 / 171 | 250 / 171 | 250 / 171 | 250 / 187 | 250 / 187 | 250 / 187 |
| 5000 | 6250 / 4250 | 6250 / 4250 | 6250 / 4250 | 6250 / 4650 | 6250 / 4650 | 6250 / 4650 |
| 5001† | 6000 / 4260 | 6000 / 4260 | 6000 / 4260 | 6000 / 4660 | 6000 / 4660 | 6000 / 4660 |
| 10000 | 12000 / 8500 | 12000 / 8500 | 12000 / 8500 | 12000 / 9300 | 12000 / 9300 | 12000 / 9300 |

### 7.2 Full arithmetic

| Ref (R) | Band | ARA, P1+P2+P3 (identical) | ARB P0 (to 09-25; min Rp50) | ARB P1 (09-28..10-16) | ARB P2 (10-19) | ARB P3 (10-20..12-31) |
|---|---|---|---|---|---|---|
| 1 | Rp1-10 | 1+1 = **2** | n/a (below Rp50 minimum) | 1-1 = 0 < min 1 -> **1** | 1-1 = 0 < min 1 -> **1** | 1-1 = 0 < min 1 -> **1** |
| 2 | Rp1-10 | 2+1 = **3** | n/a (below Rp50 minimum) | 2-1 = **1** | 2-1 = **1** | 2-1 = **1** |
| 10 | Rp1-10 | 10+1 = **11** | n/a (below Rp50 minimum) | 10-1 = **9** | 10-1 = **9** | 10-1 = **9** |
| 11 | Rp11-14 | x1.35 = 14.85 -> floor, tick 1 = **14** | n/a (below Rp50 minimum) | x0.85 = 9.35 -> ceil, tick 1 = **10** (-9.09%) | not asserted (U5; the 7% formula gives 11) | 11-1 = **10** |
| 12 | Rp11-14 | x1.35 = 16.2 -> floor, tick 1 = **16** | n/a (below Rp50 minimum) | x0.85 = 10.2 -> ceil, tick 1 = **11** (-8.33%) | not asserted (U5; the 7% formula gives 12) | 12-1 = **11** |
| 13 | Rp11-14 | x1.35 = 17.55 -> floor, tick 1 = **17** | n/a (below Rp50 minimum) | x0.85 = 11.05 -> ceil, tick 1 = **12** (-7.69%) | not asserted (U5; the 7% formula gives 13) | 13-1 = **12** |
| 14 | Rp11-14 | x1.35 = 18.9 -> floor, tick 1 = **18** | n/a (below Rp50 minimum) | x0.85 = 11.9 -> ceil, tick 1 = **12** (-14.29%) | not asserted (U5; the 7% formula gives 14) | 14-1 = **13** |
| 15 | Rp15-200 | x1.35 = 20.25 -> floor, tick 1 = **20** | n/a (below Rp50 minimum) | x0.85 = 12.75 -> ceil, tick 1 = **13** (-13.33%) | x0.93 = 13.95 -> ceil, tick 1 = **14** (-6.67%) | x0.93 = 13.95 -> ceil, tick 1 = **14** (-6.67%) |
| 16 | Rp15-200 | x1.35 = 21.6 -> floor, tick 1 = **21** | n/a (below Rp50 minimum) | x0.85 = 13.6 -> ceil, tick 1 = **14** (-12.50%) | x0.93 = 14.88 -> ceil, tick 1 = **15** (-6.25%) | x0.93 = 14.88 -> ceil, tick 1 = **15** (-6.25%) |
| 17 | Rp15-200 | x1.35 = 22.95 -> floor, tick 1 = **22** | n/a (below Rp50 minimum) | x0.85 = 14.45 -> ceil, tick 1 = **15** (-11.76%) | x0.93 = 15.81 -> ceil, tick 1 = **16** (-5.88%) | x0.93 = 15.81 -> ceil, tick 1 = **16** (-5.88%) |
| 20 | Rp15-200 | x1.35 = 27 (exact) = **27** | n/a (below Rp50 minimum) | x0.85 = 17 (exact) = **17** (-15.00%) | x0.93 = 18.6 -> ceil, tick 1 = **19** (-5.00%) | x0.93 = 18.6 -> ceil, tick 1 = **19** (-5.00%) |
| 25 | Rp15-200 | x1.35 = 33.75 -> floor, tick 1 = **33** | n/a (below Rp50 minimum) | x0.85 = 21.25 -> ceil, tick 1 = **22** (-12.00%) | x0.93 = 23.25 -> ceil, tick 1 = **24** (-4.00%) | x0.93 = 23.25 -> ceil, tick 1 = **24** (-4.00%) |
| 50 | Rp15-200 | x1.35 = 67.5 -> floor, tick 1 = **67** | x0.85 = 42.5 < min 50 -> **50** (no downside) | x0.85 = 42.5 -> ceil, tick 1 = **43** (-14.00%) | x0.93 = 46.5 -> ceil, tick 1 = **47** (-6.00%) | x0.93 = 46.5 -> ceil, tick 1 = **47** (-6.00%) |
| 100 | Rp15-200 | x1.35 = 135 (exact) = **135** | x0.85 = 85 (exact) = **85** (-15.00%) | x0.85 = 85 (exact) = **85** (-15.00%) | x0.93 = 93 (exact) = **93** (-7.00%) | x0.93 = 93 (exact) = **93** (-7.00%) |
| 199 | Rp15-200 | x1.35 = 268.65 -> floor, tick 2 = **268** | x0.85 = 169.15 -> ceil, tick 1 = **170** (-14.57%) | x0.85 = 169.15 -> ceil, tick 1 = **170** (-14.57%) | x0.93 = 185.07 -> ceil, tick 1 = **186** (-6.53%) | x0.93 = 185.07 -> ceil, tick 1 = **186** (-6.53%) |
| 200 | Rp15-200 | x1.35 = 270 (exact) = **270** | x0.85 = 170 (exact) = **170** (-15.00%) | x0.85 = 170 (exact) = **170** (-15.00%) | x0.93 = 186 (exact) = **186** (-7.00%) | x0.93 = 186 (exact) = **186** (-7.00%) |
| 201† | >200-5,000 | x1.25 = 251.25 -> floor, tick 2 = **250** | x0.85 = 170.85 -> ceil, tick 1 = **171** (-14.93%) | x0.85 = 170.85 -> ceil, tick 1 = **171** (-14.93%) | x0.93 = 186.93 -> ceil, tick 1 = **187** (-6.97%) | x0.93 = 186.93 -> ceil, tick 1 = **187** (-6.97%) |
| 202 | >200-5,000 | x1.25 = 252.5 -> floor, tick 2 = **252** | x0.85 = 171.7 -> ceil, tick 1 = **172** (-14.85%) | x0.85 = 171.7 -> ceil, tick 1 = **172** (-14.85%) | x0.93 = 187.86 -> ceil, tick 1 = **188** (-6.93%) | x0.93 = 187.86 -> ceil, tick 1 = **188** (-6.93%) |
| 500 | >200-5,000 | x1.25 = 625 (exact) = **625** | x0.85 = 425 -> ceil, tick 2 = **426** (-14.80%) | x0.85 = 425 -> ceil, tick 2 = **426** (-14.80%) | x0.93 = 465 -> ceil, tick 2 = **466** (-6.80%) | x0.93 = 465 -> ceil, tick 2 = **466** (-6.80%) |
| 505 | >200-5,000 | x1.25 = 631.25 -> floor, tick 5 = **630** | x0.85 = 429.25 -> ceil, tick 2 = **430** (-14.85%) | x0.85 = 429.25 -> ceil, tick 2 = **430** (-14.85%) | x0.93 = 469.65 -> ceil, tick 2 = **470** (-6.93%) | x0.93 = 469.65 -> ceil, tick 2 = **470** (-6.93%) |
| 1000 | >200-5,000 | x1.25 = 1250 (exact) = **1250** | x0.85 = 850 (exact) = **850** (-15.00%) | x0.85 = 850 (exact) = **850** (-15.00%) | x0.93 = 930 (exact) = **930** (-7.00%) | x0.93 = 930 (exact) = **930** (-7.00%) |
| 1995 | >200-5,000 | x1.25 = 2493.75 -> floor, tick 10 = **2490** | x0.85 = 1695.75 -> ceil, tick 5 = **1700** (-14.79%) | x0.85 = 1695.75 -> ceil, tick 5 = **1700** (-14.79%) | x0.93 = 1855.35 -> ceil, tick 5 = **1860** (-6.77%) | x0.93 = 1855.35 -> ceil, tick 5 = **1860** (-6.77%) |
| 2000 | >200-5,000 | x1.25 = 2500 (exact) = **2500** | x0.85 = 1700 (exact) = **1700** (-15.00%) | x0.85 = 1700 (exact) = **1700** (-15.00%) | x0.93 = 1860 (exact) = **1860** (-7.00%) | x0.93 = 1860 (exact) = **1860** (-7.00%) |
| 4990 | >200-5,000 | x1.25 = 6237.5 -> floor, tick 25 = **6225** | x0.85 = 4241.5 -> ceil, tick 10 = **4250** (-14.83%) | x0.85 = 4241.5 -> ceil, tick 10 = **4250** (-14.83%) | x0.93 = 4640.7 -> ceil, tick 10 = **4650** (-6.81%) | x0.93 = 4640.7 -> ceil, tick 10 = **4650** (-6.81%) |
| 5000 | >200-5,000 | x1.25 = 6250 (exact) = **6250** | x0.85 = 4250 (exact) = **4250** (-15.00%) | x0.85 = 4250 (exact) = **4250** (-15.00%) | x0.93 = 4650 (exact) = **4650** (-7.00%) | x0.93 = 4650 (exact) = **4650** (-7.00%) |
| 5001† | >5,000 | x1.2 = 6001.2 -> floor, tick 25 = **6000** | x0.85 = 4250.85 -> ceil, tick 10 = **4260** (-14.82%) | x0.85 = 4250.85 -> ceil, tick 10 = **4260** (-14.82%) | x0.93 = 4650.93 -> ceil, tick 10 = **4660** (-6.82%) | x0.93 = 4650.93 -> ceil, tick 10 = **4660** (-6.82%) |
| 5025 | >5,000 | x1.2 = 6030 -> floor, tick 25 = **6025** | x0.85 = 4271.25 -> ceil, tick 10 = **4280** (-14.83%) | x0.85 = 4271.25 -> ceil, tick 10 = **4280** (-14.83%) | x0.93 = 4673.25 -> ceil, tick 10 = **4680** (-6.87%) | x0.93 = 4673.25 -> ceil, tick 10 = **4680** (-6.87%) |
| 10000 | >5,000 | x1.2 = 12000 (exact) = **12000** | x0.85 = 8500 (exact) = **8500** (-15.00%) | x0.85 = 8500 (exact) = **8500** (-15.00%) | x0.93 = 9300 (exact) = **9300** (-7.00%) | x0.93 = 9300 (exact) = **9300** (-7.00%) |

Things this table pins down:
- The ARA is identical in P1, P2 and P3 (the October decisions changed only the ARB).
- R = 11 to 14: the ARB is 10, 11, 12, 12 under 15% (P1) and R - 1 under the nominal rule (P3). For P2 (2026-10-19) nothing is asserted (U5).
- R = 500 under 15% / 7%: the raw ARB 425 and 465 are not valid prices (tick 2 below Rp500), so they round up to 426 and 466.
- R = 4,990: the ARA crosses into the tick-25 band (6,237.5 floors to 6,225).
- R = 199: the ARA crosses into the tick-2 band (268.65 floors to 268).
- Rows whose raw limit lies in a different tick band than R depend on the own-band tick rule (U3, REPORTED): R = 500 (ARB 426 and 466), R = 4990 (ARA 6225), R = 5001† (ARB 4260 and 4660) and R = 5025 (ARB 4280 and 4680). If the tick of R's band were used instead, these would be 425 and 465, 6230, 4275 and 4675, 4275 and 4675. The BBCA observation (4,820, not 4,825) supports the own-band rule.

### 7.3 Other boards: Acceleration, Special Monitoring (Watchlist), DINFRA (10% / 10%, Rp1-10 nominal)

Same algorithm. Identical in P1 to P3. The rounding convention is assumed to be the same (REPORTED).

| Ref (R) | Band | ARA | ARB |
|---|---|---|---|
| 1 | Rp1-10 | 1+1 = **2** | 1-1 = 0 < min 1 -> **1** |
| 2 | Rp1-10 | 2+1 = **3** | 2-1 = 1 = **1** |
| 10 | Rp1-10 | 10+1 = **11** | 10-1 = 9 = **9** |
| 11 | >Rp10 | x1.10 = 12.1 -> floor, tick 1 = **12** | x0.90 = 9.9 -> ceil, tick 1 = **10** |
| 12 | >Rp10 | x1.10 = 13.2 -> floor, tick 1 = **13** | x0.90 = 10.8 -> ceil, tick 1 = **11** |
| 14 | >Rp10 | x1.10 = 15.4 -> floor, tick 1 = **15** | x0.90 = 12.6 -> ceil, tick 1 = **13** |
| 15 | >Rp10 | x1.10 = 16.5 -> floor, tick 1 = **16** | x0.90 = 13.5 -> ceil, tick 1 = **14** |
| 16 | >Rp10 | x1.10 = 17.6 -> floor, tick 1 = **17** | x0.90 = 14.4 -> ceil, tick 1 = **15** |
| 100 | >Rp10 | x1.10 = 110 (exact) = **110** | x0.90 = 90 (exact) = **90** |
| 200 | >Rp10 | x1.10 = 220 (exact) = **220** | x0.90 = 180 (exact) = **180** |
| 201† | >Rp10 | x1.10 = 221.1 -> floor, tick 2 = **220** | x0.90 = 180.9 -> ceil, tick 1 = **181** |
| 1000 | >Rp10 | x1.10 = 1100 (exact) = **1100** | x0.90 = 900 (exact) = **900** |
| 5000 | >Rp10 | x1.10 = 5500 (exact) = **5500** | x0.90 = 4500 (exact) = **4500** |
| 5001† | >Rp10 | x1.10 = 5501.1 -> floor, tick 25 = **5500** | x0.90 = 4500.9 -> ceil, tick 10 = **4510** |
| 10000 | >Rp10 | x1.10 = 11000 (exact) = **11000** | x0.90 = 9000 (exact) = **9000** |

## 8. Calibration anchors (observed market prices)

Observed limit prices that the rule reproduces. References marked "derived" were backed out from the printed percentage change and checked to reproduce the printed percentage to two decimals. "alt" is what round-to-nearest (ties up) would give.

| anchor | ref | raw limit | rule value (floor/ceil to valid tick) | observed | alt: round-nearest | match |
|---|---|---|---|---|---|---|
| GOTO/PADI/RBMS 2026-09-28 (15% ARB, ref 50 -> 43) | 50 | 42.5 | 43 | 43 | 43 | YES |
| GOTO 2026-10-19 (7% ARB, ref 25 -> 24) | 25 | 23.25 | 24 | 24 | 23 | YES |
| TLKM 2026-10-19 (ref 1900 -> 1770) | 1900 | 1767 | 1770 | 1770 | 1765 | YES |
| BBCA 2026-10-19 (ref 5175 -> 4820) | 5175 | 4812.75 | 4820 | 4820 | 4810 | YES |
| AMMN 2026-10-19 (ref 3740 -> 3480) | 3740 | 3478.2 | 3480 | 3480 | 3480 | YES |
| MORA 2026-10-19 (ref 3910 -> 3640) | 3910 | 3636.3 | 3640 | 3640 | 3640 | YES |
| BYAN 2026-10-19 (ref 11150 -> 10375) | 11150 | 10369.5 | 10375 | 10375 | 10375 | YES |
| BBCA 2026-10-16 (15% ARB, ref 6075 -> 5175) | 6075 | 5163.75 | 5175 | 5175 | 5175 | YES |
| AKSI 2025-10-21 (25%, ref 302 -> 376) | 302 | 377.5 | 376 | 376 | 378 | YES |
| FITT 2025-10-21 (25%, ref 835 -> 1040) | 835 | 1043.75 | 1040 | 1040 | 1045 | YES |
| COCO 2025-10-21 (25%, ref 246 -> 306) | 246 | 307.5 | 306 | 306 | 308 | YES |
| WAPO 2025-10-21 (25%, ref 234 -> 292) | 234 | 292.5 | 292 | 292 | 292 | YES |
| BABY 2025-10-21 (25%, ref 430 -> 535) | 430 | 537.5 | 535 | 535 | 540 | YES |
| COCO 2025-10-22 (25%, ref 306 -> 382) | 306 | 382.5 | 382 | 382 | 382 | YES |
| TEBE 2025-10-22 (25%, ref 1930 -> 2410) | 1930 | 2412.5 | 2410 | 2410 | 2410 | YES |
| NIRO 2025-10-22 (35%, ref 163 -> 220) | 163 | 220.05 | 220 | 220 | 220 | YES |
| AYLS 2025-10-22 (35%, ref 175 -> 236) | 175 | 236.25 | 236 | 236 | 236 | YES |
| PPRE 2025-10-22 (35%, ref 86 -> 116) | 86 | 116.1 | 116 | 116 | 116 | YES |
| PGUN 2025-10-22 (20%, ref 12525 -> 15025) | 12525 | 15030 | 15025 | 15025 | 15025 | YES |
| RISE 2025-10-22 (20%, ref 7300 -> 8750) | 7300 | 8760 | 8750 | 8750 | 8750 | YES |

Sources:
- 2026-10-19 ARB anchors (GOTO Rp24, TLKM 1,770, BBCA 4,820, AMMN 3,480, MORA 3,640, BYAN 10,375): CNBC Indonesia, "Batas Auto Reject Turun, 351 Saham ARB Hari Ini", 2026-10-19 17:42 (prices and percentages: BBCA -6.86%, BYAN -6.95%, AMMN -6.95%, TLKM -6.84%, MORA -6.91%; GOTO down Rp1). BBCA 4,820 is also in Katadata (2026-10-19 10:43), Kontan and Ajaib. References derived (BBCA 5,175 is printed as the 10-16 close; GOTO 25 inferred from "down Rp1" at the 7% limit).
- BBCA 2026-10-16: Katadata, closed Rp5,175 after -14.81% at the 15% ARB; reference derived as 6,075.
- 2026-09-28 Rp43: investortrust.id, 2026-09-28 09:25 (GOTO, PADI, RBMS each -14.00%, Rp7 from Rp50) plus Bisnis and Fortune headlines.
- 2025 ARA anchors: investortrust.id, 2025-10-22 16:16 market report listing both sessions (21 and 22 Oct 2025). They pre-date the reform, but the ARA rule (35/25/20) and the tick table are unchanged. For the 2025-10-22 anchors COCO, NIRO and RISE the reference is the previous-session price printed in the same article; every other reference is derived from the printed percentage.
- The anchors where round-to-nearest would clearly differ from the rule (alt column differs from observed) are: GOTO 10-19, TLKM, BBCA 10-19, AKSI, FITT, COCO 2025-10-21. BABY differs only if ties round up.
- Exact worked examples under 7% from Maybank Trade, 2026-10-20: Rp100 gives Rp93, Rp1,000 gives Rp930, Rp10,000 gives Rp9,300 (all reproduced in sections 7.1 and 7.2).

## 9. 2027-01-01 onward: status UNRESOLVED

Facts (all as of 2026-11-09):

1. Kep-00136 (2026-09-21) set two phases. Phase 1 (09-28 to 12-31): ARB 15% above Rp10. From 2027-01-01 the lower limit "will be adjusted to the same percentage as the Upper Auto Rejection limits for each applicable price range": Rp1-10 +-Rp1; above Rp10 to Rp200 35%/35%; above Rp200 to Rp5,000 25%/25%; above Rp5,000 20%/20% (NH Korindo, Katadata, Maybank and Cermati read directly; Jakarta Globe per pass A; HBT Law, through a search summary, calls it the permanent framework). CONFIRMED as the September plan.
2. BEI Director of Trading Irvan Susandy, 2026-09-23 (Bisnis Insight, 2026-09-24; emitennews): symmetric is "kondisi normalnya"; "kami akan lihat perkembangan terakhir sampai akhir tahun"; "sementara ini rencana yang begitu". Bisnis Insight: the 2027 symmetric rule "tidak bersifat mutlak" and "tidak akan dipaksakan jika pasar belum kondusif". CONFIRMED that BEI called it conditional.
3. Kep-00157 (10-19) replaced Kep-00136, and Kep-00158 (10-20) replaced Kep-00157. Both are described as valid to 2026-12-31 and to be re-evaluated. None of the more than ten October reports read mentions 2027 or symmetry. Whether either decree kept Kep-00136's 2027 table is not known (U13).
4. OJK Chair Friderica Widyasari Dewi, RDKB press conference Thu 2026-11-05: the 7% ARB "hanya berlaku hingga 31 Desember 2026" (Wartaekonomi and Bisnis, 2026-11-06). A Kalderanews summary (page blocked) adds that OJK left room for further measures as markets develop (REPORTED).
5. No report up to 2026-11-09 of an extension of 7%, of a confirmation of the symmetric plan, or of a new decree number after Kep-00158. MSCI context (per the legal pass, not re-verified): consultation 2026-10-15 to 2027-04-30, decision by 2027-06-30; nothing found ties it to a 2027 ARB change.

Conclusion: no rule is confirmed for any session from 2027-01-01. Candidate regimes: S1 symmetric (BEI's stated default in September), S2 the P3 rule simply continued, S3 something else. The first possible session is Mon 2027-01-04 (inference: Fri 2027-01-01 is an IDX holiday and Tue 2027-01-05 is another, per the RCTI+ 2027 calendar). The unconfirmed state may last months: BEI said it would decide on the evidence at year end, and an index provider's consultation on related matters runs to 2027-04-30.

Test guidance (revised in v2): tests MUST NOT assert what the exchange's rule is for any date on or after 2027-01-01, and MUST NOT assert any symmetric (35/25/20 lower limit) value for such dates. The code adopts an explicitly labelled convention for those dates, defined in CONTRACT.md section 3 (it is a modelling convention chosen for caution, not a claim about the exchange). Tests may assert that convention, in a class whose name and docstring say it is a convention.

## 10. Unconfirmed or ambiguous (keep separate from the assertions above)

| ID | Item | Grade | How to treat in tests |
|---|---|---|---|
| U1 | Decree texts (Kep-00136, 00137, 00157, 00158 attachments) not read; idx.co.id gives HTTP 403 (standard fetch tool) and a browser-style retry was refused by session policy. The register URL of the in-force II-A is https://www.idx.co.id/Media/stumk2gi/signed_peraturan_nomor_ii_a_tentang_perdagangan_efek_bersifat_ekuitas-261020.pdf | UNRESOLVED | Do not cite decree article numbers. Re-check rounding and reference-price wording there when reachable. |
| U2 | Wording of the rounding rule. No readable source states it; the IDX page has none; calcuid says Rule II-A "does not publish a rounding formula". Direction is established by 20 observed prices (section 8) | CONFIRMED by observation, wording UNRESOLVED | Assert floor ARA and ceil ARB as in section 5. |
| U3 | Tick of the limit price versus tick of the reference price at band crossings. Discriminating observation: BBCA 2026-10-19; a reviewer's raw-bar check shows the alternative reading yields off-grid prices (see section 5) | REPORTED (supported) | Assert BBCA-type cases; assert the other crossing rows in the REPORTED test class, flagged. |
| U4 | ARB when R = 1 (computed ARB 0). Result 1 follows from the minimum price Rp1; not observed | REPORTED | Assert ARB = 1 for R = 1; flag. |
| U5 | 2026-10-19 (P2), reference Rp11-14: the 7% formula gives ARB = R (no downside), and v1 derived it as market behaviour. CONTRADICTED by observation: in the 2026-11-06 raw price pull, BTEK (previous close 12, open 8, low 7, close 9, volume 849M) and TAXI (previous close 12, open 8, low 8, close 9, volume 385M) traded and closed 25% below the reference on 2026-10-19. That is below every candidate limit (ARB = R; R - 1 = 11; the old 15% rule = 11). The real behaviour that day is unknown; the next-day amendment (Kep-00158) is consistent with a defect that day. | UNRESOLVED, contradicted by observation | Assert nothing about ARB for 2026-10-19 with a reference of Rp11-14. ARA is asserted. |
| U6 | ETF and REIT limits in P1 and P2; the IDX page row for ETF/REIT carries a typo ("Rp11 to Rp200" overlapping "Rp11 to Rp14") | UNRESOLVED (P1, P2); REPORTED (P3) | Do not assert ETF/REIT for P1 and P2. |
| U7 | ETF/DIRE/DINFRA tick Rp1 (Maybank only) | REPORTED | Avoid. |
| U8 | Definition of "previous price" when the stock had no trade, was suspended, or on corporate-action days | UNRESOLVED | Tests should pass the reference price in directly. |
| U9 | IPO first-day and rights/warrant details | UNRESOLVED | Out of scope. |
| U10 | Intraday handling on 10-19 and 10-20. Announcements preceded the open, so a full-session change is assumed; orders resting overnight and their revalidation are not described | REPORTED | Assert per-session limits only. |
| U11 | Holiday calendar: 2026-12-31 may be a holiday (Tirto, single source); first 2027 session Mon 2027-01-04 inferred | REPORTED | Do not hard-code a last session date. |
| U12 | All of 2027 onward | UNRESOLVED | Section 9. |
| U13 | Whether Kep-00157/00158 kept Kep-00136's 2027 table | UNRESOLVED | Section 9. |
| U14 | Media wording on Rp11-14 ("bisa turun ke/hingga Rp1" versus "turun maksimal Rp1"). Resolved as a nominal Rp1 move | REPORTED (decree wording unread) | Assert ARB = R - 1 for R = 11 to 14 in P3. |
| U15 | Decree number spelling: several outlets print "Kep-000157"; the IDX register uses five digits ("Kep-00158/BEI/10-2026") | CONFIRMED | Use Kep-00157. |
| U16 | hukumonline's September table (">Rp200-5,000 ARB 35%; >Rp5,000 ARB 15%") contradicts every other source | UNRESOLVED, rejected as an outlier | Ignore. |
| U17 | The IDX page is undated; it reflects the post-2026-10-20 state at fetch time (2026-11-09) | n/a | Re-fetch before relying on it later. |
| U18 | The "Maximum price step" column and the sentence that step values are fixed for the day (IDX page): a rule about order entry; its relation to ARA/ARB beyond "step must not exceed the AR percentage" is not clear | UNRESOLVED | Not needed for the limits. |

## 11. Reconciliation of research pass A and pass B (and the legal pass)

Both passes agree on every numeric boundary value in the period table, and my recomputation reproduces all of them (R = 1, 10, 11, 14, 15, 16, 100, 200, 201, 5000, 5001, 10000 in section 7). They differ as follows.

| Item | A | B | Right | Why |
|---|---|---|---|---|
| 50,000 lot / 5% of listed shares | Unresolved; maybe a condition on the Rp1-10 band | Separate order-volume auto rejection, not tied to Rp1-10 | B | IDX page HTML: one Volume cell, rowspan 21, spans all 21 rows. Maybank and Cermati: unchanged order-volume rule, "whichever is smaller". A read the flattened markdown view, where the cell shows only in the first row |
| Acceleration and Special Monitoring values | Rp1-10 +-Rp1; above Rp10 10%/10% | Not found | A | IDX page table; older page copy shows the same; October releases say these boards are untouched |
| ETF and REIT | Same as Main-board structure per IDX page | Maybank says ETF, DIRE, DINFRA are 10%/10% | A for ETF/REIT; both right for DINFRA | IDX page rows; April 2025 reports say the 15% ARB covered ETF and DIRE; older IDX page copy shows ETF/DIRE at 35/25/20 with 15%. DINFRA is 10%/10% everywhere |
| Reference price | "Previous price" list from IDX page | "Acuan Harga", not defined | A | IDX page lists the four inputs; "previous day's close" from Brights and calcuid |
| Rounding | Unverified convention: ARA floor, ARB ceil | Same, unverified | Both flagged it correctly; the convention is right | 20 observed limit prices match; six differ clearly from round-to-nearest (section 8). A's BBCA inference (ref 5,175 to 4,820) is confirmed by the Katadata 10-16 close |
| Tick used at band crossings | Own band of the limit price (assumed) | Same | Both | BBCA 4,820 versus 4,825 |
| ARB at R = 1 | Ambiguous, floored at Rp1 | Ambiguous, likely 1 | Both | Minimum price Rp1; two separate rejection conditions |
| 10-19, R = 11 to 14 | ARB = R (no downside) | Ambiguous | A | 7% of Rp11-14 is below Rp1; the next-day amendment replaces 7% by Rp1 for that band |
| Prior regime | Kep-00003/BEI/04-2025, since 2025-04-08 | Not checked | A | Katadata (revoked by Kep-00136); April 2025 reports |
| Tick table history | Not verified before 09-28 | Cermati says unchanged | B, and more: same table in the Kep-00196/BEI/12-2024 era | Older IDX page copy (BCA FAQ), Brights |
| 2027 | Announced symmetric plan, low confidence | Unresolved | B; legal pass "scheduled but subject to evaluation" is the best wording | Section 9. A's 2027 row is only the conditional September plan |
| Effective date of Kep-00158 | 10-20 | 10-20 | Both | IQPlus text, RCTI+, Bareksa, Republika, Kabarbursa. A search snippet that said "sejak 19 Oktober" for Kep-00158 was quoting the Kep-00157 wording |
| Legal pass: OJK "reportedly said the same" | n/a | n/a | Confirmed | Wartaekonomi and Bisnis, 2026-11-06, quoting the 2026-11-05 press conference |
| Legal pass: first 2027 session 2027-01-04 | n/a | n/a | Consistent | RCTI+ 2027 calendar (01-01 and 01-05 are holidays) |

## 12. Checklist for the test author

Assert (CONFIRMED): the period table and date lookup; the band/limit table for Main, Development and New Economy (section 2.1); Acceleration, Special Monitoring and DINFRA 10%/10% (2.2, 2.4); the tick table and minimum price (4); the algorithm; the rows of sections 7.1 and 7.2 except those that depend on U3 or U4 (rows listed under "Things this table pins down" and R = 1) and except P2 with R = 11 to 14 (U5, not asserted); the anchors in section 8. Section 7.3 (other boards) is REPORTED because the rounding convention is assumed to carry over.

Assert with a "reported" label: R = 1 ARB; the own-band tick rows (R = 500, 4990, 5001†, 5025); section 7.3; ETF/REIT in P3.

Do not assert: anything about the exchange's rule on or after 2027-01-01 (the code's labelled convention in CONTRACT.md section 3 may be asserted as a convention); ARB on 2026-10-19 for a reference of Rp11-14 (U5); ETF/REIT in P1 and P2; IPO, warrant and rights limits; the last session date of P3; the order-volume rule together with price limits.

Use references that are valid ticks unless the test is about arithmetic boundaries (the daggered rows).

## 13. Source log

Official (read directly, 2026-11-09):
- IDX trading mechanism page (HTML parsed): https://www.idx.id/en/products-services/trading-hours-and-mechanism/
- IDX regulation register: https://www.idx.id/id/peraturan/peraturan-bei/
- IDX release repost, 19 Oct (Kep-00157): https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-batas-bawah-auto-rejection-efek-bersifat-ekuitas
- IDX release repost, 20 Oct (Kep-00158): https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-kembali-batas-bawah-auto-rejection-efek-bersifat-ekuitas
- Older IDX page copy (Kep-00196/BEI/12-2024 era; 15% ARB; effective 2025-04-08): https://bcasekuritas.co.id/en/help/faq/equities-trading-mechanism

News and broker (graded as stated):
- Katadata, 2026-09-21, Kep-00136 with previous, phase 1 and phase 2 tables: https://katadata.co.id/finansial/bursa/6ab0fe985f085/harga-minimum-saham-jadi-rp-1-mulai-pekan-depan-auto-rejection-disesuaikan
- NH Korindo (tables, quote on 2027, DINFRA): https://www.nhis.co.id/idx-regulations/
- Maybank Trade, 2026-09-22 (ticks, PR 083/BEI.SPR/09-2026, volume rule): https://www.maybanktrade.co.id/berita/aturan-saham-rp1-berlaku-28-september-2026-apa-yang-berubah/
- Maybank Trade, 2026-10-20 (7% examples Rp93, Rp930, Rp9,300): https://www.maybanktrade.co.id/berita/arb-saham-jadi-7-mulai-hari-ini-hingga-akhir-2026/
- Cermati: https://invest.cermati.com/artikel/perubahan-harga-minimum-saham-dan-batas-auto-rejection
- hukumonline (garbled table, rejected): https://www.hukumonline.com/berita/a/bei-berlakukan-batasan-harga-minimum-rp1-dan-penyesuaian-auto-rejection-lt6aba102e29b53
- Global Exchanges: https://globalexchanges.com/latest-news/indonesia-idx-adjusts-minimum-price-and-auto-rejection-limits-for-equity-securities/145803/
- Bareksa, 2026-10-19: https://www.bareksa.com/berita/saham/2026-10-19/bei-pangkas-batas-arb-saham-jadi-7-dari-15-berlaku-mulai-19-oktober-2026
- Antara, 2026-10-19 10:22: https://www.antaranews.com/berita/5795785/bei-turunkan-batas-arb-saham-jadi-7-persen-demi-jaga-volatilitas-pasar
- Fortune IDN, 2026-10-19 08:53: https://www.fortuneidn.com/market/jaga-volatilitas-pasar-bei-ubah-arb-saham-jadi-7-persen-00-3dhnm-7svyth
- Bareksa, 2026-10-20: https://www.bareksa.com/berita/saham/2026-10-20/bei-ubah-lagi-aturan-arb-mulai-20-oktober-saham-rp11rp14-dibatasi-turun-rp1
- RCTI+/IDXChannel, 2026-10-20 08:20: https://www.rctiplus.com/news/detail/idxchannel/5497737/bei-sesuaikan-ketentuan-arb-saham-rp11-rp14-jadi-rp1--berlaku-mulai-20-oktober-2026
- Beritasatu, 2026-10-20 08:34: https://www.beritasatu.com/ekonomi/3035025/bei-sesuaikan-lagi-batas-arb-saham-mulai-20-oktober
- Republika, 2026-10-20 10:22: https://ekonomi.republika.co.id/berita/tn6s16370/bursa-efek-indonesia-perbarui-ketentuan-auto-reject-bawah-untuk-saham-harga-rendah
- Fortune IDN, 2026-10-20 15:00 (Rp11-14 explained as similar to Rp1-10): https://www.fortuneidn.com/market/bei-revisi-batas-arb-saham-rp11-rp14-mulai-20-oktober-2026-d7w02-00-fykp7-xpgb46/amp
- Katadata, 2026-10-19 (BBCA): https://katadata.co.id/finansial/bursa/6ad591c732eaa/bca-bbca-gelar-buyback-setelah-saham-arb-2-hari-beruntun
- CNBC Indonesia, 2026-10-19 (351 ARB stocks, price anchors): https://www.cnbcindonesia.com/market/20261019174233-17-777615/batas-auto-reject-turun-351-saham-arb-hari-ini/amp
- investortrust.id, 2026-09-28 (Rp43): https://investortrust.id/market/117612/deretan-saham-anjlok-hingga-arb-ke-level-rp-43-usai-harga-minimum-jadi-rp-1-ada-goto-hingga-bcap
- investortrust.id, 2025-10-22 (ARA anchors): https://investortrust.id/market/82996/ihsg-ditutup-berbalik-anjlok-1-04-sebaliknya-12-saham-dipimpin-niro-hingga-pgun-cetak-ara
- Bisnis Insight, 2026-09-24 (Irvan Susandy on 2027): https://bisnisinsight.com/detail/922657/bei-belum-pastikan-auto-rejection-simetris-jalan-awal-2027-tunggu-kondisi-pasar
- emitennews, 2026-09-23 (Irvan Susandy): https://www.emitennews.com/news/bei-ungkap-alasan-pencabutan-arb-asimetris-15-mulai-1-januari-2027
- Wartaekonomi, 2026-11-06 (OJK, 2026-11-05): https://wartaekonomi.co.id/read646192/ojk-batasi-arb-7-hingga-akhir-2026
- Bisnis, 2026-11-06 headline (OJK; page blocked): https://market.bisnis.com/read/20261106/7/2019143/ojk-tekankan-arb-15-jadi-7-hanya-berlaku-sampai-31-desember-2026
- RCTI+ 2027 holiday calendar: https://www.rctiplus.com/news/detail/ekonomi/5474667/dear-investor--ini-kalender-libur-bursa-efek-indonesia-2027
- calcuid (third party; states Rule II-A has no rounding formula): https://calcuid.com/saham/ara-arb/
- Brights (previous close as reference price): https://www.brights.id/en/education/learn-investment/trading-mechanism

Working files from the research passes, for reference only: spec_A.md, spec_B.md, post2026_basis.md in the same directory as this file.
