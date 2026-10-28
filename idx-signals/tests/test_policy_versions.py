"""Paper policy identities after PR #3 (drafted as v4, now v5) met PR #6 (v4 on the base branch).
Each test names the failure it guards against."""

import unittest
from unittest import mock

from idxsig import paper
from tests.test_paper import DATA, VALIDATED, frame

# The hashes the ledger and PR #6 recorded. A change here breaks verification of recorded decisions.
V3_SHA = "fdc5b488d3fde02003f6968adafbab1015dc5c7ea753f50d09a47076261f1077"
V4_SHA = "86ff27d305c6aae11556438b51b2cd0fa6a3fd8c8187181734a34d014cd769fd"


class Versions(unittest.TestCase):
    def test_recorded_policies_keep_their_hashes(self):
        """Guards against: the merge silently adding PR #6's E3 field to the v3 record (git merged that
        line without a conflict), which changes v3's hash and orphans the 81 recorded v3 decisions."""
        self.assertEqual(paper.policy_sha(paper.POLICY_ID_V3), V3_SHA)
        self.assertEqual(paper.policy_sha(paper.POLICY_ID_V4), V4_SHA)
        self.assertNotIn("e3_plan_rule", paper.policy_record(paper.POLICY_ID_V3))

    def test_one_name_per_policy(self):
        """Guards against: two different policies recorded under one id."""
        self.assertEqual((paper.POLICY_ID_V3, paper.POLICY_ID_V4, paper.POLICY_ID_V5),
                         ("PAPER-POLICY-v3", "PAPER-POLICY-v4", "PAPER-POLICY-v5"))
        self.assertEqual(paper.POLICY_ID, paper.POLICY_ID_V4)  # v5 defined, not in force (owner, 2026-10-28)
        self.assertEqual(len({paper.policy_sha(p) for p in paper.POLICIES}), 3)

    def test_v5_does_not_decide_idx_while_an_e3_pair_is_validated(self):
        """Guards against: v5 deciding with the E3 detector but its own 5% band, a plan nobody validated."""
        e3 = {"detector": "F1_ARA", "run_id": "t-e3",
              "plan": {"entry_rule": "confirm", "entry_window": 3, "exit_rule": "stop_ref", "holding_days": 3}}
        with mock.patch.object(paper, "e3_plan", lambda: e3):
            with self.assertRaises(RuntimeError):
                paper.scan_frame(frame(spike=(7, 79)), DATA, validation=VALIDATED, policy=paper.POLICY_ID_V5)
            v3 = paper.scan_frame(frame(spike=(7, 79)), DATA, validation=VALIDATED, policy=paper.POLICY_ID_V3)
        self.assertEqual(v3["scan"]["detector"]["rule_id"], "MOONSHOT_E1_D1")


if __name__ == "__main__":
    unittest.main()
