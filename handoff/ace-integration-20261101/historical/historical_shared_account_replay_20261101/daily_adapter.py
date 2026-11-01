"""Daily historical modeling adapter; NO network, BBO or claimed public receipt time."""
from datetime import datetime,date,timedelta,timezone
from decimal import Decimal
import hashlib,json,math
D=Decimal;UTC=timezone.utc;SYMBOLS=('BTCUSDT','ETHUSDT')
KIND='historical_daily_assumption';VOLUME_FRACTION=D('.001')
def utc(s):
 t=datetime.fromisoformat(s.replace('Z','+00:00'))
 if t.tzinfo is None:raise ValueError('aware model timestamp required')
 return t.astimezone(UTC)
def stamp(t):return t.isoformat().replace('+00:00','Z')
def moment(day,minute=0):return stamp(datetime.combine(date.fromisoformat(day),datetime.min.time(),UTC)+timedelta(minutes=minute))
def available(day):return stamp(utc(moment(day))+timedelta(days=1,minutes=1))
def sha(p):return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def number(x,positive=False):
 if isinstance(x,bool):raise ValueError('boolean numeric input')
 v=D(str(x))
 if not v.is_finite() or v<0 or positive and v<=0:raise ValueError('invalid numeric input')
 return v

def evidence(p,at,snapshot):return {'kind':KIND,'payload':p,'model_available_at':at,'payload_sha256':sha(p),'input_snapshot_sha256':snapshot,'first_public_at':None}
def validate_evidence(e,at):
 if set(e)!={'kind','payload','model_available_at','payload_sha256','input_snapshot_sha256','first_public_at'} or e['kind']!=KIND or e['first_public_at'] is not None:raise ValueError('daily-model evidence only; no claimed historical publication')
 if sha(e['payload'])!=e['payload_sha256'] or utc(e['model_available_at'])>utc(at) or len(e['input_snapshot_sha256'])!=64:raise ValueError('invalid modeled evidence/hash/time')
 return e['payload']
def validate_open(q,at):
 if set(q)!={'symbol','venue','product','source_day','model_observed_at','reference_price','first_public_at'}:raise ValueError('no invented quote fields')
 if q['symbol'] not in SYMBOLS or q['venue']!='HISTORICAL_DAILY_SPOT_REFERENCE' or q['product']!='spot' or q['first_public_at'] is not None:raise ValueError('unsupported reference identity')
 if q['model_observed_at']!=moment(q['source_day']) or utc(q['model_observed_at'])!=utc(at):raise ValueError('only current opening model reference')
 number(q['reference_price'],True)
def capacity(day,volume):
 volume=str(number(volume));return {'source_day':day,'assumed_available_at':available(day),'base_volume':volume,'fraction':str(VOLUME_FRACTION),'quantity':str(D(volume)*VOLUME_FRACTION),'evidence':'SYNTHETIC_LAGGED_VOLUME_CAP_NOT_AVAILABLE_DEPTH'}
def validate_capacities(p,at):
 if set(p)!=set(SYMBOLS):raise ValueError('both modeled capacity assumptions required')
 for s,v in p.items():
  expected=(utc(at).date()-timedelta(days=1 if utc(at).time()>=datetime.min.replace(minute=1).time() else 2)).isoformat()
  if v['source_day']!=expected:raise ValueError('capacity must use latest completed observation available at model time')
  if v!=capacity(v['source_day'],v['base_volume']) or utc(v['assumed_available_at'])>utc(at):raise ValueError('capacity not known at intent creation')
 return p

def open_evidence(day,rows,snapshot):
 p={s:{'symbol':s,'venue':'HISTORICAL_DAILY_SPOT_REFERENCE','product':'spot','source_day':day,'model_observed_at':moment(day),'reference_price':str(rows[s]['open']),'first_public_at':None} for s in SYMBOLS}
 return evidence(p,moment(day),snapshot)
def bars_evidence(history,index,snapshot):
 p={}
 for s in SYMBOLS:
  selected=history[s][index-40:index]
  if len(selected)!=40:raise ValueError('40 strictly earlier closes required')
  bars=[]
  for row in selected:
   base={'day':row['day'],'close':str(row['close'])};bars.append({**base,'assumed_available_at':available(row['day']),'source_sha256':sha(base)})
  p[s]=bars
 return evidence(p,moment(history[SYMBOLS[0]][index]['day'],1),snapshot)

def validate_decision_evidence(e,signal_date,at):
 p=validate_evidence(e,at);day=utc(at).date()
 if at!=moment(day.isoformat(),1) or signal_date!=(day-timedelta(days=1)).isoformat() or e['model_available_at']!=at:raise ValueError('fixed00:01 decision/latest completed signal day required')
 if set(p)!=set(SYMBOLS):raise ValueError('both historical symbols required')
 for symbol,bars in p.items():
  if len(bars)!=40:raise ValueError('exactly40 closes required')
  for i,bar in enumerate(bars):
   expected=(date.fromisoformat(signal_date)-timedelta(days=39-i)).isoformat()
   base={'day':bar['day'],'close':bar['close']}
   if bar['day']!=expected or bar['assumed_available_at']!=available(expected) or utc(bar['assumed_available_at'])>utc(at) or bar['source_sha256']!=sha(base):raise ValueError('fixed daily bar availability/sequence/hash required')
   number(bar['close'],True)
 return p
