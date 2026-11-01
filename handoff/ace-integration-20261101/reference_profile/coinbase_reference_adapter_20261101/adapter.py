"""Coinbase Exchange public USD reference evidence. GET-only, one-shot, no credentials."""
from __future__ import annotations
import base64
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parent
HOST='api.exchange.coinbase.com'
PRODUCTS=('BTC-USD','ETH-USD')
KIND='coinbase_exchange_public_reference'
PROFILE='COINBASE_EXCHANGE_USD_REFERENCE_v1'
SCENARIO={'id':'USD_REFERENCE_ASSUMED_FEE1PCT_SLIP0_1PCT_TAX0_NOT_VENUE_TERMS_v1','fee':'.01','slippage':'.001','precision':8,'quote_max_age_seconds':5,'intent_life_seconds':3600,'daily_grace_seconds':300}
D=Decimal

def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(x):return hashlib.sha256(canon(x).encode()).hexdigest()
def utc(s):
 t=datetime.fromisoformat(s.replace('Z','+00:00'))
 if t.tzinfo is None:raise ValueError('aware UTC timestamp required')
 return t.astimezone(timezone.utc)
def stamp(t):return t.isoformat().replace('+00:00','Z')
def n(x,positive=False):
 if isinstance(x,bool):raise ValueError('boolean is not a price')
 v=D(str(x))
 if not v.is_finite() or v<0 or positive and v<=0:raise ValueError('invalid finite number')
 return v

def allowed_url(url):
 u=urllib.parse.urlsplit(url)
 if u.scheme!='https' or u.netloc!=HOST or u.fragment or u.username or u.password:raise ValueError('unapproved origin')
 parts=u.path.split('/')
 if len(parts) not in (3,4) or parts[1]!='products' or parts[2] not in PRODUCTS:raise ValueError('unapproved public path')
 query=urllib.parse.parse_qs(u.query,strict_parsing=True,keep_blank_values=True)
 if len(parts)==3:
  if query:raise ValueError('product query forbidden')
  return 'product',parts[2]
 if parts[3]=='book' and query=={'level':['1']}:return 'book',parts[2]
 if parts[3]=='candles' and set(query)=={'start','end','granularity'} and query['granularity']==['86400']:
  if any(len(query[k])!=1 for k in query):raise ValueError('duplicate query field')
  a,b=utc(query['start'][0]),utc(query['end'][0])
  if b-a!=timedelta(days=40) or any(t.hour or t.minute or t.second or t.microsecond for t in (a,b)):raise ValueError('only exact 40-day UTC warmup permitted')
  return 'candles',parts[2]
 raise ValueError('unapproved endpoint/query')

def receipt_headers(r):
 pairs=r.get('header_pairs',list(r['headers'].items()));h={}
 for key,value in pairs:
  if not isinstance(key,str) or not isinstance(value,str) or key.lower() in h:raise ValueError('invalid/duplicate response header')
  h[key.lower()]=value
 if 'header_pairs' in r and dict(pairs)!=r['headers']:raise ValueError('response header representation mismatch')
 return h

def header_age_seconds(h):
 if 'age' not in h:return 0  # Unknown cache history; NOT proof of zero cache age.
 value=h['age']
 if not value or any(ch not in '0123456789' for ch in value):raise ValueError('invalid cached response Age')
 return int(value)

def effective_source_age(r,h=None):
 h=receipt_headers(r) if h is None else h
 apparent=max(0,(utc(r['received_at'])-parsedate_to_datetime(h['date']).astimezone(timezone.utc)).total_seconds())
 return max(apparent,header_age_seconds(h)+float(r['monotonic_elapsed_seconds']))

