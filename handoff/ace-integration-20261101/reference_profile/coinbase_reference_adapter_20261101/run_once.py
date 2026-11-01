"""Explicit one-shot GET-only USD reference paper simulation; never schedules/orders."""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
import hashlib,json,os,time
from pathlib import Path
from urllib.parse import urlencode
import adapter as a
import paper_reference_core as c
ROOT=Path(__file__).resolve().parent
PINNED=('ADAPTER_SPEC.md','ADAPTER_ADDENDUM_1.md','ADAPTER_ADDENDUM_2.md','adapter.py','paper_reference_core.py','run_once.py','vendor/paper_cash_accounting.py','vendor/paper_candidate_v2_original.py')
def pins():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PINNED}
def now():return datetime.now(timezone.utc)
def save(path,value):
 with open(path,'x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def validate_clearance(r):
 if r.get('profile')!=a.PROFILE or r.get('approved_for_one_bounded_capture') is not True or r.get('source_pins')!=pins():raise ValueError('independent clearance missing/stale/not approved')
 if not r.get('reviewer') or not r.get('review_report_sha256'):raise ValueError('independent review receipt incomplete')
 return r
def check_clearance(path):return validate_clearance(json.loads(Path(path).read_text()))

def exposure(folder):
 rows=[]
 for path in sorted((folder/'responses').glob('*_receipt.json')):
  rec=json.loads(path.read_text());role,symbol=a.allowed_url(rec['url']);entry={'url':rec['url'],'role':role,'symbol':symbol,'received_at':rec['received_at'],'body_sha256':rec['body_sha256'],'http_status':rec['http_status'],'usage':'prospective_current_reference_input_not_backtest'}
  if role=='candles':
   entry['requested_window']=dict(__import__('urllib.parse',fromlist=['parse_qsl']).parse_qsl(__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(rec['url']).query))
   try:
    body=json.loads(__import__('base64').b64decode(rec['body_base64']));entry['returned_bucket_epochs']=[r[0] for r in body if isinstance(r,list) and len(r)>0]
   except Exception:entry['returned_bucket_epochs']=None
  rows.append(entry)
 return {'profile':a.PROFILE,'sealed_datasets_opened':False,'new_history_warmup_only':True,'inputs':rows}

def run_cycle(output_dir,*,client_factory=a.PublicOnceClient,wall=now,sleeper=time.sleep,review_receipt=None):
 """Dependency injection is for mocks; public CLI requires exact-source review clearance."""
 if client_factory is a.PublicOnceClient:validate_clearance(review_receipt or {})
 folder=Path(output_dir);folder.mkdir(parents=True,exist_ok=False)
 save(folder/'run_manifest.json',{'profile':a.PROFILE,'source_pins':pins(),'started_at':a.stamp(wall()),'mode':'simulation_only_no_real_orders','initial_cash_USD':'1000','scenario':a.SCENARIO,'review_clearance':review_receipt,'maximum_requests':8})
 client=client_factory(folder/'responses');ledger=None;decision=None;counts=None;stage='START';outcome={}
 try:
  end=wall().replace(hour=0,minute=0,second=0,microsecond=0);start=end-timedelta(days=40);signal_date=(end-timedelta(days=1)).date().isoformat()
  products={};stage='PRODUCT_METADATA'
  for symbol in a.PRODUCTS:
   products[symbol]=client.get('https://'+a.HOST+'/products/'+symbol)
   a.product_rules(products[symbol],a.stamp(wall()))
  stage='MINIMAL_WARMUP';bars=[]
  for symbol in a.PRODUCTS:
   url='https://'+a.HOST+'/products/'+symbol+'/candles?'+urlencode({'start':a.stamp(start),'end':a.stamp(end),'granularity':'86400'})
   bars.append(client.get(url))
  p,counts=a.bars_payload(bars,signal_date,a.stamp(wall()));bar_e=a.evidence(p,bars,'bars')
  stage='PRE_DECISION_BOOKS';quotes=[]
  for symbol in a.PRODUCTS:
   book=client.get('https://'+a.HOST+'/products/'+symbol+'/book?level=1')
   q=a.quote_payload(products[symbol],book,a.stamp(wall()));quotes.append(a.evidence(q,[products[symbol],book],'quote'))
  stage='INITIALIZE_REFERENCE_ACCOUNT';ledger=c.Ledger(folder/'paper_reference_ledger.jsonl')
  ledger.transact({'op':'init','at':a.stamp(wall()),'account_id':a.PROFILE+':'+folder.name,'initial_cash':'1000','mode':'coinbase_exchange_usd_reference_simulation','scenario':a.SCENARIO})
  for e in quotes:ledger.transact({'op':'observe','at':a.stamp(wall()),'evidence':e})
  stage='DECISION';decision=ledger.transact({'op':'decision','at':a.stamp(wall()),'signal_date':signal_date,'evidence':bar_e})
  st=ledger.state()
  if any(o['status']=='PENDING' for o in st['intents']):
   stage='POST_DECISION_BOOKS';sleeper(6)
   for symbol in a.PRODUCTS:
    book=client.get('https://'+a.HOST+'/products/'+symbol+'/book?level=1');q=a.quote_payload(products[symbol],book,a.stamp(wall()))
    ledger.transact({'op':'observe','at':a.stamp(wall()),'evidence':a.evidence(q,[products[symbol],book],'quote')})
  outcome={'status':'ONE_SHOT_REFERENCE_CYCLE_RECORDED','stage':'COMPLETE','decision':decision,'out_of_range_candle_counts':counts}
 except Exception as exc:
  # No retry, no alternate source, no fabricated data or rollback of received evidence.
  client.stopped=True
  outcome={'status':'BLOCKED_REFERENCE_ROUTE_STOPPED','stage':stage,'error_type':type(exc).__name__,'error':str(exc),'decision':decision,'out_of_range_candle_counts':counts}
 finally:
  outcome.update(profile=a.PROFILE,finished_at=a.stamp(wall()),requests_attempted=client.count,real_orders=0,scheduled_jobs=0,retry_performed=False)
  if ledger is not None:
   try:
    st=ledger.state();outcome['account_at_final_receipt']=c.wire(c.account_view(st,outcome['finished_at']));outcome['fill_count']=len(st['fills']);outcome['pending_intents']=c.wire([o for o in st['intents'] if o['status']=='PENDING']);outcome['kill']=st['kill']
   except Exception as exc:outcome['account_replay_error']=str(exc)
  else:outcome.update(account_at_final_receipt=None,fill_count=0,pending_intents=[])
  save(folder/'input_exposure.json',exposure(folder));save(folder/'outcome.json',outcome)
 return outcome

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-once',action='store_true');p.add_argument('--review-clearance',type=Path);p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args()
 if not args.public_once or args.review_clearance is None:p.error('default is OFF; --public-once and exact-source independent --review-clearance are required')
 receipt=check_clearance(args.review_clearance)
 result=run_cycle(args.output_dir,review_receipt=receipt);print(json.dumps(result,indent=2));return 0 if result['status']=='ONE_SHOT_REFERENCE_CYCLE_RECORDED' else 2
if __name__=='__main__':raise SystemExit(main())
