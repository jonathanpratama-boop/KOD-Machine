import unittest

from idxsig.guidance_margin_identity import resolve_identity


class TestIssuerIdentity(unittest.TestCase):
    def test_verified_bindings(self):
        cases = (
            ("Ballard Power Systems Inc.", "NASDAQ: BLDP", "1453015"),
            ("PowerBank Corporation", "NASDAQ: PBK", "2011053"),
            ("Elbit Systems Ltd.", "NASDAQ: ESLT", "1027664"),
            ("MINISO Group Holding Limited", "NYSE: MNSO", "1815846"),
            ("The Home Depot", "NYSE: HD", "354950"),
            ("Opera Limited", "NASDAQ: OPRA", "1737450"),
            ("Spire Inc.", "NYSE: SR", "1126956"),
            ("La-Z-Boy Incorporated", "NYSE: LZB", "57131"),
            ("Dolby Laboratories, Inc.", "NYSE: DLB", "1308547"),
        )
        for issuer, listing, cik in cases:
            with self.subTest(issuer=issuer):
                result = resolve_identity(f"({listing})", issuer)
                self.assertEqual(cik, result["issuer_cik"])
                self.assertEqual(result["ticker"], listing.split()[1])
                self.assertEqual(result["source_url"], "https://www.sec.gov/files/company_tickers_exchange.json")
                self.assertTrue(result["verified_at"])

    def test_uncertain_identity_stays_unresolved(self):
        for text, issuer in [
            ("NYSE: HD", "Spire Inc."), ("NYSE: HD", None),
            ("Home Depot announced strong sales", "The Home Depot"),
            ("Nasdaq: HD", "The Home Depot"), ("NYSE American: HD", "The Home Depot"),
            ("NYSE: HD and Nasdaq: OMIT", "The Home Depot"),
            ("NYSE: HD and NYSE Arca: OMIT", "The Home Depot"),
            ("NYSE: HD and NYSE: HD.PR", "The Home Depot"),
            ("NYSE: HDfoo", "The Home Depot"), ("NYSE: HD/A", "The Home Depot"),
        ]:
            with self.subTest(text=text, issuer=issuer):
                self.assertIsNone(resolve_identity(text, issuer, title="The Home Depot (NYSE: HD)"))

    def test_repeated_listing_and_foreign_listing(self):
        matched = resolve_identity("(NASDAQ:\u00a0BLDP; TSX: BLDP) and (Nasdaq: BLDP)", "Ballard Power Systems Inc.")
        self.assertEqual(matched["ticker"], "BLDP")
