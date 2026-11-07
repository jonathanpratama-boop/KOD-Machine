"""Activate the reporting-only check and automatic private dashboard delivery."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
STATE=Path('/var/lib/kod/research-r2')
OLD=Path('/var/lib/kod-research-r2-ops/repairs/comparison-inputs-20261107/export_results.py')
sys.path.insert(0,'/opt/kod/research-r2')
from broad_observer.store import BroadStore

before=subprocess.run(['systemctl','show','kod-research-r2.service','-p','MainPID','-p','ActiveState'],capture_output=True,text=True,check=True).stdout
if 'ActiveState=active' not in before:
    raise RuntimeError('Collector is not active before reporting installation')
new=(HERE/'export_results.py').read_bytes()
old=OLD.read_bytes()
if hashlib.sha256(old).hexdigest() not in {
        '8fb2fc5a26cd56b94a396f2e93c8c86a2785c0bddbbb510dd0bc5f478b14fedd',
        hashlib.sha256(new).hexdigest()}:
    raise RuntimeError('Exporter changed concurrently; inspect before replacing')
backup=HERE/'previous_export_results.py'
if not backup.exists():backup.write_bytes(old)
temporary=OLD.with_suffix('.new');temporary.write_bytes(new);temporary.chmod(0o644);os.replace(temporary,OLD)

path=STATE/'comparison-inputs/PROSPECTIVE_CHECK.json'
if path.exists():
    registration=json.loads(path.read_text())
    if registration.get('schema')!='KOD_PROSPECTIVE_CHECK_V1':raise ValueError('Unexpected registration')
else:
    registration={'schema':'KOD_PROSPECTIVE_CHECK_V1',
        'started_at':dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),
        'timing_arm_minutes':1,'horizon_hours':24}
    with path.open('x') as f:json.dump(registration,f,sort_keys=True);f.write('\n')
    path.chmod(0o644)
store=BroadStore(STATE)
batch='prospective-check-v1:'+registration['started_at']
now=dt.datetime.now(dt.timezone.utc)
if not store.lookup(batch,now):
    raw=[{'name':'PROSPECTIVE_CHECK.json','body':path.read_bytes()}]
    raw += [{'name':name,'body':(HERE/name).read_bytes()} for name in
        ['export_results.py','publish_dashboard.py','one_page.html','PROSPECTIVE_CHECK.md']]
    receipt=store.append_batch(batch,now,'REGISTERED',raw,registration,kind='prospective_check')
else:receipt=store.lookup(batch,now)
dropin=Path('/etc/systemd/system/kod-research-r2-backup.service.d/95-dashboard.conf')
dropin.write_text('[Service]\nExecStartPost=-/usr/bin/python3 -B /var/lib/kod-research-r2-ops/repairs/prospective-check-20261108/publish_dashboard.py\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
# Export once now. The existing timer repeats this without collector changes.
subprocess.run(['runuser','-u','kod','--','python3','-B',str(OLD),
    '--state',str(STATE),'--out',str(STATE/'comparison-inputs/RESULTS.json')],check=True)
after=subprocess.run(['systemctl','show','kod-research-r2.service','-p','MainPID','-p','ActiveState'],capture_output=True,text=True,check=True).stdout
if before!=after:raise RuntimeError('Collector identity changed during reporting installation')
record={'registration':registration,'collector':after,'collector_restarted':False,
    'archive_record':receipt['hash'],'backup_post_step':str(dropin)}
(HERE/'INSTALLATION.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,sort_keys=True))
