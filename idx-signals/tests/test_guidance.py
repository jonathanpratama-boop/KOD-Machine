import unittest

from idxsig import guidance as g


class SentenceTests(unittest.TestCase):
    def test_amd_growth_revision(self):
        old = g.guidance_sentence(
            "AMD expects full-year 2021 revenue growth of approximately 37%, "
            "driven by growth across all of our businesses."
        )
        new = g.guidance_sentence(
            "For 2021, AMD now expects revenue to grow approximately 50% compared to 2020."
        )
        self.assertEqual((old.fiscal_year, old.kind, old.mid), (2021, "growth", 0.37))
        self.assertEqual((new.fiscal_year, new.kind, new.mid), (2021, "growth", 0.50))
        self.assertAlmostEqual(g.level_change(new, old), 1.50 / 1.37 - 1)
        self.assertEqual(g.label(g.level_change(new, old)), "RAISE")

    def test_dollar_range_in_billions_and_millions(self):
        s = g.guidance_sentence(
            "The company now expects fiscal 2022 net sales of $4.0 billion to $4.2 billion."
        )
        self.assertEqual((s.fiscal_year, s.kind, s.low, s.high), (2022, "dollar", 4000.0, 4200.0))
        s = g.guidance_sentence(
            "For the full year 2021, we expect revenue of $850 million to $870 million."
        )
        self.assertEqual((s.low, s.high), (850.0, 870.0))
        s = g.guidance_sentence(
            "Full-year 2021 revenue is expected to be approximately $1.25 billion."
        )
        self.assertEqual((s.low, s.high), (1250.0, 1250.0))

    def test_quarter_only_and_eps_are_skipped(self):
        self.assertIsNone(
            g.guidance_sentence(
                "For the fourth quarter of fiscal 2022, we expect revenue of "
                "$1.0 billion to $1.1 billion."
            )
        )
        self.assertIsNone(g.guidance_sentence("We expect 2021 diluted EPS of $1.20 to $1.30."))
        self.assertIsNone(
            g.guidance_sentence("Revenue was $1.2 billion in 2021.")
        )  # no forward cue

    def test_quarter_with_full_year_cue_is_kept(self):
        s = g.guidance_sentence(
            "After a strong third quarter, we now expect full-year 2021 revenue of "
            "$2.1 billion to $2.2 billion."
        )
        self.assertEqual((s.fiscal_year, s.mid), (2021, 2150.0))

    def test_ambiguous_years_are_skipped(self):
        self.assertIsNone(
            g.guidance_sentence("We expect revenue of $2 billion in 2021 and $3 billion in 2022.")
        )

    def test_decline_is_negative(self):
        s = g.guidance_sentence("We now expect fiscal 2020 revenue to decline 5% to 7%.")
        self.assertEqual((s.low, s.high), (-0.07, -0.05))

    def test_release_takes_largest_dollar_figure(self):
        text = (
            "We expect fiscal 2022 Services revenue of $500 million to $520 million.\n"
            "We expect fiscal 2022 total revenue of $2.0 billion to $2.1 billion."
        )
        found = g.release_guidance([text])
        self.assertEqual(found[(2022, "dollar")].mid, 2050.0)

    def test_labels(self):
        self.assertEqual(g.label(0.01), "RAISE")
        self.assertEqual(g.label(0.0099), "MAINTAIN")
        self.assertEqual(g.label(-0.01), "CUT")


class SubmissionTests(unittest.TestCase):
    RAW = (
        b"<SEC-HEADER>\n<ACCEPTANCE-DATETIME>20210427161502\n</SEC-HEADER>\n"
        b"<DOCUMENT>\n<TYPE>8-K\n<TEXT>cover</TEXT>\n</DOCUMENT>\n"
        b"<DOCUMENT>\n<TYPE>EX-99.1\n<TEXT><html><p>For 2021, we now expect revenue to grow approximately"
        b"&nbsp;50% compared to 2020.</p><p>Other text.</p></html></TEXT>\n</DOCUMENT>\n"
    )

    def test_acceptance_and_exhibit(self):
        self.assertEqual(g.acceptance(self.RAW), "20210427161502")
        texts = g.exhibit_texts(self.RAW)
        self.assertEqual(len(texts), 1)
        self.assertEqual(g.release_guidance(texts)[(2021, "growth")].mid, 0.5)


if __name__ == "__main__":
    unittest.main()
