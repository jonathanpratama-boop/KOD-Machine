"""Causal preparation and cost contracts; no downloaded market outcomes."""

from decimal import Decimal
from pathlib import Path

import unittest

from idxsig.timing_context import (
    account_cost_profile,
    build_timing_context,
    calendar_board,
    context_fixture,
    premove_shadow_decision,
    prepare_event,
    shadow_executability,
    validate_avoid_observation,
    validate_calendar_event,
    validate_cost_profile,
)
from idxsig.runtime.storage import digest


AT = "2026-11-04T00:30:00Z"


def event():
    return {
        "schema_version": "KOD_CATALYST_CALENDAR_V1",
        "id": "synthetic:event:1",
        "version": 1,
        "supersedes": None,
        "family": "EARNINGS",
        "instrument_id": "SYNTHETIC_SPOT:AAA",
        "time_precision": "EXACT",
        "event_at": "2026-11-04T01:00:00Z",
        "window_end": None,
        "source_timezone": "UTC",
        "published_at": "2026-11-03T12:00:00Z",
        "received_at": "2026-11-03T12:01:00Z",
        "evidence_id": "synthetic:evidence:1",
        "source_url": "synthetic://calendar-fixture",
        "evidence_kind": "synthetic",
        "status": "SCHEDULED",
    }


def profile():
    return account_cost_profile(
        {
            "id": "synthetic-account-v1",
            "venue": "SYNTHETIC_SPOT",
            "quote_currency": "USDT",
            "fee_rate": "0.01",
            "slippage": "0",
            "evidence_type": "synthetic",
        },
        as_of=AT,
    )


def decision():
    return {
        "id": "synthetic:decision:1",
        "decision_at": "2026-11-04T00:25:00Z",
        "available_at": "2026-11-04T00:25:01Z",
        "expires_at": "2026-11-04T00:31:00Z",
        "symbol": "AAA",
        "venue": "SYNTHETIC_SPOT",
    }


def quote():
    return {
        "symbol": "AAA",
        "venue": "SYNTHETIC_SPOT",
        "evidence_id": "synthetic:quote:1",
        "received_at": "2026-11-04T00:29:59Z",
        "source_time": None,
        "request_started_at": "2026-11-04T00:29:58Z",
        "bid": "100",
        "ask": "101",
        "bid_size": "10",
        "ask_size": "10",
    }


