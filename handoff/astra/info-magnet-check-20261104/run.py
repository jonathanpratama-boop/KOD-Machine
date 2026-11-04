#!/usr/bin/env python3
"""Execute the frozen 24h INFO_MAGNET critical gate, retaining all exclusions/errors."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import datetime as dt
import hashlib
import json
from pathlib import Path
import random
import subprocess
import threading
from archive import Archive,DownloadError,DataError
from events_stats import parse_archive,summarize_paired

UTC=dt.timezone.utc
START=dt.datetime(2020,1,1,tzinfo=UTC)
CUTOFF=dt.datetime(2026,11,1,tzinfo=UTC)
FREEZE='e97a93e'

def stamp():return dt.datetime.now(UTC).isoformat()
def parse(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
def dump(path,obj):
    path=Path(path); tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n');tmp.replace(path)

def evaluate(event,archive,symbols):
    row=dict(event)
    if not event['primary_krw']:
        row['status']='SECONDARY_MARKET_NOT_PRIMARY';return row
    notice=parse(event['notice_at']);entry=parse(event['entry_at'])
    if notice<START or entry+dt.timedelta(hours=24)>CUTOFF:
        row['status']='OUTSIDE_FROZEN_MATURE_WINDOW';return row
    if event['review_required']:
        row['status']='UNRESOLVED_NOTICE';return row
    symbol=event['symbol']
    if symbol not in symbols:
        row['status']='UNMEASURABLE_NO_HISTORICAL_USDT_ARCHIVE';return row
    prior=notice.replace(minute=0,second=0,microsecond=0)-dt.timedelta(hours=1)
    try:
        bar=archive.bar(symbol,prior)
        if bar is None:
            row['status']='UNMEASURABLE_NO_PRE_NOTICE_HOUR';return row
        row['eligibility_bar_at']=prior.isoformat()
        row['eligible_on_archives']=True
        pool=[s for s in symbols if s!=symbol]
        seed=int.from_bytes(hashlib.sha256(('20261104|'+event['event_id']).encode()).digest(),'big')
        random.Random(seed).shuffle(pool)
        controls=[]; checked=0
        for candidate in pool:
            checked+=1
            if archive.bar(candidate,prior) is not None:
                controls.append(candidate)
                if len(controls)==5:break
        row['control_eligibility_probes']=checked
        row['control_symbols']=controls
        if len(controls)!=5:
            row['status']='UNRESOLVED_INSUFFICIENT_CONTROLS';return row
        # Controls are fixed from pre-notice availability before looking at exits.
        horizons={}
        for holding in (24,6,72):
            end=entry+dt.timedelta(hours=holding-1)
            if entry+dt.timedelta(hours=holding)>CUTOFF:
                horizons[str(holding)]={'status':'IMMATURE_AT_FROZEN_CUTOFF'};continue
            values={};missing=[]
            try:
                for instrument in [symbol,*controls]:
                    opened=archive.bar(instrument,entry);closed=archive.bar(instrument,end)
                    if opened is None or closed is None:
                        missing.append(instrument);continue
                    values[instrument]=float(closed['close']/opened['open']-1)
                if missing:
                    horizons[str(holding)]={'status':'UNRESOLVED_OUTCOME','missing_instruments':missing};continue
                horizons[str(holding)]={'status':'SCORED','event_gross_return':values[symbol],
                    'control_gross_returns':[values[s] for s in controls],
                    'entry_hour':entry.isoformat(),'last_exit_bar_hour':end.isoformat(),
                    'exit_at':(end+dt.timedelta(hours=1)).isoformat()}
            except (DownloadError,DataError,ValueError,OSError) as exc:
                horizons[str(holding)]={'status':'UNRESOLVED_DATA','error':f'{type(exc).__name__}: {exc}'}
        row['horizons']=horizons
        if horizons['24']['status']=='SCORED':
            row.update(horizons['24']);row['status']='SCORED'
        else:row['status']='UNRESOLVED_PRIMARY_OUTCOME'
    except (DownloadError,DataError,ValueError,OSError) as exc:
        row['status']='UNRESOLVED_DATA';row['error']=f'{type(exc).__name__}: {exc}'
    return row

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',required=True);p.add_argument('--cache',required=True);p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();base=Path(__file__).resolve().parent;out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    frozen=json.loads((base/'FREEZE.json').read_text())
    for n,h in frozen['files'].items():
        if hashlib.sha256((base/n).read_bytes()).hexdigest()!=h:raise RuntimeError('Frozen specification changed: '+n)
    inventory=parse_archive(a.raw_dir);dump(out/'NOTICE-INVENTORY.json',inventory)
    archive=Archive(a.cache,max_workers=a.workers)
    excluded=set(json.loads((base/'EXCLUSIONS.json').read_text())['base_assets'])
    all_symbols=archive.historical_symbols()
    symbols=[s for s in all_symbols if s[:-4] not in excluded]
    dump(out/'ARCHIVE-UNIVERSE.json',{'as_of':stamp(),'all_historical_usdt_symbols':all_symbols,'control_pool_after_frozen_exclusions':symbols,'basis':'historical archive directories, including delisted symbols; controls must also have pre-notice-hour data'})
    print(json.dumps({'stage':'notice_inventory_and_universe','notices':inventory['notice_count'],'primary_events':inventory['primary_krw_events'],'historical_symbols':len(all_symbols),'control_pool':len(symbols)}),flush=True)
    rows=[];lock=threading.Lock()
    with ThreadPoolExecutor(a.workers) as executor:
        futures=[executor.submit(evaluate,e,archive,symbols) for e in inventory['events']]
        for future in as_completed(futures):
            row=future.result();rows.append(row)
            with (out/'EVENTS.jsonl').open('a') as stream:stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')
            if len(rows)%10==0 or len(rows)==len(futures):
                from collections import Counter
                counts=dict(Counter(r['status'] for r in rows));dump(out/'PROGRESS.json',{'as_of':stamp(),'done':len(rows),'total':len(futures),'counts':counts})
                print(json.dumps({'done':len(rows),'total':len(futures),'counts':counts}),flush=True)
    from collections import Counter
    rows.sort(key=lambda r:(r['notice_at'],r['event_id']));dump(out/'EVENTS.json',rows)
    scored=[r for r in rows if r['status']=='SCORED']
    unresolved=[r for r in rows if r['primary_krw'] and r['status'].startswith('UNRESOLVED')]
    # Unparseable likely-primary notices also keep the positive gate closed.
    parse_unknown=[r for r in inventory['rejected_notices'] if r.get('reason') not in ('OUTSIDE_FROZEN_TITLE_FAMILY',) and ('KRW' in str(r) or '원화' in str(r))]
    parse_unknown.extend(r for r in inventory['events'] if not r['markets'] and START<=parse(r['notice_at']) and parse(r['entry_at'])+dt.timedelta(hours=24)<=CUTOFF)
    if inventory['missing_pages'] or inventory['unique_notice_ids'] not in inventory['declared_total_counts']:
        parse_unknown.append({'reason':'NOTICE_INVENTORY_INCOMPLETE'})
    primary=summarize_paired(scored,expected_primary_count=len(scored)+len(unresolved),unresolved_primary=len(unresolved)+len(parse_unknown))
    secondary={}
    for h in ('6','72'):
        usable=[]
        for row in rows:
            value=row.get('horizons',{}).get(h,{})
            if row['primary_krw'] and value.get('status')=='SCORED':usable.append({'event_id':row['event_id'],'notice_at':row['notice_at'],**value})
        secondary[h]=summarize_paired(usable)
        secondary[h]['promotion_authority']=False
    result={'schema':'INFO_MAGNET_FAST_PRIMARY_RESULT_V1','completed_at':stamp(),'freeze_commit':FREEZE,
        'original_source_commit':'b04d31d5af7e34fa2f8e016bfffa8db1ab7ba13b','frozen_files':frozen,
        'notice_inventory_counts':{k:inventory[k] for k in ('notice_count','event_count','primary_krw_events')},
        'status_counts':dict(Counter(r['status'] for r in rows)),'primary_holding_hours':24,'primary':primary,
        'secondary_holding_hours':secondary,'unresolved_notice_exclusions':parse_unknown,
        'decision':'PRIMARY_GATE_PASS_PROSPECTIVE_PAPER_ONLY' if primary['pass_gate'] else ('INCONCLUSIVE_UNRESOLVED_EVIDENCE' if primary['unresolved_primary'] else 'PRIMARY_GATE_FAIL'),
        'entry_permission':False,'scope':'Exploratory retrospective primary tradability gate; not full reproduction of every original pilot diagnostic',
        'limitations':['Hourly opens are proxies, not owner-venue executable quotes.','Static product exclusions and exact ticker mapping may miss historical identity changes.','Archive presence is a conservative measurability condition; archive updates and later-notice edits cannot establish historical availability.','No independent forward holdout or same-asset serial-dependence correction; no profitability certification.','Owner cost is a fixed additive 2% assumption; further spread, slippage, FX and access remain unverified.']}
    dump(out/'RESULT.json',result)
    print(json.dumps({'decision':result['decision'],'primary':primary}),flush=True)

if __name__=='__main__':main()
