"""Corporate-action registry (audit v2, section 5). Synthetic markets only.

Each test names the failure it guards against."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from idxsig import corporate_actions as ca
from idxsig.execution import STATUS, ExecConfig, execute
from idxsig.panel import _reference_ignored_dates
from tests.support import flat_market, rebuild

FLAT_NET = (1 - 0.0025) / (1 + 0.0015) - 1
BOUNDARY = "2024-12-31"  # every synthetic session (Jan 2024) is in the exchange-data era


def reset_market(ratio, at=5, price=1000.0, share_ratio=None, share_lag=0):
    """Ticker 0's reference resets by `ratio` at session `at` (price / ratio from then on);
    its listed share count moves by `share_ratio` `share_lag` sessions later."""
    t, d, a = flat_market(price=price)
    a["listed_shares"] = np.full(a["close"].shape, 1e9)
    for k in ("close", "high", "low", "prev"):
        a[k][0, at:] = a[k][0, at:] / ratio
    a["volume"][0, at:] *= ratio
    if share_ratio is not None:
        a["listed_shares"][0, at + share_lag:] *= share_ratio
    return rebuild(t, d, a)


def yahoo(ticker, day, ratio):
    return pd.DataFrame([{"ticker": ticker, "effective_date": day, "yahoo_ratio": ratio, "yahoo_text": f"{ratio}:1",
                          "yahoo_downloaded_at": "2026-10-07T18:20:39Z"}])


def registry(m, events=None, manual=None, boundary=BOUNDARY):
    return ca.classify(m, boundary, ca.empty_events() if events is None else events,
                       pd.DataFrame(columns=ca.MANUAL_COLUMNS) if manual is None else manual, "2026-10-07T18:07:44Z")


def trade(m, ca_mode="registry"):
    out = execute(m, np.array([0]), np.array([2]), ExecConfig(holding_days=4, ca_mode=ca_mode))  # held 3 -> 7
    return {k: v[0] for k, v in out.items()}


class ShareScalingActions(unittest.TestCase):
    def test_split_preserves_value(self):
        """Guards against: a verified 1:2 split read as a 50% loss, or scaled by a wrong ratio."""
        m = reset_market(2.0, share_ratio=2.0)
        reg = registry(m)
        self.assertEqual(reg.loc[0, ["action_type", "verification_status"]].tolist(), ["STOCK_SPLIT", "VERIFIED_CORROBORATED"])
        r = trade(m.with_registry(reg))
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertAlmostEqual(r["share_factor"], 2.0)
        self.assertAlmostEqual(r["net_return"], FLAT_NET)

    def test_reverse_split_preserves_value(self):
        """Guards against: a 5:1 consolidation read as a 400% gain."""
        m = reset_market(0.2, share_ratio=0.2)
        reg = registry(m)
        self.assertEqual(reg.loc[0, ["action_type", "verification_status"]].tolist(), ["REVERSE_SPLIT", "VERIFIED_CORROBORATED"])
        r = trade(m.with_registry(reg))
        self.assertAlmostEqual(r["share_factor"], 0.2)
        self.assertAlmostEqual(r["net_return"], FLAT_NET)

    def test_lagged_register_update_needs_a_second_source(self):
        """Guards against: a late share-count change of the right size (e.g. warrants, a placement)
        being taken alone as proof of a split."""
        m = reset_market(2.0, share_ratio=2.0, share_lag=8)
        alone = registry(m)
        self.assertEqual(alone.loc[0, "verification_status"], "UNRESOLVED")
        both = registry(m, events=yahoo("T000", str(m.dates[5]), 2.0))
        self.assertEqual(both.loc[0, ["action_type", "verification_status"]].tolist(), ["STOCK_SPLIT", "VERIFIED_CORROBORATED"])
        self.assertEqual(both.loc[0, "listed_shares_lag"], 8)

    def test_declared_ratio_is_applied_not_the_snapped_reset(self):
        """Guards against: a 511:500 stock dividend scaled by a nearby simple fraction (up to 1% off)."""
        m = reset_market(1.022, share_ratio=1.022)
        reg = registry(m, events=yahoo("T000", str(m.dates[5]), 1.022))
        self.assertEqual(reg.loc[0, "action_type"], "STOCK_DIVIDEND")
        self.assertAlmostEqual(reg.loc[0, "ratio"], 1.022)


class NonScalingActions(unittest.TestCase):
    def test_rights_issue_is_not_a_free_split(self):
        """Guards against: a rights issue (reference 1200 -> 1000, new shares paid for and listed
        later) crediting holders with 20% free shares."""
        m = reset_market(1.2, price=1200.0, share_ratio=1.5, share_lag=10)
        reg = registry(m)
        self.assertEqual(reg.loc[0, ["action_type", "verification_status"]].tolist(),
                         ["OTHER_REFERENCE_RESET", "UNRESOLVED"])
        r = trade(m.with_registry(reg))
        self.assertEqual(STATUS[r["status"]], "CORP_ACTION_UNRESOLVED")
        self.assertTrue(np.isnan(r["net_return"]))
        self.assertAlmostEqual(trade(m, ca_mode="value_preserving")["net_return"], FLAT_NET)  # the old free-share credit
        primary = pd.DataFrame([{"ticker": "T000", "effective_date": str(m.dates[5]), "action_type": "RIGHTS_ISSUE",
                                 "ratio": "", "source": "https://www.idx.co.id/example", "source_timestamp":
                                 "2026-10-07T00:00:00Z", "notes": ""}])
        reg = registry(m, manual=primary)
        self.assertEqual(reg.loc[0, ["action_type", "verification_status"]].tolist(), ["RIGHTS_ISSUE", "VERIFIED_PRIMARY"])
        self.assertEqual(STATUS[trade(m.with_registry(reg))["status"]], "CORP_ACTION_RIGHTS_ISSUE")

    def test_integer_reset_without_share_change_is_unknown(self):
        """Guards against: the old rule that every integer reset is a split. A 2x reset whose share
        count never moves is flagged, even when Yahoo calls it a split."""
        m = reset_market(2.0)
        for events in (None, yahoo("T000", str(m.dates[5]), 2.0)):
            reg = registry(m, events=events)
            self.assertEqual(reg.loc[0, ["action_type", "verification_status"]].tolist(), ["UNKNOWN", "UNRESOLVED"])
            self.assertEqual(STATUS[trade(m.with_registry(reg))["status"]], "CORP_ACTION_UNRESOLVED")
        self.assertEqual(STATUS[trade(m, ca_mode="exclude")["status"]], "EXITED")  # the old reading, kept for old runs

    def test_single_source_reset_after_the_mirror_is_not_applied(self):
        """Guards against: Yahoo-era resets (derived from Yahoo's own split events) treated as verified."""
        m = reset_market(2.0)
        reg = registry(m, events=yahoo("T000", str(m.dates[5]), 2.0), boundary="2023-12-31")
        self.assertEqual(reg.loc[0, "verification_status"], "UNVERIFIED_SINGLE_SOURCE")
        self.assertEqual(STATUS[trade(m.with_registry(reg))["status"]], "CORP_ACTION_UNRESOLVED")

    def test_reset_missing_from_the_registry_is_unresolved(self):
        """Guards against: a registry built from other data silently treating an unexplained reset as no event."""
        m = reset_market(2.0, share_ratio=2.0)
        empty = pd.DataFrame(columns=ca.COLUMNS)
        mm = m.with_registry(empty)
        self.assertEqual(mm.registry_counts["missing_from_registry"], 1)
        self.assertEqual(STATUS[trade(mm)["status"]], "CORP_ACTION_UNRESOLVED")

    def test_yahoo_event_without_a_reset_is_not_applied(self):
        """Guards against: scaling shares on a Yahoo split the exchange prices do not show."""
        m = reset_market(1.0)
        reg = registry(m, events=yahoo("T001", str(m.dates[5]), 2.0))
        self.assertEqual(reg["verification_status"].tolist(), ["NO_PRICE_RESET"])
        self.assertEqual(m.with_registry(reg).registry_counts["share_scaled"], 0)

    def test_registry_mode_refuses_a_market_without_a_registry(self):
        """Guards against: running the default mode with no registry and silently scaling nothing."""
        with self.assertRaisesRegex(ValueError, "needs a market with a corporate-action registry"):
            trade(reset_market(2.0, share_ratio=2.0))


class RegistryFiles(unittest.TestCase):
    def test_manual_entries_need_a_primary_source(self):
        """Guards against: a manual override with no URL or time, or an invented action type."""
        header = ",".join(ca.MANUAL_COLUMNS)
        cases = {
            "T000,2024-01-09,STOCK_SPLIT,2,,2026-10-07T00:00:00Z,": "primary source URL",
            "T000,2024-01-09,STOCK_SPLIT,2,https://idx.co.id/x,,": "primary source URL",
            "T000,2024-01-09,FREE_MONEY,2,https://idx.co.id/x,2026-10-07T00:00:00Z,": "unknown action_type",
            "T000,2024-01-09,STOCK_SPLIT,,https://idx.co.id/x,2026-10-07T00:00:00Z,": "needs its ratio",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manual.csv"
            for line, message in cases.items():
                path.write_text(f"# comment\n{header}\n{line}\n")
                with self.assertRaisesRegex(ValueError, message):
                    ca.read_manual(path)
            path.write_text(f"{header}\nT000,2024-01-09,STOCK_SPLIT,2,https://idx.co.id/a#frag,2026-10-07T00:00:00Z,\n")
            self.assertEqual(ca.read_manual(path).loc[0, "source"], "https://idx.co.id/a#frag")

    def test_committed_manual_file_has_no_invented_entries(self):
        """Guards against: primary-source rows added without archived documents."""
        self.assertEqual(len(ca.read_manual()), 0)

    def test_registry_for_another_panel_is_refused(self):
        """Guards against: running with a registry whose resets were read from different prices."""
        with self.assertRaisesRegex(ca.RegistryMismatch, "was built for panel"):
            ca.load(panel_sha256="0" * 64)


class SessionCalendar(unittest.TestCase):
    def test_date_the_exchange_reference_ignores_is_not_a_session(self):
        """Guards against: a stub date (the mirror's Saturday 2021-05-22) whose closes IDX's next
        reference ignores, which turns every name traded that day into a false corporate action."""
        rows = []
        for i in range(10):
            closes = {"2021-05-20": 100, "2021-05-21": 110, "2021-05-22": 120, "2021-05-24": 115, "2021-05-25": 116}
            prev = 100
            for day, close in closes.items():
                rows.append({"ticker": f"T{i}", "date": pd.Timestamp(day), "previous": prev, "close": close, "volume": 10})
                prev = close if day != "2021-05-22" else prev  # IDX prices 05-24 off 05-21
        bad = _reference_ignored_dates(pd.DataFrame(rows))
        self.assertEqual(list(bad), ["2021-05-22"])


if __name__ == "__main__":
    unittest.main()