def checked_receipt(r):
 if r['http_status']!=200:raise ValueError('HTTP refusal')
 role,symbol=allowed_url(r['url'])
 raw=base64.b64decode(r['body_base64'],validate=True)
 if hashlib.sha256(raw).hexdigest()!=r['body_sha256']:raise ValueError('raw response hash mismatch')
 start,end=utc(r['request_started_at']),utc(r['received_at'])
 elapsed=float(r['monotonic_elapsed_seconds']);wall=(end-start).total_seconds()
 if not math.isfinite(elapsed) or not 0<=elapsed<=(2 if role=='book' else 5) or wall<0 or abs(wall-elapsed)>.25:raise ValueError('clock jump or response latency')
 h=receipt_headers(r)
 if 'date' not in h:raise ValueError('missing HTTP server clock')
 server=parsedate_to_datetime(h['date'])
 if server.tzinfo is None or server.utcoffset() is None or not h['date'].endswith(' GMT'):raise ValueError('HTTP Date must explicitly identify GMT')
 server=server.astimezone(timezone.utc)
 lag=(end-server).total_seconds();max_age=5 if role=='book' else 300
 if lag < -5 or lag > max_age:raise ValueError('HTTP/server clock or source age mismatch')
 age=header_age_seconds(h)
 if not math.isfinite(age) or age<0 or age>(0 if role=='book' else 300) or effective_source_age(r,h)>max_age:raise ValueError('cached response age')
 if not 0<len(raw)<=1000000:raise ValueError('response size limit')
 def unique_object(pairs):
  obj={}
  for key,value in pairs:
   if key in obj:raise ValueError('duplicate JSON field')
   obj[key]=value
  return obj
 def reject_constant(value):raise ValueError('nonfinite JSON constant')
 return role,symbol,json.loads(raw,object_pairs_hook=unique_object,parse_constant=reject_constant)

class StopRoute(Exception):pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise StopRoute('redirect refused; selected route stopped')

class NoOriginAuth(urllib.request.BaseHandler):
 """Reject origin auth/cookies; leave managed proxy routing/auth untouched."""
 handler_order=499
 def http_request(self,request):
  names={key.lower() for key in list(request.headers)+list(request.unredirected_hdrs)}
  if names & {'authorization','cookie'}:raise StopRoute('origin authentication/cookies forbidden')
  return request
 https_request=http_request

class PublicOnceClient:
 """At most eight GETs; stop permanently on any refusal/error. Does not retry."""
 def __init__(self,folder,*,transport=None,wall=None,mono=None):
  self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
  self.transport=transport or urllib.request.build_opener(NoRedirect(),NoOriginAuth()).open
  self.wall=wall or (lambda:datetime.now(timezone.utc));self.mono=mono or time.monotonic
  self.count=0;self.stopped=False
 def get(self,url):
  if self.stopped or self.count>=8:raise StopRoute('route stopped or eight-request budget exhausted')
  allowed_url(url);self.count+=1
  start=self.wall();tick=self.mono();raw=b'';headers={};status=None;phase='TRANSPORT'
  try:
   request=urllib.request.Request(url,method='GET',headers={'User-Agent':'KOD-Reference-Paper-Research/1.0','Accept':'application/json','Accept-Encoding':'identity','Cache-Control':'no-cache'})
   try:response=self.transport(request,timeout=5)
   except urllib.error.HTTPError as refusal:response=refusal
   with response:
    status=response.status;header_pairs=list(response.headers.items());headers=dict(header_pairs);raw=response.read(1000001)
   end=self.wall();elapsed=self.mono()-tick
   rec={'url':url,'http_status':status,'request_started_at':stamp(start),'received_at':stamp(end),'monotonic_elapsed_seconds':elapsed,'headers':headers,'header_pairs':header_pairs,'body_sha256':hashlib.sha256(raw).hexdigest(),'body_base64':base64.b64encode(raw).decode()}
   phase='LOCAL_EVIDENCE_WRITE';self._save(rec,raw)
   phase='RECEIPT_VALIDATION';checked_receipt(rec)
   return rec
  except Exception as exc:
   self.stopped=True
   diagnostic=str(exc) if phase=='RECEIPT_VALIDATION' else phase+' failed: '+type(exc).__name__+' (transport details omitted to avoid credential logging)'
   error={'phase':phase,'http_status':status,'request_number':self.count,'url':url,'request_started_at':stamp(start),'failed_at':stamp(self.wall()),'status':'ROUTE_STOPPED','error_type':type(exc).__name__,'error':diagnostic,'retry_performed':False,'alternate_host_used':False}
   self._write_new(self.folder/f'{self.count:02d}_error.json',(json.dumps(error,indent=2)+'\n').encode())
   raise StopRoute(diagnostic) from None
 def _write_new(self,path,raw):
  with open(path,'xb') as f:f.write(raw);f.flush();__import__('os').fsync(f.fileno())
  os=__import__('os');fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
 def _save(self,rec,raw):
  self._write_new(self.folder/f'{self.count:02d}_response.bin',raw)
  self._write_new(self.folder/f'{self.count:02d}_receipt.json',(json.dumps(rec,indent=2)+'\n').encode())

