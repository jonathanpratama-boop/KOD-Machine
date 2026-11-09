# Official-source recheck of SPEC_FINAL (IDX auto rejection)

Prepared 2026-11-09 by the official-source rechecker. All times are UTC (WIB = UTC+7).
Looked between 2026-11-09T05:43:50Z and 2026-11-09T06:03:23Z (12:44 to 13:03 WIB, a trading day in progress).

How I looked
- Tools: WebFetch and WebSearch only. After a 403 or a bot check I did not retry or work around it (no headers, proxies or mirrors).
- Each fetch has `date -u` stamps taken just before and just after it ("window"). Where the second stamp was issued in the same tool block as the fetch, it marks the start of the call, not its end; the answer came back within about 10 seconds after it. Windows are therefore accurate to about 10 seconds.
- WebFetch passes a page through a small summarising model that would not quote more than about 125 characters at a time. Table cells below are therefore that model's restructured transcription, not raw HTML. I asked for the auto-rejection table in three separate queries on the same URL (05:44:50Z, 05:44:58Z-05:45:55Z, 06:00:21Z) and for the tick table in two (05:50:40Z, 06:00:21Z); the answers agree. Some of these may have been served from the tool's 15-minute cache, so I do not claim any of them is an independent fresh copy.
- "Search summary" = text produced by WebSearch; the page itself was not opened.
- One exception to "WebFetch only", stated plainly. The register page (item 1) shows WebFetch only a navigation shell. A sibling process in this directory (its working log is headed "NEWS RECHECK") saved the register's raw HTML (three captures, file mtimes 05:49:35Z, 05:57:18Z and 06:04:18Z, all with the identical sha256 2d61d62331219d4f421d76130be195dcafcda524318d09aa0112cbfa3edd0a52, 165,587 bytes; the third appeared in the directory after I had written the first draft and I compared it by hash at 06:04:51Z). I did not fetch it (that process's working log, fetch_log.txt in this directory, records two curl runs at 05:49:34Z and 05:57:17Z, matching the first two mtimes I checked with stat; I have not seen a log line for the third). I parsed the saved copy read-only at 06:00:05Z; the register facts below come from that copy.

## 1. Verdict

1. No change found to any rule that SPEC_FINAL asserts (period table P0-P3, sections 2.1, 2.2, 2.3-2.5, 4). The IDX trading-hours page matches the spec cell for cell (section 3). P0 and P1 were not re-read from primary sources beyond what the IDX page and the October releases show; nothing I read contradicts them.
2. Nothing confirmed after 2026-12-31 has appeared. Newest official wording: OJK SP 219/OJK/DKPU/XI/2026 (dated 2026-11-05, read on ojk.go.id): the 7% ARB applies "hingga 31 Desember 2026"; nothing about afterwards. IDX's own 20 Oct release says the rule "akan dievaluasi kembali sebagai bahan pertimbangan dalam menentukan keberlanjutan penerapannya" (evaluated again as input for deciding whether it continues). No report of an extension, of a confirmed symmetric plan, or of any rule for 2027.
3. No IDX press release about auto rejection dated after 2026-11-05 was found (35 searches, the BCA Sekuritas latest-news list, the Bareksa auto-rejection tag page). The IDX press-release list itself cannot be read (client-rendered shell).
4. Register (from the saved raw HTML): the in-force Rule II-A is still "II-A Kep-00158/BEI/10-2026", attachment 1,420 KB, file name suffix 261020; the register's attachment link is https://www.idx.co.id/Media/stumk2gi/signed_peraturan_nomor_ii_a_tentang_perdagangan_efek_bersifat_ekuitas-261020.pdf, identical to the URL in the spec's U1. The highest 2026 Kep number in the register is 00158; there is no Kep-00159 or later and no entry with a "-11-2026" suffix. Kep-00136 and Kep-00157/BEI/10-2026 are not listed; Kep-00137 and Kep-00158 are. This matches what the spec says about the register.
5. One correction to the spec wording (no rule changes): a decree number above 00158 does exist. Kep-00160/BEI/11-2026, dated 2026-11-02, amends the monthly share-registration report rules (SK LBRE). BEI and KSEI announced it on 2026-11-04 (Pasardana 2026-11-04 22:54, IDX Channel 2026-11-05 06:02 WIB; both read). Neither article mentions II-A, ARA or ARB, and it is not in the register. No source mentions Kep-00159. So section 9 fact 5 ("no report ... of a new decree number after Kep-00158") should read "no new Rule II-A decree".
6. I could not read any decree text (the II-A PDF returns HTTP 403 to me, as it did for the spec). U1, U2 and U13 are unchanged.

