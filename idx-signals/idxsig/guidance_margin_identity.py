"""Additional SEC listings verified against named PRNewswire issuer accounts."""

import re


SEC_DIRECTORY = "https://www.sec.gov/files/company_tickers_exchange.json"
VERIFIED_AT = "2026-11-18T06:53:26+00:00"
# SEC CIK, SEC issuer name, SEC exchange, exact publishing-account name on
# the retained issuer release. Keep the frozen research CIK map independent.
LISTINGS = {
    "BLDP": (
        "1453015",
        "Ballard Power Systems Inc.",
        "Nasdaq",
        "Ballard Power Systems Inc.",
    ),
    "PBK": ("2011053", "POWERBANK Corp", "Nasdaq", "PowerBank Corporation"),
    "ESLT": ("1027664", "ELBIT SYSTEMS LTD", "Nasdaq", "Elbit Systems Ltd."),
    "MNSO": (
        "1815846",
        "MINISO Group Holding Ltd",
        "NYSE",
        "MINISO Group Holding Limited",
    ),
    "HD": ("354950", "HOME DEPOT, INC.", "NYSE", "The Home Depot"),
    "OPRA": ("1737450", "Opera Ltd", "Nasdaq", "Opera Limited"),
    "SR": ("1126956", "SPIRE INC", "NYSE", "Spire Inc."),
    "LZB": ("57131", "LA-Z-BOY INC", "NYSE", "La-Z-Boy Incorporated"),
    "DLB": ("1308547", "Dolby Laboratories, Inc.", "NYSE", "Dolby Laboratories, Inc."),
}

# Capture the whole token. Otherwise e.g. "NYSE: HD.PR" or "HDfoo" could
# accidentally match the ordinary shares of Home Depot.
LISTING_TAG = re.compile(
    r"\b((?i:NASDAQ|NYSE(?: American| Arca)?|AMEX))\s*[:：]\s*"
    r"([A-Za-z0-9]+(?:[.\-/][A-Za-z0-9]+)*)"
)


def resolve_identity(text, issuer_name, *, title="", directory=None):
    """Require a single US listing in source text and exact issuer metadata."""
    if not issuer_name:
        return None
    tags = {(exchange.casefold(), ticker) for exchange, ticker in LISTING_TAG.findall(text)}
    if len(tags) != 1:
        return None
    exchange, ticker = tags.pop()
    if directory:
        from .guidance_margin_directory import company_key

        row = directory["listings"].get(ticker)
        if (
            row
            and exchange == row[2].casefold()
            and company_key(issuer_name) == company_key(row[1])
        ):
            return dict(
                ticker=ticker,
                issuer_cik=row[0],
                issuer_name=row[1],
                wire_issuer_name=issuer_name,
                exchange=row[2],
                source_url=directory["sources"][-1]["url"],
                sources=directory["sources"],
                verified_at=directory["verified_at"],
            )
        if ticker in directory["listings"] or ticker in directory.get("unresolved_tickers", ()):
            return None
    listing = LISTINGS.get(ticker)
    if not listing:
        return None
    cik, sec_name, sec_exchange, wire_name = listing
    if (
        exchange != sec_exchange.casefold()
        or issuer_name.strip().casefold() != wire_name.casefold()
    ):
        return None
    return {
        "ticker": ticker,
        "issuer_cik": cik,
        "issuer_name": sec_name,
        "wire_issuer_name": wire_name,
        "exchange": sec_exchange,
        "source_url": SEC_DIRECTORY,
        "verified_at": VERIFIED_AT,
    }
