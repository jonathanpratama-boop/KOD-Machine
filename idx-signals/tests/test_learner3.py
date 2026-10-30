"""LEARNER v2.3 (idxsig.learner3). Synthetic data, no network. Each test names the failure it guards against."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import learner3 as L3
from idxsig import paper
from idxsig.execution import Market

NOW = "2026-11-03T23:00:00Z"


def market(n_tickers=3, n_sessions=140, price=10.0, start="2026-04-01"):
    dates = np.busday_offset(np.datetime64(start, "D"), np.arange(n_sessions), roll="forward")
    shape = (n_tickers, n_sessions)
    a = {"close": np.full(shape, price), "high": np.full(shape, price * 1.01), "low": np.full(shape, price * 0.99),
         "volume": np.full(shape, 100_000.0), "present": np.ones(shape, dtype=bool), "open": np.full(shape, price)}
    return np.array([f"T{i}" for i in range(n_tickers)]), dates, a


def build(tickers, dates, a):
    prev = np.concatenate([a["close"][:, :1], a["close"][:, :-1]], axis=1)
    return Market.build(tickers, dates, a["close"], prev, a["high"], a["low"], a["volume"], a["close"] * a["volume"],
                        a["present"], None, opens=a["open"], price_limits=False)


class Features(unittest.TestCase):
    def test_edgar_windows_and_split_rules(self):
        """Guards against: an 8-K two days before counted as that day's, a forward split read as a reverse one, a share
        count from after a split, or a short share without 20 files of history."""
        fil = pd.DataFrame({"form": ["8-K", "8-K", "424B5", "S-3", "S-1"],
                            "filingDate": ["2026-10-26", "2026-10-28", "2026-01-15", "2024-02-01", "2026-09-01"]})
        short = pd.Series({f"2026-10-{d:02d}": 0.5 for d in range(1, 29)})
        short["2026-10-28"] = 0.8
        out = L3.edgar_features(fil, [{"end": "2026-06-30", "val": 1e8}], short, "2026-10-28", "2026-10-27", 5e6,
                                [("2026-08-01", 0.1)])
        self.assertEqual(out["filing_8k"], 1.0)  # the 28th
        self.assertEqual((out["offering90"], out["shelf3y"], out["b5_12m"]), (1.0, 1.0, 1.0))
        self.assertEqual(out["revsplit6m"], 1.0)
        self.assertEqual(out["has_shares"], 0.0)  # the split after the quarter end voids the count
        self.assertAlmostEqual(out["short_ratio"], (0.8 - 0.4) / 0.2)
        self.assertAlmostEqual(out["short_abn"], (0.8 - 0.5) / 0.15)
        out = L3.edgar_features(fil.iloc[:1], [{"end": "2026-06-30", "val": 1e8}], None, "2026-10-28", "2026-10-27", 5e6,
                                [("2026-05-01", 2.0)])  # a forward split, and before the quarter end
        self.assertEqual((out["filing_8k"], out["revsplit6m"], out["has_shares"], out["has_short"]), (0.0, 0.0, 1.0, 0.0))
        self.assertAlmostEqual(out["log_shares"], 8 - 7.5)
        self.assertAlmostEqual(out["log_turnover"], np.log10(5e6 / 1e8) + 1.5)
        out = L3.edgar_features(None, [], None, "2026-10-28", "2026-10-27", None, [])
        self.assertEqual(sum(out.values()), 0.0)

    def test_bar_features_stay_inside_the_lookback_and_read_the_spike(self):
        """Guards against: a lookback longer than the live pull covers, or the spike day inside its own volatility."""
        tickers, dates, a = market()
        d = 130
        rng = np.random.default_rng(0)
        a["close"][0, :d] = 10 * np.exp(np.cumsum(rng.normal(0, 0.02, d)))
        a["close"][0, d - 2] = a["close"][0, d - 3] * 0.99  # a down day ends the streak
        a["close"][0, d - 1] = a["close"][0, d - 2] * 1.01
        a["close"][0, d] = a["close"][0, d - 1] * 1.40
        m = build(tickers, dates, a)
        flag = np.zeros(m.shape, dtype=bool)
        flag[0, d - 30] = True
        f = L3.bar_features(m, flag, 0, d)
        self.assertGreater(f["vol20_pre"], 0.1)
        self.assertLess(f["vol20_pre"], 0.5)  # about 0.02 / 0.10
        self.assertTrue(1.5 < f["spike_z"] < 3.0)  # 0.40 / about 0.02 = about 20, / 10
        self.assertEqual(f["spikes60"], 1 / 3)
        self.assertEqual(f["streak"], 0.2)  # the 1% up day and the spike
        self.assertEqual(f["dist_high120"], 0.0)  # a new high
        self.assertEqual(f["age120"], 1.0)
        raw = L3.chart_raw(m, 0, d)  # v2.4's chart block: a spike that closes at a new high
        self.assertGreater(raw["rsi14"], 70)
        self.assertGreater(raw["stoch_k14"], 0.9)
        self.assertGreater(raw["bollinger_b"], 1.0)
        self.assertGreater(raw["macd_hist"], 0.0)
        for k in L3.CHART:
            self.assertTrue(-4 <= f[k] <= 4)
        m2 = build(*market(n_sessions=400))
        self.assertEqual(L3.bar_features(m2, np.zeros(m2.shape, dtype=bool), 0, 390)["age120"], 1.0)
        a["present"][0, :d - 50] = False
        self.assertAlmostEqual(L3.bar_features(build(tickers, dates, a), flag, 0, d)["age120"], 51 / 120)
        a["present"][0, :d - 20] = False  # fewer than 30 sessions: the chart block is missing (0 after scaling)
        g = L3.bar_features(build(tickers, dates, a), flag, 0, d)
        self.assertEqual([g[k] for k in L3.CHART], [0.0] * 4)


def warm_start(path: Path, n=400, seed=1) -> str:
    rng = np.random.default_rng(seed)
    with gzip.open(path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "session", *L3.FEATURES, "y_NEXT_DUMP10_1", "y_DUMP10_5"])
        for i in range(n):
            x = rng.normal(0, 1, len(L3.FEATURES))
            p = 1 / (1 + np.exp(-(-0.6 + 0.9 * x[L3.FEATURES.index("vol20_pre")])))
            w.writerow([f"H{i}", "2022-01-03", *[round(v, 6) for v in x], int(rng.random() < p), int(rng.random() < p)])
    return hashlib.sha256(path.read_bytes()).hexdigest()


def registers(n_sessions=45, per_session=8, seed=2, skill=0.9):
    """Synthetic SPEC_US sets (register v1.1) with their NEXT1 and BASE5 resolutions; features come from fake_features."""
    rng = np.random.default_rng(seed)
    recs, feats, truth = [], {}, {}
    sessions = [str(d) for d in np.busday_offset(np.datetime64("2026-10-30", "D"), np.arange(n_sessions), roll="forward")]
    for si, sess in enumerate(sessions):
        sealed = f"{sess}T23:00:00Z"
        for j in range(per_session):
            sid = f"SPEC-{sess}-{j}"
            x = rng.normal(0, 1, len(L3.FEATURES))
            p = 1 / (1 + np.exp(-(-0.6 + skill * x[L3.FEATURES.index("vol20_pre")])))
            y = rng.random() < p
            feats[sid] = x
            truth[sid] = y
            recs.append({"type": "CATALYST_SET", "family": "SPEC_US", "market": "US", "set_id": sid, "ticker": f"S{j}",
                         "signal_session": sess, "scan_id": f"SCAN-US-{sess}-G2_RET30", "sealed_at": sealed,
                         "entry_cutoff": f"{sessions[min(si + 1, n_sessions - 1)]}T13:30:00Z" if si + 1 < n_sessions else "2027-01-04T13:30:00Z",
                         "protocol": {"id": "KOD-SPEC-REGISTER-v1.1", "sha256": "x"},
                         "cone": [{"id": "DOWN10_1", "prior": 0.35}, {"id": "FADE10_5", "prior": 0.403}],
                         "record_hash": hashlib.sha256(sid.encode()).hexdigest()})
            nxt = sessions[si + 1] if si + 1 < n_sessions else None
            if nxt:
                recs.append({"type": "RESOLUTION", "set_id": sid, "window": "NEXT1", "resolved_at": f"{nxt}T23:30:00Z",
                             "cone": [{"id": "DOWN10_1", "outcome": bool(y), "twins_rate": 0.1}]})
            if si + 6 < n_sessions:
                recs.append({"type": "RESOLUTION", "set_id": sid, "window": "BASE5", "resolved_at": f"{sessions[si + 6]}T23:30:00Z",
                             "cone": [{"id": "FADE10_5", "outcome": bool(y), "twins_rate": 0.2}]})
    recs.sort(key=lambda r: r.get("sealed_at") or r.get("resolved_at"))  # a register appends in time order
    for r in recs:  # the hash chain the learner binds to
        r.setdefault("record_hash", hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest())
    return recs, feats, sessions


class EndToEnd(unittest.TestCase):
    """Seal, forecast, resolve, score, verify: a synthetic register with a real edge, through the real code."""

    def setUp(self):
        warnings.simplefilter("ignore")
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.hist = root / "events_us.csv.gz"
        sha = warm_start(self.hist)
        proto = root / "protocol.json"
        proto.write_text(json.dumps({"protocol_id": "KOD-LEARNER-v2.3-test", "claim": {"looks": [60, 120, 240], "z_min": [3.75, 3.0, 3.0], "min_sessions": [5, 10, 20]}}))
        self.patches = [mock.patch.object(L3, "HISTORY", self.hist), mock.patch.object(L3, "HISTORY_SHA256", sha),
                        mock.patch.object(L3, "PROTOCOL_JSON", proto), mock.patch.object(L3, "LEDGER", root / "learner_v3.jsonl"),
                        mock.patch.object(L3, "REPORT", root / "LEARNER_V3.md"),
                        mock.patch.object(L3.evaluation, "LEDGER", root / "evaluations.jsonl")]
        for p in self.patches:
            p.start()
        L3.history_rows.cache_clear()
        self.recs, self.feats, self.sessions = registers()
        orig = paper.ledger_lines  # the scans of whatever register the test holds at call time

        def ledger_lines(path=None):
            return ([{"type": "SCAN", "scan_id": f"SCAN-US-{s}-G2_RET30"} for s in self.sessions] if path is None
                    else orig(path))

        self.patches.append(mock.patch.object(L3.paper, "ledger_lines", ledger_lines))
        self.patches[-1].start()
        self.patches.append(mock.patch.object(L3, "set_features", lambda s, scan, ctx: (self.feats[s["set_id"]], {"test": True})))
        self.patches[-1].start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        L3.history_rows.cache_clear()
        self.tmp.cleanup()

    def run_days(self, upto: int) -> list[dict]:
        """Forecast each session's sets at 23:05 UTC of that session, on the records sealed by then."""
        from datetime import datetime, timezone

        lrecs = []
        for si in range(upto):
            asof = datetime.fromisoformat(f"{self.sessions[si]}T23:05:00+00:00")
            visible = [r for r in self.recs if (r.get("sealed_at") or r.get("resolved_at")) <= asof.strftime("%Y-%m-%dT%H:%M:%SZ")]
            out, notes = L3.forecast_records(asof, visible, lrecs, ctx=object())
            self.assertEqual(notes, [])
            lrecs += paper.append(out, path=L3.LEDGER)
        return lrecs

    def test_learns_scores_and_verifies(self):
        """Guards against: a forecast that does not reproduce from the ledger states it records; a gate that opens on
        no evidence; a claim read before its look; a verify that misses an edited forecast."""
        self.recs, self.feats, self.sessions = registers(n_sessions=95, skill=1.2)  # 33 features, 32 of them noise
        lrecs = self.run_days(80)
        self.assertEqual(len(lrecs), 80 * 8)
        asof = f"{self.sessions[80]}T23:05:00Z"
        visible = [r for r in self.recs if (r.get("sealed_at") or r.get("resolved_at")) <= asof]
        pairs = L3.forward_pairs(visible, lrecs, asof)
        self.assertGreater(len([p for p in pairs if p["statement"] == L3.HEADLINE]), 500)
        st = L3.statistics(visible, lrecs, asof)
        h = st["statements"][L3.HEADLINE]
        self.assertGreater(h["auc"], 0.6)  # the edge is in vol20_pre, which the benchmark also sees
        self.assertGreater(st["descriptive_claim"]["z"], 3.75)
        self.assertEqual(st["gates"]["PATH/1"]["observations"], 79)
        self.assertTrue(st["gates"]["PATH/1"]["open"])  # an edge of this size takes 40-80 sessions to prove
        self.assertGreater(st["gates"]["PATH/1"]["alpha"], 0.0)
        self.assertNotIn("SKILL", st["claim"]["verdict"])  # reporting never creates a planned decision
        proto, sha = L3.protocol()
        frozen = L3.evaluation.freeze(visible, lrecs, asof, proto, sha, L3.forward_pairs, L3.claim, L3.HEADLINE)
        self.assertEqual(len(frozen), 3)
        st = L3.statistics(visible, lrecs, asof)
        self.assertEqual(st["claim"]["look"], 240)
        self.assertEqual(st["claim"]["n_pairs"], 240)
        self.assertEqual(L3.evaluation.verify(claim_fn=L3.claim, proto=proto, proto_sha=sha), [])
        text = L3.render(st, lrecs)
        self.assertIn("What are we predicting?", text)
        self.assertEqual(L3.verify(L3.LEDGER, self.recs), [])
        lines_ = L3.LEDGER.read_text().splitlines()
        rec = json.loads(lines_[100])
        rec["forecasts"][L3.HEADLINE]["raw"] = round(rec["forecasts"][L3.HEADLINE]["raw"] + 0.05, 6)
        L3.LEDGER.write_text("\n".join([*lines_[:100], json.dumps(rec, sort_keys=True), *lines_[101:]]) + "\n")
        problems = L3.verify(L3.LEDGER, self.recs)
        self.assertTrue(any("does not reproduce" in p or "chain" in p.lower() or "hash" in p.lower() for p in problems))

    def test_no_edge_earns_nothing(self):
        """Guards against: confidence from noise (the fair null: the learner moves its forecasts on features unrelated
        to the outcome)."""
        self.recs, self.feats, self.sessions = registers(skill=0.0, seed=5)
        lrecs = self.run_days(40)
        asof = f"{self.sessions[40]}T23:05:00Z"
        visible = [r for r in self.recs if (r.get("sealed_at") or r.get("resolved_at")) <= asof]
        st = L3.statistics(visible, lrecs, asof)
        self.assertFalse(st["gates"]["PATH/1"]["open"])
        self.assertEqual(st["gates"]["PATH/1"]["alpha"], 0.0)
        self.assertNotIn("SKILL", st["claim"]["verdict"])

    def test_only_register_v1_1_sets_are_forecast(self):
        """Guards against: forecasting a v1 set, whose cone cannot grade the next session's close."""
        from datetime import datetime, timezone

        old = dict(self.recs[0]); old["set_id"] = "SPEC-OLD"; old["protocol"] = {"id": "KOD-SPEC-REGISTER-v1", "sha256": "y"}
        out, _ = L3.forecast_records(datetime(2026, 10, 30, 23, 5, tzinfo=timezone.utc), [old, self.recs[0]], [], ctx=object())
        self.assertEqual([r["set_id"] for r in out], [self.recs[0]["set_id"]])


class WarmStart(unittest.TestCase):
    def test_history_rows_are_capped_and_pinned(self):
        """Guards against: history outweighing the live record, or a warm start that is not the frozen file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.csv.gz"
            sha = warm_start(path, n=500)
            with mock.patch.object(L3, "HISTORY", path), mock.patch.object(L3, "HISTORY_SHA256", sha):
                L3.history_rows.cache_clear()
                rows = L3.history_rows()
                self.assertEqual(len(rows), 1000)
                self.assertAlmostEqual(sum(r.w for r in rows if r.task.endswith(L3.HEADLINE)), L3.N_CAP)
            with mock.patch.object(L3, "HISTORY", path), mock.patch.object(L3, "HISTORY_SHA256", "0" * 64):
                L3.history_rows.cache_clear()
                with self.assertRaises(RuntimeError):
                    L3.history_rows()
            L3.history_rows.cache_clear()


if __name__ == "__main__":
    unittest.main()

