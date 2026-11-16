"""Development checks; independent adversarial tests are performed by root."""
import datetime as dt
import json
from pathlib import Path
import threading
from types import SimpleNamespace

from provider_recovery import install

class Clock:
    value = 0
    def now(self): return self.value
    def sleep(self, value): self.value += value

class Rest:
    def __init__(self, response):
        self.lock = threading.RLock()
        self.root = Path('/unused')
        self.response = response
        self.requests = 0
    def clock(self): return dt.datetime.now(dt.timezone.utc)
    def _gate(self): pass
    def network(self, *args):
        self.requests += 1
        return self.response

def trial(response):
    records=[]; clock=Clock()
    module=SimpleNamespace(RestLanes=Rest, _atomic=lambda p,v:records.append(v),iso=lambda d:d.isoformat())
    transport=install(module,monotonic=clock.now,sleep=clock.sleep)
    worker=Rest(response)
    assert transport(worker,'https://api.binance.com/test',5,1000) is response
    return records,worker,clock,transport

checks=[]
for status in [500,502,503,504,599]:
    records,worker,clock,transport=trial({'status':status,'headers':{},'body':b'failed'})
    assert not records and worker._transient_retry_at==2
    transport(worker,'https://api.binance.com/test',5,1000)
    assert clock.value==2 and worker._transient_retry_at==6
    checks.append(f'{status}: error retained, transient retry')
for status in [403,418,429,451]:
    records,*_=trial({'status':status,'headers':{}})
    assert records[0]['reason']=='PROVIDER_ACCESS_OR_RATE_STOP'
    checks.append(f'{status}: existing restriction retained')
for status in [200,400]:
    records,*_=trial({'status':status,'headers':{}})
    assert records[0]['reason']=='SHARED_WEIGHT_TELEMETRY_UNAVAILABLE'
    checks.append(f'{status}: missing telemetry retains existing stop')
records,*_=trial({'status':503,'headers':{'Retry-After':'120'}})
assert records[0]['reason']=='PROVIDER_ACCESS_OR_RATE_STOP'
records,*_=trial({'status':500,'headers':{'X-MBX-USED-WEIGHT-1M':'300'}})
assert records[0]['reason']=='CONSERVATIVE_SHARED_IP_WEIGHT_CEILING'
records,worker,clock,transport=trial({'status':500,'headers':{}})
try: transport(worker,'https://api.binance.com/test',1,1000)
except TimeoutError: pass
else: raise AssertionError('backoff sent request outside timeout')
assert worker.requests==1
worker.response={'status':200,'headers':{'X-MBX-USED-WEIGHT-1M':'2'}}
transport(worker,'https://api.binance.com/test',5,1000)
assert worker._transient_retry_at==0 and worker._transient_failures==0
print(json.dumps({'status':'PASS','checks':checks,'additional_checks':['Retry-After retained','reported ceiling retained','timeout blocks request','success resets backoff']}))
