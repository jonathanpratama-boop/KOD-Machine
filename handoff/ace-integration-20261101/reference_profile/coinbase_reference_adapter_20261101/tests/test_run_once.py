import json,tempfile,unittest,io,urllib.error
from pathlib import Path
from mock_fixtures import *
import run_once as run

class Response:
 def __init__(self,raw,headers,status=200):self.raw=raw;self.headers=headers;self.status=status
 def read(self,limit):return self.raw[:limit]
 def __enter__(self):return self
 def __exit__(self,*args):pass
class World:
 def __init__(self,rising=True,refuse=False):self.seconds=0.;self.rising=rising;self.refuse=refuse;self.calls=[]
 def wall(self):return BASE+timedelta(seconds=self.seconds)
 def mono(self):return self.seconds
 def sleep(self,seconds):self.seconds+=seconds
 def transport(self,request,timeout):
  self.calls.append((request.get_method(),request.full_url,dict(request.headers)));self.seconds+=.1
  role,symbol=a.allowed_url(request.full_url)
  if self.refuse:raise urllib.error.HTTPError(request.full_url,403,'Forbidden',{'Date':format_datetime(self.wall(),usegmt=True)},io.BytesIO(b'{"error":"refused"}'))
  if role=='product':r=product(symbol,self.seconds)
  elif role=='candles':r=candles(symbol,self.seconds,self.rising)
  else:r=book(symbol,self.seconds)
  return Response(base64.b64decode(r['body_base64']),r['headers'])
 def client(self,folder):return a.PublicOnceClient(folder,transport=self.transport,wall=self.wall,mono=self.mono)

class OneShotTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)/'cycle'
 def test_full_mock_cycle_8_gets_and_no_backfill(self):
  w=World();r=run.run_cycle(self.folder,client_factory=w.client,wall=w.wall,sleeper=w.sleep)
  self.assertEqual(r['status'],'ONE_SHOT_REFERENCE_CYCLE_RECORDED');self.assertEqual(r['fill_count'],2);self.assertEqual(len(w.calls),8);self.assertTrue(all(x[0]=='GET' for x in w.calls));self.assertTrue(all('Authorization' not in x[2] for x in w.calls))
  st=c.Ledger(self.folder/'paper_reference_ledger.jsonl').state()
  for f in st['fills']:self.assertGreater(a.utc(f['observed_at']),a.utc(r['decision']['account'].get('made_at',at(.6))))
  e=json.loads((self.folder/'input_exposure.json').read_text());bars=[x for x in e['inputs'] if x['role']=='candles'];self.assertEqual(len(bars),2);self.assertEqual(len(bars[0]['returned_bucket_epochs']),40)
  self.assertEqual(st['peak'],a.D('1000'));self.assertEqual(len(st['daily']),0)
 def test_cash_cycle_only_6_gets(self):
  w=World(False);r=run.run_cycle(self.folder,client_factory=w.client,wall=w.wall,sleeper=w.sleep)
  self.assertEqual(r['status'],'ONE_SHOT_REFERENCE_CYCLE_RECORDED');self.assertEqual(r['fill_count'],0);self.assertEqual(len(w.calls),6);self.assertEqual(r['pending_intents'],[]);self.assertEqual(r['account_at_final_receipt']['nav'],'1000')
 def test_refused_source_one_request_no_account_no_retry(self):
  w=World(refuse=True);r=run.run_cycle(self.folder,client_factory=w.client,wall=w.wall,sleeper=w.sleep)
  self.assertEqual(r['status'],'BLOCKED_REFERENCE_ROUTE_STOPPED');self.assertEqual(len(w.calls),1);self.assertIsNone(r['account_at_final_receipt']);self.assertEqual(r['fill_count'],0);self.assertFalse((self.folder/'paper_reference_ledger.jsonl').exists())
 def test_directory_cannot_be_reused_to_recapture(self):
  self.folder.mkdir();w=World()
  with self.assertRaises(FileExistsError):run.run_cycle(self.folder,client_factory=w.client,wall=w.wall,sleeper=w.sleep)
  self.assertEqual(w.calls,[])
 def test_default_programmatic_path_requires_clearance_without_network(self):
  with self.assertRaisesRegex(ValueError,'clearance'):run.run_cycle(self.folder)
  self.assertFalse(self.folder.exists())
 def test_transport_budget_hard_limit_eight(self):
  w=World();client=w.client(Path(self.tmp.name)/'budget')
  for _ in range(8):client.get(product()['url'])
  with self.assertRaises(a.StopRoute):client.get(product()['url'])
  self.assertEqual(len(w.calls),8)
 def test_review_clearance_must_match_every_source_pin(self):
  f=Path(self.tmp.name)/'clearance.json';valid={'profile':a.PROFILE,'approved_for_one_bounded_capture':True,'source_pins':run.pins(),'reviewer':'mock-only','review_report_sha256':'a'*64};f.write_text(json.dumps(valid));self.assertEqual(run.check_clearance(f),valid)
  valid['source_pins']['adapter.py']='0'*64;f.write_text(json.dumps(valid))
  with self.assertRaises(ValueError):run.check_clearance(f)
if __name__=='__main__':unittest.main(verbosity=2)
