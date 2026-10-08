"""Paper scorer v2: units from corroborated split records, UNSCORABLE with a reason otherwise,
linked revisions. Synthetic data; no ledger, network or market files are touched."""

import copy
import unittest
import warnings
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import paper
from tests.test_paper_markets import DATA, VALIDATED, gframe


def events(*rows):
    cols = ["ticker", "effective_session", "numerator", "denominator", "provider_ratio", "kind"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


class ScorerV2(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")
        base = gframe(spike=(7, 70))
        self.decision = paper.scan_frame(base[base["date"] <= base["date"].unique()[70]], DATA, validation=VALIDATED,
                                         market="US")["decisions"][0]
        self.ran = gframe(spike=(7, 70), tail=0.03, gap=0.01)
        self.session_after = str(self.ran["date"].unique()[73].date())

    def reverse_split(self, df, after_session, ratio=10):
        """What the provider shows after a 1:ratio reverse split effective at `after_session`: from
        then on shares trade at ratio x the old price, and the history before is multiplied by
        ratio to match, so the whole adjusted series is ratio x the old one (volume / ratio)."""
        df = df.copy()
        rows = df["ticker"] == "T007"
        for col in ("previous", "open", "high", "low", "close"):
            df.loc[rows, col] = df.loc[rows, col] * ratio
        df.loc[rows, "volume"] = df.loc[rows, "volume"] / ratio
        return df

    def scored(self, df, ev, verify=None):
        m = paper._market(df, "US")
        units, reason, evidence = paper.scoring_units(self.decision, m, ev, verify)
        return (paper.score(self.decision, m, price_units=units) if units else None), reason, evidence

    def test_no_split_scores_with_v2(self):
        out, reason, _ = self.scored(self.ran, events())
        self.assertIsNone(reason)
        self.assertEqual(out["scoring_version"], "verified-us-units-v1")
        self.assertEqual(out["decision_verdict"], "PROFIT")

    def test_corroborated_split_inside_the_window_leaves_the_outcome_unchanged(self):
        """Guards against: a reverse split between signal and exit changing stop, chase or costs."""
        plain, _, _ = self.scored(self.ran, events())
        split = self.reverse_split(self.ran, self.session_after)
        ev = events(("T007", self.session_after, 1.0, 10.0, "1:10", "SPLIT"))
        out, reason, evidence = self.scored(split, ev, verify=lambda e: ("VERIFIED", [{"accession": "x"}]))
        self.assertIsNone(reason)
        self.assertEqual(evidence[0]["status"], "VERIFIED")
        a, b = plain["execution"]["paper_trade"], out["execution"]["paper_trade"]
        self.assertEqual(a["exit_reason"], b["exit_reason"])
        self.assertAlmostEqual(b["entry_price_as_traded"], a["entry_price_as_traded"], places=6)
        self.assertAlmostEqual(b["entry_cost_rate"], a["entry_cost_rate"])
        # after a 1:10 reverse split the shares really are sold at 10x: the exit tier is the one at that price
        self.assertAlmostEqual(b["exit_price_as_traded"], 10 * a["exit_price_as_traded"], places=6)
        gross = lambda t: (1 + t["net_return"]) * (1 + t["entry_cost_rate"]) / (1 - t["exit_cost_rate"])  # noqa: E731
        self.assertAlmostEqual(gross(a), gross(b), places=9)

    def test_uncorroborated_split_is_unscorable_with_the_reason(self):
        split = self.reverse_split(self.ran, self.session_after)
        ev = events(("T007", self.session_after, 1.0, 10.0, "1:10", "SPLIT"))
        out, reason, evidence = self.scored(split, ev, verify=lambda e: ("NO_EVIDENCE", []))
        self.assertIsNone(out)
        self.assertIn("not corroborated", reason)

    def test_rescaled_history_without_a_record_does_not_reconcile(self):
        """Guards against: inferring a split from a changed price ratio (the legacy scorer did)."""
        split = self.reverse_split(self.ran, self.session_after)
        m = paper._market(split, "US")
        units, reason, _ = paper.scoring_units(self.decision, m, events())
        self.assertIsNone(reason)
        with self.assertRaisesRegex(ValueError, "does not reconcile"):
            paper.score(self.decision, m, price_units=units)

    def test_idx_split_without_an_independent_source_is_unscorable(self):
        d = copy.deepcopy(self.decision)
        d["market"] = "IDX"
        m = paper._market(self.ran, "US")
        _, reason, _ = paper.scoring_units(d, m, events(("T007", self.session_after, 1.0, 5.0, "1:5", "SPLIT")))
        self.assertIn("no independent IDX corporate-action source", reason)

    def test_crypto_is_unadjusted(self):
        d = copy.deepcopy(self.decision)
        d["market"] = "CRYPTO"
        units, reason, _ = paper.scoring_units(d, paper._market(self.ran, "US"), events())
        self.assertEqual(units["convention"], "UNADJUSTED")
        self.assertIsNone(reason)


class Revisions(unittest.TestCase):
    def test_rescore_appends_a_revision_linked_to_the_earlier_outcome(self):
        """Guards against: a corrected outcome overwriting, or floating free of, the original."""
        warnings.simplefilter("ignore")
        base = gframe(spike=(7, 70))
        dec = paper.scan_frame(base[base["date"] <= base["date"].unique()[70]], DATA, validation=VALIDATED,
                               market="US")["decisions"][0]
        earlier = {"type": "OUTCOME", "decision_id": dec["decision_id"], "record_hash": "a" * 64, "status": "UNSCORABLE"}
        ran = gframe(spike=(7, 70), tail=0.03, gap=0.01)
        appended = []
        with mock.patch.object(paper, "ledger_lines", return_value=[dec, earlier]), \
                mock.patch.object(paper, "load_recent", return_value=(ran, {"manifest": "m", "manifest_sha256": "0"})), \
                mock.patch("idxsig.us_actions.yahoo_events", return_value=events()), \
                mock.patch.object(paper, "append", side_effect=lambda recs, timestamper=None:
                                  appended.extend(recs) or [{**r, "record_hash": "b" * 64} for r in recs]):
            _, none = paper.score_pending(paper.Path("m.jsonl"), market="US")
            self.assertEqual(none, [])  # already has an outcome: not scored again unasked
            _, outs = paper.score_pending(paper.Path("m.jsonl"), market="US", rescore={dec["decision_id"]: "evidence found"})
        self.assertEqual(len(outs), 1)
        self.assertEqual(outs[0]["revises"], "a" * 64)
        self.assertEqual(outs[0]["revision_reason"], "evidence found")
        self.assertEqual(outs[0]["status"], "SCORED")
        self.assertEqual(outs[0]["scorer"], paper.SCORER_ID)
        self.assertEqual(outs[0]["preprocessing"], "causal-close-v2")


if __name__ == "__main__":
    unittest.main()
