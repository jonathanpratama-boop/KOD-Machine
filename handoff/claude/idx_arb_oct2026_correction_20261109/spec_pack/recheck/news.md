# News recheck of SPEC_FINAL: IDX lower auto-rejection (ARB) and related price rules

Rechecker: NEWS RECHECKER (subagent). Subject: /tmp/claude-0/-home-user/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad/arb2/spec_pack/SPEC_FINAL.md (sections 1, 2.1, 2.2, 4, 9, 10 read first; whole file read).

Looked between **2026-11-09T05:44:13Z and the end of the final sweep (about 06:05Z, section 11)** (WIB = UTC+7, so 12:44 WIB onward on Monday 2026-11-09; IDX session II had not opened when I started, so Monday's close is NOT covered).

Dates in this file are 2026 unless a year is written. "Read" means I read the page text returned by WebFetch (or, for the IDX register, the raw HTML fetched with curl). "Search summary only" means I saw it only inside a WebSearch result, which is a model-written summary and not the page; I never rely on those for a fact without saying so.

## 0. Bottom line

1. **Nothing was found that changes or extends any dated rule in SPEC_FINAL.** The facts in section 1 (P1 Kep-00136, P2 Kep-00157, P3 Kep-00158, nothing confirmed from 2027-01-01) stand as of the times above.
2. **No new BEI decree.** The IDX regulation register (raw HTML, fetched three times, 05:49:34Z, 05:57:17Z and 06:04:17Z; the three files have the same SHA-256) lists "II-A Kep-00158/BEI/10-2026" (attachment 1,420 KB, file suffix 261020) as the in-force Rule II-A. No 2026 decree is numbered above 00158 and none is dated 11-2026. Rule II-V (Acceleration board) is still Kep-00084/BEI/10-2019, II-O Kep-00137/BEI/09-2026, II-X Kep-00140/BEI/09-2026.
3. **No statement from BEI or OJK about ARB after 2026-12-31 was found.** The newest ARB-rule item anywhere I looked is OJK's own press release **SP 219/OJK/DKPU/XI/2026 of 2026-11-05** (read directly): ARB 15% to 7% "yang berlaku hingga 31 Desember 2026". It says nothing about evaluation, market scope or a 2027 ARB. This matches SPEC_FINAL section 9 item 4.
4. **No extension of 7%, no reversion to 15%, no confirmation or cancellation of the symmetric 2027 plan, no BEI director statement on 2027** was found (many phrasings, Indonesian and English; section 8). Irvan Susandy: nothing newer than the 2026-09-23 remarks already in the spec (his newest search hit is dated 2026-07-28 and is about something else). Jeffrey Hendrik (BEI President Director): 2026-10-19 evaluation remarks and a 2026-11-06 statement on three MSCI-related measures that does not mention ARB.
5. **No change found to the Rp1 minimum price, the Rp11-14 rule or the order-volume rule.** The IDX trading-mechanism page (read 05:45Z) still shows Rp11-14 lower limit "IDR1.00", 7% for Rp15 and above on the Main/Development/New Economy boards, 10%/10% for Acceleration and Watchlist, and the Volume cell ">50,000 Lot or >5% of listed shares".
6. **One scheduled event that could change things within days:** MSCI's November 2026 Index Review results are due 11 Nov (CET) = **Thu 2026-11-12 05:00 WIB** (IDXChannel, 2026-11-09). BEI changed the ARB twice within two sessions of MSCI's 15/16 Oct announcement (Kep-00157 on Mon 10-19, Kep-00158 on Tue 10-20). I have no evidence BEI is planning anything; I flag the precedent only. Re-run this recheck after 2026-11-12 before relying on "nothing after 2026-11-09 is known".
7. **Market check (third-party price data, not news).** The 2026-10-29 to 2026-11-06 closes I could read are consistent with SPEC_FINAL P3: BRPT closed exactly at the spec's 7% ARB formula on 6 of 6 ARB-type sessions; TAXI fell only in Rp1 steps in the Rp11-14 band; NAYZ closed exactly at a 10% ARB four sessions in a row (so it is on a 10% board). **One observation I could not explain from sources I read: LFLO on 2026-11-06 closed at 620 from 670 (-7.46%), which is below the 7% ARB (625) and within a 10% ARB (605).** That fits only if LFLO is on a 10% board (search summaries say Acceleration Board; I could not confirm it from a page I read) or if its reference price was adjusted. Do not use LFLO as a P3 anchor; see section 4.

## 1. When I looked (UTC, 2026-11-09)

Every `date -u` reading was taken at the **start** of a tool block. The fetches and searches in that block ran in the next one to two minutes, before the next block's reading. So each fetch is dated by its batch window [reading at start of batch, reading at start of next batch]. The full working log is in fetch_log.txt in the same folder. Files I wrote in this folder: news.md, fetch_log.txt, and the downloaded register copies in raw_register/, raw_register2/, raw_register3/ (untrusted data, never executed). official.md in the same folder is not mine and I did not read or use it.

| Batch | Window (UTC) | What ran |
|---|---|---|
| 0 | 05:43:37Z | spec read, folder created |
| 1 | 05:44:13Z to 05:45:02Z | 8 searches (ARB 2027, extension, symmetric, English, Kep-00158, Irvan Susandy, OJK, MSCI) |
| 2 | 05:45:02Z to 05:46:19Z | 6 searches; IDX mechanism page; IDX register (WebFetch, menus only); Wartaekonomi |
| 3 | 05:46:19Z to 05:47:33Z | 6 searches; Bisnis (403), Kontan (403), Katadata, Fortune IDN, IDXChannel, Infobanknews, Jakarta Globe |
| 4 | 05:47:33Z to 05:49:34Z | 4 searches; Databoks x2, OJK SP 201, Kabar Bursa x2 (bot check), BCA latest-news, IDXChannel/Katadata/Bareksa indexes |
| 5 | 05:49:34Z to 05:51:21Z | curl of IDX register (05:49:34Z to 05:49:35Z); MSCI IR (403); IDX release reposts (BCA) x2; CNBC, Antara, Investortrust (404), IDX press page (403); 7 searches |
| 6 | 05:51:21Z to 05:52:03Z | decode of saved register; IDXChannel MSCI week pieces x3; Bareksa; CNBC; Ajaib x2 (403); 5 searches |
| 7 | 05:52:03Z to 05:53:13Z | Katadata "3 jurus"; Bareksa x2; CNBC; 4 searches |
| 8 | 05:53:13Z to 05:54:23Z | BCA board-rotation; IDXChannel page 2; Bareksa part 2; 4 searches |
| 9 | 05:54:23Z to 05:56:13Z | OJK SP 219; five tag pages; Databoks tag; KSEI x2; 2 searches |
| 10 | 05:56:13Z to 05:57:17Z | stockanalysis.com histories NAYZ, LFLO, TAXI; 6 searches |
| 11 | 05:57:17Z to 05:58:01Z | curl of IDX register again (05:57:17Z to 05:57:18Z); BCA; Pasardana; Pluang; 2 searches |
| 12 | 05:58:01Z to about 06:00Z | BCA special-monitoring notices x3; stockanalysis.com JPFA, BRPT; local arithmetic check |
| 12b | about 06:00Z to 06:04Z | report drafted; 2 more searches (uncached); partial reads completed (OJK SP 219 tail, Bareksa x2) |
| 13 | 06:04:17Z to about 06:05Z | final sweep after the fetch tool's 15-minute cache expired (section 11) |

Cache note: the fetch tool caches a URL for 15 minutes. These repeats returned the cached copy of the earlier fetch, so their effective read time is the earlier window: IDXChannel market-news (batch 5 = batch 4 copy), Bareksa saham index (batch 6 = batch 4), CNBC market (batch 6 = batch 5), BCA latest-news (batch 11 = batch 4).

One tool deviation, disclosed: the IDX regulation register page returned HTTP 200 but WebFetch showed only menu text (the decree list is inside an escaped JSON block in the HTML). I fetched that one public page with plain `curl` (no special headers, default proxy) three times (05:49:34Z, 05:57:17Z, 06:04:17Z), saved the copies under raw_register/, raw_register2/ and raw_register3/ in this folder (identical SHA-256), and decoded them locally. I did not retry anything that had returned 403, and I used no mirror of any blocked document.

## 2. What I could not read (not reachable or not usable)

| Source | Result | Consequence |
|---|---|---|
| market.bisnis.com (tried /read/20261106/7/2019119, IHSG close 6 Nov) | HTTP 403 (batch 3) | Bisnis not read. The 2026-11-06 Bisnis OJK article (…/2019143/…) was not fetched by me (spec says blocked; a sibling Bisnis URL gave 403). Its headline and a search summary are all I saw. |
| pusatdata.kontan.co.id (IHSG 6/11) | HTTP 403 (batch 3) | Kontan not read. |
| kabarbursa.com (an article and the market-hari-ini index) | bot-check page "One moment, please" (batch 4) | Not read; not retried. |
| ir.msci.com (MSCI Indonesia consultation press release) | HTTP 403 (batch 5) | MSCI's own text NOT read. I did not use mirrors (marketscreener, financialcontent, etc.) of that document. |
| www.idx.co.id/id/berita/siaran-pers/ (IDX press-release list) | HTTP 403 (batch 5) | IDX press page not read. I did not try the idx.id twin of that page. |
| ajaib.co.id (NAYZ and LFLO technical pages) | HTTP 403 (batch 6) | No quote/board data from Ajaib. |
| investortrust.id/market | HTTP 404 (batch 5) | Not read. |
| pasardana.id LFLO article | page returned "Berita tidak ditemukan" (batch 11) | No LFLO board information from it. |
| idx.id register via WebFetch | 200 but menus only (batch 2) | Read via curl instead (see section 1). |
| BCA special-monitoring notices (2, 4, 9 Nov) | page text has no tickers; the PDFs were not read | Cannot tell from them whether NAYZ/LFLO/TAXI are on the Watchlist board. |
| Decree PDFs (Kep-00157, Kep-00158) | not attempted this time (spec: HTTP 403) | Decree wording still unread, as in SPEC_FINAL U1. |
| WebSearch with reuters.com in allowed_domains | API error, domain not accessible to the search tool (batch 6) | Re-run without it (batch 7). |
| Bareksa "Proyeksi IHSG 2027" (422,947 characters) | only characters 0 to 300,000 read | No ARB mention in the part read; the last 122,947 characters were not read. |
| Bareksa "OJK: IHSG Turun 41,52%..." (216,760 characters) | only characters 0 to 200,000 read | No ARB mention in the part read; the last 16,760 characters were not read. |
| OJK SP 219 (112,323 characters) | read in two parts, complete | No ARB, 7%, 31 December 2026 or 2027 mention in the tail (only HSC "evaluasi" sentences). |

## 3. Findings, classified

Classes: (a) official confirmation, (b) statement of intent, (c) speculation or opinion, (d) nothing found. "Window" = published on or after 2026-11-05 (the spec's last known news date).

### 3.1 (a) Official confirmations

**A1. OJK press release SP 219/OJK/DKPU/XI/2026, "Memperkuat Ketahanan dan Penegakan Integritas Sektor Jasa Keuangan untuk Menjaga Kepercayaan dan Stabilitas Sektor Jasa Keuangan" (RDK Oktober 2026)**
- Outlet: OJK (ojk.go.id). Date: 2026-11-05 (Jakarta), no time shown. In window.
- URL: https://www.ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/RDKB-Oktober-2026.aspx
- Read in full (characters 0 to 100,000 in batch 9, 100,000 to 112,323 at about 06:03Z; the tail holds only HSC-committee "evaluasi" sentences, no ARB). Capital-market section: "penyesuaian batasan Auto Rejection Bawah (ARB) dari sebelumnya 15 persen menjadi 7 persen" issued October 2026, "yang berlaku hingga 31 Desember 2026"; buyback without RUPS extended "hingga 30 Juni 2027"; also mentions the MSCI consultation announcement. No sentence on evaluation of the ARB, on which markets or boards the ARB covers, or on a 2027 ARB.
- vs SPEC_FINAL: MATCHES section 1 (validity wording) and section 9 item 4. This is the primary document behind the Wartaekonomi/Bisnis reports. Note the sentence the fetch tool returned does not include the word "hanya" (only), and the release has no evaluation sentence about the ARB; those emphases come from the 5 Nov press conference as reported by Wartaekonomi.

**A2. IDX web page "Trading hours and mechanism" (Auto Rejection table)**
- Outlet: IDX (idx.id). Undated page. Read in batch 2 (05:45:02Z to 05:46:19Z) and again in the final sweep (after 06:04:17Z, cache expired): identical table and decree citation both times.
- URL: https://www.idx.id/en/products-services/trading-hours-and-mechanism/
- Table values: Main/New Economy/Development: Rp1-10 +Rp1/-Rp1 (Volume cell ">50,000 Lot or >5% of listed shares" in the first row); Rp11-14 35% / IDR1.00; Rp15-200 35%/7%; >Rp200-5,000 25%/7%; >Rp5,000 20%/7%. Acceleration and Watchlist: Rp1-10 Rp1/Rp1; >Rp10 10%/10%. ETF and REITs: Rp1-10 Rp1/Rp1; Rp11-14 35%/IDR1.00; a row printed "IDR11.00 to IDR200.00" 35%/7%; >Rp200 25%/7%; >Rp5,000 20%/7%. DINFRA: Rp1-10 Rp1/Rp1 (the lower cell is printed "IDR1,00"); >Rp10 10%/10%. Cites "Kep-00158/BEI/10-2026". No text about 31 December 2026, no mention of 2027, no "last updated" date. (I did not re-read the tick table.)
- vs SPEC_FINAL: MATCHES sections 2.1, 2.2, 2.3 (including the "Rp11 to Rp200" typo row), 2.4, 2.6. UNCHANGED.

**A3. IDX regulation register (raw HTML via curl)**
- Outlet: IDX (idx.id). Fetched with curl at 05:49:34Z, 05:57:17Z and 06:04:17Z (all HTTP 200, 165,587 bytes, identical SHA-256, identical decree list).
- URL: https://www.idx.id/id/peraturan/peraturan-bei/
- In-force Rule II-A: "II-A Kep-00158/BEI/10-2026", "Peraturan Nomor II-A tentang Perdagangan Efek Bersifat Ekuitas", attachment 1,420 KB, file name ending -261020.pdf (https://www.idx.co.id/Media/stumk2gi/signed_peraturan_nomor_ii_a_tentang_perdagangan_efek_bersifat_ekuitas-261020.pdf). Also II-X Kep-00140/BEI/09-2026, II-O Kep-00137/BEI/09-2026, II-V Kep-00084/BEI/10-2019 (Perdagangan EBE pada Papan Akselerasi), I-A Kep-00152/BEI/10-2026 (listing rule, not a price limit), I-X Kep-00139/BEI/09-2026. Highest 2026 decree number in the register: 00158. Decrees dated 11-2026: none.
- vs SPEC_FINAL: MATCHES sections 1 and 13 (register state). No later decree. Caveat: a decree issued today may not be on the register yet.

**A4. IDX press releases reposted by IQPlus on BCA Sekuritas (re-read)**
- Kep-00157: "BEI Sesuaikan Batas Bawah Auto Rejection Efek Bersifat Ekuitas", dated 2026-10-19 (no time), https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-batas-bawah-auto-rejection-efek-bersifat-ekuitas . Replaces Kep-00136; effective 19 Oct; valid to 31 Dec; "akan dievaluasi kembali mengikuti perkembangan yang terjadi di pasar"; no 2027 text. MATCHES.
- Kep-00158: "BEI Sesuaikan Kembali Batas Bawah Auto Rejection Efek Bersifat Ekuitas", dated 2026-10-20 (no time), https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-kembali-batas-bawah-auto-rejection-efek-bersifat-ekuitas . Effective 20 Oct to 31 Dec; boards Utama, Pengembangan, Ekonomi Baru; Akselerasi and Pemantauan Khusus keep their own limits; Rp11-14 lower limit 7% to Rp1,00. Evaluation wording (verbatim): "akan dievaluasi kembali sebagai bahan pertimbangan dalam menentukan keberlanjutan penerapannya". No 2027 text. MATCHES. Nuance: the spec quotes "mengikuti perkembangan pasar" for P2 and P3 together; that phrase belongs to the Kep-00157 release, while the Kep-00158 release says the evaluation will be input for deciding whether the rule continues. No effect on any date or value.

**A5. Wartaekonomi, "OJK Batasi ARB 7% hingga Akhir 2026"** (official statement as reported)
- Outlet: Warta Ekonomi (Merlina Aryanti). Published Fri 2026-11-06 19:33 WIB. In window.
- URL: https://wartaekonomi.co.id/read646192/ojk-batasi-arb-7-hingga-akhir-2026
- Read. OJK Board Chair Friderica Widyasari Dewi, press conference on the October RDKB, Thu 2026-11-05: ARB cut issued October 2026 together with the SROs including BEI, valid only until 31 December 2026; Rp15 and above 7%, Rp1-10 and Rp11-14 nominal Rp1; cites Kep-00157/BEI/10-2026 dated 19 Oct; the Rp11-14 change is "a separate BEI Directors' decision" (name cut off). No evaluation, no 2027 ARB. The only 2027 item is the buyback extension to 30 June 2027.
- vs SPEC_FINAL: MATCHES section 1 and section 9 item 4.

**A6. OJK press release SP 201/OJK/DPKU/X/2026, "OJK Perkuat Stabilitas dan Integritas Pasar Modal Melalui Tiga Langkah Kebijakan Strategis"**
- Outlet: OJK. Date 2026-10-26 (before the window). Read.
- URL: https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/OJK-Perkuat-Stabilitas-dan-Integritas-Pasar-Modal-Melalui-Tiga-Langkah-Kebijakan-Strategis.aspx
- Contains no sentence about ARB. Only 2027 references are the buyback extension. NEUTRAL, no effect.

### 3.2 (b) Statements of intent

**B1. BEI's own evaluation wording** (A4 above, 2026-10-19 and 2026-10-20): the 7% and the Rp1 rule "will be re-evaluated"; for Kep-00158, as input "dalam menentukan keberlanjutan penerapannya". No newer BEI statement found. MATCHES SPEC (section 1 validity wording). Interpretation: BEI itself ties continuation to a later decision; no decision is published.

**B2. Jeffrey Hendrik (BEI President Director), "BEI Nilai ARB 7 Persen Efektif Redam Kepanikan Pasar"**
- Outlet: Infobanknews. Mon 2026-10-19 16:35 WIB (before the window). Read.
- URL: https://infobanknews.com/bei-nilai-arb-7-persen-efektif-redam-kepanikan-pasar
- Says the 7% limit ran 19 Oct to 31 Dec, that BEI "akan mengevaluasi kebijakan tersebut dengan mempertimbangkan perkembangan kondisi pasar", and "evaluasi diperlukan karena penyesuaian batas ARB tersebut bukan merupakan kebijakan yang lazim diterapkan". Nothing on 2027, extension, 15% or symmetry. MATCHES; adds a quote the spec does not have (no effect on values).

**B3. Jeffrey Hendrik, "BEI Siapkan 3 Jurus Jelang Rebalancing MSCI 12 November, Apa Saja?"**
- Outlet: Katadata (Karunia Putri). Fri 2026-11-06 05:05 WIB. In window. Read.
- URL: https://katadata.co.id/finansial/bursa/6aec90aa65a46/bei-siapkan-3-jurus-jelang-rebalancing-msci-12-november-apa-saja
- The three measures are transparency (more disclosure of holders above 1%), liquidity reforms, and surveillance (real-time flagging). ARB, price limits, 7%, 31 December 2026 and 2027 are not mentioned. NEUTRAL: shows BEI's stated MSCI-related agenda this week does not include price limits.

**B4. Irvan Susandy and Bisnis Insight / emitennews, 2026-09-23 and 2026-09-24 (already in SPEC_FINAL section 9 item 2).** I did not re-read these. No newer statement by him found (search, 2026-11-09 batch 5: newest hit 2026-07-28, about Bank Indonesia leadership transition).

**B5. The September plan itself (re-read):** Jakarta Globe, "IDX Removes Rp 50 Stock Price Floor, Sets New Minimum at Rp 1", 2026-09-21 6:53 pm, https://jakartaglobe.id/business/idx-removes-rp-50-stock-price-floor-sets-new-minimum-at-rp-1 : asymmetric limits "through Dec. 31"; "From Jan. 1, 2027, the exchange plans to restore symmetric auto-rejection limits". IDXChannel, "Auto Rejection Kembali Simetris, Analis Soroti Potensi Normalisasi oleh MSCI", 2026-09-27 10:31 WIB, https://www.idxchannel.com/market-news/auto-rejection-kembali-simetris-analis-soroti-potensi-normalisasi-oleh-msci : phase 1 28 Sep to 31 Dec, phase 2 from 1 Jan 2027 symmetric ARB. Both pre-window. MATCH SPEC section 9 item 1. No later source confirms, changes or cancels this plan.

### 3.3 (c) Speculation or opinion

**C1. Stockbit analyst quoted by IDXChannel, 2026-09-27 10:31 WIB (page 2 of the article above, read):** the symmetric-ARB restoration "berpotensi mendukung normalisasi perlakuan terhadap pasar Indonesia ... oleh penyedia indeks seperti MSCI". Opinion; no date or condition tied to MSCI; pre-window; no one in the article calls the 2027 step conditional. (The spec's "conditional" comes from Irvan Susandy and Bisnis Insight.) No effect.

**C2. Bisnis, "Normalisasi ARB dan Saham Rp1 Jadi Sinyal Positif MSCI", 2026-09-23**, https://market.bisnis.com/read/20260923/7/2006520/normalisasi-arb-dan-saham-rp1-jadi-sinyal-positif-msci : headline only (Bisnis blocked, 403 on a sibling URL). Pre-window. Same theme as C1.

**C3. Unnamed analysis listing "extend 7%, back to 15%, or revise" as possible year-end outcomes**: appears only inside a search summary of a minor-outlet result list (2026-11-09 batch 9), undated and not read. Pre-window as far as I can tell. Not evidence of any decision.

**C4. Market commentary this week** (IDXChannel 2026-11-09 07:15 and 07:24 WIB; CNBC Indonesia 2026-11-09 08:45; Bareksa 2026-11-09 "Proyeksi IHSG 2027"; all read): about MSCI risk and index outlook; none mentions ARB, price limits or 2027 rules.

### 3.4 (d) Nothing found (by topic; queries are in section 8)

| Topic you asked about | Result |
|---|---|
| ARB after 2026-12-31 | Nothing published after 2026-11-06 that addresses it. Latest relevant item: OJK SP 219 (2026-11-05) and its press coverage (2026-11-06). |
| BEI extends 7% | Nothing. Every source describes 7% as valid to 2026-12-31. The only 2027 extension reported is OJK's buyback-without-RUPS extension to 2027-06-30, which is a different policy. |
| BEI reverts to 15% | Nothing. |
| BEI goes symmetric (ARB = ARA) in 2027 | Only the September plan (Jakarta Globe 09-21 and IDXChannel 09-27, both read; Katadata, emitennews and others seen in search summaries only). No confirmation, cancellation or postponement found. |
| New BEI decree or press release amending Kep-00158 | None. Register unchanged (A3). Searches for "Kep-00159/BEI" and for any 11-2026 II-A decree found nothing; the IDX press-release list is blocked (403), the BCA/IQPlus repost list (newest item 2026-11-09) has no BEI rule item. |
| OJK statements about ARB | Only A1, A5, A6 and the 2026-10-26 statements (see "Pre-window note" below). Nothing new after 2026-11-06. |
| BEI directors on the 2027 rule | Nothing newer than 2026-09-23 (Irvan Susandy). Jeffrey Hendrik: B2, B3 only. |
| MSCI consultation and price limits | MSCI's own release was not reachable (403). No source I read or saw ties the consultation to Indonesia's price limits. News summaries put MSCI's stated concerns at shareholding opacity, free-float quality and suspected coordinated trading. BEI's stated reason for the 7% was calming panic after the 15/16 Oct announcement (Infobanknews 10-19), and BEI said it would ask MSCI for clarification (Bareksa 10-19 headline; search summary). The consultation end date 2027-04-30 and decision date 2027-06-30 appear only in search summaries (MSCI's release was unreachable); IDXChannel 2026-11-09 (read) gives the separate November review date. Consistent with SPEC section 9 item 5 (spec said not re-verified; still not verified from MSCI's own text). |
| Change to the Rp1 minimum price | None. TAXI traded at Rp9 to Rp11 on 2026-11-09 (stockanalysis.com, section 4), so the Rp50 floor was not reinstated. |
| Change to the Rp11-14 rule | None. IDX page still shows IDR1.00; see section 4 for TAXI. |
| Change to the order-volume rule | None. IDX page still shows ">50,000 Lot or >5% of listed shares". A search summary credits the volume rule to Kep-00023/BEI/03-2020 (not read; no change reported). |
| Unusual ARB behaviour in market reports from 2026-11-06 | None reported in any article I read. See section 4 for the three decliners above 7% on 2026-11-06 and what explains them. Pre-window note: a search summary of a Bisnis article says OJK's Hasan Fawzi said on 2026-10-26 that the 7% ARB applies "di semua pasar"; not read (Bisnis blocked); the IDX table still shows board-specific limits, so I treat it as loose wording. |

## 4. Market reports and price data from 2026-11-06 onward (unusual-ARB check)

Reports that name decliners above 7% on 2026-11-06 (both read): Databoks, "9 Sektor Saham Melemah, Teknologi Jatuh Paling Dalam (Jumat, 6 November 2026)", Katadata Media Network, 2026-11-06 18:20 WIB, https://databoks.katadata.co.id/pasar/statistik/6aeda482a3d35/9-sektor-saham-melemah-teknologi-jatuh-paling-dalam-jumat-6-november-2026 ; and Databoks, "IHSG Naik Tipis 0,40% di Tengah Pelemahan Bursa Kawasan Asia (Jumat, 6 November 2026)", 18:00 WIB, https://databoks.katadata.co.id/pasar/statistik/6aed9f70ae7e8/ihsg-naik-tipis-040-di-tengah-pelemahan-bursa-kawasan-asia-jumat-6-november-2026 . Top losers: TAXI -9.09%, NAYZ -8.93%, LFLO -7.46%; top gainers AIMS +25%, POLU +19.93%, SMDM +16.32%. Neither article gives prices, boards or any ARB wording. Closing level: IHSG about 5,050, +0.40% (Databoks and Katadata headlines, read); session I had ended near 4,931, -1.97% (search summary only). The Katadata close report (2026-11-06 17:33 WIB) names no ARB; its largest named decline is ARCI -4.10%. For Monday 2026-11-09 session I (IDXChannel 12:15 WIB, read) no top loser or ARB is named. No full list of 2026-11-06 ARB stocks was available to me.

Because those articles give no prices, I read daily bars from stockanalysis.com (third-party aggregator, NOT official; read through WebFetch in batches 10 and 12) and checked them with exact arithmetic against the SPEC_FINAL section 5 rule (ARB = smallest valid price at or above R x (1 - b), tick of the limit price's own band):

| Stock | Session | Prev close R | Close | Move | 7% rule ARB (Main/Dev/NewEco) | 10% rule ARB (Acceleration/Watchlist) | Reading |
|---|---|---|---|---|---|---|---|
| BRPT | 10-29 | 1,235 (derived from printed -6.88%) | 1,150 | -6.88% | 1,150 | 1,115 | at the 7% ARB |
| BRPT | 10-30 | 1,150 | 1,070 | -6.96% | 1,070 | 1,035 | at the 7% ARB |
| BRPT | 11-03 | 1,120 | 1,045 | -6.70% | 1,045 | 1,010 | at the 7% ARB |
| BRPT | 11-04 | 1,045 | 975 | -6.70% | 975 | 945 | at the 7% ARB |
| BRPT | 11-05 | 975 | 910 | -6.67% | 910 | 880 | at the 7% ARB |
| BRPT | 11-06 | 910 | 850 | -6.59% | 850 | 820 | at the 7% ARB |
| JPFA | 11-06 | 1,665 | 1,550 | -6.91% | 1,550 | 1,500 | at the 7% ARB (raw 1,548.45 rounds up on the tick-5 grid). The page's own printed change for that row reads -1.59%, which contradicts its own prices; I used the prices. |
| NAYZ | 11-03 | 75 | 68 | -9.33% | 70 | 68 | at the 10% ARB, below the 7% ARB |
| NAYZ | 11-04 | 68 | 62 | -8.82% | 64 | 62 | at the 10% ARB, below the 7% ARB |
| NAYZ | 11-05 | 62 | 56 | -9.68% | 58 | 56 | at the 10% ARB, below the 7% ARB |
| NAYZ | 11-06 | 56 | 51 | -8.93% | 53 | 51 | at the 10% ARB, below the 7% ARB |
| LFLO | 11-06 | 670 | 620 (open 620, high 680, low 620) | -7.46% | 625 | 605 | below the 7% ARB, inside a 10% ARB: NOT explained (see below) |
| TAXI | 10-27 | 13 | 12 | -7.69% | 12 (Rp1 nominal) | 12 | Rp1 step |
| TAXI | 10-29 | 12 | 11 | -8.33% | 11 | 11 | Rp1 step |
| TAXI | 11-03 | 11 | 10 | -9.09% | 10 | 10 | Rp1 step |
| TAXI | 11-06 | 11 | 10 | -9.09% | 10 | 10 | Rp1 step (the "-9.09%" Databoks reports) |

What this shows:
- **Main-board 7% rule, spec formula (floor/ceil on the tick grid of the limit price's own band):** BRPT's six ARB closes and JPFA's one are each exactly ceil to the tick-5 grid of 0.93 x R. Seven of seven. These are all sessions after Kep-00158, up to 2026-11-06. Supports SPEC_FINAL P3 (7%, ceil rounding). (The board of BRPT and JPFA was not checked; the match itself indicates a 7% board.)
- **TAXI (Rp11-14 and Rp1-10 bands):** its falls 13 to 12, 12 to 11, 11 to 10 contradict the 7% formula that SPEC_FINAL section 5 says gives "no downside" for R = 11 to 14 (13, 12, 11), and fit the Rp1 nominal rule (U14). Caution: for R = 11 to 14 a 10% ARB gives the same numbers (R - 1), so TAXI cannot tell the Rp1 rule from a 10% board unless TAXI's board is known. Also 11-05: 10 to 11 (+10%) is the Rp1 nominal ARA in the Rp1-10 band, and 11-06 low 10 / 11-05 low 9 equal R - 1. TAXI traded at Rp9 to Rp11 on 11-09, so the Rp1 minimum price is still in force.
- **NAYZ:** four closes in a row exactly at ceil of 0.90 x R and each below the 7% ARB. It must be on a 10% board; this fits SPEC_FINAL section 2.2 (Acceleration/Watchlist 10%/10%, unchanged by the October decisions). Search summaries (not read) say NAYZ has been on the Acceleration Board since Feb 2023; KSEI's page (read) gives listing date 2023-02-06 but no board field.
- **LFLO:** the 6 Nov close and open (620) are below the 7% ARB (625) for a reference of 670. This is consistent with a 10% ARB (605) and inconsistent with a Main/Development/New Economy 7% ARB. Search summaries (not read) say LFLO (PT Imago Mulia Persada Tbk) was removed from special monitoring effective 2025-12-05 and traded on the Acceleration Board; I found no 2026 board news and could not confirm from a page I read (KSEI, Pluang show no board; BCA special-monitoring notices list no tickers). A reference-price adjustment (corporate action) is the other possible explanation; I found none. **Treat as unexplained and unverified. If LFLO is on a 7% board it would contradict P3; the evidence I have points to a 10% board.**
- No source reported any stock on a 7% board closing below its 7% ARB.

## 5. Pending event: MSCI November 2026 Index Review

- IDXChannel, "IHSG Pekan Ini Diproyeksi Masih Rapuh, Fokus Pasar Tertuju pada Pengumuman MSCI", 2026-11-09 07:15 WIB (read), https://www.idxchannel.com/market-news/ihsg-pekan-ini-diproyeksi-masih-rapuh-fokus-pasar-tertuju-pada-pengumuman-msci : results due "11 November waktu Eropa Tengah (12 November 2026 pukul 05.00 WIB)", changes effective 1 December 2026. It lists BEI's measures (83 HSC stocks excluded from the IHSG calculation, 15% minimum free float, tighter disclosure above 1%, real-time manipulation flagging). No ARB, no 2027 rule.
- IDXChannel, "IHSG Pekan Ini Dibayangi MSCI, Perhatikan BBCA, ICBP, UNVR, dan WIFI", 2026-11-09 07:24 WIB (read): MSCI Index Review 11-12 Nov.
- CNBC Indonesia, "Jelang Pengumuman MSCI Pekan Ini, Simak 5 Saham Pilihan Hari Ini", 2026-11-09 08:45 (read), https://www.cnbcindonesia.com/market/20261109081303-17-783393/jelang-pengumuman-msci-pekan-ini-simak-5-saham-pilihan-hari-ini : "pekan ini", no day given.
- Katadata search result: "BEI Siapkan 3 Jurus Jelang Rebalancing MSCI 12 November" (B3 above) uses the same date.
- Effect: this is new relative to SPEC_FINAL (which mentions only the consultation to 2027-04-30). Precedent: MSCI's consultation announcement is dated 2026-10-15 (US) in search results (markets fell Fri 10-16; MSCI's own text unreadable); BEI issued Kep-00157 on Mon 10-19 and Kep-00158 on Tue 10-20 (both read via the IDX release reposts). Speculation, labelled as such: a further BEI or OJK step after 2026-11-12 is possible; I found no sign of one.

## 6. Match / contradiction table against SPEC_FINAL

| SPEC_FINAL item | Status after recheck |
|---|---|
| Section 1 periods P1, P2, P3 with decree numbers and dates | UNCHANGED (A3 register, A4 reposts, A2 page). |
| Section 1 "valid until 31 Dec; to be re-evaluated" wording | UNCHANGED; Kep-00158 wording is slightly more specific (A4). |
| Section 1 last P3 session / holiday (Tirto, single source) | Not rechecked. |
| Section 2.1 table (P3 column) | UNCHANGED (A2); price data consistent (section 4). |
| Section 2.2 Acceleration/Watchlist 10%/10%, untouched by October decisions | UNCHANGED (A2, A3 shows II-V Kep-00084/BEI/10-2019 still in force); NAYZ data consistent. |
| Section 2.3 ETF/REIT P3 rows incl. the "Rp11 to Rp200" typo | UNCHANGED on the IDX page. |
| Section 2.4 DINFRA | UNCHANGED on the IDX page (lower cell printed "IDR1,00"). |
| Section 2.6 volume rule | UNCHANGED on the IDX page. |
| Section 4 tick table and minimum price | Tick table not re-read; page still cites Kep-00158 for Trading Unit and Price Fraction. Rp1 minimum: still in force 11-09 (TAXI at Rp9-Rp11). |
| Section 5 rounding rule | Supported by 7 more ARB closes (section 4). |
| Section 9 item 1 (Kep-00136 phase 2 plan) | UNCHANGED (Jakarta Globe 09-21, IDXChannel 09-27). |
| Section 9 item 2 (Irvan Susandy) | No newer statement found. |
| Section 9 item 3 (none of the October reports mentions 2027) | Still true of the October items I read (A4 reposts, B2). |
| Section 9 item 4 (OJK 2026-11-05) | CONFIRMED by the official release SP 219 (A1) and Wartaekonomi (A5). |
| Section 9 item 5 (no extension, no new decree; MSCI context) | STILL TRUE as of the times above. MSCI dates unverified from MSCI's own text. |
| Section 9 conclusion (nothing confirmed from 2027-01-01) | STANDS. |
| U5 (10-19, R = 11 to 14) | Not rechecked; TAXI's moves after 10-20 fit the nominal rule. |
| U14 (Rp11-14 nominal Rp1) | Supported by TAXI (not decisive, see section 4). |
| Section 11 "A search snippet said Kep-00158 'sejak 19 Oktober'" | Consistent with what I saw: Kep-00158 reposts say effective 20 Oct. |

## 7. Search-tool summaries that were wrong (so nobody reuses them)

- A summary said Jakarta Globe's piece puts the asymmetric period "through Dec. 1, 2027". The page I read prints "through Dec. 31" and "From Jan. 1, 2027". The summary was wrong.
- A summary said The Star's "7%" is "either an error or refers to the 2025 trading-halt framework". Wrong: 7% is the Kep-00157 limit.
- A search hit "10 Saham Memerah Saat Bursa Kembalikan ARB Simetris" (Fortune IDN) came back for my 9 November queries; the page I read is dated 2023-09-05 and concerns the 2023 normalisation, not 2027.
- "BEI Rotasi 15 Saham Antar Papan Pencatatan" (BCA Sekuritas) is dated 2025-11-24, not 2026.

## 8. Queries run

WebSearch (mode in brackets; "ext" = extended). All run 2026-11-09 in the batch windows of section 1.

Batch 1: [ext] ARB 2027 BEI batas auto rejection bawah setelah 31 Desember 2026 | [ext] BEI perpanjang ARB 7 persen tahun 2027 | ARB simetris ARA ARB sama 1 Januari 2027 BEI | [ext] IDX Indonesia lower auto rejection limit 2027 extend 7% or revert symmetric | Kep-00158/BEI/10-2026 perubahan peraturan Nomor II-A | Irvan Susandy ARB 2027 auto rejection | OJK ARB 7 persen hanya berlaku hingga 31 Desember 2026 evaluasi | MSCI consultation Indonesia price limit auto rejection
Batch 2: [ext] BEI evaluasi ARB akhir tahun keputusan 2027 Jeffrey Hendrik | saham ARB hari ini 9 November 2026 | IHSG ditutup Jumat 6 November 2026 saham ARB top losers | BEI siaran pers November 2026 auto rejection perubahan peraturan perdagangan | OJK Friderica Widyasari Dewi ARB RDKB 5 November 2026 pasar modal | harga minimum saham Rp1 BEI evaluasi perubahan fraksi harga November 2026
Batch 3: Kep-00159/BEI Direksi PT Bursa Efek Indonesia Peraturan Nomor II-A Perdagangan Efek Bersifat Ekuitas November 2026 | Indonesia Stock Exchange auto rejection limit November 2026 IDX said | OJK siaran pers RDKB Oktober 2026 ARB 7 persen pasar modal buyback tanpa RUPS 30 Juni 2027 | analis ARB 7% 2027 diperpanjang atau kembali simetris saham | saham TAXI NAYZ LFLO turun 6 November 2026 | IHSG sesi I Senin 9 November 2026
Batch 4: [ext] MSCI consultation Indonesia reclassification Standalone market October 2026 price limits auto rejection concerns press release | BEI kaji ARB 7 persen perpanjangan atau kembali 15 persen Januari 2027 Direktur Utama Jeffrey Hendrik November | Hasan Fawzi OJK ARB BEI batas auto rejection bawah 2027 pasar modal | daftar saham ARB Jumat 6 November 2026 auto reject bawah
Batch 5: Irvan Susandy BEI November 2026 | Jeffrey Hendrik BEI respons MSCI langkah baru batas harga ARB pekan ini | saham NAYZ LFLO papan akselerasi harga penutupan 6 November 2026 | BEI ubah aturan volume order auto rejection 50.000 lot 5 persen saham | Hasan Fawzi ARB minus 7 persen seluruh pasar 26 Oktober 2026 OJK konferensi pers | Proyeksi IHSG 2027 valuasi murah risiko MSCI masih membayangi ARB | [ext] Indonesia bourse asymmetric lower price limit year-end review 2027 symmetric Reuters Bloomberg
Batch 6: pengumuman MSCI pekan ini November 2026 index review Indonesia tanggal pengumuman hasil | ARB auto rejection bawah BEI 2027 (three runs, each limited to a domain set: Bisnis; Katadata/Databoks/Bareksa/IDXChannel/RCTI+; Kontan/CNBC/Antara/Investortrust/emitennews/Pasardana) | Indonesia stock exchange lower auto-rejection limit 7% 2027 (English-outlet domain set; FAILED with an API error because reuters.com is not reachable by the search tool)
Batch 7: Indonesia stock exchange lower auto-rejection limit 7% 2027 (English-outlet domain set, rerun) | saham TAXI turun 9,09% Rp10 ARB Rp1 saham Rp11-Rp14 Jumat 6 November | saham anjlok lebih dari 7 persen papan utama ARB aneh November 2026 BEI telusuri | [ext] ARB 7% berakhir 31 Desember apa selanjutnya BEI putuskan perpanjang normalisasi investor ritel
Batch 8: OJK siaran pers hasil RDKB Oktober 2026 kinerja sektor jasa keuangan pasar modal (ojk.go.id only) | Hassana Boga Sejahtera NAYZ papan pencatatan 2026 papan akselerasi atau pengembangan | LFLO saham emiten papan akselerasi 2026 Lifelong OR Lautan OR Leaf | saham ARB hari ini top losers 9 November 2026 sesi I IHSG 5.091
Batch 9: Antara OJK konferensi pers RDKB 5 November 2026 ARB 7 persen Friderica pasar modal | [ext] Friderica ARB 7 persen setelah 31 Desember 2026 evaluasi koordinasi BEI OJK kebijakan lanjutan
Batch 10: BEI tunda ARB simetris 2027 batal atau ditunda auto rejection bawah | ARB 7% dipertahankan hingga 2027 BEI putuskan lanjutkan batas auto rejection bawah | BEI konsultasi publik rancangan perubahan Peraturan II-A batas auto rejection 2027 | MSCI Indonesia consultation daily price limits lower limit asymmetric market accessibility concern | Antara English OJK lower auto-rejection 7 percent end of 2026 IDX stock market | IDX to keep 7 percent lower auto rejection limit into 2027 decision
Batch 11: Imago Mulia Persada LFLO Papan Akselerasi 2026 pemantauan khusus papan pencatatan | saham LFLO turun 7,46% 6 November 2026 ARB papan akselerasi
(Section 11 lists the final-sweep queries.)

Pages fetched with WebFetch beyond those cited above (headline lists, read): BCA Sekuritas latest-news, IDXChannel market-news, Katadata bursa, Bareksa saham, CNBC Indonesia market, Antara bursa (all newest items 2026-11-09, none about an ARB rule); tag pages Antara tag/arb, CNBC tag/arb, Viva tag/saham-arb, Fortune IDN tag/arb, Stockbit snips tag ARB (newest ARB-rule article 2026-10-19 to 2026-10-20; unrelated newer items only), Databoks tag top-losers-saham (newest 2026-11-05).

## 9. What this means for the code change

- Dated rules P1, P2, P3 and their values: no source I read contradicts SPEC_FINAL.
- Date lookup for sessions on or after 2027-01-01: still UNRESOLVED. Nothing published up to the times above confirms any regime. The spec's rule "tests must not assert the exchange's rule for dates on or after 2027-01-01" is still the right stance.
- Facts newly useful to the author (optional): the Kep-00158 evaluation sentence; OJK SP 219 as the official source for the 7% validity date; seven additional ARB observations consistent with the 7% rounding rule; NAYZ as a 10%-board example; the MSCI result date 2026-11-12 05:00 WIB.

## 10. Limits and caveats

- WebSearch is US-only and returns model-written summaries; they can be wrong (section 7). I cite a summary only where I say "search summary only".
- WebFetch answers come from a small model summarising converted page text; I quote what it returned. Pages with more than 100,000 characters were read in parts (section 2).
- The search index appears to lag: the newest indexed items on Monday 2026-11-09 were from the morning (up to 12:23 WIB). Monday's afternoon session and close are not covered.
- stockanalysis.com is a third-party aggregator; one printed percentage (JPFA 11-06) is inconsistent with its own prices. It is used only as a cross-check.
- Boards of NAYZ, LFLO, BRPT, JPFA and TAXI were not verified from pages I read.
- Nothing here replaces reading the decree PDFs (SPEC_FINAL U1), which I did not try.

## 11. Final sweep (06:04:17Z to about 06:05Z)

Run after the fetch tool's 15-minute cache had expired for the earlier reads, to catch anything published while I was working. Last clock reading when I finished this section: **2026-11-09T06:05:13Z**.

- **IDX register, third curl (06:04:17Z to 06:04:18Z):** HTTP 200, 165,587 bytes, decree list identical to the 05:49:34Z and 05:57:17Z copies. II-A is still only "II-A Kep-00158/BEI/10-2026". No 2026 decree numbered above 00158; none dated 11-2026.
- **IDX trading-mechanism page (re-read):** identical Auto Rejection table (Rp11-14 Lower AR "IDR1.00"; Rp15 and above 7%; Acceleration/Watchlist 10%/10%; DINFRA 10%/10%; Volume cell ">50,000 Lot or >5% of listed shares"); Kep-00158/BEI/10-2026 cited for trading hours and price fraction; no mention of 31 December 2026 or 2027.
- **News indexes (headlines only, read):** IDXChannel market-news newest item 12:15 WIB 2026-11-09; CNBC Indonesia market newest 12:23 WIB; Katadata bursa newest 11:35 WIB; Antara bursa newest about 2 hours old; Bareksa saham newest about 3 hours old (relative times had moved on, so this copy was fresh); BCA Sekuritas latest-news newest items dated 2026-11-09 (three new non-ARB items). No headline in any of them concerns ARB, auto rejection, a BEI rule or decree, Peraturan II-A, minimum price or price limits. Two BEI items are about the HSC list (Antara 5 Nov "Komite HSC BEI kaji metodologi..."; Katadata 9 Nov "BEI Ungkap Skema Menghitung Saham HSC...") and one about delisting (CNBC video "Mulai 10 November 2026, BEI Delisting 18 Emiten"); none is a price-limit rule. For IDXChannel, CNBC and Katadata the newest-item time was unchanged from the earlier read, which means either nothing newer had been published by lunchtime WIB or some of that content was still cached; I cannot tell which.
- **Searches:** "BEI batas ARB terbaru pengumuman hari ini 9 November 2026" [ext] and "IDX Indonesia stock exchange announcement lower limit auto rejection MSCI review next week" [ext] (about 06:03Z), and "BEI OJK keputusan ARB 2027 terbaru pengumuman resmi evaluasi akhir tahun" (final sweep): nothing newer than the 2026-11-06 OJK coverage; newest rule items are 2026-10-19 and 2026-10-20. One of the summaries said it found "nothing confirming an MSCI review next week"; that is wrong as a statement about the November Index Review, which IDXChannel (read) dates to 12 Nov 2026 05:00 WIB (the consultation to 2027-04-30 is a separate process).
- **Result:** the bottom line in section 0 is unchanged at the end of the sweep.

What a later checker should redo: (1) the register (curl or browser) and the IDX press-release page after the MSCI Index Review on 2026-11-12 05:00 WIB; (2) the Monday 2026-11-09 close and later sessions for any stock closing beyond its limit; (3) the decree PDFs when reachable (SPEC_FINAL U1); (4) the board of LFLO.
