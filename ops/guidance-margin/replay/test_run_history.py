from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_history as replay


class ReplayTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.out = self.root / "extract"
        self.label = replay.PREFIX + "example"
        self.state = {
            "model": replay.MODEL,
            "credit_budget_usd": 55,
            "prior_estimated_usd": 0.47,
            "api_calls": 0,
            "api_estimated_usd": 0,
            "credit_expiry_at": "2099-12-03T13:41:10+00:00",
        }
        replay.feed.write_json(self.root / "feed_state.json", self.state)

    def test_reservation_and_finished_replay_are_idempotent(self):
        def execute():
            self.assertEqual(
                replay.read(self.root / "feed_state.json")["api_reservations"][
                    self.label
                ]["status"],
                "UNSETTLED",
            )
            self.out.mkdir()
            result = {
                "status": "OK",
                "usage": {"input_tokens": 1000, "output_tokens": 100},
                "provider_calls": 1,
            }
            replay.feed.write_json(self.out / "result.json", result)
            return result

        a = replay.call(self.root, self.label, 300, self.out, execute)
        b = replay.call(
            self.root, self.label, 300, self.out, lambda: self.fail("repeat paid call")
        )
        self.assertEqual(a, b)
        self.assertEqual(replay.read(self.root / "feed_state.json")["api_calls"], 1)

    def test_unknown_call_stays_reserved(self):
        with self.assertRaises(ConnectionError):
            replay.call(
                self.root,
                self.label,
                10,
                self.out,
                lambda: (_ for _ in ()).throw(ConnectionError()),
            )
        with self.assertRaisesRegex(RuntimeError, "Indeterminate"):
            replay.call(
                self.root,
                self.label,
                10,
                self.out,
                lambda: self.fail("repeat paid call"),
            )

    def test_subbudget_and_shared_allowance(self):
        with patch.object(replay, "SUBBUDGET", 0):
            with self.assertRaisesRegex(RuntimeError, "subbudget"):
                replay.call(
                    self.root, self.label, 40, self.out, lambda: self.fail("paid")
                )
        self.state["credit_budget_usd"] = 0.48
        replay.feed.write_json(self.root / "feed_state.json", self.state)
        with self.assertRaisesRegex(RuntimeError, "BUDGET"):
            replay.call(self.root, self.label, 40, self.out, lambda: self.fail("paid"))

    def test_only_prior_needs_the_same_wire_account_in_corrected_replay(self):
        current = dict(
            id="current",
            url="s3",
            wire_account="issuer",
            published_at="2025-08-01T12:00:00Z",
            text="current",
        )
        agency = dict(
            id="agency",
            url="s2",
            wire_account="agency",
            published_at="2025-07-01T12:00:00Z",
            text="third party",
        )
        prior = dict(
            id="prior",
            url="s1",
            wire_account="issuer",
            published_at="2025-05-01T12:00:00Z",
            text="prior",
        )
        by_url = {d["url"]: d for d in (current, agency, prior)}
        item = dict(url="s3", index=0, cik="42")
        archive = {"links": [{"url": url} for url in by_url]}
        with (
            patch.object(replay, "getdoc", side_effect=lambda _, url: by_url[url]),
            patch.object(replay.feed, "screen", return_value=True),
            patch.object(replay.feed, "as_packet_source", side_effect=lambda doc: doc),
        ):
            with self.assertRaisesRegex(ValueError, "Intervening issuer mismatch"):
                replay.prepare(self.root, item, archive)
            packet, inventory = replay.prepare(
                self.root, item, archive, require_matching_intermediates=False
            )
            self.assertEqual(packet["prior"]["source"]["id"], "prior")
            self.assertEqual(
                [d["url"] for d in inventory["intervening_source_texts"]], ["s2"]
            )

    def test_seal_rejects_modified_decisions(self):
        f = self.root / "row.json"
        a = replay.seal(f, {"decision": "cash"})
        self.assertEqual(a, replay.seal(f, {"decision": "cash"}))
        with self.assertRaisesRegex(ValueError, "differs"):
            replay.seal(f, {"decision": "buy"})


if __name__ == "__main__":
    unittest.main()
