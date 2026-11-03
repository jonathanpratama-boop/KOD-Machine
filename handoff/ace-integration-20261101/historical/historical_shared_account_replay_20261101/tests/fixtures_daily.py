"""Invented daily tapes, never historical data."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import daily_adapter as a
import daily_core as c
import replay
from datetime import date,timedelta
SNAPSHOT='a'*64

def tape(n=48,start='2020-01-01',rising=True,volume='1000000'):
 result={}
 for s in a.SYMBOLS:
  rows=[]
  for i in range(n):
   price=100+(i if rising else -i)*.2+(i%3)*.01
   rows.append({'day':(date.fromisoformat(start)+timedelta(days=i)).isoformat(),'open':str(price),'close':str(price+.03),'volume':volume})
  result[s]=rows
 return result

def init(ledger,h,policy='TREND_V2_SHARED',index=40):
 start=h[a.SYMBOLS[0]][index]['day'];end=h[a.SYMBOLS[0]][-1]['day'];terminal=(date.fromisoformat(end)-timedelta(days=1)).isoformat()
 return ledger.transact({'op':'init','at':a.moment(start),'account_id':'mock:'+policy,'initial_cash':'10000','mode':'historical_daily_assumption','policy':policy,'terminal_decision_at':a.moment(terminal,1),'input_snapshot_sha256':SNAPSHOT,'scenario':c.SCENARIO})
def mark(ledger,h,index):
 day=h[a.SYMBOLS[0]][index]['day'];e=a.open_evidence(day,{s:h[s][index] for s in a.SYMBOLS},SNAPSHOT)
 r=ledger.transact({'op':'mark_batch','at':a.moment(day),'evidence':e,'capacities':replay.caps(h,index,2)})
 return e,r

def fill(ledger,h,index):
 e,r=mark(ledger,h,index);day=h[a.SYMBOLS[0]][index]['day'];rs=[]
 order=sorted(a.SYMBOLS,key=lambda s:not any(o['symbol']==s and o['status']=='PENDING' and o['side']=='SELL' for o in ledger.state()['intents']))
 for s in order:rs.append(ledger.transact({'op':'observe','at':a.moment(day),'evidence':a.evidence(e['payload'][s],a.moment(day),SNAPSHOT)}))
 return rs

def decide(ledger,h,index=40,terminal=False):
 day=h[a.SYMBOLS[0]][index]['day']
 return ledger.transact({'op':'decision','at':a.moment(day,1),'signal_date':h[a.SYMBOLS[0]][index-1]['day'],'evidence':a.bars_evidence(h,index,SNAPSHOT),'capacities':replay.caps(h,index,1),'terminal':terminal})
