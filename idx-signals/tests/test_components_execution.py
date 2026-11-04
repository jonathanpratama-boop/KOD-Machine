"""Recorded execution must conserve cash and inventory across lifecycle failures."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from idxsig.components.execution import ReplayExecutor, VERSION, execution_run


def profile(**changes):
    return dict(
        schema_version=VERSION,
        simulation_only=True,
        evidence_type="synthetic",
        id="simulation-1",
        initial_cash="1000",
        fee_rate="0.01",
        quote_currency="USDT",
        symbols=["BTCUSDT"],
        **changes,
    )


def submit(order="a", **changes):
    value = dict(
        event_id=f"submit-{order}",
        kind="submit",
        at="2026-11-01T00:00:00Z",
        order_id=order,
        symbol="BTCUSDT",
        side="BUY",
        quantity="5",
        limit_price="100",
        expires_at="2026-11-01T00:10:00Z",
    )
    value.update(changes)
    return value


def fill(identity="f1", **changes):
    value = dict(
        event_id=f"event-{identity}",
        kind="fill",
        at="2026-11-01T00:01:00Z",
        order_id="a",
        fill_id=identity,
        quantity="2",
        price="99",
        evidence_id=f"quote-{identity}",
        observed_at="2026-11-01T00:00:59Z",
    )
    value.update(changes)
    return value


def lifecycle(kind, **changes):
    value = dict(
        event_id=kind,
        kind=kind,
        at="2026-11-01T00:02:00Z",
        order_id="a",
        reason="recorded simulation",
    )
    value.update(changes)
    return value


class Execution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "executor"
        self.executor = ReplayExecutor(self.root, profile())

    def assert_rejected_without_change(self, event, pattern):
        before = self.executor.snapshot()
        log = self.root / "events.jsonl"
        original = log.read_bytes() if log.exists() else None
        with self.assertRaisesRegex(ValueError, pattern):
            self.executor.apply(event)
        self.assertEqual(self.executor.snapshot(), before)
        self.assertEqual(log.read_bytes() if log.exists() else None, original)

    def test_partial_fills_conserve_cash_and_reservations(self):
        self.executor.apply(submit())
        part = self.executor.apply(fill())
        self.assertEqual(part["cash"], "800.02")
        self.assertEqual(part["cash_reserved"], "303.00")
        self.assertEqual(part["holdings"]["BTCUSDT"], "2")
        self.assertEqual(part["orders"]["a"]["status"], "PARTIAL")
        final = self.executor.apply(
            fill("f2", quantity="3", at="2026-11-01T00:02:00Z", observed_at="2026-11-01T00:01:59Z")
        )
        self.assertEqual(final["cash"], "500.05")
        self.assertEqual(final["cash_reserved"], "0")
        self.assertEqual(final["orders"]["a"]["fees"], "4.95")
        self.assertEqual(final["orders"]["a"]["status"], "FILLED")

    def test_restart_and_identical_delivery_do_not_duplicate_fills(self):
        self.executor.apply(submit())
        self.executor.apply(fill())
        original = (self.root / "events.jsonl").read_bytes()
        restarted = ReplayExecutor(self.root, profile())
        before = restarted.snapshot()
        self.assertEqual(restarted.apply(fill()), before)
        self.assertEqual((self.root / "events.jsonl").read_bytes(), original)
        self.assertTrue(restarted.verify()["ok"])

    def test_reused_event_identity_with_changed_content_fails(self):
        self.executor.apply(submit())
        self.assert_rejected_without_change(submit(quantity="6"), "conflicting event")

    def test_fill_identity_cannot_be_reused_through_another_event(self):
        self.executor.apply(submit())
        self.executor.apply(fill())
        self.assert_rejected_without_change(fill(event_id="different"), "duplicate fill")

    def test_cash_reservations_prevent_two_orders_spending_same_cash(self):
        self.executor.apply(submit())
        self.assert_rejected_without_change(submit("b"), "insufficient unreserved cash")

    def test_quantity_and_price_constraints(self):
        self.executor.apply(submit())
        for event, pattern in [
            (fill(quantity="6"), "exceeds remaining"),
            (fill(price="101"), "violates limit"),
            (fill(quantity="NaN"), "finite"),
            (fill(price=True), "finite"),
        ]:
            with self.subTest(event=event):
                self.assert_rejected_without_change(event, pattern)

    def test_fill_requires_future_observation_not_submission_quote(self):
        self.executor.apply(submit())
        self.assert_rejected_without_change(
            fill(observed_at="2026-11-01T00:00:00Z"), "later observation"
        )
        self.assert_rejected_without_change(
            fill(observed_at="2026-11-01T00:02:00Z"), "later observation"
        )
        self.assert_rejected_without_change(fill(at="2026-11-01T00:10:00Z"), "before expiry")

    def test_out_of_order_receipt_is_rejected(self):
        self.executor.apply(submit())
        self.executor.apply(fill())
        self.assert_rejected_without_change(
            lifecycle("cancel", at="2026-11-01T00:00:30Z"), "out-of-order"
        )

    def test_unknown_preserves_reservations_and_does_not_imply_a_fill(self):
        self.executor.apply(submit())
        value = self.executor.apply(lifecycle("unknown"))
        self.assertEqual(value["orders"]["a"]["status"], "UNKNOWN")
        self.assertEqual(value["cash_reserved"], "505.00")
        self.assertEqual(value["cash"], "1000")
        self.assertEqual(value["fills"], {})

    def test_reconciliation_never_invents_missing_economics(self):
        self.executor.apply(submit())
        self.executor.apply(lifecycle("unknown"))
        report = dict(
            event_id="report",
            kind="reconcile",
            at="2026-11-01T00:03:00Z",
            order_id="a",
            status="FILLED",
            filled_quantity="5",
            evidence_id="report-ref",
            observed_at="2026-11-01T00:02:59Z",
        )
        self.assert_rejected_without_change(report, "cannot invent")
        report.update(status="PENDING", filled_quantity="0")
        value = self.executor.apply(report)
        self.assertEqual(value["orders"]["a"]["status"], "PENDING")
        self.assertEqual(value["cash"], "1000")

    def test_cancel_partial_releases_only_remaining_reservations(self):
        self.executor.apply(submit())
        self.executor.apply(fill())
        value = self.executor.apply(lifecycle("cancel"))
        self.assertEqual(value["cash"], "800.02")
        self.assertEqual(value["cash_reserved"], "0")
        self.assertEqual(value["holdings"]["BTCUSDT"], "2")
        self.assert_rejected_without_change(
            fill("late", at="2026-11-01T00:03:00Z"), "inactive order"
        )

    def test_expiry_must_be_explicit_and_at_deadline_or_later(self):
        self.executor.apply(submit())
        self.assert_rejected_without_change(lifecycle("expire"), "before deadline")
        value = self.executor.apply(lifecycle("expire", at="2026-11-01T00:10:00Z"))
        self.assertEqual(value["orders"]["a"]["status"], "EXPIRED")
        self.assertEqual(value["cash_reserved"], "0")

    def test_rejection_after_partial_fill_is_invalid(self):
        self.executor.apply(submit())
        self.executor.apply(fill())
        self.assert_rejected_without_change(lifecycle("reject"), "partially filled")

    def test_sell_reservations_prevent_shorting(self):
        self.assert_rejected_without_change(submit(side="SELL"), "shorting forbidden")
        root = Path(self.temp.name) / "seller"
        seller = ReplayExecutor(root, profile(initial_holdings={"BTCUSDT": "5"}))
        seller.apply(submit(side="SELL"))
        with self.assertRaisesRegex(ValueError, "shorting forbidden"):
            seller.apply(submit("b", side="SELL", quantity="1"))
        value = seller.apply(fill(price="101"))
        self.assertEqual(value["cash"], "1199.98")
        self.assertEqual(value["holdings"]["BTCUSDT"], "3")

    def test_profile_is_immutable_and_live_mode_is_forbidden(self):
        changed = profile()
        changed["initial_cash"] = "2000"
        with self.assertRaisesRegex(ValueError, "immutable artifact"):
            ReplayExecutor(self.root, changed)
        for name, value in [("simulation_only", False), ("evidence_type", "prospective")]:
            changed = profile()
            changed[name] = value
            with self.assertRaises(ValueError):
                ReplayExecutor(Path(self.temp.name) / "bad", changed)

    def test_executor_refuses_legacy_root(self):
        root = Path(self.temp.name) / "legacy"
        root.mkdir()
        (root / "snapshot.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "separate directory"):
            ReplayExecutor(root, profile())

    def test_torn_and_tampered_journals_fail_closed(self):
        self.executor.apply(submit())
        path = self.root / "events.jsonl"
        raw = path.read_bytes()
        path.write_bytes(raw[:-1])
        with self.assertRaisesRegex(ValueError, "torn"):
            self.executor.snapshot()
        path.write_bytes(raw.replace(b'"quantity":"5"', b'"quantity":"9"'))
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.executor.snapshot()

    def test_finite_batch_can_be_retried(self):
        request = {"profile": profile(), "events": [submit(), fill()]}
        root = Path(self.temp.name) / "batch"
        first = execution_run(root, request)
        second = execution_run(root, copy.deepcopy(request))
        self.assertEqual(first, second)
        self.assertEqual(first["event_count"], 2)
        self.assertEqual(first["evidence_type"], "synthetic")

    def test_journal_rejects_duplicate_keys(self):
        self.executor.apply(submit())
        path = self.root / "events.jsonl"
        raw = path.read_text()
        path.write_text(raw.replace('"sequence":1', '"sequence":1,"sequence":1'))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.executor.verify()

    def test_removed_complete_tail_is_detected_by_checkpoint(self):
        self.executor.apply(submit())
        self.executor.apply(fill())
        path = self.root / "events.jsonl"
        path.write_bytes(path.read_bytes().splitlines(keepends=True)[0])
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.executor.verify()

    def test_missing_journal_cannot_reset_cash_or_holdings(self):
        self.executor.apply(submit())
        (self.root / "events.jsonl").unlink()
        with self.assertRaisesRegex(ValueError, "missing executor journal"):
            ReplayExecutor(self.root, profile())

    def test_uncheckpointed_durable_event_recovers_from_log(self):
        checkpoint = (self.root / "checkpoint.json").read_bytes()
        self.executor.apply(submit())
        expected = self.executor.snapshot()
        (self.root / "checkpoint.json").write_bytes(checkpoint)
        self.assertEqual(ReplayExecutor(self.root, profile()).snapshot(), expected)

    def test_malformed_event_is_explicitly_rejected(self):
        for value in (None, [], "fill"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "event object"):
                self.executor.apply(value)

    def test_symlink_journal_is_rejected(self):
        path = self.root / "events.jsonl"
        other = Path(self.temp.name) / "external.jsonl"
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            self.executor.snapshot()

    def test_decision_lineage_survives_restart_without_granting_live_authority(self):
        decision = {
            "plan_id": "plan-1",
            "input_sha256": "a" * 64,
            "strategy_id": "SMA_CROSS_SHADOW_V1",
            "strategy_version": "1",
            "scope": "SHADOW_SIMULATION",
        }
        self.executor.apply(submit(decision=decision))
        restarted = ReplayExecutor(self.root, profile())
        self.assertEqual(restarted.snapshot()["orders"]["a"]["decision"], decision)
        decision["scope"] = "LIVE"
        self.assert_rejected_without_change(
            submit("b", quantity="1", decision=decision), "shadow simulation"
        )

    def test_malformed_identifiers_fail_cleanly(self):
        for change in ({"event_id": []}, {"kind": []}, {"side": []}):
            with self.subTest(change=change):
                self.assert_rejected_without_change(submit(**change), "identifier")

    def test_unknown_instrument_cannot_use_account_cash(self):
        self.assert_rejected_without_change(submit(symbol="BTCUSD"), "instrument universe")
        with self.assertRaisesRegex(ValueError, "initial holding"):
            ReplayExecutor(
                Path(self.temp.name) / "foreign", profile(initial_holdings={"BTCUSD": "1"})
            )

    def test_stale_reconciliation_cannot_resolve_unknown_or_release_cash(self):
        self.executor.apply(submit())
        self.executor.apply(lifecycle("unknown"))
        report = dict(
            event_id="stale-report",
            kind="reconcile",
            at="2026-11-01T00:03:00Z",
            order_id="a",
            status="CANCELLED",
            filled_quantity="0",
            evidence_id="stale-order-report",
            observed_at="2026-11-01T00:01:00Z",
        )
        self.assert_rejected_without_change(report, "latest uncertainty")
        report["observed_at"] = "2026-11-01T00:02:00Z"
        self.assert_rejected_without_change(report, "latest uncertainty")
        self.assertEqual(self.executor.snapshot()["cash_reserved"], "505.00")
        report["observed_at"] = "2026-11-01T00:02:01Z"
        value = self.executor.apply(report)
        self.assertEqual(value["orders"]["a"]["status"], "CANCELLED")
        self.assertEqual(value["cash_reserved"], "0")

    def test_malformed_profile_evidence_type_is_explicit_error(self):
        malformed = profile()
        malformed["evidence_type"] = []
        with self.assertRaisesRegex(ValueError, "identifier"):
            ReplayExecutor(Path(self.temp.name) / "malformed", malformed)

    def test_retry_repairs_interrupted_checkpoint_before_acknowledgement(self):
        with patch("idxsig.components.execution.atomic_json", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                self.executor.apply(submit())
        checkpoint_path = self.root / "checkpoint.json"
        self.assertEqual(json.loads(checkpoint_path.read_text())["sequence"], 0)
        journal = self.root / "events.jsonl"
        self.assertEqual(len(journal.read_bytes().splitlines()), 1)
        restarted = ReplayExecutor(self.root, profile())
        result = restarted.apply(submit())
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(json.loads(checkpoint_path.read_text())["sequence"], 1)
        self.assertEqual(len(journal.read_bytes().splitlines()), 1)
        journal.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "truncated"):
            restarted.verify()


if __name__ == "__main__":
    unittest.main()
