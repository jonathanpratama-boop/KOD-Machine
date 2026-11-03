import unittest

from idxsig import multiple_testing as mt


class MultipleTestingTests(unittest.TestCase):
    def test_p_values(self):
        self.assertAlmostEqual(mt.p_one_sided(1.959964, 1.0), 0.025, places=4)
        self.assertAlmostEqual(mt.se_from_ci95(-1.0, 1.0), 1.0 / 1.959964, places=6)
        self.assertAlmostEqual(mt.p_from_t(0.0), 0.5)

    def test_holm_matches_textbook(self):
        p = [0.01, 0.04, 0.03, 0.005]
        self.assertEqual([round(x, 4) for x in mt.holm(p)], [0.03, 0.06, 0.06, 0.02])

    def test_bh_matches_textbook(self):
        p = [0.01, 0.04, 0.03, 0.005]
        self.assertEqual([round(x, 4) for x in mt.benjamini_hochberg(p)], [0.02, 0.04, 0.04, 0.02])

    def test_adjusted_never_below_raw_and_capped(self):
        p = [0.9, 0.5, 0.2, 0.07]
        for f in (mt.holm, mt.benjamini_hochberg):
            adj = f(p)
            self.assertTrue(all(a >= r - 1e-12 and a <= 1.0 for a, r in zip(adj, p)))

    def test_hurdles_grow_with_tries(self):
        self.assertAlmostEqual(mt.hurdle_z(1), 1.645, places=2)
        self.assertGreater(mt.hurdle_z(100), mt.hurdle_z(10))
        self.assertGreater(mt.expected_max_z(300), mt.expected_max_z(15))
        self.assertAlmostEqual(mt.hurdle_z(20, method="sidak"), mt.hurdle_z(20), places=1)
        self.assertEqual(mt.project_hurdle(5), 3.0)  # the floor binds with few tries
        self.assertGreater(mt.project_hurdle(1000), 3.0)  # the Bonferroni bar binds with many


if __name__ == "__main__":
    unittest.main()
