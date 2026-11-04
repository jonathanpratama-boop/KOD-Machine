import unittest

from idxsig import call_cert as cc


class Shadow(unittest.TestCase):
    def test_history_bar_certifies_on_pooled_years(self):
        m = cc.models()
        cert = cc.certificate(list(zip(m["cal_p"], m["cal_y"])))
        self.assertIsNotNone(cert["chosen"])
        self.assertGreater(len(m["cal_p"]), 2000)

    def test_bar_uses_only_outcomes_resolved_before_each_forecast(self):
        feats = dict.fromkeys(cc.learner3.FEATURES, 0.0)
        lrecs = [
            {
                "type": cc.learner3.RECORD,
                "set_id": f"S{i}",
                "ticker": f"T{i}",
                "signal_session": "2026-11-0%d" % (i + 2),
                "made_at": "2026-11-0%dT22:00:00Z" % (i + 2),
                "features": feats,
                "forecasts": {cc.STATEMENT: {"raw": 0.3}},
            }
            for i in range(3)
        ]
        orig = cc.learner3.outcome_of, cc.learner3.outcomes
        try:
            cc.learner3.outcomes = lambda records, asof: {}
            cc.learner3.outcome_of = (
                lambda outc, sid, stmt: (True, "2026-11-04T21:00:00Z") if sid == "S0" else None
            )
            live = cc.rows(records=[], lrecs=lrecs, asof="2026-11-10T00:00:00Z")
        finally:
            cc.learner3.outcome_of, cc.learner3.outcomes = orig
        by = {r["set_id"]: r for r in live}
        self.assertEqual(
            by["S0"]["n_live_calibration"], 0
        )  # its own outcome is never in its calibration
        self.assertEqual(
            by["S1"]["n_live_calibration"], 0
        )  # made 2026-11-03 22:00, before S0 resolved (11-04 21:00)
        self.assertEqual(by["S2"]["n_live_calibration"], 1)  # made 2026-11-04 22:00, after it
        self.assertEqual(by["S0"]["y"], 1)
        self.assertIsNone(by["S1"]["y"])

    def test_report_renders_without_live_forecasts(self):
        text = cc.render([], "2026-10-29T00:00:00Z")
        self.assertIn("The three plain answers", text)
        self.assertIn("no live forecast yet", text)


if __name__ == "__main__":
    unittest.main()
