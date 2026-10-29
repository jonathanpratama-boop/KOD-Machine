import random
import unittest
from math import comb

from idxsig import risk_control as rc


class Binomial(unittest.TestCase):
    def test_cdf_matches_direct_sum(self):
        for n, p in ((10, 0.3), (57, 0.5), (200, 0.05)):
            for k in (0, 3, n // 2, n - 1):
                direct = sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
                self.assertAlmostEqual(rc.binom_cdf(k, n, p), direct, places=10)

    def test_edges(self):
        self.assertEqual(rc.binom_cdf(-1, 5, 0.5), 0.0)
        self.assertEqual(rc.binom_cdf(5, 5, 0.5), 1.0)
        self.assertEqual(rc.p_value(0, 0, 0.5), 1.0)


class Certify(unittest.TestCase):
    def test_stops_at_first_failure_and_picks_most_calls(self):
        # 1,000 scores; wrong only below 0.45: the strict thresholds pass, 0.3 (21% wrong) fails at alpha 0.2
        scores = [i / 1000 for i in range(1, 1001)]
        wrong = [1 if s < 0.45 else 0 for s in scores]
        ths = [0.9, 0.7, 0.5, 0.3, 0.1]
        out = rc.certify(scores, wrong, ths, alpha=0.2, delta=0.05)
        self.assertEqual(out["certified"], [0.9, 0.7, 0.5])
        self.assertEqual(out["chosen"], 0.5)
        self.assertEqual(len(out["tested"]), 4)  # 0.3 failed, 0.1 never tested

    def test_null_is_rarely_certified(self):
        # every call is a coin flip: a certificate at alpha 0.4 should come out at most about delta of the time
        rng, hits = random.Random(1), 0
        for _ in range(300):
            scores = [rng.random() for _ in range(300)]
            wrong = [int(rng.random() < 0.5) for _ in range(300)]
            out = rc.certify(scores, wrong, [0.95, 0.9, 0.8, 0.7, 0.5], alpha=0.4, delta=0.05)
            hits += bool(out["certified"])
        self.assertLessEqual(hits / 300, 0.08)

    def test_realised(self):
        r = rc.realised([0.9, 0.8, 0.2], [0, 1, 1], 0.5, alpha=0.5)
        self.assertEqual((r["calls"], r["losses"], r["losing_rate"]), (2, 1, 0.5))
        self.assertIsNone(rc.realised([0.1], [1], None, 0.5)["losing_rate"])


if __name__ == "__main__":
    unittest.main()
