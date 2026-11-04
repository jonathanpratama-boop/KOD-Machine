import unittest

from idxsig import guidance_v2 as g


def got(sentence):
    x = g.guidance_sentence(sentence)
    return None if x is None else (x.kind, round(x.low, 6), round(x.high, 6))


class AnchoredAmountTests(unittest.TestCase):
    def test_revenue_range_after_the_term(self):
        self.assertEqual(
            got(
                "• Increase in full year 2021 revenue guidance to a range of $1.88 billion to $2.00 "
                "billion, from prior guidance range of $1.78 billion to $1.90 billion."
            ),
            ("dollar", 1880.0, 2000.0),
        )
        self.assertEqual(
            got("- Reiterating FY21 net sales guidance of $510 to $550 million"),
            ("dollar", 510.0, 550.0),
        )

    def test_amount_directly_before_the_term(self):
        self.assertEqual(
            got(
                "Our 4Q22 outlook implies $2.80 to $2.81 billion in revenue for 2022, which is below"
            ),
            ("dollar", 2800.0, 2810.0),
        )

    def test_growth(self):
        self.assertEqual(
            got("For fiscal 2022, AMD now expects revenue growth of approximately 60%."),
            ("growth", 0.6, 0.6),
        )
        self.assertEqual(
            got(
                "The Company expects its overall revenue for fiscal year 2021 to grow 11-14% year-over "
                "year, up from its previous guidance of 10-13%."
            ),
            ("growth", 0.11, 0.14),
        )
        self.assertEqual(
            got(
                "We now expect fiscal 2022 revenue to grow 10% to 12% from fiscal 2021 revenue of "
                "$500 million."
            ),
            ("growth", 0.10, 0.12),
        )

    def test_another_measure_in_between(self):
        self.assertIsNone(
            got(
                "For full year 2021, we expect revenue and adjusted EBITDA of $500 million and $100 "
                "million."
            )
        )
        self.assertIsNone(
            got(
                "Well positioned to achieve the high end of our full year guidance • 10 - 12% Revenue "
                "Growth • 26 - 28% Adjusted EBITDA Full Year 2022 Outlook"
            )
        )


class QualifierTests(unittest.TestCase):
    def test_segment_or_measure_names(self):
        self.assertIsNone(
            got(
                "Therefore, we are updating our 2022 guidance for the following: Adjusting total "
                "revenue and Software Platform revenue by the $210 million non recurring publisher "
                "bonuses recorded as contra-revenue."
            )
        )
        self.assertIsNone(
            got(
                "BPaaS full year revenue growth of 16.8% to $390 million, ahead of our initial 12% "
                "2021 outlook"
            )
        )
        self.assertIsNone(
            got("The company expects full-year 2021 organic sales growth of 5% to 7%.")
        )
        self.assertIsNone(
            got(
                "For the full year ending December 31, 2021, the Company now expects adjusted revenues "
                "to be $2.320 - $2.350 billion, compared to prior guidance"
            )
        )

    def test_time_words_are_skipped_back_over(self):
        self.assertEqual(
            got(
                "● Expect Full Year 2022 Revenue of $250 million and Adjusted EBITDA of $26 million"
            ),
            ("dollar", 250.0, 250.0),
        )


class SubjectTests(unittest.TestCase):
    def test_acquired_business_and_year_to_date(self):
        self.assertIsNone(
            got(
                "B&G Foods projects that in 2021, the acquired business will continue to benefit from "
                "increased demand and generate annual net sales of approximately $270.0 million."
            )
        )
        self.assertIsNone(
            got(
                "Full-year 2022 guidance assumes COVID-19 testing-related sales of $7.8 billion, which "
                "includes sales of $7.3 billion through September 2022."
            )
        )
        self.assertIsNone(
            got(
                "StonePoint is projected to generate revenues of $117 million for the twelve months "
                "ending March 31, 2021."
            )
        )


if __name__ == "__main__":
    unittest.main()
