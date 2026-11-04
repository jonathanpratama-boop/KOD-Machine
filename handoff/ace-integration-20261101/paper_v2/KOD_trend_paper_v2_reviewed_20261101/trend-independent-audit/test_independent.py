"""Independent bounded synthetic checks; no market history, receipts or orders."""
import sys,copy,tempfile,unittest,json,hashlib,statistics,math
from unittest.mock import patch
from pathlib import Path
from datetime import date,timedelta
from decimal import Decimal as D
ROOT=Path(__file__).resolve().parent.parent/'trend_core_paper_v2_candidate_20261101'
sys.path.insert(0,str(ROOT))
import paper_candidate as p
from fixtures import init,quote,seed_quotes,decision,buy_both,SCENARIO
class Independent(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'j';self.l=p.Ledger(self.path)
 def test_unknown_aggregate_nav_blocks_buy_until_marks_recover(self):
  self.l.transact(init());seed_quotes(self.l);self.l.transact(decision());self.l.transact(quote('BTCUSDT','2026-02-10T00:01:05Z'))
  before=self.l.state();out=self.l.transact(quote('ETHUSDT','2026-02-10T00:04:00Z'))
  self.assertIsNone(out['account']['nav']);self.assertEqual(out['fills'],[]);self.assertEqual(self.l.state()['cash_total'],before['cash_total'])
  self.assertTrue(any(o['symbol']=='ETHUSDT' and o['status']=='PENDING' for o in self.l.state()['intents']))
  self.l.transact(quote('BTCUSDT','2026-02-10T00:04:01Z'));out=self.l.transact(quote('ETHUSDT','2026-02-10T00:04:02Z'))
  self.assertEqual(len(out['fills']),1);self.assertEqual(out['fills'][0]['side'],'BUY')
 def test_rebalance_waits_for_other_symbol_pending_sale(self):
  buy_both(self.l)
  for sym,bid,ask in [('BTCUSDT','200','200.1'),('ETHUSDT','100','100.1')]:self.l.transact(quote(sym,'2026-02-11T00:00:50Z',bid,ask))
  self.l.transact(decision('2026-02-10','2026-02-11T00:01:00Z'))
  out=self.l.transact(quote('ETHUSDT','2026-02-11T00:01:05Z'));self.assertEqual(out['fills'],[])
  self.l.transact(quote('BTCUSDT','2026-02-11T00:01:06Z','200','200.1'))
  out=self.l.transact(quote('ETHUSDT','2026-02-11T00:01:07Z'));self.assertEqual(len(out['fills']),1);self.assertGreater(D(out['fills'][0]['quantity']),D(20))
 def test_shared_cash_conservation_and_allin_fill_fees(self):
  out=buy_both(self.l,'1000');st=self.l.state()
  self.assertEqual(out['raw_targets'],{'BTCUSDT':'1.0','ETHUSDT':'1.0'});self.assertEqual(out['normalized_targets'],{'BTCUSDT':'0.5','ETHUSDT':'0.5'})
  self.assertEqual(st['cash_total'],D(1000)+sum((x['cash_change'] for x in st['fills']),D(0)))
  self.assertEqual(st['realized_fees'],sum((x['fee'] for x in st['fills']),D(0)))
  for x in st['fills']:
   self.assertEqual(x['fee'],p._core.cash_round(x['quantity']*x['price']*D('.001')))
   self.assertEqual(-x['cash_change'],x['quantity']*x['price']+x['fee'])
  v=p.account_view(st,st['clock']);self.assertGreaterEqual(v['cash_available'],0);self.assertLessEqual(v['gross_fraction'],1);self.assertEqual(v['cash_reserved'],0)
 def test_partial_kill_residual_persisted_and_no_duplicate_quote_fill(self):
  buy_both(self.l,'1000')
  for sym in p.SYMBOLS:self.l.transact(quote(sym,'2026-02-10T00:02:00Z','50','50.1'))
  st=self.l.state();self.assertIsNotNone(st['kill']);self.assertEqual(st['peak'],D(1000));before=st['holdings']['BTCUSDT']
  q=quote('BTCUSDT','2026-02-10T00:02:01Z','40','40.1',size='.1');out=self.l.transact(q)
  self.assertEqual(D(out['fills'][0]['quantity']),D('.1'));self.assertEqual(self.l.state()['holdings']['BTCUSDT'],before-D('.1'))
  raw=self.path.read_bytes();self.assertEqual(self.l.transact(q),out);self.assertEqual(self.path.read_bytes(),raw)
  pending=[o for o in self.l.state()['intents'] if o['status']=='PENDING' and o['symbol']=='BTCUSDT'];self.assertEqual(len(pending),1);self.assertEqual(pending[0]['quantity'],before-D('.1'))
  self.l.transact(quote('BTCUSDT','2026-02-10T00:02:02Z','40','40.1'));self.l.transact(quote('ETHUSDT','2026-02-10T00:02:03Z','40','40.1'))
  st=p.Ledger(self.path).state();self.assertTrue(all(v==0 for v in st['holdings'].values()));self.assertIsNotNone(st['kill']);self.assertEqual(st['peak'],D(1000))
  r=self.l.transact(decision('2026-02-10','2026-02-11T00:01:00Z'));self.assertEqual(r['status'],'BLOCKED_PERSISTENT_KILL')
 def test_unknown_depth_then_sub_precision_ioc_never_invents_units(self):
  self.l.transact(init());seed_quotes(self.l);self.l.transact(decision())
  before=self.l.state()['cash_total'];r=self.l.transact(quote('BTCUSDT','2026-02-10T00:01:01Z',size=None));self.assertEqual(r['fills'],[])
  r=self.l.transact(quote('BTCUSDT','2026-02-10T00:01:02Z',size='0.000000001'));self.assertEqual(r['fills'],[]);self.assertEqual(self.l.state()['cash_total'],before)
  self.assertEqual(self.l.state()['holdings']['BTCUSDT'],0)
 def test_wrong_venue_instrument_and_future_source_rejected_atomically(self):
  self.l.transact(init());seed_quotes(self.l);old=self.path.read_bytes()
  for field,value in [('venue','LIVE'),('symbol','SOLUSDT'),('product','CFD')]:
   c=quote('BTCUSDT','2026-02-10T00:01:01Z');c['evidence']['payload'][field]=value;c['evidence']['payload_sha256']=p.sha(c['evidence']['payload'])
   with self.assertRaises(ValueError):self.l.transact(c)
   self.assertEqual(self.path.read_bytes(),old)
  c=decision();c['evidence']['payload']['BTCUSDT'][-1]['received_at']='2026-02-10T00:01:01Z';c['evidence']['payload_sha256']=p.sha(c['evidence']['payload'])
  with self.assertRaises(ValueError):self.l.transact(c)
  self.assertEqual(self.path.read_bytes(),old)
 def test_missing_daily_nav_and_exact_warmup(self):
  buy_both(self.l);r=self.l.transact({'op':'daily','date':'2026-02-11','at':'2026-02-11T00:00:00Z'})
  self.assertIsNone(r['sample']['nav']);self.assertEqual(r['sample']['status'],'UNKNOWN_MARKS')
  samples=[{'date':(date(2026,1,1)+timedelta(days=i)).isoformat(),'nav':D(1000)*(D('1.001')**i)} for i in range(91)]
  self.assertEqual(p.sharpe_status(samples[:90])['status'],'INSUFFICIENT_90_RETURNS');self.assertFalse(p.sharpe_status(samples)['negative'])
  samples[50]['nav']=None;self.assertEqual(p.sharpe_status(samples)['status'],'MISSING_DAILY_MARK')
 def test_no_automatic_kill_reset_after_correction_metadata(self):
  buy_both(self.l)
  for sym in p.SYMBOLS:self.l.transact(quote(sym,'2026-02-10T00:02:00Z','50','50.1'))
  old=self.l.state();r=self.l.transact({'op':'audit','at':'2026-02-10T00:02:01Z','reference_sha256':'a'*64,'details':{'proposed':'reset forbidden'}})
  self.assertEqual(self.l.state()['kill'],old['kill']);self.assertEqual(self.l.state()['cash_total'],old['cash_total']);self.assertEqual(r['status'],'AUDIT_ONLY_NO_BALANCE_EFFECT')
 def test_partial_append_fails_closed_without_truncating_existing_bytes(self):
  self.l.transact(init());before=self.path.read_bytes();real_open=open
  class BrokenWriter:
   def __init__(self,f):self.f=f
   def __enter__(self):return self
   def __exit__(self,*args):self.f.close()
   def write(self,data):self.f.write(bytes(data[:11]));raise OSError('injected interrupted append')
  def selective(file,mode='r',*a,**kw):
   f=real_open(file,mode,*a,**kw)
   return BrokenWriter(f) if Path(file)==self.path and mode=='ab' else f
  with patch('builtins.open',side_effect=selective):
   with self.assertRaises(OSError):self.l.transact({'op':'advance','at':'2026-02-10T00:00:01Z'})
  torn=self.path.read_bytes();self.assertTrue(torn.startswith(before));self.assertGreater(len(torn),len(before))
  with self.assertRaisesRegex(ValueError,'torn'):p.Ledger(self.path).state()
  self.assertEqual(self.path.read_bytes(),torn)
 def test_complete_append_then_fsync_error_retry_does_not_duplicate(self):
  self.l.transact(init());c={'op':'advance','at':'2026-02-10T00:00:01Z'}
  with patch.object(p.os,'fsync',side_effect=OSError('injected uncertain durability')):
   with self.assertRaises(OSError):self.l.transact(c)
  raw=self.path.read_bytes();self.assertEqual(len(raw.splitlines()),2)
  with patch.object(p.os,'fsync',wraps=p.os.fsync) as sync:
   out=p.Ledger(self.path).transact(c)
  self.assertGreaterEqual(sync.call_count,1)
  self.assertEqual(out['status'],'ADVANCED_NO_SYNTHETIC_FILL');self.assertEqual(self.path.read_bytes(),raw)
 def test_reused_core_and_initial_protocol_hash_identity(self):
  self.assertEqual((ROOT/'vendor/paper_cash_accounting.py').read_bytes(),(ROOT.parent/'paper_cash_v1/accounting.py').read_bytes())
  self.assertEqual(hashlib.sha256((ROOT/'PAPER_PROTOCOL_v2_CANDIDATE.md').read_bytes()).hexdigest(),'94a6508600ae50766c7ab9efdd74bb069e41076c575a94f68b0f58f31be5b22c')
 def test_replay_state_and_conflicting_retry_bytes_unchanged(self):
  buy_both(self.l);st=self.l.state();self.assertEqual(p.sha(st),p.sha(p.Ledger(self.path).state()));raw=self.path.read_bytes()
  with self.assertRaises(ValueError):self.l.transact(decision(at='2026-02-10T00:02:00Z'))
  self.assertEqual(self.path.read_bytes(),raw)
if __name__=='__main__':unittest.main(verbosity=2)
