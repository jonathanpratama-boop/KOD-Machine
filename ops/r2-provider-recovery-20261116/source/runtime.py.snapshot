"""Bounded public-data lanes for the R2 capacity worker; no account APIs."""
import datetime as dt
import hashlib,json,threading,urllib.parse
from pathlib import Path
from .adapters import PublicBatchAdapters,normalize_metadata,_transport
from .store import BroadStore,canonical,digest,iso,timestamp
from .capacity import _atomic

class WorkerPaused(RuntimeError):pass

class RestLanes:
    def __init__(self,state,metadata_raw,*,primary_symbols,source_adapter_class=None,transport=None,clock=None):
        self.root=Path(state);self.clock=clock or (lambda:dt.datetime.now(dt.timezone.utc));self.lock=threading.RLock()
        self.metadata_frame=normalize_metadata(json.loads(metadata_raw));self.metadata_frame['raw_sha256']=digest(metadata_raw)
        self.primary=tuple(primary_symbols);self.network=transport or _transport
        self.source_adapter_class=source_adapter_class
        self.source_cache=self.root/'SOURCE_CACHE.json';self.source_stops=self.root/'SOURCE_HOST_STOPS.json'
        self.metadata_cache=self.root/'METADATA_CACHE.json'
        self.adapter=PublicBatchAdapters(transport=self._market_transport,now_fn=self.clock)
        self.detail_adapter=PublicBatchAdapters(transport=self._market_transport,now_fn=self.clock,max_bytes=16*1024)
        self.broad_adapter=PublicBatchAdapters(transport=self._market_transport,now_fn=self.clock,max_bytes=128*1024)
        if self.metadata_cache.exists():self.metadata_frame=json.loads(self.metadata_cache.read_bytes())

    def _gate(self):
        if any((self.root/name).exists() for name in ('PAUSED.json','PROVIDER_STOP.json')):
            raise WorkerPaused('new capacity worker is paused; no request sent')

    def _market_transport(self,url,timeout,max_bytes):
        self._gate()
        result=self.network(url,timeout,max_bytes)
        headers={str(k).lower():v for k,v in result.get('headers',{}).items()}
        weights=[headers[k] for k in ('x-mbx-used-weight-1m','x-mbx-used-weight') if k in headers]
        reason=None
        try:weight=max(int(x) for x in weights) if weights else None
        except (ValueError,TypeError):weight=None
        if result.get('status') in (403,418,429,451) or 'retry-after' in headers:reason='PROVIDER_ACCESS_OR_RATE_STOP'
        elif weight is None:reason='SHARED_WEIGHT_TELEMETRY_UNAVAILABLE'
        elif weight>=300:reason='CONSERVATIVE_SHARED_IP_WEIGHT_CEILING'
        if reason:
            _atomic(self.root/'PROVIDER_STOP.json',{'reason':reason,'at':iso(self.clock()),'http_status':result.get('status'),'reported_weight':weight,'scope':'new observer only','url':url})
        return result

    def _quote(self,symbols,seconds):
        self._gate()
        with self.lock:metadata=self.metadata_frame
        # Both frozen capacity panels contain BTC/ETH, so one request gives each
        # token and both benchmarks identical actual request/receipt intervals.
        if not {'BTCUSDT','ETHUSDT'}.issubset(symbols):raise ValueError('fresh same-batch benchmarks required')
        if len(symbols)>150:raise ValueError('capacity quote panel must fit one verified batch')
        adapter=self.detail_adapter if len(symbols)<=5 else self.broad_adapter
        return adapter.bbo_symbols_frame(metadata,sorted(symbols),cohort=sorted(s for s in symbols if s in self.primary),frame_timeout=seconds)

    def broad(self,*,symbols,target_at):return self._quote(symbols,10)
    def detailed(self,*,symbols,target_at):return self._quote(symbols,5)

    def _archive_context(self,kind,target_at,result,summary):
        receipt=BroadStore(self.root).append_batch('context:'+kind+':'+iso(target_at),self.clock(),result['status'],result.get('raw_http',[]),summary,kind='context_'+kind)
        return {'status':result['status'],'raw_http':[],'summary':{**summary,'context_archive_hash':receipt['hash'],'context_archive_day':receipt['day'],'context_archive_seq':receipt['seq']},'requires_operator_review':result.get('requires_operator_review',False)}

    def metadata(self,*,target_at,symbols=None):
        self._gate();result=self.adapter.metadata();frame=result.get('summary')
        summary={'kind':'daily_metadata','target_at':target_at,'status':result['status'],
            'raw_symbol_count':frame.get('raw_symbol_count') if frame else None,
            'normalized_spot_usdt_count':frame.get('normalized_spot_usdt_count') if frame else None,
            'metadata_raw_sha256':frame.get('raw_sha256') if frame else None,
            'membership_policy':'record changes; fixed primary never replaced',
            'missing_primary':sorted(set(self.primary)-{r['symbol'] for r in frame.get('symbols',[])}) if frame else list(self.primary)}
        archived=self._archive_context('metadata',target_at,result,summary)
        if frame is not None and result['status']=='OK':
            with self.lock:self.metadata_frame=frame
            # Commit source bytes before publishing a derived cache that names
            # them. Backup captures controls before its journal snapshot.
            _atomic(self.metadata_cache,frame)
        return archived

    def stats(self,*,symbols,target_at):
        self._gate()
        with self.lock:metadata=self.metadata_frame
        result=self.adapter.stats24h(metadata,cohort=self.primary);frame=result.get('summary') or {}
        summary={k:v for k,v in frame.items() if k not in ('rows','unmatched_rows','cohort_status')}
        summary.update(kind='hourly_activity_context',target_at=target_at,status=result['status'])
        return self._archive_context('stats',target_at,result,summary)

    def catalyst(self,*,target_at,symbols=None):
        self._gate()
        if self.source_adapter_class is None:
            return {'status':'NOT_COVERED','raw_http':[],'summary':{'source_feed_quality':{},'economic_enrollment':False,'reason':'source lane not configured'}}
        cache=json.loads(self.source_cache.read_bytes()) if self.source_cache.exists() else {'markers':[],'first_received':{}}
        stopped=json.loads(self.source_stops.read_bytes()) if self.source_stops.exists() else {}
        bodies={};total=[0]
        def capture(raw):
            sha=hashlib.sha256(raw).hexdigest()
            if sha not in bodies:
                total[0]+=len(raw)
                if total[0]>8*1024**2:raise ValueError('bounded source response total exceeded')
                bodies[sha]=raw
            return sha
        adapter=self.source_adapter_class(capture=capture)
        old_transport=adapter.transport
        def guarded(url,method,body,timeout,max_bytes):
            self._gate();host=urllib.parse.urlparse(url).hostname
            if host in stopped:raise WorkerPaused('registered source host stopped; no request sent')
            r=old_transport(url,method,body,timeout,max_bytes)
            headers={str(k).lower():str(v) for k,v in r.get('headers',{}).items()}
            if r.get('status') in (403,418,429,451) or 'retry-after' in headers:
                stopped[host]={'status':r.get('status'),'at':iso(self.clock()),'reason':'SOURCE_PROVIDER_STOP_NO_HOST_FALLBACK'}
                _atomic(self.source_stops,stopped)
            return r
        adapter.transport=guarded
        collection=adapter.collect(bootstrap=True,seen_ids=set(cache['markers']))
        attempts=collection.get('source_attempts',[]);raw_http=[]
        for a in attempts:
            item=dict(a)
            if item.get('raw_sha256') in bodies:item['body']=bodies[item['raw_sha256']]
            raw_http.append(item)
        observations=[];markers=set(cache['markers'])
        for o in collection.get('observations',[]):
            cid=o['candidate_id'];cache['first_received'].setdefault(cid,o.get('received_at') or iso(self.clock()));markers.add(cid)
            if o.get('detail_complete') and o.get('detail_version_marker'):markers.add(o['detail_version_marker'])
            observations.append({k:o.get(k) for k in ('source_id','candidate_id','published_at','received_at','raw_sha256','last_posted_at','detail_complete','detail_status')}
                |{'first_received_at':cache['first_received'][cid],'semantic_status':'CAPACITY_WATCH_NOT_ENROLLED'})
        if len(markers)>10000:raise ValueError('source marker bound exceeded')
        cache['markers']=sorted(markers)
        quality=collection.get('coverage',{}).get('sources',{})
        for feed,v in quality.items():v['coverage_semantics']='bounded feed evidence; not complete economics or a no-catalyst claim'
        summary={'kind':'independent_official_source_poll','target_at':target_at,'status':collection.get('status','FAILED'),
            'source_feed_quality':quality,'source_host_stops':stopped,'observations':observations,
            'economic_enrollment':False,'semantic_acceptance':'NOT_IMPLEMENTED_DURING_CAPACITY_TRIAL',
            'unmapped_assets':'NOT_COVERED','historical_policies':'BOOTSTRAP_NOT_NEW_DISCOVERIES'}
        # Body identities remain independent of volatile BBO minute containers,
        # allowing unchanged official pages to reuse exact immutable bytes.
        archived=self._archive_context('source',target_at,{'status':summary['status'],'raw_http':raw_http},summary)
        cache['last_source_archive_hash']=archived['summary']['context_archive_hash']
        _atomic(self.source_cache,cache)
        return archived
