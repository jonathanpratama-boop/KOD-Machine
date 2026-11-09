import unittest

import numpy as np

from idxsig import market


def lim(ref, day):
    ara, arb = market.limits(np.array([float(ref)]), np.array([np.datetime64(day, "D")]))
    return int(ara[0]), int(arb[0])


class TickTests(unittest.TestCase):
    def test_tick_bands(self):
        prices = np.array([50, 199, 200, 499, 500, 1999, 2000, 4999, 5000, 30000])
        self.assertEqual(market.tick_size(prices).tolist(), [1, 1, 2, 2, 5, 5, 10, 10, 25, 25])

    def test_rounding_to_tick(self):
        self.assertEqual(market.floor_tick(np.array([1253.0]))[0], 1250)
        self.assertEqual(market.ceil_tick(np.array([1251.0]))[0], 1255)
        self.assertEqual(market.floor_tick(np.array([6030.0]))[0], 6025)


class AutoRejectionScheduleTests(unittest.TestCase):
    def test_symmetric_before_covid(self):
        self.assertEqual(lim(1000, "2019-08-01"), (1250, 750))
        self.assertEqual(lim(100, "2019-08-01"), (135, 65))
        self.assertEqual(lim(6000, "2019-08-01"), (7200, 4800))

    def test_band_edges(self):
        self.assertEqual(lim(200, "2019-08-01"), (270, 130))  # <= Rp200 is the 35% band
        self.assertEqual(lim(5000, "2019-08-01"), (6250, 3750))  # <= Rp5,000 is the 25% band
        self.assertEqual(lim(5025, "2019-08-01")[0], 6025)  # above: 20%, floored to the Rp25 tick

    def test_covid_asymmetric(self):
        self.assertEqual(lim(1000, "2020-03-10"), (1250, 900))
        self.assertEqual(lim(1000, "2020-03-13"), (1250, 930))
        self.assertEqual(lim(1000, "2023-06-02"), (1250, 930))

    def test_normalisation_stages(self):
        self.assertEqual(lim(1000, "2023-06-05"), (1250, 850))
        self.assertEqual(lim(1000, "2023-09-04"), (1250, 750))

    def test_april_2025_and_september_2026(self):
        self.assertEqual(lim(1000, "2025-04-07"), (1250, 750))
        self.assertEqual(lim(1000, "2025-04-08"), (1250, 850))
        self.assertEqual(lim(8, "2026-09-28"), (9, 7))  # Rp1-10: +/- Rp1
        # No expectation for 2027: no rule is confirmed after 2026-12-31; the labelled convention for those
        # dates is tested in tests/test_market_oct2026.py (UnconfirmedPeriodConvention*Tests).

    def test_floor_rp50_until_september_2026(self):
        self.assertEqual(lim(55, "2024-01-02")[1], 50)
        self.assertEqual(lim(55, "2026-10-01")[1], 47)

    def test_dates_before_schedule_are_refused(self):
        with self.assertRaises(ValueError):
            lim(1000, "2019-07-26")

    def test_special_board(self):
        ara, arb = market.special_limits(np.array([1000.0, 8.0]))
        self.assertEqual(ara.tolist(), [1100, 9])
        self.assertEqual(arb.tolist(), [900, 7])


if __name__ == "__main__":
    unittest.main()
