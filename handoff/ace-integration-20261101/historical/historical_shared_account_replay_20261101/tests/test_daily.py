import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from decimal import Decimal as D
from fixtures_daily import *
class DailyTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.h=tape();self.l=c.Ledger(Path(self.tmp.name)/'events.jsonl')
 def test_signal_weights_exact_v2_and_full_session_delay(self):
  init(self.l,self.h);fill(self.l,self.h,40);d=decide(self.l,self.h);self.assertEqual(d['normalized_targets'],{'BTCUSDT':'0.5','ETHUSDT':'0.5'});self.assertEqual(len(self.l.state()['fills']),0)
  r=fill(self.l,self.h,41);self.assertEqual(sum(len(x['fills']) for x in r),2)
  for f in self.l.state()['fills']:
   self.assertGreater(a.utc(f['model_observed_at']),a.utc(self.l.state()['intents'][0]['made_at']));self.assertEqual(f['capacity_assumption']['source_day'],self.h['BTCUSDT'][39]['day']);self.assertNotIn('bid',f)
 def test_capacity_known_at_creation_and_frozen(self):
  self.h=tape(volume='10');init(self.l,self.h);fill(self.l,self.h,40);decide(self.l,self.h)
  for s in a.SYMBOLS:self.h[s][39]['volume']='1000000000'
  fill(self.l,self.h,41)
  self.assertEqual(self.l.state()['holdings']['BTCUSDT'],D('.01'))
  for o in self.l.state()['intents']:self.assertEqual(o['status'],'IOC_COMPLETE')
  cap=replay.caps(self.h,41,1)
  with self.assertRaises(ValueError):a.validate_capacities(cap,a.moment(self.h['BTCUSDT'][41]['day']))
 def test_atomic_mark_cannot_be_overwritten(self):
  init(self.l,self.h);e,_=mark(self.l,self.h,40);q=copy.deepcopy(e['payload']['BTCUSDT']);q['reference_price']='1';before=self.l.path.read_bytes()
  with self.assertRaisesRegex(ValueError,'atomic batch'):self.l.transact({'op':'observe','at':e['model_available_at'],'evidence':a.evidence(q,e['model_available_at'],SNAPSHOT)})
  self.assertEqual(self.l.path.read_bytes(),before)
 def test_kill_initial_peak_and_later_only_liquidation(self):
  init(self.l,self.h);fill(self.l,self.h,40);decide(self.l,self.h);fill(self.l,self.h,41)
  for s in a.SYMBOLS:self.h[s][42]['open']='50';self.h[s][43]['open']='40'
  r=fill(self.l,self.h,42);st=self.l.state();self.assertEqual(st['kill']['reason'],'DRAWDOWN_AT_LEAST_25_PERCENT');self.assertGreater(st['holdings']['BTCUSDT'],0);self.assertTrue(all(not x['fills'] for x in r));self.assertGreaterEqual(st['peak'],D('10000'))
  fill(self.l,self.h,43);self.assertFalse(any(self.l.state()['holdings'].values()));self.assertIsNotNone(self.l.state()['kill'])
  sells=[f for f in self.l.state()['fills'] if f['side']=='SELL'];self.assertTrue(all(f['price']==D('40')*(1-D('.0005')) for f in sells))
 def test_passive_does_not_refill_partial_entry(self):
  h=tape(volume='1');init(self.l,h,'PASSIVE_50_50_RISK_MATCHED');fill(self.l,h,40);decide(self.l,h);fill(self.l,h,41);qty=self.l.state()['holdings'].copy();fill(self.l,h,42);self.assertEqual(self.l.state()['holdings'],qty)
  with self.assertRaisesRegex(ValueError,'only once'):decide(self.l,h,42)
 def test_conventional_control_explicitly_has_no_kill(self):
  init(self.l,self.h,'CONVENTIONAL_50_50_BUY_HOLD_NO_KILL');fill(self.l,self.h,40);decide(self.l,self.h);fill(self.l,self.h,41)
  for s in a.SYMBOLS:self.h[s][42]['open']='1'
  fill(self.l,self.h,42);self.assertIsNone(self.l.state()['kill']);self.assertGreater(self.l.state()['maximum_observed_drawdown'],D('.9'))
 def test_terminal_plan_cannot_be_moved(self):
  init(self.l,self.h);fill(self.l,self.h,40)
  with self.assertRaisesRegex(ValueError,'terminal'):decide(self.l,self.h,40,True)
 def test_offline_writer_replay_reconciliation_and_terminal_fees(self):
  path=Path(self.tmp.name)/'case.jsonl';r=replay.run_case(self.h,self.h['BTCUSDT'][40]['day'],self.h['BTCUSDT'][-1]['day'],'TREND_V2_SHARED',path,SNAPSHOT)
  self.assertEqual(r['reconciliation'],'PASS');self.assertEqual(r['journal']['replay'],'PASS');self.assertTrue(all(D(v)==0 for v in r['end_account']['holdings'].values()));self.assertGreater(D(r['paid_fees']),0)
  with self.assertRaises(FileExistsError):replay.run_case(self.h,self.h['BTCUSDT'][40]['day'],self.h['BTCUSDT'][-1]['day'],'TREND_V2_SHARED',path,SNAPSHOT)
 def test_cash_control_and_zero_variance_sharpe(self):
  r=replay.run_case(self.h,self.h['BTCUSDT'][40]['day'],self.h['BTCUSDT'][-1]['day'],'CASH',Path(self.tmp.name)/'cash.jsonl',SNAPSHOT)
  self.assertEqual(r['fills'],0);self.assertEqual(r['end_account']['nav'],'10000');self.assertEqual(D(r['growth']),0)
  samples=[{'date':(date(2020,1,1)+timedelta(days=i)).isoformat(),'nav':D(100)} for i in range(91)]
  self.assertEqual(c.sharpe_status(samples)['status'],'ZERO_MEAN_ZERO_VARIANCE')
  samples[-1]['nav']=None;self.assertEqual(c.sharpe_status(samples)['status'],'MISSING_DAILY_MARK')
 def test_no_manufactured_midnight_availability_or_future_tail_effect(self):
  e=a.bars_evidence(self.h,40,SNAPSHOT);at=e['model_available_at'];last=e['payload']['BTCUSDT'][-1]
  last['assumed_available_at']=a.moment((date.fromisoformat(last['day'])+timedelta(days=1)).isoformat());e['payload_sha256']=a.sha(e['payload'])
  with self.assertRaisesRegex(ValueError,'availability'):c.signals(e,self.h['BTCUSDT'][39]['day'],at)
  original=c.signals(a.bars_evidence(self.h,40,SNAPSHOT),self.h['BTCUSDT'][39]['day'],at)
  altered=copy.deepcopy(self.h)
  for symbol in a.SYMBOLS:
   for row in altered[symbol][40:]:row.update(close='99999999',open='99999999',volume='0')
  self.assertEqual(original,c.signals(a.bars_evidence(altered,40,SNAPSHOT),altered['BTCUSDT'][39]['day'],at))
 def test_90_day_sharpe_kill_waits_for_later_open_and_never_resets(self):
  h=tape(n=137)
  for symbol in a.SYMBOLS:
   for i,row in enumerate(h[symbol]):
    if i>=41:row['open']=str(110-(i-41)*.03)
  r=replay.run_case(h,h['BTCUSDT'][40]['day'],h['BTCUSDT'][-1]['day'],'PASSIVE_50_50_RISK_MATCHED',Path(self.tmp.name)/'sharpe.jsonl',SNAPSHOT)
  self.assertEqual(r['kill']['reason'],'NEGATIVE_TRAILING_90_DAY_SHARPE');self.assertGreater(a.utc(r['last_fill']),a.utc(r['kill']['at']));self.assertFalse(any(D(v) for v in r['end_account']['holdings'].values()))
  self.assertLess(D(r['sampled_max_drawdown']),D('.25'));self.assertEqual(r['liquidation']['kill_to_first_fill_days'],1.0);self.assertGreater(r['exposure']['invested_samples'],0)
 def test_zero_variance_negative_returns_and_insufficient_history(self):
  samples=[{'date':(date(2020,1,1)+timedelta(days=i)).isoformat(),'nav':D(100)*D('.999')**i} for i in range(91)]
  self.assertTrue(c.sharpe_status(samples)['negative']);self.assertEqual(c.sharpe_status(samples[:90])['status'],'INSUFFICIENT_90_RETURNS')
 def test_original_v2_bytes_preserved(self):
  expected='dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3'
  self.assertEqual(hashlib.sha256((c.ROOT/'vendor/paper_candidate_v2_original.py').read_bytes()).hexdigest(),expected)
  self.assertEqual(hashlib.sha256((c.ROOT.parent/'trend_core_paper_v2_candidate_20261101/paper_candidate.py').read_bytes()).hexdigest(),expected)
if __name__=='__main__':unittest.main(verbosity=2)