def product_rules(r,at):
 role,symbol,p=checked_receipt(r)
 if role!='product' or p.get('id')!=symbol or p.get('base_currency')!=symbol.split('-')[0] or p.get('quote_currency')!='USD':raise ValueError('product identity mismatch')
 age=(utc(at)-utc(r['received_at'])).total_seconds()
 h=receipt_headers(r)
 source_age=effective_source_age(r,h)
 if age<0 or source_age+age>300:raise ValueError('stale product metadata')
 if p.get('status')!='online':raise ValueError('product not online')
 for flag in ('post_only','limit_only','cancel_only','auction_mode','trading_disabled'):
  if p.get(flag) is not False:raise ValueError('unknown/disabled product flag '+flag)
 step,tick,minimum=map(lambda x:n(x,True),(p.get('base_increment'),p.get('quote_increment'),p.get('min_market_funds')))
 if step!=D('0.00000001'):raise ValueError('unsupported quantity step; never default')
 return symbol,{'base_increment':str(step),'quote_increment':str(tick),'min_market_funds':str(minimum),'product_receipt_sha256':sha(r)}

def quote_payload(product,book,at):
 symbol,rules=product_rules(product,at)
 role,s,q=checked_receipt(book)
 if role!='book' or s!=symbol:raise ValueError('book identity mismatch')
 if q.get('auction_mode') is not False:raise ValueError('unknown/indicative auction book')
 if isinstance(q.get('sequence'),bool) or not isinstance(q.get('sequence'),int) or q['sequence']<0:raise ValueError('sequence absent')
 source=utc(q['time']);received=utc(book['received_at'])
 if not 0<=(received-source).total_seconds()<=5:raise ValueError('stale/future book clock')
 if utc(book['received_at'])>utc(at):raise ValueError('future receipt')
 if len(q.get('bids',[]))!=1 or len(q.get('asks',[]))!=1:raise ValueError('exact L1 depth required')
 bid,ask=n(q['bids'][0][0],True),n(q['asks'][0][0],True)
 if ask<bid:raise ValueError('crossed book')
 tick=D(rules['quote_increment'])
 if bid%tick or ask%tick:raise ValueError('price off observed grid')
 def size(side):
  row=q[side][0]
  return None if len(row)<2 or row[1] is None else str(n(row[1])*D('.1'))
 slip=D(SCENARIO['slippage'])
 model_ask=((ask*(1+slip))/tick).to_integral_value(rounding=ROUND_CEILING)*tick
 model_bid=((bid*(1-slip))/tick).to_integral_value(rounding=ROUND_FLOOR)*tick
 if model_bid<=0:raise ValueError('slipped price nonpositive')
 return {'venue':'COINBASE_EXCHANGE_REFERENCE','product':'spot','symbol':symbol,'quote_currency':'USD','profile':PROFILE,
         'observed_at':book['received_at'],'timestamp_basis':'local_first_receipt','source_observed_at':q['time'],'request_started_at':book['request_started_at'],'source_sequence':q['sequence'],
         'bid':str(bid),'ask':str(ask),'bid_qty':size('bids'),'ask_qty':size('asks'),'liquidity_cap_fraction':'0.1',
         'modeled_bid':str(model_bid),'modeled_ask':str(model_ask),'rules':rules,'raw_book_sha256':book['body_sha256']}

