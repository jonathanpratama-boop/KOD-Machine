# IDX ARA/ARB spec, pass B (blind). Prepared 2026-11-09
All sources are NEWS or broker reposts of IDX press releases. No official IDX/OJK PDF reached (idx.co.id returned 403; no direct PDF found by search). Several news sites returned 402/403 or bot-wall.

## 1. Timeline (equity, Pasar Reguler/Tunai, Main/Development/New Economy boards)
SK chain: Kep-00136/BEI/09-2026 (21 Sep 2026; revokes Kep-00003/BEI/04-2025) -> Kep-00157/BEI/10-2026 (19 Oct) -> Kep-00158/BEI/10-2026 (20 Oct; replaces 00157). All amend Peraturan II-A.

Minimum price: Rp50 until Fri 2026-09-25; Rp1 from Mon 2026-09-28 (regular + cash market).

| Period (inclusive) | Band | ARA | ARB |
|---|---|---|---|
| to 2026-09-25 | Rp50-200 | 35% | 15% |
| | >200-5000 | 25% | 15% |
| | >5000 | 20% | 15% |
| 2026-09-28 .. 2026-10-16 | Rp1-10 | Rp1 | Rp1 |
| | Rp11-200 | 35% | 15% |
| | >200-5000 | 25% | 15% |
| | >5000 | 20% | 15% |
| 2026-10-19 (one day, Kep-00157) | Rp1-10 | Rp1 | Rp1 ("tetap", per Republika) |
| | Rp11-200 | 35% | 7% |
| | >200-5000 | 25% | 7% |
| | >5000 | 20% | 7% |
| 2026-10-20 .. 2026-12-31 (Kep-00158) | Rp1-10 | Rp1 | Rp1 |
| | Rp11-14 | 35% | Rp1 |
| | Rp15-200 | 35% | 7% |
| | >200-5000 | 25% | 7% |
| | >5000 | 20% | 7% |

Boards: Kep-00157/158 ARB applies to Main, Development, New Economy. Acceleration and Special Monitoring boards keep their own existing auto-rejection rules (their values NOT found). Sept SK (Kep-00136) board split not stated in articles.
ETF/REIT/DINFRA: Maybank Trade says ETF, DIRE, DINFRA have ARA=ARB=10% above Rp10 and Rp1 for Rp1-10, no transition (its own text says table hard to parse). Katadata: DINFRA units (Kep-00137/BEI/09-2026, Peraturan II-O): Rp1-10 -> Rp1/Rp1; >Rp10 -> 10%/10%. Whether Oct 7% ARB touched ETF/REIT/DINFRA: not found.
Tick (Maybank Trade, citing BEI PR 083/BEI.SPR/09-2026): <200: Rp1; 200-<500: Rp2; 500-<2000: Rp5; 2000-<5000: Rp10; >=5000: Rp25. ETF/DIRE/DINFRA tick Rp1. Cermati: tick "Rp1, 2, 5, 10, 25 per VI.5", unchanged.
From 2027-01-01: see Unresolved. Original Kep-00136 schedule (Katadata, Bareksa, BCA, Cermati): ARB = ARA symmetric (Rp11-200 35/35; >200-5000 25/25; >5000 20/20; Rp1-10 Rp1/Rp1). But Kep-00157 "replaces" Kep-00136 and Oct articles say the 7%/Rp1 rule is "until 31 Dec 2026, to be re-evaluated"; no source I could open states what applies on 2027-01-01 after the replacement.

## 2. Rounding and reference price
- Reference price: "Acuan Harga" (Maybank Trade: limits measured against the Acuan Harga used by JATS). Cermati: "+-Rp1 dari Acuan Harga" for Rp1-10. Acuan Harga definition (previous close etc.) not quoted from any source.
- Rounding: NO source states it. Convention (ARA floored to tick, ARB ceiled to tick) is general market practice, UNVERIFIED here. Oct 20 change (Rp11-14 to Rp1) is consistent with rounding: 7% of Rp11-14 is under Rp1, so a ceiled ARB leaves no downside (inference only).
- Band is chosen by reference price (CNBC example: Rp1,000 -> ~Rp930 at 7%). Inference.

## 3. Rp1-10 band
All sources: ARA and ARB both Rp1 nominal, "bukan berdasarkan persentase" (Bareksa 22 Sep; Bloomberg Technoz 21 Sep). Cermati: "+-Rp1 dari Acuan Harga". Maybank example: Rp3 -> Rp2 or Rp4. Unclear: what ARB means at ref Rp1 (Rp0 is below min price).
Volume condition: the "50,000 lots or >5% of listed shares, whichever smaller" is the separate VOLUME auto-rejection (order size), explicitly "tidak berubah" (Cermati, Maybank Trade), not a condition of the Rp1-10 price band. I found no volume condition attached to the Rp1-10 band. 1 lot = 100 shares.

