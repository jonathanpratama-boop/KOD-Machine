"""One fixed daily-account experiment, using reviewed v2 mechanics. Network absent."""
import argparse,copy,fcntl,hashlib,json,math,os,statistics
from datetime import date,timedelta,datetime,timezone
from decimal import Decimal as D
from pathlib import Path
import daily_adapter as a
import daily_core as c
POLICIES=c.POLICIES
PARTITIONS={'development':('2017-09-26','2023-01-01'),'validation':('2023-01-01','2026-09-30')}

class ReplayWriter:
 """Linear new-file writer; existing KOD hash primitives plus final full core replay."""
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  self.lock=open(str(path)+'.lock','a');fcntl.flock(self.lock,fcntl.LOCK_EX)
  try:self.file=open(path,'xb',buffering=0)
  except BaseException:
   fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close();raise
  self.previous=None;self.ids=set();self.state=None;self.count=0
  self.pins=c.bundle_pins()
 def transact(self,command):
  command=json.loads(c.canonical(command));oid=c.operation_id(command)
  if oid in self.ids:raise ValueError('offline duplicate operation; no rewrite')
  st,result=c.apply(self.state,command)
  row={'id':oid,'type':'PAPER_OPERATION','command':command,'input_sha256':c.sha(command),'provenance':self.pins,'result':c.wire(result),'state_sha256':c.sha(st),'previous_record_hash':self.previous}
  row['record_hash']=c._core.event_hash(row);raw=(c.canonical(row)+'\n').encode()
  view=memoryview(raw)
  while view:
   written=self.file.write(view)
   if not written:raise OSError('offline journal partial write; preserve and stop')
   view=view[written:]
  self.previous=row['record_hash'];self.ids.add(oid);self.state=st;self.count+=1
  return result
 def close_without_claim(self):
  if not self.file.closed:self.file.close()
  if not self.lock.closed:fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close()
 def finish(self):
  self.file.flush();os.fsync(self.file.fileno());self.file.close()
  fd=os.open(self.path.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
  fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close()
  replayed=c.Ledger(self.path).state()
  if c.sha(replayed)!=c.sha(self.state):raise ValueError('independent sequential replay differs')
  return {'events':self.count,'last_record_hash':self.previous,'final_state_sha256':c.sha(replayed),'journal_sha256':hashlib.sha256(self.path.read_bytes()).hexdigest(),'replay':'PASS'}

def caps(history,index,offset):return {s:a.capacity(history[s][index-offset]['day'],history[s][index-offset]['volume']) for s in a.SYMBOLS}
def metrics(st,turnover,exposures):
 daily=st['daily'];nav=[r['nav'] for r in daily]
 if any(x is None or x<=0 for x in nav):raise ValueError('incomplete/nonpositive scored NAV')
 elapsed=(date.fromisoformat(daily[-1]['date'])-date.fromisoformat(daily[0]['date'])).days
 returns=[float(b/a0-1) for a0,b in zip(nav,nav[1:])];mean=statistics.mean(returns) if returns else 0;sd=statistics.stdev(returns) if len(returns)>1 else 0
 fills=st['fills'];notional=sum((f['quantity']*f['price'] for f in fills),D(0));fees=sum((f['fee'] for f in fills),D(0))
 slip=sum((f['quantity']*abs(f['price']-D(f['reference_price'])) for f in fills),D(0))
 cash=D('10000')+sum((f['cash_change'] for f in fills),D(0))
 holdings={s:sum((f['quantity']*(1 if f['side']=='BUY' else -1) for f in fills if f['symbol']==s),D(0)) for s in a.SYMBOLS}
 if cash!=st['cash_total'] or holdings!=st['holdings'] or fees!=st['realized_fees']:raise ValueError('cash/holdings/fees reconciliation failed')
 end=c.account_view(st,st['clock'])
 if end['nav']!=nav[-1]:raise ValueError('final NAV reconciliation failed')
 intents={o['id']:o for o in st['intents']}
 kill_fills=[f for f in fills if intents[f['intent_id']].get('reason')=='PERSISTENT_KILL']
 terminal_fills=[f for f in fills if intents[f['intent_id']]['made_at']==st['terminal_decision_at'] and intents[f['intent_id']].get('reason')!='PERSISTENT_KILL']
 first_liq=kill_fills[0]['model_observed_at'] if kill_fills else None
 liquidation={'first_kill_liquidation_at':first_liq,'last_kill_liquidation_at':kill_fills[-1]['model_observed_at'] if kill_fills else None,'kill_to_first_fill_days':(a.utc(first_liq)-a.utc(st['kill']['at'])).total_seconds()/86400 if first_liq else None,'kill_fill_count':len(kill_fills),'preplanned_terminal_fill_count':len(terminal_fills),'remaining_holdings':st['holdings']}
 if len(exposures)!=len(daily) or any(x is None for x in exposures):raise ValueError('exposure summary incomplete')
 exposure={'basis':'daily_postfill_open_reference','minimum':min(exposures),'maximum':max(exposures),'mean':sum(exposures,D(0))/D(len(exposures)),'invested_samples':sum(x>0 for x in exposures),'samples':len(exposures)}
 return c.wire({'initial_cash':'10000','end_account':end,'growth':nav[-1]/D('10000')-1,'CAGR':float(nav[-1]/D('10000'))**(365/elapsed)-1 if elapsed else 0,'sampled_max_drawdown':st['maximum_observed_drawdown'],'daily_vol_annualized':sd*math.sqrt(365),'daily_Sharpe':mean/sd*math.sqrt(365) if sd else None,'Sharpe_zero_variance':sd==0,'days':elapsed,'daily_samples':len(daily),'fills':len(fills),'paid_fees':fees,'modeled_slippage':slip,'traded_notional':notional,'normalized_turnover':turnover,'annualized_normalized_turnover':turnover*D(365)/D(elapsed) if elapsed else D(0),'kill':st['kill'],'liquidation':liquidation,'exposure':exposure,'pending_intents':[o for o in st['intents'] if o['status']=='PENDING'],'first_fill':fills[0]['model_observed_at'] if fills else None,'last_fill':fills[-1]['model_observed_at'] if fills else None,'reconciliation':'PASS'})

def run_case(history,start,end,policy,path,snapshot):
 days=[r['day'] for r in history[a.SYMBOLS[0]]];lo,hi=days.index(start),days.index(end)
 if lo<40 or hi<=lo+1 or any([r['day'] for r in history[s]]!=days for s in a.SYMBOLS):raise ValueError('invalid/warmup-deficient partition')
 terminal=a.moment((date.fromisoformat(end)-timedelta(days=1)).isoformat(),1)
 writer=ReplayWriter(path);writer.transact({'op':'init','at':a.moment(start),'account_id':policy+':'+start,'initial_cash':'10000','mode':'historical_daily_assumption','policy':policy,'terminal_decision_at':terminal,'input_snapshot_sha256':snapshot,'scenario':c.SCENARIO})
 try:
  turnover=D(0);exposures=[]
  for i in range(lo,hi+1):
   day=days[i];at=a.moment(day);st=writer.state
   # No market observation can change an empty, permanently killed account or CASH.
   inactive=policy=='CASH' or st['kill'] is not None and not any(st['holdings'].values())
   if not inactive:
    e=a.open_evidence(day,{s:history[s][i] for s in a.SYMBOLS},snapshot)
    r=writer.transact({'op':'mark_batch','at':at,'evidence':e,'capacities':caps(history,i,2)})
    nav_before=r['account']['nav'];day_notional=D(0)
    order=sorted(a.SYMBOLS,key=lambda s:not any(o['symbol']==s and o['status']=='PENDING' and o['side']=='SELL' for o in writer.state['intents']))
    for s in order:
     q=a.evidence(e['payload'][s],at,snapshot)
     r=writer.transact({'op':'observe','at':at,'evidence':q})
     day_notional+=sum((f['quantity']*f['price'] for f in r['fills']),D(0))
    if nav_before is not None and nav_before>0:turnover+=day_notional/nav_before
   daily_result=writer.transact({'op':'daily','at':at,'date':day});exposures.append(daily_result['account']['gross_fraction'])
   if i==hi:continue
   is_terminal=a.moment(day,1)==terminal
   should_decide=policy!='CASH' and (is_terminal or (not writer.state['kill'] and (policy=='TREND_V2_SHARED' or i==lo)))
   if should_decide:
    writer.transact({'op':'decision','at':a.moment(day,1),'signal_date':days[i-1],'evidence':a.bars_evidence(history,i,snapshot),'capacities':caps(history,i,1),'terminal':is_terminal})
  result=metrics(writer.state,turnover,exposures);result['journal']=writer.finish();result.update(policy=policy,start=start,terminal_open=end)
  return result
 finally:writer.close_without_claim()

def save(path,value):
 with open(path,'x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-reviewed-historical',action='store_true');p.add_argument('--clearance',type=Path);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args()
 if not args.run_reviewed_historical or args.clearance is None:p.error('OFF by default; independent exact-pin historical clearance required')
 clearance=json.loads(args.clearance.read_text())
 if clearance.get('approved_for_canonical_historical_run') is not True or clearance.get('source_pins')!=c.bundle_pins():raise ValueError('missing/stale independent clearance')
 args.output_dir.mkdir(parents=True,exist_ok=False)
 from history_inputs import checked_local
 started=datetime.now(timezone.utc).isoformat();save(args.output_dir/'START_PIN.json',{'started_at':started,'source_pins':c.bundle_pins(),'clearance':clearance,'partitions':PARTITIONS,'policies':POLICIES,'classification':'EXPLORATORY_REUSED_DATA_DAILY_APPROXIMATION'})
 history,quality=checked_local(args.inputs);save(args.output_dir/'INPUT_VALIDATION.json',quality)
 results={}
 for partition,(start,end) in PARTITIONS.items():
  results[partition]={}
  for policy in POLICIES:
   print('Running fixed case',partition,policy,flush=True)
   r=run_case(history,start,end,policy,args.output_dir/(partition+'_'+policy+'.jsonl'),quality['snapshot_sha256']);results[partition][policy]=r
   save(args.output_dir/(partition+'_'+policy+'_summary.json'),r)
 save(args.output_dir/'RESULTS.json',{'classification':'EXPLORATORY_REUSED_DATA_DAILY_APPROXIMATION_NOT_QUOTE_PARITY','started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'input_snapshot_sha256':quality['snapshot_sha256'],'results':results})
 print(json.dumps(results,indent=2))
if __name__=='__main__':main()
