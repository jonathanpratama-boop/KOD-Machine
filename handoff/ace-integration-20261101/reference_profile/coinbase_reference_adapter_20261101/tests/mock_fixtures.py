"""Invented schema-conformant inputs only. Not real market data."""
import base64, hashlib, json, sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import adapter as a
import paper_reference_core as c
BASE=datetime(2026,11,1,12,tzinfo=timezone.utc)
def at(seconds):return a.stamp(BASE+timedelta(seconds=seconds))
def receipt(url,obj,seconds=0,elapsed=.1):
 end=BASE+timedelta(seconds=seconds);raw=json.dumps(obj,separators=(',',':')).encode()
 return {'url':url,'http_status':200,'request_started_at':a.stamp(end-timedelta(seconds=elapsed)),'received_at':a.stamp(end),'monotonic_elapsed_seconds':elapsed,'headers':{'Date':format_datetime(end,usegmt=True)},'body_sha256':hashlib.sha256(raw).hexdigest(),'body_base64':base64.b64encode(raw).decode()}
def rewrite(r,obj):return receipt(r['url'],obj,(a.utc(r['received_at'])-BASE).total_seconds())
def product(symbol='BTC-USD',seconds=0,**changes):
 obj={'id':symbol,'base_currency':symbol.split('-')[0],'quote_currency':'USD','status':'online','base_increment':'0.00000001','quote_increment':'0.01','min_market_funds':'1','post_only':False,'limit_only':False,'cancel_only':False,'auction_mode':False,'trading_disabled':False};obj.update(changes)
 return receipt('https://'+a.HOST+'/products/'+symbol,obj,seconds)
def book(symbol='BTC-USD',seconds=1,price='100',size='100',**changes):
 obj={'sequence':1000+int(seconds*10),'time':at(seconds-.05),'auction_mode':False,'bids':[[price,size,3]],'asks':[[str(a.D(price)+a.D('.02')),size,4]]};obj.update(changes)
 return receipt('https://'+a.HOST+'/products/'+symbol+'/book?level=1',obj,seconds)
def candles(symbol='BTC-USD',seconds=0,rising=True):
 end=BASE.replace(hour=0);start=end-timedelta(days=40);rows=[]
 for i in range(40):
  price=100+i+(i%3)*.1 if rising else 140-i+(i%3)*.1
  rows.append([int((start+timedelta(days=i)).timestamp()),price-1,price+1,price,price,100])
 url='https://'+a.HOST+'/products/'+symbol+'/candles?'+urlencode({'start':a.stamp(start),'end':a.stamp(end),'granularity':'86400'})
 return receipt(url,rows,seconds)
def qe(symbol='BTC-USD',seconds=1,**kwargs):
 rs=[product(symbol),book(symbol,seconds,**kwargs)];p=a.quote_payload(*rs,at(seconds));return a.evidence(p,rs,'quote')
def be(rising=True):
 rs=[candles(s,rising=rising) for s in a.PRODUCTS];p,_=a.bars_payload(rs,'2026-10-31',at(2));return a.evidence(p,rs,'bars')
def init(ledger,cash='1000'):
 return ledger.transact({'op':'init','at':at(0),'account_id':'mock-account','initial_cash':cash,'mode':'coinbase_exchange_usd_reference_simulation','scenario':a.SCENARIO})
def seed(ledger):
 for i,s in enumerate(a.PRODUCTS):ledger.transact({'op':'observe','at':at(1+i*.1),'evidence':qe(s,1+i*.1)})
def decision(ledger,rising=True):return ledger.transact({'op':'decision','at':at(2),'signal_date':'2026-10-31','evidence':be(rising)})
def observe(ledger,s='BTC-USD',seconds=8,**kwargs):return ledger.transact({'op':'observe','at':at(seconds),'evidence':qe(s,seconds,**kwargs)})
