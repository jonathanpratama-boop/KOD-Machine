"""Independent mock-only source/profile checks. No sockets, market reads or orders."""
import sys,copy,tempfile,unittest,hashlib,json,base64,ast,io,urllib.error
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parent.parent/'coinbase_reference_adapter_20261101'
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from mock_fixtures import *
from test_run_once import World,Response
import run_once as run
class Independent(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'j';self.l=c.Ledger(self.path)
 def test_regressed_source_sequence_or_time_rejected_without_mutation(self):
  init(self.l);seed(self.l);decision(self.l);old=self.path.read_bytes()
  for kwargs in ({'sequence':1},{'time':at(.90)}):
   with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):observe(self.l,seconds=3,**kwargs)
   self.assertEqual(self.path.read_bytes(),old)
 def test_equal_sequence_newer_observation_permitted(self):
  init(self.l);seed(self.l);decision(self.l)
  out=observe(self.l,seconds=3,sequence=1010)
  self.assertEqual(len(out['fills']),1)
 def test_timezone_missing_http_date_rejected_not_assumed_local(self):
  r=product();r['headers']['Date']=BASE.astimezone().strftime('%a, %d %b %Y %H:%M:%S')
  with self.assertRaises(ValueError):a.checked_receipt(r)
 def test_raw_receipt_binds_normalized_policy_fields(self):
  original=qe()
  for key,value in [('modeled_ask','1'),('ask_qty','100000'),('quote_currency','USDT'),('source_sequence',0),('profile','BINANCE')]:
   e=copy.deepcopy(original);e['payload'][key]=value;e['payload_sha256']=a.sha(e['payload'])
   with self.subTest(key=key),self.assertRaises(ValueError):a.validate_evidence(e,at(2))
 def test_candle_column_mapping_closed_contiguous_reversed_rows(self):
  r=candles();rows=a.checked_receipt(r)[2];rows[0]=[rows[0][0],50,999,100,111,100]
  p,counts=a.bars_payload([rewrite(r,list(reversed(rows))),candles('ETH-USD')],'2026-10-31',at(2))
  self.assertEqual(p['BTC-USD'][0]['close'],'111');self.assertEqual(len(p['BTC-USD']),40)
  self.assertIsNone(p['BTC-USD'][0]['first_public_at']);self.assertEqual(p['BTC-USD'][0]['available_at'],at(0))
  self.assertEqual(counts['BTC-USD'],0)
  for bad in (rows[:-1],rows+[rows[0]]):
   with self.assertRaises(ValueError):a.bars_payload([rewrite(r,bad),candles('ETH-USD')],'2026-10-31',at(2))
 def test_post_decision_receipt_cannot_relabel_pre_decision_source_or_request(self):
  init(self.l);seed(self.l);decision(self.l)
  out=observe(self.l,seconds=3,time=at(1.99));self.assertEqual(out['fills'],[])
  br=book(seconds=3);br=receipt(br['url'],a.checked_receipt(br)[2],seconds=3,elapsed=1.01)
  rs=[product(),br];e=a.evidence(a.quote_payload(*rs,at(3)),rs,'quote')
  out=self.l.transact({'op':'observe','at':at(3.1),'evidence':e})
  self.assertEqual(out['fills'],[]);self.assertEqual(out['blocked'][0]['reason'],'REFERENCE_OBSERVATION_NOT_POST_INTENT')
 def test_wrong_origin_paths_query_never_reach_transport(self):
  transport=Mock(side_effect=AssertionError('network must not run'))
  client=a.PublicOnceClient(Path(self.tmp.name)/'client',transport=transport)
  for url in ('https://api.exchange.coinbase.com@evil.test/products/BTC-USD','https://api.exchange.coinbase.com/products/BTC-USD%2Forders','https://api.exchange.coinbase.com/products/ETH-USD/book?level=1&auth=x','https://api.exchange.coinbase.com/orders','http://api.exchange.coinbase.com/products/BTC-USD'):
   with self.assertRaises((ValueError,a.StopRoute)):client.get(url)
  transport.assert_not_called()
 def test_401_403_429_and_redirect_status_stop_one_call_no_retry(self):
  for status in (401,403,429,302):
   with self.subTest(status=status):
    raw=b'{"error":"mock refusal"}';headers={'Date':format_datetime(BASE+timedelta(seconds=.1),usegmt=True),'Retry-After':'1'}
    transport=Mock(return_value=Response(raw,headers,status));client=a.PublicOnceClient(Path(self.tmp.name)/str(status),transport=transport,wall=Mock(side_effect=[BASE,BASE+timedelta(seconds=.1),BASE+timedelta(seconds=.2)]),mono=Mock(side_effect=[0,.1]))
    with self.assertRaises(a.StopRoute):client.get(product()['url'])
    with self.assertRaises(a.StopRoute):client.get(product()['url'])
    self.assertEqual(transport.call_count,1);self.assertTrue(client.stopped)
    self.assertEqual((client.folder/'01_response.bin').read_bytes(),raw)
 def test_oversized_response_preserved_bounded_then_stopped(self):
  raw=b' '*1000001;transport=Mock(return_value=Response(raw,{'Date':format_datetime(BASE+timedelta(seconds=.1),usegmt=True)}))
  client=a.PublicOnceClient(Path(self.tmp.name)/'size',transport=transport,wall=Mock(side_effect=[BASE,BASE+timedelta(seconds=.1),BASE+timedelta(seconds=.2)]),mono=Mock(side_effect=[0,.1]))
  with self.assertRaises(a.StopRoute):client.get(product()['url'])
  self.assertTrue(client.stopped);self.assertEqual((client.folder/'01_response.bin').stat().st_size,1000001)
 def test_partial_capture_refusal_keeps_held_paper_state_no_rollback(self):
  class RefuseEighth(World):
   def transport(self,request,timeout):
    if len(self.calls)==7:
     self.calls.append((request.get_method(),request.full_url,dict(request.headers)));self.seconds+=.1
     raise urllib.error.HTTPError(request.full_url,401,'mock refusal',{'Date':format_datetime(self.wall(),usegmt=True)},io.BytesIO(b'{"error":"mock"}'))
    return super().transport(request,timeout)
  w=RefuseEighth();out=run.run_cycle(Path(self.tmp.name)/'cycle',client_factory=w.client,wall=w.wall,sleeper=w.sleep)
  self.assertEqual(len(w.calls),8);self.assertEqual(out['status'],'BLOCKED_REFERENCE_ROUTE_STOPPED');self.assertEqual(out['fill_count'],1)
  self.assertGreater(a.D(out['account_at_final_receipt']['holdings']['BTC-USD']),0);self.assertFalse(out['retry_performed'])
 def test_programmatic_default_capture_requires_clearance_before_transport(self):
  with patch.object(a.PublicOnceClient,'get',side_effect=AssertionError('must not capture')):
   with self.assertRaises(ValueError):run.run_cycle(Path(self.tmp.name)/'no-clearance')
 def test_standard_managed_routing_preserved_no_endpoint_auth_or_netrc(self):
  real=a.urllib.request.build_opener
  with patch('netrc.netrc',side_effect=AssertionError('netrc forbidden')),patch.object(a.urllib.request,'build_opener',wraps=real) as build:
   client=a.PublicOnceClient(Path(self.tmp.name)/'routing')
  self.assertEqual(len(build.call_args.args),2)
  self.assertEqual({type(h) for h in build.call_args.args},{a.NoRedirect,a.NoOriginAuth})
  self.assertFalse(any(isinstance(h,a.urllib.request.ProxyHandler) for h in build.call_args.args))
  handlers=client.transport.__self__.handlers
  self.assertFalse(any(isinstance(h,(a.urllib.request.HTTPBasicAuthHandler,a.urllib.request.HTTPDigestAuthHandler)) for h in handlers))
 def test_original_core_identity_and_unchanged_shared_reducers(self):
  raw=(ROOT/'vendor/paper_candidate_v2_original.py').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),'dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3')
  self.assertEqual(raw,(ROOT.parent/'trend_core_paper_v2_candidate_20261101/paper_candidate.py').read_bytes())
  old={n.name:n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};new={n.name:n for n in ast.parse((ROOT/'paper_reference_core.py').read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  for name in ('account_view','reserve','cancel_pending','kill','liquidations','risk','expire','sharpe_status','Ledger'):
   with self.subTest(name=name):self.assertEqual(ast.dump(old[name]),ast.dump(new[name]))
 def test_actual_synthetic_usdt_journal_cannot_be_opened_as_usd_profile(self):
  sys.path.append(str(ROOT.parent/'trend_core_paper_v2_candidate_20261101'))
  import paper_candidate as old
  journal=Path(self.tmp.name)/'old';old.Ledger(journal).transact({'op':'init','at':at(0),'account_id':'old-synthetic','initial_cash':'1000','mode':'synthetic_spot_only','scenario':a.SCENARIO})
  before=journal.read_bytes()
  with self.assertRaisesRegex(ValueError,'pin mismatch'):c.Ledger(journal).state()
  with self.assertRaisesRegex(ValueError,'pin mismatch'):init(c.Ledger(journal))
  self.assertEqual(journal.read_bytes(),before);self.assertEqual(set(old.Ledger(journal).state()['holdings']),{'BTCUSDT','ETHUSDT'})
 def test_shared_cash_profile_costs_and_mixed_journal_rejection(self):
  init(self.l);seed(self.l);decision(self.l);observe(self.l,seconds=8);observe(self.l,'ETH-USD',8.2)
  st=self.l.state();self.assertEqual(st['cash_total'],a.D(1000)+sum(f['cash_change'] for f in st['fills']));self.assertEqual(st['quote_currency'],'USD')
  for f in st['fills']:
   self.assertEqual(f['fee'],c._core.cash_round(f['quantity']*f['price']*a.D('.01')));self.assertLessEqual(f['quantity'],f['available_quantity'])
  row=json.loads(self.path.read_text().splitlines()[0]);row['provenance']['paper_reference_core.py']='0'*64;row['record_hash']=c._core.event_hash(row);self.path.write_text(json.dumps(row)+'\n')
  with self.assertRaisesRegex(ValueError,'pin mismatch'):self.l.state()
if __name__=='__main__':unittest.main(verbosity=2)
