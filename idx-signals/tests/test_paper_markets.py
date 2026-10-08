"""Prospective paper ledger on US equities and crypto (no orders). Synthetic bars, plus one
check against the committed E2 evidence. Each test names the failure it guards against."""

import unittest
import warnings

import numpy as np
import pandas as pd

from idxsig import paper

VALIDATED = {"precision": 0.05, "lift_vs_matched_random": 5.0, "p_one_sided_vs_matched": 0.005,
             "trading": {"p_one_sided": 0.01, "avg_net_return": 0.02, "matched_random_avg_net_return": 0.0, "run_id": "t"}}
DETECTION_ONLY = {**VALIDATED, "trading": {"p_one_sided": 1.0, "avg_net_return": -0.0365,
                                           "matched_random_avg_net_return": -0.006, "run_id": "t"}}


def gframe(n=60, s=80, spike=None, price=10.0, volume=500_000, tail=None, gap=0.0, crypto=False):
    """Random-walk names with opening prices; spike = (name, session) gets +35% and volume x10."""
    rng = np.random.default_rng(1)
    if crypto:
        dates = pd.date_range("2026-06-01", periods=s, freq="D")
    else:
        dates = pd.to_datetime(np.busday_offset(np.datetime64("2026-06-01", "D"), np.arange(s), roll="forward"))
    rows = []
    for i in range(n):
        p = float(price)
        for d in range(s):
            prev = p
            vol = volume * rng.uniform(0.8, 1.2)
            step, opening = rng.normal(0, 0.01), prev * (1 + rng.normal(0, 0.003))
            if spike and i == spike[0] and d == spike[1]:
                step, vol = 0.35, vol * 10
            if spike and tail is not None and i == spike[0] and d > spike[1]:
                step, opening = tail, prev * (1 + gap) if d == spike[1] + 1 else prev
            p = round(prev * (1 + step), 4)
            rows.append({"date": dates[d], "ticker": f"T{i:03d}", "source": "binance" if crypto else "yahoo",
                         "previous": prev, "open": round(opening, 4), "high": max(prev, p, opening),
                         "low": min(prev, p, opening), "close": p, "volume": vol, "value": vol * p,
                         "frequency": np.nan, "listed_shares": np.nan, "tradable_shares": np.nan})
    return pd.DataFrame(rows)


DATA = {"manifest": "synthetic", "manifest_sha256": "0" * 64, "http_status": {f"T{i:03d}": 200 for i in range(60)}}


