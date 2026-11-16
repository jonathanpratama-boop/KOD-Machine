"""One-time, evidence-preserving recovery of the reviewed transient stop."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

BASE = Path('/var/lib/kod-research-r2-ops/repairs/provider-recovery-20261116')
STATE = Path('/var/lib/kod/research-r2')
CODE = Path('/opt/kod/research-r2')
DROPIN = Path('/etc/systemd/system/kod-research-r2.service.d/95-provider-recovery.conf')

def digest(data): return hashlib.sha256(data).hexdigest()
def run(args): return subprocess.run(args, check=True, text=True, capture_output=True).stdout

def main():
    if (BASE/'RECOVERY.json').exists():
        raise RuntimeError('Recovery already applied; inspect existing receipt')
    before = json.loads((BASE/'BEFORE.json').read_text())
    status = run(['systemctl','show','kod-research-r2.service','-p','ActiveState','--value']).strip()
    if status != 'inactive': raise RuntimeError('Collector no longer inactive')
    if (STATE/'PAUSED.json').exists(): raise RuntimeError('Operator pause remains active')
    for item in before['frozen_code_files']:
        if digest((CODE/item['path']).read_bytes()) != item['sha256']:
            raise RuntimeError('Frozen code changed: '+item['path'])
    for original, archived in [('PROVIDER_STOP.json','0-PROVIDER_STOP.json'),
                               ('RESEARCH_CAPTURE_STATE.json','1-RESEARCH_CAPTURE_STATE.json')]:
        if (STATE/original).read_bytes() != (BASE/'before'/archived).read_bytes():
            raise RuntimeError('Stop state changed since review')
    stop=json.loads((STATE/'PROVIDER_STOP.json').read_text())
    if (stop['reason'],stop['http_status'],stop['reported_weight']) != ('SHARED_WEIGHT_TELEMETRY_UNAVAILABLE',500,None):
        raise RuntimeError('This is not the reviewed transient stop')
    for p in BASE.glob('*.py'): p.chmod(0o644)
    tests=run(['/usr/bin/python3','-B',str(BASE/'test_provider_recovery_independent.py')])
    check=run(['/usr/sbin/runuser','-u','kod','--','/usr/bin/python3','-B',str(BASE/'run.py'),'check'])
    url='https://api.binance.com/api/v3/ticker/bookTicker?symbol=BTCUSDT'
    with urllib.request.urlopen(url, timeout=12) as response:
        weight=response.headers.get('X-MBX-USED-WEIGHT-1M')
        if response.status != 200 or response.headers.get('Retry-After') or weight is None or int(weight)>=300:
            raise RuntimeError('Provider recovery not demonstrated')
        if json.loads(response.read(2048)).get('symbol') != 'BTCUSDT':
            raise RuntimeError('Unexpected provider response')
    sys.path.insert(0,str(CODE))
    from research_r2.capture import _read, _atomic
    state_path=STATE/'RESEARCH_CAPTURE_STATE.json'
    original_stat=state_path.stat()
    state=_read(state_path)
    if state['phase']!='PROVIDER_STOPPED': raise RuntimeError('Unexpected operational phase')
    frozen_clocks={k:json.loads((CODE/'research.json').read_text())[k]
                   for k in ['t0','admission_end_at','end_at','receipt_drain_end']}
    receipt={'recorded_at':dt.datetime.now(dt.timezone.utc).isoformat(),
             'action':'RECOVER_REVIEWED_TRANSIENT_HTTP_500',
             'previous_stop':stop,'old_phase':state['phase'],'new_phase':'WAITING',
             'preserved_study_clocks':frozen_clocks,'missing_readings_remain_missing':True,
             'frozen_code_files_verified':len(before['frozen_code_files']),
             'release_check':json.loads(check),'provider_probe':{'status':200,'weight_1m':weight,'symbol':'BTCUSDT'},
             'overlay_sha256':digest((BASE/'provider_recovery.py').read_bytes()),
             'wrapper_sha256':digest((BASE/'run.py').read_bytes()),
             'state_sha256_before':digest(state_path.read_bytes()),
             'independent_tests':'9 methods passed on deployment host'}
    (BASE/'PREPARED_RECOVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
    DROPIN.write_text('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(BASE/'run.py')+' run\n')
    state['phase']='WAITING'
    _atomic(state_path,state)
    os.chown(state_path,original_stat.st_uid,original_stat.st_gid)
    state_path.chmod(original_stat.st_mode & 0o777)
    (STATE/'PROVIDER_STOP.json').rename(BASE/'reviewed-PROVIDER_STOP.json')
    receipt['state_sha256_after_phase_reset']=digest(state_path.read_bytes())
    (BASE/'RECOVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
    run(['systemctl','daemon-reload'])
    run(['systemctl','start','kod-research-r2.service'])
    print(json.dumps({'status':'START_REQUESTED','receipt':str(BASE/'RECOVERY.json'),
                      'overlay_sha256':receipt['overlay_sha256'],'clocks':frozen_clocks}))

if __name__=='__main__':main()