## 2. What I checked (result and fetch time)

| # | Check | Source | Window (UTC) | Result |
|---|---|---|---|---|
| 1 | Register: II-A entry, 2026 Kep numbers, anything newer than Kep-00158, listing of 00136/00137/00157/00158, attachment suffix | https://www.idx.id/id/peraturan/peraturan-bei/ | WebFetch 05:43:50Z-05:43:56Z and 05:43:56Z-05:44:24Z; saved raw HTML 05:49:35Z and 05:57:18Z, parsed 06:00:05Z | WebFetch: shell only (about 1,100 characters: menu, breadcrumb, disclaimer, three tab labels Peraturan Pencatatan / Perdagangan / Keanggotaan, feedback box; zero entries; no date). The list sits in an inline script (`window.__NUXT__`) that WebFetch drops. Saved HTML: 50 entries, 12 from 2026 (see 4.1). II-A = Kep-00158/BEI/10-2026, 1,420 KB, suffix 261020. |
| 2 | Trading hours and mechanism: AR table, tick table, dates, 2027 | https://www.idx.id/en/products-services/trading-hours-and-mechanism/ | 05:44:50Z-05:44:58Z (tables); 05:44:58Z-05:45:55Z (headings, footnotes; maybe cached); 05:50:40Z-05:51:07Z (tick table; maybe cached); 06:00:21Z-06:00:27Z (full re-read of all tables; maybe cached) | Identical to the spec (section 3). No date, no "2027", no "symmetric", no "31 December", no "last updated". Cites Kep-00158/BEI/10-2026 for II-A (trading hours and price fraction). |
| 3 | IDX press-release list | https://www.idx.id/id/berita/siaran-pers/ | 05:46:35Z-05:47:04Z | Shell only, no entries. Not readable. |
| 4 | IDX release of 20 Oct (Kep-00158), as reposted by IQPlus on BCA Sekuritas | https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-kembali-batas-bawah-auto-rejection-efek-bersifat-ekuitas | 05:48:21Z-05:49:00Z | Same as spec: Rp11-14 from 7% to Rp1,00; Kep-00158 replaces Kep-000157; Papan Utama, Pengembangan, Ekonomi Baru; Akselerasi and Pemantauan Khusus "tetap mengacu" to their own rules; "berlaku efektif mulai 20 Oktober 2026 sampai dengan 31 Desember 2026". No 2027, no "simetris". |
| 5 | IDX release of 19 Oct (Kep-00157), same repost | https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-batas-bawah-auto-rejection-efek-bersifat-ekuitas | same window | Same as spec: ARB 7%; Kep-00157/BEI/10-2026 replaces Kep-00136/BEI/09-2026; "efektif diberlakukan sejak 19 Oktober 2026 sampai dengan 31 Desember 2026, dan akan dievaluasi kembali mengikuti perkembangan yang terjadi di pasar". No 2027. |
| 6 | OJK release SP 219/OJK/DKPU/XI/2026 (dateline Jakarta, 5 Nov 2026; RDKB of 28 Oct) | https://www.ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/RDKB-Oktober-2026.aspx | 05:53:02Z-05:53:59Z (two calls; 112,323 characters read in full) | One ARB sentence: ARB adjusted "dari sebelumnya 15 persen menjadi 7 persen yang berlaku hingga 31 Desember 2026"; buyback without RUPS extended to 30 Jun 2027. No decree number, no Rp11-14, no word on after 2026. |
| 7 | OJK SP 196 (2026-10-21) and SP 201 (2026-10-26) | ojk.go.id (two pages) | 05:52:41Z-05:53:02Z | No mention of ARB or 31 Dec 2026. |
| 8 | Wartaekonomi, "OJK Batasi ARB 7% hingga Akhir 2026" | https://wartaekonomi.co.id/read646192/ojk-batasi-arb-7-hingga-akhir-2026 | 05:51:07Z-05:51:50Z | Printed "Jum'at, 06 November 2026, 19:33 WIB"; OJK Chair spoke at the RDKB press conference Thu 5 Nov; 7% "hanya berlaku hingga 31 Desember 2026"; Rp1-10 "tetap menggunakan batas ARB sebesar Rp1", Rp11-14 "juga menggunakan batas ARB nominal sebesar Rp1"; cites Kep-00157 dated 19 Oct. No "simetris", no "evaluasi", 2027 only for the buyback. As in the spec. |
| 9 | calcuid ARA/ARB page | https://calcuid.com/saham/ara-arb/ | same window | "Terakhir diverifikasi 25 September 2026"; covers Kep-00136 only (no Kep-00157/00158). See 4.4. |
| 10 | Katadata 2026-07-07 12:40 and Emitennews 2026-09-25 13:28 WIB | katadata.co.id (6a4c916ae8db7), emitennews.com | 05:51:55Z-05:52:21Z | Background on the Watchlist board. See 4.5. |
| 11 | Pasardana 2026-11-04 22:54 and IDX Channel 2026-11-05 06:02 WIB | pasardana.id, idxchannel.com | 05:54:43Z-05:55:23Z | Kep-00160/BEI/11-2026 (2 Nov 2026), LBRE; no II-A, no ARB. |
| 12 | BCA Sekuritas latest-news list, page 1 | https://bcasekuritas.co.id/latest-news/news | 05:47:33Z-05:48:07Z; again 06:03:16Z-06:03:23Z | Both looks: only items dated 09 Nov 2026 (the feed had moved on between them), none on BEI rules, ARB, auto rejection, OJK or Kep. The news-recap box lists "Bursa Efek Indonesia Turunkan Batas ARB Menjadi 7%" (undated there; its page title per the search listing is the 19 Oct story; not opened). |
| 13 | Bareksa auto-rejection tag page | https://www.bareksa.com/berita/tag/auto-rejection | 05:49:21Z-05:49:55Z | Ten of 16 entries shown; newest "20 Okt" (Rp11-14 story); nothing later. |
| 14 | 35 WebSearch queries (Indonesian and English; decree numbers 00159 to 00163, "BEI.SPR/10-2026", "BEI.SPR/11-2026", "BEI.POP/11-2026"; ARB 2027, symmetric, extension, postponement; OJK, Hasan Fawzi, Jeffrey Hendrik, Irvan Susandy; idx.co.id and idx.id domain filters) | WebSearch | 05:45:55Z-05:57:12Z | Newest ARB item anywhere: the OJK material of 5-6 Nov. No IDX or OJK item dated after 2026-11-06 on ARB. No hit at all for Kep-00159. |