## 4. Sources
- Katadata 2026-09-21 16:53 (news): https://katadata.co.id/finansial/bursa/6ab0fe985f085/harga-minimum-saham-jadi-rp-1-mulai-pekan-depan-auto-rejection-disesuaikan : Kep-00136/BEI/09-2026 tgl 21 Sep, "Harga minimum Rp 50 menjadi Rp 1" (min price Rp50->Rp1), tables above incl. 2027.
- Katadata 2026-09-21 17:56: https://katadata.co.id/finansial/bursa/6ab10d458e4d5/bei-ubah-aturan-auto-rejection-batas-arb-makin-lebar-jadi-35-mulai-2027 : 1 Jan 2027 ARB widens to 35%; DINFRA. (Superseded in part by Oct SKs.)
- Bloomberg Technoz 2026-09-21 20:00 (news): https://www.bloombergtechnoz.com/detail-news/122260/bei-turunkan-minimum-harga-saham-jadi-rp1-auto-rejection-berubah : "ditetapkan menggunakan batas nominal Rp 1, bukan persentase".
- Bareksa 2026-09-22 (news): https://www.bareksa.com/berita/saham/2026-09-22/bei-turunkan-harga-minimum-saham-jadi-rp1-mulai-28-september-ini-aturan-ara-arb-barunya/amp : "ARA dan ARB ditetapkan Rp1, bukan berdasarkan persentase."
- BCA Sekuritas (broker repost of IDX/news) 2026-09-21: https://bcasekuritas.co.id/latest-news/news/bei-harga-saham-terendah-rp1-berlaku-efektif-mulai-28-september
- Maybank Trade (broker, undated, ~28 Sep): https://www.maybanktrade.co.id/berita/aturan-saham-rp1-berlaku-28-september-2026-apa-yang-berubah/ : tick table, DINFRA/ETF, volume 50,000 lot/5%, Acuan Harga, PR 083/BEI.SPR/09-2026, Kep-000137.
- Cermati (broker/fintech, undated): https://invest.cermati.com/artikel/perubahan-harga-minimum-saham-dan-batas-auto-rejection : "+-Rp1 dari Acuan Harga".
- IDXChannel 2026-09-27: https://www.idxchannel.com/market-news/auto-rejection-kembali-simetris-analis-soroti-potensi-normalisasi-oleh-msci : "simetris dengan auto rejection atas" from 1 Jan 2027.
- Bloomberg Technoz (undated; ~22 Sep): https://www.bloombergtechnoz.com/detail-news/122514/soal-auto-rejection-simetris-bei-tetap-mengacu-kondisi-pasar/2 : IDX official Irvan: "kalau kondisi pasarnya tetap baik, kami akan buka ke normal" (table garbled, unreliable).
- Republika 2026-10-19 (news of IDX PR, Sekper Elsiierra Putri Yosita): https://ekonomi.republika.co.id/berita/tn4kd5370/jaga-stabilitas-pasar-bei-sesuaikan-aturan-auto-reject-bawah-saham-jadi-7-persen : Kep-00157/BEI/10-2026 "menggantikan" Kep-00136; "efektif diberlakukan sejak 19 Oktober 2026 sampai dengan 31 Desember 2026".
- Lensa Medan 2026-10-19: https://www.lensamedan.co.id/2026/10/sesuaikan-batas-bawah-auto-rejection.html ; BCA Sekuritas 2026-10-19: https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-batas-bawah-auto-rejection-efek-bersifat-ekuitas
- CNBC Indonesia 2026-10-19 (news): https://www.cnbcindonesia.com/research/20261019141956-128-777525/bei-ubah-aturan-arb-wajar-atau-sinyal-kepanikan : trigger IHSG -11.57% on 16 Oct (MSCI consultation); consultation to 30 Apr 2027, decision by 30 Jun 2027.
- BCA Sekuritas 2026-10-20 (IQPlus repost of IDX release): https://bcasekuritas.co.id/latest-news/news/bei-sesuaikan-kembali-batas-bawah-auto-rejection-efek-bersifat-ekuitas : "dari sebelumnya 7% menjadi Rp1,00" for Rp11-14; Kep-00158/BEI/10-2026 replaces Kep-000157; 20 Oct-31 Dec 2026; boards listed.
- Lensa Medan 2026-10-20: https://www.lensamedan.co.id/2026/10/bei-kembali-sesuaikan-batas-bawah-auto.html ; Bareksa 2026-10-20: https://www.bareksa.com/berita/saham/2026-10-20/bei-ubah-lagi-aturan-arb-mulai-20-oktober-saham-rp11rp14-dibatasi-turun-rp1 ; RCTI+/IDXChannel: https://www.rctiplus.com/news/detail/idxchannel/5497737/...
- Official path cited by sources: idx.co.id > Peraturan > Peraturan BEI > Peraturan Perdagangan (not fetched).

