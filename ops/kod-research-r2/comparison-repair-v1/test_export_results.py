import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

import export_results as report


class ResultsExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "engine").mkdir()
        self.path = self.root / "engine/research.sqlite"
        self.now = dt.datetime.now(dt.timezone.utc).timestamp()
        self.watermark = int(self.now // 60) * 60 - 300
        self.day = int(self.watermark // 86400) * 86400
        self.last = int(self.watermark // 3600) * 3600 - 3600
        self.config = {"study_id": "fixture", "primary": [{"symbol": s} for s in ("TESTUSDT", "C1USDT", "C2USDT")]}
        (self.root / "research.json").write_text(json.dumps(self.config))
        (self.root / "RESEARCH_ENGINE_HEALTH.json").write_text(json.dumps({"status": "RUNNING", "epoch": self.now}))
        (self.root / "HEALTH.json").write_text(json.dumps({"collector": {"coverage": {"pooled_on_time_coverage": .6}}}))
        self.db = sqlite3.connect(self.path)
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE events(id TEXT PRIMARY KEY,symbol TEXT,hour REAL,reference REAL,payload TEXT);
            CREATE TABLE positions(id TEXT PRIMARY KEY,event_id TEXT,arm INTEGER,symbol TEXT,role TEXT,decision REAL,status TEXT,entry TEXT);
            CREATE TABLE endpoints(position_id TEXT,horizon INTEGER,deadline REAL,status TEXT,payload TEXT,PRIMARY KEY(position_id,horizon));
            CREATE TABLE daily(symbol TEXT,opened REAL,available REAL,volume REAL,PRIMARY KEY(symbol,opened));
            CREATE TABLE hours(symbol TEXT,opened REAL,available REAL,close REAL,volume REAL,payload TEXT,PRIMARY KEY(symbol,opened));
        """)
        self.db.execute("INSERT INTO meta VALUES('watermark',?)", (json.dumps(self.watermark),))
        for symbol in ("TESTUSDT", "C1USDT", "C2USDT"):
            for opened in (self.last, self.last - 24 * 3600):
                self.db.execute("INSERT INTO hours VALUES(?,?,?,?,?,?)", (symbol, opened, self.watermark - 10, 100, 1000, '{}'))
            for i in range(1, 31):
                self.db.execute("INSERT INTO daily VALUES(?,?,?,?)", (symbol, self.day - i * 86400, self.watermark - 10, 1000))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.temporary.cleanup()

    def add_event(self, ident="first", controls=True, arms=(1, 5, 30, 240), complete=False):
        reference = self.watermark - 100
        control_rows = [{"symbol": "C1USDT"}, {"symbol": "C2USDT"}] if controls else []
        self.db.execute("INSERT INTO events VALUES(?,?,?,?,?)", (ident, "TESTUSDT", reference - 3600, reference,
                        json.dumps({"controls": control_rows, "controls_status": "AVAILABLE" if controls else "UNAVAILABLE_PRE_EVENT_FEATURES"})))
        for arm in arms:
            targets = [("TESTUSDT", "EVENT", .05), ("C1USDT", "CONTROL", -.02), ("C2USDT", "CONTROL", .0)] if controls else [("TESTUSDT", "EVENT", .05)]
            for symbol, role, net in targets:
                pid = f"{ident}:{arm}:{symbol}"
                self.db.execute("INSERT INTO positions VALUES(?,?,?,?,?,?,?,?)", (pid, ident, arm, symbol, role, reference,
                    "ENTERED", json.dumps({"received_at": report.iso(reference + 1)})))
                payload = json.dumps({"returns": {"modeled_net_token_return": net, "net_excess": net - .01}}) if complete else None
                self.db.execute("INSERT INTO endpoints VALUES(?,?,?,?,?)", (pid, 24, reference + 24 * 3600, "COMPLETE" if complete else "AWAIT_EXIT", payload))
        self.db.commit()

    def test_pending_entries_are_not_results_or_zero_returns(self):
        self.add_event(controls=False)
        result = report.export_results(self.root)
        self.assertEqual(result["independent_events"], 1)
        self.assertEqual(result["events_with_completed_24h"], 0)
        self.assertEqual(result["events_without_controls"], 1)
        self.assertIsNotNone(result["next_primary_due_at"])
        for arm in result["arms"]:
            self.assertEqual((arm["event_entries"], arm["completed_24h"], arm["awaiting_24h"]), (1, 0, 1))
            self.assertIsNone(arm["mean_net_return"])
            self.assertIsNone(arm["mean_benchmark_excess"])
            self.assertIsNone(arm["mean_control_excess"])

    def test_completed_four_arms_still_count_as_one_independent_event(self):
        self.add_event(complete=True)
        result = report.export_results(self.root)
        self.assertEqual(result["events_with_completed_24h"], 1)
        self.assertIsNone(result["next_primary_due_at"])
        for arm in result["arms"]:
            self.assertEqual(arm["completed_24h"], 1)
            self.assertAlmostEqual(arm["mean_net_return"], .05)
            self.assertAlmostEqual(arm["mean_benchmark_excess"], .04)
            self.assertAlmostEqual(arm["mean_control_excess"], .06)
            self.assertEqual(arm["completed_control_pairs"], 1)

    def test_incomplete_fixed_control_set_does_not_become_a_partial_comparison(self):
        self.add_event(complete=True)
        self.db.execute("UPDATE endpoints SET status='CENSORED',payload=NULL WHERE position_id='first:1:C2USDT'")
        self.db.commit()
        result = report.export_results(self.root)
        self.assertIsNone(result["arms"][0]["mean_control_excess"])
        self.assertEqual(result["arms"][0]["completed_control_pairs"], 0)
        self.assertAlmostEqual(result["arms"][1]["mean_control_excess"], .06)

    def test_censored_or_unentered_positions_never_count_as_zero_return(self):
        self.add_event(controls=False)
        self.db.execute("UPDATE endpoints SET status='CENSORED' WHERE position_id='first:1:TESTUSDT'")
        self.db.execute("DELETE FROM endpoints WHERE position_id='first:5:TESTUSDT'")
        self.db.execute("UPDATE positions SET status='NOT_ENTERED',entry=NULL WHERE id='first:5:TESTUSDT'")
        self.db.commit()
        result = report.export_results(self.root)
        self.assertEqual(result["arms"][0]["censored_24h"], 1)
        self.assertEqual(result["arms"][1]["event_entries"], 0)
        self.assertIsNone(result["arms"][0]["mean_net_return"])
        self.assertIsNone(result["events"][0]["arms"][1]["entry_at"])

    def test_new_daily_data_only_becomes_ready_at_its_actual_receipt(self):
        self.db.execute("UPDATE daily SET available=? WHERE opened=?", (self.watermark + 1, self.day - 30 * 86400))
        self.db.commit()
        before = report.export_results(self.root)
        self.assertEqual(before["comparison_inputs"]["eligible_symbols"], 0)
        self.db.execute("UPDATE meta SET value=? WHERE key='watermark'", (json.dumps(self.watermark + 1),))
        self.db.commit()
        after = report.export_results(self.root)
        self.assertEqual(after["comparison_inputs"], {"status": "READY", "as_of": report.iso(self.watermark + 1),
                         "eligible_symbols": 3, "total_symbols": 3})

    def test_one_missing_daily_bar_keeps_that_symbol_unavailable(self):
        self.db.execute("DELETE FROM daily WHERE symbol='TESTUSDT' AND opened=?", (self.day - 86400,))
        self.db.commit()
        self.assertEqual(report.export_results(self.root)["comparison_inputs"]["eligible_symbols"], 2)

    def test_export_is_read_only(self):
        self.add_event()
        self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        original_connect = sqlite3.connect
        opened = []
        def capture_connect(*args, **kwargs):
            opened.append((args, kwargs))
            return original_connect(*args, **kwargs)
        with mock.patch.object(report.sqlite3, "connect", capture_connect):
            report.export_results(self.root)
        self.assertIn("mode=ro", opened[0][0][0])
        self.assertTrue(opened[0][1]["uri"])
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_snapshot_does_not_mix_concurrent_event_insert(self):
        self.add_event()
        original_connect = sqlite3.connect
        writer = self.db
        class ConcurrentInsertConnection(sqlite3.Connection):
            def execute(connection, sql, parameters=()):
                if sql == "SELECT * FROM events ORDER BY reference,id":
                    writer.execute("INSERT INTO events VALUES('later','TESTUSDT',0,0,'{}')")
                    writer.commit()
                return super().execute(sql, parameters)
        def connect(*args, **kwargs):
            return original_connect(*args, **kwargs, factory=ConcurrentInsertConnection)
        with mock.patch.object(report.sqlite3, "connect", connect):
            result = report.export_results(self.root)
        self.assertEqual(result["independent_events"], 1)
        self.assertEqual(writer.execute("SELECT count(*) FROM events").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