Not reachable (recorded, not retried): see section 5.

## 3. IDX trading-hours page versus SPEC_FINAL (cell by cell)

Printed labels: columns "Securities", "Price Range", "Auto Rejection (AR)", "Upper AR", "Lower AR", "Volume". Lead-in: "Based on the prevailing Exchange Regulation, that the Auto Rejection percentage limits are as follows:". No date anywhere near the table.

### 3.1 Main, New Economy and Development boards (spec 2.1, column P3; group label printed "Main Board, New Economy Board, and Development Board")

| Band as printed | Upper AR | Lower AR | Spec P3 (ARA / ARB) | Same |
|---|---|---|---|---|
| IDR1.00 to IDR10.00 | IDR1.00 | IDR1.00 | +Rp1 / -Rp1 | yes |
| IDR11.00 to IDR14.00 | 35% | IDR1.00 | 35% / -Rp1 nominal | yes (printed like the Rp1-10 cells) |
| IDR15.00 to IDR200.00 | 35% | 7% | 35% / 7% | yes |
| >IDR200.00 to IDR5,000.00 | 25% | 7% | 25% / 7% | yes |
| >IDR5,000.00 | 20% | 7% | 20% / 7% | yes |

### 3.2 Other groups

| Group as printed | Rows as printed | Spec | Same |
|---|---|---|---|
| Acceleration Board and Watchlist Board | IDR1.00 to IDR10.00: IDR1.00 / IDR1.00; >IDR10.00: 10% / 10% | 2.2: Rp1-10 +-Rp1; above Rp10 10% / 10% | yes |
| ETF and REITs (DIRE) | 1-10: IDR1.00 / IDR1.00; 11-14: 35% / IDR1.00; "IDR11.00 to IDR200.00": 35% / 7%; >200-5,000: 25% / 7%; >5,000: 20% / 7% | 2.3 (including the "Rp11 to Rp200" typo) | yes |
| Infrastructure Investment Funds (DINFRA) | 1-10: IDR1.00 / "IDR1,00"; >IDR10.00: 10% / 10% | 2.4 | yes (comma typo is cosmetic) |
| Right Issue | all ranges: dashes | 2.5: no limits | yes |
| Warrants, first listing day | upper cell "at or above the last traded price of the underlying", lower cell a dash | 2.5 | yes |
| Warrants after first day | 1 to 9: IDR10.00 (other cell a dash); >9-200: 50% / 50%; >200-5,000: 40% / 40%; >5,000: 30% / 30% | 2.5 | yes (the model said column alignment of the first rows is unclear) |
| Volume column | ">50,000 Lot or >5% of listed shares", shown in the first row only in the text I received | 2.6 | not checkable: the flattened text cannot show whether the cell spans all rows (the spec's rowspan 21 came from raw HTML, which I did not read) |

### 3.3 Tick table (spec section 4)

Heading "Price Fraction Scale"; column headers "Price Fraction" and "Maximum Price Movement*" (the asterisk has no footnote text). Rows as printed, tick and maximum step:

| Price range as printed | Tick | Max step | Spec 4 | Same |
|---|---|---|---|---|
| <200,- | IDR1,- | IDR10,- | below Rp200: 1 / 10 | yes |
| IDR200,- < IDR500,- | IDR2,- | IDR20,- | 200 to <500: 2 / 20 | yes |
| IDR500,- < IDR2.000,- | IDR5,- | IDR50,- | 500 to <2,000: 5 / 50 | yes |
| IDR2.000,- < IDR5.000,- | IDR10,- | IDR100,- | 2,000 to <5,000: 10 / 100 | yes |
| >= IDR5.000,- | IDR25,- | IDR250,- | 5,000 and above: 25 / 250 | yes |

Sentences on the page: "Stock step value and its maximum price step are valid for one entire trading day"; adjusted next day if the close falls in another price range; "The maximum price step should not exceed the percentage of Auto Rejection limit." The page states no minimum price (the spec's minimum-price facts come from news sources, so no conflict).

### 3.4 Reference price (spec section 3) and decree citations

Reference Price used to set the upper and lower limit in the regular market: previous price; theoretical price of a corporate-action result; initial price of a first listing; fair value set by a business appraiser (same four bases as the spec; the earlier read also showed the POJK 35/POJK.04/2020 reference). Decree citations: "II-A Kep-00158/BEI/10-2026" (trading hours; price fraction); other decrees on the page are unrelated topics (Kep-00316/BEI/11-2023 Watchlist full call auction; Kep-00056/BEI/03-2023 derivatives).

### 3.5 Differences, validity date, 2027

- Differences in any value: none.
- Cosmetic only: tick-table labels "Price Fraction" / "Maximum Price Movement*" (spec says "Tick" / "Maximum price step"); DINFRA lower cell "IDR1,00"; warrant board labels with misplaced brackets.
- Any mention of a validity date, 2027, "symmetric", "31 December", "effective", "as of" or "updated": none (searched in the 06:00Z read).

## 4. Found, not in the spec (none changes an asserted rule)

4.1 Register contents, from the saved raw HTML (50 entries). 2026 decrees listed, by number: III-P Kep-00022/02-2026; III-B Kep-00023/02-2026; III-H Kep-00024/02-2026; I-C Kep-00064/04-2026; II-C Kep-00065/04-2026; III-L Kep-00066/04-2026; II-E Kep-00088/06-2026; II-O Kep-00137/09-2026; I-X Kep-00139/09-2026; II-X Kep-00140/09-2026; I-A Kep-00152/10-2026; II-A Kep-00158/10-2026. II-V is still Kep-00084/BEI/10-2019. String-match trap: the register also contains "II-H Kep-00157/BEI/10-2024", "III-I Kep-00160/BEI/10-2024" and "III-D Kep-00161/BEI/10-2024" (2024 decrees). A naive search for "Kep-00157" or "Kep-00160" finds these; they are not the 2026 decrees. No "Kep-00136" string at all. No year-suffix "-11-2026" or "-12-2026".

4.2 Kep-00160/BEI/11-2026 (see verdict 5). Kep-00159: no source found in any search.

4.3 Official OJK text for the 2026-12-31 validity (SP 219, row 6). The spec relied on press reports of the 5 Nov press conference; the OJK release is now read directly.

4.4 calcuid (third party, data as of 2026-09-25, Kep-00136 only): says the Rule II-A attachment itself contains the symmetric limits and that Kep-00136 "menangguhkan klausul lampiran itu sampai 31 Desember 2026" (suspends that attachment clause until 31 Dec 2026), with the 15% transition table in the decree body, not the attachment; "mulai 1 Januari 2027 batas bawah sama besar dengan batas atas". It links the signed decree PDF and says its table is copied from the decree, but gives no read date for Kep-00136. Relevance: a lead on U13 (whether Kep-00157/00158 kept the 2027 table). It predates Kep-00157/00158 and I could not check the decree. Nothing to assert; section 9 guidance stands.

4.5 Watchlist board (spec 2.2). Katadata 2026-07-07 12:40: BEI is preparing refinements to the special-monitoring board rules, including "batas atas dan bawah auto rejection ... yang lebih berjenjang"; still in rule making and public hearing; the page gives no numbers. Emitennews 2026-09-25 13:28 WIB: BEI President Director Jeffrey Hendrik hopes the FCA-rule evaluation is done "di akhir tahun"; no new date; nothing on ARB 2027. Search summaries (pages not read) mention banded 35/25/20 percent figures for that proposal. None enacted: the IDX table fetched today still shows 10% / 10%.

4.6 Exact wording of the IDX releases. 20 Oct (Kep-00158): "Ketentuan ini berlaku efektif mulai 20 Oktober 2026 sampai dengan 31 Desember 2026 dan akan dievaluasi kembali sebagai bahan pertimbangan dalam menentukan keberlanjutan penerapannya". 19 Oct (Kep-00157): "efektif diberlakukan sejak 19 Oktober 2026 sampai dengan 31 Desember 2026, dan akan dievaluasi kembali mengikuti perkembangan yang terjadi di pasar". The spec prints "berlaku mulai 20 Oktober hingga 31 Desember 2026" in quotation marks for P3, which is not the wording of the IQPlus text I read (it may come from another outlet), and its "akan dievaluasi kembali mengikuti perkembangan pasar" matches the 19 Oct release, not the 20 Oct one. The 20 Oct wording is the stronger one for section 9: whether the rule continues is to be decided after an evaluation. If the spec's quotes are reproduced verbatim in code comments or test docstrings, re-source them. The 20 Oct release also prints the register URL for the latest II-A: www.idx.co.id/id/peraturan/peraturan-bei/.

4.7 Wartaekonomi (6 Nov) uses the word "nominal" for the Rp11-14 ARB, a further press source for U14 (decree wording still unread).

## 5. Not reachable or not verified

- Register through WebFetch: shell only (twice). Facts in 4.1 rest on the saved raw HTML described above, not on a fetch of mine.
- https://www.idx.id/id/berita/siaran-pers/ : shell only.
- https://www.idx.co.id/id/produk/mekanisme-dan-jam-perdagangan (Indonesian trading page): HTTP 403, 05:48:07Z-05:48:14Z.
- https://www.idx.co.id/Media/stumk2gi/signed_peraturan_nomor_ii_a_tentang_perdagangan_efek_bersifat_ekuitas-261020.pdf (in-force II-A): HTTP 403, 05:51:50Z-05:51:55Z. One attempt only.
- investasi.kontan.co.id article "BEI Berlakukan ARB 7% hingga Akhir 2026": HTTP 403.
- Bisnis: bisnis.com/read/20260706/... HTTP 403 (my slip: I typed the host as bisnis.com, not market.bisnis.com); market.bisnis.com/read/20261026/... HTTP 403 (05:57:12Z). Their content is known only from search summaries (for example a statement attributed to OJK's Hasan Fawzi that "the policy" could be applied again if the market needs further stabilisation; the summary does not make clear whether that means the 7% ARB, the buyback measure or both; search summary, not read).
- kabarbursa.com article on the Watchlist-board evaluation: bot-check page ("One moment, please...").

## 6. Limits

- A trading day was in progress. An IDX release later on 2026-11-09, or any day after, would not be seen. Repeat the check before relying on this, in particular late December and around Mon 2027-01-04.
- "Not found" means not found by this search engine and these fetches, not that nothing exists. Search coverage of idx.co.id and idx.id is thin.
- The WebFetch cells go through a small model (see top). The register facts rest on a copy saved by another process.
- Decree texts were not read, so rounding wording, reference-price wording and any 2027 clause remain unverified.

## 7. Final re-check

- 06:00:21Z-06:00:27Z: IDX trading-hours page read again in full (all groups, tick table, keyword search). Same as at 05:44Z; no date, no 2027, no "symmetric".
- 06:03:16Z-06:03:23Z: BCA Sekuritas latest-news list read again. The feed had moved on (different items than at 05:47Z), all dated 09 Nov 2026; none about BEI rules, ARB or OJK. The news-recap box is unchanged.
- Register: the three saved captures (05:49:35Z, 05:57:18Z, 06:04:18Z) are byte-identical, so the register did not change between 05:49Z and 06:04Z. I parsed the second one in full (06:00:05Z) and did not re-parse the others, relying on the identical hash.
- Nothing changed between my first look (05:43:50Z) and my last (06:03:23Z).