class USPaper(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_no_signal_session_is_recorded_under_the_us_scan_id(self):
        out = paper.scan_frame(gframe(), DATA, market="US")
        self.assertEqual(out["scan"]["result"], "NO SIGNAL")
        self.assertEqual(out["scan"]["market"], "US")
        self.assertTrue(out["scan"]["scan_id"].startswith("SCAN-US-"))
        self.assertEqual(out["scan"]["detector"]["selected"], "G2_RET30")
        self.assertEqual(out["decisions"], [])

    def test_failed_trading_validation_gives_pass_with_a_full_plan(self):
        d = paper.scan_frame(gframe(spike=(7, 79)), DATA, validation=DETECTION_ONLY, market="US")["decisions"][0]
        self.assertEqual(d["decision"], "PASS")
        self.assertIn("buy at the next open", d["reason"])
        self.assertIn("opening print", d["plan"]["entry_trigger"])
        self.assertEqual(d["instrument"]["currency"], "USD")

    def test_us_sizing_stays_inside_the_risk_budget_in_whole_shares(self):
        d = paper.scan_frame(gframe(spike=(7, 79)), DATA, validation=VALIDATED, market="US")["decisions"][0]
        self.assertEqual(d["decision"], "BUY ON TRIGGER")
        for sc in d["plan"]["scenarios"]:
            self.assertEqual(sc["shares"], int(sc["shares"]))
            self.assertLessEqual(sc["max_planned_loss_usd"], sc["risk_budget_usd"] * 1.0001)
            self.assertLessEqual(sc["position_usd"], 0.2 * paper.POLICY.equity_usd + 1e-6)
        self.assertLess(d["plan"]["invalidation"], d["verified_price"]["close"] * 0.95 + 0.01)

    def test_us_outcome_enters_at_the_next_open_not_the_close(self):
        base = gframe(spike=(7, 70))
        dec = paper.scan_frame(base[base["date"] <= base["date"].unique()[70]], DATA, validation=VALIDATED,
                               market="US")["decisions"][0]
        ran = gframe(spike=(7, 70), tail=0.04, gap=0.02)
        out = paper.score(dec, paper._market(ran, "US"))
        trade = out["execution"]["paper_trade"]
        m = paper._market(ran, "US")
        n = list(m.tickers).index("T007")
        self.assertEqual(trade["entry_basis"], "open")
        self.assertAlmostEqual(trade["entry_price"], float(m.open[n, 71]))
        self.assertEqual(trade["exit_reason"], "horizon")
        self.assertEqual(trade["exit_session"], str(m.dates[76]))  # entry session + 5, as in the harness
        self.assertEqual(out["decision_verdict"], "PROFIT")


    def test_a_reverse_split_inside_the_window_does_not_change_the_outcome(self):
        """Guards against: the source rescaling a name's whole history after a reverse split, so
        the plan's stop and chase prices (decision-day units) are compared with prices 10x larger."""
        base = gframe(spike=(7, 70))
        dec = paper.scan_frame(base[base["date"] <= base["date"].unique()[70]], DATA, validation=VALIDATED,
                               market="US")["decisions"][0]
        ran = gframe(spike=(7, 70), tail=-0.03, gap=0.01)
        split = ran.copy()
        rows = split["ticker"] == "T007"
        for col in ("previous", "open", "high", "low", "close"):
            split.loc[rows, col] = split.loc[rows, col] * 10  # 1-for-10, applied to all history
        split.loc[rows, "volume"] = split.loc[rows, "volume"] / 10
        plain = paper.score(dec, paper._market(ran, "US"))
        scaled = paper.score(dec, paper._market(split, "US"))
        self.assertAlmostEqual(scaled["price_scale"], 10.0)
        self.assertIn("price_scale_note", scaled)
        self.assertEqual(scaled["decision_verdict"], plain["decision_verdict"])
        self.assertEqual(scaled["execution"]["paper_trade"]["exit_reason"],
                         plain["execution"]["paper_trade"]["exit_reason"])
        self.assertAlmostEqual(scaled["execution"]["paper_trade"]["net_return"],
                               plain["execution"]["paper_trade"]["net_return"], places=9)


class CryptoPaper(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_no_live_quote_means_not_executable(self):
        d = paper.scan_frame(gframe(spike=(3, 79), crypto=True, price=2.0), DATA, validation=VALIDATED,
                             market="CRYPTO")["decisions"][0]
        self.assertEqual(d["decision"], "NOT EXECUTABLE")
        self.assertIn("no live quote", d["reason"])

    def test_live_quote_is_the_verified_price_and_the_entry(self):
        df = gframe(spike=(3, 79), crypto=True, price=2.0)
        close = float(df[(df["ticker"] == "T003")]["close"].iloc[-1])
        quotes = lambda tickers: {t: (close * 1.02, "2026-08-19T00:23:00Z") for t in tickers}  # noqa: E731
        d = paper.scan_frame(df, DATA, validation=VALIDATED, market="CRYPTO", quotes=quotes)["decisions"][0]
        self.assertEqual(d["decision"], "BUY ON TRIGGER")
        self.assertAlmostEqual(d["verified_price"]["quote"], close * 1.02)
        self.assertIn("decision-time quote", d["plan"]["entry_trigger"])
        self.assertIsNone(d["plan"]["scenarios"][0]["lots"])  # fractional units
        for sc in d["plan"]["scenarios"]:
            self.assertLessEqual(sc["max_planned_loss_usdt"], sc["risk_budget_usdt"] * 1.0001)

    def test_quote_above_the_chase_limit_is_not_chased(self):
        df = gframe(spike=(3, 79), crypto=True, price=2.0)
        close = float(df[(df["ticker"] == "T003")]["close"].iloc[-1])
        quotes = lambda tickers: {t: (close * 1.25, "2026-08-19T00:23:00Z") for t in tickers}  # noqa: E731
        d = paper.scan_frame(df, DATA, validation=VALIDATED, market="CRYPTO", quotes=quotes)["decisions"][0]
        self.assertEqual(d["decision"], "NOT EXECUTABLE")
        self.assertIn("above the chase limit", d["reason"])


class FrozenFeatures(unittest.TestCase):
    def test_us_features_are_gzipped_reproducibly_and_hashed(self):
        """Guards against: a frozen feature file whose bytes change with the write time (gzip
        stores one by default), so the same inputs could not be shown to hash the same."""
        import gzip
        import tempfile
        from pathlib import Path
        from unittest import mock

        warnings.simplefilter("ignore")
        out = paper.scan_frame(gframe(spike=(7, 79)), DATA, validation=DETECTION_ONLY, market="US")
        original = paper.append
        digests = []
        for run in range(2):
            with tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(paper, "SCANS", Path(tmp) / "scans"), \
                    mock.patch.object(paper, "rel", str), \
                    mock.patch.object(paper, "append", lambda recs, timestamper=None, _t=tmp:
                                      original(recs, path=Path(_t) / "ledger.jsonl")):
                rec = {**out, "scan": dict(out["scan"])}
                paths = paper.record_scan(rec)
                self.assertTrue(str(paths[0]).endswith("features.csv.gz"))
                self.assertEqual(paper.sha256_file(paths[0]), rec["scan"]["features_sha256"])
                with gzip.open(paths[0], "rt", encoding="utf-8") as fh:
                    self.assertEqual(len(pd.read_csv(fh)), 60)
                digests.append(rec["scan"]["features_sha256"])
        self.assertEqual(digests[0], digests[1])


class CommittedEvidence(unittest.TestCase):
    def test_e2_evidence_is_found_and_blocks_a_buy(self):
        """The decision gate must read the committed E2 validation and its harness run; if either is
        missed, a decision could be taken on detection alone."""
        for market in ("US", "CRYPTO"):
            ev = paper.validation_evidence(market)
            self.assertIsNotNone(ev, market)
            self.assertEqual(ev["rule"], "G2_RET30")
            self.assertLess(ev["p_one_sided_vs_matched"], 0.05)
            self.assertIsNotNone(ev["trading"], market)
            self.assertGreaterEqual(ev["trading"]["p_one_sided"], 0.05)
            self.assertEqual(paper.already_scanned("1999-01-01", market), False)


if __name__ == "__main__":
    unittest.main()
