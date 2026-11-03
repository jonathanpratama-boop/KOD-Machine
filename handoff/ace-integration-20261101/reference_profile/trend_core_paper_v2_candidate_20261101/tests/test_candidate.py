import copy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
import hashlib
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from paper_candidate import Ledger, account_view, apply, evidence, operation_id, sha, sharpe_status, stamp
from fixtures import SCENARIO, init, quote, decision, seed_quotes, buy_both


def worker(path, command, out):
    try: out.put(("ok", Ledger(path).transact(command)))
    except Exception as exc: out.put(("error",type(exc).__name__,str(exc)))


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"account.jsonl"
        self.l=Ledger(self.path)
    def tearDown(self): self.tmp.cleanup()
    def test_cash_fixture_1000_and_10000(self):
        for cash in ("1000","10000"):
            with self.subTest(cash=cash):
                l=Ledger(Path(self.tmp.name)/(cash+".jsonl"))
                d=buy_both(l,cash)
                self.assertEqual(d["normalized_targets"],{"BTCUSDT":"0.5","ETHUSDT":"0.5"})
                self.assertEqual(D(d["account"]["cash_reserved"]),D(cash))
                st=l.state();v=account_view(st,st["clock"])
                self.assertGreater(st["holdings"]["BTCUSDT"],0)
                self.assertGreater(st["holdings"]["ETHUSDT"],0)
                self.assertGreaterEqual(v["cash_available"],0)
                self.assertLessEqual(v["gross_fraction"],1)
                self.assertEqual(v["cash_reserved"],0)
                self.assertEqual(D(cash)+sum(f["cash_change"] for f in st["fills"]),st["cash_total"])
                self.assertEqual(sum(f["fee"] for f in st["fills"]),st["realized_fees"])
                self.assertEqual(st["peak"],D(cash))
                self.assertLess(v["nav"],D(cash))
    def test_replay_retry_and_conflict(self):
        command=init()
        first=self.l.transact(command);before=self.path.read_bytes()
        self.assertEqual(Ledger(self.path).transact(command),first)
        self.assertEqual(before,self.path.read_bytes())
        with self.assertRaisesRegex(ValueError,"conflicting payload"):
            self.l.transact({**command,"initial_cash":"1000"})
        self.assertEqual(before,self.path.read_bytes())
    def test_uncertain_fsync_retry_establishes_new_durability_barrier(self):
        self.l.transact(init())
        command={"op":"advance","at":"2026-02-10T00:00:01Z"}
        import paper_candidate as p
        real=p.os.fsync
        with patch.object(p.os,"fsync",side_effect=OSError("injected fsync failure")):
            with self.assertRaises(OSError): self.l.transact(command)
        before=self.path.read_bytes()
        with patch.object(p.os,"fsync",wraps=real) as barrier:
            out=self.l.transact(command)
            self.assertGreaterEqual(barrier.call_count,2)
        self.assertEqual(out["status"],"ADVANCED_NO_SYNTHETIC_FILL")
        self.assertEqual(before,self.path.read_bytes())
    def test_concurrent_same_operation_only_once(self):
        q=multiprocessing.Queue();command=init()
        workers=[multiprocessing.Process(target=worker,args=(str(self.path),command,q)) for _ in range(4)]
        for p in workers:p.start()
        for p in workers:p.join(10);self.assertEqual(p.exitcode,0)
        for _ in workers:self.assertEqual(q.get(timeout=1)[0],"ok")
        self.assertEqual(len(self.path.read_text().splitlines()),1)
    def test_unknown_mark_propagates_not_cost(self):
        buy_both(self.l)
        v=self.l.transact({"op":"advance","at":"2026-02-10T00:04:00Z"})["account"]
        self.assertIsNone(v["nav"])
        self.assertEqual(set(v["missing_marks"]),{"BTCUSDT","ETHUSDT"})
        self.assertTrue(all(q>0 for q in self.l.state()["holdings"].values()))
    def test_future_receipt_and_wrong_product_rejected(self):
        self.l.transact(init())
        q=quote("BTCUSDT","2026-02-10T00:00:10Z")
        q["at"]="2026-02-10T00:00:05Z"
        with self.assertRaises(ValueError):self.l.transact(q)
        q=quote("BTCUSDT","2026-02-10T00:00:10Z")
        q["evidence"]["payload"]["product"]="perpetual"
        q["evidence"]["payload_sha256"]=sha(q["evidence"]["payload"])
        with self.assertRaises(ValueError):self.l.transact(q)
        q["evidence"]["kind"]="live"
        with self.assertRaises(ValueError):self.l.transact(q)
    def test_same_time_and_past_midnight_do_not_fill(self):
        self.l.transact(init());seed_quotes(self.l);self.l.transact(decision())
        out=self.l.transact(quote("BTCUSDT","2026-02-10T00:01:00Z"))
        self.assertEqual(out["fills"],[])
        self.assertEqual(out["blocked"][0]["reason"],"INELIGIBLE_TIME")
        with self.assertRaises(ValueError):self.l.transact(quote("BTCUSDT","2026-02-10T00:00:00Z",received_at="2026-02-10T00:01:01Z"))
    def test_unknown_liquidity_no_fill_and_expiry(self):
        self.l.transact(init());seed_quotes(self.l);self.l.transact(decision())
        out=self.l.transact(quote("BTCUSDT","2026-02-10T00:01:05Z",size=None))
        self.assertEqual(out["fills"],[])
        self.assertEqual(out["blocked"][0]["reason"],"UNKNOWN_LIQUIDITY")
        out=self.l.transact({"op":"advance","at":"2026-02-10T01:01:00Z"})
        self.assertEqual(out["account"]["cash_reserved"],"0")
        self.assertFalse(self.l.state()["fills"])
    def test_buy_fails_closed_when_other_held_mark_stale(self):
        self.l.transact(init());seed_quotes(self.l);self.l.transact(decision())
        self.l.transact(quote("BTCUSDT","2026-02-10T00:01:05Z"))
        out=self.l.transact(quote("ETHUSDT","2026-02-10T00:04:00Z"))
        self.assertEqual(out["fills"],[])
        self.assertIsNone(out["account"]["nav"])
        self.assertEqual(out["blocked"][0]["reason"],"UNKNOWN_AGGREGATE_NAV_AT_FILL")
        self.l.transact(quote("BTCUSDT","2026-02-10T00:04:01Z"))
        out=self.l.transact(quote("ETHUSDT","2026-02-10T00:04:02Z"))
        self.assertEqual(len(out["fills"]),1)
    def test_partial_fill_quantity_and_fees(self):
        self.l.transact(init());seed_quotes(self.l);self.l.transact(decision())
        out=self.l.transact(quote("BTCUSDT","2026-02-10T00:01:05Z",size=".01"))
        self.assertEqual(D(out["fills"][0]["quantity"]),D(".01"))
        before=len(self.l.state()["fills"])
        self.l.transact(quote("BTCUSDT","2026-02-10T00:01:06Z",size="10000"))
        self.assertEqual(len(self.l.state()["fills"]),before)
    def test_actual_holdings_drift_requires_rebalance(self):
        buy_both(self.l)
        self.l.transact(quote("BTCUSDT","2026-02-11T00:00:50Z","200","200.1"))
        self.l.transact(quote("ETHUSDT","2026-02-11T00:00:50Z","100","100.1"))
        self.l.transact(decision("2026-02-10","2026-02-11T00:01:00Z"))
        pending={o["symbol"]:o for o in self.l.state()["intents"] if o["status"]=="PENDING"}
        self.assertEqual(pending["BTCUSDT"]["side"],"SELL")
        self.assertEqual(pending["ETHUSDT"]["side"],"BUY")
        before=self.l.state()["holdings"]["BTCUSDT"]
        self.l.transact(quote("BTCUSDT","2026-02-11T00:01:05Z","200","200.1"))
        self.assertLess(self.l.state()["holdings"]["BTCUSDT"],before)
        self.l.transact(quote("ETHUSDT","2026-02-11T00:01:06Z","100","100.1"))
        v=account_view(self.l.state(),"2026-02-11T00:01:06Z")
        self.assertGreaterEqual(v["cash_available"],0)
        self.assertLessEqual(v["gross_fraction"],1)
    def test_sells_before_buys_across_symbols_not_quote_arrival_order(self):
        buy_both(self.l)
        self.l.transact(quote("BTCUSDT","2026-02-11T00:00:50Z","200","200.1"))
        self.l.transact(quote("ETHUSDT","2026-02-11T00:00:50Z","100","100.1"))
        self.l.transact(decision("2026-02-10","2026-02-11T00:01:00Z"))
        early=self.l.transact(quote("ETHUSDT","2026-02-11T00:01:05Z","100","100.1"))
        self.assertEqual(early["fills"],[])
        self.assertEqual(early["blocked"][0]["reason"],"WAITING_FOR_SELLS")
        self.l.transact(quote("BTCUSDT","2026-02-11T00:01:06Z","200","200.1"))
        later=self.l.transact(quote("ETHUSDT","2026-02-11T00:01:07Z","100","100.1"))
        self.assertEqual(len(later["fills"]),1)
        self.assertGreater(D(later["fills"][0]["quantity"]),D(1))
    def test_first_peak_and_persistent_kill_no_same_quote_liquidation(self):
        buy_both(self.l,"1000")
        self.l.transact(quote("BTCUSDT","2026-02-10T00:02:00Z","50","50.1"))
        out=self.l.transact(quote("ETHUSDT","2026-02-10T00:02:00Z","50","50.1"))
        st=self.l.state()
        self.assertIsNotNone(st["kill"])
        self.assertEqual(st["peak"],D(1000))
        self.assertGreaterEqual(st["maximum_observed_drawdown"],D(".25"))
        self.assertTrue(all(q>0 for q in st["holdings"].values()))
        count=len(st["fills"])
        self.l.transact(quote("BTCUSDT","2026-02-10T00:02:01Z","40","40.1",size=".1"))
        self.assertGreater(len(self.l.state()["fills"]),count)
        self.assertLess(self.l.state()["fills"][-1]["price"],D(50))
        self.assertGreater(self.l.state()["holdings"]["BTCUSDT"],0)
        d=decision("2026-02-09","2026-02-10T00:02:02Z")
        # Same date is already sealed: conflicting retry must reject rather than re-evaluate.
        with self.assertRaises(ValueError): self.l.transact(d)
        result=Ledger(self.path).transact(decision("2026-02-10","2026-02-11T00:01:00Z"))
        self.assertEqual(result["status"],"BLOCKED_PERSISTENT_KILL")
        self.assertIsNotNone(Ledger(self.path).state()["kill"])
    def test_missing_cycles_and_late_daily_not_reconstructed(self):
        self.l.transact(init())
        a=self.l.transact({"op":"daily","date":"2026-02-10","at":"2026-02-10T00:00:00Z"})
        self.assertEqual(a["sample"]["nav"],"10000")
        m=self.l.transact({"op":"missed","date":"2026-02-11","at":"2026-02-12T00:00:00Z","reason":"PROCESS_NOT_RUN"})
        self.assertEqual(m["logged_at"],"2026-02-12T00:00:00Z")
        b=self.l.transact({"op":"daily","date":"2026-02-12","at":"2026-02-12T00:00:00Z"})
        self.assertIsNone(b["sample"]["daily_return"])
        c=self.l.transact({"op":"daily","date":"2026-02-13","at":"2026-02-13T00:06:00Z"})
        self.assertEqual(c["status"],"MISSED_CUTOFF")
        self.assertIsNone(c["sample"]["nav"])
    def test_bar_completeness_and_future_publication(self):
        self.l.transact(init());seed_quotes(self.l)
        for mutation in ("gap","future","hash"):
            d=decision();bars=d["evidence"]["payload"]["BTCUSDT"]
            if mutation=="gap": bars[1]["day"]=bars[0]["day"]
            if mutation=="future": bars[-1]["published_at"]="2027-01-01T00:00:00Z"
            if mutation=="hash": bars[-1]["close"]="1"
            d["evidence"]["payload_sha256"]=sha(d["evidence"]["payload"])
            with self.assertRaises(ValueError):self.l.transact(d)
    def test_sharpe_clean_window_missing_and_zero_variance(self):
        start=date(2026,1,1)
        flat=[{"date":(start+timedelta(days=i)).isoformat(),"nav":D(1000)} for i in range(91)]
        self.assertEqual(sharpe_status(flat)["status"],"ZERO_MEAN_ZERO_VARIANCE")
        self.assertEqual(sharpe_status(flat[:90])["status"],"INSUFFICIENT_90_RETURNS")
        bad=copy.deepcopy(flat);bad[40]["nav"]=None
        self.assertEqual(sharpe_status(bad)["status"],"MISSING_DAILY_MARK")
        bad=copy.deepcopy(flat);bad[40]["date"]="2020-01-01"
        self.assertEqual(sharpe_status(bad)["status"],"MISSING_DAILY_MARK")
        losing=[{"date":(start+timedelta(days=i)).isoformat(),"nav":D(1000)*(D(".999")**i)} for i in range(91)]
        self.assertTrue(sharpe_status(losing)["negative"])
    def test_actual_daily_negative_sharpe_kills_before_drawdown(self):
        # Pure transition API exercises exact reducer without quadratic journal I/O.
        zero={**SCENARIO,"id":"SYNTHETIC_ZERO_COST", "fee":"0","slippage":"0"}
        st,_=apply(None,init("1000",scenario=zero))
        for symbol in ("BTCUSDT","ETHUSDT"):
            st,_=apply(st,quote(symbol,"2026-02-10T00:00:50Z","100","100"))
        st,_=apply(st,decision())
        for symbol in ("BTCUSDT","ETHUSDT"):
            st,_=apply(st,quote(symbol,"2026-02-10T00:01:05Z","100","100"))
        start=date(2026,2,11)
        for i in range(91):
            t=(start+timedelta(days=i)).isoformat()+"T00:00:00Z"
            price=D(100)*(D(".999")**i)*(D("1.0001") if i%2 else D(1))
            for symbol in ("BTCUSDT","ETHUSDT"):
                st,_=apply(st,quote(symbol,t,str(price),str(price)))
            st,out=apply(st,{"op":"daily","date":t[:10],"at":t})
        self.assertEqual(st["kill"]["reason"],"NEGATIVE_TRAILING_90_DAY_SHARPE")
        self.assertLess(st["maximum_observed_drawdown"],D(".25"))
        self.assertEqual(len(st["daily"]),91)
        self.assertEqual(out["trailing_sharpe"]["returns"],90)
    def test_torn_tampered_and_changed_code_refused(self):
        self.l.transact(init());raw=self.path.read_bytes()
        self.path.write_bytes(raw[:-1])
        with self.assertRaisesRegex(ValueError,"torn"):self.l.state()
        self.path.write_bytes(raw.replace(b'10000',b'20000',1))
        with self.assertRaises(ValueError):self.l.state()
        self.path.write_bytes(raw)
        # Alter a journal's claimed code pin and recompute chain: replay still refuses.
        from paper_candidate import _core
        row=json.loads(raw);row["provenance"]["paper_candidate.py"]="0"*64
        row["record_hash"]=_core.event_hash(row)
        self.path.write_text(json.dumps(row)+"\n")
        with self.assertRaisesRegex(ValueError,"pin mismatch"):self.l.state()

if __name__=="__main__":unittest.main(verbosity=2)
