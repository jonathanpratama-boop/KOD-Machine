"""Read-only verification of the ONE completed canonical output. No alternate runs."""
import json,hashlib,sys,statistics,math
from pathlib import Path
from decimal import Decimal as D,ROUND_HALF_UP
from datetime import datetime,date,timedelta
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'historical_shared_account_results_20261101T1134'
def check(v,msg):
 if not v:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def utc(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def load(p):return json.loads(p.read_text())
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-12)
partial='--completed' in sys.argv
if partial:
 results={'results':{},'input_snapshot_sha256':load(OUT/'INPUT_VALIDATION.json')['snapshot_sha256']}
 for file in sorted(OUT.glob('*_summary.json')):
  part,policy=file.name[:-len('_summary.json')].split('_',1);results['results'].setdefault(part,{})[policy]=load(file)
else:results=load(OUT/'RESULTS.json')
start=load(OUT/'START_PIN.json');quality=load(OUT/'INPUT_VALIDATION.json');clear=load(ROOT/'historical-independent-audit/REVIEW_CLEARANCE.json')
check(start['source_pins']==clear['source_pins'],'clearance mismatch')
for name,digest in clear['source_pins'].items():check(sha((ROOT/'historical_shared_account_replay_20261101'/name).read_bytes())==digest,'source changed '+name)
check(sha((ROOT/'historical-independent-audit/REVIEW.md').read_bytes())==clear['review_report_sha256'],'review changed')
check(quality['snapshot_sha256']==results['input_snapshot_sha256'],'snapshot mismatch')
check(len(quality['objects'])==220 and quality['network_requests']==0,'input scope')
report={'scope':'ONE_CANONICAL_RUN_READ_ONLY_POSTRUN_AUDIT','input_snapshot_sha256':quality['snapshot_sha256'],'cases':{}}
for partition,policies in results['results'].items():
 for policy,s in policies.items():
  path=OUT/(partition+'_'+policy+'.jsonl');raw=path.read_bytes();check(sha(raw)==s['journal']['journal_sha256'],'journal SHA')
  check(s==load(OUT/(partition+'_'+policy+'_summary.json')),'combined/individual summary mismatch')
  cash=D('10000');hold={'BTCUSDT':D(0),'ETHUSDT':D(0)};fees=D(0);slip=D(0);notional=D(0);normalized=D(0);marks={};ids=set();fillids=set();previous=None;daily=[];peak=D('10000');maxdd=D(0);kill=None;fillcount=0;firstliq=None;exposures=[];lastclock=None;events=0
  day_notional=D(0);opening_nav=None
  for line in raw.splitlines():
   r=json.loads(line);cmd=r['command'];res=r['result'];at=utc(cmd['at']);events+=1
   check(r['id'] not in ids,'duplicate operation');ids.add(r['id']);check(r['previous_record_hash']==previous,'chain link');check(r['record_hash']==sha(canonical({k:v for k,v in r.items() if k!='record_hash'}).encode()),'chain hash');previous=r['record_hash'];check(r['provenance']==clear['source_pins'],'provenance')
   check(lastclock is None or at>=lastclock,'clock reversal');lastclock=at
   check(at.date()<=date.fromisoformat(s['terminal_open']),'beyond terminal')
   if events==1:check(cmd['initial_cash']=='10000' and at.date().isoformat()==s['start'],'initial condition')
   if 'evidence' in cmd:
    e=cmd['evidence'];check(e['input_snapshot_sha256']==quality['snapshot_sha256'],'mixed snapshot');check(sha(canonical(e['payload']).encode())==e['payload_sha256'],'evidence hash')
   if cmd['op']=='mark_batch':
    marks={symbol:D(q['reference_price']) for symbol,q in cmd['evidence']['payload'].items()};opening_nav=cash+sum(hold[x]*marks[x] for x in hold);day_notional=D(0)
   if cmd['op']=='decision':
    check(at.hour==0 and at.minute==1 and at.second==0,'decision model time')
    for bars in cmd['evidence']['payload'].values():
     check(len(bars)==40,'warmup');check(bars[-1]['day']==(at.date()-timedelta(days=1)).isoformat(),'future decision data')
     for bar in bars:check(utc(bar['assumed_available_at'])<=at and date.fromisoformat(bar['day'])<at.date(),'future close')
   if kill is not None:check(res.get('kill')==kill,'kill reset/change')
   for f in res.get('fills',[]):
    check(f['id'] not in fillids,'duplicate fill');fillids.add(f['id']);fillcount+=1
    q,p,fee=D(f['quantity']),D(f['price']),D(f['fee']);ref=D(f['reference_price']);cap=f['capacity_assumption'];side=f['side'];sym=f['symbol']
    check(q<=D(cap['quantity']) and D(cap['quantity'])==D(cap['base_volume'])*D('.001'),'capacity')
    check(utc(cap['assumed_available_at'])<at,'future capacity');check(f['model_observed_at']==cmd['at'],'fill time')
    if f['intent_id'].startswith('decision:'):
     signal=date.fromisoformat(f['intent_id'].split(':')[1]);check(at.date()>signal+timedelta(days=1),'same decision-day fill')
    if side=='BUY':check(kill is None,'entry after persistent kill')
    check(p==ref*(D('1.0005') if side=='BUY' else D('.9995')),'slippage');check(fee==(q*p*D('.001')).quantize(D('.01'),rounding=ROUND_HALF_UP),'fee')
    delta=-q*p-fee if side=='BUY' else q*p-fee;check(delta==D(f['cash_change']),'cash flow')
    cash+=delta;hold[sym]+=q if side=='BUY' else -q;fees+=fee;notional+=q*p;day_notional+=q*p;slip+=q*abs(p-ref)
    check(cash>=0 and min(hold.values())>=0,'negative cash/holdings')
    if f['intent_id'].startswith('liquidate:'):
     check(res.get('kill') is not None and at>utc(res.get('kill')['at']),'same-trigger liquidation');firstliq=firstliq or cmd['at']
   if res.get('kill') is not None:kill=res.get('kill')
   av=res['account'];check(D(av['cash_total'])==cash and {x:D(v) for x,v in av['holdings'].items()}==hold,'event account reconciliation');check(0<=D(av['cash_reserved'])<=cash,'reservation')
   if av['nav'] is not None:
    nav=cash+sum(hold[x]*marks.get(x,D(0)) for x in hold);check(nav==D(av['nav']),'NAV');peak=max(peak,nav);maxdd=max(maxdd,(peak-nav)/peak)
   if cmd['op']=='daily':
    daily.append((cmd['date'],D(res['sample']['nav'])));exposures.append(D(av['gross_fraction']))
    if opening_nav is not None:normalized+=day_notional/opening_nav
    day_notional=D(0);opening_nav=None
  check(events==s['journal']['events'] and previous==s['journal']['last_record_hash'],'event totals')
  check(r['state_sha256']==s['journal']['final_state_sha256'],'final state receipt')
  check(cash==D(s['end_account']['cash_total']) and hold=={x:D(v) for x,v in s['end_account']['holdings'].items()},'summary balances')
  check(fees==D(s['paid_fees']) and notional==D(s['traded_notional']) and slip==D(s['modeled_slippage']) and fillcount==s['fills'],'summary fills/costs')
  check(normalized==D(s['normalized_turnover']),'turnover')
  check(maxdd==D(s['sampled_max_drawdown']),'drawdown')
  check(kill==s['kill'] and firstliq==s['liquidation']['first_kill_liquidation_at'],'kill/liquidation')
  if kill and kill['reason']=='NEGATIVE_TRAILING_90_DAY_SHARPE':
   window=[x for x in daily if x[0]<=kill['at'][:10]][-91:];check(len(window)==91,'kill warmup');rr=[float(b[1]/a[1]-1) for a,b in zip(window,window[1:])];check(statistics.mean(rr)<0,'Sharpe kill reason')
  if kill and kill['reason']=='DRAWDOWN_AT_LEAST_25_PERCENT':check(maxdd>=D('.25'),'drawdown kill reason')
  check(len(daily)==s['daily_samples'] and daily[0][0]==s['start'] and daily[-1][0]==s['terminal_open'],'daily boundaries')
  check(all(date.fromisoformat(b[0])-date.fromisoformat(a[0])==timedelta(days=1) for a,b in zip(daily,daily[1:])),'daily gap')
  returns=[float(b[1]/a[1]-1) for a,b in zip(daily,daily[1:])];sd=statistics.stdev(returns);mean=statistics.mean(returns)
  check(close(sd*math.sqrt(365),s['daily_vol_annualized']),'volatility');check((sd==0 and s['daily_Sharpe'] is None) or close(mean/sd*math.sqrt(365),s['daily_Sharpe']),'Sharpe')
  check(daily[-1][1]/D('10000')-1==D(s['growth']),'growth');check(close(float(daily[-1][1]/D('10000'))**(365/s['days'])-1,s['CAGR']),'CAGR')
  check(min(exposures)==D(s['exposure']['minimum']) and max(exposures)==D(s['exposure']['maximum']) and sum(exposures)/D(len(exposures))==D(s['exposure']['mean']),'exposure')
  report['cases'][partition+'/'+policy]={'status':'PASS','events':events,'fills':fillcount,'NAV':str(daily[-1][1]),'growth':s['growth'],'kill':kill,'first_liquidation':firstliq,'residual_holdings':{x:str(v) for x,v in hold.items()},'source_pins':'MATCH','journal_sha256':sha(raw)}
print(json.dumps(report,indent=2))
