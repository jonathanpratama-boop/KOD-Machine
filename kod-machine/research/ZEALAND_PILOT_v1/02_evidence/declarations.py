"""Write the KOD-EVIDENCE-v2 declarations for ZEALAND_PILOT_v1 (one JSON per document).

Run from kod-machine/:  python3 research/ZEALAND_PILOT_v1/02_evidence/declarations.py
Then record each with:  python3 -m kod --db var/kod.db evidence <declaration> [--file <bytes>]

Publication times come from the exchange system's releaseTime (queried with timeZone=CET).
For dates in summer time the feed's clock may be local CEST; the conversion below uses fixed
UTC+1, which gives the later of the two possible instants (conservative for "published by
the cutoff"; the true instant may be one hour earlier). Retrieval times come from fetch_log.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = {r["file"]: r for r in json.loads((HERE / "fetch_log.json").read_text())["retrieved"] if r["file"]}
AR = next(r for r in json.loads((HERE / "fetch_log.json").read_text())["retrieved"] if r["file"] is None)

T30, T72, T24 = "2025-02-09T16:00:00Z", "2025-03-08T16:00:00Z", "2025-03-10T16:00:00Z"
DECISION = "2025-03-11T16:00:00Z"
FEED = ("releaseTime of the Nasdaq Nordic company-announcement system (api.news.eu.nasdaq.com, "
        "pinned in 01_protocol/pin), read as UTC+1")
PROV = "retrieved from the exchange's announcement viewer; bytes in research/ZEALAND_PILOT_v1/02_evidence/raw"
NO_ARCHIVE = ("Existence: the exchange system's own release time. Content: not verified; no archive capture "
              "dated by the cutoff could be checked (Internet Archive rate-limited from this environment).")


def utc(cet: str) -> str:
    return (datetime.strptime(cet, "%Y-%m-%d %H:%M:%S") - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def exchange(key, raw, as_of, title, notes, publisher="Zealand Pharma A/S via Nasdaq Copenhagen",
             doc="company announcement", event_time=None):
    r = LOG[raw]
    return key, raw, {
        "source_url": r["url"], "source_type": "PRIMARY", "publisher": publisher, "document_type": doc,
        "title": title, "event_time": event_time,
        "publication_time": utc(r["release_time_cet"]), "publication_time_basis": FEED,
        "retrieval_time": r["retrieved_at"], "as_of_cutoff": as_of, "evidence_grade": "B",
        "existence_method": "PRIMARY_SOURCE_TIMESTAMP", "content_method": "NONE",
        "verification_notes": NO_ARCHIVE + " " + notes, "provenance": PROV,
    }


DECLS = [
    exchange("P01_offering_2024-06-25", "raw/nasdaq_zeal_1303357.html", T30,
             "Zealand Pharma launches equity offering of new shares (USD 900m)",
             "Quote: 'The Company is prioritizing resources on R&D and expects to engage in strategic partnerships "
             "for commercialization and co-development.' No asset or timing named."),
    exchange("P02_h1_2024", "raw/nasdaq_zeal_1310818.html", T30,
             "Zealand Pharma Announces Financial Results for the First Half of 2024",
             "CEO quote: 'we are investing significantly in our differentiated obesity candidates to accelerate the "
             "development programs as we explore partnership opportunities.' No asset-specific timing."),
    exchange("P03_9m_2024", "raw/nasdaq_zeal_1326289.html", T30,
             "Zealand Pharma Announces Financial Results for the First Nine Months of 2024",
             "Partnership discussions are stated for glepaglutide and dasiglucagon (rare diseases) only. Petrelintide: "
             "Phase 2b start Q4 2024, enrolment completion H1 2025, second Phase 2b in H1 2025. No partnering statement "
             "for petrelintide."),
    exchange("P04_pdmr_sale_2024-11", "raw/nasdaq_zeal_1327123_attachment.pdf", T30,
             "PDMR notification: Anneline Nansen, sale of 1,500 shares", "Board member (employee elected) sold 1,000 "
             "at DKK 850 and 500 at DKK 847 on 2024-11-08 (DKK 1,273,500).", doc="PDMR notification (MAR art. 19)"),
    exchange("P05_glepaglutide_crl", "raw/nasdaq_zeal_1334667.html", T30,
             "FDA Complete Response Letter for glepaglutide NDA", "Rare-disease setback; not petrelintide.",
             doc="company announcement (inside information)"),
    exchange("P06_pdmr_purchase_2024-12", "raw/nasdaq_zeal_1335333_attachment.pdf", T30,
             "PDMR notification: Leonard Kruimer, purchase of 300 shares", "Board member bought 300 shares at DKK 720 "
             "on 2024-12-20 on Nasdaq Copenhagen (DKK 216,000). Form is a scanned image, read visually.",
             doc="PDMR notification (MAR art. 19)"),
    exchange("P07_pdmr_inheritance_2025-01", "raw/nasdaq_zeal_1337157_attachment.pdf", T30,
             "PDMR notification: Frederik Barfoed Beck, inheritance of 1,090 shares", "Not a market trade (price DKK 0, "
             "outside a trading venue). The last PDMR notification before the event.",
             doc="PDMR notification (MAR art. 19)"),
    exchange("P08_fy_2024", "raw/nasdaq_zeal_1344139.html", T72,
             "Zealand Pharma Announces Financial Results for the Full Year 2024",
             "Quotes: 'significantly accelerate its investments in the company's wholly-owned obesity programs, which in "
             "2025 will include three large Phase 2b trials'; 2025 guidance for 'Revenue anticipated from existing and new "
             "license and partnership agreements': 'No guidance'. No petrelintide partnering statement or timing.",
             doc="annual financial report announcement"),
    ("P09_annual_report_2024", None, {
        "source_url": AR["url"], "source_type": "PRIMARY", "publisher": "Zealand Pharma A/S via Nasdaq Copenhagen",
        "document_type": "annual report 2024 (attachment to announcement 1344139)",
        "title": "Zealand Pharma 2024 Annual Report", "event_time": None,
        "publication_time": utc(AR["release_time_cet"]), "publication_time_basis": FEED + " of the announcement it is attached to",
        "retrieval_time": AR["retrieved_at"], "as_of_cutoff": T72, "evidence_grade": "B",
        "existence_method": "PRIMARY_SOURCE_TIMESTAMP", "content_method": "NONE",
        "verification_notes": NO_ARCHIVE + f" Bytes not archived here (17 MB); sha256 {AR['sha256']}. Quotes: "
        "'Zealand's strategy is to pursue global co-development and commercialization partnerships that complement and "
        "extend our capabilities'; 'we continue our efforts to initiate new strategic partnerships for co-development "
        "and commercialization' (in the rare-disease paragraph). Of 31 petrelintide mentions none is near a partnering "
        "statement or timing.",
        "provenance": "retrieved from the exchange attachment URL; text extract in 02_evidence/raw/annual_report_2024.txt"}),
    exchange("P10_ads_delisting_2022", "raw/nasdaq_zeal_1174635.html", DECISION,
             "Zealand Pharma Announces Voluntary Delisting of ADSs from the Nasdaq Global Select Market",
             "Trading consolidated on Nasdaq Copenhagen (ZEAL, DKK); ADS delisting expected effective by end of Q3 2022.",
             doc="company announcement (inside information)"),
    exchange("N01_redefine1", "raw/nasdaq_novo_1334781.html", T30,
             "Novo Nordisk: CagriSema REDEFINE 1", "Amylin-class (cagrilintide combination) phase 3 readout; context only.",
             publisher="Novo Nordisk A/S via Nasdaq Copenhagen", doc="company announcement (inside information)"),
    exchange("N02_amycretin", "raw/nasdaq_novo_1338827.html", T30,
             "Novo Nordisk: subcutaneous amycretin phase 1b/2a", "Amylin/GLP-1 co-agonist readout; context only.",
             publisher="Novo Nordisk A/S via Nasdaq Copenhagen", doc="company announcement (inside information)"),
    exchange("N03_redefine2", "raw/nasdaq_novo_1347896.html", T24,
             "Novo Nordisk: CagriSema REDEFINE 2", "Released 2025-03-10 11:23:57 CET: 15.7% weight loss at 68 weeks if "
             "adherent (13.7% treatment policy) vs 3.1%/3.4% placebo. Amylin-class context the session before the cutoff.",
             publisher="Novo Nordisk A/S via Nasdaq Copenhagen", doc="company announcement (inside information)"),
    exchange("E00_event", "raw/nasdaq_zeal_1348334.html", "2025-03-12T06:00:00Z",
             "Zealand Pharma and Roche enter collaboration and license agreement for petrelintide",
             "The event. Upfront USD 1.65bn (1.4bn at closing), total up to USD 5.3bn, 50/50 US/EU profit share; closing "
             "expected Q2 2025. Published after the decision cutoff; never cited in an information set.",
             doc="company announcement (inside information)", event_time="2025-03-12T06:00:00Z"),
    ("S01_investing_2024-08-20", None, {
        "source_url": "https://www.investing.com/news/stock-market-news/zealand-pharma-rebound-after-prior-session-losses-3578702",
        "source_type": "SECONDARY", "publisher": "Investing.com", "document_type": "news article",
        "title": "Zealand Pharma rebound after prior session losses", "event_time": None,
        "publication_time": "2024-08-20T09:02:00Z",
        "publication_time_basis": "time printed on the article page ('Aug 20, 2024, 05:02 AM'; the text gives 0902 GMT)",
        "retrieval_time": "2026-10-08T12:35:00Z", "as_of_cutoff": T30, "evidence_grade": "C",
        "existence_method": "NONE", "content_method": "NONE",
        "verification_notes": "Read through a fetch tool (direct download returned 403); bytes not held; retrieval time "
        "approximate. States the previous session's fall followed 'comments by the company's CEO ... about seeking a "
        "large pharmaceutical partner for the company's weight loss drug'. No timing.",
        "provenance": "web page as served on 2026-10-08"}),
    ("S02_pharmtech_2025-02-20", None, {
        "source_url": "https://www.pharmaceutical-technology.com/news/zealand-pharma-steadfastly-upholds-amylin-based-obesity-drug-strategy/",
        "source_type": "SECONDARY", "publisher": "Pharmaceutical Technology (GlobalData)", "document_type": "news article",
        "title": "Zealand Pharma steadfastly upholds amylin-based obesity drug strategy", "event_time": None,
        "publication_time": "2025-02-20T23:59:59Z",
        "publication_time_basis": "date printed on the article page (20 February 2025); no time of day shown, so the end of that UTC day is used",
        "retrieval_time": "2026-10-08T12:35:00Z", "as_of_cutoff": T72, "evidence_grade": "C",
        "existence_method": "NONE", "content_method": "NONE",
        "verification_notes": "Read through a fetch tool (direct download returned 403); bytes not held; retrieval time "
        "approximate. Reports the partner search for petrelintide 'remains ongoing', the CEO on the 20 February call "
        "saying the company is 'exactly where it wants to be in the process', and a preference for a co-development and "
        "co-commercialisation partnership with profit-sharing. No date or window.",
        "provenance": "web page as served on 2026-10-08"}),
    ("M01_auctions_factsheet", "raw/nasdaq_nordic_auctions_factsheet_2026.pdf", {
        "source_url": LOG["raw/nasdaq_nordic_auctions_factsheet_2026.pdf"]["url"], "source_type": "RETROSPECTIVE",
        "publisher": "Nasdaq", "document_type": "exchange factsheet", "title": "Nasdaq Nordic Auctions factsheet",
        "event_time": None, "publication_time": None, "publication_time_basis": None,
        "retrieval_time": LOG["raw/nasdaq_nordic_auctions_factsheet_2026.pdf"]["retrieved_at"], "as_of_cutoff": DECISION,
        "evidence_grade": "D", "existence_method": "NONE", "content_method": "NONE",
        "verification_notes": "Current document (copyright 2026, cites Q2 2026 statistics). Copenhagen shares: opening "
        "auction 08:45-09:00 CET, random uncross 09:00:00-09:00:05; closing auction 16:55-17:00, uncross 16:59:30-17:00. "
        "Applying it to March 2025 is an assumption.", "provenance": "downloaded from nasdaq.com"}),
    ("M02_dk_share_duty_repeal", "raw/folketingstidende_1998_L33_vedtaget.pdf", {
        "source_url": LOG["raw/folketingstidende_1998_L33_vedtaget.pdf"]["url"], "source_type": "PRIMARY",
        "publisher": "Folketinget (Danish Parliament)", "document_type": "adopted act",
        "title": "Lov om ophævelse af lov om afgift ved overdragelse af aktier m.v. (L 33, 1998-99)",
        "event_time": "1999-10-01T00:00:00Z", "publication_time": "1998-12-16T00:00:00Z",
        "publication_time_basis": "date of Lov nr. 909 af 16. december 1998, printed in the official Folketingstidende record "
        "(adopted at third reading 15 December 1998)",
        "retrieval_time": LOG["raw/folketingstidende_1998_L33_vedtaget.pdf"]["retrieved_at"], "as_of_cutoff": DECISION,
        "evidence_grade": "B", "existence_method": "PRIMARY_SOURCE_TIMESTAMP", "content_method": "NONE",
        "verification_notes": "Repeals the share transfer duty (aktieafgiftsloven) for transfers from 1 October 1999. That "
        "no transfer duty was reintroduced by March 2025 is not shown by this document and is an assumption.",
        "provenance": "downloaded from folketingstidende.dk"}),
    ("D01_price_series", None, {
        "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/ZEAL.CO?period1=1420070400&period2=1791461930&interval=1d&events=div%2Csplits&includeAdjustedClose=true",
        "source_type": "RETROSPECTIVE", "publisher": "Yahoo Finance", "document_type": "daily price series",
        "title": "ZEAL.CO daily bars 2015-01-02..2026-10-08", "event_time": None, "publication_time": None,
        "publication_time_basis": None, "retrieval_time": "2026-10-08T12:18:51Z", "as_of_cutoff": DECISION,
        "evidence_grade": "D", "existence_method": "NONE", "content_method": "NONE",
        "verification_notes": "A vendor series retrieved in 2026; it cannot show what the tape displayed in 2025. Bytes "
        "committed at research/ZEALAND_PILOT_v1/01_protocol/pin/ZEAL.CO.json, sha256 "
        "a20b3934ebc11a3f4d44e9e11d73e5636ecf3543994ce58ad5b10d6b40598b8b (manifest yahoo_dk-20261008T121850Z).",
        "provenance": "idxsig yahoo fetcher"}),
]


def main() -> None:
    out = HERE / "declarations"
    out.mkdir(exist_ok=True)
    plan = []
    for key, raw, meta in DECLS:
        (out / f"{key}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        plan.append({"key": key, "declaration": f"declarations/{key}.json", "file": raw})
    (HERE / "record_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(f"{len(plan)} declarations")


if __name__ == "__main__":
    main()