def bars_payload(receipts,signal_date,at):
 end=datetime.combine(date.fromisoformat(signal_date)+timedelta(days=1),datetime.min.time(),timezone.utc)
 if end.date()!=utc(at).date():raise ValueError('only latest completed UTC day eligible; no stale-signal backfill')
 start=end-timedelta(days=40);wanted={int((start+timedelta(days=i)).timestamp()) for i in range(40)}
 result={};counts={}
 for r in receipts:
  role,symbol,rows=checked_receipt(r)
  if role!='candles' or symbol in result:raise ValueError('candle source mismatch')
  query=urllib.parse.parse_qs(urllib.parse.urlsplit(r['url']).query)
  if utc(query['start'][0])!=start or utc(query['end'][0])!=end:raise ValueError('warmup URL differs from chosen signal range')
  if utc(r['received_at'])>utc(at):raise ValueError('future candle receipt')
  h=receipt_headers(r)
  if parsedate_to_datetime(h['date']).astimezone(timezone.utc)<end:raise ValueError('response HTTP Date precedes selected final daily close')
  chosen={};outside=0
  if not isinstance(rows,list):raise ValueError('candle rows missing')
  for row in rows:
   if not isinstance(row,list) or len(row)!=6:raise ValueError('unexpected candle schema')
   ts=row[0]
   if isinstance(ts,bool) or not isinstance(ts,int) or ts%86400:raise ValueError('non-daily candle boundary')
   if ts not in wanted:outside+=1;continue
   if ts in chosen:raise ValueError('duplicate daily candle')
   low,high,op,close=map(lambda x:n(x,True),row[1:5]);volume=n(row[5])
   if low>min(op,close) or high<max(op,close) or low>high or volume<=0:raise ValueError('invalid/empty OHLCV')
   if datetime.fromtimestamp(ts,timezone.utc)+timedelta(days=1)>utc(r['received_at']):raise ValueError('unclosed candle')
   day=datetime.fromtimestamp(ts,timezone.utc).date().isoformat();base={'day':day,'close':str(close)}
   chosen[ts]={**base,'first_public_at':None,'available_at':r['received_at'],'received_at':r['received_at'],'source_sha256':sha(base),'raw_response_sha256':r['body_sha256']}
  if set(chosen)!=wanted:raise ValueError('incomplete 40-day contiguous warmup')
  result[symbol]=[chosen[k] for k in sorted(chosen)];counts[symbol]=outside
 if set(result)!=set(PRODUCTS):raise ValueError('both products needed')
 return result,counts

def evidence(payload,receipts,kind):
 return {'kind':KIND,'payload':payload,'received_at':max((r['received_at'] for r in receipts),key=utc),'payload_sha256':sha(payload),'normalization':kind,'receipts':receipts}

def validate_evidence(e,at):
 if set(e)!={'kind','payload','received_at','payload_sha256','normalization','receipts'} or e['kind']!=KIND:raise ValueError('reference evidence kind/schema')
 if sha(e['payload'])!=e['payload_sha256'] or utc(e['received_at'])>utc(at):raise ValueError('payload/future input')
 if e['received_at']!=max((r['received_at'] for r in e['receipts']),key=utc):raise ValueError('receipt chronology mismatch')
 if e['normalization']=='quote':
  if len(e['receipts'])!=2:raise ValueError('metadata+book required')
  expected=quote_payload(*e['receipts'],at)
 elif e['normalization']=='bars':
  signal_date=e['payload'][PRODUCTS[0]][-1]['day']
  expected,_=bars_payload(e['receipts'],signal_date,at)
 else:raise ValueError('unsupported normalization')
 if e['payload']!=expected:raise ValueError('normalization differs from original response bytes')
 return expected
