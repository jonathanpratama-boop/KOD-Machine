"""The pooled DOCUMENT_CLASS statistic (idxsig.catalysts.document_class, prereg_3_document_class.json). Synthetic
records only. Each test names the failure it guards against."""

from __future__ import annotations

import unittest

from idxsig import catalysts as cr


def res(sid, family, diff, session, direction=1, window="H20", cls="FIRE", status="RESOLVED", median=0.0, revises=None):
    r = {"type": "RESOLUTION", "family": family, "set_id": sid, "window": window, "coverage": cls, "status": status,
         "signal_session": session, "direction": direction, "candidate": {"trade": {"net_return": diff}},
         "paired": {"candidate_net": diff, "diff": diff, "twins_mean_net": 0.0, "twins_median_net": median}, "cone": []}
    if revises:
        r["revises"] = revises
    return r


def cset(sid, family, close):
    return {"type": "CATALYST_SET", "set_id": sid, "family": family, "signal": {"close": close}}


class DocumentClass(unittest.TestCase):
    def test_parents_only_signed_by_direction_one_record_per_set(self):
        """Guards against: a child family counted beside its parent (a filing twice), an avoid family's correct call
        counted as a loss, an ABSTAIN or H60 record in the class, or a revised resolution counted twice."""
        records = [
            cset("S1", "SEC13D", 42.0), cset("D1", "DILUTION_8K", 3.5), cset("F1", "FORM4", 25.0), cset("F2", "FORM4", 8.0),
            res("S1", "SEC13D", 0.04, "2026-11-02"),
            res("D1", "DILUTION_8K", -0.03, "2026-11-02", direction=-1, median=-0.01),  # the issuer lost: a correct avoid
            res("F1", "FORM4", 0.02, "2026-11-03"),
            res("F2", "FORM4", -0.05, "2026-11-03"),
            res("F2", "FORM4", 0.01, "2026-11-03", revises="x"),  # a later revision replaces the earlier record
            res("V1", "SEC13D_V2", 0.50, "2026-11-02"),  # the same filing as S1: excluded
            res("P1", "FORM4_SHARP", 0.50, "2026-11-03"),  # a subset of FORM4: excluded
            res("A1", "SEC13D", 0.50, "2026-11-02", cls="ABSTAIN"),
            res("H1", "FORM4", 0.50, "2026-11-03", window="H60"),
            res("U1", "FORM4", 0.50, "2026-11-03", status="UNRESOLVABLE"),
        ]
        dc = cr.document_class(records)
        self.assertEqual(dc["families"], ["SEC13D", "DILUTION_8K", "FORM4"])
        m = dc["MEAN"]
        self.assertEqual((m["n_paired"], m["n_sessions"]), (4, 2))
        # sessions: 2026-11-02 mean of (+0.04, +0.03) = 0.035; 2026-11-03 mean of (+0.02, +0.01) = 0.015
        self.assertAlmostEqual(m["mean_diff"], (0.04 + 0.03 + 0.02 + 0.01) / 4)
        self.assertEqual(dc["by_family"]["DILUTION_8K"]["n_paired"], 1)
        self.assertAlmostEqual(dc["by_family"]["DILUTION_8K"]["mean_diff"], 0.03)
        self.assertEqual(dc["by_family"]["FORM4"]["n_paired"], 2)
        wr = dc["win_rate_descriptive"]
        self.assertEqual((wr["n"], wr["wins"]), (4, 4))  # D1: (-0.03 - -0.01) x -1 = +0.02 > 0, a win for the avoid call
        self.assertEqual(dc["by_price_band"]["close_ge_20"]["n_paired"], 2)
        self.assertEqual(dc["by_price_band"]["close_lt_20"]["n_paired"], 2)
        self.assertEqual(m["look"]["verdict"], "accumulating (no look reached)")
        self.assertEqual(m["look"]["next"], 60)

    def test_design_is_the_frozen_file_and_the_looks_are_prereg_2s(self):
        """Guards against: the class silently reading another design, or a look schedule that drifts from the family
        looks it claims to share."""
        design, sha = cr.document_class_design()
        self.assertEqual(design["id"], "KOD-CATALYST-REGISTER-v1-PREREG-3-DOCUMENT-CLASS")
        self.assertEqual(design["looks"]["n"], cr.prereg()[0]["looks"]["n"])
        self.assertEqual(design["looks"]["t_min"], cr.prereg()[0]["looks"]["t_min"])
        self.assertEqual(len(sha), 64)
        self.assertNotIn("SEC13D_V2", design["families"])
        self.assertNotIn("FORM4_SHARP", design["families"])
        self.assertEqual(cr.document_class([])["MEAN"]["n_paired"], 0)

    def test_statistics_and_report_carry_the_class(self):
        """Guards against: the class computed but never shown."""
        st = cr.statistics([])
        self.assertIn("document_class", st)
        md = cr.render(st, [])
        self.assertIn("## DOCUMENT_CLASS", md)
        self.assertIn("accumulating", md)


if __name__ == "__main__":
    unittest.main()