class TimingContextTests(unittest.TestCase):
    def test_calendar_normalizes_offset_without_changing_source_timezone(self):
        e = event()
        e["event_at"] = "2026-11-04T08:00:00+07:00"
        e["source_timezone"] = "Asia/Jakarta"
        result = validate_calendar_event(e, as_of=AT)
        assert result["event_at"] == "2026-11-04T01:00:00Z"
        assert result["source_timezone"] == "Asia/Jakarta"
        assert e["event_at"].endswith("+07:00")

    def test_calendar_rejects_future_source_and_naive_event_times(self):
        e = event()
        e["received_at"] = "2026-11-04T00:31:00Z"
        with self.assertRaisesRegex(ValueError, "future"):
            validate_calendar_event(e, as_of=AT)
        e = event()
        e["event_at"] = "2026-11-04T01:00:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            validate_calendar_event(e, as_of=AT)

    def test_unknown_calendar_time_never_becomes_due(self):
        e = event()
        e.update(time_precision="UNKNOWN", event_at=None)
        result = calendar_board([e], as_of=AT)
        assert result["events"][0]["timing_state"] == "UNKNOWN_TIME"
        assert result["due_count"] == 0

    def test_calendar_rejects_ambiguous_window_and_conflicting_revision(self):
        e = event()
        e.update(time_precision="WINDOW", window_end="2026-11-04T00:50:00Z")
        with self.assertRaisesRegex(ValueError, "window"):
            validate_calendar_event(e, as_of=AT)
        a, b = event(), event()
        b["event_at"] = "2026-11-04T02:00:00Z"
        with self.assertRaisesRegex(ValueError, "conflict"):
            calendar_board([a, b], as_of=AT)

    def test_prepared_branches_must_precede_event_and_use_research_actions(self):
        branches = [
            {
                "id": "upside",
                "condition": "result exceeds stated expectation",
                "mechanism": "repricing hypothesis",
                "action": "RESEARCH",
            }
        ]
        result = prepare_event(event(), branches, prepared_at=AT)
        assert result["entry_permission"] is False
        with self.assertRaisesRegex(ValueError, "before"):
            prepare_event(event(), branches, prepared_at="2026-11-04T01:00:00Z")
        branches[0]["action"] = "BUY"
        with self.assertRaisesRegex(ValueError, "research"):
            prepare_event(event(), branches, prepared_at=AT)

    def test_cost_profile_is_versioned_and_does_not_rewrite_account(self):
        result = profile()
        assert result["legacy_profile_id"] == "synthetic-account-v1"
        assert result["buy_fee_fraction"] == "0.01"
        assert result["verification_status"] == "SIMULATION_ASSUMPTION"
        assert result["spread_convention"] == "OBSERVED_BID_ASK"

    def test_cost_profile_rejects_future_expired_and_bad_fractions(self):
        p = profile()
        with self.assertRaisesRegex(ValueError, "future|effective"):
            validate_cost_profile(p, as_of="2026-11-04T00:29:00Z")
        p["valid_from"] = "2026-11-04T00:29:00Z"
        p["valid_until"] = AT
        with self.assertRaisesRegex(ValueError, "expired"):
            validate_cost_profile(p, as_of=AT)
        p = profile()
        p["buy_fee_fraction"] = True
        with self.assertRaisesRegex(ValueError, "number"):
            validate_cost_profile(p, as_of=AT)

    def test_missing_quote_is_unknown_not_zero_or_executable(self):
        r = shadow_executability(decision(), None, profile(), as_of=AT)
        assert r["status"] == "UNKNOWN"
        assert r["spread_fraction"] is None
        assert not r["entry_permission"]

    def test_post_availability_quote_checks_and_price_units(self):
        q = quote()
        r = shadow_executability(
            decision(), q, profile(), as_of=AT, requested_quantity="2"
        )
        assert r["status"] == "OBSERVED"
        assert r["fill_at"] is None
        assert r["depth_scope"] == "TOP_OF_BOOK_ONLY"
        assert r["capacity_status"] == "DISPLAYED_SIZE_SUFFICIENT"
        assert Decimal(r["spread_fraction"]) == Decimal(1) / Decimal("100.5")
        # Entry at ask including buy fee; exit at bid less sell fee. Spread counted once.
        assert (
            Decimal(r["instant_round_trip_return"])
            == Decimal(100) * Decimal("0.99") / (Decimal(101) * Decimal("1.01")) - 1
        )

    def test_old_label_open_cannot_be_reconstructed_as_a_fill(self):
        q = quote()
        q["received_at"] = "2026-11-04T00:00:00Z"
        q["request_started_at"] = "2026-11-03T23:59:59Z"
        r = shadow_executability(decision(), q, profile(), as_of=AT)
        assert r["status"] == "REJECTED"
        assert "QUOTE_PRECEDES_AVAILABILITY" in r["reasons"]
        assert r["fill_at"] is None

    def test_quote_requested_before_decision_is_not_postdecision_evidence(self):
        q = quote()
        q["request_started_at"] = "2026-11-04T00:24:00Z"
        r = shadow_executability(decision(), q, profile(), as_of=AT)
        assert "REQUEST_PRECEDES_AVAILABILITY" in r["reasons"]

    def test_proxy_does_not_prove_owner_venue_executability(self):
        r = shadow_executability(
            decision(), quote(), profile(), as_of=AT, owner_venue="ETORO"
        )
        assert r["status"] == "PROXY_ONLY"
        assert r["owner_venue_executable"] is False
        assert r["cost_scope"] == "QUOTE_VENUE_ONLY"

    def test_expired_stale_crossed_future_and_wrong_symbol_are_rejected(self):
        for changes, reason in [
            (
                {"received_at": "2026-11-04T00:26:00Z", "request_started_at": None},
                "STALE_QUOTE",
            ),
            ({"bid": "102"}, "CROSSED_QUOTE"),
            ({"received_at": "2026-11-04T00:31:00Z"}, "FUTURE_QUOTE"),
            ({"symbol": "BBB"}, "INSTRUMENT_MISMATCH"),
        ]:
            q = quote()
            q.update(changes)
            result = shadow_executability(decision(), q, profile(), as_of=AT)
            assert result["status"] == "REJECTED"
            assert reason in result["reasons"]
        d = decision()
        d["expires_at"] = AT
        assert (
            shadow_executability(d, quote(), profile(), as_of=AT)["status"] == "EXPIRED"
        )

    def test_insufficient_displayed_size_blocks_whole_size_claim(self):
        result = shadow_executability(
            decision(), quote(), profile(), as_of=AT, requested_quantity="11"
        )
        assert result["status"] == "REJECTED"
        assert "INSUFFICIENT_DISPLAYED_SIZE" in result["reasons"]

    def test_zero_displayed_ask_size_is_not_an_executable_quote(self):
        q = quote()
        q["ask_size"] = "0"
        result = shadow_executability(decision(), q, profile(), as_of=AT)
        assert result["status"] == "REJECTED"
        assert result["executable_at"] is None
        assert "NO_DISPLAYED_ASK_LIQUIDITY" in result["reasons"]

    def test_unknown_slippage_and_fx_remain_unknown(self):
        p = profile()
        p["buy_slippage_fraction"] = None
        result = shadow_executability(decision(), quote(), p, as_of=AT)
        assert result["instant_round_trip_return"] is None
        assert "buy_slippage_fraction" in result["unknown_costs"]
        assert result["fx_cost_fraction"] is None

    def test_avoid_flags_are_observations_not_vetoes(self):
        record = {
            "schema_version": "KOD_AVOID_OBSERVATION_V1",
            "id": "synthetic:avoid:1",
            "decision_id": "synthetic:decision:1",
            "as_of": AT,
            "regime": {"label": "UNKNOWN", "evidence_id": None},
            "checks": {
                "lone_spike": {
                    "status": "PRESENT",
                    "evidence_id": "synthetic:evidence:1",
                    "available_at": AT,
                }
            },
        }
        result = validate_avoid_observation(record, as_of=AT)
        assert result["checks"]["share_issuance"]["status"] == "UNKNOWN"
        assert result["entry_permission"] is False
        assert result["veto"] is False
        record["checks"]["lone_spike"]["available_at"] = "2026-11-04T00:31:00Z"
        with self.assertRaisesRegex(ValueError, "future"):
            validate_avoid_observation(record, as_of=AT)

    def test_profile_files_are_valid_but_not_owner_verified(self):
        import json

        root = Path(__file__).resolve().parents[2]
        p = json.loads((root / "costs" / "etoro_crypto_2026.json").read_text())
        p = validate_cost_profile(p, as_of="2026-11-04T23:59:59Z")
        assert p["verification_status"] == "OWNER_REPORTED_ASSUMPTION"
        assert p["account_applicability"] == "UNKNOWN"
        assert p["buy_slippage_fraction"] is None

    def test_calendar_revision_supersedes_without_mutating_old_event(self):
        old = event()
        revision = event()
        revision.update(
            version=2, supersedes=old["id"] + ":v1", event_at="2026-11-04T02:00:00Z"
        )
        result = calendar_board([old, revision], as_of=AT)
        assert result["events"][0]["version"] == 2
        assert old["event_at"] == "2026-11-04T01:00:00Z"
        revision["supersedes"] = "another-event:v1"
        with self.assertRaisesRegex(ValueError, "previous"):
            calendar_board([old, revision], as_of=AT)

    def test_quote_venue_cost_mismatch_never_calculates_owner_return(self):
        p = profile()
        p["venue"] = "ETORO"
        result = shadow_executability(decision(), quote(), p, as_of=AT)
        assert result["status"] == "REJECTED"
        assert result["instant_round_trip_return"] is None
        assert "COST_VENUE_MISMATCH" in result["reasons"]

    def test_source_clock_conflict_is_rejected(self):
        q = quote()
        q["source_time"] = "2026-11-04T00:30:01Z"
        result = shadow_executability(decision(), q, profile(), as_of=AT)
        assert result["status"] == "REJECTED"
        assert "SOURCE_CLOCK_CONFLICT" in result["reasons"]

    def test_later_receipt_cannot_make_predecision_source_quote_executable(self):
        q = quote()
        q.update(
            source_time="2026-11-04T00:25:00Z",
            received_at="2026-11-04T00:25:02Z",
            request_started_at="2026-11-04T00:25:01Z",
        )
        p = profile()
        p["valid_from"] = "2026-11-04T00:00:00Z"
        result = shadow_executability(decision(), q, p, as_of="2026-11-04T00:25:03Z")
        assert result["status"] == "REJECTED"
        assert "QUOTE_SOURCE_PRECEDES_AVAILABILITY" in result["reasons"]
        assert "STALE_SOURCE_QUOTE" not in result["reasons"]

    def test_synthetic_context_runs_every_adapter_without_entry_permission(self):
        pack = context_fixture()
        result = build_timing_context(pack, as_of=pack["as_of"])
        assert result["calendar"]["due_count"] == 1
        assert len(result["preparations"]) == 1
        assert [x["status"] for x in result["shadow"]] == ["PROXY_ONLY", "REJECTED"]
        assert result["avoid"][0]["checks"]["lone_spike"]["status"] == "UNKNOWN"
        assert result["entry_permission"] is False
        assert result == build_timing_context(pack, as_of=pack["as_of"])

    def test_context_rejects_wrong_containers_and_cutoff(self):
        for key in (
            "calendar_events",
            "preparations",
            "avoid_observations",
            "shadow_checks",
        ):
            pack = context_fixture()
            pack[key] = {}
            with self.assertRaisesRegex(ValueError, "list"):
                build_timing_context(pack, as_of=pack["as_of"])
        with self.assertRaisesRegex(ValueError, "cutoff"):
            build_timing_context(context_fixture(), as_of="2026-11-04T00:31:00Z")

    def test_premove_adapter_preserves_label_and_uses_retained_availability(self):
        forecast = {
            "type": "PREMOVE_SHADOW_FORECAST",
            "trial": "PREMOVE_SHADOW_v1",
            "made_at": "2026-11-04T00:25:00Z",
            "entry": "open of 2026-11-04 UTC (label reference only)",
            "candidates": {"AAA": {}},
            "prev_hash": None,
        }
        forecast["record_hash"] = digest(forecast)
        result = premove_shadow_decision(
            forecast,
            "AAA",
            observed_at="2026-11-04T00:25:05Z",
            sealed_at="2026-11-04T00:25:03Z",
            availability_evidence_id="synthetic:forecast-receipt",
            expires_at="2026-11-04T00:31:00Z",
            venue="SYNTHETIC_SPOT",
        )
        assert result["available_at"] == "2026-11-04T00:25:05Z"
        assert result["original_label_reference"] == forecast["entry"]
        assert result["forecast_record_hash"] == forecast["record_hash"]
        q = quote()
        q.update(received_at="2026-11-04T00:00:00Z", request_started_at=None)
        assert (
            shadow_executability(result, q, profile(), as_of=AT)["status"] == "REJECTED"
        )
        with self.assertRaisesRegex(ValueError, "seal"):
            premove_shadow_decision(
                forecast,
                "AAA",
                observed_at="2026-11-04T00:25:01Z",
                sealed_at="2026-11-04T00:25:03Z",
                availability_evidence_id="synthetic:receipt",
                expires_at="2026-11-04T00:31:00Z",
            )
        forecast["made_at"] = "2026-11-04T00:20:00Z"
        with self.assertRaisesRegex(ValueError, "hash"):
            premove_shadow_decision(
                forecast,
                "AAA",
                observed_at=AT,
                availability_evidence_id="synthetic:receipt",
                expires_at="2026-11-04T00:31:00Z",
            )

    def test_currency_mismatch_blocks_economic_result(self):
        q = quote()
        q["quote_currency"] = "USD"
        result = shadow_executability(decision(), q, profile(), as_of=AT)
        assert result["status"] == "REJECTED"
        assert result["instant_round_trip_return"] is None
        assert "COST_CURRENCY_MISMATCH" in result["reasons"]
