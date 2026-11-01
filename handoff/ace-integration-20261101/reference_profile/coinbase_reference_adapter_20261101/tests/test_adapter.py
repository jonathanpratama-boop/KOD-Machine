import copy, io, json, tempfile, unittest, urllib.error
from pathlib import Path
from unittest.mock import Mock,patch
from mock_fixtures import *

class AdapterTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.ledger=c.Ledger(Path(self.tmp.name)/'ledger.jsonl')
 def test_origin_and_endpoint_allowlist(self):
  for url in ['https://api.exchange.coinbase.com/orders','https://api.exchange.coinbase.com/accounts','https://api.exchange.coinbase.com/products/BTC-USD?x=','https://evil.test/products/BTC-USD','http://api.exchange.coinbase.com/products/BTC-USD','https://api.exchange.coinbase.com/products/BTC-USD/book?level=2']:
   with self.subTest(url=url),self.assertRaises(ValueError):a.allowed_url(url)
 def test_receipt_hash_clock_cache(self):
  base=product()
  for key,value in [('body_sha256','0'*64),('monotonic_elapsed_seconds',2.1),('received_at',at(10))]:
   r=copy.deepcopy(base);r[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):a.checked_receipt(r)
  for header,value in [('Age','301'),('Age','nan'),('Date','Sun, 01 Nov 2026 00:00:00 GMT'),('Date','Sun, 01 Nov 2026 19:00:00'),('Date','Sun, 01 Nov 2026 12:00:00 +0000')]:
   r=copy.deepcopy(base);r['headers'][header]=value
   with self.subTest(header=header,value=value),self.assertRaises(ValueError):a.checked_receipt(r)
 def test_endpoint_specific_latency_cache_and_effective_metadata_age(self):
  obj=a.checked_receipt(product())[2]
  r=receipt(product()['url'],obj,seconds=0,elapsed=3)
  r['headers']['Age']='120';r['headers']['Date']=format_datetime(BASE-timedelta(seconds=120),usegmt=True)
  a.checked_receipt(r);a.product_rules(r,at(176))
  with self.assertRaisesRegex(ValueError,'stale product'):a.product_rules(r,at(178))
  br=book();br['headers']['Age']='1'
  with self.assertRaisesRegex(ValueError,'cached'):a.checked_receipt(br)
  br=receipt(book()['url'],a.checked_receipt(book())[2],seconds=1,elapsed=3)
  with self.assertRaisesRegex(ValueError,'latency'):a.checked_receipt(br)
  cr=candles();cr['headers']['Age']='120';cr['headers']['Date']=format_datetime(BASE-timedelta(seconds=120),usegmt=True)
  p,_=a.bars_payload([cr,candles('ETH-USD')],'2026-10-31',at(2));self.assertEqual(len(p['BTC-USD']),40)
 def test_cached_preclose_response_cannot_be_mislabeled_closed(self):
  cr=candles();raw=a.checked_receipt(cr)[2];midnight=BASE.replace(hour=0)
  end=midnight+timedelta(seconds=1)
  cr['received_at']=a.stamp(end);cr['request_started_at']=a.stamp(end-timedelta(seconds=.1))
  cr['headers']['Date']=format_datetime(midnight-timedelta(seconds=1),usegmt=True)
  with self.assertRaisesRegex(ValueError,'precedes selected final daily close'):
   a.bars_payload([cr,candles('ETH-USD')],'2026-10-31',at(2))
 def test_duplicate_headers_and_response_delay_age(self):
  r=product();r['headers']['date']=r['headers']['Date']
  with self.assertRaisesRegex(ValueError,'duplicate'):a.checked_receipt(r)
  r=product();r['header_pairs']=[('Date',r['headers']['Date']),('Date',r['headers']['Date'])]
  with self.assertRaisesRegex(ValueError,'duplicate'):a.checked_receipt(r)
  r=product();r['headers']['Age']='299.95'
  with self.assertRaisesRegex(ValueError,'cached'):a.checked_receipt(r)
  r=product();r['headers']['Age']='-1'
  with self.assertRaisesRegex(ValueError,'cached'):a.checked_receipt(r)
 def test_product_unknowns_block(self):
  for change in [{'status':'offline'},{'quote_currency':'USDT'},{'base_increment':'0.000001'},{'min_market_funds':None},{'auction_mode':True},{'trading_disabled':None}]:
   with self.subTest(change=change),self.assertRaises((ValueError,ArithmeticError)):a.product_rules(product(**change),at(1))
  with self.assertRaises(ValueError):a.product_rules(product(),at(301))
 def test_book_identity_quantity_tick_and_source_clock(self):
  q=a.quote_payload(product(),book(size='2'),at(1));self.assertEqual(q['ask_qty'],'0.2');self.assertEqual(q['modeled_ask'],'100.13');self.assertEqual(q['modeled_bid'],'99.90')
  q=a.quote_payload(product(),book(size=None),at(1));self.assertIsNone(q['ask_qty'])
  for change in [{'time':at(-5)},{'time':at(2)},{'auction_mode':None},{'sequence':None},{'bids':[['100.001','2',2]]}]:
   with self.subTest(change=change),self.assertRaises(ValueError):a.quote_payload(product(),book(**change),at(1))
 def test_warmup_no_publication_claim_and_bars_are_latest(self):
  e=be();p=a.validate_evidence(e,at(2));self.assertEqual(len(p['BTC-USD']),40);self.assertIsNone(p['BTC-USD'][0]['first_public_at']);self.assertEqual(p['BTC-USD'][0]['available_at'],at(0))
  with self.assertRaises(ValueError):a.validate_evidence(e,'2026-11-02T12:00:00Z')
 def test_gaps_duplicates_empty_bars(self):
  orig=candles();rows=a.checked_receipt(orig)[2]
  for bad in [rows[:-1],rows+[rows[0]],[[*rows[0][:-1],0]]+rows[1:]]:
   with self.assertRaises(ValueError):a.bars_payload([rewrite(orig,bad),candles('ETH-USD')],'2026-10-31',at(2))
  extra=copy.deepcopy(rows[0]);extra[0]-=86400
  p,counts=a.bars_payload([rewrite(orig,rows+[extra]),candles('ETH-USD')],'2026-10-31',at(2));self.assertEqual(counts['BTC-USD'],1)
 def test_payload_cannot_relabel_or_modify_raw_data(self):
  e=qe();e['payload']['ask']='1';e['payload_sha256']=a.sha(e['payload'])
  with self.assertRaises(ValueError):a.validate_evidence(e,at(2))
  e=qe();e['kind']='synthetic'
  with self.assertRaises(ValueError):a.validate_evidence(e,at(2))
 def test_shared_cash_actual_future_quote_fill_and_replay(self):
  init(self.ledger);seed(self.ledger);d=decision(self.ledger);self.assertEqual(d['normalized_targets'],{'BTC-USD':'0.5','ETH-USD':'0.5'})
  command={'op':'observe','at':at(8),'evidence':qe('BTC-USD',8)}
  r=self.ledger.transact(command);self.assertEqual(len(r['fills']),1);self.assertEqual(r,self.ledger.transact(command))
  observe(self.ledger,'ETH-USD',8.2);st=self.ledger.state();self.assertGreaterEqual(st['cash_total'],0);self.assertLessEqual(c.account_view(st,at(8.2))['gross_fraction'],1);self.assertEqual(st['quote_currency'],'USD');self.assertEqual(len(st['fills']),2)
 def test_no_fill_past_source_or_request_unknown_size_or_minimum(self):
  init(self.ledger);seed(self.ledger);decision(self.ledger)
  r=observe(self.ledger,seconds=3,time=at(1.99));self.assertEqual(r['blocked'][0]['reason'],'REFERENCE_OBSERVATION_NOT_POST_INTENT')
  r=observe(self.ledger,seconds=4,size=None);self.assertEqual(r['blocked'][0]['reason'],'UNKNOWN_LIQUIDITY')
  r=observe(self.ledger,seconds=5,size='0.001');self.assertEqual(r['blocked'][0]['reason'],'MIN_MARKET_FUNDS');self.assertEqual(r['fills'],[]);self.assertEqual(self.ledger.state()['holdings']['BTC-USD'],0)
 def test_regressing_source_sequence_or_time_fails_closed(self):
  init(self.ledger);seed(self.ledger);decision(self.ledger)
  prior=self.ledger.path.read_bytes()
  with self.assertRaisesRegex(ValueError,'regressing source'):observe(self.ledger,seconds=3,sequence=1)
  with self.assertRaisesRegex(ValueError,'regressing source'):observe(self.ledger,seconds=3,time=at(.9))
  self.assertEqual(self.ledger.path.read_bytes(),prior)
  # An unchanged sequence with a genuinely newer snapshot time is allowed.
  r=observe(self.ledger,seconds=3,sequence=1010);self.assertEqual(len(r['fills']),1)
 def test_pending_buy_blocked_unknown_other_mark(self):
  init(self.ledger);seed(self.ledger);decision(self.ledger);observe(self.ledger,seconds=8)
  r=observe(self.ledger,'ETH-USD',14);self.assertEqual(r['blocked'][0]['reason'],'UNKNOWN_AGGREGATE_NAV_AT_FILL');self.assertIsNone(r['account']['nav'])
 def test_cash_signal_does_not_force_trade(self):
  init(self.ledger);seed(self.ledger);r=decision(self.ledger,False);self.assertEqual(r['normalized_targets'],{'BTC-USD':'0','ETH-USD':'0'});self.assertEqual(self.ledger.state()['intents'],[])
 def test_http_refusal_preserved_stops_without_retry(self):
  headers={'Date':'Sun, 01 Nov 2026 12:00:00 GMT'}
  transport=Mock(side_effect=urllib.error.HTTPError(product()['url'],403,'Forbidden',headers,io.BytesIO(b'{"error":"forbidden"}')))
  wall=Mock(side_effect=[BASE,BASE+timedelta(seconds=.1),BASE+timedelta(seconds=.2)])
  client=a.PublicOnceClient(Path(self.tmp.name)/'http',transport=transport,wall=wall,mono=Mock(side_effect=[0,.1]))
  with self.assertRaises(a.StopRoute):client.get(product()['url'])
  with self.assertRaises(a.StopRoute):client.get(product()['url'])
  self.assertEqual(transport.call_count,1);self.assertEqual((client.folder/'01_response.bin').read_bytes(),b'{"error":"forbidden"}');self.assertTrue((client.folder/'01_error.json').exists())
 def test_default_transport_preserves_managed_routing_and_blocks_origin_auth(self):
  with patch('adapter.urllib.request.build_opener') as builder:
   a.PublicOnceClient(Path(self.tmp.name)/'direct')
  handlers=builder.call_args.args
  self.assertIsInstance(handlers[0],a.NoRedirect);self.assertIsInstance(handlers[1],a.NoOriginAuth)
  self.assertFalse(any(isinstance(h,a.urllib.request.ProxyHandler) for h in handlers))
  for key in ('Authorization','Cookie'):
   request=a.urllib.request.Request(product()['url'],headers={key:'fabricated-test-value'})
   with self.assertRaises(a.StopRoute):a.NoOriginAuth().http_request(request)
  request=a.urllib.request.Request(product()['url'],headers={'Proxy-Authorization':'fabricated-managed-route-test'})
  self.assertIs(a.NoOriginAuth().http_request(request),request)
 def test_transport_errors_do_not_echo_possible_ambient_credentials(self):
  transport=Mock(side_effect=urllib.error.URLError('https://fake-user:fake-secret@mock-proxy.invalid'))
  client=a.PublicOnceClient(Path(self.tmp.name)/'redacted',transport=transport,wall=lambda:BASE,mono=lambda:0)
  with self.assertRaises(a.StopRoute) as ctx:client.get(product()['url'])
  self.assertNotIn('fake-secret',str(ctx.exception));self.assertNotIn('fake-secret',(client.folder/'01_error.json').read_text())
 def test_redirect_refused(self):
  with self.assertRaises(a.StopRoute):a.NoRedirect().redirect_request(None,None,302,'Found',{},'https://elsewhere.example')
 def test_original_core_and_synthetic_default_unchanged(self):
  expected='dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3'
  self.assertEqual(hashlib.sha256((a.ROOT/'vendor/paper_candidate_v2_original.py').read_bytes()).hexdigest(),expected)
  original=a.ROOT.parent/'trend_core_paper_v2_candidate_20261101/paper_candidate.py'
  self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),expected)
  with self.assertRaises(ValueError):self.ledger.transact({'op':'init','at':at(0),'account_id':'bad','initial_cash':'1000','mode':'synthetic_spot_only','scenario':a.SCENARIO})
if __name__=='__main__':unittest.main(verbosity=2)