## 5. Boundary table (hand computed; assumes convention ARA floor to tick, ARB ceil to tick; AMBIGUOUS where flagged)
Ticks by price: <200:1, 200-<500:2, 500-<2000:5, 2000-<5000:10, >=5000:25. Periods: A=9/25 (min Rp50, ref<50 not tradable, "n/a"), B=9/28 and 10/16 (35/25/20 up; 15% down), C=10/19 (7% down), D=10/20 and 12/31 (7%; Rp11-14 Rp1). ARA is the same on all dates from 9/28 on.
Raw (unrounded) -> rounded.
| Ref | ARA 9/25 | ARA 9/28-12/31 | ARB 9/25 | ARB B (9/28,10/16) | ARB C (10/19) | ARB D (10/20,12/31) |
|---|---|---|---|---|---|---|
| 1 | n/a | 2 (Rp1) | n/a | Rp1 -> 0 below min; AMBIG (likely 1) | same AMBIG | same AMBIG |
| 10 | n/a | 11 | n/a | 9 | 9 | 9 |
| 11 | n/a | 14.85->14 | n/a | 9.35->10 | 10.23->11 (no downside; AMBIG) | 10 (Rp1) |
| 14 | n/a | 18.9->18 | n/a | 11.9->12 | 13.02->14 (AMBIG) | 13 (Rp1) |
| 15 | n/a | 20.25->20 | n/a | 12.75->13 | 13.95->14 | 13.95->14 |
| 16 | n/a | 21.6->21 | n/a | 13.6->14 | 14.88->15 | 15 |
| 100 | 135 | 135 | 85 | 85 | 93 | 93 |
| 200 | 270 | 270 | 170 | 170 | 186 | 186 |
| 201 | 251.25->250 | 250 | 170.85->171 | 171 | 186.93->187 | 187 |
| 5000 | 6250 | 6250 | 4250 | 4250 | 4650 | 4650 |
| 5001 | 6001.2->6000 | 6000 | 4250.85->4260 | 4260 | 4650.93->4660 | 4660 |
| 10000 | 12000 | 12000 | 8500 | 8500 | 9300 | 9300 |
Notes: ref 10 band is Rp1-10 (+-1). Ref 200 and 5000 are in the lower band (bands "<=200", "<=5000"). Ref 201 ARA 251.25 sits in the tick-2 zone (floor 250). Ref 15 on 10/19-12/31: 7% > Rp1 so tick matters; ARB 14 is only a 1-tick move. Whether 9/25 ARA values apply to Rp50 min price: refs 1-16 untradable then. Rp1-10 band on 9/25: not applicable. Prior-to-2026 sources not checked for 9/25 ARB 15% (from Katadata "Aturan sebelumnya").

## 6. Unresolved
1. Official IDX/OJK primary text (PDF) of Kep-00136, 00157, 00158 never opened; all values are news/broker.
2. Rounding direction/tick conventions for ARA/ARB: not stated by any source.
3. Definition of Acuan Harga: not quoted.
4. What applies from 2027-01-01: Kep-00136 schedule (symmetric 35/25/20) vs "replaced" by 00157/00158 which end 31 Dec 2026 "will be re-evaluated". Not established.
5. ARB at ref Rp1 (ARB Rp1 => Rp0).
6. Oct 19 treatment of Rp1-10 (only "tetap" per one article) and Rp11-14 rounding on that day.
7. Acceleration board and Special Monitoring (watchlist) numeric rules, and whether Kep-00136 split by board.
8. ETF/REIT/DINFRA: 10% (Sept) confirmed by two sources, but effect of the Oct 7% change is not stated; Maybank table flagged hard to parse.
9. Exact publication dates of Maybank, Cermati, Bloomberg Technoz second article.
10. Whether trading holidays fall in 28 Sep-31 Dec (no calendar checked).
