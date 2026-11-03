"""Independent synthetic-only replay audit. Never loads historical archive rows."""
import sys,copy,tempfile,unittest,json,hashlib
from pathlib import Path
from decimal import Decimal as D
ROOT=Path(__file__).resolve().parent.parent/'historical_shared_account_replay_20261101'
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from fixtures_daily import *
class Independent(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.h=tape();self.l=c.Ledger(Path(self.tmp.name)/'ledger')
 def run_case(self,h,name,policy='TREND_V2_SHARED'):
  return replay.run_case(h,h['BTCUSDT'][40]['day'],h['BTCUSDT'][-1]['day'],policy,Path(self.tmp.name)/name,SNAPSHOT)
 def test_future_open_gap_changes_quantity_not_frozen_buy_budget(self):
  init(self.l,self.h);fill(self.l,self.h,40);decide(self.l,self.h);old=self.l.state();self.assertEqual(sum(o['reserved'] for o in old['intents']),D('10000'))
  for s in a.SYMBOLS:self.h[s][41]['open']='200'
  fill(self.l,self.h,41);st=self.l.state()
  for f in st['fills']:
   self.assertEqual(f['price'],D('200.1'));self.assertLessEqual(-f['cash_change'],D('5000'));self.assertLess(f['quantity'],D('25'))
  self.assertGreaterEqual(st['cash_total'],0);self.assertLessEqual(c.account_view(st,st['clock'])['gross_fraction'],1)
 def test_terminal_capacity_residual_is_not_forced_flat(self):
  for s in a.SYMBOLS:self.h[s][-3]['volume']='1'
  r=self.run_case(self.h,'residual','CONVENTIONAL_50_50_BUY_HOLD_NO_KILL')
  self.assertTrue(all(D(x)>0 for x in r['end_account']['holdings'].values()))
  st=c.Ledger(Path(self.tmp.name)/'residual').state();sells=[f for f in st['fills'] if f['side']=='SELL'];self.assertEqual(len(sells),2)
  self.assertTrue(all(f['quantity']==D('.001') for f in sells));self.assertEqual(r['reconciliation'],'PASS')
 def test_terminal_close_volume_and_later_rows_never_affect_result(self):
  h2=copy.deepcopy(self.h)
  for s in a.SYMBOLS:h2[s][-1]['close']='999999';h2[s][-1]['volume']='0'
  r1=self.run_case(self.h,'a');r2=self.run_case(h2,'b');self.assertEqual(r1,r2)
  self.assertEqual((Path(self.tmp.name)/'a').read_bytes(),(Path(self.tmp.name)/'b').read_bytes())
 def test_fixed_availability_cannot_be_moved_to_midnight(self):
  e=a.bars_evidence(self.h,40,SNAPSHOT);day=self.h['BTCUSDT'][40]['day']
  for rows in e['payload'].values():rows[-1]['assumed_available_at']=a.moment(day)
  e['model_available_at']=a.moment(day);e['payload_sha256']=a.sha(e['payload'])
  with self.assertRaises(ValueError):c.signals(e,self.h['BTCUSDT'][39]['day'],a.moment(day))
 def test_input_snapshot_mix_and_atomic_missing_mark_reject(self):
  init(self.l,self.h);e,_=mark(self.l,self.h,40);before=self.l.path.read_bytes()
  e['input_snapshot_sha256']='b'*64
  with self.assertRaises(ValueError):self.l.transact({'op':'observe','at':e['model_available_at'],'evidence':e})
  self.assertEqual(self.l.path.read_bytes(),before)
  day=self.h['BTCUSDT'][41]['day'];e=a.open_evidence(day,{s:self.h[s][41] for s in a.SYMBOLS},SNAPSHOT);del e['payload']['ETHUSDT'];e['payload_sha256']=a.sha(e['payload'])
  with self.assertRaises(ValueError):self.l.transact({'op':'mark_batch','at':a.moment(day),'evidence':e,'capacities':replay.caps(self.h,41,2)})
  self.assertEqual(self.l.path.read_bytes(),before)
 def test_missing_current_marks_propagate_unknown_nav(self):
  init(self.l,self.h);fill(self.l,self.h,40);decide(self.l,self.h);fill(self.l,self.h,41)
  day=self.h['BTCUSDT'][42]['day'];r=self.l.transact({'op':'daily','at':a.moment(day),'date':day})
  self.assertIsNone(r['sample']['nav']);self.assertEqual(r['sample']['status'],'UNKNOWN_MARKS')
 def test_cash_fees_and_holdings_reconcile_independently(self):
  self.run_case(self.h,'money');st=c.Ledger(Path(self.tmp.name)/'money').state();cash=D('10000');hold=dict.fromkeys(a.SYMBOLS,D(0));fees=D(0)
  for f in st['fills']:
   q,p=f['quantity'],f['price'];fee=(q*p*D('.001')).quantize(D('.01'),rounding='ROUND_HALF_UP');self.assertEqual(fee,f['fee']);fees+=fee
   cash+=(-q*p-fee) if f['side']=='BUY' else (q*p-fee);hold[f['symbol']]+=q if f['side']=='BUY' else -q
   self.assertGreaterEqual(cash,0)
  self.assertEqual((cash,hold,fees),(st['cash_total'],st['holdings'],st['realized_fees']))
 def test_kill_residual_capacity_is_frozen_and_never_same_open(self):
  init(self.l,self.h);fill(self.l,self.h,40);decide(self.l,self.h);fill(self.l,self.h,41)
  for s in a.SYMBOLS:self.h[s][40]['volume']='1';self.h[s][42]['open']='50';self.h[s][43]['open']='40'
  fill(self.l,self.h,42);st=self.l.state();self.assertIsNotNone(st['kill']);self.assertEqual(len(st['fills']),2)
  fill(self.l,self.h,43);st=self.l.state();sells=[f for f in st['fills'] if f['side']=='SELL'];self.assertEqual([f['quantity'] for f in sells],[D('.001')]*2)
  self.assertTrue(any(st['holdings'].values()));self.assertTrue(all(o['made_at']==a.moment(self.h['BTCUSDT'][43]['day']) for o in st['intents'] if o['status']=='PENDING'))
 def test_sharpe_requires_91_clean_samples_and_missing_resets(self):
  samples=[{'date':(date(2020,1,1)+timedelta(days=i)).isoformat(),'nav':D(100)-D(i)/10} for i in range(91)]
  self.assertFalse(c.sharpe_status(samples[:90])['negative']);self.assertTrue(c.sharpe_status(samples)['negative'])
  samples[50]['nav']=None;self.assertFalse(c.sharpe_status(samples)['negative'])
 def test_signal_and_sharpe_parity_with_original_v2(self):
  import importlib.util
  path=ROOT.parent/'trend_core_paper_v2_candidate_20261101'/'paper_candidate.py'
  spec=importlib.util.spec_from_file_location('audited_original_v2',path);original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
  self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3')
  self.assertEqual(hashlib.sha256((ROOT/'vendor/paper_cash_accounting.py').read_bytes()).hexdigest(),'29688797f6738e4aa02ca87403a5a90d60dec0bca54cffab36a4a4a7e266f8a6')
  e=a.bars_evidence(self.h,40,SNAPSHOT);p=copy.deepcopy(e['payload'])
  for rows in p.values():
   for bar in rows:bar['published_at']=bar.pop('assumed_available_at');bar['received_at']=bar['published_at']
  legacy=original.evidence(p,e['model_available_at']);day=self.h['BTCUSDT'][39]['day'];at=e['model_available_at']
  self.assertEqual(c.signals(e,day,at),original.signals(legacy,day,at))
  import ast
  def node(file,name):return ast.dump(next(x for x in ast.parse(file.read_text()).body if isinstance(x,ast.FunctionDef) and x.name==name),include_attributes=False)
  for name in ('reserve','cancel_pending','sharpe_status'):
   self.assertEqual(node(ROOT/'daily_core.py',name),node(path,name))
 def test_sell_quantity_frozen_at_decision_despite_later_price(self):
  init(self.l,self.h);fill(self.l,self.h,40);decide(self.l,self.h);fill(self.l,self.h,41)
  self.h['BTCUSDT'][42]['open']='200';fill(self.l,self.h,42);decide(self.l,self.h,42)
  pending=[o for o in self.l.state()['intents'] if o['status']=='PENDING' and o['side']=='SELL'];self.assertEqual(len(pending),1);o=pending[0]
  self.h['BTCUSDT'][43]['open']='300';fill(self.l,self.h,43)
  f=next(f for f in self.l.state()['fills'] if f['intent_id']==o['id'])
  self.assertEqual(f['quantity'],o['quantity'].quantize(D('.00000001'),rounding='ROUND_FLOOR'));self.assertEqual(f['price'],D('299.85'))
 def test_duplicate_retry_and_conflict_cannot_duplicate_decision(self):
  init(self.l,self.h);fill(self.l,self.h,40);r=decide(self.l,self.h);before=self.l.path.read_bytes()
  self.assertEqual(decide(self.l,self.h),r);self.assertEqual(self.l.path.read_bytes(),before)
  altered=copy.deepcopy(self.h);altered['BTCUSDT'][39]['close']='999'
  with self.assertRaises(ValueError):decide(self.l,altered)
  self.assertEqual(self.l.path.read_bytes(),before)
 def test_torn_or_tampered_offline_journal_is_not_silently_recovered(self):
  self.run_case(self.h,'valid');p=Path(self.tmp.name)/'valid';raw=p.read_bytes()
  torn=Path(self.tmp.name)/'torn';torn.write_bytes(raw[:-20])
  with self.assertRaises((ValueError,json.JSONDecodeError)):c.Ledger(torn).state()
  lines=raw.splitlines();row=json.loads(lines[1]);row['state_sha256']='0'*64;lines[1]=json.dumps(row).encode();bad=Path(self.tmp.name)/'bad';bad.write_bytes(b'\n'.join(lines)+b'\n')
  with self.assertRaises(ValueError):c.Ledger(bad).state()
 def test_terminal_reporting_does_not_relabel_kill_intents(self):
  for symbol in a.SYMBOLS:
   for row in self.h[symbol][42:]:row['open']='40'
  self.run_case(self.h,'kill');st=c.Ledger(Path(self.tmp.name)/'kill').state()
  self.assertIsNotNone(st['kill'])
  for o in st['intents']:
   if o.get('reason')=='PERSISTENT_KILL':o['made_at']=st['terminal_decision_at']
  r=replay.metrics(st,D(0),[D(0)]*len(st['daily']))
  self.assertGreater(r['liquidation']['kill_fill_count'],0);self.assertEqual(r['liquidation']['preplanned_terminal_fill_count'],0)
if __name__=='__main__':unittest.main(verbosity=2)
